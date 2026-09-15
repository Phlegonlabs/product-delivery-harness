#!/usr/bin/env python3
"""Validate pinned external UI-profile skill dependencies without installing."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from check_skill_bindings import hash_skill


REQUIRED_PROFILES = (
    "ui_design",
    "frontend_implementation",
    "authorized_ui_quality",
)
PIN_RE = re.compile(r"^[0-9a-f]{64}$")
SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_COMPATIBILITY: dict[str, dict[str, Any]] = {
    "frontend-design": {
        "allowed_uses": ["visual_direction", "frontend_authoring"],
        "forbidden_claims": [
            "compilation_mode",
            "conformance_mode",
            "read_only_review",
        ],
    },
    "impeccable": {
        "allowed_uses": ["authorized_ui_quality_review"],
        "execution": "explicit_authorization_required",
        "side_effects": [
            "subagents",
            "browser",
            "local_server",
            "snapshot_write",
            "optional_binary_download",
        ],
        "forbidden_roles": ["harness_read_only_reviewer"],
    },
}
EXPECTED_PROFILE_SKILLS = {
    "ui_design": {"frontend-design"},
    "frontend_implementation": {"frontend-design"},
    "authorized_ui_quality": {"impeccable"},
}
REQUIRED_ACQUISITION: dict[str, dict[str, Any]] = {
    "frontend-design": {
        "source_locator": "https://github.com/anthropics/skills/tree/main/skills/frontend-design",
        "install": {
            "kind": "codex_skill_installer",
            "request": (
                "Install frontend-design from "
                "https://github.com/anthropics/skills/tree/main/skills/frontend-design"
            ),
        },
    },
    "impeccable": {
        "source_locator": "https://github.com/pbakaus/impeccable",
        "install": {"kind": "command", "argv": ["npx", "impeccable", "install"]},
    },
}


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("dependency manifest must be a JSON object")
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if manifest.get("version") != 2:
        findings.append("manifest version must be 2")

    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict):
        return findings + ["manifest profiles must be an object"]

    for profile in REQUIRED_PROFILES:
        if profile not in profiles:
            findings.append(f"required profile is absent: {profile}")
    extra_profiles = sorted(set(profiles) - set(REQUIRED_PROFILES))
    if extra_profiles:
        findings.append("unexpected external dependency profiles: " + ", ".join(extra_profiles))

    pinned: dict[str, str] = {}
    for profile, dependencies in profiles.items():
        if not isinstance(dependencies, dict) or not isinstance(
            dependencies.get("skills"), list
        ):
            findings.append(f"profile {profile!r} must contain a skills list")
            continue
        if not dependencies["skills"]:
            findings.append(f"profile {profile!r} has no dependencies")

        names: set[str] = set()
        for entry in dependencies["skills"]:
            if not isinstance(entry, dict):
                findings.append(f"profile {profile!r} contains a non-object dependency")
                continue
            name = entry.get("name")
            pin = entry.get("sha256")
            source = entry.get("source")
            if not isinstance(name, str) or not SKILL_NAME_RE.fullmatch(name):
                findings.append(f"profile {profile!r} contains an invalid skill name")
                continue
            if name in names:
                findings.append(f"profile {profile!r} duplicates dependency {name!r}")
            names.add(name)
            if source != "external":
                findings.append(
                    f"profile {profile!r} dependency {name!r} must declare source external"
                )
            expected_acquisition = REQUIRED_ACQUISITION.get(name)
            if expected_acquisition is not None and any(
                entry.get(field) != expected
                for field, expected in expected_acquisition.items()
            ):
                findings.append(
                    f"profile {profile!r} dependency {name!r} must declare its "
                    "approved source locator and install route"
                )
            if not isinstance(pin, str) or not PIN_RE.fullmatch(pin):
                findings.append(
                    f"profile {profile!r} dependency {name!r} has an invalid pin"
                )
                continue
            if name in pinned and pinned[name] != pin:
                findings.append(
                    f"dependency {name!r} has different pins across profiles"
                )
            pinned[name] = pin
            expected_compatibility = REQUIRED_COMPATIBILITY.get(name)
            if expected_compatibility is None:
                findings.append(
                    f"profile {profile!r} dependency {name!r} is not an approved external skill"
                )
            elif entry.get("compatibility") != expected_compatibility:
                findings.append(
                    f"profile {profile!r} dependency {name!r} has an incompatible "
                    "capability/side-effect contract"
                )
        expected_names = EXPECTED_PROFILE_SKILLS.get(profile)
        if expected_names is not None and names != expected_names:
            findings.append(
                f"profile {profile!r} must bind exactly: "
                + ", ".join(sorted(expected_names))
            )

    return findings


def locate_skill(
    name: str, skill_dirs: list[Path], bundled_skills_root: Path
) -> Path | None:
    for directory in skill_dirs:
        candidate = (directory / name).resolve()
        try:
            candidate.relative_to(bundled_skills_root.resolve())
        except ValueError:
            pass
        else:
            continue
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


def selected_profiles(requested: list[str], manifest: dict[str, Any]) -> list[str]:
    profiles = requested or list(REQUIRED_PROFILES)
    available = manifest.get("profiles", {})
    if not isinstance(available, dict):
        print("manifest profiles must be an object", file=sys.stderr)
        return 2
    return [profile for profile in profiles if isinstance(available.get(profile), dict)]


def check_dependencies(
    manifest: dict[str, Any],
    profiles: list[str],
    skill_dirs: list[Path],
    bundled_skills_root: Path,
) -> list[str]:
    findings = validate_manifest(manifest)
    available = manifest.get("profiles", {})
    for profile in profiles:
        dependencies = available.get(profile)
        if not isinstance(dependencies, dict):
            continue
        for entry in dependencies.get("skills", []):
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            pin = entry.get("sha256")
            if not isinstance(name, str) or not isinstance(pin, str):
                continue
            located = locate_skill(name, skill_dirs, bundled_skills_root)
            if located is None:
                findings.append(
                    f"{profile}: required skill {name!r} is missing from "
                    "the supplied skill directories"
                )
                continue
            try:
                current = hash_skill(located)
            except (OSError, ValueError) as exc:
                findings.append(
                    f"{profile}: required skill {name!r} cannot be hashed: {exc}"
                )
                continue
            if current != pin:
                findings.append(
                    f"{profile}: required skill {name!r} hash drifted "
                    f"(pinned {pin[:12]}..., installed {current[:12]}...)"
                )
    return findings


def default_skill_dirs(script: Path) -> list[Path]:
    candidates = [
        Path.home() / ".agents" / "skills",
    ]
    directories: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in directories:
            directories.append(resolved)
    return directories


def main(argv: list[str] | None = None) -> int:
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=script.parents[1] / "assets" / "external-skill-dependencies.json",
    )
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help="profile to check (repeatable; defaults to all required profiles)",
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        action="append",
        default=[],
        help="additional directory holding installed skills (repeatable)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="list profiles in the manifest",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"cannot read dependency manifest {args.manifest}: {error}", file=sys.stderr)
        return 2

    available = manifest.get("profiles", {})
    if args.list_profiles:
        if not isinstance(available, dict):
            print("manifest profiles must be an object", file=sys.stderr)
            return 2
        for profile in sorted(available):
            print(profile)
        return 0

    unknown = [profile for profile in args.profile if profile not in available]
    if unknown:
        for profile in unknown:
            print(f"unknown dependency profile: {profile}", file=sys.stderr)
        return 2

    skill_dirs = [path.resolve() for path in args.skill_dir] or default_skill_dirs(script)
    findings = check_dependencies(
        manifest,
        selected_profiles(args.profile, manifest),
        skill_dirs,
        script.parents[2],
    )
    for finding in findings:
        print(f"{args.manifest}: {finding}")
    if findings:
        return 1
    print("all required external skill dependencies are present and unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
