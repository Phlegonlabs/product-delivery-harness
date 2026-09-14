#!/usr/bin/env python3
"""Hardened Git subprocess helpers for authority-bearing repository reads."""

from __future__ import annotations

import os
import re
import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Mapping


class GitMetadataError(RuntimeError):
    """Raised when local Git metadata can substitute immutable objects."""


class GitConfigurationError(GitMetadataError):
    """Raised when local Git configuration can retarget or execute a helper."""


_REPOSITORY_ENVIRONMENT = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES_RELATIVE",
    "GIT_SHALLOW_FILE",
    "GIT_NAMESPACE",
    "GIT_REPLACE_REF_BASE",
}

# These variables either select a configuration file/key or cause Git to
# execute a caller-provided helper.  They are never inherited by an
# authority-bearing Git command.  The deny-list is deliberately broader than
# the exact variables currently used by the repository so aliases and future
# Git additions cannot become an injection escape hatch.
_CONFIGURATION_ENVIRONMENT_PREFIX = "GIT_CONFIG"
_HELPER_ENVIRONMENT = {
    "GIT_SSH_COMMAND",
    "GIT_SSH",
    "GIT_ASKPASS",
    "GIT_PROXY_COMMAND",
    "GIT_SSH_VARIANT",
    "SSH_ASKPASS",
    "SSH_ASKPASS_REQUIRE",
    "GIT_EXTERNAL_DIFF",
    "GIT_EXEC_PATH",
    "GIT_TERMINAL_PROMPT",
    "GIT_EDITOR",
    "GIT_SEQUENCE_EDITOR",
    "GIT_DIFF_OPTS",
}

_REMOTE_COMMANDS = {
    "clone",
    "fetch",
    "fetch-pack",
    "ls-remote",
    "pull",
    "push",
    "receive-pack",
    "send-pack",
    "upload-pack",
}

# Config keys which can silently change where Git connects or execute a local
# process during a remote operation.  Normal remote.<name>.url/pushurl keys
# are intentionally not rejected: the caller binds the resolved, exact URL in
# an immutable request and rechecks it immediately before any side effect.
_DANGEROUS_CONFIG_EXACT = {
    "core.sshcommand",
    "core.gitproxy",
    "http.proxy",
    "https.proxy",
    "http.proxycommand",
    "https.proxycommand",
    "credential.helper",
    "core.hookspath",
    "core.fsmonitor",
    "include.path",
    "http.sslverify",
    "https.sslverify",
    "http.sslcainfo",
    "https.sslcainfo",
    "http.sslcert",
    "https.sslcert",
    "http.sslkey",
    "https.sslkey",
    "http.extraheader",
    "https.extraheader",
}


def _path_has_reparse_or_link(path: Path) -> bool:
    """Return true when any existing component is a link/reparse point."""

    current = Path(path)
    while True:
        try:
            if current.is_symlink():
                return True
            if os.name == "nt" and current.exists():
                # ``stat().st_file_attributes`` is available on modern
                # Windows Python and exposes junctions without following
                # them.  Keep the fallback conservative when unavailable.
                attributes = getattr(current.stat(), "st_file_attributes", 0)
                if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400):
                    return True
        except OSError:
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _machine_git_roots() -> tuple[Path, ...]:
    if os.name == "nt":
        return windows_machine_roots()
    return (Path("/usr").resolve(), Path("/bin").resolve(), Path("/opt").resolve())


def windows_machine_roots() -> tuple[Path, ...]:
    """Resolve Windows system roots through kernel32, never caller env vars."""

    if os.name != "nt":
        return ()


    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if not length:
            return ()
        windows = Path(buffer.value[:length]).resolve()
        drive = Path(windows.anchor)
        return (windows, (drive / "Program Files").resolve())
    except (AttributeError, OSError, ValueError):
        return ()


def windows_icacls_path() -> tuple[Path, str] | None:
    """Bind the ACL inspector to System32; never resolve it from PATH."""

    roots = windows_machine_roots()
    if not roots:
        return None
    candidate = roots[0] / "System32" / "icacls.exe"
    try:
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file() or _path_has_reparse_or_link(resolved):
            return None
        return resolved, hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError:
        return None


