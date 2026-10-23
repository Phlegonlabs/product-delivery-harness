"""Native document displacement with bounded, preserving conflict recovery."""

import hashlib
import os
from pathlib import Path
import secrets
import stat
from typing import Any

def _posix_exchange(parent_fd: int, left_name: str, right_name: str) -> None:
    """Exchange two document names atomically; fail closed when unavailable."""

    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    # Linux renameat2(RENAME_EXCHANGE) and macOS renameatx_np(RENAME_SWAP)
    # take the same arguments and both use flag 0x2.
    exchange = getattr(libc, "renameat2", None)
    if exchange is None:
        exchange = getattr(libc, "renameatx_np", None)
    if exchange is None:
        raise OSError(
            "document commit requires renameat2(RENAME_EXCHANGE) or renameatx_np(RENAME_SWAP)"
        )
    exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    exchange.restype = ctypes.c_int
    if exchange(parent_fd, os.fsencode(left_name), parent_fd, os.fsencode(right_name), 0x2) != 0:
        error = ctypes.get_errno()
        raise OSError(f"document atomic exchange failed (errno={error})")



def _windows_replace(destination: Path, replacement: Path, backup: Path) -> None:
    """Use ReplaceFileW with an explicit displaced document backup."""

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReplaceFileW.restype = wintypes.BOOL
    kernel32.ReplaceFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    if os.path.lexists(backup):
        raise OSError(f"document transaction backup already exists: {backup}")
    if not kernel32.ReplaceFileW(str(destination), str(replacement), str(backup), 0x1, None, None):
        raise OSError(f"document ReplaceFileW failed (winerror={ctypes.get_last_error()}); inspect displaced backup if present: {backup}")



def _open_posix_parent_chain(path: Path) -> list[int]:
    """Open every parent component with O_NOFOLLOW and retain all handles."""

    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    handles: list[int] = []
    try:
        current_fd = os.open(os.sep, flags)
        handles.append(current_fd)
        components = [part for part in absolute.parts if part not in {absolute.anchor, ""}]
        for component in components:
            current_fd = os.open(component, flags, dir_fd=current_fd)
            handles.append(current_fd)
        return handles
    except OSError:
        for descriptor in reversed(handles):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise



def _open_windows_parent(path: Path, *, writable: bool = False) -> tuple[Any, int]:
    """Hold a non-reparse parent directory for a relative native rename."""

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    attrs = kernel32.GetFileAttributesW(str(path))
    if attrs == wintypes.DWORD(-1).value or attrs & 0x0400:
        raise OSError(f"document parent is unavailable or reparse: {path}")
    handle = kernel32.CreateFileW(
        str(path),
        0x80000000 | (0x40000000 | 0x0002 if writable else 0),  # read, plus add-file for final parent
        0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        3,  # OPEN_EXISTING
        0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        None,
    )
    if handle in (None, wintypes.HANDLE(-1).value):
        raise OSError(f"cannot hold document parent directory: {path}")
    class AttributeTag(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]
    kernel32.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    tag = AttributeTag()
    if not kernel32.GetFileInformationByHandleEx(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)) or tag.attributes & 0x400:
        kernel32.CloseHandle(handle)
        raise OSError(f"document parent is reparse or unreadable: {path}")
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not length:
        kernel32.CloseHandle(handle)
        raise OSError(f"cannot resolve held document parent directory: {path}")
    actual = buffer.value[:length].removeprefix("\\\\?\\").casefold().replace("\\", "/")
    expected = str(path.resolve(strict=True)).casefold().replace("\\", "/")
    if actual != expected:
        kernel32.CloseHandle(handle)
        raise OSError("held document parent directory changed before rename")
    return kernel32, int(handle)



def _open_windows_parent_chain(path: Path) -> list[tuple[Any, int]]:
    """Hold every existing Windows ancestor so no junction swap can retarget it."""

    absolute = Path(os.path.abspath(path))
    ancestors = [
        ancestor
        for ancestor in (list(reversed(absolute.parents)) + [absolute])
        if ancestor != Path(absolute.anchor)
    ]
    handles: list[tuple[Any, int]] = []
    try:
        for ancestor in ancestors:
            handles.append(_open_windows_parent(ancestor, writable=ancestor == absolute))
        return handles
    except BaseException:
        for kernel32, handle in reversed(handles):
            kernel32.CloseHandle(handle)
        raise



