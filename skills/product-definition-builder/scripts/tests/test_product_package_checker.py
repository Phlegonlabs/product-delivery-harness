import contextlib
import io
import json
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
import contract_utils  # noqa: E402
from git_evidence import GitEvidenceError, verify_revision_path  # noqa: E402
from prd_ui_contract import validate_prd_wireframe_data  # noqa: E402
from release_targets import parse_release_targets  # noqa: E402


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


def documentation_only_package() -> tuple[str, str]:
    security_table = """| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-003 | Fixture command trust boundary | Untrusted input mutates run records | Validate input and fail closed without writing | TEST-003 | Owner | none — no accepted residual risk |
"""
    prd = valid_prd().replace(
        "Security Requirements Gate: required — executable fixture input can create "
        "unsafe writes, decided by Owner",
        "Security Requirements Gate: not_required — the package only documents the "
        "fixture and executes no security-relevant scope, decided by Owner",
    ).replace("Security scope: executable", "Security scope: documentation_only")
    prd = prd.replace(security_table, "")
    prd = prd.replace(
        "| PRD-003 | Security | Fixture command input boundary | Denied malformed "
        "input | 100% denied with no write | TEST-003 |\n",
        "",
    )
    prd = prd.replace(
        "| TEST-003 | Deny untrusted fixture input before any write | security | Yes "
        "| PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n",
        "",
    )
    documentation_wording = {
        "A deterministic contract validation fixture": (
            "A documentation-only product contract fixture"
        ),
        "At least 90% of fixture runs complete": (
            "At least 90% of package reviews complete"
        ),
        "Passing executions": "Completed document reviews",
        "PRD-001 | Complete the fixture | Must | Completion is observable": (
            "PRD-001 | Document the fixture requirements | Must | "
            "The approved package is observable"
        ),
        "The fixture keeps deterministic local records and has no external data integration.": (
            "The package records decisions in Markdown and has no runtime data integration."
        ),
        "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |": (
            "| Completion | Completed document reviews | 0 | 90% | 30 days | "
            "Review log | Owner |"
        ),
    }
    for old, new in documentation_wording.items():
        prd = prd.replace(old, new)
    architecture = valid_architecture().replace(
        "PRD-003 places the fixture command at a trust boundary: validation "
        "denies untrusted input before the run record is touched.\n"
        "TEST-003 observes that denial: the command returns a validation error "
        "and the record keeps zero writes.",
        "This section records concrete fixture boundaries, ownership, failure "
        "handling, and implementation responsibilities."
    ).replace(
        "| ARCH-001 | Fixture service | Complete fixture requests | PRD-001 | Owned by team |",
        "| ARCH-001 | docs/product-definition.md | Record product definition decisions | PRD-001 | Owned by team |",
    ).replace(
        "| Fixture run | id, status | belongs to owner | Test-only record |",
        "| Decision record | status, owner | belongs to package | Documentation-only record |",
    ).replace(
        "| ARCH-002 | Fixture command | explicit run | request | result | validation error | TEST-001 |",
        "| ARCH-002 | Document review | owner review | candidate package | approval decision | validation finding | TEST-001 |",
    ).replace(
        "| ARCH-001 | Fixture execution | PRD-001 | TEST-001 |",
        "| ARCH-001 | Documentation decisions | PRD-001 | TEST-001 |",
    )
    for heading in (
        "Frontend Architecture", "Backend Architecture",
        "API and Interface Contracts", "AI and Automation Architecture", "Data Model",
    ):
        architecture = re.sub(
            rf"(## {re.escape(heading)}\n)[\s\S]*?(?=\n## |\Z)",
            r"\1not_required — only human-reviewed Markdown documents are delivered.",
            architecture,
        )
    architecture = re.sub(
        r"(## Product Archetype\n)[\s\S]*?(?=\n## |\Z)",
        r"\1documentation_only — only human-reviewed Markdown documents are delivered.",
        architecture,
    )
    for heading, kind in (
        ("Workflow and Data Flow", "human_review"),
        ("Deployment and Operations", "document_distribution"),
    ):
        architecture = re.sub(
            rf"(## {re.escape(heading)}\n)[\s\S]*?(?=\n## |\Z)",
            rf"\1{kind} — only human-reviewed Markdown documents are delivered.",
            architecture,
        )
    return prd, architecture


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


def toolchain_package(surface_classes: tuple[str, ...]) -> tuple[str, str, str]:
    targets = []
    surfaces = []
    for surface_class in surface_classes:
        surface = surface_class.replace("_", "-")
        surfaces.append(surface)
        for stage in ("development", "production"):
            targets.append(release_target(
                f"{surface}-{stage}", stage=stage, surface=surface,
                suffix=surface, provider="Direct download",
                release_name=f"fixture-{surface}" + ("-dev" if stage == "development" else ""),
            ).replace("Surface class: other_nonpublic", f"Surface class: {surface_class}"))
    architecture = valid_architecture().replace(
        "Expected deployable surfaces: none — fixture ships no deployable surface.",
        "Expected deployable surfaces: " + ", ".join(surfaces) + "\n" + "\n".join(targets),
    )
    stack = valid_stack().split("### Coherent Options Presented")[0] + """### Coherent Options Presented
| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-CLI-01 | Toolchain | Python package with pytest | Local command | Team maintains packaging | approved |
| OPT-CLI-02 | Toolchain | Go executable with go test | Standalone binary | Team maintains compilation | rejected |

## CLI and Toolchain Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Language | Python | Approved | Owner decision | Fits team | None |
| Toolchain | Python and build | Approved | Owner decision | Reproducible package | Pin versions |
| Distribution mechanism | Signed wheel | Approved | Owner decision | Direct download | Verify signature |
| Testing | pytest | Approved | Owner decision | Covers commands | None |
"""
    return strictize_approved_package(valid_prd(), architecture, stack)


