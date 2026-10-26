"""Shape-row checks of the product package checker.

These tests own the At a Glance Shape row paths: the console operations
rule, the app AEO/SEO companion rule, and the companion value rules.
The fixtures are copied from tests/test_product_package_checker.py so
this file stays independent of that module's private names.
"""

import re
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import check_product_package  # noqa: E402
import contract_utils  # noqa: E402


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
| PRD-003 | Security | Fixture command input boundary | Denied malformed input | 100% denied with no write | TEST-003 |
## UX Requirements
not_required — the fixture exposes no shipped user interface.
## Data and Integration Requirements
The fixture keeps deterministic local records and has no external data integration.
## Data and Trust
Data and Trust Gate: not_required — no personal or regulated data, decided by Owner
## Security Requirements
Security Requirements Gate: required — executable fixture input can create unsafe writes, decided by Owner
Security scope: executable

| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-003 | Fixture command trust boundary | Untrusted input mutates run records | Validate input and fail closed without writing | TEST-003 | Owner | none — no accepted residual risk |
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
| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |
## UI Design Handoff Status
UI design: not_required — fixture is headless
UI decision owner: n/a for headless
## Product Definition Decisions
### Research Gate
Research Gate: go — assessed 2026-09-12, decided by Owner
<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: {mode}
- Package revision: PD-R1@sha256:e8bb1cd27acddeb3fd2be4ed21ad941d2a86e333767ad980c0bbc8441658cba4
- Package digest: sha256:e8bb1cd27acddeb3fd2be4ed21ad941d2a86e333767ad980c0bbc8441658cba4
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
        "Auth, Permissions, and Security": (
            "PRD-003 places the fixture command at a trust boundary: validation "
            "denies untrusted input before the run record is touched.\n"
            "TEST-003 observes that denial: the command returns a validation error "
            "and the record keeps zero writes."
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
- Checkpoint digest: sha256:f9b21aca0ae23212aaa44b326c778e566dd5ac5b133fa4ef5da088ec48a9ada3
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


def finalize_approval_digests(
    prd_text: str, architecture_text: str, stack_text: str, *, revision: str = "PD-R1"
) -> tuple[str, str, str]:
    """Bind the fixture's approval fields to the exact candidate bytes."""
    zero = "0" * 64
    prd = re.sub(r"^- Package revision:.*$", f"- Package revision: {revision}@sha256:{zero}", prd_text, count=1, flags=re.MULTILINE)
    prd = re.sub(r"^- Package digest:.*$", f"- Package digest: sha256:{zero}", prd, count=1, flags=re.MULTILINE)
    stack = re.sub(r"^- Checkpoint digest:.*$", f"- Checkpoint digest: sha256:{zero}", stack_text, count=1, flags=re.MULTILINE)
    stack_digest = contract_utils.sha256_text(contract_utils.canonical_stack_bytes(stack))
    stack = re.sub(r"^- Checkpoint digest:.*$", f"- Checkpoint digest: sha256:{stack_digest}", stack, count=1, flags=re.MULTILINE)
    package_digest = contract_utils.sha256_text(contract_utils.canonical_product_bytes(prd, architecture_text, stack))
    prd = re.sub(r"^- Package revision:.*$", f"- Package revision: {revision}@sha256:{package_digest}", prd, count=1, flags=re.MULTILINE)
    prd = re.sub(r"^- Package digest:.*$", f"- Package digest: sha256:{package_digest}", prd, count=1, flags=re.MULTILINE)
    return prd, architecture_text, stack


def strictize_approved_package(prd: str, architecture: str, stack: str) -> tuple[str, str, str]:
    """Render fixture approval fields from the exact candidate bytes."""
    zero = "0" * 64
    prd = re.sub(r"- Package revision:.*", f"- Package revision: PD-R1@sha256:{zero}", prd, count=1)
    prd = re.sub(r"- Package digest:.*", f"- Package digest: sha256:{zero}", prd, count=1)
    stack = re.sub(r"- Checkpoint digest:.*", f"- Checkpoint digest: sha256:{zero}", stack, count=1)
    contract, _ = check_product_package.parse_release_targets(architecture)
    areas = check_product_package.release_area_requirements(contract.targets)
    ui_surfaces, _ = check_product_package.parse_prd_ui_contract(prd, require_responsive=True)
    for surface in ui_surfaces.values():
        areas.add("mobile or desktop" if surface.get("responsiveKind") == "sizeClasses" else "frontend")
    if "AI and Automation Gate: required" in prd:
        areas.add("ai or automation")
    if "Data and Trust Gate: required" in prd:
        areas.add("backend or data")
    if "Monetization Infrastructure Gate | required" in prd or "Partner Channel Gate | required" in prd:
        areas.add("commercial")
    area_value = ", ".join(sorted(areas)) if areas else "none"
    stack = re.sub(r"- Approved areas:.*", f"- Approved areas: {area_value}", stack, count=1)
    return finalize_approval_digests(prd, architecture, stack)


TEST_002_ROW = (
    "| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |"
)

TEST_003_ROW = (
    "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 "
    "| denial: rejected (validation error returned); no unauthorized side effects: "
    "unchanged (run record has zero writes) |"
)

SEO_TEST_ROW = (
    "| TEST-004 | Landing page SEO metadata renders on the companion surface | seo | Yes "
    "| PRD-001 | meta title and meta description render on the landing route |"
)

CONSOLE_JOURNEYS = """### Journey 2: Configure the fixture
1. The owner configures the fixture per PRD-001.
### Journey 3: Run the fixture inspection
1. The owner inspects the run state per PRD-002.
### Journey 4: Approve a fixture change
1. The owner approves the pending run record per PRD-003."""


def growth_contract_section(track: str = "web") -> str:
    return f"""## Growth Contract
### North Star
| Track | North star | Day 7 target | Day 30 target | Stretch | Source (MS-*) |
| --- | --- | --- | --- | --- | --- |
| {track} | Weekly returning fixture users | 40% return by day 7 | 55% return by day 30 | 70% return by day 30 | MS-100 |

### Re-engagement
| Mechanism | Surface or event | TEST ID |
| --- | --- | --- |
| email digest | Fixture digest surface on the home route | TEST-001 |

### Discovery Surfaces
| Surface | Kind | Owner stage | TEST or MS ID |
| --- | --- | --- | --- |
| /launch | landing | gtm | MS-110 |

### Launch Window
| Day | Channel class | Action | Owner | Readback metric |
| --- | --- | --- | --- | --- |
| Day 0 | owned | Announce the fixture launch | Owner | Return visits |

"""


def shaped_prd(
    shape_value: str = "track: web; companion: Fixture landing page; console: none",
    *,
    growth: bool = True,
) -> str:
    """Insert one At a Glance Shape row (and its Growth Contract) into the fixture PRD."""
    prd = valid_prd().replace(
        "| Biggest risk | A malformed contract could appear approved |",
        "| Biggest risk | A malformed contract could appear approved |\n"
        f"| Shape | {shape_value} |",
        1,
    )
    if growth:
        track_match = re.search(r"track:\s*(\w+)", shape_value)
        track = track_match.group(1) if track_match else "web"
        if track not in ("web", "app", "agent"):
            track = "web"
        prd = prd.replace(
            "## Problem Statement",
            growth_contract_section(track) + "## Problem Statement",
            1,
        )
    return prd


def console_journeys_prd(shape_value: str) -> str:
    return shaped_prd(shape_value).replace(
        "2. The checker reports an observable pass or exact finding.\n",
        "2. The checker reports an observable pass or exact finding.\n"
        + CONSOLE_JOURNEYS
        + "\n",
        1,
    )


def config_only_traced_prd(shape_value: str) -> str:
    """Keep every Required Yes test tracing into the configuration journey only."""
    prd = console_journeys_prd(shape_value)
    prd = prd.replace(TEST_002_ROW, TEST_002_ROW.replace("| PRD-002 |", "| PRD-001 |"), 1)
    return prd.replace(TEST_003_ROW, TEST_003_ROW.replace("| PRD-003 |", "| PRD-001 |"), 1)


def nonrequired_run_trace_prd(shape_value: str) -> str:
    """Trace the run inspection journey from a Required No test only."""
    prd = console_journeys_prd(shape_value)
    return prd.replace(
        TEST_002_ROW, TEST_002_ROW.replace("| Yes | PRD-002 |", "| No | PRD-002 |"), 1
    )


OPERATIONS_SHAPE = (
    "track: agent; companion: none (docs ship inside the repo); console: operations"
)


class ProductShapeCheckerTests(unittest.TestCase):
    def validate(
        self, prd: str, *, architecture: str | None = None
    ) -> list[str]:
        selected_architecture = architecture
        if selected_architecture is None and "<!-- ui-surface-contract:start -->" in prd:
            selected_architecture = release_architecture()
        package = strictize_approved_package(
            prd, selected_architecture or valid_architecture(), valid_stack()
        )
        return check_product_package.validate_texts(
            *package,
            require_filled=True,
            require_approved=True,
        )


class ConsoleOperationsTests(ProductShapeCheckerTests):
    def test_console_operations_passes_with_per_journey_traces(self) -> None:
        self.assertEqual([], self.validate(console_journeys_prd(OPERATIONS_SHAPE)))

    def test_console_operations_requires_a_required_test_per_journey(self) -> None:
        findings = self.validate(config_only_traced_prd(OPERATIONS_SHAPE))
        self.assertTrue(
            any(
                "Required Yes Test Obligation" in item
                and "run inspection" in item
                and "approval" in item
                for item in findings
            ),
            findings,
        )

    def test_console_operations_ignores_not_required_traces(self) -> None:
        findings = self.validate(nonrequired_run_trace_prd(OPERATIONS_SHAPE))
        self.assertTrue(
            any("tracing into the run inspection journey" in item for item in findings),
            findings,
        )
        self.assertFalse(any("approval journey" in item for item in findings), findings)

    def test_console_operations_requires_the_three_journey_headings(self) -> None:
        findings = self.validate(shaped_prd(OPERATIONS_SHAPE))
        self.assertTrue(
            any("(missing: configuration, run inspection)" in item for item in findings),
            findings,
        )


if __name__ == "__main__":
    unittest.main()
