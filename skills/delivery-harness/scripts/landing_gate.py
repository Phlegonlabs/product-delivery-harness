#!/usr/bin/env python3
"""Epic landing gate: bind a recorded owner grant to one exact candidate.

``record`` writes the owner's pre-recorded landing grant outside the checkout.
``revoke`` drops a revocation marker beside it. ``check`` reports offline
whether the grant covers one action at one exact candidate commit, reading the
repository policy from ``.harness/landing-policy.json`` at the grant's frozen
base commit. ``cleanup-plan`` prints the commands that would remove the landed
branch and its worktrees.

The policy is strict JSON, not a section of AGENTS.md: a Markdown file has
many spellings that render alike, and four reviews each found one more that a
line reader took for policy. JSON with a fixed field set has one spelling.

The script is fail-closed. The grant file, the evidence file and the read-back
are parent-written and live outside the checkout; the candidate's commits, the
working tree and local refs are untrusted. Anything the script cannot read or
decide is a refusal or an error, never a PASS. It never contacts the network
and never pushes, merges, deletes or writes inside the checkout; every result
only reports.

It does not run the review, the required checks, the journey command, Preview
or the production smoke. The parent performs those and reports what it
observed in the evidence file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
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
# Handling a review thread may add a repair round, so it reports the count.
# A reviewed candidate may be published; a landing also needs checks and acceptance.
BUDGET_EVIDENCE_ACTIONS = ("review_threads",)
REVIEW_EVIDENCE_ACTIONS = ("push", "pull_request")
FULL_EVIDENCE_ACTIONS = ("merge", "production_deploy")
PROTECTED_BRANCHES = ("refs/heads/main", "refs/heads/development")
BRANCH_PREFIX = "refs/heads/"
TARGET_REF = "refs/heads/main"
# Instruction files at any depth, and CI configuration at its standard paths.
OWNER_ONLY_BASENAMES = ("agents.md", "agents.override.md", "claude.md")
BUILTIN_OWNER_ONLY = (
    ".harness/",
    ".github/",
    ".gitlab-ci.yml",
    ".gitlab/",
    ".circleci/",
    ".buildkite/",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "Jenkinsfile",
)
POLICY_PATH = ".harness/landing-policy.json"
# The only ignored content a cleanup may delete with a worktree: caches a tool
# rebuilds on its next run. Every other ignored file may be local data.
REGENERABLE_DIRECTORIES = frozenset(
    ("node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
)
POLICY_SCHEMA = "landing-policy/1"
POLICY_TEXT_FIELDS = ("journey_command", "production_smoke_command", "recovery")
POLICY_LIST_FIELDS = ("required_checks", "owner_only_paths")
POLICY_FIELDS = frozenset(("schema", "landing", *POLICY_TEXT_FIELDS, *POLICY_LIST_FIELDS))
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_BAD_BRANCH_CHARS = set(" ~^:?*[\\\x7f")


def _now() -> datetime:
    """The clock. Tests replace this function; the CLI offers no override."""

    return datetime.now(timezone.utc)


def _git(root: Path, *args: str) -> str:
    result = run_git(root, *args, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _is_commit(root: Path, sha: str) -> bool:
    result = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}",
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.returncode == 0


def _ref_tip(root: Path, ref: str) -> str | None:
    result = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}",
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _is_ancestor(root: Path, older: str, younger: str) -> bool:
    """True or False from git; any other git exit is an error, not "no"."""

    result = run_git(
        root, "merge-base", "--is-ancestor", older, younger,
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ManifestError(result.stderr.strip() or f"git merge-base --is-ancestor {older} {younger} failed")


def _diff_names(root: Path, older: str, younger: str) -> list[str]:
    """Every path that differs between two commits.

    -z keeps names unquoted, so a non-ASCII path is compared as it is.
    --no-renames reports a rename as its old and its new path, so a moved
    owner-only file still shows where it left. A git failure raises.

    Git separates directories with "/" on every platform. A backslash in its
    output is part of a file name, so names are used exactly as git prints them.
    """

    output = _git(root, "diff", "--name-only", "--no-renames", "-z", older, younger)
    return [name for name in output.split("\0") if name]


def _utc_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        return None
    return parsed


def _is_protected(ref: str) -> bool:
    # Windows and macOS resolve refs/heads/Main to the same ref as main.
    return ref.casefold() in PROTECTED_BRANCHES


def _valid_branch_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith(BRANCH_PREFIX) or _is_protected(value):
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


def _owner_only_match(pattern: str, path: str) -> bool:
    """Case-insensitive, because the same file has two spellings on Windows."""

    folded_path = path.casefold()
    folded_pattern = pattern.casefold()
    if folded_pattern.endswith("/"):
        # The directory entry itself changes when it becomes a submodule or symlink.
        return folded_path == folded_pattern[:-1] or folded_path.startswith(folded_pattern)
    return fnmatchcase(folded_path, folded_pattern)


def _owner_only_paths(changed: list[str], policy: dict[str, Any]) -> list[str]:
    patterns = [*BUILTIN_OWNER_ONLY, *policy.get("owner_only_paths", [])]
    matching = set()
    for path in changed:
        if path.casefold().rsplit("/", 1)[-1] in OWNER_ONLY_BASENAMES:
            matching.add(path)
        elif any(_owner_only_match(pattern, path) for pattern in patterns):
            matching.add(path)
    return sorted(matching)


def _tree(root: Path, sha: str) -> str:
    return _git(root, "rev-parse", "--verify", f"{sha}^{{tree}}").strip()


def _parents(root: Path, sha: str) -> list[str]:
    return _git(root, "rev-list", "--parents", "-n", "1", sha).split()[1:]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _value in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("a key repeats")
    return dict(pairs)


def _no_constant(name: str) -> Any:
    raise ValueError(f"{name} is not JSON")


def _text_ok(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip() and "<fill>" not in value


def _read_policy(raw: bytes) -> tuple[dict[str, Any], str | None]:
    """The landing policy in the bytes of the policy file, or why it is not eligible.

    One spelling is accepted: a UTF-8 JSON object with exactly the fields in
    POLICY_FIELDS, no key repeated, every text a non-empty string and every
    list a list of distinct non-empty strings. Anything else is a refusal.
    """

    prefix = f"the repository is not eligible: {POLICY_PATH} at the grant base "
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_no_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {}, prefix + "is not strict UTF-8 JSON with unique keys"
    if not isinstance(value, dict) or set(value) != POLICY_FIELDS:
        return {}, prefix + "must be one object with exactly these fields: " + ", ".join(sorted(POLICY_FIELDS))
    if value["schema"] != POLICY_SCHEMA:
        return {}, prefix + f"is not schema {POLICY_SCHEMA}"
    for field in POLICY_TEXT_FIELDS:
        if not _text_ok(value[field]):
            return {}, prefix + f"leaves `{field}` unset; it must be a non-empty string"
    for field in POLICY_LIST_FIELDS:
        items = value[field]
        if not isinstance(items, list) or not all(_text_ok(item) for item in items) or len(set(items)) != len(items):
            return {}, prefix + f"must give `{field}` as a list of distinct non-empty strings"
    if not value["required_checks"]:
        return {}, prefix + "names no required check; an eligible repository names its checks"
    if value["landing"] != "epic_grant":
        return {}, prefix + 'does not say "landing": "epic_grant"'
    return value, None


def _policy_at_base(root: Path, base: str) -> tuple[dict[str, Any], str | None]:
    """The policy exactly as the base commit records it, never the candidate's."""

    result = run_git(
        root, "show", "--format=", f"{base}:{POLICY_PATH}",
        capture_output=True, text=False, timeout=30, check=False,
    )
    if result.returncode != 0:
        return {}, f"the repository is not eligible: {POLICY_PATH} does not exist at the grant base"
    return _read_policy(bytes(result.stdout))


