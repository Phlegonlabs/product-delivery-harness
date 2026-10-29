from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_outcome_review  # noqa: E402


SHA = "a" * 40
ARTIFACT = "web-build-1"
BINDING = f"web-prod@{SHA}#{ARTIFACT}"
MS_TARGET = "google_analytics/account-1/property-2/stream-3"
MS_RETRIEVAL = "bounded GA4 Data API query for the verified stream"
MS_OWNER = "Analytics owner"
MS_VERIFIED_AT = "2026-09-07T18:02:00Z"
MS_EVIDENCE = "GA4 property 2 stream 3 returned the setup event count for web-build-1"

ARCHITECTURE = """# Architecture

## Release Targets

Expected deployable surfaces: web-app

### Release Target: web-dev
- Surface: web-app
- Surface class: hosted_web
- Public discoverability: yes
- Surface suffix: web
- Release name: fixture-web-dev
- Provider: Cloudflare
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: static development bundle
- Signing requirement: not required
- Exact channel / track: fixture-development-route
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: route answers the smoke check
- Rollout: all development testers
- Rollback / forward-fix: deploy the prior development bundle

### Release Target: web-prod
- Surface: web-app
- Surface class: hosted_web
- Public discoverability: yes
- Surface suffix: web
- Release name: fixture-web
- Provider: Cloudflare
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: static production bundle
- Signing requirement: not required
- Exact channel / track: fixture-production-route
- Submission / promotion / review / manual approval path: candidate checks, main promotion, owner approval
- Availability signal: route answers the smoke check
- Rollout: all users after smoke passes
- Rollback / forward-fix: deploy the prior bundle or corrected forward-fix
"""

PRD = """# PRD: Example

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


def measurement_sources_row(
    *,
    source_id: str = "MS-001",
    binding: str = BINDING,
    role: str = "ga4",
    owner: str = MS_OWNER,
    status: str = "verified",
    verified_at: str = MS_VERIFIED_AT,
    evidence: str = MS_EVIDENCE,
) -> str:
    return (
        f"| {source_id} | Activation rate, TEST-001 | {MS_TARGET} | production "
        f"| {MS_RETRIEVAL} | {role} | {binding} | {owner} | {status} | {verified_at} | {evidence} |"
    )


def deployment_record(row: str | None = None) -> str:
    if row is None:
        row = measurement_sources_row()
    return f"""# Deployment

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| web-dev | web-app | development | Cloudflare;fixture-development-route | pending | pending | pending | pending | pending | pending | pending |
| web-prod | web-app | production | Cloudflare;fixture-production-route | https://example.com | {SHA} | {SHA} | {ARTIFACT} | production route answered the smoke check | 2026-09-07T18:04:00Z | PASS |

## Measurement Sources

| MS ID | Signals | Target | Environment | Retrieval | Source role | Release bindings | Owner | Status | Verified at | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{row}
"""


DEPLOYMENT = deployment_record()
DEPLOYMENT_SHA256 = hashlib.sha256(DEPLOYMENT.encode("utf-8")).hexdigest()


def valid_outcome(*, verdict: str = "no_change", schema: str = "outcome-review/1") -> str:
    incident = """| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |"""
    if verdict == "incident":
        incident = """| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| checkout failures | rollout halted | Incident owner | PRD Risks: checkout reliability | PRD Open Questions: retain staged rollout? | MS-001 |"""
    return f"""# Outcome Review

## Record
- Schema: {schema}
- Product: Example
- Outcome owner: Product owner
- Production release target: web-prod
- Release SHA: {SHA}
- Artifact / build identity: {ARTIFACT}
- Deployment identity: fixture-web;fixture-production-route;{ARTIFACT}
- Deployment checked: 2026-09-07T18:04:00Z
- Deployment status: PASS
- Measurement record: docs/DEPLOYMENT.md
- Deployment sha256: {DEPLOYMENT_SHA256}
- Reviewed on: 2026-09-10
- Verdict: {verdict}

