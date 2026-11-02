"""A minimal program package: program files plus kernel/KRN and inventory/INV.

Built from the checker's own single-product fixtures, so the program files
stay valid against the existing checker as it changes. Expected values in
tests are written out literally; nothing here calls program_package.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import contract_utils  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    valid_architecture,
    valid_prd,
    valid_stack,
)

MODULES = (("kernel", "KRN"), ("inventory", "INV"))

PROGRAM_SECTIONS = """## Module Map
| Module | Scope | Name | Owns | Depends on | Order | Status |
| --- | --- | --- | --- | --- | --- | --- |
| kernel | KRN | Shared kernel | Party, item, currency | none | 1 | approved |
| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |
## Shared Data
| Entity | Owner module | Readers | Identity key | Change rule |
| --- | --- | --- | --- | --- |
| Party | kernel | inventory | party_id | Owner writes; readers keep party_id |
## Glossary
| Term | Definition | Owning module | Avoid |
| --- | --- | --- | --- |
| Item | A stocked product | kernel | product |
| Receipt | Goods booked into a warehouse | inventory | delivery |
## Permission Matrix
### Roles
| Role | Description | Scope |
| --- | --- | --- |
| kernel-admin | Maintains master data | Company |
| warehouse-clerk | Posts receipts | Own warehouse |
| warehouse-manager | Approves stock adjustments | All warehouses |
### Segregation of Duties
| Duty A | Duty B | Rule | TEST ID |
| --- | --- | --- | --- |
| inventory:post-receipt | inventory:approve-adjustment | No role holds both | TEST-PRG-009 |
## Capacity Assumptions
| Driver | Value | Basis | NFR IDs |
| --- | --- | --- | --- |
| Peak concurrent users | 150 | Interviews, 400 named users | PRD-PRG-021 |
| Transactions per day | 120,000 | Last 12 months of legacy volume | PRD-PRG-022 |
## Integrations Register
| External system | Direction and cadence | Idempotency key | Reconciliation report | Error queue owner | Modules | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |
| Carrier API | Outbound, hourly | shipment_id | Daily carrier report | Warehouse manager | inventory | TEST-INV-004 |
## Business Processes
| Process | Modules in order | TEST IDs |
| --- | --- | --- |
| goods-receipt | kernel, inventory | TEST-E2E-001 |
"""

PROGRAM_NFR_ROWS = (
    "| PRD-PRG-021 | Performance | Peak concurrent users | p95 response time | 150 users under 2 s | TEST-PRG-004 |\n"
    "| PRD-PRG-022 | Scalability | Daily transaction volume | Transactions per day | 120,000 per day | TEST-PRG-005 |\n"
)

PROGRAM_TEST_ROWS = (
    "| TEST-PRG-004 | Hold the peak user load on fixture PF-BASE | performance | Yes | PRD-PRG-021 | p95 stays under 2 s |\n"
    "| TEST-PRG-005 | Hold the daily volume on fixture PF-BASE | scalability | Yes | PRD-PRG-022 | All 120,000 postings complete |\n"
    "| TEST-PRG-009 | No role holds both duties of a pair | integration | Yes | PRD-PRG-001 | The role report lists no role with both duties |\n"
    "| TEST-E2E-001 | Goods receipt on fixture PF-BASE from party to stock | E2E | Yes | PRD-PRG-001 | Stock value equals expected/receipt.json |\n"
)

PERIOD_CLOSE_TEST_ROW = (
    "| TEST-E2E-002 | Period close on fixture PF-BASE after the receipt run | E2E | Yes | PRD-PRG-002 | Close succeeds only when sub-ledgers reconcile |\n"
)

MIGRATION_TEST_ROWS = "".join(
    f"| TEST-MIG-00{n} | {text} | migration | Yes | PRD-PRG-001 | {signal} |\n"
    for n, text, signal in (
        (1, "Dress rehearsal on a copy of the legacy data", "Every control total matches"),
        (2, "Re-running the load adds no duplicates", "Row counts stay equal"),
        (3, "Parallel run of three cycles", "Legacy and new differ only in explained rows"),
        (4, "Rollback rehearsal restores legacy", "Legacy runs within the stated time"),
    )
)

CARRIER_INTEGRATION = (
    "| System | Purpose | Data exchanged | Auth / scopes | Contract / limits | Failure / recovery | Owner |\n"
    "| --- | --- | --- | --- | --- | --- | --- |\n"
    "| Carrier API | Ship stock | Shipment notices | API key | 60 calls per minute | Retry then queue | Warehouse manager |\n"
)

BUSINESS_RULES = """## Business Rules
| ID | Trigger | Condition | Outcome | Exceptions | Owner | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |
| BR-{scope}-001 | Fixture package submitted | Package lacks owner approval | Package is rejected | none | Delivery owner | TEST-{scope}-004 |
"""

DOCUMENT_STATES = """### Document States
Document: Stock receipt. Terminal states: Posted, Cancelled.
| From | To | Action | Who may trigger | Side effects | Guard |
| --- | --- | --- | --- | --- | --- |
| Draft | Posted | Post | warehouse-clerk | Adds stock to the ledger | BR-INV-001 |
"""

MODULE_EXTRAS = """## Permission Matrix
| Role | Action | Data scope | Condition |
| --- | --- | --- | --- |
{permissions}## Reports
| PRD ID | Report | Audience | Filters | Source entities | Freshness | Export |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-{scope}-001 | Fixture completion | Delivery owner | Date range | Fixture run | Daily | CSV |
"""

PERMISSIONS = {
    "KRN": "| kernel-admin | kernel:maintain-party | Company | none |\n",
    "INV": (
        "| warehouse-clerk | inventory:post-receipt | Own warehouse | Within BR-INV-001 |\n"
        "| warehouse-manager | inventory:approve-adjustment | All warehouses | none |\n"
    ),
}


def replace(text: str, old: str, new: str) -> str:
    assert old in text, f"fixture anchor missing: {old!r}"
    return text.replace(old, new, 1)


def _before(text: str, anchor: str, block: str) -> str:
    return replace(text, anchor, block + anchor)


def _scoped(text: str, scope: str) -> str:
    return re.sub(r"\b(PRD|UX|UI|ARCH|TEST)-(\d{3})\b", rf"\1-{scope}-\2", text)


def program_prd() -> str:
    prd = _scoped(valid_prd(), "PRG")
    prd = replace(
        prd,
        "| Biggest risk | A malformed contract could appear approved |\n",
        "| Biggest risk | A malformed contract could appear approved |\n| Delivery profile | program |\n",
    )
    prd = _before(prd, "## UX Requirements\n", PROGRAM_NFR_ROWS)
    prd = _before(prd, "## Test Obligations\n", PROGRAM_SECTIONS)
    return _before(prd, "## UI Design Handoff Status\n", PROGRAM_TEST_ROWS)


def program_architecture() -> str:
    architecture = _scoped(valid_architecture(), "PRG")
    architecture = replace(
        architecture,
        "## Integrations\nnot_required — the fixture has no external system integration.\n",
        "## Integrations\n" + CARRIER_INTEGRATION,
    )
    return _before(
        architecture,
        "## Release Targets\n",
        "## Migration and Cutover\nnot_required — greenfield program with no legacy data to load.\n",
    )


def module_prd(scope: str, revision: str) -> str:
    prd = _scoped(valid_prd(), scope)
    prd = _before(prd, "## Problem Statement\n", f"Program revision: {revision}\n")
    rules = BUSINESS_RULES.format(scope=scope) + (DOCUMENT_STATES if scope == "INV" else "")
    prd = replace(
        prd,
        "## Business Rules\nOnly an exact human-approved package may become implementation authority.\n",
        rules,
    )
    if scope == "INV":
        prd = replace(prd, "| Yes | PRD-INV-001 | Completion observed |", "| Yes | PRD-INV-001, PRD-KRN-001 | Completion observed |")
    prd = _before(prd, "## Test Obligations\n", MODULE_EXTRAS.format(scope=scope, permissions=PERMISSIONS[scope]))
    return _before(
        prd,
        "## UI Design Handoff Status\n",
        f"| TEST-{scope}-004 | Reject an unapproved fixture package | integration | Yes | PRD-{scope}-001, BR-{scope}-001 | Rejection is observable |\n",
    )


def program_files() -> dict[str, str]:
    """Relative path under docs/product -> text for the whole program."""

    prd = program_prd()
    # Hash the canonical bytes directly so tests do not share program_package's path.
    revision = "sha256:" + hashlib.sha256(contract_utils.canonical_product_bytes(prd, "", "")).hexdigest()
    files = {
        "PRD.md": prd,
        "architecture.md": program_architecture(),
        "stack-decisions.md": valid_stack(),
    }
    for module_id, scope in MODULES:
        files[f"modules/{module_id}/PRD.md"] = module_prd(scope, revision)
        files[f"modules/{module_id}/architecture.md"] = _scoped(valid_architecture(), scope)
    return files


def edit(files: dict[str, str], name: str, old: str, new: str) -> None:
    files[name] = replace(files[name], old, new)


def write_program(root: Path, files: dict[str, str]) -> Path:
    """Write the files under root/docs/product and return that directory."""

    product_root = root / "docs" / "product"
    for name, text in files.items():
        path = product_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return product_root
