#!/usr/bin/env python3
"""Parse the opt-in platform-delivery/1 architecture contract."""

from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_contract import active_text, is_human_owner
from release_targets import KEBAB_RE, PLACEHOLDER_RE, parse_release_targets


PROTOCOL = "platform-delivery/1"
SECTION_HEADING = "## Platform Delivery Sequence"
STAGE_HEADER = (
    "| Order | Stage | Release surfaces | Required TEST IDs | Completion signal |"
)
MODES = {"whole_platform_sequential", "not_required"}
STATUSES = {"approved", "draft", "revision_requested", "blocked"}
USER_FACING_SURFACE_CLASSES = {
    "browser_extension",
    "hosted_web",
    "ios",
    "macos",
    "windows",
    "linux",
    "android",
}
ARCH_ID_RE = re.compile(r"\bARCH-[A-Z0-9-]+\b", re.IGNORECASE)
TEST_ID_RE = re.compile(r"\bTEST-[A-Z0-9-]+\b", re.IGNORECASE)
MARKER_RE = re.compile(
    r"^[ \t]*(?:-[ \t]*)?Platform delivery contract:[ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
FIELD_RE = re.compile(
    r"^[ \t]*(?:-[ \t]*)?(Platform delivery contract|Delivery mode|Decision owner|"
    r"Decision status|Shared surfaces|Shared interface ARCH IDs):[ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
STAGE_HEADING_RE = re.compile(rf"^{re.escape(STAGE_HEADER)}[ \t]*$", re.MULTILINE)


@dataclass(frozen=True)
class PlatformDeliveryStage:
    order: int
    stage_id: str
    surfaces: tuple[str, ...]
    test_ids: tuple[str, ...]
    completion_signal: str

    @property
    def id(self) -> str:
        return self.stage_id


@dataclass(frozen=True)
class PlatformDeliveryContract:
    protocol: str
    delivery_mode: str
    decision_owner: str
    decision_status: str
    shared_surfaces: tuple[str, ...]
    shared_arch_ids: tuple[str, ...]
    stages: tuple[PlatformDeliveryStage, ...]

    @property
    def mode(self) -> str:
        return self.delivery_mode


def _meaningful(value: str, *, minimum: int = 10) -> bool:
    value = value.strip()
    return (
        len(value) >= minimum
        and PLACEHOLDER_RE.search(value) is None
        and value.casefold().strip(" .") not in {"none", "n/a", "same", "works", "done"}
    )


def _ids(value: str, prefix: str) -> tuple[str, ...]:
    pattern = ARCH_ID_RE if prefix == "ARCH" else TEST_ID_RE
    values: list[str] = []
    for match in pattern.finditer(value):
        item = match.group(0).upper()
        if item not in values:
            values.append(item)
    return tuple(values)


def _exact_ids(value: str, prefix: str, label: str, findings: list[str]) -> tuple[str, ...]:
    pattern = rf"{prefix}-[A-Z0-9-]+"
    values: list[str] = []
    seen: set[str] = set()
    if not value.strip():
        return tuple(values)
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            findings.append(f"architecture: platform delivery {label} contains an empty ID")
            continue
        if re.fullmatch(pattern, item, re.IGNORECASE) is None:
            findings.append(
                f"architecture: platform delivery {label} contains invalid ID {item!r}"
            )
            continue
        normalized = item.upper()
        if normalized in seen:
            findings.append(
                f"architecture: platform delivery {label} contains duplicate ID {item!r}"
            )
            continue
        if normalized not in values:
            seen.add(normalized)
            values.append(normalized)
    return tuple(values)


def _split_values(value: str, label: str, findings: list[str]) -> tuple[str, ...]:
    values: list[str] = []
    if not value.strip():
        return tuple(values)
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            findings.append(f"architecture: platform delivery {label} contains an empty value")
            continue
        if item not in values:
            values.append(item)
    return tuple(values)


def _section(text: str) -> tuple[str | None, list[str]]:
    active = active_text(text)
    matches = list(
        re.finditer(rf"^{re.escape(SECTION_HEADING)}[ \t]*$", active, re.MULTILINE)
    )
    if len(matches) != 1:
        if len(matches) > 1:
            return None, [
                "architecture: Platform Delivery Sequence must contain exactly one active section"
            ]
        return None, []
    start = matches[0].end()
    following = re.search(r"^##\s+", active[start:], re.MULTILINE)
    end = start + following.start() if following else len(active)
    return active[start:end], []


def _field_rows(section: str) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    duplicates: set[str] = set()
    for match in FIELD_RE.finditer(section):
        label = match.group(1).casefold()
        if label in fields:
            duplicates.add(match.group(1))
            continue
        fields[label] = match.group(2).strip()
    return fields, sorted(duplicates)


def _markdown_cells(line: str) -> tuple[str, ...]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return tuple(cell.strip() for cell in stripped.split("|"))


def _separator_row(cells: tuple[str, ...]) -> bool:
    return all(cell and set(cell) == {"-"} for cell in cells)


def _table_rows(section: str) -> tuple[list[tuple[str, ...]], list[str]]:
    matches = list(STAGE_HEADING_RE.finditer(section))
    if len(matches) != 1:
        return [], ["architecture: Platform Delivery Sequence must contain exactly one stage-table header"]
    start = matches[0].end()
    following = re.search(r"^#\s+", section[start:], re.MULTILINE)
    end = start + following.start() if following else len(section)
    rows: list[tuple[str, ...]] = []
    findings: list[str] = []
    for line in section[start:end].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("|"):
            findings.append(
                "architecture: Platform Delivery Sequence stage table may contain only rows and blanks"
            )
            continue
        cells = _markdown_cells(line)
        is_separator = len(cells) == 5 and _separator_row(cells)
        if is_separator:
            continue
        if len(cells) != 5:
            findings.append(
                "architecture: Platform Delivery Sequence stage table uses the canonical five columns"
            )
            continue
        rows.append(cells)
    return rows, findings


def _architecture_contract_ids(architecture_text: str) -> set[str]:
    ids: set[str] = set()
    active = active_text(architecture_text)
    headings = (
        "## Component Architecture",
        "## API and Interface Contracts",
        "## Architecture Trace Index",
    )
    for heading in headings:
        match = re.search(rf"^{re.escape(heading)}\s*$", active, re.MULTILINE)
        if match is None:
            continue
        start = match.end()
        following = re.search(r"^##\s+", active[start:], re.MULTILINE)
        end = start + following.start() if following else len(active)
        for line in active[start:end].splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = _markdown_cells(line)
            if cells:
                ids.update(match_.group(0).upper() for match_ in ARCH_ID_RE.finditer(cells[0]))
    return ids


def _required_prd_tests(prd_text: str) -> set[str]:
    active = active_text(prd_text)
    match = re.search(r"^## Test Obligations\s*$", active, re.MULTILINE)
    if match is None:
        return set()
    start = match.end()
    following = re.search(r"^##\s+", active[start:], re.MULTILINE)
    end = start + following.start() if following else len(active)
    required: set[str] = set()
    for line in active[start:end].splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _markdown_cells(line)
        is_separator = len(cells) == 6 and _separator_row(cells)
        if is_separator:
            continue
        if len(cells) != 6:
            continue
        test_ids = _ids(cells[0], "TEST")
        if len(test_ids) == 1 and cells[3].casefold() == "yes":
            required.add(test_ids[0])
    return required


def _validate_marker(text: str, section: str | None, findings: list[str]) -> None:
    active = active_text(text)
    markers = MARKER_RE.findall(active)
    section_markers = MARKER_RE.findall(section or "")
    if not markers and section is None:
        return
    for marker in markers:
        if marker.strip() != PROTOCOL:
            findings.append(
                "architecture: Platform delivery contract supports only platform-delivery/1"
            )
    if len(markers) != 1:
        findings.append(
            "architecture: Platform delivery contract must occur exactly once"
        )
    elif len(section_markers) != 1:
        findings.append(
            "architecture: the Platform delivery contract must be inside "
            "Platform Delivery Sequence"
        )
    if section is None:
        findings.append(
            "architecture: a Platform delivery contract requires an active "
            "Platform Delivery Sequence section"
        )


def parse_platform_delivery(
    architecture_text: str,
    prd_text: str,
    *,
    require: bool = False,
) -> tuple[PlatformDeliveryContract | None, list[str]]:
    """Return the normalized platform contract and all fail-closed findings.

    An absent active section means legacy behavior and returns ``(None, [])``.
    A visible contract marker without its section is malformed. Code fences,
    comments, and indented examples never create a contract.
    """

    findings: list[str] = []
    section, section_findings = _section(architecture_text)
    findings.extend(section_findings)
    _validate_marker(architecture_text, section, findings)
    if section is None:
        if require:
            findings.append(
                "architecture: --platform-delivery requires platform-delivery/1"
            )
        return None, sorted(set(findings))

    fields, duplicate_fields = _field_rows(section)
    if duplicate_fields:
        findings.append(
            "architecture: platform delivery has duplicate fields: "
            + ", ".join(duplicate_fields)
        )
    missing_fields = [
        label
        for label in (
            "platform delivery contract",
            "delivery mode",
            "decision owner",
            "decision status",
            "shared surfaces",
            "shared interface arch ids",
        )
        if label not in fields
    ]
    if missing_fields:
        findings.append(
            "architecture: platform delivery is missing fields: "
            + ", ".join(missing_fields)
        )

    stage_rows, stage_findings = _table_rows(section)
    findings.extend(stage_findings)
    release_contract, release_findings = parse_release_targets(architecture_text)
    if release_findings:
        findings.append(
            "architecture: platform delivery cannot validate against invalid Release Targets"
        )

    expected_surfaces = release_contract.expected_surfaces
    class_by_surface: dict[str, str] = {}
    for target in release_contract.targets:
        class_by_surface.setdefault(target.surface, target.surface_class)
    user_facing_classes = {
        surface_class
        for surface, surface_class in class_by_surface.items()
        if surface_class in USER_FACING_SURFACE_CLASSES
    }

    stages: list[PlatformDeliveryStage] = []
    if not stage_findings:
        stage_ids: set[str] = set()
        surface_owner: dict[str, int] = {}
        expected_order = 1
        for row in stage_rows:
            order_value, stage_id, surfaces_value, tests_value, completion = row
            if not re.fullmatch(r"[1-9][0-9]*", order_value):
                findings.append(
                    "architecture: platform delivery stage order must be a positive decimal integer"
                )
                continue
            order = int(order_value)
            if order != expected_order:
                findings.append(
                    f"architecture: platform delivery stage order {order} is not contiguous"
                )
            expected_order = order + 1
            if not _meaningful(stage_id, minimum=3):
                findings.append(
                    "architecture: platform delivery stage ID is missing or uses placeholder text"
                )
            elif KEBAB_RE.fullmatch(stage_id) is None:
                findings.append(
                    f"architecture: platform delivery stage ID {stage_id!r} "
                    "must use lowercase kebab-case"
                )
            stage_key = stage_id.casefold()
            if stage_key in stage_ids:
                findings.append(
                    f"architecture: duplicate platform delivery stage ID {stage_id!r}"
                )
            stage_ids.add(stage_key)
            surfaces = _split_values(surfaces_value, "stage release surfaces", findings)
            if not surfaces:
                findings.append(
                    f"architecture: platform delivery stage {stage_id!r} names no release surface"
                )
            for surface in surfaces:
                if surface in surface_owner:
                    findings.append(
                        f"architecture: platform delivery surface {surface!r} appears in stages "
                        f"{surface_owner[surface]} and {order}"
                    )
                surface_owner[surface] = order
            test_ids = _exact_ids(
                tests_value,
                "TEST",
                f"stage {stage_id!r} TEST IDs",
                findings,
            )
            if not test_ids:
                findings.append(
                    f"architecture: platform delivery stage {stage_id!r} names no required TEST ID"
                )
            if not _meaningful(completion, minimum=12):
                findings.append(
                    f"architecture: platform delivery stage {stage_id!r} needs an observable completion signal"
                )
            stages.append(
                PlatformDeliveryStage(
                    order=order,
                    stage_id=stage_id,
                    surfaces=surfaces,
                    test_ids=test_ids,
                    completion_signal=completion,
                )
            )

    contract: PlatformDeliveryContract | None = None
    mode = fields.get("delivery mode", "")
    mode_match = re.fullmatch(
        r"whole_platform_sequential|not_required\s*(?:—|-|:)\s*(.+)",
        mode,
    )
    is_not_required = mode_match is not None and mode_match.group(1) is not None
    if fields.get("platform delivery contract") != PROTOCOL:
        findings.append(
            "architecture: Platform delivery contract must be platform-delivery/1"
        )
    if mode == "whole_platform_sequential":
        if not stages:
            findings.append(
                "architecture: whole_platform_sequential requires at least one stage"
            )
        if expected_surfaces and {surface for stage in stages for surface in stage.surfaces} != set(expected_surfaces):
            findings.append(
                "architecture: platform delivery stages must cover the expected release-surface inventory exactly once"
            )
    elif is_not_required:
        reason = mode_match.group(1).strip()
        if not _meaningful(reason, minimum=15):
            findings.append(
                "architecture: not_required delivery mode needs a concrete single-platform reason"
            )
        if stages:
            findings.append(
                "architecture: not_required delivery mode cannot contain platform stages"
            )
        if len(user_facing_classes) > 1:
            findings.append(
                "architecture: not_required delivery mode cannot bypass a multi-platform user-facing scope"
            )
        if fields.get("shared surfaces") or fields.get("shared interface arch ids"):
            findings.append(
                "architecture: not_required delivery mode cannot declare shared surfaces or interfaces"
            )
    elif mode:
        findings.append(
            "architecture: Delivery mode supports only whole_platform_sequential "
            "or not_required with a concrete reason"
        )

    owner = fields.get("decision owner", "")
    if not is_human_owner(owner) or not _meaningful(owner, minimum=3) or owner.casefold() in {
        "n/a", "none", "pending", "unknown", "same", "test",
    }:
        findings.append("architecture: platform delivery requires a named decision owner")
    status = fields.get("decision status", "").casefold()
    if status not in STATUSES:
        findings.append(
            "architecture: Decision status supports approved, draft, revision_requested, or blocked"
        )

    shared_surfaces = _split_values(fields.get("shared surfaces", ""), "shared surfaces", findings)
    shared_arch_ids = _exact_ids(
        fields.get("shared interface arch ids", ""),
        "ARCH",
        "shared interface ARCH IDs",
        findings,
    )
    known_arch_ids = _architecture_contract_ids(architecture_text)
    for arch_id in shared_arch_ids:
        if arch_id not in known_arch_ids:
            findings.append(
                f"architecture: platform delivery references unknown shared ARCH ID {arch_id}"
            )
    required_tests = _required_prd_tests(prd_text)
    all_test_ids = {test_id for stage in stages for test_id in stage.test_ids}
    for test_id in sorted(all_test_ids - required_tests):
        findings.append(
            f"architecture: platform delivery required TEST ID {test_id} is missing from PRD Required-Yes tests"
        )
    for surface in shared_surfaces:
        if surface not in expected_surfaces:
            findings.append(
                f"architecture: shared surface {surface!r} is not in the release-surface inventory"
            )
    covered_surfaces = {surface for stage in stages for surface in stage.surfaces}
    for surface in shared_surfaces:
        if surface not in covered_surfaces:
            findings.append(
                f"architecture: shared surface {surface!r} has no platform delivery stage coverage"
            )

    if fields.get("platform delivery contract") == PROTOCOL and (
        mode == "whole_platform_sequential" or mode_match is not None
    ):
        delivery_mode = (
            "not_required" if is_not_required else "whole_platform_sequential"
        )
        contract = PlatformDeliveryContract(
            protocol=PROTOCOL,
            delivery_mode=delivery_mode,
            decision_owner=owner,
            decision_status=status,
            shared_surfaces=shared_surfaces,
            shared_arch_ids=shared_arch_ids,
            stages=tuple(stages),
        )

    if require and contract is not None and status != "approved":
        findings.append(
            "architecture: --platform-delivery requires an approved platform contract"
        )
    return contract, sorted(set(findings))
