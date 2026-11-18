#!/usr/bin/env python3
"""Epic landing gate: bind a recorded owner grant to one exact candidate.

``record`` writes the owner's pre-recorded landing grant outside the checkout.
``revoke`` drops a revocation marker beside it. ``check`` reports offline
whether the grant covers one action at one exact candidate commit, reading the
repository policy from the grant's frozen base commit. ``cleanup-plan`` prints
the commands that would remove the landed branch and its worktrees. The script
never contacts the network and never pushes, merges, deletes or writes inside
the checkout; every result only reports, it performs no action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from harness_core import ManifestError, is_full_sha
from harness_git import GitMetadataError, run_git
from push_archived_candidate import _configured_push_url

GRANT_SCHEMA = "landing-grant/1"
AUTHORITY_NOTE = (
    "reports whether the recorded owner grant covers this action at this candidate; "
    "it performs no action"
)
ALLOWED_ACTIONS = ("push", "pull_request", "merge", "production_deploy", "cleanup", "review_threads")
PROTECTED_BRANCHES = ("refs/heads/main", "refs/heads/development")
BRANCH_PREFIX = "refs/heads/"
TARGET_REF = "refs/heads/main"
EVIDENCE_ACTIONS = ("merge", "production_deploy")
BUILTIN_OWNER_ONLY = ("AGENTS.md", "CLAUDE.md", ".github/workflows/*")
POLICY_HEADING = "## Delivery Autonomy"
POLICY_INELIGIBLE = (
    "the repository is not eligible; its Delivery Autonomy section on the base commit "
    "does not say `Landing: epic_grant`"
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_BAD_BRANCH_CHARS = set(" ~^:?*[\\\x7f")


def _git(root: Path, *args: str) -> str:
    result = run_git(root, *args, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _git_or_none(root: Path, *args: str) -> str | None:
    result = run_git(root, *args, capture_output=True, text=True, timeout=30, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _utc_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime | None:
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed


def _required_utc(value: str, flag: str) -> datetime:
    parsed = _parse_utc(value)
    if parsed is None:
        raise ManifestError(f"{flag} requires an ISO-8601 UTC timestamp such as 2026-11-25T00:00:00Z")
    return parsed


def _valid_branch_ref(value: str) -> bool:
    if not value.startswith(BRANCH_PREFIX) or value in PROTECTED_BRANCHES:
        return False
    name = value[len(BRANCH_PREFIX):]
    if not name or name.startswith(("-", "/")) or name.endswith(("/", ".")):
        return False
    if any(char in _BAD_BRANCH_CHARS or ord(char) < 0x20 for char in name):
        return False
    if ".." in name or "//" in name or "@{" in name:
        return False
    parts = name.split("/")
    return not any(part in ("", ".") or part.startswith(".") or part.endswith(".lock") for part in parts)


def _is_commit(root: Path, sha: str) -> bool:
    return _git_or_none(root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}") is not None


def _is_ancestor(root: Path, older: str, younger: str) -> bool:
    result = run_git(
        root, "merge-base", "--is-ancestor", older, younger,
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.returncode == 0


def _diff_names(root: Path, older: str, younger: str) -> list[str]:
    """Every path that differs, with a rename reported as its old and new path.

    Without --no-renames a renamed owner-only file would show only its new
    name and slip past the owner-only check. A git failure raises: an unknown
    diff must never read as "nothing changed".
    """

    output = _git(root, "diff", "--name-only", "--no-renames", older, younger)
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def _is_record_only(path: str) -> bool:
    """Paths a review PASS may carry across: project records, not rules or code."""

    if path.startswith("docs/"):
        return True
    return "/" not in path and (path.startswith("README") or path == "CHANGELOG.md") and path.endswith(".md")


def _split_policy_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return [] if items == ["none"] else items


def _policy_at_base(root: Path, base: str) -> tuple[dict[str, str], str | None]:
    """Read the Delivery Autonomy policy exactly as the base commit records it."""

    result = run_git(
        root, "show", "--format=", f"{base}:AGENTS.md",
        capture_output=True, text=False, timeout=30, check=False,
    )
    if result.returncode != 0:
        return {}, POLICY_INELIGIBLE
    try:
        text = bytes(result.stdout).decode("utf-8")
    except UnicodeDecodeError:
        return {}, POLICY_INELIGIBLE
    policy: dict[str, str] = {}
    inside = False
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            if inside:
                break
            inside = stripped == POLICY_HEADING
            continue
        if not inside or not stripped.startswith("- "):
            continue
        key, separator, item = stripped[2:].partition(":")
        if separator:
            policy.setdefault(key.strip(), item.strip())
    if not inside or policy.get("Landing") != "epic_grant":
        return {}, POLICY_INELIGIBLE
    return policy, None


def _pattern_match(pattern: str, path: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return fnmatchcase(path, pattern)


def _owner_only_patterns(policy: dict[str, str]) -> list[str]:
    extra = _split_policy_list(policy.get("Owner-only paths"))
    return list(BUILTIN_OWNER_ONLY) + (extra or [])


def _grant_string(grant: dict[str, Any], key: str) -> str:
    value = grant.get(key)
    return value if isinstance(value, str) else ""


def _load_grant(grant_path: Path, expected_sha256: str) -> tuple[dict[str, Any] | None, str | None]:
    if not _HEX64.fullmatch(expected_sha256):
        raise ManifestError("--grant-sha256 requires 64 lowercase hex characters")
    try:
        raw = grant_path.read_bytes()
    except OSError:
        return None, f"the grant file is missing or unreadable: {grant_path}"
    try:
        grant = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, f"the grant file is not valid JSON and so is not {GRANT_SCHEMA}"
    if not isinstance(grant, dict) or grant.get("schema") != GRANT_SCHEMA:
        return None, f"the grant file is not schema {GRANT_SCHEMA}"
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        return None, "the grant file bytes do not hash to --grant-sha256"
    return grant, None


def _expiry_reason(grant: dict[str, Any], now: datetime) -> str | None:
    expires = _parse_utc(_grant_string(grant, "expires"))
    if expires is None:
        return "the grant records no parsable ISO-8601 UTC expiry"
    if expires <= now:
        return f"the grant expired at {_grant_string(grant, 'expires')}"
    return None


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise ManifestError(f"{path} already exists; never overwrite a recorded grant") from exc


def _record(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve(strict=False)
    reasons: list[str] = []
    if out.is_relative_to(root):
        reasons.append("--out must resolve outside --repo-root; a grant never lives in the checkout")
    if out.exists():
        reasons.append("--out already exists; a recorded grant is never overwritten")
    if args.branch in PROTECTED_BRANCHES:
        reasons.append(f"--branch {args.branch} is protected; grants never cover main or development")
    elif not _valid_branch_ref(args.branch):
        reasons.append(f"--branch {args.branch} is not a full refs/heads/<name> ref")
    if not is_full_sha(args.base):
        reasons.append("--base requires one full 40-character Git SHA")
    elif not _is_commit(root, args.base):
        reasons.append(f"--base {args.base} is not a commit in the repository")
    expires = _parse_utc(args.expires)
    if expires is None:
        reasons.append(f"--expires {args.expires!r} is not an ISO-8601 UTC timestamp")
    elif expires <= datetime.now(timezone.utc):
        reasons.append(f"--expires {args.expires} is not in the future")
    unknown = [action for action in args.action if action not in ALLOWED_ACTIONS]
    if not args.action:
        reasons.append("at least one --action is required")
    if unknown:
        reasons.append(f"unknown actions: {', '.join(unknown)}; allowed: {', '.join(ALLOWED_ACTIONS)}")
    if not args.source.strip():
        reasons.append("--source must quote the owner instruction and its date")
    # _configured_push_url rejects a password or an http(s) user and accepts a
    # passwordless ssh identity such as git@host:owner/repo.git.
    push_url: str | None = None
    try:
        push_url = _configured_push_url(root, args.remote)
    except ManifestError as exc:
        reasons.append(f"the push URL of remote {args.remote!r} cannot be read or carries credentials: {exc}")
    if reasons:
        return {"status": "REFUSED", "reasons": reasons}
    grant = {
        "schema": GRANT_SCHEMA,
        "repository": push_url,
        "remote": args.remote,
        "epic": args.epic,
        "branch": args.branch,
        "target": TARGET_REF,
        "base": args.base,
        "actions": sorted(set(args.action)),
        "expires": _utc_z(expires),
        "repair_budget": args.repair_budget,
        "source": args.source,
        "recorded_at": _utc_z(datetime.now(timezone.utc)),
    }
    _write_json_exclusive(out, grant)
    return {
        "status": "recorded",
        "grant": str(out),
        "grant_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }


def _revoke(args: argparse.Namespace) -> dict[str, Any]:
    grant = Path(args.grant)
    if not grant.is_file():
        return {"status": "REFUSED", "reasons": [f"the grant file does not exist: {grant}"]}
    marker = grant.with_name(grant.name + ".revoked")
    if marker.exists():
        return {"status": "revoked", "marker": str(marker), "already_revoked": True}
    _write_json_exclusive(
        marker,
        {"source": args.source, "revoked_at": _utc_z(datetime.now(timezone.utc))},
    )
    return {"status": "revoked", "marker": str(marker), "already_revoked": False}


def _evidence_reasons(
    root: Path,
    candidate: str,
    evidence_path: str | None,
    policy: dict[str, str],
    action: str,
) -> list[str]:
    reasons: list[str] = []
    evidence: Any = None
    if evidence_path is None:
        return [f"action {action!r} requires --evidence with the parent-observed checks, review and acceptance"]
    try:
        evidence = json.loads(Path(evidence_path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [f"the evidence file is missing or malformed: {evidence_path}"]
    if not isinstance(evidence, dict) or not all(
        isinstance(evidence.get(key), dict) for key in ("checks", "review", "acceptance")
    ):
        return ["the evidence file is malformed: checks, review and acceptance objects are required"]
    checks = evidence["checks"]
    review = evidence["review"]
    acceptance = evidence["acceptance"]
    if checks.get("sha") != candidate:
        reasons.append(f"evidence checks.sha {checks.get('sha')!r} is not the candidate")
    required = _split_policy_list(policy.get("Required checks"))
    if not required:
        reasons.append("an eligible repository names its checks; the policy at the base names none")
    else:
        results = checks.get("results") if isinstance(checks.get("results"), dict) else {}
        absent = [name for name in required if results.get(name) != "pass"]
        if absent:
            reasons.append("required checks absent or not pass: " + ", ".join(absent))
    if review.get("verdict") != "PASS":
        reasons.append(f"evidence review.verdict {review.get('verdict')!r} is not PASS")
    review_sha = review.get("sha")
    if not isinstance(review_sha, str):
        review_sha = ""
    if review_sha == candidate:
        pass
    elif not (
        is_full_sha(review_sha)
        and _is_commit(root, review_sha)
        and _is_ancestor(root, review_sha, candidate)
    ):
        reasons.append(f"evidence review.sha {review.get('sha')!r} is neither the candidate nor an ancestor of it")
    else:
        off_policy = sorted(
            {
                path
                for path in _diff_names(root, review_sha, candidate)
                if not _is_record_only(path)
            }
        )
        if off_policy:
            reasons.append("code changed after the reviewed SHA: " + ", ".join(off_policy))
    status = acceptance.get("status")
    if status == "pass":
        if acceptance.get("sha") != candidate:
            reasons.append(f"evidence acceptance.sha {acceptance.get('sha')!r} is not the candidate")
    elif status != "not_applicable":
        reasons.append(
            f"evidence acceptance.status {status!r} is neither pass nor not_applicable"
        )
    if action == "production_deploy":
        readback = evidence.get("readback")
        if not isinstance(readback, dict):
            reasons.append("production_deploy requires the promotion readback object in the evidence")
        else:
            problems = []
            if readback.get("status") != "PASS":
                problems.append("status is not PASS")
            if readback.get("landing") not in ("exact", "tree_equal_S"):
                problems.append("landing is not exact or tree_equal_S")
            if readback.get("candidate") != candidate:
                problems.append("candidate is not the candidate")
            if problems:
                reasons.append("the promotion readback does not prove the landing: " + "; ".join(problems))
    return reasons


def _check(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    grant_path = Path(args.grant)
    now = _required_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    grant, refusal = _load_grant(grant_path, args.grant_sha256)
    policy_base = _grant_string(grant, "base") if grant is not None else None
    if refusal is not None:
        return _check_result("REFUSED", args, policy_base, [refusal])
    reasons: list[str] = []
    if grant_path.with_name(grant_path.name + ".revoked").exists():
        reasons.append("the grant is revoked")
    expiry = _expiry_reason(grant, now)
    if expiry is not None:
        reasons.append(expiry)
    granted = grant.get("actions") if isinstance(grant.get("actions"), list) else []
    if args.action == "cleanup":
        reasons.append("cleanup is never checked here; use `landing_gate.py cleanup-plan`")
    elif args.action not in granted:
        reasons.append(f"the grant does not cover action {args.action!r}; granted: {', '.join(map(str, granted))}")
    if grant_path.resolve(strict=False).is_relative_to(root):
        reasons.append("the grant file lives inside the repository checkout")
    try:
        configured = _configured_push_url(root, _grant_string(grant, "remote"))
    except ManifestError:
        configured = None
    if configured != grant.get("repository"):
        reasons.append(
            f"the push URL of remote {_grant_string(grant, 'remote')!r} differs from the grant "
            f"repository {grant.get('repository')!r}"
        )
    candidate = args.candidate
    base = policy_base or ""
    if not is_full_sha(candidate):
        reasons.append("--candidate requires one full 40-character Git SHA")
        candidate_ok = False
    elif not _is_commit(root, candidate):
        reasons.append(f"--candidate {candidate} is not a commit in the repository")
        candidate_ok = False
    else:
        candidate_ok = True
    base_ok = is_full_sha(base) and _is_commit(root, base)
    if candidate_ok and not base_ok:
        reasons.append(f"the grant base {base!r} is not a commit in the repository")
    elif candidate_ok and base_ok and not _is_ancestor(root, base, candidate):
        reasons.append(f"the grant base {base} is not an ancestor of the candidate")
    branch_ref = _grant_string(grant, "branch")
    tip = _git_or_none(root, "rev-parse", "--verify", "--quiet", branch_ref) if branch_ref else None
    if tip != candidate:
        reasons.append(
            f"the local tip of {branch_ref} is {tip or 'missing'}; it must be the candidate"
        )
    policy, policy_reason = _policy_at_base(root, base) if base_ok else ({}, POLICY_INELIGIBLE)
    if policy_reason is not None:
        reasons.append(policy_reason)
    if candidate_ok and base_ok:
        changed = _diff_names(root, base, candidate)
        matching = sorted(
            {path for path in changed for pattern in _owner_only_patterns(policy) if _pattern_match(pattern, path)}
        )
        if matching:
            reasons.append("owner-only paths changed: " + ", ".join(matching))
    if args.action in EVIDENCE_ACTIONS:
        reasons.extend(_evidence_reasons(root, candidate, args.evidence, policy, args.action))
    return _check_result("REFUSED" if reasons else "PASS", args, policy_base, reasons)


def _check_result(
    status: str, args: argparse.Namespace, policy_base: str | None, reasons: list[str]
) -> dict[str, Any]:
    return {
        "status": status,
        "action": args.action,
        "candidate": args.candidate,
        "grant_sha256": args.grant_sha256,
        "policy_base": policy_base,
        "reasons": reasons,
    }


def _worktree_entries(root: Path) -> list[dict[str, Any]]:
    output = _git(root, "worktree", "list", "--porcelain")
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if not line.strip():
            if current is not None:
                entries.append(current)
                current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": Path(value), "branch": None}
        elif current is not None and key == "branch":
            current["branch"] = value
    if current is not None:
        entries.append(current)
    return entries


def _worktree_clean(path: Path) -> bool:
    output = _git_or_none(path, "status", "--porcelain")
    return output is not None and output.strip() == ""


def _cleanup_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    grant_path = Path(args.grant)
    if args.remote_tip is not None and not is_full_sha(args.remote_tip):
        raise ManifestError("--remote-tip requires one full 40-character Git SHA")
    now = _required_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    value: dict[str, Any] = {"commands": [], "refused": [], "notes": []}
    grant, refusal = _load_grant(grant_path, args.grant_sha256)
    if refusal is not None:
        return {**value, "status": "REFUSED", "reasons": [refusal]}
    reasons: list[str] = []
    if grant_path.with_name(grant_path.name + ".revoked").exists():
        reasons.append("the grant is revoked")
    expiry = _expiry_reason(grant, now)
    if expiry is not None:
        reasons.append(expiry)
    granted = grant.get("actions") if isinstance(grant.get("actions"), list) else []
    if "cleanup" not in granted:
        reasons.append("the grant does not cover cleanup")
    readback: Any = None
    try:
        readback = json.loads(Path(args.readback).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        reasons.append(f"the readback file is missing or malformed: {args.readback}")
    candidate = readback.get("candidate") if isinstance(readback, dict) else None
    observed_main = readback.get("observed_main") if isinstance(readback, dict) else None
    if not isinstance(readback, dict):
        readback = {}
    if readback.get("status") != "PASS":
        reasons.append("the readback status is not PASS")
    if readback.get("landing") not in ("exact", "tree_equal_S"):
        reasons.append("the readback landing is not exact or tree_equal_S")
    if not is_full_sha(candidate):
        reasons.append("the readback candidate is not a full 40-character SHA")
        candidate = None
    branch_ref = _grant_string(grant, "branch")
    branch_name = branch_ref[len(BRANCH_PREFIX):] if branch_ref.startswith(BRANCH_PREFIX) else ""
    if branch_ref in PROTECTED_BRANCHES:
        reasons.append(f"{branch_ref} is protected; cleanup never removes main or development")
    elif not branch_name:
        reasons.append(f"the grant branch {branch_ref!r} is not a refs/heads/ ref")
    tip = _git_or_none(root, "rev-parse", "--verify", "--quiet", branch_ref) if branch_ref else None
    if candidate is not None and tip != candidate:
        reasons.append(
            f"the local tip of {branch_ref} is {tip or 'missing'}; the branch moved after landing"
        )
    if reasons:
        return {**value, "status": "REFUSED", "reasons": reasons}
    commands: list[list[str]] = []
    refused: list[dict[str, str]] = []
    notes: list[str] = []
    entries = _worktree_entries(root)
    for worktree in entries[1:]:
        if worktree["branch"] != branch_ref:
            continue
        worktree_path = Path(worktree["path"])
        if _worktree_clean(worktree_path):
            commands.append(["git", "worktree", "remove", str(worktree_path)])
        else:
            refused.append(
                {
                    "target": str(worktree_path),
                    "reason": "the worktree is dirty; clean it before planning its removal",
                }
            )
    if entries and entries[0]["branch"] == branch_ref:
        refused.append(
            {
                "target": branch_ref,
                "reason": "switch the primary checkout to another branch first",
            }
        )
    else:
        merged = (
            is_full_sha(observed_main)
            and candidate is not None
            and _is_ancestor(root, candidate, observed_main)
        )
        if merged:
            commands.append(["git", "branch", "-d", branch_name])
        else:
            commands.append(["git", "branch", "-D", branch_name])
            notes.append(
                f"tree equality, not ancestry, proves the landing; {branch_ref} needs git branch -D"
            )
    if args.remote_tip is not None:
        if args.remote_tip == candidate:
            commands.append(["git", "push", _grant_string(grant, "remote"), "--delete", branch_name])
        else:
            refused.append(
                {
                    "target": f"{_grant_string(grant, 'remote')}:{branch_ref}",
                    "reason": (
                        f"the remote tip is {args.remote_tip}; it must be the landed candidate {candidate}"
                    ),
                }
            )
    return {
        "status": "REFUSED" if refused else "PASS",
        "commands": commands,
        "refused": refused,
        "notes": notes,
        "reasons": [],
    }


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--repair-budget requires an integer: {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError(f"--repair-budget requires an integer >= 0: {value}")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record_parser = sub.add_parser("record", help="write the owner's landing grant outside the checkout")
    record_parser.add_argument("--repo-root", required=True, type=Path)
    record_parser.add_argument("--out", required=True, type=Path)
    record_parser.add_argument("--remote", required=True)
    record_parser.add_argument("--epic", required=True)
    record_parser.add_argument("--branch", required=True)
    record_parser.add_argument("--base", required=True)
    record_parser.add_argument("--action", action="append")
    record_parser.add_argument("--expires", required=True)
    record_parser.add_argument("--repair-budget", required=True, type=_non_negative_int)
    record_parser.add_argument("--source", required=True)
    revoke_parser = sub.add_parser("revoke", help="drop a revocation marker beside the grant")
    revoke_parser.add_argument("--grant", required=True, type=Path)
    revoke_parser.add_argument("--source", required=True)
    check_parser = sub.add_parser("check", help="report whether the grant covers one action at the candidate")
    check_parser.add_argument("--repo-root", required=True, type=Path)
    check_parser.add_argument("--grant", required=True, type=Path)
    check_parser.add_argument("--grant-sha256", required=True)
    check_parser.add_argument("--candidate", required=True)
    check_parser.add_argument("--action", required=True)
    check_parser.add_argument("--evidence", default=None)
    check_parser.add_argument("--now", default=None)
    cleanup_parser = sub.add_parser("cleanup-plan", help="print the commands that would clean up the landed branch")
    cleanup_parser.add_argument("--repo-root", required=True, type=Path)
    cleanup_parser.add_argument("--grant", required=True, type=Path)
    cleanup_parser.add_argument("--grant-sha256", required=True)
    cleanup_parser.add_argument("--readback", required=True, type=Path)
    cleanup_parser.add_argument("--remote-tip", default=None)
    cleanup_parser.add_argument("--now", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            value = _record(args)
        elif args.command == "revoke":
            value = _revoke(args)
        elif args.command == "check":
            value = _check(args)
        else:
            value = _cleanup_plan(args)
    except (OSError, ManifestError, ValueError, KeyError, GitMetadataError) as exc:
        print(json.dumps({"authority": AUTHORITY_NOTE, "status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    print(json.dumps({"authority": AUTHORITY_NOTE, **value}, sort_keys=True))
    return 0 if value.get("status") in ("PASS", "recorded", "revoked") else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
