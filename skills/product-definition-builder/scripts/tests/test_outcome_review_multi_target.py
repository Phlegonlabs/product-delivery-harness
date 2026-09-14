"""Multi-target Outcome Review contract coverage."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import check_outcome_review  # noqa: E402
import test_activation_seed_reconciliation as seed  # noqa: E402


SHA = "a" * 40
PRIMARY_ARTIFACT = seed.PRODUCTION["api-prod"][3]
PRODUCTION_TARGETS = tuple(seed.PRODUCTION)
SIGNAL_TARGETS = {
    "Completion": ("api-prod",),
    "TEST-001": ("android-prod",),
    "TEST-002": PRODUCTION_TARGETS,
}


def outcome_activation() -> str:
    text = seed.activation_for_hybrid_targets()
    all_targets = ", ".join(PRODUCTION_TARGETS)
    text = text.replace(
        f"| Completion | Completed runs | 0 | 90% | 30 days | n/a — metric row | {all_targets} | MS-001 | verified |",
        "| Completion | Completed runs | 0 | 90% | 30 days | n/a — metric row | api-prod | MS-001 | verified |",
    )
    text = text.replace(
        f"| TEST-001 | Complete fixture | none recorded | n/a — required test has no numeric target | integration test | Completion observed | {all_targets} | MS-001 | verified |",
        "| TEST-001 | Complete fixture | none recorded | n/a — required test has no numeric target | integration test | Completion observed | android-prod | MS-001 | verified |",
    )
    text = text.replace(
        "## Outcome Coverage\n",
        "| CAP-002 | browser | available | read, readback | android-prod | production | 2026-09-12T17:56:00Z | Android-specific release console read-back available |\n\n## Outcome Coverage\n",
        1,
    )
    text = text.replace(
        "## Activation Tasks\n",
        "| MS-002 | android-prod | production | Android-specific release evidence read-back | first_party | browser;CAP-002 | android-prod@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#fixture-android-build-1 | Android owner | verified | EVID-021, EVID-022 |\n\n## Activation Tasks\n",
        1,
    )
    text = text.replace(
        "## Manual Handoff\n",
        "| EVID-021 | MS-002 | readback | browser;n/a;android-prod@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#fixture-android-build-1 | 2026-09-12T18:21:00Z | PASS | Android release identity read back |\n| EVID-022 | MS-002 | behavior | browser;n/a;android-prod@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa#fixture-android-build-1 | 2026-09-12T18:22:00Z | PASS | Android acceptance behavior verified |\n\n## Manual Handoff\n",
        1,
    )
    return text


def multi_target_outcome() -> str:
    activation = outcome_activation()
    activation_sha = hashlib.sha256(activation.encode("utf-8")).hexdigest()
    target_review_rows = []
    target_measurement_rows = []
    for target, (_surface_class, suffix, provider, artifact, _availability) in seed.PRODUCTION.items():
        source_ids = "MS-001, MS-002" if target == "android-prod" else "MS-001"
        target_review_rows.append(
            f"| {target} | {SHA} | {artifact} | fixture-{suffix};fixture-{suffix}-production-track;{artifact} | 2026-08-01T18:04:00Z | PASS | {source_ids} | no_change |"
        )
    for signal, baseline, expected in (
        ("Completion", "0", "90%"),
        ("TEST-001", "none recorded", "Completion observed"),
        ("TEST-002", "none recorded", "All runs pass"),
    ):
        for target in SIGNAL_TARGETS[signal]:
            target_measurement_rows.append(
                f"| {signal} | {target} | {baseline} | {expected} | 2026-08-02 | 2026-09-01 | observed {target} | MS-001 |"
            )
    return f"""# Outcome Review

