#!/usr/bin/env python3
"""Build a git-free review packet for a reviewer whose sandbox cannot run git.

Clones --repo to <out>/clone, checks out --head detached, and writes
<out>/clone/review-input/: HEAD.txt, BASE.txt, candidate.diff, commit-log.txt,
changed-files.txt, parent-status.txt, one scope-<name>.diff per --scope, and
tracked-files.sha256 (SHA-256 of every clone file except .git/ and review-input/).
The reviewer proves candidate identity and a clean checkout from that manifest,
parent-status.txt and HEAD.txt instead of running git. parent-status.txt warns
when the parent's info/attributes holds rules, since the clone does not get them.

--scope name=pathspec[,pathspec...] limits one diff to those git pathspecs.

--remove <packet dir> deletes a packet this script built (the --out directory)
once its review point passed or a newer packet superseded it. It refuses a path
that is or passes through a link or junction, a packet holding one or the
current directory, a Git work tree root, and any directory that is not what
the build makes: only clone/, a Git checkout detached at the SHA in
clone/review-input/HEAD.txt, with BASE.txt holding one SHA and
tracked-files.sha256 holding "<sha256>  <relative path>" lines.
Exit 0 on success, 2 on any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from harness_git import GitMetadataError, git_argv, git_environment, run_git

SCOPE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
DIFF_FLAGS = ("--no-color", "--no-ext-diff", "--no-textconv")
PACKET_MARKERS = ("HEAD.txt", "BASE.txt", "tracked-files.sha256")
FULL_SHA = re.compile(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})\n")
# "<sha256>  <relative path>", as build() writes tracked-files.sha256.
MANIFEST_LINE = re.compile(rb"[0-9a-f]{64}  (?!/|[A-Za-z]:/)([^\r]+)")


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

    def fail(error: OSError) -> None:
        raise ReviewInputError(f"cannot list {error.filename}: {error.strerror}")

    for root, dirs, files in os.walk(clone, onerror=fail):
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
    if len({name.casefold() for name, _ in scopes}) != len(scopes):
        raise ReviewInputError("duplicate --scope name (names are compared case-insensitively)")
    base, head = (rev_sha(repo, "--verify", "--end-of-options", f"{rev}^{{commit}}") for rev in (base, head))
    repo_head = rev_sha(repo, "HEAD")
    if repo_head != head:
        raise ReviewInputError(f"--repo HEAD is {repo_head}, not --head {head}; build from the candidate checkout")
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    tracked_dirty = any(line and not line.startswith(b"??") for line in status.splitlines())
    untracked = sum(1 for line in status.splitlines() if line.startswith(b"??"))
    local_attributes = repo / os.fsdecode(git(repo, "rev-parse", "--git-path", "info/attributes").strip())
    attributes_warning = ""
    if local_attributes.is_file() and local_attributes.stat().st_size:
        attributes_warning = (
            f"warning: {local_attributes.as_posix()} holds attribute rules that do not reach clones; "
            "they must be in the committed .gitattributes (delivery-harness/references/gitattributes-contract.md)\n"
        )

    out.mkdir(parents=True)
    clone = out / "clone"
    git(repo, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(repo), str(clone))
    git(clone, "checkout", "--quiet", "--detach", head)
    if rev_sha(clone, "HEAD") != head:
        raise ReviewInputError("clone HEAD does not equal --head")
    if git(clone, "status", "--porcelain", "--untracked-files=all").strip():
        raise ReviewInputError("clone is not clean after checkout")

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
    state = "dirty" if tracked_dirty else "clean"
    put("parent-status.txt", (
        f"repo: {repo.as_posix()}\nhead: {repo_head}\nstatus: {state}\nuntracked: {untracked}\n"
        "note: the clone holds committed content only; untracked and ignored parent files are not in it\n"
        + attributes_warning
    ).encode() + status)
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


def is_link(info: os.stat_result) -> bool:
    """True for a symlink and, on Windows, for any reparse point such as a junction."""
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def first_bad_manifest_line(data: bytes) -> int:
    """Number of the first line that is not "<sha256>  <relative path>" and a newline, else 0."""
    lines = data.split(b"\n")
    unterminated = lines.pop()
    for number, line in enumerate(lines, 1):
        match = MANIFEST_LINE.fullmatch(line)
        if not match or b".." in match.group(1).split(b"/"):
            return number
    return len(lines) + 1 if unterminated else 0


def remove(packet: Path) -> dict:
    def refuse(reason: str) -> ReviewInputError:
        return ReviewInputError(f"not a review packet: {reason}")

    given = Path(os.path.abspath(packet))
    packet = given.resolve()
    if os.path.normcase(given) != os.path.normcase(packet) or any(
        os.path.lexists(part) and is_link(os.lstat(part)) for part in (given, *given.parents)
    ):
        raise refuse(f"{given} is or passes through a link or junction")
    if not packet.is_dir():
        raise refuse(f"{packet} does not exist or is not a directory")
    cwd = Path.cwd().resolve()
    if cwd == packet or packet in cwd.parents:
        raise refuse(f"{packet} holds the current working directory")
    clone = packet / "clone"
    for name in PACKET_MARKERS:
        if not (clone / "review-input" / name).is_file():
            raise refuse(f"clone/review-input/{name} is missing in {packet}")
    others = sorted(entry.name for entry in packet.iterdir() if entry.name != "clone")
    if others:
        raise refuse(f"{packet} also holds {', '.join(others)}")
    pending = [packet]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if is_link(info):
                    inside = Path(entry.path).relative_to(packet).as_posix()
                    raise refuse(f"{inside} in {packet} is a link or junction")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(entry.path)

    markers = {name: (clone / "review-input" / name).read_bytes() for name in PACKET_MARKERS}
    for name in ("HEAD.txt", "BASE.txt"):
        if not FULL_SHA.fullmatch(markers[name]):
            raise refuse(f"clone/review-input/{name} in {packet} does not hold one full SHA")
    bad_line = first_bad_manifest_line(markers["tracked-files.sha256"])
    if bad_line:
        raise refuse(f"clone/review-input/tracked-files.sha256 in {packet} line {bad_line} "
                     "is not '<sha256>  <relative path>'")
    if not (clone / ".git").is_dir():
        raise refuse(f"clone/.git is missing in {packet}, so clone/ is not a Git checkout")
    # One call: top level, HEAD commit, then "HEAD" when detached or the branch ref.
    found = run_git(clone, "rev-parse", "--show-toplevel", "HEAD", "--symbolic-full-name", "HEAD", timeout=30)
    lines = found.stdout.splitlines() if found.returncode == 0 else []
    if len(lines) != 3 or Path(lines[0]).resolve() != clone:
        raise refuse(f"clone/ in {packet} is not a Git checkout of its own")
    head = markers["HEAD.txt"].decode("ascii").strip()
    if lines[1:] != [head, "HEAD"]:
        raise refuse(f"clone/ in {packet} is at {lines[1]} ({lines[2]}), "
                     f"not detached at {head} as clone/review-input/HEAD.txt says")
    # A packet may sit inside another work tree, but Git must not treat the packet itself as one
    # (an outer repository's core.worktree can). Plain discovery: no repository-config preflight.
    outer = subprocess.run(
        git_argv("rev-parse", "--show-toplevel"), cwd=packet, env=git_environment(), capture_output=True,
        text=True, encoding="utf-8", errors="surrogateescape", timeout=30, check=False,
    )
    if outer.returncode == 0 and Path(outer.stdout.strip()).resolve() == packet:
        raise refuse(f"{packet} is a Git work tree root")

    def clear_read_only(function, path, _error) -> None:
        # Git object files are read-only; on Windows that blocks unlink.
        os.chmod(path, stat.S_IWRITE)
        function(path)

    if sys.version_info >= (3, 12):
        shutil.rmtree(packet, onexc=clear_read_only)
    else:
        shutil.rmtree(packet, onerror=clear_read_only)
    return {"removed": packet.as_posix()}


def scope_arg(value: str) -> tuple[str, list[str]]:
    name, separator, spec = value.partition("=")
    paths = [item.strip() for item in spec.split(",") if item.strip()]
    if not separator or not SCOPE_NAME.fullmatch(name) or not paths:
        raise argparse.ArgumentTypeError(f"expected name=pathspec[,pathspec...] with a plain name: {value!r}")
    return name, paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, help="candidate checkout, HEAD at --head")
    parser.add_argument("--base", help="base revision of the reviewed range")
    parser.add_argument("--head", help="candidate revision")
    parser.add_argument("--out", type=Path, help="new directory; must not exist")
    parser.add_argument("--scope", type=scope_arg, action="append", default=[], metavar="NAME=PATHSPEC[,...]")
    parser.add_argument("--remove", type=Path, metavar="PACKET", help="delete a packet built by this script")
    args = parser.parse_args(argv)
    build_args = (args.repo, args.base, args.head, args.out)
    if args.remove is not None and (args.scope or any(value is not None for value in build_args)):
        parser.error("--remove takes no other option")
    if args.remove is None and None in build_args:
        parser.error("--repo, --base, --head and --out are required to build a packet")
    try:
        if args.remove is not None:
            summary = remove(args.remove)
        else:
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
