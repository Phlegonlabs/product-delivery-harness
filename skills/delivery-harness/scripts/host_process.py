#!/usr/bin/env python3
"""Run a host verifier as an owned process tree.

This is process ownership, not an OS sandbox.  Windows uses a Job object so
later descendants remain owned.  POSIX owns one process group; descendants that
successfully call ``setsid`` can escape that group and this helper cannot see or
terminate them.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


IS_WINDOWS = os.name == "nt"
CLEANUP_SECONDS = 5.0


class HostProcessError(RuntimeError):
    """A containment setup or cleanup operation failed."""

    def __init__(
        self,
        message: str,
        *,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True)
class HostProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timeout: bool = False


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    _PROCESS_ASSIGN_ACCESS = 0x0101  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
    _CREATE_SUSPENDED = 0x00000004
    _THREAD_SUSPEND_RESUME = 0x0002
    _TH32CS_SNAPTHREAD = 0x00000004
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CreateJobObjectW.argtypes = [
        wintypes.LPVOID,
        wintypes.LPCWSTR,
    ]
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
    ]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
    ]
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    _kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.CreateToolhelp32Snapshot.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _kernel32.OpenThread.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    _kernel32.OpenThread.restype = wintypes.HANDLE
    _kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    _kernel32.ResumeThread.restype = wintypes.DWORD

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    class _THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", ctypes.c_long),
            ("tpDeltaPri", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
        ]

    class _OwnedHandle:
        def __init__(self, handle: int, description: str) -> None:
            if not handle or handle == _INVALID_HANDLE_VALUE:
                raise HostProcessError(
                    f"cannot create {description}: error {ctypes.get_last_error()}"
                )
            self.handle = handle
            self.description = description

        def close(self) -> None:
            if self.handle:
                if not _kernel32.CloseHandle(self.handle):
                    raise HostProcessError(
                        f"cannot close {self.description}: "
                        f"error {ctypes.get_last_error()}"
                    )
                self.handle = 0


if IS_WINDOWS:
    for _name in ("Thread32First", "Thread32Next"):
        _function = getattr(_kernel32, _name)
        _function.argtypes = [wintypes.HANDLE, ctypes.POINTER(_THREADENTRY32)]
        _function.restype = wintypes.BOOL

    def _job_active_processes(job: _OwnedHandle) -> int:
        info = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        if not _kernel32.QueryInformationJobObject(
            job.handle, _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(info), ctypes.sizeof(info), None,
        ):
            raise HostProcessError(f"cannot inspect Windows job: error {ctypes.get_last_error()}")
        return int(info.ActiveProcesses)

    def _wait_job_empty(job: _OwnedHandle) -> None:
        if not _kernel32.TerminateJobObject(job.handle, 1):
            raise HostProcessError(f"cannot terminate Windows job: error {ctypes.get_last_error()}")
        deadline = time.monotonic() + CLEANUP_SECONDS
        while _job_active_processes(job):
            if time.monotonic() >= deadline:
                raise HostProcessError("Windows job still contains live processes")
            time.sleep(0.01)

    def _resume_initial_thread(process_id: int) -> None:
        snapshot = _OwnedHandle(
            _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0),
            "Windows thread snapshot",
        )
        entry = _THREADENTRY32()
        entry.dwSize = ctypes.sizeof(entry)
        try:
            found = _kernel32.Thread32First(snapshot.handle, ctypes.byref(entry))
            while found:
                if entry.th32OwnerProcessID == process_id:
                    thread = _OwnedHandle(
                        _kernel32.OpenThread(_THREAD_SUSPEND_RESUME, False, entry.th32ThreadID),
                        "suspended process thread",
                    )
                    try:
                        if _kernel32.ResumeThread(thread.handle) != 1:
                            raise HostProcessError("initial thread was not suspended exactly once")
                    finally:
                        thread.close()
                    return
                found = _kernel32.Thread32Next(snapshot.handle, ctypes.byref(entry))
            error = ctypes.get_last_error()
            raise HostProcessError(f"cannot find suspended initial thread: error {error}")
        finally:
            snapshot.close()

    def _run_windows(argv, cwd, environment, timeout_seconds, stdout, stderr):
        job = _OwnedHandle(_kernel32.CreateJobObjectW(None, None), "Windows job object")
        process = None
        try:
            limits = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not _kernel32.SetInformationJobObject(
                job.handle, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits), ctypes.sizeof(limits),
            ):
                raise HostProcessError(f"cannot configure Windows job: error {ctypes.get_last_error()}")
            try:
                process = subprocess.Popen(
                    list(argv), cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, creationflags=_CREATE_SUSPENDED,
                )
                opened = _OwnedHandle(
                    _kernel32.OpenProcess(_PROCESS_ASSIGN_ACCESS, False, process.pid),
                    "suspended process",
                )
                try:
                    if not _kernel32.AssignProcessToJobObject(job.handle, opened.handle):
                        raise HostProcessError(f"cannot assign process to Windows job: error {ctypes.get_last_error()}")
                finally:
                    opened.close()
                _resume_initial_thread(process.pid)
            except Exception as exc:
                raise HostProcessError(f"Windows process-tree setup failure: {exc}") from exc
            try:
                return process.wait(timeout=timeout_seconds), False
            except subprocess.TimeoutExpired:
                return None, True
        finally:
            try:
                _wait_job_empty(job)
            finally:
                try:
                    # Assignment may have failed while the direct process was suspended.
                    if process is not None:
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=CLEANUP_SECONDS)
                finally:
                    job.close()

else:
    def _live_group_processes(process_group: int) -> list[int]:
        # Use the OS utility rather than a project-supplied PATH entry.
        listing = subprocess.run(
            ["/bin/ps", "-axo", "pid=,stat=,pgid="], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1.0,
        )
        if listing.returncode:
            raise HostProcessError(f"cannot inspect POSIX process group: {listing.stderr.strip()}")
        live = []
        for line in listing.stdout.splitlines():
            fields = line.split()
            if not fields:
                continue
            if len(fields) != 3:
                raise HostProcessError("unexpected POSIX process table")
            process_id, state, group_id = int(fields[0]), fields[1], int(fields[2])
            if group_id == process_group and not state.upper().startswith("Z"):
                live.append(process_id)
        return live

    def _terminate_group(process_group: int) -> None:
        # Kill before polling so pipe owners cannot hold up output collection.
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + CLEANUP_SECONDS
        while _live_group_processes(process_group):
            if time.monotonic() >= deadline:
                raise HostProcessError("POSIX process group still contains live processes")
            time.sleep(0.01)

    def _run_posix(argv, cwd, environment, timeout_seconds, stdout, stderr):
        process = subprocess.Popen(
            list(argv), cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True,
        )
        try:
            try:
                return process.wait(timeout=timeout_seconds), False
            except subprocess.TimeoutExpired:
                return None, True
        finally:
            try:
                _terminate_group(process.pid)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=CLEANUP_SECONDS)


def run_process_tree(
    argv: Sequence[str], *, cwd: Path, environment: Mapping[str, str],
    timeout_seconds: float,
) -> HostProcessResult:
    """Finish the owned tree before reading output or returning to Git checks."""
    runner = _run_windows if IS_WINDOWS else _run_posix
    # Files avoid pipe backpressure and grandchildren keeping communicate() open.
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        try:
            code, timed_out = runner(argv, cwd, environment, timeout_seconds, stdout, stderr)
        except (HostProcessError, OSError, ValueError, subprocess.SubprocessError) as exc:
            stdout.seek(0)
            stderr.seek(0)
            raise HostProcessError(str(exc), stdout=stdout.read(), stderr=stderr.read()) from exc
        stdout.seek(0)
        stderr.seek(0)
        return HostProcessResult(code, stdout.read(), stderr.read(), timed_out)
