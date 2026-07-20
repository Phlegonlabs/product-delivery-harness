#!/usr/bin/env python3
"""Select targeted task and worker verifiers from observed changed files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

from harness_manifest import (
    ManifestError,
    load_plan,
    path_in_scopes,
    validate_plan,
    validate_scope_claim,
)


SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class VerifierSelectionError(ValueError):
    """Raised when verifier selection inputs are invalid."""


def canonical_changed_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise VerifierSelectionError("changed files must be non-empty strings")
    problem = validate_scope_claim(value)
    if problem is not None:
        raise VerifierSelectionError(f"invalid changed file {value!r}: {problem}")
    if value.endswith("/**"):
        raise VerifierSelectionError(
            f"invalid changed file {value!r}: changed files must be exact paths"
        )
    return value


def normalize_changed_files(values: Iterable[Any]) -> list[str]:
    changed_files = [canonical_changed_path(value) for value in values]
    if len(changed_files) != len(set(changed_files)):
        raise VerifierSelectionError("changed files must not contain duplicates")
    return sorted(changed_files)


def verifier_is_applicable(
    verifier: dict[str, Any], changed_files: Iterable[str]
) -> bool:
    selection = verifier.get("selection")
    if not isinstance(selection, dict) or selection.get("mode") in {None, "always"}:
        return True
    if selection.get("mode") != "changed_files":
        raise VerifierSelectionError("verifier selection mode is unsupported")
    scopes = selection.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise VerifierSelectionError("changed_files selection requires scopes")
    return any(path_in_scopes(path, scopes) for path in changed_files)


def applicable_targeted_verifiers(
    mission: dict[str, Any], changed_files: Iterable[Any]
) -> dict[str, Any]:
    observed_files = normalize_changed_files(changed_files)
    selected: list[dict[str, Any]] = []
    not_applicable: list[dict[str, Any]] = []
    task_ids: dict[str, set[str]] = {}
    worker_ids: set[str] = set()

    for task in mission.get("tasks", []):
        if not isinstance(task, dict) or task.get("replaced_by"):
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str):
            continue
        task_ids[task_id] = set()
        for verifier in task.get("verifiers", []):
            if not isinstance(verifier, dict) or not isinstance(verifier.get("id"), str):
                continue
            record = {
                "id": verifier["id"],
                "level": "task",
                "task_id": task_id,
            }
            if verifier_is_applicable(verifier, observed_files):
                task_ids[task_id].add(verifier["id"])
                selected.append(record)
            else:
                not_applicable.append(
                    {**record, "reason": "no_changed_file_in_scope"}
                )

    for verifier in mission.get("worker_verifiers", []):
        if not isinstance(verifier, dict) or not isinstance(verifier.get("id"), str):
            continue
        record = {"id": verifier["id"], "level": "worker", "task_id": None}
        if verifier_is_applicable(verifier, observed_files):
            worker_ids.add(verifier["id"])
            selected.append(record)
        else:
            not_applicable.append({**record, "reason": "no_changed_file_in_scope"})

    order = lambda item: (item["level"], item["task_id"] or "", item["id"])
    return {
        "changed_files": observed_files,
        "selected": sorted(selected, key=order),
        "not_applicable": sorted(not_applicable, key=order),
        "task_verifier_ids": {
            task_id: sorted(verifier_ids)
            for task_id, verifier_ids in sorted(task_ids.items())
        },
        "worker_verifier_ids": sorted(worker_ids),
        "metrics": {
            "considered": len(selected) + len(not_applicable),
            "selected": len(selected),
            "not_applicable": len(not_applicable),
        },
    }


def select_verifiers(
    plan: dict[str, Any],
    mission_id: str,
    changed_files: Iterable[Any],
    *,
    head_sha: str | None = None,
) -> dict[str, Any]:
    errors = validate_plan(plan)
    if errors:
        raise VerifierSelectionError("PLAN validation failed: " + "; ".join(errors))
    matches = [
        mission
        for mission in plan.get("missions", [])
        if isinstance(mission, dict) and mission.get("id") == mission_id
    ]
    if len(matches) != 1:
        raise VerifierSelectionError(f"mission {mission_id!r} is not uniquely defined")
    if head_sha is not None and not SHA_RE.fullmatch(head_sha):
        raise VerifierSelectionError("head SHA must be 40 or 64 lowercase hexadecimal characters")
    result = applicable_targeted_verifiers(matches[0], changed_files)
    return {
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "mission_id": mission_id,
        "head_sha": head_sha,
        **result,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select applicable task and worker verifiers from changed files."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--head-sha")
    parser.add_argument("--changed-file", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = select_verifiers(
            load_plan(args.plan),
            args.mission_id,
            args.changed_file,
            head_sha=args.head_sha,
        )
    except (ManifestError, OSError, VerifierSelectionError) as exc:
        print(
            json.dumps(
                {"status": "ERROR", "errors": [str(exc)]},
                sort_keys=True,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
