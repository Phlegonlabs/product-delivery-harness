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
    return text


def multi_target_outcome() -> str:
    activation = outcome_activation()
    activation_sha = hashlib.sha256(activation.encode("utf-8")).hexdigest()
    target_review_rows = []
    target_measurement_rows = []
    for target, (_surface_class, suffix, provider, artifact, _availability) in seed.PRODUCTION.items():
        target_review_rows.append(
            f"| {target} | {SHA} | {artifact} | fixture-{suffix};fixture-{suffix}-production-track;{artifact} | 2026-09-12T18:04:00Z | PASS | MS-001 | no_change |"
        )
    for signal, baseline, expected in (
        ("Completion", "0", "90%"),
        ("TEST-001", "none recorded", "Completion observed"),
        ("TEST-002", "none recorded", "All runs pass"),
    ):
        for target in SIGNAL_TARGETS[signal]:
            target_measurement_rows.append(
                f"| {signal} | {target} | {baseline} | {expected} | 2026-09-08 | 2026-09-09 | observed {target} | MS-001 |"
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
- Deployment checked: 2026-09-12T18:04:00Z
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
| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Verdict
Verdict: no_change — all reviewed targets met their recorded targets

## Open Follow-ups
| Follow-up | Route |
| --- | --- |
| none | none |
"""


class MultiTargetOutcomeReviewTests(unittest.TestCase):
    def check(self, text: str) -> list[str]:
        return check_outcome_review.check_outcome_review_text(
            text,
            prd_text=seed.product_fixtures.valid_prd(),
            architecture_text=seed.architecture_with_hybrid_targets(),
            deployment_text=seed.deployment_for_hybrid_targets(),
            activation_text=outcome_activation(),
        )

    def test_multi_target_outcome_review_passes(self) -> None:
        self.assertEqual([], self.check(multi_target_outcome()))

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
