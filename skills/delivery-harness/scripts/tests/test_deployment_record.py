#!/usr/bin/env python3
"""check_deployment.py and configure_project_context placeholder checks."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_deployment  # noqa: E402
import configure_project_context  # noqa: E402


GOOD_DEPLOYMENT = f"""# Deployment

## Record

- Platform: cloudflare
- Mode: git_connected
- Production URL: https://example.com
- Preview URL pattern: <hash>.example.pages.dev
- Deployed-commit check: wrangler pages deployment list
- Protected resources preview must never bind: prod-db

## Release Unit Names

| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| web-app | web | example-web | example-web-dev | Cloudflare;production route | Cloudflare;development route |

## Resource Isolation

| Binding class | Production resource | Development resource |
| --- | --- | --- |
| D1 database | d1-prod-001 | d1-preview-001 |
| KV namespace | kv-prod-001 | kv-preview-001 |
| R2 bucket | n/a | n/a |

## Required Secrets and Variables

| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AUTH_SECRET | secret | app runtime | Cloudflare preview Worker secret | Cloudflare production Worker secret | operator-generated | verified |
| PUBLIC_APP_URL | variable | app runtime | Cloudflare preview Worker variable | Cloudflare production Worker variable | deployment URL | configured |

## External Console Setup

| Service | Setting | Preview / non-production | Production | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| Auth provider | callback URL | https://abc.example.pages.dev/callback | https://example.com/callback | operator | verified |

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| development | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | 2026-09-03 | PASS |
| production | | | | | |
"""

SHARED_RESOURCE_DEPLOYMENT = """# Deployment

## Record

- Platform: cloudflare
- Mode: ci_connected
- Production URL: https://example.com
- Deployed-commit check: wrangler deployments list

## Release Unit Names

| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| api | api | example-api | example-api-dev | Cloudflare;production route | Cloudflare;development route |

## Resource Isolation

| Binding class | Production resource | Development resource |
| --- | --- | --- |
| D1 database | d1-prod-001 | d1-prod-001 |
| KV namespace | kv-prod-001 | kv-preview-001 |

## Required Secrets and Variables

| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a | n/a |

## External Console Setup

| Service | Setting | Preview / non-production | Production | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| development | | | | | |
| production | | | | | |
"""

BAD_DEPLOYMENT = """# Deployment

## Record

- Platform: <cloudflare | vercel>
- Production URL: <url>

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| production | https://example.com | short | nope | 2026-09-03 | |
"""

CI_CONNECTED_DEPLOYMENT = f"""# Deployment

## Record

- Platform: cloudflare
- Mode: ci_connected
- Production URL: https://example.com
- Preview URL pattern: <hash>.example.pages.dev
- Deployed-commit check: wrangler pages deployment list
- Protected resources preview must never bind: prod-db

## Release Unit Names

| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| browser-extension | extension | example-extension | example-extension-dev | Chrome Web Store;production | Chrome Web Store;test |

## Required Secrets and Variables

| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a | n/a |

## External Console Setup

| Service | Setting | Preview / non-production | Production | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| development | https://abc.example.pages.dev | {"b" * 40} | {"b" * 40} | 2026-09-03 | PASS |
| production | | | | | |
"""


def target_block(
    target_id: str,
    surface: str,
    suffix: str,
    release_name: str,
    provider: str,
    stage: str,
    artifact_kind: str,
) -> str:
    source_policy = (
        "stage=development; ref=run.integration.branch; "
        "sha=run.integration.integration_head_sha"
        if stage == "development"
        else "stage=production; ref=refs/heads/main; "
        "sha=promotion.verified_main_sha"
    )
    availability = (
        "API answers the smoke check"
        if suffix == "api"
        else "build is installable or downloadable and passes smoke"
    )
    return f"""### Release Target: {target_id}
