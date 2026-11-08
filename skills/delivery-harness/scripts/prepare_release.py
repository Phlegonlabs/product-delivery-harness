#!/usr/bin/env python3
"""Prepare a source release of this repository in the working tree.

    python skills/delivery-harness/scripts/prepare_release.py --version 0.78.0 --entries <dir>
    python skills/delivery-harness/scripts/prepare_release.py --check

`--entries` names a directory holding en.md, zh-TW.md, zh-CN.md and es.md.
Each file is one version-history entry body: the one-line text that follows
`- **X.Y.Z** — ` in that language's README.

The command refuses, and writes nothing, unless `skills/delivery-harness/VERSION`,
`package.json`, both `package-lock.json` version fields, the four README badges
and the four top README entries hold the same version, and the four READMEs
hold the same number of version-history entries. It then sets the new version
on those surfaces, puts each entry first in its README's version history,
drops each README's oldest entry so the window keeps its size, moves the
English one to the top of CHANGELOG.md's list, updates CHANGELOG.md's
"through" line and prints the files it changed. Every file keeps its line
endings. It never commits, tags or pushes.

`--check` prints the version each surface holds and exits 1 when they differ.
Run both from the repository root, or pass `--root`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


VERSION_FILE = "skills/delivery-harness/VERSION"
PACKAGE = "package.json"
LOCK = "package-lock.json"
CHANGELOG = "CHANGELOG.md"
READMES = {
    "en.md": "README.md",
    "zh-TW.md": "README.zh-TW.md",
    "zh-CN.md": "README.zh-CN.md",
    "es.md": "README.es.md",
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
BADGE = re.compile(r"badge/version-(\d+\.\d+\.\d+)-")
ENTRY = re.compile(r"^- \*\*(\d+\.\d+\.\d+)\*\* ")
THROUGH = re.compile(r"^(English release history through )(\d+\.\d+\.\d+)(\.)", re.M)
JSON_VERSION = re.compile(r'"version": "(\d+\.\d+\.\d+)"')


class ReleaseError(Exception):
    pass


def read_text(path: Path) -> tuple[str, str]:
    """Return the file's text with LF line breaks and its own line break."""
    text = path.read_bytes().decode("utf-8")
    crlf = text.count("\r\n")
    if crlf and crlf != text.count("\n"):
        raise ReleaseError(f"{path.name} mixes CRLF and LF line endings")
    return text.replace("\r\n", "\n"), "\r\n" if crlf else "\n"


def entry_lines(name: str, lines: list[str]) -> list[int]:
    """Indices of the version-history entries, one line each, blank-line separated."""
    found = [index for index, line in enumerate(lines) if ENTRY.match(line)]
    if not found:
        raise ReleaseError(f"{name} has no version-history entries")
    for before, after in zip(found, found[1:]):
        if after != before + 2 or lines[before + 1].strip():
            raise ReleaseError(f"{name} version-history entries are not one blank line apart")
    if found[-1] + 1 >= len(lines) or lines[found[-1] + 1].strip():
        raise ReleaseError(f"{name} has no blank line after its oldest entry")
    return found


def surfaces(root: Path) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Return (label, version) for every release surface and each README's entry count."""
    found = [(VERSION_FILE, (root / VERSION_FILE).read_text(encoding="utf-8").strip())]
    found.append((PACKAGE, str(json.loads((root / PACKAGE).read_text(encoding="utf-8")).get("version"))))
    lock = json.loads((root / LOCK).read_text(encoding="utf-8"))
    found.append((f"{LOCK} version", str(lock.get("version"))))
    found.append((f'{LOCK} packages[""].version', str(lock.get("packages", {}).get("", {}).get("version"))))
    counts = {}
    for readme in READMES.values():
        text, _ = read_text(root / readme)
        badges = BADGE.findall(text)
        found.append((f"{readme} badge", badges[0] if len(badges) == 1 else f"{len(badges)} badges"))
        lines = text.split("\n")
        indices = entry_lines(readme, lines)
        found.append((f"{readme} top entry", ENTRY.match(lines[indices[0]]).group(1)))
        counts[readme] = len(indices)
    return found, counts


def disagreements(found: list[tuple[str, str]], counts: dict[str, int]) -> list[str]:
    problems = []
    if len({version for _, version in found}) != 1:
        problems.append("release surfaces disagree: " + "; ".join(f"{label} {version}" for label, version in found))
    if len(set(counts.values())) != 1:
        problems.append("READMEs hold different entry counts: " + "; ".join(f"{name} {count}" for name, count in counts.items()))
    return problems


