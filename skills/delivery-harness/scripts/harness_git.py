#!/usr/bin/env python3
"""Hardened Git subprocess helpers for authority-bearing repository reads."""

from __future__ import annotations

import os
import re
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
}


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
    }
    # ``trusted_boundary`` is retained as an explicit call-site marker for
    # compatibility, but this module never restores helper environment
    # variables.  The separate trusted host owns its authentication process;
    # local Harness reads remain sanitized even when that marker is present.
    result["GIT_NO_REPLACE_OBJECTS"] = "1"
    return result


def git_argv(*arguments: str) -> list[str]:
    """Build a Git argv that reads raw object identities."""

    return ["git", "--no-replace-objects", *arguments]


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
        if local_only_helper:
            origin_path = origin.removeprefix("file:").replace("\\", "/").casefold()
            local_config = (
                origin_path.endswith("/.git/config")
                or origin_path.endswith("/.git/config.worktree")
                or ("/.git/worktrees/" in origin_path and origin_path.endswith("/config"))
            )
            if not local_config:
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
