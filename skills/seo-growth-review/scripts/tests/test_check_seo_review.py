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
SIBLING_SCRIPTS = (
    SKILLS_ROOT / "product-definition-builder" / "scripts",
    SKILLS_ROOT / "product-activation" / "scripts",
    SKILLS_ROOT / "delivery-harness" / "scripts",
)
for sibling in SIBLING_SCRIPTS:
    if str(sibling) not in sys.path:
        sys.path.insert(0, str(sibling))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_seo_review  # noqa: E402


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
TARGET_SCOPE = activation_fixtures.TARGET
ACTIVATION_SHA256 = hashlib.sha256(ACTIVATION.encode("utf-8")).hexdigest()


def valid_review() -> str:
    return f"""# SEO Growth Review

## Record
- Schema: seo-review/1
- Mode: baseline
- Review type: lifecycle_public_release
- Review owner: Growth owner
- Production release target: web-prod
- Release SHA: {SHA}
- Artifact / build identity: {ARTIFACT}
- Deployment identity: fixture-web;fixture-production-route;{ARTIFACT}
- Deployment checked: 2026-09-07T18:04:00Z
- Production domain: example.com
- Data cutoff: 2026-09-07T18:02:00Z
- Activation record: docs/ACTIVATION.md
- Activation sha256: {ACTIVATION_SHA256}
- Review date: 2026-09-10

## Verified Sources
| MS ID | Scope | Release binding | Source role | Data cutoff | Evidence |
| --- | --- | --- | --- | --- | --- |
| MS-001 | {TARGET_SCOPE} | web-prod@{SHA}#{ARTIFACT} | ga4 | 2026-09-07T18:02:00Z | EVID-004 verified property read-back |

## Measurement Integrity
| Check | Result | Evidence |
| --- | --- | --- |
| Production scope | PASS | canonical host and property agree |
| Release identity | PASS | target, SHA, artifact, and deployment agree |
| Date coverage | PASS | complete week before cutoff |

## Technical Findings
| Priority | Finding | Scope | Evidence | Impact | Route |
| --- | --- | --- | --- | --- | --- |
| high | duplicate titles | /pricing | observed | weaker search presentation | delivery |

## Growth Opportunities
| Priority | Query or topic | Intent / type | Evidence | Current page | Action / route | Follow-up metric |
| --- | --- | --- | --- | --- | --- | --- |
| high | fixture setup | existing_page | observed | / | improve title / delivery | clicks after next complete month |

## What To Do First

1. Fix the duplicate titles before pursuing new content.

## Limits And Next Window

No query-level seasonality conclusion is possible until the next complete month is available.
"""


def valid_review_v2(*, mode: str = "baseline") -> str:
    text = valid_review().replace("seo-review/1", "seo-review/2", 1)
    text = text.replace(
        "- Mode: baseline",
        f"- Mode: {mode}",
        1,
    )
    text = text.replace(
        "- Review owner: Growth owner",
        "- Review owner: Growth owner\n- Product: Example\n- Target market: United States\n- Language: en-US\n- Business outcome: setup activation\n- Timezone: UTC\n- Comparison window: 2026-08-01/2026-08-31 vs 2026-07-01/2026-07-31\n- Segmentation: query, page, country, device\n- Global data coverage through: 2026-09-07T18:02:00Z",
        1,
    )
    text = text.replace(
        "| MS ID | Scope | Release binding | Source role | Data cutoff | Evidence |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"| MS-001 | {TARGET_SCOPE} | web-prod@{SHA}#{ARTIFACT} | ga4 | 2026-09-07T18:02:00Z | EVID-004 verified property read-back |",
        "| MS ID | Scope | Release binding | Source role | Verified at | Coverage through | Evidence |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        f"| MS-001 | {TARGET_SCOPE} | web-prod@{SHA}#{ARTIFACT} | ga4 | 2026-09-07T18:02:00Z | 2026-09-07T18:02:00Z | EVID-004 verified property read-back |",
        1,
    )
    return text


