from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
SKILL_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_activation  # noqa: E402


SHA = "a" * 40
ARTIFACT = "web-build-1"
BINDING = f"web-prod@{SHA}#{ARTIFACT}"
TARGET = "google_analytics/account-1/property-2/stream-3"

VALID_PRD = """# PRD: Example

## Metrics
| Metric | Definition | Target |
| --- | --- | --- |
| Activation rate | Users completing setup | 70% in 14 days |

## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Setup succeeds | operational | Yes | PRD-001 | One verified setup event |
| TEST-002 | Nice to have | unit | No | PRD-002 | Optional signal |
"""


def task_fields(
    task_id: str = "ACT-001",
    *,
    depends_on: str = "none",
    status: str = "verified",
    evidence_ids: str = "EVID-001, EVID-002, EVID-003",
) -> dict[str, str]:
    fields = {
        "Source refs": "PRD-001, TEST-001",
        "Release bindings": BINDING,
        "Depends on": depends_on,
        "Operation": "update",
        "Target": TARGET,
        "Environment": "production",
        "Precondition": "stream is absent",
        "Desired state": "production web stream exists",
        "Secret names": "none",
        "Risk tags": "none",
        "Risk": "high",
        "Confirmation": "action_time_confirmation",
        "Execution route": "browser",
        "Execution capability": "CAP-001",
        "Read-back route": "browser",
        "Read-back capability": "CAP-001",
        "Authorization": "consumed" if status in {"configured", "verified", "uncertain"} else "approved",
        "Authorization source": "owner approved ACT-001 on 2026-09-07",
        "Action digest": "pending",
        "Authorized digest": "pending",
        "Required": "yes",
        "Status": status,
        "Verification": "Realtime contains one setup event",
        "Evidence IDs": evidence_ids,
        "Blocker / N/A reason": "none",
        "Updated": "2026-09-07T18:00:00Z",
    }
    digest = check_activation.action_digest(task_id, fields)
    fields["Action digest"] = digest
    fields["Authorized digest"] = digest
    return fields


def task_block(task_id: str, fields: dict[str, str], title: str = "Create production stream") -> str:
    lines = [f"### {task_id} — {title}", ""]
    lines.extend(f"- {name}: {fields[name]}" for name in check_activation.TASK_FIELDS)
    return "\n".join(lines)


def valid_record(*, task_blocks: list[str] | None = None) -> str:
    default_fields = task_fields()
    blocks = task_blocks or [task_block("ACT-001", default_fields)]
    rendered_blocks = chr(10).join(blocks)
    digest_match = next(
        (
            line.removeprefix("- Action digest: ")
            for line in rendered_blocks.splitlines()
            if line.startswith("- Action digest: ")
        ),
        default_fields["Action digest"],
    )
    execution_route = next(
        (
            line.removeprefix("- Execution route: ")
            for line in rendered_blocks.splitlines()
            if line.startswith("- Execution route: ")
        ),
        "browser",
    )
    readback_route = next(
        (
            line.removeprefix("- Read-back route: ")
            for line in rendered_blocks.splitlines()
            if line.startswith("- Read-back route: ")
        ),
        "browser",
    )
    write_kind = "manual" if execution_route == "manual" else "write"
    return f"""# Product Activation

## Record
- Schema: product-activation/1
- Product: Example
- Activation owner: product owner
- Release reference: v1.0.0
- Status: handoff_ready
- Updated: 2026-09-07T18:00:00Z
- Measurement window starts: 2026-09-07T18:00:00Z

## Applied Profiles
| Profile | Applies | Reason | Owner |
| --- | --- | --- | --- |
| core | yes | shared baseline | product owner |
| web | yes | public web release | web owner |

## Capability Observations
| Observation ID | Route | Status | Supports | Target scope | Environment | Checked | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAP-001 | browser | available | read, write, readback | {TARGET} | production | 2026-09-07T17:55:00Z | account and property read back |
| CAP-002 | manual | human_only | read, write, readback | {TARGET} | production | 2026-09-07T17:55:00Z | owner present |

## Outcome Coverage
| Signal | Definition / target | Window | Release targets | Source ID | Status |
| --- | --- | --- | --- | --- | --- |
| Activation rate | Users completing setup; 70% target | 14 days | web-prod | MS-001 | verified |
| TEST-001 | One verified setup event | release smoke | web-prod | MS-001 | verified |

## Measurement Sources
| MS ID | Target | Environment | Retrieval | Route / capability | Release bindings | Owner | Status | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-001 | {TARGET} | production | GA4 Realtime setup event query | browser;CAP-001 | {BINDING} | analytics owner | verified | EVID-004 |

## Activation Tasks
<!-- activation-task-contract:start -->
{rendered_blocks}
<!-- activation-task-contract:end -->

## Verification Evidence
| Evidence ID | Item ID | Kind | Route / action / release binding | Checked | Result | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| EVID-001 | ACT-001 | {write_kind} | {execution_route};{digest_match};{BINDING} | 2026-09-07T18:00:00Z | PASS | stream create receipt without secrets |
| EVID-002 | ACT-001 | readback | {readback_route};{digest_match};{BINDING} | 2026-09-07T18:01:00Z | PASS | stream ID visible after refresh |
| EVID-003 | ACT-001 | behavior | {readback_route};{digest_match};{BINDING} | 2026-09-07T18:02:00Z | PASS | one setup event in Realtime |
| EVID-004 | MS-001 | readback | browser;n/a;{BINDING} | 2026-09-07T18:02:00Z | PASS | bounded Realtime query returned event |

## Manual Handoff
| Item ID | Owner | Exact step | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| ACT-001 | n/a | n/a | n/a | n/a |

## Target Readiness
| Release target | Source SHA | Artifact / build identity | Status | Checked | Blockers |
| --- | --- | --- | --- | --- | --- |
| web-prod | {SHA} | {ARTIFACT} | ready | 2026-09-07T18:03:00Z | none |

## Open Blockers
| Blocker ID | Release targets | Kind | Owner | Next step | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
"""


