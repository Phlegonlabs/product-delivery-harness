import os
import subprocess
import re
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import check_product_package  # noqa: E402
from git_evidence import GitEvidenceError, verify_revision_path  # noqa: E402
from prd_ui_contract import validate_prd_wireframe_data  # noqa: E402


def valid_prd(*, mode: str = "new") -> str:
    return f"""# PRD: Fixture

## At a Glance
| | |
| --- | --- |
| What it is | A deterministic contract validation fixture |
| Primary user | Product delivery owners and reviewers |
| Why now | Release gates need repeatable validation |
| Success looks like | At least 90% of fixture runs complete |
| Biggest risk | A malformed contract could appear approved |
## Problem Statement
Delivery owners need one observable way to reject incomplete product contracts before implementation begins.
## Goals
- Reject incomplete authority before implementation starts.
## Non-Goals
- Do not contact external systems from this fixture.
## Users and Personas
| Persona | Need | Key Workflow | Success Signal |
| --- | --- | --- | --- |
| Delivery owner | Trust the frozen package | Review and approve the package | Invalid authority is rejected |
## User Journeys
### Journey 1: Approve a fixture
1. The owner reviews the completed product package.
2. The checker reports an observable pass or exact finding.
## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-001 | Complete the fixture | Must | Completion is observable |
## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-002 |
## UX Requirements
not_required — the fixture exposes no shipped user interface.
## Data and Integration Requirements
The fixture keeps deterministic local records and has no external data integration.
## Data and Trust
Data and Trust Gate: not_required — no personal or regulated data, decided by Owner
## AI and Automation
AI and Automation Gate: not_required — no AI or autonomous action, decided by Owner
## Business Rules
Only an exact human-approved package may become implementation authority.
## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |
| Partner Channel Gate | not_required | No outside sellers | approved | n/a |
| Monetization model | none | No payer | approved | n/a |
| Pricing and offer | n/a | No offer | approved | n/a |
| Purchase and entitlement | n/a | No purchase | approved | n/a |
| Merchant of record / tax owner | n/a | No merchant of record | approved | n/a |
| Partner motion | none | No outside partner | approved | n/a |
| Partner economics and operations | n/a | No channel economics | approved | n/a |
## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |
## Risks
| Risk | Impact | Mitigation |
| --- | --- | --- |
| False approval | Incomplete work could ship | Fail closed on missing authority |
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
## UI Design Handoff Status
UI design: not_required — fixture is headless
UI decision owner: n/a for headless
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
        "Frontend Architecture",
        "Backend Architecture",
        "Data Model",
        "API and Interface Contracts",
        "Workflow and Data Flow",
        "Auth, Permissions, and Security",
        "Data and Trust Architecture",
        "AI and Automation Architecture",
        "Integrations",
        "Monetization and Partner Channel Architecture",
        "Deployment and Operations",
        "Release Targets",
        "Observability",
        "Scaling and Reliability",
        "Technical Risks and Tradeoffs",
        "Architecture Trace Index",
    )
    content = {
        "Component Architecture": (
            "| ARCH ID | Component | Responsibility | Upstream trace IDs | Notes |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| ARCH-001 | Fixture service | Complete fixture requests | PRD-001 | Owned by team |"
        ),
        "Data Model": (
            "| Entity | Key Fields | Relationships | Notes |\n"
            "| --- | --- | --- | --- |\n"
            "| Fixture run | id, status | belongs to owner | Test-only record |"
        ),
        "API and Interface Contracts": (
            "| ARCH ID | Interface | Method or Trigger | Input | Output | Errors | TEST IDs |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| ARCH-002 | Fixture command | explicit run | request | result | validation error | TEST-001 |"
        ),
        "Integrations": "not_required — the fixture has no external system integration.",
        "Technical Risks and Tradeoffs": (
            "| Decision | Options Considered | Recommendation | Reason |\n"
            "| --- | --- | --- | --- |\n"
            "| Fixture boundary | local or remote | local | deterministic validation |"
        ),
        "Architecture Trace Index": (
            "| ARCH ID | Contract or decision | Upstream PRD / UX IDs | Downstream UI / TEST IDs |\n"
            "| --- | --- | --- | --- |\n"
            "| ARCH-001 | Fixture execution | PRD-001 | TEST-001 |"
        ),
        "Release Targets": (
            "Expected deployable surfaces: none — fixture ships no deployable surface."
        ),
    }
    default = (
        "This section records concrete fixture boundaries, ownership, failure "
        "handling, and implementation responsibilities."
    )
    body = "\n".join(
        f"## {heading}\n{content.get(heading, default)}" for heading in headings
    )
    return "# Architecture: Fixture\n\n" + body


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

## Backend and Data Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Service topology | Single service | Required | Owner decision | Keeps fixture simple | Revisit at scale |
| Backend runtime / framework | Python service | Required | Owner decision | Fits fixture | Revisit at scale |
| Database category | None | Required | Owner decision | Fixture is deterministic | Revisit if persistence lands |
| Database engine | None | Required | Owner decision | Fixture is deterministic | Revisit if persistence lands |
| Auth strategy | None | Required | Owner decision | No protected data | Revisit if auth lands |
| Auth provider | None | Required | Owner decision | No protected data | Revisit if auth lands |
| API style | Local command | Required | Owner decision | Fits fixture | Revisit if hosted |
| Background jobs / queue | None | Required | Owner decision | No jobs | Revisit if jobs land |
| File / object storage | None | Required | Owner decision | No files | Revisit if files land |
"""


