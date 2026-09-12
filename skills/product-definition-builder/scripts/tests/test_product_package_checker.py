import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import check_product_package  # noqa: E402


def valid_prd(*, mode: str = "new") -> str:
    return f"""# PRD: Fixture

## At a Glance
Fixture.
## Problem Statement
Problem.
## Goals
- Goal.
## Non-Goals
- None.
## Users and Personas
Users.
## User Journeys
Journey.
## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-001 | Complete the fixture | Must | Completion is observable |
## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-002 |
## UX Requirements
UX.
## Data and Integration Requirements
Data.
## Data and Trust
Data and Trust Gate: not_required — no personal or regulated data, decided by Owner
## AI and Automation
AI and Automation Gate: not_required — no AI or autonomous action, decided by Owner
## Business Rules
Rules.
## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |
| Partner Channel Gate | not_required | No outside sellers | approved | n/a |
## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |
## Risks
Risks.
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
## Product Definition Decisions
### Research Gate
Research Gate: go — assessed 2026-09-12, decided by Owner
<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: {mode}
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
"""


def valid_architecture() -> str:
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
    return "# Architecture: Fixture\n\n" + "\n".join(
        f"## {heading}\nFilled." for heading in headings
    )


def valid_stack(*, status: str = "Approved", decision: str = "approved") -> str:
    return f"""# Stack Decisions: Fixture

<!-- stack-decision-checkpoint:start -->
## Stack Decision Checkpoint
- Decision: {decision}
- Decision owner: Owner
- Decided on: 2026-09-12
- Approved areas: frontend
- Delegated choices: none
- Open areas: none
<!-- stack-decision-checkpoint:end -->

### Coherent Options Presented
| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-FE-01 | Frontend | React Router bundle | Interactive app | Team owns source | approved |
| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |

## Frontend Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Deployment / runtime | Cloudflare Workers | {status} | Owner decision | Fits deployment | None |
| Rendering model | SPA | {status} | Owner decision | Fits interactions | None |
| Language | TypeScript | {status} | Owner decision | Fits team | None |
| Package manager | npm | {status} | Owner decision | Existing standard | None |
| Framework | React Router | {status} | Owner decision | Fits the app | None |
| UI library | React | {status} | Owner decision | Fits framework | None |
| Component foundation | shadcn/ui owned source | {status} | Owner decision | Editable components | Own copied source |
| Styling approach | Tailwind CSS | {status} | Owner decision | Fits components | Token discipline |
| Build tool | Vite | {status} | Owner decision | Fits framework | None |
| Routing and data | React Router loaders | {status} | Owner decision | Typed route data | None |
| Testing | Vitest and Playwright | {status} | Owner decision | Covers required layers | None |
"""