def _snapshot(path: Path, parent_fd=None):
    """Read the same no-follow regular object whose identity is returned."""
    location = path if parent_fd is None else path.name
    options = {} if parent_fd is None else {"dir_fd": parent_fd}
    before = os.stat(location, follow_symlinks=False, **options)
    if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400:
        raise OSError(f"document must be a regular non-reparse file: {path}")
    descriptor = os.open(location, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), **options)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError(f"document changed while opening: {path}")
        payload = stream.read(32 * 1024 * 1024 + 1)
        after = os.fstat(stream.fileno())
    token = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode)
    if len(payload) > 32 * 1024 * 1024 or token(opened) != token(after):
        raise OSError(f"document changed or exceeds the write limit: {path}")
    return (*token(after), hashlib.sha256(payload).hexdigest()), payload


def _parents_current(path, descriptors):
    if os.name == "nt":
        return True  # Held ancestor handles deny deletion and renaming.
    for index, component in enumerate(path.parent.parts[1:]):
        observed = os.stat(component, dir_fd=descriptors[index], follow_symlinks=False)
        held = os.fstat(descriptors[index + 1])
        if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev, observed.st_ino) != (held.st_dev, held.st_ino):
            return False
    return True


def _new_name(path):
    return f".pdh-conflict-{path.name}-{secrets.token_hex(16)}"


def _swap(path, replacement, parent_fd):
    if os.name == "nt":
        backup = path.parent / _new_name(path)
        _windows_replace(path, path.parent / replacement, backup)
        return backup.name
    _posix_exchange(parent_fd, replacement, path.name)
    return replacement


def replace_existing_bytes(path, payload, expected, *, before_commit=None):
    """Use native displacement; preserve concurrent edits captured by either swap.

    Recovery is bounded to one preserving restore. Conflict files are retained
    for the owner. This does not guarantee later writes through old handles.
    """
    path = Path(os.path.abspath(path))
    descriptors = []
    windows = []
    temporary = None
    staged_token = None
    displaced = None
    try:
        if os.name == "nt":
            windows = _open_windows_parent_chain(path.parent)
            parent_fd = None
        else:
            if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
                raise OSError("document writes require no-follow directory descriptors")
            descriptors = _open_posix_parent_chain(path.parent)
            parent_fd = descriptors[-1]
        expected_token, contents = _snapshot(path, parent_fd)
        if contents != expected:
            raise OSError(f"{path} content changed before write")
        temporary = _new_name(path)
        location = path.parent / temporary if parent_fd is None else temporary
        options = {} if parent_fd is None else {"dir_fd": parent_fd}
        descriptor = os.open(location, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600, **options)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            created = os.fstat(stream.fileno())
            if hasattr(os, "fchmod"):
                os.fchmod(stream.fileno(), stat.S_IMODE(expected_token[4]))
        if os.name == "nt":
            os.chmod(path.parent / temporary, stat.S_IMODE(expected_token[4]))
        staged_token, _ = _snapshot(path.parent / temporary, parent_fd)
        if staged_token[:2] != (created.st_dev, created.st_ino):
            raise OSError("document staging file changed")
        if before_commit is not None:
            before_commit(path.parent / temporary)
        if not _parents_current(path, descriptors) or _snapshot(path, parent_fd)[0] != expected_token:
            raise OSError(f"{path} content changed at the commit boundary")
        displaced = _swap(path, temporary, parent_fd)
        # After displacement, this name contains owner data, never staging.
        temporary = None
        observed_token = None
        try:
            observed_token, _ = _snapshot(path.parent / displaced, parent_fd)
            unchanged = (observed_token == expected_token and _parents_current(path, descriptors)
                         and _snapshot(path, parent_fd)[0] == staged_token)
        except OSError:
            unchanged = False
        if unchanged:
            if _snapshot(path.parent / displaced, parent_fd)[0] != expected_token:
                raise OSError(f"displaced document changed; retained at {path.parent / displaced}")
            os.unlink(path.parent / displaced) if parent_fd is None else os.unlink(displaced, dir_fd=parent_fd)
            if parent_fd is not None:
                os.fsync(parent_fd)
            return
        retained = [displaced]
        restored = False
        restore_error = None
        try:
            if _snapshot(path, parent_fd)[0] == staged_token:
                retained.append(_swap(path, displaced, parent_fd))
                restored = (_snapshot(path, parent_fd)[0] == observed_token
                            and _snapshot(path.parent / retained[-1], parent_fd)[0] == staged_token)
        except OSError as error:
            restore_error = str(error)
        raise OSError(f"{path} displaced bytes or parents changed; concurrent bytes preserved; restore verified={restored}, restore error={restore_error!r}; recovery entries {retained!r} in the bound directory originally named {path.parent}")
    finally:
        if temporary is not None and staged_token is not None:
            try:
                if _snapshot(path.parent / temporary, parent_fd)[0] == staged_token:
                    os.unlink(path.parent / temporary) if parent_fd is None else os.unlink(temporary, dir_fd=parent_fd)
            except OSError:
                pass
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        for kernel, handle in reversed(windows):
            kernel.CloseHandle(handle)