def _trusted_executable(path: Path, label: str) -> Path:
    """Bind an executable to an administrator-managed, non-reparse path."""

    try:
        resolved = path.resolve(strict=True)
        resolved.stat()
    except OSError as exc:
        raise GitMetadataError(f"{label} is unavailable: {path}") from exc
    if not resolved.is_file() or _path_has_reparse_or_link(path):
        raise GitMetadataError(f"{label} must be a non-reparse regular file: {resolved}")
    try:
        resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        pass
    else:
        raise GitMetadataError(f"{label} must not come from the current repository/worktree: {resolved}")
    roots = _machine_git_roots()
    if not any(_is_within(resolved, root) for root in roots):
        raise GitMetadataError(f"{label} must come from an OS-protected install path: {resolved}")
    if os.name != "nt":
        for component in (resolved, *resolved.parents):
            component_info = component.stat()
            if component_info.st_uid != 0 or component_info.st_mode & 0o022:
                raise GitMetadataError(f"{label} path must be root-owned and not writable by group/other: {component}")
    elif resolved.suffix.casefold() != ".exe":
        raise GitMetadataError(f"{label} must be a native .exe on Windows: {resolved}")
    elif _windows_parent_user_writable(resolved.parent):
        raise GitMetadataError(f"{label} parent is user-writable: {resolved.parent}")
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _windows_parent_user_writable(path: Path) -> bool:
    """Use native owner/DACL AccessCheck and fail closed on uncertainty."""

    if os.name != "nt" or windows_icacls_path() is None:
        return os.name == "nt"
    return _windows_acl_allows_current_write(Path(path))


def _windows_acl_allows_current_write(path: Path) -> bool:
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi32.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    advapi32.OpenThreadToken.restype = wintypes.BOOL
    advapi32.OpenThreadToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.DuplicateToken.restype = wintypes.BOOL
    advapi32.DuplicateToken.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.AccessCheck.restype = wintypes.BOOL
    owner_sid = ctypes.c_void_p()
    group_sid = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    descriptor = ctypes.c_void_p()
    status = advapi32.GetNamedSecurityInfoW(
        str(path),
        1,
        1 | 2 | 4,  # OWNER | GROUP | DACL security information
        ctypes.byref(owner_sid),
        ctypes.byref(group_sid),
        ctypes.byref(dacl),
        None,
        ctypes.byref(descriptor),
    )
    if status != 0 or not descriptor.value:
        return True
    owner_text = ctypes.c_wchar_p()
    try:
        if not advapi32.ConvertSidToStringSidW(owner_sid, ctypes.byref(owner_text)):
            return True
        owner = owner_text.value or ""
        if owner not in {"S-1-5-18", "S-1-5-32-544"} and not owner.startswith("S-1-5-80-"):
            return True
        source_token = wintypes.HANDLE()
        kernel32.GetCurrentThread.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        token_access = 0x0008 | 0x0002  # TOKEN_QUERY | TOKEN_DUPLICATE
        if not advapi32.OpenThreadToken(kernel32.GetCurrentThread(), token_access, True, ctypes.byref(source_token)) and not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), token_access, ctypes.byref(source_token)):
            return True
        try:
            token = wintypes.HANDLE()
            if not advapi32.DuplicateToken(
                source_token,
                2,  # SecurityImpersonation
                ctypes.byref(token),
            ):
                return True
            try:
                class GenericMapping(ctypes.Structure):
                    _fields_ = [("read", wintypes.DWORD), ("write", wintypes.DWORD), ("execute", wintypes.DWORD), ("all", wintypes.DWORD)]
                mapping = GenericMapping(0x120089, 0x120116, 0x1200A0, 0x1F01FF)
                advapi32.AccessCheck.argtypes = [
                    wintypes.LPVOID,
                    wintypes.HANDLE,
                    wintypes.DWORD,
                    ctypes.POINTER(GenericMapping),
                    wintypes.LPVOID,
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.BOOL),
                ]
                privilege = ctypes.create_string_buffer(1024)
                privilege_length = wintypes.DWORD(len(privilege))
                granted = wintypes.DWORD()
                access_status = wintypes.BOOL()
                checked = advapi32.AccessCheck(
                    descriptor,
                    token,
                    0x02000000,  # MAXIMUM_ALLOWED
                    ctypes.byref(mapping),
                    privilege,
                    ctypes.byref(privilege_length),
                    ctypes.byref(granted),
                    ctypes.byref(access_status),
                )
                dangerous = (
                    0x00000002  # FILE_ADD_FILE / FILE_WRITE_DATA
                    | 0x00000004  # FILE_ADD_SUBDIRECTORY / FILE_APPEND_DATA
                    | 0x00000010  # FILE_WRITE_EA
                    | 0x00000100  # FILE_WRITE_ATTRIBUTES
                    | 0x00010000  # DELETE
                    | 0x00040000  # WRITE_DAC
                    | 0x00080000  # WRITE_OWNER
                )
                return (
                    not checked
                    or not access_status.value
                    or bool(int(granted.value) & dangerous)
                )
            finally:
                kernel32.CloseHandle(token)
        finally:
            kernel32.CloseHandle(source_token)
    finally:
        if owner_text:
            kernel32.LocalFree(owner_text)
        if descriptor:
            kernel32.LocalFree(descriptor)