class ProductPackageCheckerTests(unittest.TestCase):
    def validate(
        self,
        prd: str | None = None,
        architecture: str | None = None,
        stack: str | None = None,
        *,
        require_approved: bool = True,
    ) -> list[str]:
        return check_product_package.validate_texts(
            prd if prd is not None else valid_prd(),
            architecture if architecture is not None else valid_architecture(),
            stack if stack is not None else valid_stack(),
            require_filled=True,
            require_approved=require_approved,
        )

    def test_approved_package_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_recommended_or_provisional_stack_cannot_pass_approval(self) -> None:
        for status in ("Recommended", "Provisional"):
            problems = self.validate(stack=valid_stack(status=status))
            self.assertTrue(any("owner approval is required" in item for item in problems))

        self.assertEqual(
            [],
            self.validate(
                stack=valid_stack(status="Recommended"), require_approved=False
            ),
        )

    def test_missing_or_unapproved_product_decision_fails(self) -> None:
        missing = valid_prd().replace(
            "<!-- product-definition-approval:start -->",
            "<!-- missing-product-approval:start -->",
        )
        self.assertTrue(any("marker pair" in item for item in self.validate(prd=missing)))

        blocked = valid_prd().replace("- Decision: approved", "- Decision: blocked")
        self.assertTrue(
            any("Decision must be approved" in item for item in self.validate(prd=blocked))
        )

    def test_research_gate_must_be_resolved_before_approval(self) -> None:
        clarify = valid_prd().replace(
            "Research Gate: go", "Research Gate: clarify"
        )
        self.assertTrue(
            any("Research Gate is 'clarify'" in item for item in self.validate(prd=clarify))
        )

        missing = valid_prd().replace("Research Gate: go — assessed 2026-09-12, decided by Owner", "")
        self.assertTrue(any("missing Research Gate" in item for item in self.validate(prd=missing)))

    def test_stack_checkpoint_must_be_approved(self) -> None:
        problems = self.validate(stack=valid_stack(decision="revision_requested"))
        self.assertTrue(any("Decision must be approved" in item for item in problems))

    def test_approved_layers_require_the_option_record(self) -> None:
        stack = valid_stack()
        option_start = stack.index("### Coherent Options Presented")
        option_end = stack.index("## Frontend Technology Decision")
        stack = stack[:option_start] + stack[option_end:]
        self.assertTrue(
            any(
                "Approved layers require a non-empty Coherent Options Presented table"
                in item
                for item in self.validate(stack=stack)
            )
        )

    def test_approved_area_requires_two_coherent_options(self) -> None:
        stack = valid_stack().replace(
            "| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |\n",
            "",
        )
        self.assertTrue(
            any("require two or three coherent options" in item for item in self.validate(stack=stack))
        )

    def test_frontend_stack_requires_component_and_styling_layers(self) -> None:
        stack = valid_stack().replace(
            "| Component foundation | shadcn/ui owned source | Approved | Owner decision | Editable components | Own copied source |\n",
            "",
        ).replace(
            "| Styling approach | Tailwind CSS | Approved | Owner decision | Fits components | Token discipline |\n",
            "",
        )
        problems = self.validate(stack=stack)
        self.assertTrue(any("component foundation" in item for item in problems))
        self.assertTrue(any("styling approach" in item for item in problems))

    def test_stack_layer_table_requires_all_six_columns(self) -> None:
        stack = valid_stack().replace(
            "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |",
            "| Layer | Selection | Status |",
        )
        self.assertTrue(
            any("exact six-column layer table" in item for item in self.validate(stack=stack))
        )

    def test_decision_owners_must_be_human(self) -> None:
        prd = valid_prd().replace("- Decision owner: Owner", "- Decision owner: AI")
        self.assertTrue(any("must name a human owner" in item for item in self.validate(prd=prd)))

        stack = valid_stack().replace("- Decision owner: Owner", "- Decision owner: Codex")
        self.assertTrue(any("must name a human owner" in item for item in self.validate(stack=stack)))

    def test_duplicate_approval_fields_are_rejected(self) -> None:
        prd = valid_prd().replace(
            "- Decision: approved", "- Decision: approved\n- Decision: approved", 1
        )
        self.assertTrue(any("duplicate field 'decision'" in item for item in self.validate(prd=prd)))

        stack = valid_stack().replace(
            "- Open areas: none", "- Open areas: none\n- Open areas: none"
        )
        self.assertTrue(any("duplicate field 'open areas'" in item for item in self.validate(stack=stack)))

    def test_blocking_open_question_fails(self) -> None:
        prd = valid_prd().replace(
            "| --- | --- | --- | --- | --- | --- |\n## Test Obligations",
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Which vendor? | Changes data handling | Owner | 2026-09-20 | Yes | Open |\n"
            "## Test Obligations",
        )
        self.assertTrue(
            any("blocking open question" in item for item in self.validate(prd=prd))
        )

    def test_blocked_data_or_ai_gate_fails(self) -> None:
        for gate in ("Data and Trust Gate", "AI and Automation Gate"):
            prd = valid_prd().replace(f"{gate}: not_required", f"{gate}: blocked")
            self.assertTrue(any(f"{gate} is blocked" in item for item in self.validate(prd=prd)))

    def test_trust_and_ai_gates_require_reason_and_owner(self) -> None:
        prd = valid_prd().replace(
            "Data and Trust Gate: not_required — no personal or regulated data, decided by Owner",
            "Data and Trust Gate: not_required",
        )
        self.assertTrue(any("missing complete Data and Trust Gate" in item for item in self.validate(prd=prd)))

    def test_commercial_gates_require_owner_resolution(self) -> None:
        prd = valid_prd().replace(
            "| Partner Channel Gate | not_required | No outside sellers | approved | n/a |",
            "| Partner Channel Gate | not_required | No outside sellers | recommended | n/a |",
        )
        self.assertTrue(
            any("Partner Channel Gate remains 'recommended'" in item for item in self.validate(prd=prd))
        )

    def test_ui_packages_require_builder_direction_and_resolved_motion(self) -> None:
        ui_contract = """
<!-- ui-surface-contract:start -->
## UI Surface Contract
### UI-001 — Home
- `route`: /home
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
<!-- ui-surface-contract:end -->
"""
        prd = valid_prd() + ui_contract
        self.assertTrue(any("missing Builder UX Direction" in item for item in self.validate(prd=prd)))

        broken_contract = ui_contract.replace("- `route`: /home\n", "")
        prd = valid_prd() + broken_contract
        self.assertTrue(any("requires exactly one `route` anchor" in item for item in self.validate(prd=prd)))

        builder = """
## Builder UX Direction Decision
Motion Need Gate:
| UI scope | Gate | Purpose and trigger | Decision source | Reduced-motion fallback |
| --- | --- | --- | --- | --- |
| UI-001 | blocked | Needs owner decision | Owner | Static state |
"""
        prd = valid_prd().replace("## Product Definition Decisions", builder + "\n## Product Definition Decisions") + ui_contract
        self.assertTrue(any("Motion Need Gate remains blocked" in item for item in self.validate(prd=prd)))

    def test_ui_target_requires_matching_stack_area(self) -> None:
        ui_contract = """
<!-- ui-surface-contract:start -->
## UI Surface Contract
### UI-001 — Home
- `route`: /home
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
<!-- ui-surface-contract:end -->
"""
        builder = """
## Builder UX Direction Decision
| UI scope | Gate | Purpose and trigger | Decision source | Reduced-motion fallback |
| --- | --- | --- | --- | --- |
| UI-001 | not_required | Static workflow | Owner | Static state |
"""
        prd = valid_prd().replace(
            "## Product Definition Decisions",
            builder + "\n## Product Definition Decisions",
        ) + ui_contract
        stack = valid_stack().replace("- Approved areas: frontend", "- Approved areas: none")
        stack = stack[: stack.index("## Frontend Technology Decision")]
        self.assertTrue(
            any("missing required frontend technology decision section" in item for item in self.validate(prd=prd, stack=stack))
        )

    def test_required_ai_and_commercial_gates_require_stack_sections(self) -> None:
        ai_prd = valid_prd().replace(
            "AI and Automation Gate: not_required — no AI or autonomous action, decided by Owner",
            "AI and Automation Gate: required — model output affects the workflow, decided by Owner",
        )
        self.assertTrue(
            any("missing required ai or automation technology decision section" in item for item in self.validate(prd=ai_prd))
        )

        commercial_prd = valid_prd().replace(
            "| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |",
            "| Monetization Infrastructure Gate | required | Paid access | approved | PRD-001 |",
        )
        self.assertTrue(
            any("missing required commercial technology decision section" in item for item in self.validate(prd=commercial_prd))
        )

    def test_metric_placeholders_are_rejected_when_filled_is_required(self) -> None:
        prd = valid_prd().replace(
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |",
            "| [Metric] | Completed runs | 0 | 90% | 30 days | Event count | Owner |",
        )
        self.assertTrue(any("Metrics row contains an empty value or placeholder" in item for item in self.validate(prd=prd)))

    def test_must_and_nfr_require_required_test_coverage(self) -> None:
        prd = valid_prd().replace(
            "| TEST-001 | Complete fixture | integration | Yes | PRD-001 | Completion observed |",
            "| TEST-001 | Complete fixture | integration | Yes | PRD-999 | Completion observed |",
        )
        self.assertTrue(any("PRD-001 has no required Test Obligations coverage" in item for item in self.validate(prd=prd)))

        prd = valid_prd().replace("| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-002 |", "| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-999 |")
        self.assertTrue(any("PRD-002 references unknown TEST-999" in item for item in self.validate(prd=prd)))

    def test_enhancement_requires_impact_record(self) -> None:
        self.assertTrue(
            any(
                "Enhancement Impact Record" in item
                for item in self.validate(prd=valid_prd(mode="enhancement"))
            )
        )

    def test_cli_reads_all_three_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd = root / "PRD.md"
            architecture = root / "architecture.md"
            stack = root / "stack-decisions.md"
            prd.write_text(valid_prd(), encoding="utf-8")
            architecture.write_text(valid_architecture(), encoding="utf-8")
            stack.write_text(valid_stack(), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "check_product_package.py"),
                    "--prd",
                    str(prd),
                    "--architecture",
                    str(architecture),
                    "--stack-decisions",
                    str(stack),
                    "--require-filled",
                    "--require-approved",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("owner-approved", result.stdout)


if __name__ == "__main__":
    unittest.main()