def _grant_fields_reason(grant: Any) -> str | None:
    if not isinstance(grant, dict) or grant.get("schema") != GRANT_SCHEMA:
        return f"the grant file is not schema {GRANT_SCHEMA}"
    for key in ("repository", "remote", "epic", "source"):
        if not isinstance(grant.get(key), str) or not grant[key].strip():
            return f"the grant file has no usable `{key}`"
    if not _valid_branch_ref(grant.get("branch")):
        return "the grant file names no valid unprotected refs/heads/ branch"
    if grant.get("target") != TARGET_REF:
        return f"the grant file target is not {TARGET_REF}"
    if not is_full_sha(grant.get("base")):
        return "the grant file base is not a full 40-character SHA"
    actions = grant.get("actions")
    if not isinstance(actions, list) or not actions or any(action not in ALLOWED_ACTIONS for action in actions):
        return "the grant file actions are missing or unknown"
    if _parse_utc(grant.get("expires")) is None:
        return "the grant file has no parsable ISO-8601 UTC expiry"
    budget = grant.get("repair_budget")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        return "the grant file repair_budget is not an integer >= 0"
    return None


def _load_grant(grant_path: Path, expected_sha256: str) -> tuple[dict[str, Any] | None, Path, str | None]:
    """The grant, its canonical path, and the single reason it cannot be used."""

    if not _HEX64.fullmatch(expected_sha256):
        raise ManifestError("--grant-sha256 requires 64 lowercase hex characters")
    canonical = grant_path.resolve(strict=False)
    try:
        raw = canonical.read_bytes()
    except OSError:
        return None, canonical, f"the grant file is missing or unreadable: {grant_path}"
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        return None, canonical, "the grant file bytes do not hash to --grant-sha256"
    try:
        grant = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, canonical, f"the grant file is not valid JSON and so is not {GRANT_SCHEMA}"
    reason = _grant_fields_reason(grant)
    return (None, canonical, reason) if reason else (grant, canonical, None)