IOS_TARGETS = """
### Release Target: ios-dev
- Surface: ios-app
- Surface class: ios
- Public discoverability: no
- Surface suffix: ios
- Release name: fixture-ios-dev
- Provider: App Store Connect
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: signed iOS archive
- Signing requirement: App Store development certificate
- Exact channel / track: testflight-internal
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: TestFlight smoke check passes on the build
- Rollout: internal testers only
- Rollback / forward-fix: expire the build and upload the prior one

### Release Target: ios-prod
- Surface: ios-app
- Surface class: ios
- Public discoverability: no
- Surface suffix: ios
- Release name: fixture-ios
- Provider: App Store Connect
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: signed iOS archive
- Signing requirement: App Store distribution certificate
- Exact channel / track: app-store-production
- Submission / promotion / review / manual approval path: candidate checks, main promotion, App Store review
- Availability signal: App Store listing passes the smoke check
- Rollout: phased release to all users
- Rollback / forward-fix: submit a corrected forward-fix build
"""
WEB_PROFILE_ROW = "| web | yes | public web release | web owner |"
WEB_READINESS_PREFIX = "| web-prod | production | Cloudflare;fixture-production-route |"


def web_and_pending_ios() -> tuple[str, str, str]:
    """Architecture, Deployment and Activation with iOS still in App Store review."""

    architecture = ARCHITECTURE.replace(
        "Expected deployable surfaces: web-app",
        "Expected deployable surfaces: web-app, ios-app",
    ) + IOS_TARGETS
    deployment = DEPLOYMENT + (
        "| ios-dev | ios-app | development | App Store Connect;testflight-internal | pending | pending | pending | pending | pending | pending | pending |\n"
        f"| ios-prod | ios-app | production | App Store Connect;app-store-production | pending | {SHA} | {SHA} | ios-build-7 | pending | pending | pending |\n"
    )
    activation = (
        activation_fixtures.valid_record_v2()
        .replace(
            WEB_PROFILE_ROW,
            WEB_PROFILE_ROW + "\n| ios | yes | App Store release | ios owner |",
            1,
        )
        .replace("- Status: handoff_ready", "- Status: active", 1)
        .replace(
            WEB_READINESS_PREFIX,
            "| ios-dev | development | App Store Connect;testflight-internal | pending | pending | n/a | n/a | n/a | n/a — development candidate is not an activation target | none |\n"
            f"| ios-prod | production | App Store Connect;app-store-production | {SHA} | ios-build-7 | pending | pending | pending | none | none |\n"
            + WEB_READINESS_PREFIX,
            1,
        )
    )
    return architecture, deployment, activation


