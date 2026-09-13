#!/usr/bin/env python3
"""Opt-in golden-path E2E: the real CLI spine over one frozen product package.

CI enables this test explicitly. Run it locally with:

    HARNESS_GOLDEN_PATH=1 python -m unittest discover \
        -s skills/delivery-harness/scripts/tests \
        -p "test_golden_path.py" -v

The per-component suites each stay green while the four skills drift apart;
this test walks the documented spine in order against one synthetic package —
`new_run.py` generating RUN from PLAN, `validate_harness_plan.py` re-running
the frozen source joins including the sibling skill's core-package and wireframe checkers,
and `validate_result.py` validating a returned graph payload with `--repo-root`
— so cross-skill contract drift surfaces here as one red test.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_run  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    git,
    init_repo,
    manifest_markdown,
    wireframes_html,
)
from test_harness_manifest import valid_plan  # noqa: E402
from test_validate_node_result import running_result  # noqa: E402


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def frozen_source(
    identifier: str, kind: str, location: str, path: Path
) -> dict[str, object]:
    return {
        "id": identifier,
        "kind": kind,
        "location": location,
        "owner": "product",
        "status": "frozen",
        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_revision": None,
        "staged_revision": None,
        "notes": "golden-path frozen source",
    }


def approved_prd() -> str:
    headings = (
        "At a Glance",
        "Problem Statement",
        "Goals",
        "Non-Goals",
        "Users and Personas",
        "User Journeys",
    )
    text = "# PRD: Golden Path\n\n" + "\n".join(
        f"## {heading}\nFilled." for heading in headings
    )
    return text + """
## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-001 | Complete fixture | Must | Completion is observable |
## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-002 |
## UX Requirements
Filled.
## Data and Integration Requirements
Filled.
## Data and Trust
Data and Trust Gate: not_required — synthetic data only, decided by Owner
## AI and Automation
AI and Automation Gate: not_required — no AI, decided by Owner
## Business Rules
Filled.
## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |
| Partner Channel Gate | not_required | No outside sellers | approved | n/a |
## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Completion | Completed | 0 | 1 | Test run | Test result | Owner |
## Risks
Filled.
## Assumptions
| Assumption | Impact if wrong | Validation | Owner | Decision date | Status |
| --- | --- | --- | --- | --- | --- |
## Open Questions
| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |
| --- | --- | --- | --- | --- | --- |
## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Complete fixture | integration | Yes | PRD-001 | Completion observed |
| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |
## Builder UX Direction Decision
Decision owner: Owner
Motion Need Gate:
| UI scope | Gate | Purpose and trigger | Decision source | Reduced-motion fallback |
| --- | --- | --- | --- | --- |
| UI-001 | not_required | Static fixture | Owner | Static fixture |
## Product Definition Decisions
### Research Gate
Research Gate: go — assessed 2026-09-12, decided by Owner
<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: new
- Package revision: PD-R1
- Decision: approved
- Decision owner: Owner
- Decided on: 2026-09-12
- Approved artifacts: PRD.md, architecture.md, stack-decisions.md
- Market research reconciliation: completed
- Stack Decision Checkpoint: approved
- Accepted assumptions and non-blocking questions: none
- Blocking items: none
<!-- product-definition-approval:end -->
<!-- ui-surface-contract:start -->
## UI Surface Contract

### UI-001 — Home

- `route`: /home
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
<!-- ui-surface-contract:end -->
"""


def approved_architecture() -> str:
    headings = (
        "Architecture Summary",
        "Product Archetype",
        "System Context",
        "Component Architecture",
        "Data Model",
        "API and Interface Contracts",
        "Workflow and Data Flow",
        "Auth, Permissions, and Security",
        "Data and Trust Architecture",
        "AI and Automation Architecture",
        "Integrations",
        "Deployment and Operations",
        "Observability",
        "Scaling and Reliability",
        "Technical Risks and Tradeoffs",
        "Architecture Trace Index",
    )
    return "# Architecture: Golden Path\n\n" + "\n".join(
        f"## {heading}\nFilled." for heading in headings
    )


def approved_stack() -> str:
    return """# Stack Decisions: Golden Path