def _binding_reasons(root: Path, grant: dict[str, Any], canonical: Path) -> tuple[list[str], dict[str, Any]]:
    """What must hold for any use of the grant, and the base policy when eligible."""

    reasons: list[str] = []
    # The marker sits beside the real file, whatever alias the caller used.
    if canonical.with_name(canonical.name + ".revoked").exists():
        reasons.append("the grant is revoked")
    expires = _parse_utc(grant["expires"])
    if expires is None or expires <= _now():
        reasons.append(f"the grant expired at {grant['expires']}")
    if canonical.is_relative_to(root):
        reasons.append("the grant file lives inside the repository checkout")
    try:
        configured: str | None = _configured_push_url(root, grant["remote"])
    except ManifestError as exc:
        configured = None
        reasons.append(f"the push URL of remote {grant['remote']!r} cannot be read: {exc}")
    if configured is not None and configured != grant["repository"]:
        reasons.append(
            f"the push URL of remote {grant['remote']!r} differs from the grant repository {grant['repository']!r}"
        )
    policy: dict[str, Any] = {}
    if not _is_commit(root, grant["base"]):
        reasons.append(f"the grant base {grant['base']} is not a commit in the repository")
    else:
        policy, policy_reason = _policy_at_base(root, grant["base"])
        if policy_reason is not None:
            reasons.append(policy_reason)
    return reasons, policy


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
    actions = list(args.action or [])
    reasons: list[str] = []
    if out.is_relative_to(root):
        reasons.append("--out must resolve outside --repo-root; a grant never lives in the checkout")
    if out.exists():
        reasons.append("--out already exists; a recorded grant is never overwritten")
    if isinstance(args.branch, str) and _is_protected(args.branch):
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
    elif expires <= _now():
        reasons.append(f"--expires {args.expires} is not in the future")
    unknown = [action for action in actions if action not in ALLOWED_ACTIONS]
    if not actions:
        reasons.append("at least one --action is required")
    if unknown:
        reasons.append(f"unknown actions: {', '.join(unknown)}; allowed: {', '.join(ALLOWED_ACTIONS)}")
    for flag, value in (("--epic", args.epic), ("--source", args.source)):
        if not value.strip():
            reasons.append(f"{flag} must not be empty")
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
        "actions": sorted(set(actions)),
        "expires": _utc_z(expires),
        "repair_budget": args.repair_budget,
        "source": args.source,
        "recorded_at": _utc_z(_now()),
    }
    _write_json_exclusive(out, grant)
    return {
        "status": "recorded",
        "grant": str(out),
        "grant_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }


def _revoke(args: argparse.Namespace) -> dict[str, Any]:
    grant = Path(args.grant).resolve(strict=False)
    if not grant.is_file():
        return {"status": "REFUSED", "reasons": [f"the grant file does not exist: {args.grant}"]}
    marker = grant.with_name(grant.name + ".revoked")
    if marker.exists():
        return {"status": "revoked", "marker": str(marker), "already_revoked": True}
    _write_json_exclusive(marker, {"source": args.source, "revoked_at": _utc_z(_now())})
    return {"status": "revoked", "marker": str(marker), "already_revoked": False}


def _load_json_object(root: Path, path: str | None, label: str) -> tuple[dict[str, Any] | None, str | None]:
    """A parent-written input. A file inside the checkout is the candidate's, not the parent's."""

    if path is None:
        return None, f"this action requires the parent-observed {label} file"
    canonical = Path(path).resolve(strict=False)
    if canonical.is_relative_to(root):
        return None, f"the {label} file lives inside the repository checkout: {path}"
    try:
        value = json.loads(canonical.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, f"the {label} file is missing or malformed: {path}"
    if not isinstance(value, dict):
        return None, f"the {label} file is not a JSON object: {path}"
    return value, None


def _readback_reasons(root: Path, readback: Any, candidate: str | None) -> list[str]:
    """A read-back proves a landing only when every field it rests on is present."""

    if not isinstance(readback, dict):
        return ["the promotion read-back object is missing"]
    problems: list[str] = []
    if readback.get("status") != "PASS":
        problems.append("status is not PASS")
    if readback.get("landing") not in ("exact", "tree_equal_S"):
        problems.append("landing is not exact or tree_equal_S")
    if not is_full_sha(readback.get("candidate")):
        problems.append("candidate is not a full 40-character SHA")
    elif candidate is not None and readback["candidate"] != candidate:
        problems.append("candidate is not this candidate")
    observed = readback.get("observed_main")
    if not is_full_sha(observed):
        problems.append("observed_main is not a full 40-character SHA")
    elif not _is_commit(root, observed):
        problems.append("observed_main is not a commit in this repository")
    elif not problems:
        # Recompute what promotion_readback.py would say; the label alone proves nothing.
        landed = readback["candidate"]
        if not _is_commit(root, landed):
            problems.append("candidate is not a commit in this repository")
        else:
            actual = (
                "exact" if observed == landed
                else "tree_equal_S" if _tree(root, observed) == _tree(root, landed)
                else "new_candidate"
            )
            if actual != readback["landing"]:
                problems.append(f"it says `{readback['landing']}` but the commits are `{actual}`")
    return ["the promotion read-back does not prove the landing: " + "; ".join(problems)] if problems else []


def _review_reasons(root: Path, evidence: dict[str, Any], candidate: str) -> list[str]:
    """The review must bind the candidate itself.

    One inheritance exists: for a managed RUN the candidate is archive-only
    child A of closeout candidate C. The review of C stands for A when A's only
    parent is C and the parent reports the receipt-bound C-to-A verification
    of push_archived_candidate.py as passed.
    """

    review = evidence.get("review")
    if not isinstance(review, dict):
        return ["the evidence has no review object"]
    reasons: list[str] = []
    if review.get("verdict") != "PASS":
        reasons.append(f"evidence review.verdict {review.get('verdict')!r} is not PASS")
    review_sha = review.get("sha")
    if review_sha == candidate:
        return reasons
    archive = evidence.get("archive")
    inherited = (
        isinstance(archive, dict)
        and archive.get("verification") == "PASS"
        and is_full_sha(review_sha)
        and archive.get("closeout") == review_sha
        and _parents(root, candidate) == [review_sha]
    )
    if not inherited:
        reasons.append(
            f"evidence review.sha {review_sha!r} is not the candidate; a review binds one exact SHA, "
            "and only a verified archive child inherits its parent's review"
        )
    return reasons


def _evidence_reasons(
    root: Path, candidate: str, evidence_path: str | None, grant: dict[str, Any],
    policy: dict[str, Any], action: str,
) -> list[str]:
    evidence, problem = _load_json_object(root, evidence_path, "evidence")
    if evidence is None:
        return [str(problem)]
    reasons = [] if action in BUDGET_EVIDENCE_ACTIONS else _review_reasons(root, evidence, candidate)
    rounds = evidence.get("repair_rounds")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
        reasons.append("evidence repair_rounds must be an integer >= 0")
    elif rounds > grant["repair_budget"]:
        reasons.append(f"repair rounds {rounds} exceed the grant's repair budget {grant['repair_budget']}")
    if action not in FULL_EVIDENCE_ACTIONS:
        return reasons
    checks = evidence.get("checks")
    if not isinstance(checks, dict):
        reasons.append("the evidence has no checks object")
    else:
        if checks.get("sha") != candidate:
            reasons.append(f"evidence checks.sha {checks.get('sha')!r} is not the candidate")
        results = checks.get("results") if isinstance(checks.get("results"), dict) else {}
        absent = [name for name in policy.get("required_checks", []) if results.get(name) != "pass"]
        if absent or not policy:
            reasons.append("required checks absent or not pass: " + (", ".join(absent) or "policy unavailable"))
    acceptance = evidence.get("acceptance")
    status = acceptance.get("status") if isinstance(acceptance, dict) else None
    if status == "pass":
        if acceptance.get("sha") != candidate:
            reasons.append(f"evidence acceptance.sha {acceptance.get('sha')!r} is not the candidate")
    elif status != "not_applicable":
        reasons.append(f"evidence acceptance.status {status!r} is neither pass nor not_applicable")
    if action == "production_deploy":
        reasons.extend(_readback_reasons(root, evidence.get("readback"), candidate))
    return reasons


def _check(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    result = {
        "action": args.action,
        "candidate": args.candidate,
        "grant_sha256": args.grant_sha256,
        "policy_base": None,
    }
    grant, canonical, refusal = _load_grant(Path(args.grant), args.grant_sha256)
    if grant is None:
        return {**result, "status": "REFUSED", "reasons": [refusal]}
    result["policy_base"] = grant["base"]
    reasons, policy = _binding_reasons(root, grant, canonical)
    if args.action == "cleanup":
        reasons.append("cleanup is never checked here; use `landing_gate.py cleanup-plan`")
    elif args.action not in grant["actions"]:
        reasons.append(f"the grant does not cover action {args.action!r}; granted: {', '.join(grant['actions'])}")
    candidate = args.candidate
    candidate_ok = is_full_sha(candidate) and _is_commit(root, candidate)
    base_ok = _is_commit(root, grant["base"])
    if not is_full_sha(candidate):
        reasons.append("--candidate requires one full 40-character Git SHA")
    elif not candidate_ok:
        reasons.append(f"--candidate {candidate} is not a commit in the repository")
    elif base_ok and not _is_ancestor(root, grant["base"], candidate):
        reasons.append(f"the grant base {grant['base']} is not an ancestor of the candidate")
    tip = _ref_tip(root, grant["branch"])
    if tip != candidate:
        reasons.append(f"the local tip of {grant['branch']} is {tip or 'missing'}; it must be the candidate")
    if candidate_ok and base_ok:
        matching = _owner_only_paths(_diff_names(root, grant["base"], candidate), policy)
        if matching:
            reasons.append("owner-only paths changed: " + ", ".join(matching))
        if args.action in BUDGET_EVIDENCE_ACTIONS + REVIEW_EVIDENCE_ACTIONS + FULL_EVIDENCE_ACTIONS:
            reasons.extend(_evidence_reasons(root, candidate, args.evidence, grant, policy, args.action))
    return {**result, "status": "REFUSED" if reasons else "PASS", "reasons": reasons}


def _worktree_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in _git(root, "worktree", "list", "--porcelain").splitlines():
        if not line.strip():
            current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": Path(value), "branch": None}
            entries.append(current)
        elif current is not None and key == "branch":
            current["branch"] = value
    if not entries:
        raise ManifestError("git worktree list returned no worktree; refusing to plan a cleanup")
    return entries


def _worktree_residue(path: Path) -> str | None:
    """Why removing this worktree would lose something, or None when it would not.

    `git worktree remove` refuses modified and untracked files but deletes
    ignored ones without a word, and ignored files are where local data lives:
    environment files, local databases, credentials. So ignored files count,
    except under a directory a tool rebuilds.
    """

    entries = [
        entry for entry in _git(path, "status", "--porcelain", "--ignored", "--untracked-files=all", "-z").split("\0")
        if entry
    ]
    if any(not entry.startswith("!! ") for entry in entries):
        return "the worktree has uncommitted or untracked changes; nothing is removed"
    kept = sorted(
        ignored for ignored in (entry[3:] for entry in entries)
        if not REGENERABLE_DIRECTORIES.intersection(ignored.rstrip("/").split("/"))
    )
    if kept:
        shown = ", ".join(kept[:5]) + (f" and {len(kept) - 5} more" if len(kept) > 5 else "")
        return f"the worktree holds ignored local files that removal would delete: {shown}; nothing is removed"
    return None


def _cleanup_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    if args.remote_tip is not None and not is_full_sha(args.remote_tip):
        raise ManifestError("--remote-tip requires one full 40-character Git SHA")
    empty: dict[str, Any] = {"commands": [], "refused": [], "notes": []}
    grant, canonical, refusal = _load_grant(Path(args.grant), args.grant_sha256)
    if grant is None:
        return {**empty, "status": "REFUSED", "reasons": [refusal]}
    reasons, _policy = _binding_reasons(root, grant, canonical)
    if "cleanup" not in grant["actions"]:
        reasons.append("the grant does not cover cleanup")
    readback, problem = _load_json_object(root, str(args.readback), "read-back")
    if readback is None:
        reasons.append(str(problem))
    else:
        reasons.extend(_readback_reasons(root, readback, None))
    if reasons:
        return {**empty, "status": "REFUSED", "reasons": reasons}
    candidate = readback["candidate"]
    branch_ref = grant["branch"]
    branch_name = branch_ref[len(BRANCH_PREFIX):]
    tip = _ref_tip(root, branch_ref)
    if tip != candidate:
        reasons.append(f"the local tip of {branch_ref} is {tip or 'missing'}; the branch moved after landing")
    merged = _is_ancestor(root, candidate, readback["observed_main"])
    if not merged and readback["landing"] != "tree_equal_S":
        reasons.append("the read-back says `exact`, but the candidate is not an ancestor of the observed main")
    if reasons:
        return {**empty, "status": "REFUSED", "reasons": reasons}
    commands: list[list[str]] = []
    refused: list[dict[str, str]] = []
    notes: list[str] = []
    entries = _worktree_entries(root)
    # Exact match: a ref that differs only in case can be another branch.
    same_branch = [entry for entry in entries if entry["branch"] == branch_ref]
    for entry in same_branch:
        if entry is entries[0]:
            refused.append({"target": branch_ref, "reason": "switch the primary checkout to another branch first"})
        else:
            residue = _worktree_residue(entry["path"])
            if residue is None:
                commands.append(["git", "worktree", "remove", str(entry["path"])])
            else:
                refused.append({"target": str(entry["path"]), "reason": residue})
    if merged:
        commands.append(["git", "branch", "-d", branch_name])
    else:
        commands.append(["git", "branch", "-D", branch_name])
        notes.append(f"tree equality, not ancestry, proves the landing; {branch_ref} needs git branch -D")
    if args.remote_tip is not None:
        if args.remote_tip == candidate:
            commands.append(["git", "push", grant["remote"], "--delete", branch_name])
        else:
            refused.append({
                "target": f"{grant['remote']}:{branch_ref}",
                "reason": f"the remote tip is {args.remote_tip}; it must be the landed candidate {candidate}",
            })
    if refused:
        # All or nothing: a partial plan would leave the parent to guess.
        return {"status": "REFUSED", "commands": [], "refused": refused, "notes": [], "reasons": []}
    return {"status": "PASS", "commands": commands, "refused": [], "notes": notes, "reasons": []}


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
    record_parser.add_argument("--action", action="append", default=[])
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
    cleanup_parser = sub.add_parser("cleanup-plan", help="print the commands that would clean up the landed branch")
    cleanup_parser.add_argument("--repo-root", required=True, type=Path)
    cleanup_parser.add_argument("--grant", required=True, type=Path)
    cleanup_parser.add_argument("--grant-sha256", required=True)
    cleanup_parser.add_argument("--readback", required=True, type=Path)
    cleanup_parser.add_argument("--remote-tip", default=None)
    args = parser.parse_args(argv)
    handlers = {"record": _record, "revoke": _revoke, "check": _check, "cleanup-plan": _cleanup_plan}
    try:
        value = handlers[args.command](args)
    except (OSError, ManifestError, ValueError, KeyError, TypeError, GitMetadataError, subprocess.SubprocessError) as exc:
        print(json.dumps({"authority": AUTHORITY_NOTE, "status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    print(json.dumps({"authority": AUTHORITY_NOTE, **value}, sort_keys=True))
    return 0 if value.get("status") in ("PASS", "recorded", "revoked") else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