class ActivationCheckerTests(unittest.TestCase):
    def test_template_is_structurally_valid_but_not_filled(self) -> None:
        template = (SKILL_ROOT / "assets" / "templates" / "ACTIVATION.template.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], check_activation.check_activation_text(template))
        self.assertIn(
            "unresolved placeholder",
            "\n".join(check_activation.check_activation_text(template, require_filled=True)),
        )

    def test_verified_record_passes_prd_source_and_target_checks(self) -> None:
        findings = check_activation.check_activation_text(
            valid_record(),
            prd_text=VALID_PRD,
            require_verified_sources=True,
            require_ready=("web-prod",),
        )
        self.assertEqual([], findings)

    def test_verified_source_mode_implies_filled_validation(self) -> None:
        record = valid_record().replace("- Product: Example", "- Product: <fill>")
        self.assertIn(
            "unresolved placeholder",
            "\n".join(
                check_activation.check_activation_text(
                    record, prd_text=VALID_PRD, require_verified_sources=True
                )
            ),
        )

    def test_outcome_source_must_cover_the_same_release_target(self) -> None:
        record = valid_record().replace(
            f"| MS-001 | {TARGET} | production | GA4 Realtime setup event query | browser;CAP-001 | {BINDING} |",
            f"| MS-001 | {TARGET} | production | GA4 Realtime setup event query | browser;CAP-001 | other-prod@{SHA}#{ARTIFACT} |",
        )
        self.assertIn(
            "does not cover every target",
            "\n".join(check_activation.check_activation_text(record)),
        )

    def test_prd_coverage_rejects_missing_and_unknown_signals(self) -> None:
        missing = valid_record().replace(
            "| TEST-001 | One verified setup event | release smoke | web-prod | MS-001 | verified |\n",
            "| UNKNOWN | Other | release smoke | web-prod | MS-001 | verified |\n",
        )
        joined = "\n".join(
            check_activation.check_activation_text(missing, prd_text=VALID_PRD)
        )
        self.assertIn("missing PRD signal TEST-001", joined)
        self.assertIn("unknown PRD signal UNKNOWN", joined)

    def test_action_digest_detects_target_drift(self) -> None:
        stale = valid_record().replace(
            f"- Target: {TARGET}",
            "- Target: google_analytics/account-1/property-9/stream-3",
            1,
        )
        self.assertIn(
            "Action digest does not match",
            "\n".join(check_activation.check_activation_text(stale)),
        )

    def test_unknown_dependency_and_cycle_fail(self) -> None:
        first = task_fields(depends_on="ACT-002")
        second = task_fields("ACT-002", depends_on="ACT-001")
        second["Authorization source"] = "owner approved ACT-002 on 2026-09-07"
        second_digest = check_activation.action_digest("ACT-002", second)
        second["Action digest"] = second_digest
        second["Authorized digest"] = second_digest
        record = valid_record(
            task_blocks=[
                task_block("ACT-001", first),
                task_block("ACT-002", second, "Link destination"),
            ]
        )
        joined = "\n".join(check_activation.check_activation_text(record))
        self.assertIn("dependency cycle", joined)

    def test_verified_task_requires_separate_readback_and_behavior(self) -> None:
        fields = task_fields(evidence_ids="EVID-001")
        joined = "\n".join(
            check_activation.check_activation_text(
                valid_record(task_blocks=[task_block("ACT-001", fields)])
            )
        )
        self.assertIn("PASS readback evidence", joined)
        self.assertIn("PASS behavior evidence", joined)

    def test_manual_handoff_needs_a_matching_completed_row(self) -> None:
        fields = task_fields(status="configured")
        fields["Risk"] = "handoff"
        fields["Confirmation"] = "user_handoff"
        fields["Execution route"] = "manual"
        fields["Execution capability"] = "CAP-002"
        fields["Authorization"] = "handoff_complete"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        record = valid_record(task_blocks=[task_block("ACT-001", fields)]).replace(
            "| ACT-001 | n/a | n/a | n/a | n/a |",
            "| OTHER | owner | enter secret | read-back | completed |",
        )
        self.assertIn(
            "needs a Manual Handoff row",
            "\n".join(check_activation.check_activation_text(record)),
        )

    def test_secret_patterns_are_rejected(self) -> None:
        unsafe = valid_record() + "\nAuthorization: Bearer visible-token\n"
        self.assertIn(
            "bearer credential",
            "\n".join(check_activation.check_activation_text(unsafe)),
        )

    def test_common_github_and_stripe_secret_patterns_are_rejected(self) -> None:
        for secret in (
            "github_pat_11AA22_bbCC33ddEE44ffGG55",
            "sk_test_51AA22bbCC33ddEE44",
        ):
            with self.subTest(secret=secret.split("_")[0]):
                unsafe = valid_record() + f"\nleaked: {secret}\n"
                self.assertIn(
                    "known secret value pattern",
                    "\n".join(check_activation.check_activation_text(unsafe)),
                )

    def test_task_evidence_is_bound_to_current_digest_route_and_artifact(self) -> None:
        stale_digest = valid_record().replace(
            f"browser;{task_fields()['Action digest']};{BINDING}",
            f"browser;{'b' * 64};{BINDING}",
            1,
        )
        self.assertIn(
            "stale action digest",
            "\n".join(check_activation.check_activation_text(stale_digest)),
        )
        stale_artifact = valid_record().replace(
            f"browser;{task_fields()['Action digest']};{BINDING}",
            f"browser;{task_fields()['Action digest']};web-prod@{SHA}#old-build",
            1,
        )
        self.assertIn(
            "another release binding",
            "\n".join(check_activation.check_activation_text(stale_artifact)),
        )

    def test_measurement_evidence_is_bound_to_release_and_uses_no_action_digest(self) -> None:
        stale = valid_record().replace(
            f"browser;n/a;{BINDING}",
            f"browser;n/a;web-prod@{SHA}#old-build",
        )
        self.assertIn(
            "another release binding",
            "\n".join(check_activation.check_activation_text(stale)),
        )
        task_digest = valid_record().replace(
            f"browser;n/a;{BINDING}",
            f"browser;{task_fields()['Action digest']};{BINDING}",
        )
        self.assertIn(
            "must use action digest n/a",
            "\n".join(check_activation.check_activation_text(task_digest)),
        )

    def test_capability_must_match_exact_target_and_route(self) -> None:
        wrong_target = valid_record().replace(
            f"| CAP-001 | browser | available | read, write, readback | {TARGET} | production |",
            "| CAP-001 | browser | available | read, write, readback | google_analytics/another-account | production |",
        )
        joined = "\n".join(check_activation.check_activation_text(wrong_target))
        self.assertIn("capability does not match the exact target", joined)

        wrong_route = valid_record().replace(
            f"| CAP-001 | browser | available | read, write, readback | {TARGET} | production |",
            f"| CAP-001 | api | available | read, write, readback | {TARGET} | production |",
        )
        self.assertIn(
            "capability uses another route",
            "\n".join(check_activation.check_activation_text(wrong_route)),
        )

    def test_capability_must_match_the_exact_environment(self) -> None:
        fields = task_fields()
        fields["Environment"] = "live"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        joined = "\n".join(
            check_activation.check_activation_text(
                valid_record(task_blocks=[task_block("ACT-001", fields)])
            )
        )
        self.assertIn("execution capability does not match the environment", joined)
        self.assertIn("read-back capability does not match the environment", joined)

    def test_prod_and_live_environment_aliases_default_to_high_risk(self) -> None:
        for environment in ("prod", "live", "production-preview"):
            with self.subTest(environment=environment):
                fields = task_fields()
                fields["Environment"] = environment
                fields["Risk"] = "standard"
                fields["Confirmation"] = "exact_preapproval"
                digest = check_activation.action_digest("ACT-001", fields)
                fields["Action digest"] = digest
                fields["Authorized digest"] = digest
                joined = "\n".join(
                    check_activation.check_activation_text(
                        valid_record(task_blocks=[task_block("ACT-001", fields)])
                    )
                )
                self.assertIn("non-preview operation requires high risk", joined)

    def test_sensitive_target_requires_an_explicit_risk_tag(self) -> None:
        fields = task_fields()
        fields["Environment"] = "preview"
        fields["Target"] = "cloudflare/account-1/zone-2/dns/record-3"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        self.assertIn(
            "requires explicit dns risk tag",
            "\n".join(
                check_activation.check_activation_text(
                    valid_record(task_blocks=[task_block("ACT-001", fields)])
                )
            ),
        )

    def test_sensitive_resource_can_be_checked_read_only(self) -> None:
        dns_target = "cloudflare/account-1/zone-2/dns/record-3"
        fields = task_fields(evidence_ids="EVID-002, EVID-003")
        fields["Operation"] = "read"
        fields["Target"] = dns_target
        fields["Risk"] = "read_only"
        fields["Confirmation"] = "read_only"
        fields["Authorization"] = "not_required"
        fields["Authorization source"] = "none"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        record = valid_record(task_blocks=[task_block("ACT-001", fields)]).replace(
            TARGET, dns_target
        )
        record = "\n".join(
            line for line in record.splitlines() if "| EVID-001 |" not in line
        )
        self.assertEqual([], check_activation.check_activation_text(record, prd_text=VALID_PRD))

    def test_high_impact_operation_cannot_use_standard_preapproval(self) -> None:
        fields = task_fields()
        fields["Operation"] = "delete"
        fields["Environment"] = "preview"
        fields["Risk"] = "standard"
        fields["Confirmation"] = "exact_preapproval"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        joined = "\n".join(
            check_activation.check_activation_text(
                valid_record(task_blocks=[task_block("ACT-001", fields)])
            )
        )
        self.assertIn("delete operation requires high risk", joined)

    def test_manual_execution_cannot_use_standard_preapproval(self) -> None:
        fields = task_fields(status="configured")
        fields["Environment"] = "preview"
        fields["Execution route"] = "manual"
        fields["Execution capability"] = "CAP-002"
        fields["Risk"] = "standard"
        fields["Confirmation"] = "exact_preapproval"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        self.assertIn(
            "manual or human-only execution requires handoff risk",
            "\n".join(
                check_activation.check_activation_text(
                    valid_record(task_blocks=[task_block("ACT-001", fields)])
                )
            ),
        )

    def test_verified_mutation_requires_write_evidence(self) -> None:
        fields = task_fields(evidence_ids="EVID-002, EVID-003")
        joined = "\n".join(
            check_activation.check_activation_text(
                valid_record(task_blocks=[task_block("ACT-001", fields)])
            )
        )
        self.assertIn("verified task needs PASS write or manual evidence", joined)

    def test_readback_and_behavior_must_follow_the_write(self) -> None:
        record = valid_record().replace(
            "| 2026-09-07T18:01:00Z | PASS | stream ID visible after refresh |",
            "| 2025-09-07T18:01:00Z | PASS | stream ID visible after refresh |",
        ).replace(
            "| 2026-09-07T18:02:00Z | PASS | one setup event in Realtime |",
            "| 2025-09-07T18:02:00Z | PASS | one setup event in Realtime |",
        )
        joined = "\n".join(check_activation.check_activation_text(record))
        self.assertIn("readback evidence", joined)
        self.assertIn("must follow write evidence", joined)
        self.assertIn("predates its capability probe", joined)

    def test_later_failed_readback_invalidates_an_earlier_pass(self) -> None:
        fields = task_fields(
            evidence_ids="EVID-001, EVID-002, EVID-003, EVID-005"
        )
        record = valid_record(task_blocks=[task_block("ACT-001", fields)]).replace(
            f"| EVID-003 | ACT-001 | behavior | browser;{fields['Action digest']};{BINDING} | 2026-09-07T18:02:00Z | PASS | one setup event in Realtime |",
            f"| EVID-003 | ACT-001 | behavior | browser;{fields['Action digest']};{BINDING} | 2026-09-07T18:02:00Z | PASS | one setup event in Realtime |\n"
            f"| EVID-005 | ACT-001 | readback | browser;{fields['Action digest']};{BINDING} | 2026-09-07T18:04:00Z | FAIL | stream missing after refresh |",
        )
        joined = "\n".join(
            check_activation.check_activation_text(
                record, prd_text=VALID_PRD, require_verified_sources=True
            )
        )
        self.assertIn("needs distinct PASS readback evidence", joined)
        self.assertIn("readiness check predates its verification evidence", joined)

    def test_measurement_source_cannot_be_verified_by_manual_evidence(self) -> None:
        record = valid_record().replace(
            "| EVID-004 | MS-001 | readback |",
            "| EVID-004 | MS-001 | manual |",
        )
        self.assertIn(
            "verified source MS-001 needs PASS evidence",
            "\n".join(check_activation.check_activation_text(record)),
        )

    def test_later_failed_source_readback_invalidates_an_earlier_pass(self) -> None:
        record = valid_record().replace(
            "| analytics owner | verified | EVID-004 |",
            "| analytics owner | verified | EVID-004, EVID-006 |",
        ).replace(
            f"| EVID-004 | MS-001 | readback | browser;n/a;{BINDING} | 2026-09-07T18:02:00Z | PASS | bounded Realtime query returned event |",
            f"| EVID-004 | MS-001 | readback | browser;n/a;{BINDING} | 2026-09-07T18:02:00Z | PASS | bounded Realtime query returned event |\n"
            f"| EVID-006 | MS-001 | readback | browser;n/a;{BINDING} | 2026-09-07T18:05:00Z | FAIL | bounded Realtime query lost the event |",
        )
        joined = "\n".join(
            check_activation.check_activation_text(
                record, prd_text=VALID_PRD, require_verified_sources=True
            )
        )
        self.assertIn("verified source MS-001 needs PASS evidence", joined)
        self.assertIn("readiness check predates its verification evidence", joined)

    def test_bare_verification_na_is_not_a_reason(self) -> None:
        fields = task_fields(evidence_ids="EVID-001, EVID-002")
        fields["Verification"] = "n/a"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        self.assertIn(
            "Verification n/a needs a reason",
            "\n".join(
                check_activation.check_activation_text(
                    valid_record(task_blocks=[task_block("ACT-001", fields)])
                )
            ),
        )

    def test_strict_gate_rejects_pending_action_and_outcome_fields(self) -> None:
        fields = task_fields()
        fields["Precondition"] = "pending"
        fields["Desired state"] = "pending"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        record = valid_record(task_blocks=[task_block("ACT-001", fields)]).replace(
            "| Users completing setup; 70% target | 14 days |",
            "| pending | pending |",
        )
        joined = "\n".join(
            check_activation.check_activation_text(
                record, prd_text=VALID_PRD, require_verified_sources=True
            )
        )
        self.assertIn("filled task needs Precondition", joined)
        self.assertIn("filled task needs Desired state", joined)
        self.assertIn("Outcome Coverage: Activation rate needs Definition / target", joined)
        self.assertIn("Outcome Coverage: Activation rate needs Window", joined)

    def test_handoff_ready_requires_every_active_target(self) -> None:
        fields = task_fields()
        fields["Release bindings"] = f"{BINDING}, other-prod@{SHA}#other-build"
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        joined = "\n".join(
            check_activation.check_activation_text(
                valid_record(task_blocks=[task_block("ACT-001", fields)])
            )
        )
        self.assertIn("missing active target other-prod", joined)

    def test_open_target_and_global_blockers_prevent_handoff(self) -> None:
        marker = """## Open Blockers
| Blocker ID | Release targets | Kind | Owner | Next step | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
"""
        for targets in ("web-prod", "all"):
            with self.subTest(targets=targets):
                record = valid_record().replace(
                    marker,
                    marker
                    + f"| BLOCK-001 | {targets} | access_gap | owner | restore access | open | login unavailable |\n",
                    1,
                )
                joined = "\n".join(check_activation.check_activation_text(record))
                self.assertIn("handoff_ready cannot have open blockers", joined)
                self.assertIn("has open blocker", joined)

    def test_resolved_blocker_does_not_prevent_readiness(self) -> None:
        marker = """## Open Blockers
| Blocker ID | Release targets | Kind | Owner | Next step | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
"""
        record = valid_record().replace(
            marker,
            marker
            + "| BLOCK-001 | web-prod | access_gap | owner | restored | resolved | access restored |\n",
            1,
        )
        self.assertEqual([], check_activation.check_activation_text(record, prd_text=VALID_PRD))

    def test_typed_artifact_identity_and_partial_pending_rules(self) -> None:
        ios_binding = f"web-prod@{SHA}#appstore-build-123"
        fields = task_fields()
        fields["Release bindings"] = ios_binding
        digest = check_activation.action_digest("ACT-001", fields)
        fields["Action digest"] = digest
        fields["Authorized digest"] = digest
        ios = valid_record(task_blocks=[task_block("ACT-001", fields)]).replace(
            BINDING, ios_binding
        ).replace(
            f"| web-prod | {SHA} | {ARTIFACT} |",
            f"| web-prod | {SHA} | appstore-build-123 |",
        )
        self.assertEqual([], check_activation.check_activation_text(ios, prd_text=VALID_PRD))
        malformed = valid_record().replace(BINDING, f"web-prod@pending#{ARTIFACT}", 1)
        self.assertIn(
            "partial pending identity",
            "\n".join(check_activation.check_activation_text(malformed)),
        )

    def test_action_digest_changes_with_artifact_and_execution_capability(self) -> None:
        base = task_fields()
        base_digest = check_activation.action_digest("ACT-001", base)
        artifact_changed = dict(base)
        artifact_changed["Release bindings"] = f"web-prod@{SHA}#other-build"
        capability_changed = dict(base)
        capability_changed["Execution capability"] = "CAP-002"
        self.assertNotEqual(
            base_digest, check_activation.action_digest("ACT-001", artifact_changed)
        )
        self.assertNotEqual(
            base_digest, check_activation.action_digest("ACT-001", capability_changed)
        )

    def test_verified_source_gate_requires_prd(self) -> None:
        self.assertIn(
            "verified-source handoff requires the current PRD",
            "\n".join(
                check_activation.check_activation_text(
                    valid_record(), require_verified_sources=True
                )
            ),
        )

    def test_act_heading_outside_boundaries_is_rejected(self) -> None:
        record = valid_record() + "\n### ACT-999 — hidden action\n"
        self.assertIn(
            "outside the task-contract boundaries",
            "\n".join(check_activation.check_activation_text(record)),
        )

    def test_ready_target_rejects_unverified_required_task(self) -> None:
        fields = task_fields(status="configured")
        record = valid_record(task_blocks=[task_block("ACT-001", fields)])
        self.assertIn(
            "unverified task ACT-001",
            "\n".join(check_activation.check_activation_text(record)),
        )

    def test_cli_exit_codes_and_digest_output(self) -> None:
        script = SCRIPTS_DIR / "check_activation.py"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ACTIVATION.md"
            path.write_text(valid_record(), encoding="utf-8")
            passed = subprocess.run(
                [sys.executable, str(script), "--activation", str(path), "--show-action-digests"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
            self.assertIn("ACT-001", passed.stdout)
            missing = subprocess.run(
                [sys.executable, str(script), "--activation", str(Path(temp) / "missing.md")],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, missing.returncode)
            strict_without_prd = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--activation",
                    str(path),
                    "--require-verified-sources",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, strict_without_prd.returncode)
            self.assertIn("requires --prd", strict_without_prd.stderr)


if __name__ == "__main__":
    unittest.main()