def windows_parent_user_writable(path: Path) -> bool:
    """Shared effective-access policy for trusted Windows parent directories."""

    return _windows_parent_user_writable(path)


def git_executable(environment: Mapping[str, str] | None = None) -> str:
    """Resolve Git once and reject PATH-shadowed or repository-local binaries."""

    source = dict(os.environ if environment is None else environment)
    found = shutil.which("git", path=source.get("PATH"))
    if found is None:
        raise GitMetadataError("administrator-installed Git executable is unavailable")
    return str(_trusted_executable(Path(found), "Git executable"))


def _normalise_config_name(value: str) -> str:
    return value.strip().casefold()


def _dangerous_config_name(value: str) -> bool:
    """Return whether a local config key can retarget or execute a helper."""

    name = _normalise_config_name(value)
    if name in _DANGEROUS_CONFIG_EXACT:
        return True
    # Includes can pull an attacker-controlled config file into the local
    # repository.  ``includeif`` is represented with a dotted suffix.
    if name.startswith("includeif.") and name.endswith(".path"):
        return True
    # Credential helpers may be URL-scoped (credential.<url>.helper).
    if name.startswith("credential.") and name.endswith(".helper"):
        return True
    # Repository-local clean/smudge/process filters and command drivers can
    # execute arbitrary binaries while authority reads inspect blobs or status.
    if name.startswith("filter.") and name.rsplit(".", 1)[-1] in {
        "clean",
        "smudge",
        "process",
        "required",
    }:
        return True
    if name.startswith("diff.") and name.rsplit(".", 1)[-1] in {
        "command",
        "textconv",
    }:
        return True
    if name.startswith("merge.") and name.endswith(".driver"):
        return True
    # URL rewrite rules apply even when the command receives an explicit URL.
    if name.startswith("url.") and name.endswith((".insteadof", ".pushinsteadof")):
        return True
    # Per-remote proxy/helper/transport commands can execute a different
    # endpoint or process.  Keep remote URL/pushurl itself available for exact
    # endpoint binding and retarget detection.
    if name.startswith("remote.") and name.rsplit(".", 1)[-1] in {
        "proxy",
        "uploadpack",
        "receivepack",
        "helper",
    }:
        return True
    # Git also accepts protocol-specific proxy keys and arbitrary HTTP proxy
    # scopes (http.<url>.proxy / https.<url>.proxy).
    if name.endswith(".proxy") or name.endswith(".proxycommand"):
        return True
    return bool(re.search(r"(?:^|\.)(?:sshcommand|gitproxy|uploadpack|receivepack)$", name))


