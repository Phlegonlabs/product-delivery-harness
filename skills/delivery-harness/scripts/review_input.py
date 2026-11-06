#!/usr/bin/env python3
"""Build a git-free review packet for a reviewer whose sandbox cannot run git.

Clones --repo to <out>/clone, checks out --head detached, and writes
<out>/clone/review-input/: HEAD.txt, BASE.txt, candidate.diff, commit-log.txt,
changed-files.txt, parent-status.txt, one scope-<name>.diff per --scope, and
tracked-files.sha256 (SHA-256 of every clone file except .git/ and review-input/).
The reviewer proves candidate identity and a clean checkout from that manifest,
parent-status.txt and HEAD.txt instead of running git.

--scope name=pathspec[,pathspec...] limits one diff to those git pathspecs.
Exit 0 on success, 2 on any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from harness_git import GitMetadataError, run_git

SCOPE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
DIFF_FLAGS = ("--no-color", "--no-ext-diff", "--no-textconv")


class ReviewInputError(Exception):
    pass


def git(repo: Path, *args: str) -> bytes:
    result = run_git(repo, *args, text=False, timeout=600)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewInputError(f"git {args[0]} failed: {detail}")
    return result.stdout


def rev_sha(repo: Path, *args: str) -> str:
    return git(repo, "rev-parse", *args).decode("ascii").strip()


def manifest(clone: Path) -> list[tuple[str, str]]:
    """(relative posix path, sha256) for every clone file except .git and review-input."""

    entries: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(clone):
        if Path(root) == clone:
            dirs[:] = [name for name in dirs if name not in (".git", "review-input")]
        linked_dirs = [name for name in dirs if os.path.islink(os.path.join(root, name))]
        for name in files + linked_dirs:
            path = Path(root, name)
            rel = path.relative_to(clone).as_posix()
            if "\n" in rel or "\r" in rel:
                raise ReviewInputError(f"line break in file name {rel!r}")
            data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            entries.append((rel, hashlib.sha256(data).hexdigest()))
    return sorted(entries)


def build(repo: Path, base: str, head: str, out: Path, scopes: list[tuple[str, list[str]]]) -> dict:
    repo, out = repo.resolve(), out.resolve()
    if out.exists():
        raise ReviewInputError(f"refusing existing --out {out}")
    if len({name for name, _ in scopes}) != len(scopes):
        raise ReviewInputError("duplicate --scope name")
    base, head = (rev_sha(repo, "--verify", "--end-of-options", f"{rev}^{{commit}}") for rev in (base, head))
    repo_head = rev_sha(repo, "HEAD")
    if repo_head != head:
        raise ReviewInputError(f"--repo HEAD is {repo_head}, not --head {head}; build from the candidate checkout")
    status = git(repo, "status", "--porcelain", "--untracked-files=no")

    out.mkdir(parents=True)
    clone = out / "clone"
    git(repo, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(repo), str(clone))
    git(clone, "checkout", "--quiet", "--detach", head)
    if rev_sha(clone, "HEAD") != head:
        raise ReviewInputError("clone HEAD does not equal --head")

    packet = clone / "review-input"
    packet.mkdir()

    def put(name: str, data: bytes | str) -> None:
        (packet / name).write_bytes(data.encode("utf-8") if isinstance(data, str) else data)

    def diff(*paths: str) -> bytes:
        return git(repo, "diff", *DIFF_FLAGS, base, head, *(("--", *paths) if paths else ()))

    candidate = diff()
    put("HEAD.txt", head + "\n")
    put("BASE.txt", base + "\n")
    put("candidate.diff", candidate)
    put("commit-log.txt", git(repo, "log", "--format=%H %s", f"{base}..{head}"))
    put("changed-files.txt", git(repo, "diff", "--name-status", base, head))
    state = "dirty" if status.strip() else "clean"
    put("parent-status.txt", f"repo: {repo.as_posix()}\nhead: {repo_head}\nstatus: {state}\n".encode() + status)
    scope_lines = {}
    for name, paths in scopes:
        data = diff(*paths)
        put(f"scope-{name}.diff", data)
        scope_lines[name] = data.count(b"\n")
    files = manifest(clone)
    put("tracked-files.sha256", "".join(f"{digest}  {rel}\n" for rel, digest in files))
    return {
        "clone": clone.as_posix(),
        "head": head,
        "files": len(files),
        "candidate_diff_lines": candidate.count(b"\n"),
        "scope_diff_lines": scope_lines,
    }


def scope_arg(value: str) -> tuple[str, list[str]]:
    name, separator, spec = value.partition("=")
    paths = [item.strip() for item in spec.split(",") if item.strip()]
    if not separator or not SCOPE_NAME.fullmatch(name) or not paths:
        raise argparse.ArgumentTypeError(f"expected name=pathspec[,pathspec...] with a plain name: {value!r}")
    return name, paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, required=True, help="candidate checkout, HEAD at --head")
    parser.add_argument("--base", required=True, help="base revision of the reviewed range")
    parser.add_argument("--head", required=True, help="candidate revision")
    parser.add_argument("--out", type=Path, required=True, help="new directory; must not exist")
    parser.add_argument("--scope", type=scope_arg, action="append", default=[], metavar="NAME=PATHSPEC[,...]")
    args = parser.parse_args(argv)
    try:
        summary = build(args.repo, args.base, args.head, args.out, args.scope)
    except (ReviewInputError, GitMetadataError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
