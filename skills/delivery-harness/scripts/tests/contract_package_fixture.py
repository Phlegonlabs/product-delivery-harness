"""Build the genuine current UI3/DS4 fixture used by golden-path tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from eval_plan_contract import ACCEPTANCE_GATE_VERSION  # noqa: E402
from harness_schema import version_at_least  # noqa: E402


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


def current_package(root: Path, *, pin: str = "0.59.0") -> dict[str, Any]:
    """Return a validated ordinary-flow package and canonical paths."""

    saved_path = list(sys.path)
    if str(TESTS_DIR) not in sys.path:
        sys.path.insert(0, str(TESTS_DIR))
    try:
        import test_contract_source_binding as contract_fixture
    finally:
        sys.path[:] = saved_path

    fixture = object.__new__(contract_fixture.FrozenPackageJoinTests)
    plan, run, _view, _legacy = contract_fixture.FrozenPackageJoinTests.fixture(
        fixture, root, pin=pin
    )

    paths = {
        "prd": root / "docs/product/PRD.md",
        "architecture": root / "docs/product/architecture.md",
        "stack": root / "docs/product/stack-decisions.md",
        "ui": root / "docs/design/ui-design.md",
        "target": next(
            Path(root / row["location"])
            for row in plan["sources"]
            if row["kind"] == "approved ui target"
        ),
        "design_markdown": root / "docs/design/design-system.md",
        "design_json": root / "docs/design/design-system.json",
        "preview": root / "docs/design/design-system-preview.html",
    }
    design_json_id = next(
        row["id"] for row in plan["sources"] if row["kind"] == "design system json"
    )
    registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
    ds_trace_id = next(
        rule for rule in registry.get("signatureRules", []) if isinstance(rule, str)
    )
    if not any(trace.get("id") == ds_trace_id for trace in plan["traces"]):
        plan["traces"].append(
            {
                "id": ds_trace_id,
                "source_ids": [design_json_id],
                "priority": "must",
                "requirement": "Apply the registered design-system signature rule",
                "disposition": "planned",
                "rationale": None,
            }
        )
    for surface in plan["ui_surfaces"]:
        if ds_trace_id not in surface["trace_ids"]:
            surface["trace_ids"].append(ds_trace_id)

    plan["security_review"] = {
        "status": "required",
        "skill_slot": "code_security_verification",
        "reason": None,
    }
    from test_graph_orchestration import add_security_review

    add_security_review(plan)
    for mission in plan["missions"]:
        mission["write_scope"] = ["docs/README.md"]
        if ds_trace_id not in mission["trace_ids"]:
            mission["trace_ids"].append(ds_trace_id)
        for task in mission["tasks"]:
            task["write_scope"] = ["docs/README.md"]
            if ds_trace_id not in task["trace_ids"]:
                task["trace_ids"].append(ds_trace_id)
            for acceptance in task["acceptance_matrix"]:
                if ds_trace_id not in acceptance["trace_ids"]:
                    acceptance["trace_ids"].append(ds_trace_id)
    for node in plan["graph"]["nodes"]:
        if isinstance(node.get("review"), dict):
            node["review"]["scope"] = ["docs/README.md"]

    if version_at_least(pin, ACCEPTANCE_GATE_VERSION):
        add_acceptance_chain(plan, root)

    return {"plan": plan, "run": run, "paths": paths}


def add_acceptance_chain(plan: dict[str, Any], root: Path) -> None:
    """Freeze the delivery-acceptance source and its gate chain, as 0.79.0 pins require.

    The contract binds the frozen PRD hash; the `delivery-acceptance` gate names
    the observed Python, the installed checker and the contract hash; the graph
    routes every broad final gate through it to `final-closeout` on pass only.
    """

    prd_row = next(row for row in plan["sources"] if row["kind"] == "prd")
    prd_bytes = (root / prd_row["location"]).read_bytes()
    contract_path = root / "docs/verification/delivery-acceptance.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_bytes = (json.dumps({"schema": "delivery-acceptance/1", "prd_sha256": hashlib.sha256(prd_bytes).hexdigest(),
                                  "tests": []}, indent=2) + "\n").encode("utf-8")
    contract_path.write_bytes(contract_bytes)
    contract_row = dict(prd_row, id=f"SRC-{len(plan['sources'])}", kind="delivery acceptance",
                        location="docs/verification/delivery-acceptance.json",
                        content_sha256=hashlib.sha256(contract_bytes).hexdigest(), notes="frozen acceptance contract")
    plan["sources"].append(contract_row)
    scripts = Path(__file__).resolve().parent.parent
    plan["final_gates"].append({
        "id": "delivery-acceptance", "cwd": ".", "pass_signal": "exit 0",
        "execution": {"parallel_safe": False, "resources": [], "isolation": "host"},
        "argv": [sys.executable, str(scripts / "check_delivery_acceptance.py"), "--repo-root", ".",
                 "--prd", prd_row["location"], "--contract", contract_row["location"],
                 "--contract-sha256", contract_row["content_sha256"],
                 "--results", "docs/verification/delivery-results.json", "--candidate-from-head"],
    })
    plan["final_gates"].append({
        "id": "final-closeout", "cwd": ".", "argv": ["tool", "final-closeout"], "pass_signal": "exit 0",
        "execution": {"parallel_safe": False, "resources": [], "isolation": "host"},
    })
    broad_nodes = [node["id"] for node in plan["graph"]["nodes"]
                   if node.get("kind") == "verifier" and node.get("executor") == "local_command"
                   and node.get("ref") in {gate["id"] for gate in plan["final_gates"]} - {"delivery-acceptance", "final-closeout"}]
    for node_id, ref in (("N-ACCEPTANCE-GATE", "delivery-acceptance"), ("N-FINAL-CLOSEOUT", "final-closeout")):
        plan["graph"]["nodes"].append({"id": node_id, "kind": "verifier", "ref": ref, "executor": "local_command",
                                       "allowed_outcomes": ["pass", "blocked"], "max_attempts": 2, "runtime": None})
    edges = [(before, "N-ACCEPTANCE-GATE") for before in broad_nodes] + [("N-ACCEPTANCE-GATE", "N-FINAL-CLOSEOUT")]
    for before, after in edges:
        plan["graph"]["edges"].append({"id": f"E-{before[2:]}-{after[2:]}", "kind": "dependency", "from": before, "to": after,
                                       "on_outcomes": ["pass"], "max_traversals": None})