def git_environment(
    environment: Mapping[str, str] | None = None,
    *,
    trusted_boundary: bool = False,
) -> dict[str, str]:
    """Return an environment safe for authority-bearing Git operations.

    ``trusted_boundary`` is explicit and intentionally narrow: it does not
    restore any ``GIT_CONFIG_*`` injection or helper variable.  A trusted host
    owns its separate authentication process; local Harness tooling remains
    sanitized on every path.
    """

    result = dict(os.environ if environment is None else environment)
    forbidden = _REPOSITORY_ENVIRONMENT | _HELPER_ENVIRONMENT
    # Environment names are case-insensitive on Windows.  Remove aliases by
    # normalized name so a caller cannot retain ``git_dir`` beside ``GIT_DIR``.
    # Every GIT_CONFIG_* spelling is removed, including numbered key/value
    # pairs used by Git's config injection protocol.
    result = {
        key: value
        for key, value in result.items()
        if key.upper() not in forbidden
        and not key.upper().startswith(_CONFIGURATION_ENVIRONMENT_PREFIX + "_")
        and key.upper() != _CONFIGURATION_ENVIRONMENT_PREFIX
        and not key.upper().startswith("GIT_SSL_")
    }
    # ``trusted_boundary`` is retained as an explicit call-site marker for
    # compatibility, but this module never restores helper environment
    # variables.  The separate trusted host owns its authentication process;
    # local Harness reads remain sanitized even when that marker is present.
    result["GIT_NO_REPLACE_OBJECTS"] = "1"
    return result


def git_argv(*arguments: str) -> list[str]:
    """Build a Git argv that reads raw object identities."""

    return [git_executable(), "--no-replace-objects", *arguments]


def _raw_git(
    root: Path,
    *arguments: str,
    capture_output: bool = True,
    text: bool = True,
    timeout: float = 30,
    check: bool = False,
    environment: Mapping[str, str] | None = None,
    input: str | bytes | None = None,
    encoding: str | None = None,
    errors: str | None = None,
    trusted_boundary: bool = False,
) -> subprocess.CompletedProcess[Any]:
    """Run Git without remote-config preflight (used by the preflight itself)."""

    return subprocess.run(
        git_argv(*arguments),
        cwd=root,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check,
        env=git_environment(environment, trusted_boundary=trusted_boundary),
        input=input,
        encoding=encoding,
        errors=errors,
    )