<!-- stack-decision-checkpoint:start -->
## Stack Decision Checkpoint
- Decision: approved
- Decision owner: Owner
- Decided on: 2026-09-12
- Approved areas: frontend
- Delegated choices: none
- Open areas: none
<!-- stack-decision-checkpoint:end -->
### Coherent Options Presented
| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-FE-01 | Frontend | Fixture bundle | Synthetic test | Team ownership | approved |
| OPT-FE-02 | Frontend | Alternate bundle | Synthetic alternative | Team ownership | rejected |
## Frontend Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Deployment / runtime | Fixture runtime | Approved | Owner | Synthetic test | None |
| Rendering model | SPA | Approved | Owner | Synthetic test | None |
| Language | TypeScript | Approved | Owner | Synthetic test | None |
| Package manager | npm | Approved | Owner | Synthetic test | None |
| Framework | Fixture | Approved | Owner | Synthetic test | None |
| UI library | Fixture UI | Approved | Owner | Synthetic test | None |
| Component foundation | Fixture components | Approved | Owner | Synthetic test | None |
| Styling approach | Plain CSS | Approved | Owner | Synthetic test | None |
| Build tool | Fixture build | Approved | Owner | Synthetic test | None |
| Routing and data | Fixture router | Approved | Owner | Synthetic test | None |
| Testing | Fixture tests | Approved | Owner | Synthetic test | None |
"""


@unittest.skipUnless(
    os.environ.get("HARNESS_GOLDEN_PATH"),
    "set HARNESS_GOLDEN_PATH=1 to run the golden-path E2E",
)
class GoldenPathTests(unittest.TestCase):
    def test_frozen_package_walks_the_real_cli_spine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repo(root, "README.md")

            product = root / "docs" / "product"
            product.mkdir(parents=True)
            prd_path = product / "PRD.md"
            prd_path.write_text(approved_prd(), encoding="utf-8")
            wireframes_path = product / "wireframes.html"
            wireframes_path.write_text(
                wireframes_html(
                    [{"id": "UI-001", "route": "/home", "states": ["ready"]}],
                    schema="wireframes/3",
                    viewports=(390, 768, 1200),
                ),
                encoding="utf-8",
            )
            architecture_path = product / "architecture.md"
            architecture_path.write_text(approved_architecture(), encoding="utf-8")
            stack_path = product / "stack-decisions.md"
            stack_path.write_text(approved_stack(), encoding="utf-8")

            plan = valid_plan()
            plan["security_review"] = {
                "status": "not_applicable",
                "skill_slot": "code_security_verification",
                "reason": "synthetic contract fixture has no implementation candidate",
            }
            plan["ui_surfaces"] = [
                {
                    "id": "UI-001",
                    "trace_ids": ["REQ-001"],
                    "route": "/home",
                    "breakpoints": ["390", "768", "1200"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                }
            ]
            plan["sources"] = [
                frozen_source(
                    "SRC-001", "prd", "docs/product/PRD.md", prd_path
                ),
                frozen_source(
                    "SRC-002",
                    "architecture",
                    "docs/product/architecture.md",
                    architecture_path,
                ),
                frozen_source(
                    "SRC-STACK",
                    "stack decisions",
                    "docs/product/stack-decisions.md",
                    stack_path,
                ),
                frozen_source(
                    "SRC-WIREFRAMES",
                    "wireframe",
                    "docs/product/wireframes.html",
                    wireframes_path,
                ),
            ]
            git(root, "add", "docs")
            git(root, "commit", "-qm", "freeze product package")
            head = git(root, "rev-parse", "HEAD")

            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown(
                    "## Harness Plan Manifest", "harness_plan", plan
                ),
                encoding="utf-8",
            )

            generated = run_cli(
                str(SCRIPTS_DIR / "new_run.py"),
                "--plan",
                str(plan_path),
                "--run-id",
                "RUN-GOLDEN",
                "--branch",
                "refs/heads/run/golden-path",
                "--out",
                str(root / "RUN.md"),
            )
            self.assertEqual(0, generated.returncode, generated.stderr)
            run_path = root / "RUN.md"
            self.assertTrue(run_path.is_file())

            validated = run_cli(
                str(SCRIPTS_DIR / "validate_harness_plan.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--repo-root",
                str(root),
                "--prd",
                str(prd_path),
                "--wireframes",
                str(wireframes_path),
            )
            self.assertEqual(
                0,
                validated.returncode,
                validated.stdout + validated.stderr,
            )
            self.assertEqual("PASS", json.loads(validated.stdout)["status"])

            run = load_run(run_path)
            run["integration"]["batch_base_sha"] = head
            node_result = running_result(plan, run)
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            node_path = root / "node-result.json"
            node_path.write_text(
                json.dumps({"node_result": node_result}), encoding="utf-8"
            )

            merged = run_cli(
                str(SCRIPTS_DIR / "validate_result.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--node-result",
                str(node_path),
                "--repo-root",
                str(root),
            )
            self.assertEqual(0, merged.returncode, merged.stdout)
            payload = json.loads(merged.stdout)
            self.assertEqual("PASS", payload["status"])
            self.assertEqual([], payload["errors"])


if __name__ == "__main__":
    unittest.main()
