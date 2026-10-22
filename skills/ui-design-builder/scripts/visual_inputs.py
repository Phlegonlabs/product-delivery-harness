#!/usr/bin/env python3
"""Assemble source-bound visual inputs for an existing frontend task packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import check_ui_design_contract as contract
from review_evidence import HIFI_MANIFEST_RE, MAX_BYTES, read_identity, safe_path


def _identity(root: Path, relative: str) -> dict[str, str]:
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("visual source is missing or exceeds the read limit")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build_visual_inputs(root: Path, ui_design: str, stage: str) -> str:
    """Return pointers to current visual truth, never an approval or new copy."""
    if stage not in {"direction", "hifi", "implementation"}:
        raise ValueError("stage must be direction, hifi or implementation")
    authority = _identity(root, ui_design)
    text = read_identity(root, authority).decode("utf-8")
    view, problems = contract.parse_ui_contract_view(text)
    if problems:
        raise ValueError("; ".join(problems))
    active = contract.active_text(text)
    style = contract._section(active, "## Style Integration") or ""
    selected = view["selected_direction"]
    if stage != "direction" and (not selected or not selected.startswith("VD-")):
        raise ValueError("selected direction is required after direction exploration")
    selected_id = selected.split()[0].rstrip(",;") if selected else None
    target = view["approved_target"]
    if stage == "implementation" and target is None:
        raise ValueError("implementation requires the approved target identity and scope")

    inputs = {authority["path"]: authority}

    def retain(binding):
        if not binding:
            raise ValueError("required visual source identity is missing")
        identity = {key: binding[key] for key in ("path", "sha256")}
        data = read_identity(root, identity)
        if identity["path"] in inputs and inputs[identity["path"]] != identity:
            raise ValueError("visual sources disagree about one file identity")
        inputs[identity["path"]] = identity
        return data

    for key in ("prd", "architecture", "stack"):
        retain(view["source_identities"][key])

    screens = []
    comparison = contract._section(style, "### Direction comparison") or ""
    for row in contract._table_rows(comparison):
        if len(row) != 8 or row[0] == "Direction":
            continue
        if stage != "direction" and row[0] != selected_id:
            continue
        binding = contract._source_identity(row[6])
        retain(binding)
        screens.append(binding)
    if stage != "direction" and not screens:
        raise ValueError("selected direction has no retained screen captures")

    hifi = target if stage == "implementation" else view["source_identities"]["hifi"]
    if hifi:
        data = retain(hifi)
        matches = HIFI_MANIFEST_RE.findall(data.decode("utf-8"))
        if len(matches) != 1:
            raise ValueError("HiFi source requires exactly one closed manifest")
        manifest = json.loads(matches[0])
        if not isinstance(manifest, dict) or manifest.get("schema") != "ui-hifi/2":
            raise ValueError("HiFi source requires a ui-hifi/2 manifest")
        documents = contract._hifi_bundle_documents(safe_path(root, hifi["path"]), data.decode("utf-8"), manifest)
        for name in documents:
            if name != "index.html":
                relative = str(Path(hifi["path"]).parent / name).replace("\\", "/")
                retain(_identity(root, relative))

    pair = view["design_system_pair"]
    if stage == "implementation" and view["gate_decision"] == "required" and not pair:
        raise ValueError("implementation requires the current design-system pair")
    if stage == "implementation" and pair:
        retain(pair["markdown"])
        registry = json.loads(retain(pair["registry"]).decode("utf-8"))
        if registry.get("schema") == "design-system/4":
            preview = str(Path(pair["registry"]["path"]).parent / "design-system-preview.html").replace("\\", "/")
            retain(_identity(root, preview))

    def label(binding):
        return binding["path"] + " @ sha256:" + binding["sha256"]

    rows = ["Visual inputs:", "- Stage: " + stage,
            "- Authority: " + label(authority),
            "- Direction mode: " + (view["direction_mode"] or "pending"),
            "- Selected direction: " + (selected or "pending"),
            "- Approved target: " + (label(target) if target else "pending"),
            "- Scope: " + (json.dumps(target["scope"], ensure_ascii=False, sort_keys=True)
                            if target else "approved PRD UI scope and current direction-study cases"),
            "- Screens to inspect: " + ("; ".join(label(item) for item in screens) or "pending direction studies"),
            "- Fonts: read Style Integration, Candidate theme and Platform rules; inspect the bound HiFi font declarations, weights and language fallbacks.",
            "- Assets: read Motion And Media Intent and every bound HiFi page; use its approved inline images, icons, media and font bytes.",
            "- Visual features: read the Design Brief, selected direction rationale and Candidate theme; retain their concrete composition, typography, material and motion choices.",
            "- Source files:"]
    rows.extend("  - " + label(binding) for binding in inputs.values())
    rows.extend([
        "- Author read evidence: report the paths/hashes and the captures, font declarations, assets and visual features actually inspected before editing.",
        "- Missing or uninspectable required visual material blocks its dependent edit; do not invent replacements or claim visual inspection from HTML text alone.",
        "- Run the existing stage approval/source checks and final packet byte-budget check. This block grants no approval, write, download or model authority.",
    ])
    return "\n".join(rows) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--ui-design", required=True)
    parser.add_argument("--stage", choices=("direction", "hifi", "implementation"), required=True)
    options = parser.parse_args(argv)
    try:
        print(build_visual_inputs(options.repo_root.resolve(), options.ui_design, options.stage), end="")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        parser.exit(2, "visual inputs blocked: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
