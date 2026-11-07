#!/usr/bin/env python3
"""Read-only main-promotion readback for Promote To Main conditions 4, 7 and 8.

``pre`` reads ``refs/heads/main`` once through the archive-push readback and
proves the recorded main pre-state plus candidate ancestry from the frozen
base. ``post`` reads main again after the separately authorized fetch and
classifies the landing as ``exact``, ``tree_equal_S`` or ``new_candidate``.
The script never fetches, pushes, merges or tags, and its JSON grants no
landing, tag or deployment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness_core import ManifestError, is_full_sha
from harness_git import GitMetadataError, run_git
from push_archived_candidate import _configured_push_url, _remote_state

BRANCH_REF = "refs/heads/main"
AUTHORITY_NOTE = "read-only readback; this result grants no landing, tag or deployment"


def _git(root: Path, *args: str) -> str:
    result = run_git(root, *args, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _sha_argument(value: str, flag: str) -> str:
    if not is_full_sha(value):
        raise ManifestError(f"{flag} requires one full 40-character Git SHA")
    return value


def _local_commit(root: Path, sha: str) -> bool:
    result = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}",
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.returncode == 0


def _tree(root: Path, sha: str) -> str:
    return _git(root, "rev-parse", "--verify", f"{sha}^{{tree}}")


def _is_ancestor(root: Path, older: str, younger: str) -> bool:
    result = run_git(
        root, "merge-base", "--is-ancestor", older, younger,
        capture_output=True, text=True, timeout=30, check=False,
    )
    return result.returncode == 0


def _observed_main(root: Path, remote: str) -> str | None:
    return _remote_state(_configured_push_url(root, remote), BRANCH_REF)


def _classify_landing(
    candidate: str, observed_main: str | None, candidate_tree: str, main_tree: str | None
) -> str:
    if observed_main is None or main_tree is None:
        return "unknown"
    if observed_main == candidate:
        return "exact"
    if candidate_tree == main_tree:
        return "tree_equal_S"
    return "new_candidate"


def _read_main_and_trees(
    root: Path, remote: str, candidate: str
) -> tuple[str | None, str, str | None]:
    candidate_tree = _tree(root, candidate)
    observed_main = _observed_main(root, remote)
    main_tree = _tree(root, observed_main) if observed_main and _local_commit(root, observed_main) else None
    return observed_main, candidate_tree, main_tree


def _result(
    command: str,
    args: argparse.Namespace,
    observed_main: str | None,
    candidate_tree: str,
    main_tree: str | None,
    ancestry: dict[str, bool],
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "authority": AUTHORITY_NOTE,
        "base": args.base,
        "branch_ref": BRANCH_REF,
        "candidate": args.candidate,
        "candidate_tree": candidate_tree,
        "command": command,
        "expected_main": args.main_before,
        "landing": _classify_landing(args.candidate, observed_main, candidate_tree, main_tree),
        "main_tree": main_tree,
        "observed_main": observed_main,
        "reasons": reasons,
        "remote": args.remote,
        "status": "BLOCKED" if reasons else "PASS",
        **ancestry,
    }


def _pre(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    candidate = _sha_argument(args.candidate, "--candidate")
    base = _sha_argument(args.base, "--base")
    main_before = _sha_argument(args.main_before, "--main-before")
    for flag, sha in (("--candidate", candidate), ("--base", base), ("--main-before", main_before)):
        if not _local_commit(root, sha):
            raise ManifestError(f"{flag} {sha} does not resolve to a local commit")
    observed_main, candidate_tree, main_tree = _read_main_and_trees(root, args.remote, candidate)
    base_ancestor_of_candidate = _is_ancestor(root, base, candidate)
    main_before_ancestor_of_candidate = _is_ancestor(root, main_before, candidate)
    reasons: list[str] = []
    if observed_main is None:
        reasons.append(f"remote {BRANCH_REF} is missing")
    elif observed_main != main_before:
        reasons.append(f"remote {BRANCH_REF} does not equal the recorded main pre-state")
    if not base_ancestor_of_candidate:
        reasons.append("--base is not an ancestor of --candidate")
    if not main_before_ancestor_of_candidate:
        reasons.append("--main-before is not an ancestor of --candidate")
    return _result(
        "pre",
        args,
        observed_main,
        candidate_tree,
        main_tree,
        {
            "base_ancestor_of_candidate": base_ancestor_of_candidate,
            "main_before_ancestor_of_candidate": main_before_ancestor_of_candidate,
            "main_matches_pre_state": observed_main == main_before,
        },
        reasons,
    )


def _post(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    candidate = _sha_argument(args.candidate, "--candidate")
    _sha_argument(args.base, "--base")
    main_before = _sha_argument(args.main_before, "--main-before")
    for flag, sha in (("--candidate", candidate), ("--main-before", main_before)):
        if not _local_commit(root, sha):
            raise ManifestError(f"{flag} {sha} does not resolve to a local commit")
    observed_main, candidate_tree, main_tree = _read_main_and_trees(root, args.remote, candidate)
    main_before_ancestor_of_new_main = False
    new_main_exists_locally = False
    reasons: list[str] = []
    if observed_main is None:
        reasons.append(f"remote {BRANCH_REF} is missing")
    else:
        new_main_exists_locally = _local_commit(root, observed_main)
        if not new_main_exists_locally:
            reasons.append("the observed main SHA is absent locally; run the separately authorized fetch first")
        else:
            main_before_ancestor_of_new_main = _is_ancestor(root, main_before, observed_main)
            if not main_before_ancestor_of_new_main:
                reasons.append("--main-before is not an ancestor of the observed main")
    if _classify_landing(candidate, observed_main, candidate_tree, main_tree) == "new_candidate":
        reasons.append("the observed main tree differs from the candidate tree; it is a new candidate")
    return _result(
        "post",
        args,
        observed_main,
        candidate_tree,
        main_tree,
        {
            "main_before_ancestor_of_new_main": main_before_ancestor_of_new_main,
            "new_main_exists_locally": new_main_exists_locally,
        },
        reasons,
    )


def _write_out(root: Path, out: Path, value: dict[str, Any]) -> None:
    resolved = out.resolve(strict=False)
    if resolved.is_relative_to(root):
        raise ManifestError("--out must live outside the reviewed checkout")
    if resolved.exists():
        raise ManifestError("--out already exists; record this readback at a new path")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write("\n")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--remote", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--main-before", required=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pre_parser = sub.add_parser("pre", help="prove the main pre-state and candidate ancestry (condition 4)")
    _add_common_arguments(pre_parser)
    post_parser = sub.add_parser("post", help="prove the landed main ancestry and tree equality (conditions 7 and 8)")
    _add_common_arguments(post_parser)
    post_parser.add_argument("--out", type=Path, default=None, help="write the same JSON outside the checkout")
    args = parser.parse_args(argv)
    try:
        value = _pre(args) if args.command == "pre" else _post(args)
        if args.command == "post" and args.out is not None:
            _write_out(Path(args.repo_root).resolve(), args.out, value)
    except (OSError, ManifestError, ValueError, KeyError, GitMetadataError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