def reject_dangerous_local_config(
    root: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Reject local config that can retarget a remote or execute a helper.

    This is intentionally a read-only, local-file preflight.  Global/system
    credential helpers remain usable for a trusted host, while repository-local
    endpoint rewrites and helpers fail closed before ``ls-remote``/``push``.
    """

    resolved = Path(root).resolve()
    try:
        result = _raw_git(
            resolved,
            "config",
            "--show-origin",
            "--name-only",
            "--null",
            "--list",
            environment=environment,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitConfigurationError(f"cannot inspect local Git configuration: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() if isinstance(result.stderr, str) else ""
        raise GitConfigurationError(detail or "cannot inspect local Git configuration")
    fields = [item for item in result.stdout.split("\0") if item]
    dangerous: list[str] = []
    # ``git config --show-origin --name-only --null --list`` emits
    # origin/name pairs.  A malformed odd-length response is not trustworthy.
    if len(fields) % 2:
        raise GitConfigurationError("effective Git configuration listing is malformed")
    root_resolved = resolved
    for index in range(0, len(fields), 2):
        origin, name = fields[index], fields[index + 1]
        if not _dangerous_config_name(name):
            continue
        # Credential/filter/diff/merge helpers from an operator's global/system
        # config are ordinary workstation policy.  A repository-local helper
        # is rejected before every authority-bearing Git operation.  This
        # keeps trusted-host authentication workable without allowing a
        # checked-out repository to execute a sentinel command.
        normalized = _normalise_config_name(name)
        local_only_helper = (
            (normalized.startswith("credential.") and normalized.endswith(".helper"))
            or normalized.startswith("filter.")
            or (normalized.startswith("diff.") and normalized.rsplit(".", 1)[-1] in {"command", "textconv"})
            or (normalized.startswith("merge.") and normalized.endswith(".driver"))
            or normalized in {"core.hookspath", "core.fsmonitor"}
        )
        origin_path = origin.removeprefix("file:").replace("\\", "/")
        local_config = False
        if origin_path and not origin_path.startswith(("command:", "blob:", "stdin:")):
            try:
                origin_candidate = Path(origin_path)
                if not origin_candidate.is_absolute():
                    origin_candidate = root_resolved / origin_candidate
                local_config = _is_within(origin_candidate.resolve(strict=False), root_resolved / ".git")
            except OSError:
                local_config = True
        # Repository-local helpers, URL rewrites, endpoint overrides, and
        # local TLS weakening are never trusted.  System/global operator
        # policy remains available for corporate proxies and credential
        # helpers, but command-line/config-injection origins are rejected.
        remote_rewrite = normalized.startswith("url.") and normalized.endswith((".insteadof", ".pushinsteadof"))
        always_reject = remote_rewrite or normalized in {
            "http.sslverify",
            "https.sslverify",
            "http.extraheader",
            "https.extraheader",
        }
        proxy_or_tls = (
            normalized.endswith((".proxy", ".proxycommand"))
            or normalized in _DANGEROUS_CONFIG_EXACT
        )
        if local_only_helper or proxy_or_tls or remote_rewrite:
            if always_reject or local_config or origin.startswith(("command:", "blob:", "stdin:")):
                dangerous.append(f"{origin}:{name}")
            continue
        dangerous.append(f"{origin}:{name}")
    if dangerous:
        raise GitConfigurationError(
            "dangerous Git configuration is forbidden before authority access: "
            + ", ".join(dangerous)
        )


def _remote_access(arguments: tuple[str, ...]) -> bool:
    if not arguments:
        return False
    # Git options may precede the subcommand in callers that build argv
    # dynamically.  Ignore option values conservatively and only treat a known
    # command token as remote-sensitive.
    for argument in arguments:
        if argument.startswith("-"):
            continue
        return argument.casefold() in _REMOTE_COMMANDS or argument.casefold() == "remote"
    return False


def run_git(
    root: Path,
    *arguments: str,
    capture_output: bool = True,
    text: bool = True,
    timeout: float = 30,
    check: bool = False,
    environment: Mapping[str, str] | None = None,
    input: str | bytes | None = None,
    encoding: str | None = None,
    errors: str | None = None,
    trusted_boundary: bool = False,
) -> subprocess.CompletedProcess[Any]:
    """Run Git with replacement objects disabled and remote config preflight."""

    if arguments and not trusted_boundary:
        reject_dangerous_local_config(Path(root), environment=environment)
    return _raw_git(
        Path(root),
        *arguments,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check,
        environment=environment,
        input=input,
        encoding=encoding,
        errors=errors,
        trusted_boundary=trusted_boundary,
    )


def reject_object_substitution(root: Path) -> None:
    """Reject replace refs and legacy graft metadata in one repository.

    ``--no-replace-objects`` already makes each hardened read use the raw
    object. Rejecting the metadata as well prevents a caller from mistaking a
    clean worktree for a clean object database before a validation or side
    effect.
    """

    resolved = Path(root).resolve()
    try:
        refs = run_git(
            resolved,
            "for-each-ref",
            "--format=%(refname)",
            "refs/replace/",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitMetadataError(f"cannot inspect Git replacement refs: {exc}") from exc
    if refs.returncode != 0:
        raise GitMetadataError(
            refs.stderr.strip() or "cannot inspect Git replacement refs"
        )
    replacement_refs = [line for line in refs.stdout.splitlines() if line.strip()]
    if replacement_refs:
        raise GitMetadataError(
            "Git replacement refs are forbidden for exact-SHA validation: "
            + ", ".join(sorted(replacement_refs))
        )

    try:
        graft = run_git(resolved, "rev-parse", "--git-path", "info/grafts")
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitMetadataError(
            f"cannot resolve legacy Git graft metadata: {exc}"
        ) from exc
    if graft.returncode != 0 or not graft.stdout.strip():
        raise GitMetadataError(
            graft.stderr.strip() or "cannot resolve legacy Git graft metadata"
        )
    graft_path = Path(graft.stdout.strip())
    if not graft_path.is_absolute():
        graft_path = (resolved / graft_path).resolve(strict=False)
    try:
        graft_exists = graft_path.exists() or graft_path.is_symlink()
    except OSError as exc:
        raise GitMetadataError(
            f"cannot inspect legacy Git graft metadata: {exc}"
        ) from exc
    if graft_exists:
        raise GitMetadataError(
            f"legacy Git graft metadata is forbidden for exact-SHA validation: {graft_path}"
        )
