#!/usr/bin/env python3
"""Parse the authoritative Release Targets section in architecture.md."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from markdown_contract import active_text


SECTION_HEADING = "## Release Targets"
EXPECTED_PREFIX = "Expected deployable surfaces:"
RELEASE_MARKER_LINE_RE = re.compile(r"^Release source policy:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
TARGET_HEADING_RE = re.compile(r"^### Release Target:\s*(.*?)\s*$", re.MULTILINE)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_POLICY_RE = re.compile(
    r"^stage=(development|production);\s*ref=([a-zA-Z0-9._/-]+);\s*"
    r"sha=([a-zA-Z0-9._/-]+)$"
)
PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]|<[^>]+>|\b(?:tbd|todo|placeholder)\b", re.I)

FIELDS = (
    "Surface",
    "Surface class",
    "Public discoverability",
    "Surface suffix",
    "Release name",
    "Provider",
    "Stage",
    "Source policy",
    "Artifact kind",
    "Signing requirement",
    "Exact channel / track",
    "Submission / promotion / review / manual approval path",
    "Availability signal",
    "Rollout",
    "Rollback / forward-fix",
)

SURFACE_CLASSES = {
    "hosted_web",
    "hosted_api",
    "browser_extension",
    "ios",
    "android",
    "macos",
    "windows",
    "worker",
    "job",
    "webhook",
    "realtime",
    "cli",
    "agent",
    "other_nonpublic",
    "mcp_server",
    "skill_or_plugin",
    "library_or_sdk",
    "messaging_bot",
    "marketplace_app",
    "assistant_listing",
    "container_or_self_hosted",
    "internal_service",
}
# Surface classes a Public discoverability=yes target may use.
DISCOVERABLE_SURFACE_CLASSES = {
    "hosted_web",
    "mcp_server",
    "skill_or_plugin",
    "library_or_sdk",
    "messaging_bot",
    "marketplace_app",
    "assistant_listing",
    "container_or_self_hosted",
}
DISCOVERABILITY_VALUES = {"yes", "no"}
NO_INDEPENDENT_ARTIFACT = "no independent artifact"

DESCRIPTIVE_FIELDS = {
    "source policy",
    "signing requirement",
    "submission / promotion / review / manual approval path",
    "availability signal",
    "rollout",
    "rollback / forward-fix",
}


@dataclass(frozen=True)
class ReleaseTarget:
    target_id: str
    surface: str
    surface_class: str
    public_discoverability: str
    surface_suffix: str
    release_name: str
    provider: str
    stage: str
    source_policy: str
    artifact_kind: str
    signing_requirement: str
    channel: str
    approval_path: str
    availability_signal: str
    rollout: str
    recovery: str
    source_policy_protocol: str = "candidate/1"


@dataclass(frozen=True)
class ReleaseTargetContract:
    expected_surfaces: tuple[str, ...]
    targets: tuple[ReleaseTarget, ...]
    explicit_none_reason: str | None
    source_policy_protocol: str = "candidate/1"

    def by_id(self) -> dict[str, ReleaseTarget]:
        return {target.target_id: target for target in self.targets}


@dataclass(frozen=True)
class SourcePolicyAuthority:
    stage: str
    ref: str
    sha: str


def allows_no_independent_artifact(target: ReleaseTarget) -> bool:
    return target.artifact_kind.strip().casefold() == NO_INDEPENDENT_ARTIFACT


def is_public_web_target(target: ReleaseTarget) -> bool:
    return target.surface_class == "hosted_web" and target.public_discoverability == "yes"


def _meaningful(value: str, *, minimum: int = 8) -> bool:
    stripped = value.strip()
    return (
        len(stripped) >= minimum
        and PLACEHOLDER_RE.search(stripped) is None
        and stripped.casefold().strip(" .")
        not in {"none", "n/a", "same", "works", "done", "see above"}
    )


def _section(text: str) -> tuple[str | None, list[str]]:
    active = active_text(text)
    matches = list(
        re.finditer(rf"^{re.escape(SECTION_HEADING)}\s*$", active, re.MULTILINE)
    )
    if len(matches) != 1:
        return None, [
            "architecture: Release Targets must contain exactly one active section"
        ]
    start = matches[0].end()
    following = re.search(r"^##\s+", active[start:], re.MULTILINE)
    end = start + following.start() if following else len(active)
    return active[start:end], []


def _field_rows(block: str) -> tuple[dict[str, str], list[str]]:
    pairs = [
        (match.group(1).strip().casefold(), match.group(2).strip())
        for match in re.finditer(r"^\s*-\s*([^:\n]+):\s*(.*?)\s*$", block, re.MULTILINE)
    ]
    counts = Counter(key for key, _ in pairs)
    return dict(pairs), sorted(key for key, count in counts.items() if count > 1)


def _release_marker_protocol(section: str) -> tuple[str, list[str]]:
    """Read one active policy marker; ambiguous or unknown markers fail."""

    markers = RELEASE_MARKER_LINE_RE.findall(section)
    supported = {"dual-branch/1", "main-preview/1"}
    findings: list[str] = []
    if len(markers) > 1:
        findings.append(
            "architecture: Release Targets must contain at most one "
            "active Release source policy marker"
        )
    if any(marker not in supported for marker in markers):
        findings.append(
            "architecture: the only supported Release source policy markers "
            "are dual-branch/1 and main-preview/1; omit the line for the legacy candidate protocol"
        )
    protocol = markers[0] if len(markers) == 1 and markers[0] in supported else "candidate/1"
    return protocol, findings


def parse_source_policy(
    source_policy: str,
    *,
    expected_stage: str,
    source_policy_protocol: str = "candidate/1",
) -> tuple[SourcePolicyAuthority | None, list[str]]:
    """Return the stage, ref, and SHA authorities selected by the protocol."""

    if source_policy_protocol not in {"candidate/1", "dual-branch/1", "main-preview/1"}:
        return None, [
            "Source policy protocol must be candidate/1, dual-branch/1 or main-preview/1"
        ]
    if expected_stage not in {"development", "production"}:
        return None, ["Source policy expected stage must be development or production"]
    match = SOURCE_POLICY_RE.fullmatch(source_policy.strip())
    expected_authorities = {
        "development": (
            "run.integration.branch",
            "run.integration.integration_head_sha",
        ),
        "production": ("refs/heads/main", "promotion.verified_main_sha"),
    }
    if source_policy_protocol == "dual-branch/1":
        expected_authorities["development"] = (
            "refs/heads/development",
            "promotion.verified_development_sha",
        )
    expected_ref, expected_sha = expected_authorities[expected_stage]
    if match is None:
        return None, [
            f"{expected_stage} Source policy must use the closed "
            "stage=<stage>; ref=<authority>; sha=<authority> format"
        ]
    policy_stage, policy_ref, policy_sha = match.groups()
    if (
        policy_stage != expected_stage
        or policy_ref != expected_ref
        or policy_sha != expected_sha
    ):
        return None, [
            f"{expected_stage} Source policy must be stage={expected_stage}; "
            f"ref={expected_ref}; sha={expected_sha}"
        ]
    return (
        SourcePolicyAuthority(
            stage=expected_stage, ref=expected_ref, sha=expected_sha
        ),
        [],
    )


def parse_release_targets(
    architecture_text: str,
) -> tuple[ReleaseTargetContract, list[str]]:
    """Return the normalized release identity contract and all findings."""

    findings: list[str] = []
    section, section_findings = _section(architecture_text)
    findings.extend(section_findings)
    if section is None:
        return ReleaseTargetContract((), (), None), findings
    marker_protocol, marker_findings = _release_marker_protocol(section)
    findings.extend(marker_findings)

    inventory_matches = list(
        re.finditer(
            rf"^{re.escape(EXPECTED_PREFIX)}\s*(.*?)\s*$",
            section,
            re.MULTILINE | re.IGNORECASE,
        )
    )
    if len(inventory_matches) != 1:
        findings.append(
            "architecture: Release Targets must contain exactly one expected "
            "deployable-surface inventory"
        )
        return ReleaseTargetContract((), (), None, marker_protocol), findings

    inventory = inventory_matches[0].group(1).strip()
    none_match = re.fullmatch(r"none\s*(?:—|-)\s*(.+)", inventory, re.I)
    explicit_none_reason: str | None = None
    expected_values: list[str] = []
    if none_match:
        explicit_none_reason = none_match.group(1).strip()
        if not _meaningful(explicit_none_reason, minimum=15):
            findings.append(
                "architecture: explicit none deployable-surface inventory requires "
                "a concrete reason"
            )
    else:
        expected_values = [value.strip() for value in inventory.split(",") if value.strip()]
        duplicates = sorted(
            value for value, count in Counter(expected_values).items() if count > 1
        )
        if duplicates:
            findings.append(
                "architecture: duplicate expected deployable surfaces: "
                + ", ".join(duplicates)
            )
        if not expected_values:
            findings.append("architecture: expected surface inventory is empty")
        invalid = sorted(value for value in expected_values if not KEBAB_RE.fullmatch(value))
        if invalid:
            findings.append(
                "architecture: expected surfaces use lowercase kebab-case IDs: "
                + ", ".join(invalid)
            )

    headings = list(TARGET_HEADING_RE.finditer(section))
    targets: list[ReleaseTarget] = []
    seen_ids: set[str] = set()
    expected = set(expected_values)
    for index, heading in enumerate(headings):
        target_id = heading.group(1).strip()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        block = section[heading.end() : end]
        fields, duplicates = _field_rows(block)
        if not KEBAB_RE.fullmatch(target_id):
            findings.append(f"architecture: invalid release-target ID {target_id!r}")
        if target_id in seen_ids:
            findings.append(f"architecture: duplicate release-target ID {target_id!r}")
        seen_ids.add(target_id)
        if duplicates:
            findings.append(
                f"architecture: release target {target_id!r} has duplicate fields: "
                + ", ".join(duplicates)
            )
        missing = [field for field in FIELDS if field.casefold() not in fields]
        if missing:
            findings.append(
                f"architecture: release target {target_id!r} is missing fields: "
                + ", ".join(missing)
            )
            continue
        empty = [field for field in FIELDS if not fields[field.casefold()]]
        if empty:
            findings.append(
                f"architecture: release target {target_id!r} has empty fields: "
                + ", ".join(empty)
            )
            continue
        placeholder_fields = [
            field
            for field in FIELDS
            if PLACEHOLDER_RE.search(fields[field.casefold()])
        ]
        if placeholder_fields:
            findings.append(
                f"architecture: release target {target_id!r} has placeholder fields: "
                + ", ".join(placeholder_fields)
            )

        surface = fields["surface"]
        surface_class = fields["surface class"].casefold()
        public_discoverability = fields["public discoverability"].casefold()
        suffix = fields["surface suffix"]
        release_name = fields["release name"]
        provider = fields["provider"]
        stage = fields["stage"].casefold()
        source_policy = fields["source policy"]
        artifact_kind = fields["artifact kind"]
        if not KEBAB_RE.fullmatch(surface):
            findings.append(
                f"architecture: release target {target_id!r} has invalid surface {surface!r}"
            )
        if surface_class not in SURFACE_CLASSES:
            findings.append(
                f"architecture: release target {target_id!r} has invalid Surface class {fields['surface class']!r}"
            )
        if public_discoverability not in DISCOVERABILITY_VALUES:
            findings.append(
                f"architecture: release target {target_id!r} has invalid Public discoverability {fields['public discoverability']!r}"
            )
        elif (
            public_discoverability == "yes"
            and surface_class not in DISCOVERABLE_SURFACE_CLASSES
        ):
            findings.append(
                f"architecture: release target {target_id!r} Public discoverability=yes requires a discoverable Surface class, not {fields['surface class']!r}"
            )
        if expected and surface not in expected:
            findings.append(
                f"architecture: release target {target_id!r} names unexpected surface "
                f"{surface!r}"
            )
        if explicit_none_reason is not None:
            findings.append(
                "architecture: none deployable-surface inventory has target "
                f"{target_id!r}"
            )
        if not KEBAB_RE.fullmatch(suffix):
            findings.append(
                f"architecture: release target {target_id!r} surface suffix "
                f"{suffix!r} is not lowercase kebab-case"
            )
        if not KEBAB_RE.fullmatch(release_name):
            findings.append(
                f"architecture: release target {target_id!r} release name "
                f"{release_name!r} is not lowercase kebab-case"
            )
        if not _meaningful(provider, minimum=2):
            findings.append(
                f"architecture: release target {target_id!r} has invalid Provider"
            )
        if not _meaningful(artifact_kind, minimum=3):
            findings.append(
                f"architecture: release target {target_id!r} has invalid Artifact kind"
            )
        invalid_descriptive = sorted(
            field
            for field in DESCRIPTIVE_FIELDS
            if not _meaningful(fields[field], minimum=8)
        )
        if invalid_descriptive:
            findings.append(
                f"architecture: release target {target_id!r} has incomplete fields: "
                + ", ".join(invalid_descriptive)
            )
        if stage not in {"development", "production"}:
            findings.append(
                f"architecture: release target {target_id!r} has invalid stage "
                f"{fields['stage']!r}"
            )
        _source_authority, source_findings = parse_source_policy(
            source_policy,
            expected_stage=stage,
            source_policy_protocol=marker_protocol,
        )
        findings.extend(
            f"architecture: release target {target_id!r} {item}"
            for item in source_findings
        )
        availability = fields["availability signal"].casefold()
        if "smoke" not in availability and "acceptance" not in availability:
            findings.append(
                f"architecture: release target {target_id!r} availability must name "
                "a smoke or acceptance check"
            )

        targets.append(
            ReleaseTarget(
                target_id=target_id,
                surface=surface,
                surface_class=surface_class,
                public_discoverability=public_discoverability,
                surface_suffix=suffix,
                release_name=release_name,
                provider=provider,
                stage=stage,
                source_policy=source_policy,
                artifact_kind=artifact_kind,
                signing_requirement=fields["signing requirement"],
                channel=fields["exact channel / track"],
                approval_path=fields[
                    "submission / promotion / review / manual approval path"
                ],
                availability_signal=fields["availability signal"],
                rollout=fields["rollout"],
                recovery=fields["rollback / forward-fix"],
                source_policy_protocol=marker_protocol,
            )
        )

    if expected and not headings:
        findings.append(
            "architecture: every expected deployable surface requires release targets"
        )

    by_surface_stage: dict[tuple[str, str], ReleaseTarget] = {}
    name_owner: dict[str, str] = {}
    for target in targets:
        pair = (target.surface, target.stage)
        if pair in by_surface_stage:
            findings.append(
                f"architecture: surface {target.surface!r} has duplicate "
                f"{target.stage} targets"
            )
        else:
            by_surface_stage[pair] = target
        owner = name_owner.setdefault(target.release_name, target.surface)
        if owner != target.surface:
            findings.append(
                f"architecture: release name {target.release_name!r} is reused by "
                f"{owner!r} and {target.surface!r}"
            )

    for surface in sorted(expected):
        missing_stages = [
            stage
            for stage in ("development", "production")
            if (surface, stage) not in by_surface_stage
        ]
        if missing_stages:
            findings.append(
                f"architecture: expected surface {surface!r} is missing "
                + " and ".join(missing_stages)
                + " release targets"
            )
            continue
        development = by_surface_stage[(surface, "development")]
        production = by_surface_stage[(surface, "production")]
        if development.surface_suffix != production.surface_suffix:
            findings.append(
                f"architecture: surface {surface!r} development and production "
                "targets must use the same surface suffix"
            )
        if development.surface_class != production.surface_class:
            findings.append(
                f"architecture: surface {surface!r} development and production targets must use the same Surface class"
            )
        if development.public_discoverability != production.public_discoverability:
            findings.append(
                f"architecture: surface {surface!r} development and production targets must use the same Public discoverability value"
            )
        if production.release_name.endswith("-prod"):
            findings.append(
                f"architecture: production release {production.release_name!r} "
                "must not end in -prod"
            )
        if (
            not production.release_name.endswith(f"-{production.surface_suffix}")
            or development.release_name != f"{production.release_name}-dev"
        ):
            findings.append(
                f"architecture: surface {surface!r} release names are not a "
                f"canonical {production.surface_suffix!r} development/production pair"
            )

    return (
        ReleaseTargetContract(
            tuple(expected_values),
            tuple(targets),
            explicit_none_reason,
            marker_protocol,
        ),
        sorted(set(findings)),
    )