- Surface: {surface}
- Surface class: {'hosted_web' if surface == 'web-app' else 'hosted_api' if surface == 'public-api' else 'android' if surface == 'android-app' else 'macos' if surface == 'macos-app' else 'windows' if surface == 'windows-app' else 'other_nonpublic'}
- Public discoverability: {'yes' if surface == 'web-app' else 'no'}
- Surface suffix: {suffix}
- Release name: {release_name}
- Provider: {provider}
- Stage: {stage}
- Source policy: {source_policy}
- Artifact kind: {artifact_kind}
- Signing requirement: not required or exact platform signing
- Exact channel / track: fixture-{target_id}
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: {availability}
- Rollout: staged by owner decision
- Rollback / forward-fix: halt rollout and issue a corrected artifact
"""


def multi_surface_architecture() -> str:
    definitions = (
        ("api-dev", "public-api", "api", "fixture-api-dev", "API development gateway", "development", "API service"),
        ("api-prod", "public-api", "api", "fixture-api", "API production gateway", "production", "API service"),
        ("android-dev", "android-app", "android", "fixture-android-dev", "Play internal track", "development", "AAB"),
        ("android-prod", "android-app", "android", "fixture-android", "Google Play production", "production", "AAB"),
        ("macos-dev", "macos-app", "macos", "fixture-macos-dev", "TestFlight", "development", "signed DMG"),
        ("macos-prod", "macos-app", "macos", "fixture-macos", "direct download", "production", "signed DMG"),
        ("windows-dev", "windows-app", "windows", "fixture-windows-dev", "winget test", "development", "MSIX"),
        ("windows-prod", "windows-app", "windows", "fixture-windows", "Microsoft Store", "production", "MSIX"),
    )
    return "# Architecture\n\n## Release Targets\n\nExpected deployable surfaces: public-api, android-app, macos-app, windows-app\n\n" + "".join(
        target_block(*definition) for definition in definitions
    )


def multi_surface_deployment() -> str:
    rows = [
        ("api-dev", "public-api", "development", "API development gateway;fixture-api-dev", "pending", "pending", "pending", "pending", "pending", "pending", "pending"),
        ("api-prod", "public-api", "production", "API production gateway;fixture-api-prod", "https://api.example.com", "a" * 40, "a" * 40, "api-deployment-1", "API route answered the smoke check", "2026-09-03T12:00:00Z", "PASS"),
        ("android-dev", "android-app", "development", "Play internal track;fixture-android-dev", "pending", "pending", "pending", "pending", "pending", "pending", "pending"),
        ("android-prod", "android-app", "production", "Google Play production;fixture-android-prod", "n/a — artifact-only:play-build-1; no network endpoint", "a" * 40, "a" * 40, "play-build-1", "approved build installed and passed smoke", "2026-09-03T12:01:00Z", "PASS"),
        ("macos-dev", "macos-app", "development", "TestFlight;fixture-macos-dev", "pending", "pending", "pending", "pending", "pending", "pending", "pending"),
        ("macos-prod", "macos-app", "production", "direct download;fixture-macos-prod", "https://downloads.example.com/macos", "a" * 40, "a" * 40, "dmg-build-1", "signed artifact downloaded and installed", "2026-09-03T12:02:00Z", "PASS"),
        ("windows-dev", "windows-app", "development", "winget test;fixture-windows-dev", "pending", "pending", "pending", "pending", "pending", "pending", "pending"),
        ("windows-prod", "windows-app", "production", "Microsoft Store;fixture-windows-prod", "n/a — artifact-only:msix-build-1; no network endpoint", "a" * 40, "a" * 40, "msix-build-1", "store package installed and passed smoke", "2026-09-03T12:03:00Z", "PASS"),
    ]
    table = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    release_units = """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| public-api | api | fixture-api | fixture-api-dev | API production gateway;fixture-api-prod | API development gateway;fixture-api-dev |
| android-app | android | fixture-android | fixture-android-dev | Google Play production;fixture-android-prod | Play internal track;fixture-android-dev |
| macos-app | macos | fixture-macos | fixture-macos-dev | direct download;fixture-macos-prod | TestFlight;fixture-macos-dev |
| windows-app | windows | fixture-windows | fixture-windows-dev | Microsoft Store;fixture-windows-prod | winget test;fixture-windows-dev |
"""
    base = CI_CONNECTED_DEPLOYMENT.replace(
        """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| browser-extension | extension | example-extension | example-extension-dev | Chrome Web Store;production | Chrome Web Store;test |""",
        release_units.rstrip(),
    )
    return base + f"""

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{table}
"""

RELEASE_ARCHITECTURE = """# Architecture

## Release Targets

Expected deployable surfaces: web-app