def read_entries(directory: Path) -> dict[str, str]:
    bodies = {}
    for name, readme in READMES.items():
        path = directory / name
        if not path.is_file():
            raise ReleaseError(f"missing entry file {path}")
        body = path.read_text(encoding="utf-8-sig").strip()
        if not body:
            raise ReleaseError(f"{path} is empty")
        if "\n" in body:
            raise ReleaseError(f"{path} must be one line: a README entry is one paragraph")
        if body.startswith("- **"):
            raise ReleaseError(f"{path} must hold only the entry body; the script adds `- **X.Y.Z** — `")
        bodies[readme] = body
    return bodies


def set_json_versions(name: str, text: str, old: str, new: str, count: int, expected: dict) -> str:
    updated, replaced = JSON_VERSION.subn(
        lambda match: match.group(0).replace(old, new) if match.group(1) == old else match.group(0),
        text,
        count=count,
    )
    if replaced != count or json.loads(updated) != expected:
        raise ReleaseError(f"{name}: the first {count} version fields are not the release fields")
    return updated


def prepare(root: Path, new: str, entries_dir: Path) -> list[str]:
    if not SEMVER.match(new):
        raise ReleaseError(f"--version must be X.Y.Z, got {new!r}")
    found, counts = surfaces(root)
    problems = disagreements(found, counts)
    if problems:
        raise ReleaseError("; ".join(problems))
    old = found[0][1]
    if tuple(map(int, new.split("."))) <= tuple(map(int, old.split("."))):
        raise ReleaseError(f"--version {new} must be greater than the current {old}")
    bodies = read_entries(entries_dir)

    writes: dict[str, tuple[str, str]] = {}
    text, newline = read_text(root / VERSION_FILE)
    writes[VERSION_FILE] = (text.replace(old, new, 1), newline)

    text, newline = read_text(root / PACKAGE)
    expected = json.loads(text)
    expected["version"] = new
    writes[PACKAGE] = (set_json_versions(PACKAGE, text, old, new, 1, expected), newline)

    text, newline = read_text(root / LOCK)
    expected = json.loads(text)
    expected["version"] = new
    expected["packages"][""]["version"] = new
    writes[LOCK] = (set_json_versions(LOCK, text, old, new, 2, expected), newline)

    rotated = ""
    for readme, body in bodies.items():
        text, newline = read_text(root / readme)
        text = BADGE.sub(f"badge/version-{new}-", text, count=1)
        lines = text.split("\n")
        indices = entry_lines(readme, lines)
        if readme == "README.md":
            rotated = lines[indices[-1]]
        del lines[indices[-1]:indices[-1] + 2]
        lines[indices[0]:indices[0]] = [f"- **{new}** — {body}", ""]
        writes[readme] = ("\n".join(lines), newline)

    text, newline = read_text(root / CHANGELOG)
    rotated_version = ENTRY.match(rotated).group(1)
    if len(THROUGH.findall(text)) != 1:
        raise ReleaseError(f"{CHANGELOG} needs exactly one 'English release history through X.Y.Z.' line")
    lines = text.split("\n")
    existing = [index for index, line in enumerate(lines) if ENTRY.match(line)]
    if any(ENTRY.match(lines[index]).group(1) == rotated_version for index in existing):
        raise ReleaseError(f"{CHANGELOG} already holds {rotated_version}")
    if not existing:
        raise ReleaseError(f"{CHANGELOG} has no entries")
    lines[existing[0]:existing[0]] = [rotated, ""]
    text = THROUGH.sub(lambda match: match.group(1) + rotated_version + match.group(3), "\n".join(lines))
    writes[CHANGELOG] = (text, newline)

    for name, (text, newline) in writes.items():
        (root / name).write_bytes(text.replace("\n", newline).encode("utf-8"))
    return list(writes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set a new release version on every surface, or check that they agree.",
        allow_abbrev=False,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--version", help="new version X.Y.Z")
    mode.add_argument("--check", action="store_true", help="report whether the surfaces agree")
    parser.add_argument("--entries", type=Path, help="directory holding en.md, zh-TW.md, zh-CN.md and es.md")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    if args.version and args.entries is None:
        parser.error("--version needs --entries")
    try:
        if args.check:
            found, counts = surfaces(args.root)
            for label, version in found:
                print(f"{label}: {version}")
            problems = disagreements(found, counts)
            for problem in problems:
                print(problem, file=sys.stderr)
            if not problems:
                print(f"release surfaces agree on {found[0][1]}")
            return 1 if problems else 0
        for name in prepare(args.root, args.version, args.entries):
            print(name)
        return 0
    except (ReleaseError, OSError, ValueError, KeyError) as exc:
        print(f"prepare_release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