## Record
- Schema: outcome-review/1
- Product: Fixture
- Outcome owner: Product owner
- Production release target: api-prod
- Production release targets: target-set: {', '.join(PRODUCTION_TARGETS)}
- Release SHA: {SHA}
- Artifact / build identity: {PRIMARY_ARTIFACT}
- Deployment identity: fixture-api;fixture-api-production-track;{PRIMARY_ARTIFACT}
- Deployment checked: 2026-08-01T18:04:00Z
- Deployment status: PASS
- Activation record: docs/ACTIVATION.md
- Activation sha256: {activation_sha}
- Reviewed on: 2026-09-12
- Verdict: no_change

## Activation Sources
| MS ID | Release binding | Owner | Verified at | Evidence |
| --- | --- | --- | --- | --- |
| MS-001 | api-prod@{SHA}#{PRIMARY_ARTIFACT} | Analytics owner | 2026-09-12T18:14:00Z | EVID-013 EVID-014 EVID-015 EVID-016 EVID-017 EVID-018 EVID-019 EVID-020 verified per-target sources |

## Measurements
| Signal | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- |
| Completion | 0 | 90% | 2026-09-08 | 2026-09-09 | observed api-prod | MS-001 |
| TEST-001 | none recorded | Completion observed | 2026-09-08 | 2026-09-09 | observed api-prod | MS-001 |
| TEST-002 | none recorded | All runs pass | 2026-09-08 | 2026-09-09 | observed api-prod | MS-001 |

## Target Reviews
| Release target | Release SHA | Artifact / build identity | Deployment identity | Deployment checked | Deployment status | Activation sources | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(target_review_rows)}

## Target Measurements
| Signal | Release target | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(target_measurement_rows)}

## Feedback
| Fact | Release target | Source ID | Observed |
| --- | --- | --- | --- |
""" + "\n".join(
        f"| Target reported its expected post-deployment signal | {target} | MS-001 | target-specific read-back and behavior evidence |"
        for target in PRODUCTION_TARGETS
    ) + """

## Incident Response
| Incident | Release target | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(
        f"| none | {target} | n/a | n/a | n/a | n/a | n/a |"
        for target in PRODUCTION_TARGETS
    ) + """

## Verdict
Verdict: no_change — all reviewed targets met their recorded targets

## Open Follow-ups
| Follow-up | Route |
| --- | --- |
| none | none |
"""


def incident_multi_target_outcome() -> str:
    outcome = multi_target_outcome()
    outcome = outcome.replace("- Verdict: no_change", "- Verdict: incident", 1)
    outcome = outcome.replace("Verdict: no_change —", "Verdict: incident —", 1)
    outcome = outcome.replace(
        "| android-prod | " + SHA + " | fixture-android-build-1 | fixture-android;fixture-android-production-track;fixture-android-build-1 | 2026-08-01T18:04:00Z | PASS | MS-001, MS-002 | no_change |",
        "| android-prod | " + SHA + " | fixture-android-build-1 | fixture-android;fixture-android-production-track;fixture-android-build-1 | 2026-08-01T18:04:00Z | PASS | MS-001, MS-002 | incident |",
        1,
    )
    outcome = outcome.replace(
        "| none | android-prod | n/a | n/a | n/a | n/a | n/a |",
        "| Android acceptance failed | android-prod | rollout halted | Android owner | PRD Risks: Android release reliability | PRD Open Questions: retain Android rollout? | MS-002 |",
        1,
    )
    return outcome


