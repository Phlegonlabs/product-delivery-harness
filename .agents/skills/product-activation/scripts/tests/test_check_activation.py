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
        "Release bindings": f"web-prod@{SHA}",
        "Depends on": depends_on,
        "Operation": "update",
        "Target": "google_analytics/account-1/property-2/stream-3",
        "Environment": "production",
        "Precondition": "stream is absent",
        "Desired state": "production web stream exists",
        "Secret names": "none",
        "Risk": "standard",
        "Confirmation": "exact_preapproval",
        "Execution route": "browser",
        "Read-back route": "browser",
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
    blocks = task_blocks or [task_block("ACT-001", task_fields())]
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
| Route | Status | Supports | Surface | Target context | Checked | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| browser | available | read, write, readback | signed-in browser | confirmed | 2026-09-07T17:55:00Z | account and property read back |
| manual | available | read, write, readback | user handoff | confirmed | 2026-09-07T17:55:00Z | owner present |

## Outcome Coverage
| Signal | Definition / target | Window | Release targets | Source ID | Status |
| --- | --- | --- | --- | --- | --- |
| Activation rate | Users completing setup; 70% target | 14 days | web-prod | MS-001 | verified |
| TEST-001 | One verified setup event | release smoke | web-prod | MS-001 | verified |

## Measurement Sources
| MS ID | System / retrieval | Route | Release targets | Owner | Status | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- |
| MS-001 | GA4 Realtime setup event query | browser | web-prod | analytics owner | verified | EVID-004 |

## Activation Tasks
<!-- activation-task-contract:start -->
{chr(10).join(blocks)}
<!-- activation-task-contract:end -->

## Verification Evidence
| Evidence ID | Item ID | Kind | Checked | Result | Route | Reference |
| --- | --- | --- | --- | --- | --- | --- |
| EVID-001 | ACT-001 | write | 2026-09-07T18:00:00Z | PASS | browser | stream create receipt without secrets |
| EVID-002 | ACT-001 | readback | 2026-09-07T18:01:00Z | PASS | browser | stream ID visible after refresh |
| EVID-003 | ACT-001 | behavior | 2026-09-07T18:02:00Z | PASS | browser | one setup event in Realtime |
| EVID-004 | MS-001 | readback | 2026-09-07T18:02:00Z | PASS | browser | bounded Realtime query returned event |

## Manual Handoff
| Item ID | Owner | Exact step | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| ACT-001 | n/a | n/a | n/a | n/a |

## Target Readiness
| Release target | Release identity | Status | Checked | Blockers |
| --- | --- | --- | --- | --- |
| web-prod | {SHA} | ready | 2026-09-07T18:03:00Z | none |

## Open Blockers
- none
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
            "| MS-001 | GA4 Realtime setup event query | browser | web-prod |",
            "| MS-001 | GA4 Realtime setup event query | browser | other-prod |",
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
        stale = valid_record().replace("property-2/stream-3", "property-9/stream-3", 1)
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


if __name__ == "__main__":
    unittest.main()
