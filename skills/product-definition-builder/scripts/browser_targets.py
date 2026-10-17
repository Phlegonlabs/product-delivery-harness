#!/usr/bin/env python3
"""Parse the PRD Browser Targets contract (browser-targets/1).

Shared by the Product Definition package checker, the delivery acceptance
checker, and consumer CI. Consumer repositories copy this file into
.github/scripts/ next to markdown_contract.py, so it may depend only on the
standard library and that sibling module.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

# Consumer repositories copy this file next to markdown_contract.py; import
# the sibling without duplicating the path entry on repeated imports.
SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from markdown_contract import active_text  # noqa: E402


SECTION_HEADING = "### Browser Targets"
CONTRACT_MARKER = "Browser targets contract: browser-targets/1"
TABLE_HEADER = "| Release target | Browser | Platform | Smoke TEST ID |"
RELEASE_TARGET_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SMOKE_TEST_ID_RE = re.compile(r"^TEST-[A-Z0-9-]+$")
# The section runs until the next heading of level 1, 2 or 3; level 4 and
# deeper headings stay inside it.
SECTION_BOUNDARY_RE = re.compile(r"#{1,3}(?:\s|$)")
DELIMITER_CELL_RE = re.compile(r":?-{1,}:?")

ENGINE_ORDER = ("chromium", "firefox", "webkit")
BROWSER_ENGINES = {
    "chrome": "chromium",
    "edge": "chromium",
    "firefox": "firefox",
    "safari": "webkit",
}
SUPPORTED_PAIRS = {
    ("chrome", "desktop"),
    ("chrome", "android"),
    ("edge", "desktop"),
    ("firefox", "desktop"),
    ("safari", "macos"),
    ("safari", "ios"),
}
ENGINE_LABELS = {
    "chromium": "Chromium engine",
    "firefox": "Playwright Firefox",
    "webkit": "WebKit approximation of Safari",
}


@dataclass(frozen=True)
class BrowserTarget:
    release_target: str
    browser: str
    platform: str
    smoke_test_id: str
    engine: str


@dataclass(frozen=True)
class BrowserTargets:
    declared: bool
    targets: tuple[BrowserTarget, ...]
    engines: tuple[str, ...]
    coverage: tuple[tuple[str, str, str], ...]
    errors: tuple[str, ...]


def _table_cells(row: str) -> list[str]:
    """Split one pipe-bounded row into cells without trimming outer pipes."""
    return [cell.strip() for cell in row.strip()[1:-1].split("|")]


def _is_delimiter_row(row: str) -> bool:
    stripped = row.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = _table_cells(stripped)
    return len(cells) == 4 and all(
        DELIMITER_CELL_RE.fullmatch(cell) for cell in cells
    )


def parse_browser_targets(prd_text: str) -> BrowserTargets:
    """Return the declared browser-target contract and every finding."""
    lines = active_text(prd_text).splitlines()
    headings = [
        number for number, line in enumerate(lines) if line.strip() == SECTION_HEADING
    ]
    markers = [
        number for number, line in enumerate(lines) if line.strip() == CONTRACT_MARKER
    ]
    if not headings and not markers:
        return BrowserTargets(False, (), ("chromium",), (), ())

    errors: list[str] = []
    if len(headings) != 1:
        errors.append(
            f"browser targets: expected exactly one '{SECTION_HEADING}' heading, "
            f"found {len(headings)}"
        )
    if len(markers) != 1:
        errors.append(
            f"browser targets: expected exactly one '{CONTRACT_MARKER}' marker, "
            f"found {len(markers)}"
        )
    if errors:
        return BrowserTargets(True, (), (), (), tuple(errors))

    heading_line, marker_line = headings[0], markers[0]
    section_end = next(
        (
            number
            for number in range(heading_line + 1, len(lines))
            if SECTION_BOUNDARY_RE.match(lines[number].strip())
        ),
        len(lines),
    )
    if not heading_line < marker_line < section_end:
        errors.append(
            f"browser targets: the contract marker must appear inside the "
            f"'{SECTION_HEADING}' section"
        )
        return BrowserTargets(True, (), (), (), tuple(errors))

    section = lines[heading_line + 1 : section_end]
    header_offsets = [
        offset for offset, line in enumerate(section) if line.strip() == TABLE_HEADER
    ]
    if not header_offsets:
        errors.append(f"browser targets: missing table header '{TABLE_HEADER}'")
        return BrowserTargets(True, (), (), (), tuple(errors))
    header_offset = header_offsets[0]
    if marker_line - heading_line - 1 > header_offset:
        errors.append(
            "browser targets: the contract marker must appear before the targets table"
        )
    # A stray table or piped prose line before the canonical header would
    # otherwise be ignored silently; report each such active line once.
    for line in section[:header_offset]:
        if "|" in line:
            errors.append(
                "browser targets: unexpected table content before the targets table"
            )

    delimiter_offset = header_offset + 1
    if delimiter_offset >= len(section) or not _is_delimiter_row(
        section[delimiter_offset]
    ):
        errors.append(
            "browser targets: the table header must be followed by a delimiter "
            "row with exactly four cells matching :?-+:?"
        )
        return BrowserTargets(True, (), (), (), tuple(errors))

    # Data rows are the contiguous pipe-bounded lines after the delimiter. A
    # piped line that is not a proper row is reported instead of silently
    # ending the table; the table only ends at a line without any pipe.
    rows: list[str] = []
    for offset in range(delimiter_offset + 1, len(section)):
        stripped = section[offset].strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            rows.append(stripped)
            continue
        if "|" in stripped:
            errors.append(
                "browser targets: table row must start and end with '|': "
                f"{stripped!r}"
            )
            continue
        for later in section[offset + 1 :]:
            if "|" in later:
                errors.append(
                    "browser targets: unexpected table content after the "
                    "targets table"
                )
        break
    if not rows:
        errors.append("browser targets: the targets table has no data rows")
        return BrowserTargets(True, (), (), (), tuple(errors))

    seen: set[tuple[str, str, str]] = set()
    targets: list[BrowserTarget] = []
    for position, row in enumerate(rows, start=1):
        cells = _table_cells(row)
        if len(cells) != 4:
            errors.append(
                f"browser targets: table row {position} has {len(cells)} cells, "
                "expected 4"
            )
            continue
        release_target, browser, platform, smoke_test_id = cells
        if not RELEASE_TARGET_RE.fullmatch(release_target):
            errors.append(
                f"browser targets: release target {release_target!r} must be "
                "lowercase kebab-case"
            )
        if not SMOKE_TEST_ID_RE.fullmatch(smoke_test_id):
            errors.append(
                f"browser targets: Smoke TEST ID {smoke_test_id!r} must match "
                "TEST-[A-Z0-9-]+"
            )
        key = (release_target, browser, platform)
        if key in seen:
            errors.append(
                f"browser targets: duplicate target row for release target "
                f"{release_target!r}, browser {browser!r}, platform {platform!r}"
            )
        seen.add(key)
        if browser not in BROWSER_ENGINES:
            errors.append(f"browser targets: unknown browser {browser!r}")
            continue
        if (browser, platform) not in SUPPORTED_PAIRS:
            errors.append(
                f"browser targets: unsupported browser and platform pair "
                f"{browser!r} on {platform!r}"
            )
            continue
        targets.append(
            BrowserTarget(
                release_target=release_target,
                browser=browser,
                platform=platform,
                smoke_test_id=smoke_test_id,
                engine=BROWSER_ENGINES[browser],
            )
        )

    if errors:
        return BrowserTargets(True, (), (), (), tuple(errors))
    engines = tuple(
        engine
        for engine in ENGINE_ORDER
        if any(target.engine == engine for target in targets)
    )
    coverage = sorted(
        {
            (target.release_target, target.smoke_test_id, target.engine)
            for target in targets
        },
        key=lambda item: (item[0], ENGINE_ORDER.index(item[2]), item[1]),
    )
    return BrowserTargets(True, tuple(targets), engines, tuple(coverage), ())


def engine_label(engine: str) -> str:
    """Return the human-readable label for one Playwright engine."""
    return ENGINE_LABELS[engine]


def requires_cross_browser(result: BrowserTargets) -> bool:
    """Return whether a valid declaration demands more than Chromium."""
    return (
        result.declared
        and not result.errors
        and any(engine != "chromium" for engine in result.engines)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse the PRD Browser Targets contract (browser-targets/1)"
    )
    parser.add_argument("--prd", required=True, help="path to the PRD Markdown file")
    parser.add_argument(
        "--github-output",
        help="GitHub Actions output file receiving declared= and engines= lines",
    )
    args = parser.parse_args()
    try:
        prd_text = Path(args.prd).read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"browser targets: cannot read {args.prd}: {error}", file=sys.stderr)
        return 2
    result = parse_browser_targets(prd_text)
    if result.errors:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"declared": result.declared, "engines": list(result.engines)},
            separators=(",", ":"),
        )
    )
    if args.github_output:
        engines = json.dumps(list(result.engines), separators=(",", ":"))
        with open(args.github_output, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"declared={'true' if result.declared else 'false'}\n")
            handle.write(f"engines={engines}\n")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