class MultiTargetOutcomeReviewTests(unittest.TestCase):
    def check(self, text: str) -> list[str]:
        return check_outcome_review.check_outcome_review_text(
            text,
            prd_text=seed.product_fixtures.valid_prd(),
            architecture_text=seed.architecture_with_hybrid_targets(),
            deployment_text=seed.deployment_for_hybrid_targets().replace(
                "2026-09-12T18:04:00Z", "2026-08-01T18:04:00Z"
            ),
            activation_text=outcome_activation(),
        )

    def test_multi_target_outcome_review_passes(self) -> None:
        self.assertEqual([], self.check(multi_target_outcome()))

    def test_android_specific_incident_source_and_aggregate_verdict_pass(self) -> None:
        self.assertEqual([], self.check(incident_multi_target_outcome()))

    def test_incident_cannot_use_android_source_for_api_target(self) -> None:
        outcome = incident_multi_target_outcome().replace(
            "| Android acceptance failed | android-prod | rollout halted |",
            "| Android acceptance failed | api-prod | rollout halted |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("api-prod incident must use a verified source bound to that target", findings)

    def test_multi_feedback_header_is_strict(self) -> None:
        outcome = multi_target_outcome().replace(
            "| Fact | Release target | Source ID | Observed |",
            "| Fact | Source ID | Observed |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("Feedback: expected columns fact | release target | source id | observed", findings)

    def test_multi_feedback_allows_distinct_facts_for_one_target_but_not_duplicates(self) -> None:
        outcome = multi_target_outcome()
        row = (
            "| Target reported its expected post-deployment signal | api-prod | "
            "MS-001 | target-specific read-back and behavior evidence |"
        )
        second = (
            "| API latency remained within the approved guardrail | api-prod | "
            "MS-001 | bounded API observation |"
        )
        expanded = outcome.replace(row, row + "\n" + second, 1)
        self.assertEqual([], self.check(expanded))
        findings = "\n".join(self.check(expanded.replace(second, second + "\n" + second, 1)))
        self.assertIn("Feedback: duplicate fact row for api-prod", findings)

    def test_multi_incident_header_is_strict(self) -> None:
        outcome = multi_target_outcome().replace(
            "| Incident | Release target | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |",
            "| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("Incident Response: expected columns incident | release target", findings)

    def test_duplicate_multi_incident_target_is_rejected(self) -> None:
        outcome = incident_multi_target_outcome()
        row = "| Android acceptance failed | android-prod | rollout halted | Android owner | PRD Risks: Android release reliability | PRD Open Questions: retain Android rollout? | MS-002 |"
        findings = "\n".join(self.check(outcome.replace(row, row + "\n" + row, 1)))
        self.assertIn("duplicate incident row for android-prod", findings)

    def test_missing_target_signal_is_rejected(self) -> None:
        outcome = multi_target_outcome()
        missing = next(
            line
            for line in outcome.splitlines()
            if line.startswith("| Completion | api-prod |")
        )
        findings = "\n".join(self.check(outcome.replace(missing + "\n", "", 1)))
        self.assertIn("missing Completion for api-prod", findings)

    def test_out_of_scope_signal_target_is_rejected(self) -> None:
        outcome = multi_target_outcome()
        marker = "## Feedback"
        extra = (
            "| Completion | android-prod | 0 | 90% | 2026-09-08 | 2026-09-09 | "
            "observed android-prod | MS-001 |\n\n"
        )
        findings = "\n".join(self.check(outcome.replace(marker, extra + marker, 1)))
        self.assertIn("Completion/android-prod is outside its Activation Outcome Coverage target set", findings)

    def test_target_window_duration_must_match_prd(self) -> None:
        outcome = multi_target_outcome().replace(
            "| Completion | api-prod | 0 | 90% | 2026-08-02 | 2026-09-01 |",
            "| Completion | api-prod | 0 | 90% | 2026-08-02 | 2026-08-31 |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("Completion/api-prod window must match PRD measurement window", findings)

    def test_target_window_must_start_after_that_target_deployment(self) -> None:
        outcome = multi_target_outcome().replace(
            "| Completion | api-prod | 0 | 90% | 2026-08-02 | 2026-09-01 |",
            "| Completion | api-prod | 0 | 90% | 2026-07-01 | 2026-07-31 |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("Completion/api-prod window must start and end after target deployment", findings)

    def test_mixed_target_identity_is_rejected(self) -> None:
        outcome = multi_target_outcome().replace(
            "| android-prod | " + SHA + " | fixture-android-build-1 |",
            "| android-prod | " + SHA + " | fixture-api-build-1 |",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("android-prod artifact does not match deployment", findings)


if __name__ == "__main__":
    unittest.main()