class SeoLifecycleReviewTests(unittest.TestCase):
    def check(
        self,
        review: str,
        *,
        stack_text: str | None = None,
        repo_root: Path | None = None,
    ) -> list[str]:
        with patch("check_seo_review.check_activation_text", return_value=[]):
            return check_seo_review.check_seo_review_text(
                review,
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
                stack_text=stack_text,
                repo_root=repo_root,
            )

    def test_verified_source_context_is_forwarded_to_activation(self) -> None:
        stack_text = "# Stack Decisions: Example\n"
        repo_root = Path(__file__).resolve().parents[4]
        with patch(
            "check_seo_review.check_activation_text", return_value=[]
        ) as activation_check, patch(
            "check_product_package.validate_texts", return_value=[]
        ), patch(
            "check_deployment.check_deployment_text", return_value=[]
        ) as deployment_check:
            check_seo_review.check_seo_review_text(
                valid_review_v2(),
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
                stack_text=stack_text,
                repo_root=repo_root,
            )

        self.assertEqual(stack_text, activation_check.call_args.kwargs["stack_text"])
        self.assertEqual(repo_root, activation_check.call_args.kwargs["repo_root"])
        self.assertTrue(deployment_check.call_args.kwargs["require_source_provenance"])
        self.assertEqual(
            ("web-prod",),
            deployment_check.call_args.kwargs["strict_target_subset"],
        )

    def test_package_and_deployment_are_validated_once(self) -> None:
        with patch(
            "check_product_package.validate_texts", return_value=["bad stack"]
        ) as package_check, patch(
            "check_deployment.check_deployment_text", return_value=["bad deploy"]
        ) as deployment_check:
            findings = check_seo_review.check_seo_review_text(
                valid_review_v2(),
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
                stack_text="# Stack Decisions: Example\n",
                repo_root=Path(__file__).resolve().parents[4],
            )
        self.assertEqual(1, package_check.call_count)
        self.assertEqual(1, deployment_check.call_count)
        self.assertEqual(1, findings.count("Product package: bad stack"))
        self.assertEqual(1, findings.count("Deployment: bad deploy"))
        self.assertFalse(any(item.startswith("Activation: Product package") for item in findings))

    def test_activation_still_validates_package_unless_told_otherwise(self) -> None:
        check_activation = sys.modules["check_activation"]
        for validated, expected_calls in ((False, 1), (True, 0)):
            with self.subTest(package_validated=validated), patch(
                "check_product_package.validate_texts", return_value=[]
            ) as package_check, patch(
                "check_deployment.check_deployment_text", return_value=[]
            ) as deployment_check:
                check_activation.check_activation_text(
                    activation_fixtures.valid_record_v2(),
                    prd_text=activation_fixtures.APPROVED_PRD,
                    architecture_text=ARCHITECTURE,
                    deployment_text=DEPLOYMENT,
                    stack_text="# Stack Decisions: Example",
                    repo_root=Path.cwd(),
                    require_ready=("web-prod",),
                    package_validated=validated,
                )
            self.assertEqual(expected_calls, package_check.call_count)
            self.assertEqual(expected_calls, deployment_check.call_count)

    def test_other_targets_may_stay_pending_but_reviewed_target_must_be_ready(self) -> None:
        architecture, deployment, activation = web_and_pending_ios()

        def run(activation_text: str) -> list[str]:
            review = valid_review_v2().replace(
                ACTIVATION_SHA256,
                hashlib.sha256(activation_text.encode("utf-8")).hexdigest(),
            )
            with patch("check_product_package.validate_texts", return_value=[]), patch(
                "check_deployment.check_deployment_text", return_value=[]
            ):
                return check_seo_review.check_seo_review_text(
                    review,
                    prd_text=activation_fixtures.APPROVED_PRD,
                    architecture_text=architecture,
                    deployment_text=deployment,
                    activation_text=activation_text,
                    stack_text="# Stack Decisions: Example",
                    repo_root=Path.cwd(),
                )

        self.assertEqual([], run(activation))
        # The product-wide handoff rules this review no longer needs.
        with patch("check_product_package.validate_texts", return_value=[]), patch(
            "check_deployment.check_deployment_text", return_value=[]
        ):
            handoff = "\n".join(
                sys.modules["check_activation"].check_activation_text(
                    activation,
                    prd_text=activation_fixtures.APPROVED_PRD,
                    architecture_text=architecture,
                    deployment_text=deployment,
                    stack_text="# Stack Decisions: Example",
                    repo_root=Path.cwd(),
                    require_verified_sources=True,
                )
            )
        self.assertIn("verified handoff target ios-prod must be ready or n/a", handoff)
        self.assertIn("requires status handoff_ready", handoff)

        web_pending = activation.replace("| deployed | ready |", "| deployed | pending |", 1)
        self.assertIn(
            "Activation: Target Readiness: required target web-prod is not ready",
            run(web_pending),
        )

    def test_valid_lifecycle_review_passes_exact_bindings(self) -> None:
        self.assertEqual([], self.check(valid_review()))

    def test_schema2_lifecycle_review_preserves_product_and_mode_fields(self) -> None:
        with patch("check_seo_review.check_activation_text", return_value=[]), patch(
            "check_product_package.validate_texts", return_value=[]
        ), patch("check_deployment.check_deployment_text", return_value=[]):
            findings = check_seo_review.check_seo_review_text(
                valid_review_v2(),
                prd_text=PRD,
                architecture_text=ARCHITECTURE,
                deployment_text=DEPLOYMENT,
                activation_text=ACTIVATION,
                stack_text="# Stack Decisions: Example",
                repo_root=Path.cwd(),
            )
        self.assertEqual([], findings)

    def test_schema2_mode_specific_windows_and_segmentation_are_required(self) -> None:
        for mode in ("growth_review", "traffic_drop"):
            missing_window = valid_review_v2(mode=mode).replace(
                "- Comparison window: 2026-08-01/2026-08-31 vs 2026-07-01/2026-07-31",
                "- Comparison window: one period",
                1,
            )
            expected = (
                "requires equal comparison windows"
                if mode == "traffic_drop"
                else "requires a comparison window"
            )
            self.assertIn(expected, "\n".join(self.check(missing_window)))
        missing_segments = valid_review_v2(mode="traffic_drop").replace(
            "- Segmentation: query, page, country, device",
            "- Segmentation: query only",
            1,
        )
        self.assertIn(
            "Segmentation must include query, page, country, and device",
            "\n".join(self.check(missing_segments)),
        )

    def test_schema2_requires_market_language_outcome_timezone_and_cutoff(self) -> None:
        for field, marker in (
            ("Target market", "- Target market: United States"),
            ("Language", "- Language: en-US"),
            ("Business outcome", "- Business outcome: setup activation"),
            ("Timezone", "- Timezone: UTC"),
            ("Global data coverage through", "- Global data coverage through: 2026-09-07T18:02:00Z"),
        ):
            with self.subTest(field=field):
                missing = valid_review_v2().replace(marker, f"- {field}: ", 1)
                self.assertIn(f"Record: {field} must be substantive", "\n".join(self.check(missing)))

    def test_schema2_duplicate_record_fields_and_source_times_are_rejected(self) -> None:
        duplicate = valid_review_v2().replace(
            "- Product: Example\n",
            "- Product: Example\n- Product: Example\n",
            1,
        )
        self.assertIn("Record: duplicate field product", "\n".join(self.check(duplicate)))
        stale_verified_at = valid_review_v2().replace(
            "| ga4 | 2026-09-07T18:02:00Z | 2026-09-07T18:02:00Z |",
            "| ga4 | 2026-09-07T17:02:00Z | 2026-09-07T18:02:00Z |",
            1,
        )
        self.assertIn(
            "verified at must equal the latest PASS Activation evidence",
            "\n".join(self.check(stale_verified_at)),
        )

    def test_schema2_global_cutoff_cannot_exceed_source_or_record_scope(self) -> None:
        future_cutoff = valid_review_v2().replace(
            "- Global data coverage through: 2026-09-07T18:02:00Z",
            "- Global data coverage through: 2099-09-07T18:02:00Z",
            1,
        )
        self.assertIn(
            "Global data coverage through cannot be in the future",
            "\n".join(self.check(future_cutoff)),
        )

    def test_schema2_date_only_data_cutoff_is_a_finding_not_a_crash(self) -> None:
        date_only = valid_review_v2().replace(
            "- Data cutoff: 2026-09-07T18:02:00Z", "- Data cutoff: 2026-09-07", 1
        )
        self.assertIn(
            "Record: Data cutoff must be an RFC3339 timestamp",
            "\n".join(self.check(date_only)),
        )
        # Source rows are still checked after the malformed cutoff.
        self.assertIn(
            "verified at must equal",
            "\n".join(
                self.check(
                    date_only.replace(
                        "| ga4 | 2026-09-07T18:02:00Z | 2026-09-07T18:02:00Z |",
                        "| ga4 | 2026-09-07T17:02:00Z | 2026-09-07T18:02:00Z |",
                        1,
                    )
                )
            ),
        )

    def test_release_domain_or_artifact_mismatch_is_rejected(self) -> None:
        domain = valid_review().replace("- Production domain: example.com", "- Production domain: https://example.com/path")
        artifact = valid_review().replace(
            f"- Artifact / build identity: {ARTIFACT}",
            "- Artifact / build identity: other-build",
        )
        self.assertIn("Production domain", "\n".join(self.check(domain)))
        self.assertIn("Deployment: reviewed target artifact", "\n".join(self.check(artifact)))

    def test_lifecycle_review_requires_public_web_target_and_deployment_hostname(self) -> None:
        wrong_domain = valid_review().replace(
            "- Production domain: example.com", "- Production domain: other.example.com"
        )
        self.assertIn(
            "hostname must equal",
            "\n".join(self.check(wrong_domain)),
        )
        api_architecture = ARCHITECTURE.replace(
            "Surface class: hosted_web", "Surface class: hosted_api"
        ).replace("Public discoverability: yes", "Public discoverability: no")
        api_review = valid_review()
        findings = check_seo_review.check_seo_review_text(
            api_review,
            prd_text=PRD,
            architecture_text=api_architecture,
            deployment_text=DEPLOYMENT,
            activation_text=ACTIVATION,
        )
        self.assertIn(
            "public web production targets",
            "\n".join(findings),
        )

    def test_activation_hash_and_source_binding_mismatches_are_rejected(self) -> None:
        stale_hash = valid_review().replace(ACTIVATION_SHA256, "b" * 64)
        stale_source = valid_review().replace(
            f"MS-001 | {TARGET_SCOPE} | web-prod@{SHA}#{ARTIFACT}",
            f"MS-001 | {TARGET_SCOPE} | web-prod@{SHA}#other-build",
        )
        self.assertIn("Activation sha256 does not match", "\n".join(self.check(stale_hash)))
        self.assertIn("mismatched release binding", "\n".join(self.check(stale_source)))

    def test_duplicate_required_sections_are_rejected(self) -> None:
        duplicate = valid_review() + "\n## Verified Sources\n| duplicate | section |\n"
        self.assertIn(
            "duplicate required section ## Verified Sources",
            "\n".join(self.check(duplicate)),
        )

    def test_lifecycle_cli_enforces_dated_immutable_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = root / "review.md"
            review.write_text(valid_review(), encoding="utf-8")
            (root / "PRD.md").write_text(PRD, encoding="utf-8")
            (root / "architecture.md").write_text(ARCHITECTURE, encoding="utf-8")
            (root / "DEPLOYMENT.md").write_text(DEPLOYMENT, encoding="utf-8")
            (root / "ACTIVATION.md").write_text(ACTIVATION, encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPTS_DIR / "check_seo_review.py"),
                "--review",
                str(review),
                "--prd",
                str(root / "PRD.md"),
                "--architecture",
                str(root / "architecture.md"),
                "--deployment",
                str(root / "DEPLOYMENT.md"),
                "--activation",
                str(root / "ACTIVATION.md"),
                "--repo-root",
                str(root),
                "--require-lifecycle",
            ]
            invalid = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(1, invalid.returncode)
            self.assertIn("requires Schema: seo-review/2", invalid.stderr)

            dated = root / "docs" / "seo" / "reviews" / "2026-09-10-public-release.md"
            dated.parent.mkdir(parents=True)
            dated.write_text(valid_review_v2(), encoding="utf-8")
            gated = subprocess.run(
                [part if part != str(review) else str(dated) for part in command],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, gated.returncode)
            self.assertIn("requires --stack-decisions", gated.stderr)

            (root / "stack-decisions.md").write_text("# Stack Decisions: Example\n", encoding="utf-8")
            with_stack = [
                part if part != str(review) else str(dated) for part in command
            ] + ["--stack-decisions", str(root / "stack-decisions.md")]
            package = subprocess.run(with_stack, text=True, capture_output=True, check=False)
            self.assertEqual(1, package.returncode)
            # Package findings print once on stdout next to the review findings.
            self.assertIn(": Product package: ", package.stdout)
            self.assertNotIn("Activation: Product package", package.stdout)
            self.assertIn(": Activation: ", package.stdout)
            self.assertEqual("", package.stderr)


if __name__ == "__main__":
    unittest.main()
