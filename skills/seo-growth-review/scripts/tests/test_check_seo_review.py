from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
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


class SeoLifecycleReviewTests(unittest.TestCase):
    def check(self, review: str) -> list[str]:
        return check_seo_review.check_seo_review_text(
            review,
            prd_text=PRD,
            architecture_text=ARCHITECTURE,
            deployment_text=DEPLOYMENT,
            activation_text=ACTIVATION,
        )

    def test_valid_lifecycle_review_passes_exact_bindings(self) -> None:
        self.assertEqual([], self.check(valid_review()))

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
            self.assertIn("docs/seo/reviews/YYYY-MM-DD-<slug>.md", invalid.stdout)

            dated = root / "docs" / "seo" / "reviews" / "2026-09-10-public-release.md"
            dated.parent.mkdir(parents=True)
            dated.write_text(valid_review(), encoding="utf-8")
            valid = subprocess.run(
                [part if part != str(review) else str(dated) for part in command],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, valid.returncode, valid.stdout + valid.stderr)

            mismatched = root / "docs" / "seo" / "reviews" / "2026-09-11-public-release.md"
            mismatched.write_text(valid_review(), encoding="utf-8")
            invalid_date = subprocess.run(
                [part if part != str(review) else str(mismatched) for part in command],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, invalid_date.returncode)
            self.assertIn("filename date must equal Record Review date", invalid_date.stdout)


if __name__ == "__main__":
    unittest.main()