## Activation Sources
| MS ID | Release binding | Owner | Verified at | Evidence |
| --- | --- | --- | --- | --- |
| MS-001 | web-prod@{SHA}#{ARTIFACT} | {MS_OWNER} | {MS_VERIFIED_AT} | {MS_EVIDENCE} |

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
    def check(self, outcome: str, *, deployment: str = DEPLOYMENT) -> list[str]:
        return check_outcome_review.check_outcome_review_text(
            outcome,
            prd_text=PRD,
            architecture_text=ARCHITECTURE,
            deployment_text=deployment,
        )

    def test_valid_outcome_is_bound_to_verified_release(self) -> None:
        self.assertEqual([], self.check(valid_outcome()))
        self.assertEqual([], self.check(valid_outcome(schema="outcome-review/2")))

    def test_multi_target_record_is_rejected(self) -> None:
        multi = valid_outcome().replace(
            "- Production release target: web-prod",
            "- Production release target: web-prod\n- Production release targets: target-set: web-prod, other-prod",
            1,
        )
        self.assertIn("one record per target", "\n".join(self.check(multi)))

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

    def test_window_must_elapse_after_deployment(self) -> None:
        same_day = valid_outcome().replace(
            "2026-09-07 | 2026-09-09",
            "2026-09-07 | 2026-09-07",
        )
        self.assertIn("window must elapse after deployment", "\n".join(self.check(same_day)))
        before_deployment = valid_outcome().replace(
            "2026-09-07 | 2026-09-09",
            "2026-09-01 | 2026-09-05",
        )
        self.assertIn(
            "window must elapse after deployment", "\n".join(self.check(before_deployment))
        )

    def test_stale_deployment_hash_is_rejected(self) -> None:
        outcome = valid_outcome().replace(DEPLOYMENT_SHA256, "b" * 64)
        self.assertIn(
            "Deployment sha256 does not match",
            "\n".join(self.check(outcome)),
        )

    def test_non_matching_ms_source_is_rejected(self) -> None:
        outcome = valid_outcome().replace(
            "| MS-001 | web-prod@",
            "| MS-002 | web-prod@",
            1,
        )
        findings = "\n".join(self.check(outcome))
        self.assertIn("MS-002 is not a matching verified measurement source", findings)
        self.assertIn("every matching verified MS source", findings)

    def test_review_row_must_copy_the_deployment_row(self) -> None:
        stale_time = valid_outcome().replace(MS_VERIFIED_AT, "2026-09-08T09:00:00Z", 1)
        self.assertIn(
            "verified time must equal the deployment row Verified at",
            "\n".join(self.check(stale_time)),
        )
        other_evidence = valid_outcome().replace(MS_EVIDENCE, "unrelated screenshot", 1)
        self.assertIn(
            "evidence must equal the deployment row Evidence",
            "\n".join(self.check(other_evidence)),
        )
        other_owner = valid_outcome().replace(
            f"| MS-001 | web-prod@{SHA}#{ARTIFACT} | {MS_OWNER} |",
            f"| MS-001 | web-prod@{SHA}#{ARTIFACT} | Growth owner |",
            1,
        )
        self.assertIn(
            "owner differs from the deployment row",
            "\n".join(self.check(other_owner)),
        )

    def test_unverified_deployment_source_is_rejected(self) -> None:
        planned = deployment_record(
            measurement_sources_row(
                binding="web-prod@pending#pending",
                status="planned",
                verified_at="pending",
            )
        )
        findings = "\n".join(self.check(valid_outcome(), deployment=planned))
        self.assertIn("MS-001 is not a matching verified measurement source", findings)
        self.assertIn("every matching verified MS source", findings)

    def test_invalid_verified_deployment_row_is_flagged(self) -> None:
        broken = deployment_record(
            measurement_sources_row(role="assumed_vendor", verified_at="pending", evidence="pending")
        )
        findings = "\n".join(self.check(valid_outcome(), deployment=broken))
        self.assertIn("has invalid source role", findings)
        self.assertIn("Verified at must be an RFC3339 timestamp", findings)
        self.assertIn("MS-001 needs evidence", findings)

    def test_missing_or_malformed_measurement_sources_table_is_rejected(self) -> None:
        no_table = DEPLOYMENT.split("## Measurement Sources", 1)[0]
        self.assertIn(
            "Measurement Sources table is missing or invalid",
            "\n".join(self.check(valid_outcome(), deployment=no_table)),
        )

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

    def run_cli(self, root: Path, outcome_path: Path, *extra: str) -> subprocess.CompletedProcess:
        for name, content in {
            "PRD.md": PRD,
            "architecture.md": ARCHITECTURE,
            "DEPLOYMENT.md": DEPLOYMENT,
        }.items():
            (root / name).write_text(content, encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "check_outcome_review.py"),
                "--outcome", str(outcome_path),
                "--prd", str(root / "PRD.md"),
                "--architecture", str(root / "architecture.md"),
                "--deployment", str(root / "DEPLOYMENT.md"),
                *extra,
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_cli_accepts_a_bound_record_and_rejects_a_stale_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outcome = root / "outcome.md"
            outcome.write_text(valid_outcome(), encoding="utf-8")
            accepted = self.run_cli(root, outcome)
            self.assertEqual(0, accepted.returncode, accepted.stdout + accepted.stderr)
            outcome.write_text(
                valid_outcome().replace(DEPLOYMENT_SHA256, "b" * 64), encoding="utf-8"
            )
            rejected = self.run_cli(root, outcome)
            self.assertEqual(1, rejected.returncode)
            self.assertIn("Deployment sha256 does not match", rejected.stdout)

    def test_lifecycle_cli_requires_dated_path_and_schema2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review_path = root / "docs" / "product" / "outcomes" / "2026-09-10-example.md"
            review_path.parent.mkdir(parents=True)
            review_path.write_text(valid_outcome(), encoding="utf-8")
            command = ("--repo-root", str(root), "--require-lifecycle")
            schema_failure = self.run_cli(root, review_path, *command)
            self.assertEqual(1, schema_failure.returncode)
            self.assertIn("requires Schema: outcome-review/2", schema_failure.stderr)
            review_path.write_text(valid_outcome(schema="outcome-review/2"), encoding="utf-8")
            accepted = self.run_cli(root, review_path, *command)
            self.assertEqual(0, accepted.returncode, accepted.stdout + accepted.stderr)
            misplaced = root / "outcome.md"
            misplaced.write_text(valid_outcome(schema="outcome-review/2"), encoding="utf-8")
            path_failure = self.run_cli(root, misplaced, *command)
            self.assertEqual(1, path_failure.returncode)
            self.assertIn("lifecycle outcomes must use", path_failure.stderr)


if __name__ == "__main__":
    unittest.main()
