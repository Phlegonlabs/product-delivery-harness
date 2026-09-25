#!/usr/bin/env python3
"""Report the normative word weight of each skill and its delta vs a baseline.

Counts words in every skill's SKILL.md and every Markdown file under its
references/ tree, including nested optional references, while excluding
scripts, assets, and other skill trees. It compares the totals against the
most recent reachable v* tag (or --baseline <ref>) and prints one line per
changed file plus per-skill and grand totals. This is a read-only visibility
tool for the documentation complexity ratchet: it makes growth visible at
verification time and never gates a release.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import ManifestError  # noqa: E402
from harness_git import GitMetadataError, reject_object_substitution, run_git  # noqa: E402

def _git(repo_root: Path, *args: str) -> str:
    result = run_git(
        repo_root,
        *args,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0:
        raise ManifestError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def _run_git_bytes(
    repo_root: Path, *args: str, input_bytes: bytes | None = None
) -> tuple[bytes, subprocess.CompletedProcess[bytes]]:
    result = run_git(
        repo_root,
        *args,
        text=False,
        timeout=60,
        input=input_bytes,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ManifestError(f"git {' '.join(args)} failed: {detail}")
    assert isinstance(result.stdout, bytes)
    return result.stdout, result


def _word_count(text: str) -> int:
    return len(text.split())


def _is_skill_document(path: Path) -> bool:
    parts = path.parts
    if parts[:1] != ("skills",):
        return False
    if len(parts) == 3 and parts[2] == "SKILL.md":
        return True
    return len(parts) >= 4 and parts[2] == "references" and path.suffix == ".md"


def tracked_files(repo_root: Path, ref: str | None) -> list[Path]:
    """SKILL.md plus nested references Markdown under skills/ at ref."""

    if ref is None:
        listing = _git(
            repo_root,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "skills",
        )
    else:
        listing = _git(repo_root, "ls-tree", "-r", "--name-only", ref, "--", "skills")
    files = []
    for line in listing.splitlines():
        path = line.strip()
        if not path:
            continue
        pure = Path(path)
        if ref is None and not (repo_root / pure).is_file():
            # A working-tree move/deletion can leave the old path in the index
            # before the user authorizes a commit. Count the live worktree,
            # not a path whose bytes no longer exist.
            continue
        if _is_skill_document(pure):
            files.append(pure)
    return sorted(files)


def _tree_blobs(repo_root: Path, ref: str) -> list[tuple[Path, str]]:
    """Return tracked skill-document paths and their immutable blob OIDs."""

    listing = _git(
        repo_root,
        "ls-tree",
        "-r",
        "-z",
        ref,
        "--",
        "skills",
    )
    entries: list[tuple[Path, str]] = []
    for raw_entry in listing.split("\0"):
        if not raw_entry:
            continue
        metadata, separator, path = raw_entry.partition("\t")
        if not separator:
            raise ManifestError(f"malformed git ls-tree entry for {ref}")
        pure = Path(path)
        if not _is_skill_document(pure):
            continue
        parts = metadata.split()
        if len(parts) != 3:
            raise ManifestError(f"malformed git ls-tree metadata for {ref}")
        _mode, object_type, oid = parts
        if (
            re.fullmatch(r"[0-9a-f]{40,64}", oid) is None
            or object_type != "blob"
        ):
            raise ManifestError(f"git ls-tree returned a non-blob entry for {ref}")
        entries.append((pure, oid))
    return sorted(entries, key=lambda item: item[0].as_posix())


def _blob_words(repo_root: Path, blobs: list[tuple[Path, str]]) -> dict[str, int]:
    """Read every immutable blob with one cat-file batch subprocess."""

    if not blobs:
        return {}
    request = "".join(f"{oid}\n" for _, oid in blobs).encode("ascii")
    raw, _ = _run_git_bytes(
        repo_root,
        "cat-file",
        "--batch",
        input_bytes=request,
    )
    words: dict[str, int] = {}
    offset = 0
    for path, oid in blobs:
        header_end = raw.find(b"\n", offset)
        if header_end < 0:
            raise ManifestError(f"git cat-file batch ended before {oid}")
        header = raw[offset:header_end].decode("ascii", errors="replace")
        parts = header.split()
        if len(parts) != 3 or parts[0] != oid or parts[1] != "blob":
            raise ManifestError(f"git cat-file returned malformed header for {oid}")
        try:
            size = int(parts[2])
        except ValueError as exc:
            raise ManifestError(f"git cat-file returned malformed size for {oid}") from exc
        if size < 0 or header_end + 1 + size + 1 > len(raw) or raw[header_end + 1 + size] != 10:
            raise ManifestError(f"git cat-file returned truncated blob {oid}")
        content = raw[header_end + 1:header_end + 1 + size]
        words[path.as_posix()] = _word_count(content.decode("utf-8", errors="replace"))
        offset = header_end + 1 + size + 1
    if offset != len(raw):
        raise ManifestError("git cat-file returned unexpected trailing data")
    return words


def read_file(repo_root: Path, path: Path, ref: str | None) -> str:
    if ref is None:
        return (repo_root / path).read_text(encoding="utf-8")
    return _git(repo_root, "show", f"{ref}:{path.as_posix()}")


def resolve_ref(repo_root: Path, ref: str) -> str:
    """Resolve one immutable commit before listing or reading baseline blobs."""

    result = run_git(
        repo_root,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{ref}^{{commit}}",
        text=True,
        timeout=30,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
        raise ManifestError(f"invalid baseline ref: {ref}")
    return commit


def weights(repo_root: Path, ref: str | None) -> dict[str, int]:
    if ref is not None:
        return _blob_words(repo_root, _tree_blobs(repo_root, ref))
    return {
        path.as_posix(): _word_count(read_file(repo_root, path, ref))
        for path in tracked_files(repo_root, ref)
    }


def latest_tag(repo_root: Path) -> str | None:
    result = run_git(
        repo_root,
        "describe",
        "--tags",
        "--abbrev=0",
        "--match",
        "v[0-9]*",
        text=True,
        timeout=30,
    )
    tag = result.stdout.strip()
    return tag if result.returncode == 0 and re.fullmatch(r"v[\d.]+", tag) else None


def report(repo_root: Path, baseline: str | None) -> int:
    try:
        reject_object_substitution(repo_root)
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    now = weights(repo_root, None)
    ref = baseline
    baseline_label = ref
    if ref is None:
        ref = latest_tag(repo_root)
        if ref is None:
            print("no v* tag found; reporting absolute counts only")
        baseline_label = ref
    if ref is not None:
        ref = resolve_ref(repo_root, ref)
    base = weights(repo_root, ref) if ref else {}

    skills = sorted({path.split("/", 2)[1] for path in now} |
                    {path.split("/", 2)[1] for path in base})
    grand_now = grand_base = 0
    for skill in skills:
        prefix = f"skills/{skill}/"
        skill_now = sum(v for k, v in now.items() if k.startswith(prefix))
        skill_base = sum(v for k, v in base.items() if k.startswith(prefix))
        grand_now += skill_now
        grand_base += skill_base
        for key in sorted(set(now) | set(base)):
            if not key.startswith(prefix):
                continue
            file_now = now.get(key, 0)
            file_base = base.get(key, 0)
            if file_now == file_base:
                continue
            status = "added" if key not in base else (
                "removed" if key not in now else "changed"
            )
            print(
                f"{status:>7} {key}: {file_base} -> {file_now} "
                f"({file_now - file_base:+d})"
            )
        print(f"TOTAL {skill}: {skill_base} -> {skill_now} "
              f"({skill_now - skill_base:+d})")
    print(f"GRAND TOTAL: {grand_base} -> {grand_now} ({grand_now - grand_base:+d}) "
          f"baseline: {baseline_label or 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--baseline",
        help="git ref to compare against (default: most recent v* tag)",
    )
    args = parser.parse_args(argv)
    try:
        return report(args.repo_root, args.baseline)
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
