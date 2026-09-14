from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILLS_ROOT = SCRIPTS_DIR.parents[1]
ACTIVATION_TEST_PATH = (
    SKILLS_ROOT / "product-activation" / "scripts" / "tests" / "test_check_activation.py"
)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_outcome_review  # noqa: E402


spec = importlib.util.spec_from_file_location("activation_fixtures", ACTIVATION_TEST_PATH)
activation_fixtures = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(activation_fixtures)


PRD = activation_fixtures.VALID_PRD
ARCHITECTURE = activation_fixtures.ARCHITECTURE
DEPLOYMENT = activation_fixtures.DEPLOYMENT
ACTIVATION = activation_fixtures.valid_record()
SHA = activation_fixtures.SHA
ARTIFACT = activation_fixtures.ARTIFACT
ACTIVATION_SHA256 = hashlib.sha256(ACTIVATION.encode("utf-8")).hexdigest()


def valid_outcome(*, verdict: str = "no_change") -> str:
    incident = """| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |"""
    if verdict == "incident":
        incident = """| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| checkout failures | rollout halted | Incident owner | PRD Risks: checkout reliability | PRD Open Questions: retain staged rollout? | MS-001 |"""
    return f"""# Outcome Review

## Record
- Schema: outcome-review/1
- Product: Example
- Outcome owner: Product owner
- Production release target: web-prod
- Release SHA: {SHA}
- Artifact / build identity: {ARTIFACT}
- Deployment identity: fixture-web;fixture-production-route;{ARTIFACT}
- Deployment checked: 2026-09-07T18:04:00Z
- Deployment status: PASS
- Activation record: docs/ACTIVATION.md
- Activation sha256: {ACTIVATION_SHA256}
- Reviewed on: 2026-09-10
- Verdict: {verdict}

## Activation Sources
| MS ID | Release binding | Owner | Verified at | Evidence |
| --- | --- | --- | --- | --- |
| MS-001 | web-prod@{SHA}#{ARTIFACT} | analytics owner | 2026-09-07T18:02:00Z | EVID-004 bounded verified query |

## Measurements
| Signal | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- |
| Activation rate | none recorded | 70% in 14 days | 2026-09-07 | 2026-09-09 | 72% | MS-001 |
| TEST-001 | none recorded | One verified setup event | 2026-09-07 | 2026-09-09 | 18 events | MS-001 |

## Feedback
| Fact | Source ID | Observed |
| --- | --- | --- |
| Setup completion exceeded target | MS-001 | 72% |

## Incident Response
{incident}

## Verdict
Verdict: {verdict} — measured outcomes met the reviewed target

## Open Follow-ups
| Follow-up | Route |
| --- | --- |
| none | none |
"""