def ui_contract(*, copy: str = "draft — product responsibility is draft") -> str:
    return f"""
<!-- ui-surface-contract:start -->
## UI Surface Contract
### UI-001 — Home
- `route`: /home
- `releaseSurface`: web-app
- `surfaceClass`: hosted_web
- `captureMode`: hosted-browser
- Main purpose: Let the delivery owner inspect fixture completion.
- Content responsibilities: Show completion state from the fixture record with source, order, format, count, length, and fallback bounds.
- Actions and transitions: Refresh the record, show success feedback, and show a recoverable failure state.
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
- `copy`: {copy}
- Responsive obligations: Never drop status or recovery actions; support long content, keyboard input, and overlay focus return.
- Accessibility: Preserve headings, labels, focus order, announcements, and meaningful alternative text.
- SEO metadata: title Fixture status; meta description Current fixture completion; canonical n/a — private tool.
- Trace IDs: PRD-001, UX-001, ARCH-001, TEST-001
<!-- ui-surface-contract:end -->
"""


def release_target(
    target_id: str,
    *,
    stage: str,
    release_name: str,
    surface: str = "web-app",
    suffix: str = "web",
    provider: str = "Cloudflare",
) -> str:
    surface_class = {
        "web-app": "hosted_web",
        "public-api": "hosted_api",
        "browser-extension": "browser_extension",
        "ios-app": "ios",
        "android-app": "android",
        "macos-app": "macos",
        "windows-app": "windows",
    }.get(surface, "other_nonpublic")
    source_policy = (
        "stage=development; ref=run.integration.branch; "
        "sha=run.integration.integration_head_sha"
        if stage == "development"
        else "stage=production; ref=refs/heads/main; "
        "sha=promotion.verified_main_sha"
    )
    return f"""### Release Target: {target_id}
- Surface: {surface}
- Surface class: {surface_class}
- Public discoverability: {'yes' if surface == 'web-app' else 'no'}
- Surface suffix: {suffix}
- Release name: {release_name}
- Provider: {provider}
- Stage: {stage}
- Source policy: {source_policy}
- Artifact kind: static production bundle
- Signing requirement: not required
- Exact channel / track: fixture-{stage}
- Submission / promotion / review / manual approval path: candidate checks, owner approval, deploy
- Availability signal: URL answers the smoke check and the intended user reaches the route
- Rollout: all users after smoke passes
- Rollback / forward-fix: deploy the prior bundle or a corrected forward-fix
"""


def release_architecture(
    *,
    expected: str = "web-app",
    include_production: bool = True,
    extra_targets: str = "",
) -> str:
    targets = release_target("web-development", stage="development", release_name="fixture-web-dev")
    if include_production:
        targets += "\n" + release_target("web-production", stage="production", release_name="fixture-web")
    if extra_targets:
        targets += "\n" + extra_targets
    return valid_architecture().replace(
        "Expected deployable surfaces: none — fixture ships no deployable surface.",
        f"Expected deployable surfaces: {expected}\n\n{targets}",
    )


