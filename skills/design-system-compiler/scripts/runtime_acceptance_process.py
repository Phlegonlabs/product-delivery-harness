"""Owned process-tree supervision for source-runtime browser acceptance.

The probe runs as ``node <probe file>`` inside the unchanged Harness
host_process tree: a Windows Job object (kill on close, emptiness checked by
job accounting) or a POSIX process group. The probe prints ``ds-owned`` lines
for itself and the Chromium processes it launched. After the tree returns,
on success, failure, exception or timeout, every recorded process must have
exited. Processes are identified by PID and start time, never by name.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

HARNESS_SCRIPTS = Path(__file__).resolve().parents[2] / "delivery-harness" / "scripts"
OWNED = "ds-owned "
# A live PID whose creation is later than the recorded start (plus clock slack) was reused by another process.
REUSE_SLACK_MS = 1500


class AcceptanceRunError(RuntimeError):
    """The probe did not produce a report; ``processes`` records the owned tree outcome."""

    def __init__(self, message: str, processes: list[dict]) -> None:
        super().__init__(message)
        self.processes = processes


def _host_process():
    if str(HARNESS_SCRIPTS) not in sys.path:
        sys.path.append(str(HARNESS_SCRIPTS))
    import host_process

    return host_process


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _QUERY_LIMITED = 0x1000
    _STILL_ACTIVE = 259

    def live_since(pid: int) -> float | None:
        """Creation time in epoch milliseconds of a live process, else None."""
        handle = _kernel32.OpenProcess(_QUERY_LIMITED, False, pid)
        if not handle:
            return None
        try:
            code = wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != _STILL_ACTIVE:
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            if not _kernel32.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
                return 0.0
            created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            return created / 10_000 - 11_644_473_600_000
        finally:
            _kernel32.CloseHandle(handle)
else:
    def live_since(pid: int) -> float | None:
        """POSIX exposes no portable start time here; a live PID counts as still owned."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            return 0.0
        return 0.0


def owned_records(stdout: str) -> list[dict]:
    rows = []
    for line in stdout.splitlines():
        if not line.startswith(OWNED):
            continue
        try:
            row = json.loads(line[len(OWNED):])
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("pid"), int) and isinstance(row.get("started"), (int, float)):
            rows.append(row)
    return rows


def exit_report(records: list[dict], *, command: list[str], purpose: str, launched: datetime, expiry: datetime) -> list[dict]:
    """One row per owned process: identity, purpose, expiry and whether it has exited."""
    report = []
    for row in records:
        created = live_since(row["pid"])
        exited = created is None or (created > 0 and created > row["started"] + REUSE_SLACK_MS)
        report.append({"role": str(row.get("role", "process"))[:40], "pid": row["pid"],
                       "started": datetime.fromtimestamp(row["started"] / 1000, timezone.utc).isoformat(),
                       "command": command if row.get("role") == "node" else str(row.get("command", ""))[:200],
                       "purpose": purpose, "launchedAt": launched.isoformat(), "expiry": expiry.isoformat(),
                       "exited": exited, "checkedAt": datetime.now(timezone.utc).isoformat()})
    return report


def run_probe(probe: str, arguments: list[str], *, timeout: float, purpose: str) -> tuple[str, list[dict]]:
    """Run the probe as an owned tree; return its stdout and the verified-exited process records."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for source-runtime browser acceptance")
    host = _host_process()
    with tempfile.TemporaryDirectory(prefix="ds-runtime-acceptance-") as folder:
        script = Path(folder) / "probe.cjs"
        script.write_text(probe, encoding="utf-8")
        command = [node, str(script), *arguments]
        launched = datetime.now(timezone.utc)
        expiry = launched + timedelta(seconds=timeout)
        try:
            result = host.run_process_tree(command, cwd=Path.cwd(), environment=dict(os.environ), timeout_seconds=timeout)
        except host.HostProcessError as error:
            processes = exit_report(owned_records(error.stdout), command=command[:2], purpose=purpose,
                                    launched=launched, expiry=expiry)
            raise AcceptanceRunError(f"browser acceptance process tree was not contained: {error}", processes) from error
    processes = exit_report(owned_records(result.stdout), command=command[:2], purpose=purpose, launched=launched, expiry=expiry)
    if any(not row["exited"] for row in processes):
        raise AcceptanceRunError("an owned browser acceptance process outlived its process tree", processes)
    if result.timeout:
        raise AcceptanceRunError(f"browser acceptance timed out after {timeout:g}s; its owned process tree was terminated", processes)
    if result.exit_code != 0:
        raise AcceptanceRunError("browser acceptance failed to run: " + result.stderr[-2000:], processes)
    return result.stdout, processes