### Release Target: web-dev
- Surface: web-app
- Surface class: hosted_web
- Public discoverability: yes
- Surface suffix: web
- Release name: example-web-dev
- Provider: Cloudflare
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: static bundle
- Signing requirement: not required
- Exact channel / track: development route
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: route answers the smoke check
- Rollout: development users
- Rollback / forward-fix: deploy the prior development bundle

### Release Target: web-prod
- Surface: web-app
- Surface class: hosted_web
- Public discoverability: yes
- Surface suffix: web
- Release name: example-web
- Provider: Cloudflare
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: static bundle
- Signing requirement: not required
- Exact channel / track: production route
- Submission / promotion / review / manual approval path: candidate checks, promotion, owner approval
- Availability signal: route answers the smoke check
- Rollout: all users
- Rollback / forward-fix: deploy the prior bundle
"""

ARCHITECTURE_BACKED_DEPLOYMENT = GOOD_DEPLOYMENT + f"""

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| web-dev | web-app | development | Cloudflare;development route | pending | pending | pending | pending | pending | pending | pending |
| web-prod | web-app | production | Cloudflare;production route | https://example.com | {"a" * 40} | {"a" * 40} | deployment-1 | production route answered the API smoke check | 2026-09-03T12:00:00Z | PASS |
"""

NATIVE_ARCHITECTURE = """# Architecture

## Release Targets

Expected deployable surfaces: ios-app

### Release Target: ios-dev
- Surface: ios-app
- Surface class: ios
- Public discoverability: no
- Surface suffix: ios
- Release name: example-ios-dev
- Provider: TestFlight
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: IPA
- Signing requirement: distribution certificate
- Exact channel / track: internal testers
- Submission / promotion / review / manual approval path: upload and owner approval
- Availability signal: build is installable and passes smoke
- Rollout: internal testers
- Rollback / forward-fix: halt rollout and submit a corrected signed build