class ProductPackageCheckerTests(unittest.TestCase):
    def validate(
        self,
        prd: str | None = None,
        architecture: str | None = None,
        stack: str | None = None,
        *,
        require_approved: bool = True,
        repo_root: Path | None = None,
    ) -> list[str]:
        selected_prd = prd if prd is not None else valid_prd()
        selected_architecture = architecture
        if selected_architecture is None:
            selected_architecture = (
                release_architecture()
                if "<!-- ui-surface-contract:start -->" in selected_prd
                else valid_architecture()
            )
        return check_product_package.validate_texts(
            selected_prd,
            selected_architecture,
            stack if stack is not None else valid_stack(),
            require_filled=True,
            require_approved=require_approved,
            repo_root=repo_root,
        )

    def test_approved_package_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_code_and_outer_comments_cannot_supply_contracts(self) -> None:
        fenced = valid_prd().replace(
            "<!-- product-definition-approval:start -->",
            "```markdown\n<!-- product-definition-approval:start -->",
        ).replace(
            "<!-- product-definition-approval:end -->",
            "<!-- product-definition-approval:end -->\n```",
        )
        self.assertTrue(
            any(
                "active exact standalone product-definition approval marker pair"
                in item
                for item in self.validate(prd=fenced)
            )
        )

        trailing_text_fence = (
            "````markdown\n```not-a-close\n"
            + valid_prd()
            + "\n````\n"
        )
        self.assertTrue(
            any(
                "active exact standalone product-definition approval" in item
                for item in self.validate(prd=trailing_text_fence)
            )
        )

        raw_html = valid_prd().replace(
            "<!-- product-definition-approval:start -->",
            "<script>\n<!-- product-definition-approval:start -->",
        ).replace(
            "<!-- product-definition-approval:end -->",
            "<!-- product-definition-approval:end -->\n</script>",
        )
        self.assertTrue(
            any(
                "active exact standalone product-definition approval" in item
                for item in self.validate(prd=raw_html)
            )
        )

        for opening, closing in (
            ("<![CDATA[", "]]>") ,
            ("<?xml version='1.0'", "?>"),
            ("<textarea>", "</textarea>"),
            ("<x-widget>", "</x-widget>"),
        ):
            with self.subTest(raw_block=opening):
                wrapped = valid_prd().replace(
                    "<!-- product-definition-approval:start -->",
                    opening + "\n<!-- product-definition-approval:start -->",
                ).replace(
                    "<!-- product-definition-approval:end -->",
                    "<!-- product-definition-approval:end -->\n" + closing,
                )
                self.assertTrue(
                    any(
                        "active exact standalone product-definition approval" in item
                        for item in self.validate(prd=wrapped)
                    )
                )

        commented_ui = (
            valid_prd().replace(
                "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
                "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
            )
            + "\n<!--\n"
            + ui_contract()
            + "\n-->\n"
        )
        self.assertTrue(
            any(
                "exactly one matched ui-surface-contract boundary pair" in item
                for item in self.validate(prd=commented_ui)
            )
        )

    def test_zero_functional_or_test_rows_fail(self) -> None:
        no_requirements = valid_prd().replace(
            "| PRD-001 | Complete the fixture | Must | Completion is observable |\n",
            "",
        )
        problems = self.validate(prd=no_requirements)
        self.assertTrue(
            any("at least one requirement" in item for item in problems)
        )
        self.assertTrue(
            any("meaningful requirement" in item for item in problems)
        )

        no_tests = valid_prd().replace(
            "| TEST-001 | Complete fixture | integration | Yes | PRD-001 | Completion observed |\n",
            "",
        ).replace(
            "| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |\n",
            "",
        )
        problems = self.validate(prd=no_tests)
        self.assertTrue(any("at least one test" in item for item in problems))
        self.assertTrue(any("at least one Required Yes test" in item for item in problems))

    def test_release_target_inventory_stages_and_names_are_required(self) -> None:
        self.assertTrue(
            any(
                "Release Targets must contain" in item
                for item in self.validate(architecture="Architecture")
            )
        )

        missing_stage = self.validate(
            architecture=release_architecture(include_production=False)
        )
        self.assertTrue(
            any("missing production release targets" in item for item in missing_stage)
        )

        missing_surface = self.validate(
            architecture=release_architecture(expected="web-app, public-api")
        )
        self.assertTrue(
            any("public-api' is missing" in item for item in missing_surface)
        )

        bad_names = valid_architecture().replace(
            "Expected deployable surfaces: none — fixture ships no deployable surface.",
            "Expected deployable surfaces: web-app\n\n"
            + release_target(
                "web-development",
                stage="development",
                release_name="fixture-web-production",
            )
            + "\n"
            + release_target(
                "web-production",
                stage="production",
                release_name="fixture-web-prod",
            ),
        )
        problems = self.validate(architecture=bad_names)
        self.assertTrue(any("not a canonical" in item for item in problems))
        self.assertTrue(any("must not end in -prod" in item for item in problems))

    def test_required_gates_require_architecture_and_test_obligations(self) -> None:
        data_prd = valid_prd().replace(
            "Data and Trust Gate: not_required",
            "Data and Trust Gate: required",
        )
        problems = self.validate(prd=data_prd)
        self.assertTrue(
            any(
                "Data and Trust Gate architecture" in item
                or "Data and Trust Architecture requires substantive" in item
                for item in problems
            )
        )
        self.assertTrue(
            any("Data and Trust Gate must use its canonical decision table" in item for item in problems)
        )

        ai_prd = valid_prd().replace(
            "AI and Automation Gate: not_required",
            "AI and Automation Gate: required",
        )
        problems = self.validate(prd=ai_prd)
        self.assertTrue(
            any("AI and Automation Gate must use its canonical decision table" in item for item in problems)
        )

        commercial_prd = valid_prd().replace(
            "| Monetization Infrastructure Gate | not_required",
            "| Monetization Infrastructure Gate | required",
        )
        problems = self.validate(prd=commercial_prd)
        self.assertTrue(
            any("required commercial" in item for item in problems)
        )

    def test_required_gate_rejects_not_required_architecture_and_unrelated_tests(self) -> None:
        rows = """
| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Classification and ownership | Personal records owned by customer | Privacy owner | TEST-001 |
| Residency and vendor processing | United States processing only | Privacy owner | TEST-001 |
| Retention, deletion, and export | Delete after thirty days with export | Privacy owner | TEST-001 |
| Consent and policy basis | Explicit account consent | Privacy owner | TEST-001 |
| Human and administrative access | Approved support role with audit | Security owner | TEST-001 |
| Incident and residual risk | Incident owner accepts residual risk | Security owner | TEST-001 |
"""
        prd = valid_prd().replace(
            "Data and Trust Gate: not_required — no personal or regulated data, decided by Owner",
            "Data and Trust Gate: required — personal customer data needs controls, decided by Owner"
            + rows,
        )
        architecture = re.sub(
            r"(## Data and Trust Architecture\n)[\s\S]*?(?=^## AI and Automation Architecture)",
            r"\1not_required — classification ownership residency vendor encryption access audit retention deletion export consent policy backup recovery incident controls are not used.\n",
            valid_architecture(),
            count=1,
            flags=re.MULTILINE,
        )
        problems = self.validate(prd=prd, architecture=architecture)
        self.assertTrue(any("cannot mark its architecture not_required" in item for item in problems))
        self.assertTrue(any("TRUST-CLASSIFICATION" in item for item in problems))

    def test_enhancement_changed_rows_cannot_refresh_none(self) -> None:
        impacts = """
## Enhancement Impact Record
| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | unchanged | none | none |
| UI structure / style | none | none | none |
| Data / integrations | unchanged | none | none |
| Architecture / stack | changed | ARCH-001, frontend framework | none |
| Data trust / AI | unchanged | none | none |
| Monetization / partner | unchanged | none | none |
| Release / operations | unchanged | none | none |
"""
        prd = valid_prd(mode="enhancement").replace(
            "## Problem Statement",
            impacts + "\n## Problem Statement",
        )
        problems = self.validate(prd=prd)
        self.assertTrue(
            any("area-specific refresh" in item for item in problems)
        )

    def test_prefix_and_placeholder_bypasses_fail(self) -> None:
        nonevil = valid_prd().replace(
            "- Blocking items: none", "- Blocking items: nonevil hidden decision"
        )
        self.assertTrue(any("Blocking items must be none" in item for item in self.validate(prd=nonevil)))

        completedly = valid_prd().replace(
            "- Market research reconciliation: completed",
            "- Market research reconciliation: completedly",
        )
        self.assertTrue(
            any("invalid market research reconciliation" in item for item in self.validate(prd=completedly))
        )

        todo = valid_prd().replace(
            "| Completion | Completed runs |", "| Completion TODO | Completed runs |"
        )
        self.assertTrue(
            any("empty value or placeholder" in item for item in self.validate(prd=todo))
        )

    def test_nonhuman_owner_invalid_date_and_artifact_list_fail(self) -> None:
        owner = valid_prd().replace(
            "- Decision owner: Owner", "- Decision owner: AI assistant"
        )
        self.assertTrue(any("must name a human owner" in item for item in self.validate(prd=owner)))

        invalid_date = valid_prd().replace(
            "- Decided on: 2026-09-12", "- Decided on: 2026-02-31"
        )
        self.assertTrue(any("real YYYY-MM-DD" in item for item in self.validate(prd=invalid_date)))

        wrong_artifacts = valid_prd().replace(
            "- Approved artifacts: PRD.md, architecture.md, stack-decisions.md",
            "- Approved artifacts: not-prd.md, architecture.md, stack-decisions.md",
        )
        self.assertTrue(
            any("must be exactly" in item for item in self.validate(prd=wrong_artifacts))
        )

    def test_duplicate_metrics_and_ui_states_fail(self) -> None:
        duplicate_metric = valid_prd().replace(
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |",
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |\n"
            "| Completion | Completed runs | 0 | 95% | 30 days | Event count | Owner |",
        )
        self.assertTrue(any("duplicate metric" in item for item in self.validate(prd=duplicate_metric)))

        duplicate_state = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ) + ui_contract().replace(
            "- `states`: ready", "- `states`: ready, ready", 1
        )
        problems = self.validate(prd=duplicate_state)
        self.assertTrue(any("duplicate states" in item for item in problems))

    def test_every_ui_surface_requires_copy_anchor(self) -> None:
        missing_copy = (
            valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
            )
            + ui_contract().replace(
                "- `copy`: draft — product responsibility is draft\n", ""
            )
        )
        self.assertTrue(
            any("requires exactly one `copy` anchor" in item for item in self.validate(prd=missing_copy))
        )

    def test_wireframe_approval_advances_draft_copy_without_circular_prd_rewrite(self) -> None:
        data = {
            "schema": "wireframes/4",
            "viewports": [390, 768, 1200],
            "screens": [
                {
                    "id": "UI-001",
                    "route": "/home",
                    "states": [{"id": "ready"}],
                    "copyStatus": "approved",
                }
            ],
        }
        prd = ui_contract(copy="draft — ui-design-builder owns exact Copy Freeze")
        self.assertEqual([], validate_prd_wireframe_data(prd, data, web_floor=3))

        for status in ("revision_requested", "blocked"):
            prd = ui_contract(copy=f"{status} — stop")
            problems = validate_prd_wireframe_data(prd, data, web_floor=3)
            self.assertTrue(
                any("cannot proceed while the PRD copy status" in item for item in problems)
            )

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

    def test_ui_packages_require_an_explicit_ui_design_builder_handoff(self) -> None:
        contract = ui_contract(
            copy="draft — responsibility draft; ui-design-builder owns exact copy"
        )
        prd = valid_prd() + contract
        self.assertTrue(any("must defer UI design" in item for item in self.validate(prd=prd)))

        prd = prd.replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ).replace(
            "not_required — the fixture exposes no shipped user interface.",
            "| ID | User / task | Requirement | Success and failure signal | Evidence status |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| UX-001 | Owner reviews status | Show completion and recovery | Success is visible; failure offers retry | prototype-reviewed |",
        )
        self.assertEqual([], self.validate(prd=prd))

        bad_traces = prd.replace(
            "PRD-001, UX-001, ARCH-001, TEST-001",
            "PRD-999, UX-999, TEST-999",
        )
        problems = self.validate(prd=bad_traces)
        self.assertTrue(any("must include ARCH-*" in item for item in problems))
        self.assertTrue(any("unknown PRD-999" in item for item in problems))
        self.assertTrue(any("unknown UX-999" in item for item in problems))
        self.assertTrue(any("unknown TEST-999" in item for item in problems))

        broken_contract = contract.replace("- `route`: /home\n", "")
        prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ) + broken_contract
        self.assertTrue(any("requires exactly one `route` anchor" in item for item in self.validate(prd=prd)))

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
        prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
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

    def test_normal_deployable_release_targets_pass(self) -> None:
        self.assertEqual([], self.validate(architecture=release_architecture()))

    def test_hybrid_ui_surfaces_bind_web_and_ios_release_contracts(self) -> None:
        native_surface = """
### UI-002 — Native home
- `route`: /native-home
- `releaseSurface`: ios-app
- `surfaceClass`: ios
- `captureMode`: native
- Main purpose: Let the owner inspect the same fixture on iOS.
- Content responsibilities: Show completion state with source: fixture record; order: status then recovery; format: text; count: one; length: bounded; fallback: unavailable message.
- Actions and transitions: Refresh the record, show success feedback, and show a recoverable failure state.
- `states`: ready
- `responsive`: sizeClasses: compact, regular
- `copy`: draft — product responsibility is draft
- Responsive obligations: Never drop status or recovery actions in compact and regular layouts.
- Accessibility: Preserve headings, labels, focus order, announcements, and meaningful alternative text.
- SEO metadata: n/a — native app surface.
- Trace IDs: PRD-001, UX-001, ARCH-001, TEST-001
"""
        contract = ui_contract().replace(
            "<!-- ui-surface-contract:end -->",
            native_surface + "\n<!-- ui-surface-contract:end -->",
        )
        prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ).replace(
            "not_required — the fixture exposes no shipped user interface.",
            "| ID | User / task | Requirement | Success and failure signal | Evidence status |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| UX-001 | Owner reviews status | Show completion and recovery | Success is visible; failure offers retry | prototype-reviewed |",
        ) + contract
        ios_targets = "\n".join(
            (
                release_target(
                    "ios-development",
                    surface="ios-app",
                    suffix="ios",
                    provider="TestFlight",
                    stage="development",
                    release_name="fixture-ios-dev",
                ),
                release_target(
                    "ios-production",
                    surface="ios-app",
                    suffix="ios",
                    provider="App Store",
                    stage="production",
                    release_name="fixture-ios",
                ),
            )
        )
        architecture = release_architecture(
            expected="web-app, ios-app",
            extra_targets=ios_targets,
        )
        stack = valid_stack().replace(
            "- Approved areas: frontend",
            "- Approved areas: frontend, mobile or desktop",
        ).replace(
            "| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |",
            "| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |\n"
            "| OPT-MOB-01 | Mobile or desktop | Native SwiftUI and Xcode bundle | iOS app | Mobile team owns distribution | approved |\n"
            "| OPT-MOB-02 | Mobile or desktop | Cross-platform client bundle | Multi-OS app | Team owns framework upgrades | rejected |",
        )
        mobile_rows = "\n".join(
            f"| {layer.title()} | fixture choice | Approved | Owner decision | Fits iOS | None |"
            for layer in check_product_package.STACK_SECTION_LAYERS[
                "Mobile/Desktop Technology Decision"
            ]
        )
        stack += (
            "\n## Mobile/Desktop Technology Decision\n"
            "### Recorded or Approved Stack\n"
            "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            + mobile_rows
            + "\n"
        )

        self.assertEqual(
            [],
            self.validate(prd=prd, architecture=architecture, stack=stack),
        )

    def test_capture_mode_requires_matching_responsive_kind_for_web_ios_and_extension(self) -> None:
        web_prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ).replace(
            "not_required — the fixture exposes no shipped user interface.",
            "| ID | User / task | Requirement | Success and failure signal | Evidence status |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| UX-001 | Owner reviews status | Show completion and recovery | Success is visible; failure offers retry | prototype-reviewed |",
        ) + ui_contract()
        web_bad = web_prd.replace(
            "- `responsive`: viewports: 390, 768, 1200",
            "- `responsive`: sizeClasses: compact, regular",
        )
        self.assertTrue(
            any("responsive" in finding and "viewports" in finding for finding in self.validate(prd=web_bad))
        )

        native_surface = """
### UI-002 — Native home
- `route`: /native-home
- `releaseSurface`: ios-app
- `surfaceClass`: ios
- `captureMode`: native
- Main purpose: Let the owner inspect the same fixture on iOS.
- Content responsibilities: Show completion state with source: fixture record; order: status then recovery; format: text; count: one; length: bounded; fallback: unavailable message.
- Actions and transitions: Refresh the record, show success feedback, and show a recoverable failure state.
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
- `copy`: draft — product responsibility is draft
- Responsive obligations: Never drop status or recovery actions.
- Accessibility: Preserve headings, labels, focus order, announcements, and meaningful alternative text.
- SEO metadata: n/a — native app surface.
- Trace IDs: PRD-001, UX-001, ARCH-001, TEST-001
"""
        ios_contract = ui_contract().replace(
            "<!-- ui-surface-contract:end -->",
            native_surface + "\n<!-- ui-surface-contract:end -->",
        )
        ios_prd = web_prd[: -len(ui_contract())] + ios_contract
        ios_targets = "\n".join(
            (
                release_target("ios-development", surface="ios-app", suffix="ios", provider="TestFlight", stage="development", release_name="fixture-ios-dev"),
                release_target("ios-production", surface="ios-app", suffix="ios", provider="App Store", stage="production", release_name="fixture-ios"),
            )
        )
        ios_architecture = release_architecture(expected="web-app, ios-app", extra_targets=ios_targets)
        ios_findings = self.validate(prd=ios_prd, architecture=ios_architecture)
        self.assertTrue(
            any(
                "prd.UI-002.responsive" in finding and "sizeClasses" in finding
                for finding in ios_findings
            ),
            ios_findings,
        )

        extension_prd = web_prd.replace(
            "releaseSurface`: web-app", "releaseSurface`: browser-extension"
        ).replace(
            "surfaceClass`: hosted_web", "surfaceClass`: browser_extension"
        ).replace(
            "captureMode`: hosted-browser", "captureMode`: browser-extension"
        ).replace(
            "viewports: 390, 768, 1200", "sizeClasses: compact, regular"
        )
        extension_target = "\n".join(
            (
                release_target("extension-development", surface="browser-extension", suffix="extension", provider="Chrome", stage="development", release_name="fixture-extension-dev"),
                release_target("extension-production", surface="browser-extension", suffix="extension", provider="Chrome", stage="production", release_name="fixture-extension"),
            )
        )
        extension_architecture = release_architecture(expected="browser-extension", extra_targets=extension_target)
        self.assertTrue(
            any(
                "responsive" in finding and "viewports" in finding
                for finding in self.validate(prd=extension_prd, architecture=extension_architecture)
            )
        )

    def test_release_target_typed_surface_and_discoverability_are_closed(self) -> None:
        architecture = release_architecture().replace(
            "- Surface class: hosted_web", "- Surface class: guessed_web"
        )
        findings = self.validate(architecture=architecture)
        self.assertTrue(any("invalid Surface class" in item for item in findings))
        architecture = release_architecture().replace(
            "- Public discoverability: yes", "- Public discoverability: maybe"
        )
        findings = self.validate(architecture=architecture)
        self.assertTrue(any("invalid Public discoverability" in item for item in findings))

    def test_release_target_pairs_keep_typed_class_and_discoverability(self) -> None:
        architecture = release_architecture()
        marker = "- Surface class: hosted_web\n- Public discoverability: yes"
        first, second = architecture.split(marker, 1)
        architecture = first + marker + second.replace(marker, "- Surface class: hosted_api\n- Public discoverability: no", 1)
        findings = self.validate(architecture=architecture)
        joined = "\n".join(findings)
        self.assertIn("same Surface class", joined)
        self.assertIn("same Public discoverability", joined)

    def test_empty_architecture_sections_cannot_pass(self) -> None:
        body = []
        for heading in check_product_package.REQUIRED_ARCHITECTURE_HEADINGS:
            body.append(heading)
            if heading == "## Release Targets":
                body.append(
                    "Expected deployable surfaces: none — this fixture has no release destination."
                )
        architecture = "# Architecture: Empty\n\n" + "\n".join(body)
        problems = self.validate(architecture=architecture)
        self.assertTrue(
            any(
                "requires substantive implementation content" in item
                or "requires a populated canonical table" in item
                for item in problems
            ),
            problems,
        )

        blanket = valid_architecture()
        for heading in check_product_package.REQUIRED_ARCHITECTURE_HEADINGS:
            if heading == "## Release Targets":
                continue
            blanket = re.sub(
                rf"({re.escape(heading)}\n)[\s\S]*?(?=^##\s+|\Z)",
                r"\1not_required — this sentence claims the whole architecture is inapplicable.\n",
                blanket,
                count=1,
                flags=re.MULTILINE,
            )
        problems = self.validate(architecture=blanket)
        self.assertTrue(any("mandatory and cannot be not_required" in item for item in problems))

    def test_empty_core_prd_and_incomplete_ui_surface_cannot_pass(self) -> None:
        duplicate_glance = valid_prd().replace(
            "| Primary user |",
            "| What it is | A contradictory second product identity |\n| Primary user |",
            1,
        )
        self.assertTrue(
            any("exactly its five canonical rows" in item for item in self.validate(prd=duplicate_glance))
        )

        prd = valid_prd()
        for heading, next_heading in (
            ("At a Glance", "Problem Statement"),
            ("Problem Statement", "Goals"),
            ("Goals", "Non-Goals"),
            ("Non-Goals", "Users and Personas"),
            ("Users and Personas", "User Journeys"),
            ("User Journeys", "Functional Requirements"),
            ("UX Requirements", "Data and Integration Requirements"),
            ("Data and Integration Requirements", "Data and Trust"),
            ("Business Rules", "Monetization and Partner Channels"),
            ("Risks", "Assumptions"),
        ):
            prd = re.sub(
                rf"(## {re.escape(heading)}\n)[\s\S]*?(?=## {re.escape(next_heading)})",
                r"\1",
                prd,
                count=1,
            )
        problems = self.validate(prd=prd)
        self.assertTrue(any("At a Glance" in item for item in problems))
        self.assertTrue(any("Problem Statement" in item for item in problems))
        self.assertTrue(any("Users and Personas" in item for item in problems))

        incomplete = """
<!-- ui-surface-contract:start -->
## UI Surface Contract
### UI-001 — Home
- `route`: /home
- `states`: ready
- `responsive`: viewports: 390, 768, 1200
- `copy`: draft — responsibility remains with product owner
<!-- ui-surface-contract:end -->
"""
        ui_prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ).replace(
            "not_required — the fixture exposes no shipped user interface.",
            "| ID | User / task | Requirement | Success and failure signal | Evidence status |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| UX-001 | Owner reviews status | Show completion and recovery | Success visible; failure recoverable | prototype-reviewed |",
        ) + incomplete
        problems = self.validate(prd=ui_prd)
        self.assertTrue(any("Main purpose" in item for item in problems))
        self.assertTrue(any("Trace IDs" in item for item in problems))

    def test_indented_markdown_code_cannot_supply_contracts_or_tables(self) -> None:
        def indent_block(text: str, start: str, end: str) -> str:
            match = re.search(
                re.escape(start) + r"[\s\S]*?" + re.escape(end), text
            )
            self.assertIsNotNone(match)
            indented = "\n".join("    " + line for line in match.group(0).splitlines())
            return text[: match.start()] + indented + text[match.end() :]

        prd = indent_block(
            valid_prd(),
            "<!-- product-definition-approval:start -->",
            "<!-- product-definition-approval:end -->",
        )
        self.assertTrue(
            any("active exact standalone product-definition approval" in item for item in self.validate(prd=prd))
        )

        stack = indent_block(
            valid_stack(),
            "<!-- stack-decision-checkpoint:start -->",
            "<!-- stack-decision-checkpoint:end -->",
        )
        self.assertTrue(
            any("active exact standalone stack-decision checkpoint" in item for item in self.validate(stack=stack))
        )

        prd = re.sub(
            r"(## Functional Requirements\n)([\s\S]*?)(?=## Non-Functional Requirements)",
            lambda match: match.group(1)
            + "\n".join("    " + line for line in match.group(2).splitlines()),
            valid_prd(),
            count=1,
        )
        self.assertTrue(
            any("Functional Requirements must use the canonical table" in item for item in self.validate(prd=prd))
        )

    def test_nfr_and_priority_cannot_escape_test_coverage(self) -> None:
        empty_nfr = re.sub(
            r"(## Non-Functional Requirements\n\| ID[^\n]*\n\| ---[^\n]*\n)\| PRD-002[^\n]*\n",
            r"\1",
            valid_prd(),
        ).replace(
            "| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |\n",
            "",
        )
        self.assertTrue(
            any("Non-Functional Requirements must contain" in item for item in self.validate(prd=empty_nfr))
        )

        mustard = valid_prd().replace("| Must |", "| Mustard |").replace(
            "| TEST-001 | Complete fixture | integration | Yes | PRD-001 | Completion observed |\n",
            "",
        )
        problems = self.validate(prd=mustard)
        self.assertTrue(any("Priority must be Must" in item for item in problems))
        self.assertTrue(any("must include at least one Must" in item for item in problems))

    def test_release_targets_are_scoped_and_stage_bound(self) -> None:
        architecture = release_architecture()
        match = re.search(
            r"## Release Targets\n([\s\S]*?)(?=## Observability)", architecture
        )
        self.assertIsNotNone(match)
        moved = (
            architecture[: match.start(1)]
            + "\n"
            + architecture[match.end(1) :]
            + "\n"
            + match.group(1)
        )
        self.assertTrue(
            any("expected deployable-surface inventory" in item for item in self.validate(architecture=moved))
        )

        mismatched_suffix = release_architecture().replace(
            "- Surface suffix: web", "- Surface suffix: development-web", 1
        )
        self.assertTrue(
            any("must use the same surface suffix" in item for item in self.validate(architecture=mismatched_suffix))
        )

        wrong_source = release_architecture().replace(
            "stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha",
            "candidate branch is forbidden and no SHA is available; deploy main instead",
            1,
        )
        self.assertTrue(
            any("closed stage=<stage>" in item for item in self.validate(architecture=wrong_source))
        )
        negated_production = release_architecture().replace(
            "stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha",
            "main is forbidden and SHA is unavailable; deploy the candidate instead",
            1,
        )
        self.assertTrue(
            any("closed stage=<stage>" in item for item in self.validate(architecture=negated_production))
        )

    def test_selected_stack_requires_repository_evidence_and_unique_sections(self) -> None:
        selected = valid_stack(status="Selected")
        self.assertTrue(
            any("Selected layer" in item for item in self.validate(stack=selected))
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Product Test"], cwd=root, check=True
            )
            subprocess.run(["git", "add", "package.json"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            evidence = f"repository:package.json@{revision}"
            selected = selected.replace("Owner decision", evidence)
            self.assertEqual([], self.validate(stack=selected, repo_root=root))

            invented = selected.replace("package.json", "does-not-exist")
            self.assertTrue(
                any("path does not exist" in item for item in self.validate(stack=invented, repo_root=root))
            )

        duplicate = valid_stack() + "\n## Frontend Technology Decision\ncontradiction\n"
        self.assertTrue(
            any("duplicate technology decision section" in item for item in self.validate(stack=duplicate))
        )

    def test_selected_evidence_rejects_replacements_grafts_and_identity_env(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Product Test"], cwd=root, check=True
            )
            subprocess.run(["git", "add", "package.json"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            with self.assertRaisesRegex(GitEvidenceError, "replacement refs"):
                subprocess.run(
                    ["git", "update-ref", f"refs/replace/{revision}", revision],
                    cwd=root,
                    check=True,
                )
                verify_revision_path(root, revision, "package.json")

            subprocess.run(
                ["git", "update-ref", "-d", f"refs/replace/{revision}"],
                cwd=root,
                check=True,
            )
            git_dir = Path(
                subprocess.check_output(
                    ["git", "rev-parse", "--absolute-git-dir"], cwd=root, text=True
                ).strip()
            )
            graft = git_dir / "info" / "grafts"
            graft.parent.mkdir(parents=True, exist_ok=True)
            graft.write_text("# adversarial graft\n", encoding="utf-8")
            with self.assertRaisesRegex(GitEvidenceError, "graft metadata"):
                verify_revision_path(root, revision, "package.json")

            graft.unlink()
            alternate = Path(directory).parent / f"alternate-{root.name}"
            subprocess.run(["git", "init", "-q", str(alternate)], check=True)
            other_git = subprocess.check_output(
                ["git", "rev-parse", "--absolute-git-dir"],
                cwd=alternate,
                text=True,
            ).strip()
            with self.assertRaisesRegex(GitEvidenceError, "identity environment"):
                verify_revision_path(
                    root,
                    revision,
                    "package.json",
                    environment={**os.environ, "GIT_DIR": other_git},
                )
            # Git's numbered config injection protocol is removed before the
            # exact-SHA read; it cannot select an attacker URL/config file.
            verify_revision_path(
                root,
                revision,
                "package.json",
                environment={
                    **os.environ,
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "url.https://attacker.invalid/.insteadOf",
                    "GIT_CONFIG_VALUE_0": "origin",
                },
            )

    def test_owner_status_and_research_provenance_are_closed(self) -> None:
        metric_ai = valid_prd().replace(
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |",
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | AI |",
        )
        self.assertTrue(any("metric 'Completion' must name a human" in item for item in self.validate(prd=metric_ai)))

        assumption_ai = valid_prd().replace(
            "## Open Questions",
            "| Vendor remains stable | Delivery changes | Review contract | AI | 2026-09-12 | accepted |\n## Open Questions",
        )
        self.assertTrue(any("assumption 'Vendor remains stable' must name a human" in item for item in self.validate(prd=assumption_ai)))

        question = valid_prd().replace(
            "## Test Obligations",
            "| Choose provider | Changes delivery | Owner | 2026-09-12 | Yes-ish | Open |\n## Test Obligations",
        )
        self.assertTrue(any("Blocks approval must be Yes or No" in item for item in self.validate(prd=question)))

        invalid_research_date = valid_prd().replace("assessed 2026-09-12", "assessed 2026-02-31")
        self.assertTrue(any("real assessed" in item for item in self.validate(prd=invalid_research_date)))

        duplicate_artifact = valid_prd().replace(
            "PRD.md, architecture.md, stack-decisions.md",
            "PRD.md, PRD.md, architecture.md, stack-decisions.md",
        )
        self.assertTrue(any("exactly, once and in order" in item for item in self.validate(prd=duplicate_artifact)))

    def test_natural_language_no_refresh_and_normalized_state_duplicates_fail(self) -> None:
        impacts = """
## Enhancement Impact Record
| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | unchanged | none | none |
| UI structure / style | none | none | none |
| Data / integrations | unchanged | none | none |
| Architecture / stack | changed | No IDs or decisions are affected | No refresh is required here |
| Data trust / AI | unchanged | none | none |
| Monetization / partner | unchanged | none | none |
| Release / operations | unchanged | none | none |
"""
        prd = valid_prd(mode="enhancement").replace(
            "## Problem Statement", impacts + "\n## Problem Statement"
        )
        problems = self.validate(prd=prd)
        self.assertTrue(any("structured affected IDs" in item for item in problems))
        self.assertTrue(any("area-specific refresh" in item for item in problems))

        wrong_area_refresh = impacts.replace(
            "| UI structure / style | none | none | none |",
            "| UI structure / style | both | UI-001 | PRD.md and validate checker |",
        ).replace(
            "| Release / operations | unchanged | none | none |",
            "| Release / operations | changed | decision:release-target-web | wireframes.html and approval gate |",
        )
        prd = valid_prd(mode="enhancement").replace(
            "## Problem Statement", wrong_area_refresh + "\n## Problem Statement"
        )
        problems = self.validate(prd=prd)
        self.assertTrue(
            any("UI structure / style" in item and "wireframes.html" in item for item in problems)
        )
        self.assertTrue(
            any("Release / operations" in item and "architecture.md" in item for item in problems)
        )

        prd = valid_prd().replace(
            "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
            "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
        ) + ui_contract().replace(
            "- `states`: ready",
            "- `states`: ready, offline:n/a — first reason, offline:n/a — second reason",
        )
        self.assertTrue(
            any("duplicate states: offline" in item for item in self.validate(prd=prd))
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