def commercial_option_package() -> tuple[str, str, str]:
    """Build an approved headless package with comma-containing commercial text."""

    prd = valid_prd()
    prd = prd.replace(
        "| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |",
        "| Monetization Infrastructure Gate | required | Paid usage needs billing surfaces | approved | TEST-001 |",
        1,
    )
    prd = prd.replace(
        "| Partner Channel Gate | not_required | No outside sellers | approved | n/a |",
        "| Partner Channel Gate | required | Outside partners need attribution | approved | TEST-001 |",
        1,
    )
    dependent = {
        "| Monetization model | none | No payer | approved | n/a |":
            "| Monetization model | usage_based | Payers buy metered runs | approved | TEST-001 |",
        "| Pricing and offer | n/a | No offer | approved | n/a |":
            "| Pricing and offer | Usage plan, $20/month base, annual or monthly | Pricing supports metered and committed use | approved | TEST-001 |",
        "| Purchase and entitlement | n/a | No purchase | approved | n/a |":
            "| Purchase and entitlement | Web checkout and entitlement service | Purchases create and revoke entitlements | approved | TEST-001 |",
        "| Merchant of record / tax owner | n/a | No merchant of record | approved | n/a |":
            "| Merchant of record / tax owner | Product company with payment provider | The company owns invoices and refunds | approved | TEST-001 |",
        "| Partner motion | none | No outside partner | approved | n/a |":
            "| Partner motion | Affiliate and referral | Outside partners drive trials | approved | TEST-001 |",
        "| Partner economics and operations | n/a | No channel economics | approved | n/a |":
            "| Partner economics and operations | Commission, payout, and reversal records | Economics stay auditable per partner | approved | TEST-001 |",
    }
    for old, new in dependent.items():
        prd = prd.replace(old, new, 1)
    architecture = valid_architecture().replace(
        "## Monetization and Partner Channel Architecture\n"
        "This section records concrete fixture boundaries, ownership, failure "
        "handling, and implementation responsibilities.",
        "## Monetization and Partner Channel Architecture\n"
        "Purchase and billing events create entitlements; refunds and chargebacks "
        "revoke or restore them. Reconciliation is idempotent. Partner attribution, "
        "commission, payout, provisioning, and termination records remain separate.",
        1,
    )
    stack = valid_stack().split("### Coherent Options Presented")[0] + """### Coherent Options Presented
| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-MP-01 | Monetization or partner channel | Web billing, entitlement service, affiliate, and custom operations | Owned commercial lifecycle | Team owns reconciliation and payouts | approved |
| OPT-MP-02 | Monetization or partner channel | Third-party affiliate and billing platform | Faster launch | External platform owns workflows | rejected |

## Monetization and Partner Channel Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Store commerce / billing | Web billing, annual, monthly | Approved | Owner decision | Supports usage plans | Reconcile webhooks |
| Subscription and entitlement source | Entitlement service | Approved | Owner decision | One lifecycle source | Test revocation |
| Paywall / checkout | Web checkout | Approved | Owner decision | Keeps checkout owned | Preserve tax evidence |
| Merchant of record / tax | Product company | Approved | Owner decision | Owner owns invoices | Track refunds |
| Affiliate / referral / reseller platform | First-party links, commission, payout | Approved | Owner decision | Keeps partner facts local | Audit reversals |
| Attribution, commission, payout, and reseller operations | Ledger, $20 monthly payout, reversal, provisioning, termination | Approved | Owner decision | Matches the approved bundle | Reconcile monthly |
"""
    return strictize_approved_package(prd, architecture, stack)


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
        selected_stack = stack if stack is not None else valid_stack()
        if require_approved:
            selected_prd, selected_architecture, selected_stack = strictize_approved_package(
                selected_prd, selected_architecture, selected_stack
            )
        return check_product_package.validate_texts(
            selected_prd,
            selected_architecture,
            selected_stack,
            require_filled=True,
            require_approved=require_approved,
            repo_root=repo_root,
        )

    def test_approved_package_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_approved_commercial_package_passes(self) -> None:
        prd, architecture, stack = commercial_option_package()
        self.assertEqual([], check_product_package.validate_texts(
            prd, architecture, stack, require_filled=True, require_approved=True,
        ))

    def test_retired_bookkeeping_fields_are_not_checked(self) -> None:
        prd = valid_prd().replace(
            "| --- | --- | --- | --- | --- | --- |\n## Open Questions",
            "| --- | --- | --- | --- | --- | --- |\n| data assumption | impact | owner validation | Owner | 2026-09-12 | accepted |\n## Open Questions",
            1,
        )
        prd, architecture, stack = strictize_approved_package(prd, valid_architecture(), valid_stack())
        stack = stack.replace(
            "<!-- stack-decision-checkpoint:end -->",
            "- Applicable areas: ghost\n- Resolved areas: none\n"
            "- Approved option map: OPT-FE-02=frontend=>mutated\n"
            "<!-- stack-decision-checkpoint:end -->",
            1,
        )
        package = finalize_approval_digests(prd, architecture, stack)
        self.assertEqual([], check_product_package.validate_texts(
            *package, require_filled=True, require_approved=True,
        ))

    def test_toolchain_release_packages_pass_full_approval(self) -> None:
        for classes in (("cli",), ("other_nonpublic",), ("cli", "other_nonpublic")):
            with self.subTest(classes=classes):
                package = toolchain_package(classes)
                self.assertEqual([], check_product_package.validate_texts(
                    *package, require_filled=True, require_approved=True,
                ))

    def test_toolchain_approval_rejects_missing_section_layer_and_unapproved_choice(self) -> None:
        for classes in (("cli",), ("other_nonpublic",)):
            prd, architecture, stack = toolchain_package(classes)
            for candidate, expected in (
                (stack.split("## CLI and Toolchain Decision")[0], "missing required toolchain"),
                (re.sub(r"^\| Testing \|.*\n", "", stack, flags=re.MULTILINE), "missing layers: testing"),
                (stack.replace("| Python | Approved |", "| Python | Recommended |"), "remains 'Recommended'"),
            ):
                with self.subTest(classes=classes, expected=expected):
                    package = strictize_approved_package(prd, architecture, candidate)
                    problems = check_product_package.validate_texts(
                        *package, require_filled=True, require_approved=True,
                    )
                    self.assertIn(expected, "\n".join(problems))

    def test_cli_toolchain_alias_passes_approval(self) -> None:
        prd, architecture, stack = toolchain_package(("cli",))
        stack = re.sub(
            r"(?m)^(- Approved areas: )toolchain$",
            r"\1CLI/toolchain", stack,
        )
        stack = re.sub(r"(?m)^(\| OPT-CLI-\d+ \| )Toolchain(?= \|)", r"\1CLI/toolchain", stack)
        package = finalize_approval_digests(prd, architecture, stack)
        self.assertEqual([], check_product_package.validate_texts(
            *package, require_filled=True, require_approved=True,
        ))

    def test_strict_approval_requires_digests_structured_revision_and_identities(self) -> None:
        prd = valid_prd()
        architecture = valid_architecture().replace("# Architecture: Fixture", "# Architecture", 1)
        stack = valid_stack().replace("# Stack Decisions: Fixture", "# Stack Decisions", 1)
        prd = re.sub(r"^- Package revision:.*\n", "- Package revision: PD-R1\n", prd, flags=re.MULTILINE)
        prd = re.sub(r"^- Package digest:.*\n", "", prd, flags=re.MULTILINE)
        stack = re.sub(r"^- Checkpoint digest:.*\n", "", stack, flags=re.MULTILINE)
        findings = check_product_package.validate_texts(
            prd, architecture, stack, require_filled=True, require_approved=True
        )
        joined = "\n".join(findings)
        self.assertIn("Package digest", joined)
        self.assertIn("non-empty canonical product identity", joined)
        self.assertIn("Checkpoint digest", joined)

    def test_strict_approval_digest_binds_exact_approved_bytes(self) -> None:
        prd, architecture, stack = strictize_approved_package(
            valid_prd(), valid_architecture(), valid_stack()
        )
        mutated = prd.replace(
            "Delivery owners need one observable way",
            "Delivery owners need a different observable way",
            1,
        )
        findings = check_product_package.validate_texts(
            mutated, architecture, stack, require_filled=True, require_approved=True
        )
        self.assertIn("Package digest does not match", "\n".join(findings))

    def test_strict_approval_digest_covers_fenced_indented_and_comment_text(self) -> None:
        extra = (
            "\n```sql\nCREATE TABLE notes (id int);\n```\n"
            "- Retention rule\n    - delete after 30 days\n"
            "<!-- PII stored encrypted -->\n"
        )
        prd, architecture, stack = strictize_approved_package(
            valid_prd() + extra, valid_architecture() + extra, valid_stack() + extra
        )
        self.assertEqual([], check_product_package.validate_texts(
            prd, architecture, stack, require_filled=True, require_approved=True
        ))
        # A CRLF checkout of the same approved text keeps the same digests.
        self.assertEqual([], check_product_package.validate_texts(
            *(text.replace("\n", "\r\n") for text in (prd, architecture, stack)),
            require_filled=True, require_approved=True,
        ))
        for old, new in (
            ("id int", "id bigint"),
            ("delete after 30 days", "keep forever"),
            ("PII stored encrypted", "PII stored in plaintext"),
        ):
            with self.subTest(edit=new):
                for texts in (
                    (prd.replace(old, new), architecture),
                    (prd, architecture.replace(old, new)),
                ):
                    findings = "\n".join(check_product_package.validate_texts(
                        *texts, stack, require_filled=True, require_approved=True,
                    ))
                    self.assertIn("Package digest does not match", findings)
                findings = "\n".join(check_product_package.validate_texts(
                    prd, architecture, stack.replace(old, new),
                    require_filled=True, require_approved=True,
                ))
                self.assertIn("Checkpoint digest does not match", findings)
                self.assertIn("Package digest does not match", findings)

    def test_cli_pass_line_claims_owner_approval_only_when_checked(self) -> None:
        prd, architecture, stack = strictize_approved_package(
            valid_prd(), valid_architecture(), valid_stack()
        )
        blocked = re.sub(r"(?m)^- Decision: approved$", "- Decision: blocked", prd, count=1)
        self.assertNotEqual(prd, blocked)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {"prd": root / "PRD.md", "architecture": root / "architecture.md", "stack": root / "stack-decisions.md"}
            for key, text in (("prd", blocked), ("architecture", architecture), ("stack", stack)):
                paths[key].write_text(text, encoding="utf-8")
            base = ["--prd", str(paths["prd"]), "--architecture", str(paths["architecture"]),
                    "--stack-decisions", str(paths["stack"])]

            def run(*flags: str) -> tuple[int, str]:
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                    code = check_product_package.main([*base, *flags])
                return code, output.getvalue()

            code, output = run()
            self.assertEqual(0, code)
            self.assertIn("approval not checked", output)
            self.assertNotIn("owner-approved", output)
            self.assertEqual(1, run("--require-filled", "--require-approved")[0])
            paths["prd"].write_text(prd, encoding="utf-8")
            code, output = run("--require-filled", "--require-approved")
            self.assertEqual(0, code)
            self.assertIn("complete and owner-approved", output)

    def test_strict_approval_revision_is_an_exact_digest_binding(self) -> None:
        prd, architecture, stack = strictize_approved_package(
            valid_prd(), valid_architecture(), valid_stack()
        )
        digest = re.search(r"Package digest: (sha256:[0-9a-f]{64})", prd).group(1)
        for revision in (
            f"release-PD-R1@{digest}",
            f"PD-R1@{digest}-suffix",
            f"PD-R1@sha256:{'f' * 64}",
        ):
            with self.subTest(revision=revision):
                candidate = re.sub(r"- Package revision:.*", f"- Package revision: {revision}", prd, count=1)
                findings = check_product_package.validate_texts(
                    candidate, architecture, stack, require_filled=True, require_approved=True
                )
                self.assertIn("Package revision", "\n".join(findings))

    def test_strict_approval_requires_exact_approved_areas(self) -> None:
        prd, architecture, stack = strictize_approved_package(
            valid_prd(), valid_architecture(), valid_stack()
        )
        wrong_areas = stack.replace("- Approved areas: none", "- Approved areas: frontend", 1)
        findings = check_product_package.validate_texts(
            prd, architecture, wrong_areas, require_filled=True, require_approved=True
        )
        self.assertIn("Approved areas must exactly match", "\n".join(findings))

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
        ).replace(
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n",
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

    def test_security_parser_returns_contract_and_ignores_inactive_authority(self) -> None:
        contract, errors = check_product_package.parse_security_requirements(valid_prd())
        self.assertEqual([], errors)
        self.assertEqual("required", contract["status"])
        self.assertEqual("executable", contract["scope"])
        self.assertEqual(
            [{"prd_id": "PRD-003", "test_ids": ["TEST-003"]}],
            [
                {
                    "prd_id": row["prd_id"],
                    "test_ids": row["test_ids"],
                }
                for row in contract["requirements"]
            ],
        )

        inactive = valid_prd().replace(
            "Security scope: executable",
            "Security scope: executable\n"
            "```\n"
            "Security Requirements Gate: blocked — inactive example, decided by Owner\n"
            "Security scope: documentation_only\n"
            "| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |\n"
            "```\n",
        )
        contract, errors = check_product_package.parse_security_requirements(inactive)
        self.assertEqual([], errors)
        self.assertEqual("required", contract["status"])

        invalid_contract, invalid_errors = check_product_package.parse_security_requirements(object())
        self.assertEqual({"status": "", "scope": "", "requirements": []}, invalid_contract)
        self.assertTrue(invalid_errors)

    def test_security_contract_rejects_structural_bypasses(self) -> None:
        security_row = (
            "| PRD-003 | Fixture command trust boundary | Untrusted input mutates "
            "run records | Validate input and fail closed without writing | "
            "TEST-003 | Owner | none — no accepted residual risk |"
        )
        mutations = (
            (
                valid_prd().replace(
                    "Security Requirements Gate: required",
                    "Security Requirements Gate: maybe",
                ),
                "missing complete Security Requirements Gate reason or decision owner",
            ),
            (
                valid_prd().replace(
                    "Security scope: executable",
                    "Security scope: executable\nSecurity scope: documentation_only",
                ),
                "Security scope requires exactly one",
            ),
            (
                valid_prd().replace(
                    "Security scope: executable",
                    "Security scope: deployment",
                ),
                "Security scope must be executable or documentation_only",
            ),
            (
                valid_prd().replace(
                    security_row,
                    security_row + "\n" + security_row,
                ),
                "duplicate Security Requirements ID PRD-003",
            ),
            (
                valid_prd().replace(
                    security_row,
                    "| PRD-003 | Fixture command trust boundary | Untrusted input "
                    "mutates run records | Validate input and fail closed without "
                    "writing | TEST-003 | Owner |",
                ),
                "Security Requirements row has 6 cells, expected 7",
            ),
            (
                valid_prd().replace(
                    security_row,
                    "| PRD-003 | [Asset boundary] | [Abuse case] | [Safe failure] "
                    "| TEST-003 | [Owner] | [Residual risk] |",
                ),
                "Security Requirements row contains an empty value or placeholder",
            ),
            (
                valid_prd().replace(security_row + "\n", ""),
                "required Security Requirements table must contain rows",
            ),
        )
        for prd, expected in mutations:
            with self.subTest(expected=expected):
                contract, errors = check_product_package.parse_security_requirements(prd)
                self.assertIn(expected, "\n".join(errors))
                self.assertEqual(
                    {"status": "", "scope": "", "requirements": []}, contract
                )
                self.assertTrue(any(expected in item for item in self.validate(prd=prd)))

        inactive_authority = valid_prd().replace(
            "Security scope: executable",
            "Security scope: executable\n"
            "<!--\n"
            "Security Requirements Gate: blocked — hidden example, decided by Owner\n"
            "-->\n"
            "    Security Requirements Gate: blocked — indented example, decided by Owner\n",
        )
        contract, errors = check_product_package.parse_security_requirements(
            inactive_authority
        )
        self.assertEqual([], errors)
        self.assertEqual("required", contract["status"])
        self.assertEqual("executable", contract["scope"])

        start = valid_prd().index("## Security Requirements")
        end = valid_prd().index("## AI and Automation")
        hidden_only = (
            valid_prd()[:start]
            + valid_prd()[end:]
            + "\n<!--\n"
            + "## Security Requirements\n"
            + "Security Requirements Gate: blocked — hidden example, decided by Owner\n"
            + "Security scope: documentation_only\n"
            + "-->\n"
            + "    ## Security Requirements\n"
            + "    Security Requirements Gate: blocked — indented example, decided by Owner\n"
        )
        contract, errors = check_product_package.parse_security_requirements(hidden_only)
        self.assertEqual(
            {"status": "", "scope": "", "requirements": []}, contract
        )
        self.assertIn("Security Requirements section is required", "\n".join(errors))
        self.assertEqual([], self.validate(prd=hidden_only, require_approved=False))
        self.assertTrue(
            any(
                "Security Requirements section is required" in item
                for item in self.validate(prd=hidden_only)
            )
        )

        blocked = valid_prd().replace(
            "Security Requirements Gate: required",
            "Security Requirements Gate: blocked",
        )
        contract, errors = check_product_package.parse_security_requirements(blocked)
        self.assertEqual([], errors)
        self.assertEqual("blocked", contract["status"])
        self.assertTrue(
            any(
                "Security Requirements Gate is blocked" in item
                for item in self.validate(prd=blocked)
            )
        )

    def test_security_validation_rejects_semantic_bypasses(self) -> None:
        test003 = (
            "| TEST-003 | Deny untrusted fixture input before any write | security | "
            "Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |"
        )
        unrelated_test = valid_prd().replace(
            test003 + "\n## UI Design Handoff Status",
            test003
            + "\n| TEST-004 | Check unrelated command behavior | security | Yes | "
            "PRD-001 | Behavior is observed |\n## UI Design Handoff Status",
        ).replace("| TEST-003 | Owner |", "| TEST-004 | Owner |")
        self.assertTrue(
            any(
                "TEST-004 upstream traces must name the same PRD-003" in item
                for item in self.validate(prd=unrelated_test)
            )
        )

        active_architecture_security = (
            "The fixture command boundary validates input and fails closed without "
            "writes.\n"
            "<!--\nPRD-003 and TEST-003 are hidden here.\n-->\n"
            "    PRD-003 and TEST-003 are indented code.\n"
        )
        architecture = valid_architecture().replace(
            "PRD-003 places the fixture command at a trust boundary: validation "
            "denies untrusted input before the run record is touched.\n"
            "TEST-003 observes that denial: the command returns a validation error "
            "and the record keeps zero writes.",
            active_architecture_security,
        )
        problems = self.validate(architecture=architecture)
        self.assertTrue(
            any(
                "PRD-003 needs an active substantive Auth, Permissions, and Security join"
                in item
                for item in problems
            )
        )
        self.assertTrue(
            any(
                "TEST-003 needs an active substantive Auth, Permissions, and Security join"
                in item
                for item in problems
            )
        )

        for old, new, expected in (
            ("| TEST-003 | Owner |", "| TEST-003 | System |", "must name a human owner"),
            (
                "| none — no accepted residual risk |",
                "| pending incident review |",
                "residual risk must be an explicit decision",
            ),
            (
                "| none — no accepted residual risk |",
                "| unknown residual risk |",
                "residual risk must be an explicit decision",
            ),
        ):
            with self.subTest(expected=expected):
                problems = self.validate(prd=valid_prd().replace(old, new))
                self.assertTrue(any(expected in item for item in problems))

    def test_security_residual_risk_requires_explicit_decision_syntax(self) -> None:
        original = "none — no accepted residual risk"
        for value in (
            "none",
            original,
            "none - no accepted residual risk",
            "accepted — limited retention risk; mitigation pending next release",
        ):
            with self.subTest(value=value):
                self.assertEqual([], self.validate(prd=valid_prd().replace(original, value)))

        for value in (
            "pending incident review",
            "owner review is pending",
            "risk decision is unknown",
            "accepted",
            "accepted —",
            "accepted - short",
        ):
            with self.subTest(value=value):
                problems = self.validate(prd=valid_prd().replace(original, value))
                self.assertTrue(
                    any(
                        "residual risk must be an explicit decision" in item
                        for item in problems
                    ),
                    problems,
                )

        placeholder_problems = self.validate(
            prd=valid_prd().replace(original, "accepted — [risk rationale]")
        )
        self.assertTrue(
            any(
                "residual risk must be an explicit decision" in item
                for item in placeholder_problems
            )
        )

    def test_security_expected_signal_requires_both_observable_assertions(self) -> None:
        original = "denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes)"
        for signal in (
            "The trusted request succeeds and creates a record",
            "The security check returns a result",
            "denial: rejected (validation error returned)",
            "no unauthorized side effects: unchanged (run record has zero writes)",
            "not " + original,
            original.replace("rejected", "accepted"),
            original.replace("unchanged", "changed"),
            original.replace("run record has zero writes", "[state evidence]"),
            "denial: rejected (observable rejection signal); no unauthorized side effects: unchanged (observable state evidence)",
            original + "; denial: accepted (request succeeds)",
        ):
            with self.subTest(signal=signal):
                problems = self.validate(prd=valid_prd().replace(original, signal))
                self.assertIn("TEST-003 security Expected signal must declare", "\n".join(problems))
        self.assertEqual([], self.validate())

    def test_required_security_test_cannot_be_orphaned(self) -> None:
        prd = valid_prd().replace(
            "## UI Design Handoff Status",
            "| TEST-004 | Positive-only security happy path | security | Yes | PRD-003 | Trusted request creates a record |\n## UI Design Handoff Status",
        )
        problems = self.validate(prd=prd)
        self.assertIn("required security TEST-004 must be referenced", "\n".join(problems))
        self.assertIn("TEST-004 security Expected signal must declare", "\n".join(problems))

    def test_documentation_exemption_requires_product_and_architecture_proof(self) -> None:
        prd, architecture = documentation_only_package()
        for description in (
            "A local CLI that processes files", "An autonomous agent workflow",
            "A static site for public readers", "A mobile client application",
        ):
            with self.subTest(description=description):
                problems = self.validate(
                    prd=prd.replace("A documentation-only product contract fixture", description),
                    architecture=architecture,
                )
                self.assertIn("needs a documentation-only", "\n".join(problems))
        problems = self.validate(prd=prd, architecture=valid_architecture())
        self.assertIn("needs a documentation-only", "\n".join(problems))
        for old, new in (
            ("docs/product-definition.md | Record product definition decisions", "Executable CLI | Execute local commands against operator files"),
            ("docs/product-definition.md", "Local binary"),
            ("docs/product-definition.md", "scripts/process.py"),
            ("docs/product-definition.md", "docs/../process.py"),
            ("docs/product-definition.md", "docs/interactive.mdx"),
        ):
            with self.subTest(component=new):
                mutated = architecture.replace(old, new)
                self.assertNotEqual(architecture, mutated)
                self.assertIn("needs a documentation-only", "\n".join(self.validate(prd=prd, architecture=mutated)))
        for heading in ("Product Archetype", "Frontend Architecture", "Backend Architecture", "API and Interface Contracts", "AI and Automation Architecture", "Data Model", "Workflow and Data Flow", "Deployment and Operations"):
            with self.subTest(heading=heading):
                executable = re.sub(
                    rf"(## {re.escape(heading)}\n)[\s\S]*?(?=\n## |\Z)",
                    r"\1A local command executes file processing for the operator.", architecture,
                )
                self.assertIn("needs a documentation-only", "\n".join(self.validate(prd=prd, architecture=executable)))
        self.assertEqual([], self.validate(prd=prd, architecture=architecture))
        self.assertEqual([], self.validate(prd=prd, architecture=architecture.replace(
            "Record product definition decisions",
            "Document the command reference for a separately owned system",
        )))

    def test_security_section_structure_failures(self) -> None:
        duplicate_section = """## Security Requirements
Security Requirements Gate: required — duplicate authority must fail, decided by Owner
Security scope: executable

| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-003 | Fixture command trust boundary | Untrusted input mutates run records | Validate input and fail closed without writing | TEST-003 | Owner | none |
"""
        duplicate_table = """| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |"""
        mutations = (
            (
                valid_prd().replace(
                    "Security Requirements Gate: required — executable fixture input "
                    "can create unsafe writes, decided by Owner\n",
                    "",
                ),
                "Security Requirements Gate requires exactly one active status line",
            ),
            (
                valid_prd().replace(
                    "Security Requirements Gate: required",
                    "Security Requirements Gate: blocked",
                ),
                "Security Requirements Gate is blocked",
            ),
            (
                valid_prd().replace(
                    "Security Requirements Gate: required",
                    "Security Requirements Gate: required\n"
                    "Security Requirements Gate: required",
                ),
                "exactly one active status line",
            ),
            (
                valid_prd().replace(
                    "## AI and Automation",
                    duplicate_section + "\n## AI and Automation",
                ),
                "duplicate Security Requirements section",
            ),
            (
                valid_prd().replace(
                    "| PRD-003 | Fixture command trust boundary | Untrusted input "
                    "mutates run records | Validate input and fail closed without "
                    "writing | TEST-003 | Owner | none — no accepted residual risk |",
                    "| PRD-003 | Fixture command trust boundary | Untrusted input "
                    "mutates run records | Validate input and fail closed without "
                    "writing | TEST-003 | Owner | none — no accepted residual risk |\n"
                    + duplicate_table,
                ),
                "duplicate Security Requirements table header",
            ),
        )
        for prd, expected in mutations:
            with self.subTest(expected=expected):
                problems = self.validate(prd=prd)
                self.assertIn(expected, "\n".join(problems))

    def test_security_rows_require_known_required_security_tests_and_owners(self) -> None:
        optional_prd = valid_prd().replace(
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n"
            "## UI Design Handoff Status",
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n"
            "| TEST-004 | Inspect optional denial behavior | security | No | PRD-003 | Denied request returns validation error |\n"
            "## UI Design Handoff Status",
        ).replace("| TEST-003 | Owner |", "| TEST-004 | Owner |")
        should_prd = valid_prd().replace(
            "| PRD-001 | Complete the fixture | Must | Completion is observable |\n",
            "| PRD-001 | Complete the fixture | Must | Completion is observable |\n"
            "| PRD-004 | Add optional fixture behavior | Should | Behavior is observable |\n",
        ).replace(
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n",
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n"
            "| TEST-004 | Check optional behavior | security | Yes | PRD-004 | Optional behavior is observed |\n",
        ).replace(
            "| PRD-003 | Fixture command trust boundary | Untrusted input mutates "
            "run records | Validate input and fail closed without writing | TEST-003 "
            "| Owner |",
            "| PRD-004 | Fixture command trust boundary | Untrusted input mutates "
            "run records | Validate input and fail closed without writing | TEST-004 "
            "| Owner |",
        )
        self.assertIn(
            "| TEST-004 | Inspect optional denial behavior | security | No | PRD-003 |",
            optional_prd,
        )
        contract, errors = check_product_package.parse_security_requirements(optional_prd)
        self.assertEqual([], errors)
        self.assertEqual(
            [{"prd_id": "PRD-003", "test_ids": ["TEST-004"]}],
            [{"prd_id": row["prd_id"], "test_ids": row["test_ids"]} for row in contract["requirements"]],
        )
        mutations = (
            (optional_prd, "references optional TEST-004"),
            (
                valid_prd().replace("| TEST-003 | Owner |", "| TEST-999 | Owner |"),
                "optional or unknown TEST-999",
            ),
            (
                valid_prd().replace("| TEST-003 | Owner |", "| TEST-001 | Owner |"),
                "TEST-001 must have Test type security",
            ),
            (
                valid_prd().replace(
                    "| PRD-003 | Fixture command trust boundary",
                    "| PRD-999 | Fixture command trust boundary",
                ),
                "must reference one existing Must or applicable NFR PRD ID",
            ),
            (should_prd, "must reference one existing Must or applicable NFR PRD ID"),
            (
                valid_prd().replace("| TEST-003 | Owner |", "| TEST-003 | AI |"),
                "must name a human owner",
            ),
        )
        for prd, expected in mutations:
            with self.subTest(expected=expected):
                problems = self.validate(prd=prd)
                self.assertIn(expected, "\n".join(problems))

    def test_security_architecture_requires_substantive_prd_and_test_joins(self) -> None:
        for identifier in ("PRD-003", "TEST-003"):
            with self.subTest(identifier=identifier):
                architecture = valid_architecture().replace(
                    f"{identifier} ",
                    "",
                    1,
                )
                problems = self.validate(architecture=architecture)
                self.assertIn(
                    "active substantive Auth, Permissions, and Security join",
                    "\n".join(problems),
                )

    def test_security_scope_is_human_owned_and_release_aware(self) -> None:
        documentation_prd, documentation_architecture = documentation_only_package()
        contract, errors = check_product_package.parse_security_requirements(
            documentation_prd
        )
        self.assertEqual([], errors)
        self.assertEqual("not_required", contract["status"])
        self.assertEqual("documentation_only", contract["scope"])
        self.assertEqual([], contract["requirements"])
        self.assertEqual(
            [],
            self.validate(prd=documentation_prd, architecture=documentation_architecture),
        )

        security_table_start = valid_prd().index(
            "| PRD ID | Asset / trust boundary | Abuse case | "
            "Control / safe failure | TEST IDs | Owner | Residual risk |"
        )
        security_table_end = valid_prd().index("## AI and Automation")
        security_table = (
            valid_prd()[security_table_start:security_table_end].rstrip() + "\n"
        )
        moved_table = documentation_prd.replace(
            "## AI and Automation",
            "## AI and Automation\n" + security_table,
        )
        contract, errors = check_product_package.parse_security_requirements(moved_table)
        self.assertEqual(
            ["prd: Security Requirements table must stay inside its own section"],
            errors,
        )
        self.assertEqual(
            {"status": "", "scope": "", "requirements": []}, contract
        )
        self.assertTrue(
            any(
                "Security Requirements table must stay inside its own section" in item
                for item in self.validate(
                    prd=moved_table,
                    architecture=documentation_architecture,
                )
            )
        )

        self.assertEqual([], self.validate())

        executable_not_required = documentation_prd.replace(
            "Security scope: documentation_only",
            "Security scope: executable",
        )
        problems = self.validate(
            prd=executable_not_required,
            architecture=documentation_architecture,
        )
        self.assertIn(
            "not_required Security Requirements Gate requires documentation_only "
            "scope",
            "\n".join(problems),
        )

        problems = self.validate(
            prd=documentation_prd,
            architecture=release_architecture(),
        )
        self.assertIn(
            "deployable surfaces require the Security Requirements Gate to be required",
            "\n".join(problems),
        )

        self.assertEqual([], self.validate(architecture=release_architecture()))

        blocked = valid_prd().replace(
            "Security Requirements Gate: required",
            "Security Requirements Gate: blocked",
        )
        architectures = (valid_architecture(), release_architecture())
        for architecture_index, architecture in enumerate(architectures):
            with self.subTest(release_targets=architecture_index == 1):
                blocked_prd, blocked_architecture, blocked_stack = strictize_approved_package(
                    blocked,
                    architecture,
                    valid_stack(),
                )
                self.assertEqual(
                    [],
                    self.validate(
                        prd=blocked_prd,
                        architecture=blocked_architecture,
                        stack=blocked_stack,
                        require_approved=False,
                    ),
                )
                self.assertTrue(
                    any(
                        "Security Requirements Gate is blocked" in item
                        for item in self.validate(
                            prd=blocked_prd,
                            architecture=blocked_architecture,
                            stack=blocked_stack,
                        )
                    )
                )

        old_prd = valid_prd()
        old_section_start = old_prd.index("## Security Requirements")
        old_section_end = old_prd.index("## AI and Automation")
        old_prd = old_prd[:old_section_start] + old_prd[old_section_end:]
        self.assertEqual(
            [],
            check_product_package.validate_texts(
                old_prd,
                valid_architecture(),
                valid_stack(),
                require_filled=True,
                require_approved=False,
            ),
        )

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
| Security | unchanged | none | none |
| Monetization / partner | unchanged | none | none |
| Release / operations | unchanged | none | none |
"""
        prd = valid_prd(mode="enhancement").replace(
            "## Problem Statement",
            impacts + "\n## Problem Statement",
        )
        problems = self.validate(prd=prd)
        self.assertTrue(
            any("non-none refresh" in item for item in problems)
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

    def test_ui_design_v3_operations_reach_every_surface_and_leave_every_opened_state(self) -> None:
        def op(identifier, source, surface, state, presentation="page"):
            return {"id": identifier, "trigger": identifier, "control": identifier.lower(),
                    "sourceState": source, "destination": {"surface": surface, "state": state},
                    "presentation": presentation}

        def findings(home_ops, detail_ops, contract="ui-design/3"):
            base = ui_contract()
            block = base[base.index("### UI-001"):base.index("<!-- ui-surface-contract:end -->")]
            detail = (block.replace("### UI-001 — Home", "### UI-002 — Detail")
                      .replace("/home", "/detail")
                      .replace("- `states`: ready", "- `states`: ready, confirm, saved"))
            values = [ops if isinstance(ops, str) else json.dumps(ops) for ops in (home_ops, detail_ops)]
            contract_text = base.replace(
                block, block + f"- `operations`: {values[0]}\n" + detail + f"- `operations`: {values[1]}\n"
            )
            prd = valid_prd().replace(
                "UI design: not_required — fixture is headless\nUI decision owner: n/a for headless",
                "UI design: pending explicit ui-design-builder request\nUI decision owner: Product owner",
            ) + contract_text
            problems = check_product_package.validate_texts(
                prd, valid_architecture(), valid_stack(), ui_contract=contract
            )
            return [item for item in problems if "entry surface" in item or "exit operation" in item]

        home = [op("OP-open", "ready", "UI-002", "ready")]
        detail = [
            op("OP-home", "ready", "UI-001", "ready"),
            op("OP-delete", "ready", "UI-002", "confirm", "overlay"),
            op("OP-cancel", "confirm", "UI-002", "ready", "state"),
            op("OP-save", "ready", "UI-002", "saved", "feedback"),
        ]
        self.assertEqual([], findings(home, detail))

        unreachable = findings([op("OP-refresh", "ready", "UI-001", "ready")], detail)
        self.assertIn(
            "prd: UI surface UI-002 is not reachable from entry surface UI-001 through operations",
            unreachable,
        )
        # A self-loop does not leave its state.
        self.assertIn("prd: UI surface UI-001 state ready has no exit operation", unreachable)
        self.assertEqual([], findings([op("OP-refresh", "ready", "UI-001", "ready")], detail, "ui-design/2"))

        trapped = findings(home, [row for row in detail if row["id"] != "OP-cancel"])
        self.assertEqual(["prd: UI surface UI-002 state confirm has no exit operation"], trapped)

        terminal = findings(home, "none — read-only receipt with no product controls")
        self.assertEqual([], terminal)

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

    def test_at_a_glance_accepts_a_delivery_profile_row(self) -> None:
        with_profile = valid_prd().replace(
            "| Biggest risk |",
            "| Delivery profile | mvp |\n| Biggest risk |",
            1,
        )
        self.assertEqual(
            [],
            [item for item in self.validate(prd=with_profile) if "At a Glance" in item],
        )

        bad_value = with_profile.replace(
            "| Delivery profile | mvp |", "| Delivery profile | fast |", 1
        )
        self.assertTrue(
            any(
                "'Delivery profile' must be one of: mvp, standard" in item
                for item in self.validate(prd=bad_value)
            )
        )

        duplicate = with_profile.replace(
            "| Biggest risk |", "| Delivery profile | standard |\n| Biggest risk |", 1
        )
        self.assertTrue(
            any(
                "exactly its five canonical rows" in item
                for item in self.validate(prd=duplicate)
            )
        )

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
            r"(## Non-Functional Requirements\n\| ID[^\n]*\n\| ---[^\n]*\n)"
            r"\| PRD-002[^\n]*\n\| PRD-003[^\n]*\n",
            r"\1",
            valid_prd(),
        ).replace(
            "| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |\n",
            "",
        ).replace(
            "| TEST-003 | Deny untrusted fixture input before any write | security | Yes | PRD-003 | denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes) |\n",
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

    def test_release_source_marker_selects_dual_branch_protocol(self) -> None:
        legacy, legacy_findings = parse_release_targets(release_architecture())
        self.assertEqual([], legacy_findings)
        self.assertEqual("candidate/1", legacy.source_policy_protocol)
        self.assertEqual(
            "run.integration.branch", legacy.targets[0].source_policy.split("ref=")[1].split(";")[0]
        )

        dual = release_architecture().replace(
            "## Release Targets\n",
            "## Release Targets\n\nRelease source policy: dual-branch/1\n",
        )
        dual = re.sub(
            r"^- Source policy: stage=development; .*$",
            "- Source policy: stage=development; ref=refs/heads/development; "
            "sha=promotion.verified_development_sha",
            dual,
            count=1,
            flags=re.MULTILINE,
        )
        parsed, findings = parse_release_targets(dual)
        self.assertEqual([], findings)
        self.assertEqual("dual-branch/1", parsed.source_policy_protocol)
        self.assertEqual(
            "refs/heads/development",
            parsed.targets[0].source_policy.split("ref=")[1].split(";")[0],
        )

        forged = dual.replace(
            "Release source policy: dual-branch/1",
            "Release source policy: dual-branch/1 forged",
            1,
        )
        legacy_for_marker, findings = parse_release_targets(forged)
        self.assertTrue(
            any(
                "must be stage=development; ref=run.integration.branch" in item
                for item in findings
            )
        )
        self.assertEqual("candidate/1", legacy_for_marker.source_policy_protocol)
        self.assertEqual(
            "refs/heads/development",
            legacy_for_marker.targets[0].source_policy.split("ref=")[1].split(";")[0],
        )

        duplicated = dual.replace(
            "## Release Targets\n",
            "## Release Targets\n\nRelease source policy: dual-branch/1\n",
            1,
        )
        duplicated_contract, findings = parse_release_targets(duplicated)
        self.assertEqual("candidate/1", duplicated_contract.source_policy_protocol)
        self.assertTrue(
            any("at most one active Release source policy marker" in item for item in findings)
        )

    def test_main_preview_sources_use_candidate_and_reject_development_branch(self) -> None:
        preview = release_architecture().replace(
            "## Release Targets\n",
            "## Release Targets\n\nRelease source policy: main-preview/1\n",
        )
        parsed, findings = parse_release_targets(preview)
        self.assertEqual([], findings)
        self.assertEqual("main-preview/1", parsed.source_policy_protocol)
        wrong_source = preview.replace(
            "ref=run.integration.branch; sha=run.integration.integration_head_sha",
            "ref=refs/heads/development; sha=promotion.verified_development_sha",
        )
        self.assertTrue(parse_release_targets(wrong_source)[1])
        mixed = preview.replace(
            "Release source policy: main-preview/1",
            "Release source policy: main-preview/1\nRelease source policy: dual-branch/1",
        )
        self.assertTrue(parse_release_targets(mixed)[1])

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
| Security | unchanged | none | none |
| Monetization / partner | unchanged | none | none |
| Release / operations | unchanged | none | none |
"""
        prd = valid_prd(mode="enhancement").replace(
            "## Problem Statement", impacts + "\n## Problem Statement"
        )
        problems = self.validate(prd=prd)
        self.assertTrue(any("structured affected IDs" in item for item in problems))
        self.assertTrue(any("non-none refresh" in item for item in problems))

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
            fixture_prd, fixture_architecture, fixture_stack = strictize_approved_package(
                valid_prd(), valid_architecture(), valid_stack()
            )
            prd.write_text(fixture_prd, encoding="utf-8")
            architecture.write_text(fixture_architecture, encoding="utf-8")
            stack.write_text(fixture_stack, encoding="utf-8")
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
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("owner-approved", result.stdout)


AMBITION_SECTION = """## Ambition
### Goal Beyond The Goal
| Rung | Outcome | Outside judge |
| --- | --- | --- |
| 1 | Ship the fixture gate reliably | The delivery owner signs each run log |
| 2 | The fixture gate becomes the team default | Peer teams adopt the checker |
| 3 | Contract gates are cited outside the team | External teams reference the checker |

### Depth
| Best practitioners | Their instruments | Rawest material | Stretch target | Outside judge |
| --- | --- | --- | --- | --- |
| Contract tooling maintainers | Schema checkers and CI gates | Rejected package reports | Zero false approvals across seasons | The delivery owner audits findings |

### Range
Verbs: validate, reject, gate
| Field | What they actually do here | Method or tool | Used as |
| --- | --- | --- | --- |
| Package review | Review rejected findings weekly | Unit test suites | design input |
| Release planning | Weigh gate findings against launch dates | Roadmap reviews | review lens |

### Access
| Need | Present or missing | Unlocks |
| --- | --- | --- |
| Run logs from peer teams | missing | Adoption evidence for rung 2 |
"""

DELTA_EIR = """## Enhancement Impact Record
| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | changed | PRD-001 | PRD.md and Product Definition Approval |
| UI structure / style | none | none | none |
| Data / integrations | unchanged | none | none |
| Architecture / stack | unchanged | none | none |
| Data trust / AI | unchanged | none | none |
| Security | unchanged | none | none |
| Monetization / partner | unchanged | none | none |
| Release / operations | unchanged | none | none |
"""


def delta_mode_prd(
    *,
    ambition: bool = True,
    stretch_metrics: bool = True,
    latest_line: str = "docs/product/deltas/PRD-DELTA-EPIC-041.md",
) -> str:
    prd = valid_prd()
    if ambition:
        prd = prd.replace(
            "- Reject incomplete authority before implementation starts.\n## Non-Goals",
            "- Reject incomplete authority before implementation starts.\n"
            + AMBITION_SECTION
            + "## Non-Goals",
            1,
        )
    if stretch_metrics:
        prd = prd.replace(
            "| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| Completion | Completed runs | 0 | 90% | 30 days | Event count | Owner |",
            "| Metric | Definition | Baseline | Target / guardrail | Stretch | Measurement window | Source / method | Owner |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| Completion | Completed runs | 0 | 90% | 99% | 30 days | Event count | Owner |",
            1,
        )
    if latest_line is not None:
        prd = prd.replace(
            "## Product Definition Decisions\n### Research Gate",
            "## Product Definition Decisions\n"
            f"Latest delta: {latest_line}\n### Research Gate",
            1,
        )
    return prd


def delta_document(
    *,
    epic_id: str = "EPIC-041",
    status: str = "approved",
    result: str = "pending",
    changed_rows: str = "| PRD-001 | revised | Complete the fixture | Harden completion evidence with a signed run log | TEST-001 |",
    impact: str = DELTA_EIR,
    decision: str | None = None,
    blocking_items: str = "none",
) -> str:
    decision_value = (
        decision
        if decision is not None
        else (status if status in {"approved", "revision_requested", "blocked"} else "draft")
    )
    return f"""# PRD Delta {epic_id}: Harden the fixture gate

| | |
| --- | --- |
| Epic | docs/epics/{epic_id}-fixture-gate.md |
| Baseline PRD | sha256:{"a" * 64} |
| Result PRD | {result} |
| Status | {status} |
| Ambition rung | 2 — The fixture gate becomes the team default |

## Why
Peer teams reject the fixture gate as unproven; one hardened revision answers the adoption blocker.

{impact}
## Changed Requirements
| ID | Change | Before | After | TEST IDs |
| --- | --- | --- | --- | --- |
{changed_rows}

## Decisions
The owner approved hardening completion evidence before wider adoption.

## Approval
<!-- product-definition-approval:start -->
### Delta Approval
- Decision: {decision_value}
- Decision owner: Owner
- Decided on: 2026-09-12
- Blocking items: {blocking_items}
<!-- product-definition-approval:end -->
"""


class DeltaAmbitionPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def finalize(self, prd: str) -> tuple[str, str, str]:
        return strictize_approved_package(prd, valid_architecture(), valid_stack())

    def result_digest(self, package: tuple[str, str, str]) -> str:
        return contract_utils.sha256_text(
            contract_utils._without_machine_block(
                package[0],
                check_product_package.PRODUCT_APPROVAL_START,
                check_product_package.PRODUCT_APPROVAL_END,
            )
        )

    def write_deltas(self, deltas: dict[str, str]) -> Path:
        deltas_dir = self.root / "deltas"
        deltas_dir.mkdir()
        for name, text in deltas.items():
            (deltas_dir / name).write_text(text, encoding="utf-8")
        return deltas_dir

    def write_epic(self, name: str = "EPIC-041-fixture-gate.md") -> Path:
        repo_root = self.root / "repo"
        epics = repo_root / "docs" / "epics"
        epics.mkdir(parents=True, exist_ok=True)
        (epics / name).write_text("# Epic: fixture gate\n", encoding="utf-8")
        return repo_root

    def validate(
        self,
        package: tuple[str, str, str],
        *,
        deltas: dict[str, str] | None = None,
        repo_root: Path | None = None,
        require_approved: bool = True,
        notes: list[str] | None = None,
    ) -> list[str]:
        deltas_dir = self.write_deltas(deltas) if deltas is not None else None
        return check_product_package.validate_texts(
            *package,
            require_filled=True,
            require_approved=require_approved,
            repo_root=repo_root,
            deltas_dir=deltas_dir,
            notes=notes,
        )

    def test_legacy_package_reports_one_informational_line(self) -> None:
        notes: list[str] = []
        self.assertEqual([], self.validate(self.finalize(valid_prd()), notes=notes))
        self.assertEqual(1, len(notes))
        self.assertIn("legacy", notes[0])

    def test_delta_mode_package_passes(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(result=f"sha256:{self.result_digest(package)}")
        repo_root = self.write_epic()
        notes: list[str] = []
        self.assertEqual(
            [], self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta}, repo_root=repo_root, notes=notes)
        )
        self.assertEqual([], notes)

    def test_delta_mode_rejects_dated_prd_heading(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace(
                "## Problem Statement\n", "## Problem Statement\n### Reassessed 2026-10-01\n", 1
            )
        )
        delta = delta_document(result=f"sha256:{self.result_digest(package)}")
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(any("dated heading" in finding for finding in findings), findings)

    def test_delta_mode_rejects_enhancement_impact_record_in_prd(self) -> None:
        package = self.finalize(delta_mode_prd() + "\n" + DELTA_EIR)
        delta = delta_document(result=f"sha256:{self.result_digest(package)}")
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(
            any("Enhancement Impact Record in PRD deltas, not PRD.md" in finding for finding in findings),
            findings,
        )

    def test_delta_mode_rejects_result_prd_hash_mismatch(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(result=f"sha256:{"b" * 64}")
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(any("Result PRD hash does not match" in finding for finding in findings), findings)

    def test_delta_mode_rejects_missing_revised_id(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(
            result=f"sha256:{self.result_digest(package)}",
            changed_rows="| PRD-099 | revised | old | new obligations and wording | none |",
        )
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(any("PRD-099 is absent from PRD.md" in finding for finding in findings), findings)

    def test_delta_mode_rejects_retired_id_still_present(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(
            result=f"sha256:{self.result_digest(package)}",
            changed_rows="| PRD-001 | retired | Complete the fixture | none | none |",
        )
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(
            any("retired ID PRD-001 is still present in PRD.md" in finding for finding in findings),
            findings,
        )

    def test_delta_mode_rejects_missing_test_id(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(
            result=f"sha256:{self.result_digest(package)}",
            changed_rows="| PRD-001 | revised | Complete the fixture | Harden completion evidence | TEST-999 |",
        )
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(any("unknown TEST-999" in finding for finding in findings), findings)

    def test_delta_mode_require_approved_rejects_draft_status(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(status="draft", result=f"sha256:{self.result_digest(package)}")
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta}, require_approved=True)
        self.assertTrue(any("Status must be approved" in finding for finding in findings), findings)

    def test_delta_mode_rejects_blocked_delta_approval(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(
            result=f"sha256:{self.result_digest(package)}",
            decision="blocked",
            blocking_items="unresolved",
        )
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta}, require_approved=True)
        self.assertTrue(any("Decision must be approved" in finding for finding in findings), findings)
        self.assertTrue(any("Blocking items must be none" in finding for finding in findings), findings)

    def test_delta_mode_rejects_incomplete_delta_approval(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(result=f"sha256:{self.result_digest(package)}").replace(
            "- Decision owner: Owner" + chr(10),
            "",
            1,
        )
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta}, require_approved=True)
        self.assertTrue(
            any("missing required field 'Decision owner'" in finding for finding in findings),
            findings,
        )

    def test_delta_mode_accepts_retired_ids_in_the_impact_record(self) -> None:
        package = self.finalize(delta_mode_prd())
        delta = delta_document(
            result=f"sha256:{self.result_digest(package)}",
            changed_rows="| PRD-099 | retired | Previous requirement | none | none |",
            impact=DELTA_EIR.replace(
                "| Product scope / behavior | changed | PRD-001 |",
                "| Product scope / behavior | changed | PRD-099 |",
                1,
            ),
        )
        self.assertEqual([], self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta}))

    def test_ambition_package_without_deltas_passes(self) -> None:
        package = self.finalize(delta_mode_prd(latest_line=None))
        notes: list[str] = []
        self.assertEqual([], self.validate(package, notes=notes))
        self.assertEqual([], notes)

    def test_ambition_rejects_missing_rung(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace(
                "| 3 | Contract gates are cited outside the team | External teams reference the checker |\n",
                "",
                1,
            )
        )
        findings = self.validate(package)
        self.assertTrue(any("missing rung(s) 3" in finding for finding in findings), findings)

    def test_ambition_rejects_empty_judge_cell(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace(
                "| 1 | Ship the fixture gate reliably | The delivery owner signs each run log |",
                "| 1 | Ship the fixture gate reliably |  |",
                1,
            )
        )
        findings = self.validate(package)
        self.assertTrue(
            any("Goal Beyond The Goal row contains an empty value" in finding for finding in findings),
            findings,
        )

    def test_ambition_rejects_verbs_content_borrowed_from_the_next_line(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace("Verbs: validate, reject, gate", "Verbs:", 1)
        )
        findings = self.validate(package)
        self.assertTrue(any("non-empty 'Verbs:' line" in finding for finding in findings), findings)

    def test_ambition_rejects_an_empty_range_crew_table(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace(
                "| Package review | Review rejected findings weekly | Unit test suites | design input |"
                + chr(10)
                + "| Release planning | Weigh gate findings against launch dates | Roadmap reviews | review lens |"
                + chr(10),
                "",
                1,
            )
        )
        findings = self.validate(package)
        self.assertTrue(any("Range crew table" in finding for finding in findings), findings)

    def test_ambition_rejects_bad_range_used_as(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace("| Roadmap reviews | review lens |", "| Roadmap reviews | marketing |", 1)
        )
        findings = self.validate(package)
        self.assertTrue(
            any("Used as must be design input, review lens or go-to-market" in finding for finding in findings),
            findings,
        )

    def test_ambition_rejects_missing_stretch_metrics_column(self) -> None:
        package = self.finalize(delta_mode_prd(latest_line=None, stretch_metrics=False))
        findings = self.validate(package)
        self.assertTrue(
            any("Metrics must add the Stretch column" in finding for finding in findings),
            findings,
        )

    def test_delta_mode_rejects_duplicate_latest_delta_lines(self) -> None:
        package = self.finalize(
            delta_mode_prd().replace(
                "## Product Definition Decisions" + chr(10),
                "## Product Definition Decisions" + chr(10)
                + "Latest delta: docs/product/deltas/PRD-DELTA-EPIC-041.md" + chr(10),
                1,
            )
        )
        delta = delta_document(result=f"sha256:{self.result_digest(package)}")
        findings = self.validate(package, deltas={"PRD-DELTA-EPIC-041.md": delta})
        self.assertTrue(any("exactly once" in finding for finding in findings), findings)

    def test_delta_mode_requires_the_latest_delta_file(self) -> None:
        package = self.finalize(delta_mode_prd())
        findings = self.validate(
            package,
            deltas={"PRD-DELTA-EPIC-042.md": delta_document(epic_id="EPIC-042")},
        )
        self.assertTrue(any("Latest delta file" in finding for finding in findings), findings)

    def test_ambition_must_immediately_follow_goals(self) -> None:
        package = self.finalize(
            delta_mode_prd(latest_line=None).replace(
                "- Reject incomplete authority before implementation starts.\n" + AMBITION_SECTION,
                "- Reject incomplete authority before implementation starts.\n",
                1,
            ).replace(
                "## Risks\n",
                AMBITION_SECTION + "## Risks\n",
                1,
            )
        )
        findings = self.validate(package)
        self.assertTrue(
            any("'## Ambition' must immediately follow '## Goals'" in finding for finding in findings),
            findings,
        )


if __name__ == "__main__":
    unittest.main()
