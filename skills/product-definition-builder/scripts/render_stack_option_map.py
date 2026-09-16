#!/usr/bin/env python3
"""Render a candidate approved-stack option map from canonical stack rows.

This is a pre-review aid, not an approval or rewrite tool. It reads one
stack-decisions file, derives the approved option IDs and executable layer
selections, and prints the current explicit ``||...||`` syntax for the owner to
review. It does not write, re-anchor an approved package, change a status, or
compute approval digests. The checker still compares the owner-approved map
independently against the same executable rows.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_product_package import (
    EXECUTABLE_STACK_STATUSES,
    STACK_OPTIONS_HEADER,
    STACK_SECTION_AREAS,
    STACK_LAYER_HEADER,
    _find_table,
    _section,
    _stack_areas,
    _subsection,
    _table_cells,
)
from markdown_contract import active_text


class OptionMapError(ValueError):
    """The stack rows cannot produce an unambiguous candidate map."""


def _reject_reserved(value: str, *, label: str) -> None:
    if not value:
        raise OptionMapError(f"{label} must not be empty")
    if any(token in value for token in ("||", ";", "=>")) or "\n" in value:
        raise OptionMapError(
            f"{label} {value!r} contains a reserved map separator; fix the "
            "stack text instead of inventing escaping"
        )


def candidate_option_map(stack_text: str) -> str:
    """Return the unambiguous explicit map for approved executable rows."""

    stack_text = active_text(stack_text)
    option_rows = _single_table(stack_text, STACK_OPTIONS_HEADER)
    if not option_rows:
        raise OptionMapError("stack decisions have no Coherent Options Presented table")

    entries: list[str] = []
    seen_option_ids: set[str] = set()
    for row in option_rows:
        if len(row) != len(STACK_OPTIONS_HEADER):
            raise OptionMapError(
                f"Coherent Options Presented row has {len(row)} cells; expected "
                f"{len(STACK_OPTIONS_HEADER)}"
            )
        if re.fullmatch(r"OPT-[A-Z0-9-]+", row[0], re.I) is None:
            raise OptionMapError(f"invalid option ID {row[0]!r}")
        option_id = row[0].upper()
        if option_id in seen_option_ids:
            raise OptionMapError(f"duplicate option ID {option_id}")
        seen_option_ids.add(option_id)
        disposition = row[5].strip().casefold()
        if disposition not in {"approved", "recommended", "rejected"}:
            raise OptionMapError(f"invalid option disposition {row[5]!r}")
        if disposition != "approved":
            continue

        areas = _stack_areas(row[1])
        if not areas:
            raise OptionMapError(
                f"approved option {option_id} has an unrecognized area {row[1]!r}"
            )
        layers: dict[str, str] = {}
        layer_names: dict[str, str] = {}
        for section_name, area_name in STACK_SECTION_AREAS.items():
            if area_name not in areas:
                continue
            if len(re.findall(rf"^## {re.escape(section_name)}\s*$", stack_text, re.M)) != 1:
                raise OptionMapError(f"missing or duplicate decision section {section_name!r}")
            section = _section(stack_text, f"## {section_name}") or ""
            if len(re.findall(r"^### Recorded or Approved Stack\s*$", section, re.M)) != 1:
                raise OptionMapError(f"missing or duplicate Recorded or Approved Stack in {section_name}")
            recorded = _subsection(section, "### Recorded or Approved Stack") or ""
            rows = _single_table(recorded, STACK_LAYER_HEADER)
            if not rows:
                raise OptionMapError(f"{section_name} has no recorded layer rows")
            for layer_row in rows:
                if len(layer_row) != len(STACK_LAYER_HEADER):
                    raise OptionMapError(
                        f"{section_name} layer row has {len(layer_row)} cells; "
                        f"expected {len(STACK_LAYER_HEADER)}"
                    )
                if layer_row[2].strip().casefold() not in EXECUTABLE_STACK_STATUSES:
                    raise OptionMapError(f"{section_name} layer {layer_row[0]!r} remains {layer_row[2]!r}; owner decision required")
                layer_key = layer_row[0].strip().casefold()
                selection = layer_row[1].strip()
                _reject_reserved(layer_row[0].strip(), label="layer name")
                _reject_reserved(selection, label=f"{option_id} layer {layer_key!r} selection")
                if layer_key in layers:
                    raise OptionMapError(
                        f"approved option {option_id} has duplicate layer {layer_key!r}"
                    )
                layer_names[layer_key] = layer_row[0].strip()
                layers[layer_key] = selection
        if not layers:
            raise OptionMapError(
                f"approved option {option_id} has no executable layer rows"
            )
        payload = ";".join(
            f"{layer_names[layer_key]}=>{layers[layer_key]}"
            for layer_key in layers
        )
        entries.append(f"{option_id}={payload}")

    if not entries:
        raise OptionMapError(
            "no approved option found; a generator cannot mint an approval"
        )
    return "||" + "||".join(entries) + "||"


def _single_table(text: str, header: tuple[str, ...]):
    expected = tuple(cell.casefold() for cell in header)
    matches = sum(
        1 for line in text.splitlines()
        if (cells := _table_cells(line)) is not None
        and tuple(cell.casefold() for cell in cells) == expected
    )
    if matches > 1:
        raise OptionMapError(f"duplicate table with header {header[0]!r}")
    return _find_table(text, header)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stack-decisions",
        required=True,
        type=Path,
        help="read-only stack-decisions.md input",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        stack_text = args.stack_decisions.read_text(encoding="utf-8")
        print(candidate_option_map(stack_text))
    except (OSError, UnicodeError, OptionMapError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