### Release Target: ios-prod
- Surface: ios-app
- Surface class: ios
- Public discoverability: no
- Surface suffix: ios
- Release name: example-ios
- Provider: App Store
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: IPA
- Signing requirement: distribution certificate
- Exact channel / track: production store
- Submission / promotion / review / manual approval path: store review and owner promotion
- Availability signal: build is installable and passes smoke
- Rollout: phased store rollout
- Rollback / forward-fix: halt rollout and submit a corrected signed build
"""

NATIVE_BASE = CI_CONNECTED_DEPLOYMENT.replace(
    """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| browser-extension | extension | example-extension | example-extension-dev | Chrome Web Store;production | Chrome Web Store;test |""",
    """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| ios-app | ios | example-ios | example-ios-dev | App Store;production store | TestFlight;internal testers |""",
)

NATIVE_DEPLOYMENT = NATIVE_BASE + f"""

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ios-dev | ios-app | development | TestFlight;internal testers | pending | pending | pending | pending | pending | pending | pending |
| ios-prod | ios-app | production | App Store;production store | n/a — artifact-only:appstore-build-9; no network endpoint | {"b" * 40} | {"b" * 40} | appstore-build-9 | URL returned HTTP 200 | 2026-09-03T12:00:00Z | PASS |
"""


class DeploymentRecordTests(unittest.TestCase):
    def test_a_resolved_record_with_one_verified_row_passes(self) -> None:
        findings = check_deployment.check_deployment_text(GOOD_DEPLOYMENT)
        self.assertEqual([], findings)

    def test_architecture_backed_release_targets_pass(self) -> None:
        findings = check_deployment.check_deployment_text(
            ARCHITECTURE_BACKED_DEPLOYMENT, architecture_text=RELEASE_ARCHITECTURE
        )
        self.assertEqual([], findings)

    def test_api_android_and_desktop_targets_join_a_multi_surface_architecture(self) -> None:
        findings = check_deployment.check_deployment_text(
            multi_surface_deployment(),
            architecture_text=multi_surface_architecture(),
        )
        self.assertEqual([], findings)

    def test_architecture_backed_records_reject_missing_invented_and_duplicate_targets(self) -> None:
        missing = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "| web-dev | web-app | development | Cloudflare;development route | pending | pending | pending | pending | pending | pending | pending |\n",
            "",
        )
        invented = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "| web-dev | web-app | development | Cloudflare;development route |",
            "| invented-prod | web-app | development | Cloudflare;development route |",
        )
        duplicate = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "| web-prod | web-app | production | Cloudflare;production route | https://example.com | "
            f'{"a" * 40} | {"a" * 40} | deployment-1 | production route answered the API smoke check | '
            "2026-09-03T12:00:00Z | PASS |",
            "| web-prod | web-app | production | Cloudflare;production route | https://example.com | "
            f'{"a" * 40} | {"a" * 40} | deployment-1 | production route answered the API smoke check | '
            "2026-09-03T12:00:00Z | PASS |\n"
            "| web-prod | web-app | production | Cloudflare;production route | https://example.com | "
            f'{"a" * 40} | {"a" * 40} | deployment-1 | production route answered the API smoke check | '
            "2026-09-03T12:00:00Z | PASS |",
        )
        cases = (
            ("missing", missing, "architecture release targets are missing: web-dev"),
            ("invented", invented, "is not an architecture release target"),
            ("duplicate", duplicate, "duplicate release target 'web-prod'"),
        )
        for label, deployment, expected in cases:
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        deployment, architecture_text=RELEASE_ARCHITECTURE
                    )
                )
                self.assertIn(expected, findings)

    def test_architecture_backed_pass_requires_equal_exact_identities(self) -> None:
        mismatch = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            f'| web-prod | web-app | production | Cloudflare;production route | https://example.com | {"a" * 40} | {"a" * 40} | deployment-1 |',
            f'| web-prod | web-app | production | Cloudflare;production route | https://example.com | {"a" * 40} | {"b" * 40} | deployment-1 |',
        )
        missing_artifact = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "| web-prod | web-app | production | Cloudflare;production route | https://example.com | "
            f'{"a" * 40} | {"a" * 40} | deployment-1 |',
            "| web-prod | web-app | production | Cloudflare;production route | https://example.com | "
            f'{"a" * 40} | {"a" * 40} | n/a |',
        )
        self.assertIn(
            "requires Expected and Deployed SHAs to be identical",
            "\n".join(
                check_deployment.check_deployment_text(
                    mismatch, architecture_text=RELEASE_ARCHITECTURE
                )
            ),
        )
        self.assertIn(
            "needs an exact artifact or build identity",
            "\n".join(
                check_deployment.check_deployment_text(
                    missing_artifact, architecture_text=RELEASE_ARCHITECTURE
                )
            ),
        )

    def test_architecture_backed_status_requires_exact_channel_and_endpoint(self) -> None:
        wrong_channel = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "Cloudflare;production route | https://example.com",
            "Cloudflare;wrong-route | https://example.com",
        )
        wrong_endpoint = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "Cloudflare;production route | https://example.com",
            "Cloudflare;production route | pending",
        )
        self.assertIn(
            "provider/channel must be",
            "\n".join(
                check_deployment.check_deployment_text(
                    wrong_channel, architecture_text=RELEASE_ARCHITECTURE
                )
            ),
        )
        self.assertIn(
            "target-specific endpoint",
            "\n".join(
                check_deployment.check_deployment_text(
                    wrong_endpoint, architecture_text=RELEASE_ARCHITECTURE
                )
            ),
        )
        userinfo = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "https://example.com", "https://token@example.com"
        )
        self.assertIn(
            "must not contain userinfo",
            "\n".join(
                check_deployment.check_deployment_text(
                    userinfo, architecture_text=RELEASE_ARCHITECTURE
                )
            ),
        )
        bad_native = NATIVE_DEPLOYMENT.replace(
            "n/a — artifact-only:appstore-build-9; no network endpoint", "x", 1
        )
        self.assertIn(
            "artifact-only disposition",
            "\n".join(
                check_deployment.check_deployment_text(
                    bad_native, architecture_text=NATIVE_ARCHITECTURE
                )
            ),
        )
        for bad_identity in ("abcd", "test", "n/a — x", "n/a — same"):
            with self.subTest(bad_identity):
                malformed = NATIVE_DEPLOYMENT.replace(
                    "n/a — artifact-only:appstore-build-9; no network endpoint", bad_identity, 1
                )
                self.assertIn(
                    "native/store",
                    "\n".join(
                        check_deployment.check_deployment_text(
                            malformed, architecture_text=NATIVE_ARCHITECTURE
                        )
                    ),
                )

    def test_native_pass_requires_install_or_artifact_evidence_not_url_parity(self) -> None:
        findings = "\n".join(
            check_deployment.check_deployment_text(
                NATIVE_DEPLOYMENT, architecture_text=NATIVE_ARCHITECTURE
            )
        )
        self.assertIn(
            "install/download or artifact/build proof",
            findings,
        )

    def test_a_ci_connected_record_passes_the_same_checks(self) -> None:
        findings = check_deployment.check_deployment_text(CI_CONNECTED_DEPLOYMENT)
        self.assertEqual([], findings)

    def test_a_shared_resource_id_fails_the_isolation_check(self) -> None:
        findings = check_deployment.check_deployment_text(SHARED_RESOURCE_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn(
            "must not share one resource between production and development", joined
        )

    def test_placeholders_and_incoherent_rows_fail(self) -> None:
        findings = check_deployment.check_deployment_text(BAD_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn("missing the development row", joined)
        self.assertIn("unresolved placeholder", joined)
        self.assertIn("must be a full lowercase SHA once checked", joined)
        self.assertIn("checked but has no status", joined)

    def test_a_pass_with_mismatched_expected_and_deployed_shas_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            f'| development | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | 2026-09-03 | PASS |',
            f'| development | https://abc.example.pages.dev | {"a" * 40} | {"b" * 40} | 2026-09-03 | PASS |',
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn(
            "PASS requires Expected head and Deployed SHA to be identical", findings
        )

    def test_environment_status_uses_a_closed_vocabulary(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| development | https://abc.example.pages.dev | "
            f'{"a" * 40} | {"a" * 40} | 2026-09-03 | PASS |',
            "| development | https://abc.example.pages.dev | "
            f'{"a" * 40} | {"a" * 40} | 2026-09-03 | verified |',
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn("has invalid status 'verified'", findings)

    def test_a_status_without_a_checked_value_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| production | | | | | |",
            f'| production | https://example.com | {"a" * 40} | {"a" * 40} | | PASS |',
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn("status 'PASS' requires a Checked value", findings)

    def test_missing_handoff_sections_fail(self) -> None:
        findings = check_deployment.check_deployment_text(BAD_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn("Required Secrets and Variables: missing section", joined)
        self.assertIn("External Console Setup: missing section", joined)
        self.assertIn("Release Unit Names: missing section", joined)

    def test_release_unit_names_reject_prod_and_mismatched_development(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| web-app | web | example-web | example-web-dev | Cloudflare;production route | Cloudflare;development route |",
            "| web-app | web | example-web-prod | example-web-development | Cloudflare;production route | Cloudflare;development route |",
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn("production release name must not end in -prod", findings)
        self.assertIn(
            "development release name must equal example-web-prod-dev", findings
        )

    def test_release_unit_names_require_surface_suffix(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| web-app | web | example-web | example-web-dev | Cloudflare;production route | Cloudflare;development route |",
            "| web-app | web | example-service | example-service-dev | Cloudflare;production route | Cloudflare;development route |",
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn("production release name must end in -web", findings)

    def test_release_unit_names_reject_cross_surface_name_reuse(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| web-app | web | example-web | example-web-dev | Cloudflare;production route | Cloudflare;development route |",
            "| web-app | web | example-web | example-web-dev | Cloudflare;production route | Cloudflare;development route |\n"
            "| marketing-web | web | example-web | example-web-dev | Cloudflare Pages;production route | Cloudflare Pages;development route |",
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn(
            "release name 'example-web' is reused by surfaces 'web-app' and 'marketing-web'",
            findings,
        )

    def test_secret_value_column_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Status |",
            "| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Secret value | Status |",
        )
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "must not include a secret-value column", "\n".join(findings)
        )

    def test_duplicate_required_level_two_section_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "## External Console Setup",
            "## External Console Setup\n\n## External Console Setup",
            1,
        )
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "External Console Setup: duplicate required level-2 section",
            "\n".join(findings),
        )

    def test_duplicate_environment_row_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| production | | | | | |",
            "| development | https://other.example.pages.dev | | | | |\n"
            "| production | | | | | |",
            1,
        )
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn("Environment Status: duplicate development row", "\n".join(findings))

    def test_duplicate_handoff_identity_fails(self) -> None:
        duplicate = (
            "| AUTH_SECRET | secret | app runtime | Cloudflare preview Worker secret | "
            "Cloudflare production Worker secret | operator-generated | verified |"
        )
        deployment = GOOD_DEPLOYMENT.replace(duplicate, duplicate + "\n" + duplicate, 1)
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "Required Secrets and Variables: duplicate identity row 'AUTH_SECRET'",
            "\n".join(findings),
        )

    def test_duplicate_resource_identity_fails(self) -> None:
        duplicate = "| D1 database | d1-prod-001 | d1-preview-001 |"
        deployment = GOOD_DEPLOYMENT.replace(duplicate, duplicate + "\n" + duplicate, 1)
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "Resource Isolation: duplicate identity row 'D1 database'",
            "\n".join(findings),
        )

    def test_duplicate_unknown_resource_identity_also_fails(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| D1 database | d1-prod-001 | d1-preview-001 |",
            "| Queue | queue-prod-001 | queue-preview-001 |\n"
            "| Queue | queue-prod-002 | queue-preview-002 |",
            1,
        )
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "Resource Isolation: duplicate identity row 'Queue'",
            "\n".join(findings),
        )

    def test_identity_lookalikes_in_other_sections_are_ignored(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "- Protected resources preview must never bind: prod-db",
            "- Protected resources preview must never bind: prod-db\n"
            "| D1 database | d1-prod-001 | d1-prod-001 |",
            1,
        )
        findings = check_deployment.check_deployment_text(deployment)
        self.assertNotIn("must not share one resource", "\n".join(findings))

    def test_section_headings_in_code_and_comments_are_ignored(self) -> None:
        examples = (
            "```markdown\n## Environment Status\n```",
            "    ## Environment Status",
            "<!-- ## Environment Status -->",
        )
        for example in examples:
            with self.subTest(example=example):
                deployment = GOOD_DEPLOYMENT.replace(
                    "- Protected resources preview must never bind: prod-db",
                    "- Protected resources preview must never bind: prod-db\n" + example,
                    1,
                )
                self.assertEqual([], check_deployment.check_deployment_text(deployment))

    def test_tables_in_code_and_comments_cannot_satisfy_or_duplicate_live_rows(self) -> None:
        examples = (
            "```markdown\n| development | https://fake.example | | | | |\n```",
            "    | development | https://fake.example | | | | |",
            "<!--\n| development | https://fake.example | | | | |\n-->",
        )
        for example in examples:
            with self.subTest(example=example):
                deployment = GOOD_DEPLOYMENT.replace(
                    "## Environment Status",
                    "## Environment Status\n\n" + example,
                    1,
                )
                self.assertEqual([], check_deployment.check_deployment_text(deployment))

    def test_atx_closing_hash_heading_is_normalized_for_duplicate_detection(self) -> None:
        deployment = GOOD_DEPLOYMENT + "\n## Environment Status ##\n"
        findings = check_deployment.check_deployment_text(deployment)
        self.assertIn(
            "Environment Status: duplicate required level-2 section",
            "\n".join(findings),
        )


class ConfigurePlaceholderTests(unittest.TestCase):
    def test_unresolved_markers_are_reported_with_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text(
                "# Rules\n\n| design_direction | UI | <bundled pass> |\n\n"
                "- Production URL: <fill>\n",
                encoding="utf-8",
            )
            findings = configure_project_context.unresolved_placeholders(root)
            joined = "\n".join(findings)
            self.assertIn("<bundled", joined)
            self.assertIn("<fill>", joined)
            self.assertIn("line 3", joined)
            self.assertIn("line 5", joined)

    def test_a_resolved_agents_md_reports_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pin = "0" * 64
            (root / "AGENTS.md").write_text(
                "# Rules\n\n## Skill Bindings\n\n"
                "| Slot | Stage | Bound skill | Pinned SHA-256 |\n"
                "| --- | --- | --- | --- |\n"
                f"| ui_design | UI | `design-taste-frontend` | {pin} |\n"
                f"| style_integration | style | `design-taste-frontend` | {pin} |\n"
                f"| design_compilation | pair | `design-taste-frontend` | {pin} |\n"
                f"| frontend_implementation | code | `design-taste-frontend` | {pin} |\n"
                f"| ui_quality_verification | quality | `design-taste-frontend` | {pin} |\n"
                f"| code_security_verification | security | `design-taste-frontend` | {pin} |\n",
                encoding="utf-8",
            )
            self.assertEqual([], configure_project_context.unresolved_placeholders(root))


if __name__ == "__main__":
    unittest.main()