class OutcomeReviewTests(unittest.TestCase):
    def check(self, outcome: str) -> list[str]:
        # Outcome tests isolate the Outcome contract; the activation gate is
        # covered by the dedicated Product Activation suite.
        with patch("check_outcome_review.check_activation_text", return_value=[]):
            return check_outcome_review.check_outcome_review_text(
                outcome,
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
            )

    def test_valid_outcome_is_bound_to_verified_release(self) -> None:
        self.assertEqual([], self.check(valid_outcome()))

    def test_schema2_direct_review_is_accepted(self) -> None:
        self.assertEqual([], self.check(valid_outcome().replace("outcome-review/1", "outcome-review/2", 1)))

    def test_schema2_review_can_run_with_approved_stack_and_deployment_gate(self) -> None:
        with patch("check_outcome_review.check_activation_text", return_value=[]), patch(
            "check_product_package.validate_texts", return_value=[]
        ), patch("check_deployment.check_deployment_text", return_value=[]):
            findings = check_outcome_review.check_outcome_review_text(
                valid_outcome().replace("outcome-review/1", "outcome-review/2", 1),
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
                stack_text="# Stack Decisions: Example",
            )
        self.assertEqual([], findings)

    def test_multi_target_prefix_and_first_target_projection_are_exact(self) -> None:
        multi = valid_outcome().replace(
            "- Production release target: web-prod",
            "- Production release target: web-prod\n- Production release targets: web-prod, other-prod",
            1,
        )
        # The checker must fail closed even before it can inspect target rows.
        findings = "\n".join(self.check(multi))
        self.assertIn("exact `target-set:` prefix", findings)

    def test_single_target_mode_rejects_active_multi_target_tables_and_placeholders(self) -> None:
        target_reviews = (
            "\n## Target Reviews\n"
            "| Release target | Release SHA | Artifact / build identity | Deployment identity | Deployment checked | Deployment status | Activation sources | Verdict |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| [target] | [sha] | [artifact] | [deployment] | [time] | [status] | [sources] | [verdict] |\n"
        )
        target_measurements = (
            "\n## Target Measurements\n"
            "| Signal | Release target | Baseline | Target | Window start | Window end | Actual | Source ID |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| [signal] | [target] | [baseline] | [target] | [start] | [end] | [actual] | [source] |\n"
        )
        findings = "\n".join(self.check(valid_outcome() + target_reviews + target_measurements))
        self.assertIn("single-target reviews cannot carry active Target Reviews", findings)
        self.assertIn("single-target reviews cannot carry active Target Measurements", findings)

    def test_duplicate_record_field_is_rejected(self) -> None:
        duplicate = valid_outcome().replace(
            "- Verdict: no_change\n",
            "- Verdict: no_change\n- Verdict: no_change\n",
            1,
        )
        self.assertIn("Record: duplicate field verdict", "\n".join(self.check(duplicate)))

    def test_enhancement_verdict_requires_enhancement_follow_up(self) -> None:
        enhancement = valid_outcome(verdict="enhancement")
        findings = "\n".join(self.check(enhancement))
        self.assertIn("enhancement verdict requires an enhancement request", findings)

    def test_same_day_measurement_window_is_rejected(self) -> None:
        same_day = valid_outcome().replace(
            "2026-09-07 | 2026-09-09",
            "2026-09-07 | 2026-09-07",
        )
        self.assertIn("window must elapse after deployment", "\n".join(self.check(same_day)))

    def test_stale_activation_hash_is_rejected(self) -> None:
        outcome = valid_outcome().replace(ACTIVATION_SHA256, "b" * 64)
        self.assertIn(
            "Activation sha256 does not match",
            "\n".join(self.check(outcome)),
        )

    def test_non_matching_ms_source_is_rejected(self) -> None:
        outcome = valid_outcome().replace(
            "| MS-001 | web-prod@",
            "| MS-002 | web-prod@",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("MS-002 is not a matching verified Activation source", findings)
        self.assertIn("every matching verified MS source", findings)

    def test_mismatched_release_or_deployment_identity_is_rejected(self) -> None:
        stale_sha = valid_outcome().replace(f"- Release SHA: {SHA}", f"- Release SHA: {'b' * 40}")
        stale_artifact = valid_outcome().replace(
            f"- Artifact / build identity: {ARTIFACT}",
            "- Artifact / build identity: other-build",
        )
        for label, outcome in (("SHA", stale_sha), ("artifact", stale_artifact)):
            with self.subTest(label):
                findings = "\n".join(self.check(outcome))
                self.assertIn("Deployment:", findings)

    def test_outcome_is_production_only_and_rejects_future_window(self) -> None:
        development_target = valid_outcome().replace(
            "- Production release target: web-prod", "- Production release target: web-dev"
        )
        self.assertIn(
            "must be an architecture production target",
            "\n".join(self.check(development_target)),
        )
        future_window = valid_outcome().replace(
            "2026-09-09 | 72%", "2099-09-09 | 72%"
        )
        self.assertIn(
            "window cannot end in the future",
            "\n".join(self.check(future_window)),
        )

    def test_incident_requires_containment_human_owner_and_prd_routing(self) -> None:
        broken = valid_outcome(verdict="incident").replace(
            "| checkout failures | rollout halted | Incident owner | PRD Risks: checkout reliability | PRD Open Questions: retain staged rollout? | MS-001 |",
            "| checkout failures | none | AI | risks | questions | MS-001 |",
        )
        findings = "\n".join(self.check(broken))
        self.assertIn("incident requires containment", findings)
        self.assertIn("incident requires a human owner", findings)
        self.assertIn("explicit PRD Risks routing", findings)
        self.assertIn("explicit PRD Open Questions routing", findings)

    def test_duplicate_sections_and_signals_are_rejected(self) -> None:
        duplicate = valid_outcome() + "\n## Measurements\n| duplicate | section |\n"
        self.assertIn(
            "duplicate required section ## Measurements",
            "\n".join(self.check(duplicate)),
        )

        duplicate_signal = valid_outcome().replace(
            "| Activation rate | none recorded | 70% in 14 days | 2026-09-07 | 2026-09-09 | 72% | MS-001 |",
            "| Activation rate | none recorded | 70% in 14 days | 2026-09-07 | 2026-09-09 | 72% | MS-001 |\n"
            "| Activation rate | none recorded | 70% in 14 days | 2026-09-07 | 2026-09-09 | 1% | MS-001 |",
        )
        self.assertIn(
            "duplicate signal(s) Activation rate",
            "\n".join(self.check(duplicate_signal)),
        )

    def test_cli_requires_exact_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "outcome.md": valid_outcome(),
                "PRD.md": PRD,
                "architecture.md": ARCHITECTURE,
                "DEPLOYMENT.md": DEPLOYMENT,
                "ACTIVATION.md": ACTIVATION,
            }
            for name, content in paths.items():
                (root / name).write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "check_outcome_review.py"),
                    "--outcome",
                    str(root / "outcome.md"),
                    "--prd",
                    str(root / "PRD.md"),
                    "--architecture",
                    str(root / "architecture.md"),
                    "--deployment",
                    str(root / "DEPLOYMENT.md"),
                    "--activation",
                    str(root / "ACTIVATION.md"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("stack", result.stdout + result.stderr)

    def test_lifecycle_cli_requires_schema2_and_stack_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review_path = root / "docs" / "product" / "outcomes" / "2026-09-10-example.md"
            review_path.parent.mkdir(parents=True)
            review_path.write_text(valid_outcome(), encoding="utf-8")
            paths = {
                "PRD.md": PRD,
                "architecture.md": ARCHITECTURE,
                "DEPLOYMENT.md": DEPLOYMENT,
                "ACTIVATION.md": ACTIVATION,
            }
            for name, content in paths.items():
                (root / name).write_text(content, encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPTS_DIR / "check_outcome_review.py"),
                "--outcome", str(review_path),
                "--prd", str(root / "PRD.md"),
                "--architecture", str(root / "architecture.md"),
                "--deployment", str(root / "DEPLOYMENT.md"),
                "--activation", str(root / "ACTIVATION.md"),
                "--repo-root", str(root),
                "--require-lifecycle",
            ]
            stack_path = root / "stack-decisions.md"
            stack_path.write_text("# Stack Decisions: Example\n", encoding="utf-8")
            schema_failure = subprocess.run(
                command + ["--stack-decisions", str(stack_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, schema_failure.returncode)
            self.assertIn("requires Schema: outcome-review/2", schema_failure.stderr)
            review_path.write_text(valid_outcome().replace("outcome-review/1", "outcome-review/2", 1), encoding="utf-8")
            stack_failure = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(2, stack_failure.returncode)
            self.assertIn("requires --stack-decisions", stack_failure.stderr)

    def test_prior_outcome_digest_binds_immutable_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current = root / "current.md"
            prior = root / "prior.md"
            for path, content in ((current, valid_outcome()), (prior, valid_outcome())):
                path.write_text(content, encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPTS_DIR / "check_outcome_review.py"),
                "--outcome", str(current),
                "--prd", str(root / "PRD.md"),
                "--architecture", str(root / "architecture.md"),
                "--deployment", str(root / "DEPLOYMENT.md"),
                "--activation", str(root / "ACTIVATION.md"),
                "--prior-outcome", str(prior),
            ]
            for name, content in {
                "PRD.md": PRD,
                "architecture.md": ARCHITECTURE,
                "DEPLOYMENT.md": DEPLOYMENT,
                "ACTIVATION.md": ACTIVATION,
            }.items():
                (root / name).write_text(content, encoding="utf-8")
            rejected = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(1, rejected.returncode)
            self.assertIn("Prior outcome sha256", rejected.stderr)
            prior_digest = hashlib.sha256(prior.read_bytes()).hexdigest()
            current.write_text(
                valid_outcome() + f"\n- Prior outcome sha256: {prior_digest}\n",
                encoding="utf-8",
            )
            prior.write_text(prior.read_text(encoding="utf-8") + "\nrewritten history\n", encoding="utf-8")
            rewritten = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(1, rewritten.returncode)
            self.assertIn("Prior outcome sha256", rewritten.stderr)


if __name__ == "__main__":
    unittest.main()
