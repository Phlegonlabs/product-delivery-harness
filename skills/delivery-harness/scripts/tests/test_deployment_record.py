#!/usr/bin/env python3
"""check_deployment.py and configure_project_context placeholder checks."""

from __future__ import annotations

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_deployment  # noqa: E402
import configure_project_context  # noqa: E402
import release_targets  # noqa: E402


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
| development | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | 2026-09-03T10:00:00Z | PASS |
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
| production | https://example.com | short | nope | 2026-09-03T10:00:00Z | |
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
| development | https://abc.example.pages.dev | {"b" * 40} | {"b" * 40} | 2026-09-03T10:00:00Z | PASS |
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
- Surface class: {'hosted_web' if surface == 'web-app' else 'hosted_api' if surface == 'public-api' else 'android' if surface == 'android-app' else 'macos' if surface == 'macos-app' else 'windows' if surface == 'windows-app' else 'linux' if surface == 'linux-app' else 'other_nonpublic'}
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
        ("linux-dev", "linux-app", "linux", "fixture-linux-dev", "Flathub beta", "development", "Flatpak"),
        ("linux-prod", "linux-app", "linux", "fixture-linux", "Flathub", "production", "Flatpak"),
    )
    return "# Architecture\n\n## Release Targets\n\nExpected deployable surfaces: public-api, android-app, macos-app, windows-app, linux-app\n\n" + "".join(
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
        ("linux-dev", "linux-app", "development", "Flathub beta;fixture-linux-dev", "pending", "pending", "pending", "pending", "pending", "pending", "pending"),
        ("linux-prod", "linux-app", "production", "Flathub;fixture-linux-prod", "https://flathub.org/apps/com.example.Fixture", "a" * 40, "a" * 40, "flatpak-build-1", "Flatpak installed from Flathub and passed smoke", "2026-09-03T12:04:00Z", "PASS"),
    ]
    table = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    release_units = """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| public-api | api | fixture-api | fixture-api-dev | API production gateway;fixture-api-prod | API development gateway;fixture-api-dev |
| android-app | android | fixture-android | fixture-android-dev | Google Play production;fixture-android-prod | Play internal track;fixture-android-dev |
| macos-app | macos | fixture-macos | fixture-macos-dev | direct download;fixture-macos-prod | TestFlight;fixture-macos-dev |
| windows-app | windows | fixture-windows | fixture-windows-dev | Microsoft Store;fixture-windows-prod | winget test;fixture-windows-dev |
| linux-app | linux | fixture-linux | fixture-linux-dev | Flathub;fixture-linux-prod | Flathub beta;fixture-linux-dev |
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

TYPED_ARCHITECTURE = """# Architecture

## Release Targets

Expected deployable surfaces: mcp-server, assistant-listing, messaging-bot

### Release Target: mcp-dev
- Surface: mcp-server
- Surface class: mcp_server
- Public discoverability: yes
- Surface suffix: mcp
- Release name: example-mcp-dev
- Provider: PyPI
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: wheel
- Signing requirement: not required
- Exact channel / track: test index
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: package install passes smoke
- Rollout: test index users
- Rollback / forward-fix: publish a corrected wheel

### Release Target: mcp-prod
- Surface: mcp-server
- Surface class: mcp_server
- Public discoverability: yes
- Surface suffix: mcp
- Release name: example-mcp
- Provider: PyPI
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: wheel
- Signing requirement: not required
- Exact channel / track: production index
- Submission / promotion / review / manual approval path: publish and owner approval
- Availability signal: package install passes smoke
- Rollout: all users after smoke passes
- Rollback / forward-fix: publish a corrected wheel

### Release Target: listing-dev
- Surface: assistant-listing
- Surface class: assistant_listing
- Public discoverability: yes
- Surface suffix: listing
- Release name: example-listing-dev
- Provider: Assistant Store
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: no independent artifact
- Signing requirement: store managed
- Exact channel / track: staging placement
- Submission / promotion / review / manual approval path: store review and owner approval
- Availability signal: listing review passes acceptance
- Rollout: staged store rollout
- Rollback / forward-fix: unpublish the listing revision

### Release Target: listing-prod
- Surface: assistant-listing
- Surface class: assistant_listing
- Public discoverability: yes
- Surface suffix: listing
- Release name: example-listing
- Provider: Assistant Store
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: no independent artifact
- Signing requirement: store managed
- Exact channel / track: featured placement
- Submission / promotion / review / manual approval path: store review and owner promotion
- Availability signal: listing review passes acceptance
- Rollout: phased store rollout
- Rollback / forward-fix: unpublish the listing revision

### Release Target: bot-dev
- Surface: messaging-bot
- Surface class: messaging_bot
- Public discoverability: no
- Surface suffix: bot
- Release name: example-bot-dev
- Provider: Bot Grid
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: service deployment
- Signing requirement: not required
- Exact channel / track: staging workspace
- Submission / promotion / review / manual approval path: candidate checks and owner approval
- Availability signal: webhook smoke check answers
- Rollout: staging workspace
- Rollback / forward-fix: redeploy the prior service revision

### Release Target: bot-prod
- Surface: messaging-bot
- Surface class: messaging_bot
- Public discoverability: no
- Surface suffix: bot
- Release name: example-bot
- Provider: Bot Grid
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: service deployment
- Signing requirement: not required
- Exact channel / track: production workspace
- Submission / promotion / review / manual approval path: candidate checks, promotion, owner approval
- Availability signal: webhook smoke check answers
- Rollout: all workspaces after smoke passes
- Rollback / forward-fix: redeploy the prior service revision
"""

TYPED_BASE = CI_CONNECTED_DEPLOYMENT.replace(
    """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| browser-extension | extension | example-extension | example-extension-dev | Chrome Web Store;production | Chrome Web Store;test |""",
    """| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |
| --- | --- | --- | --- | --- | --- |
| mcp-server | mcp | example-mcp | example-mcp-dev | PyPI;production index | PyPI;test index |
| assistant-listing | listing | example-listing | example-listing-dev | Assistant Store;featured placement | Assistant Store;staging placement |
| messaging-bot | bot | example-bot | example-bot-dev | Bot Grid;production workspace | Bot Grid;staging workspace |""",
)

TYPED_DEPLOYMENT = TYPED_BASE + f"""

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mcp-dev | mcp-server | development | PyPI;test index | pending | pending | pending | pending | pending | pending | pending |
| mcp-prod | mcp-server | production | PyPI;production index | https://pypi.org/project/example-mcp/ | {"c" * 40} | {"c" * 40} | wheel-9 | wheel installed and passed smoke | 2026-09-03T12:00:00Z | PASS |
| listing-dev | assistant-listing | development | Assistant Store;staging placement | pending | pending | pending | pending | pending | pending | pending |
| listing-prod | assistant-listing | production | Assistant Store;featured placement | n/a — channel-only:Assistant Store;featured placement; no network endpoint | {"c" * 40} | {"c" * 40} | n/a | listing approved and installable on the store | 2026-09-03T12:01:00Z | PASS |
| bot-dev | messaging-bot | development | Bot Grid;staging workspace | pending | pending | pending | pending | pending | pending | pending |
| bot-prod | messaging-bot | production | Bot Grid;production workspace | https://bot-gateway.example.com | {"c" * 40} | {"c" * 40} | bot-deployment-7 | webhook answered the smoke check | 2026-09-03T12:02:00Z | PASS |
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

    def test_hosted_http_is_limited_to_private_loopback_development(self) -> None:
        production_http = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "Cloudflare;production route | https://example.com",
            "Cloudflare;production route | http://127.0.0.1",
        )
        public_development_http = ARCHITECTURE_BACKED_DEPLOYMENT.replace(
            "| web-dev | web-app | development | Cloudflare;development route | "
            "pending | pending | pending | pending | pending | pending | pending |",
            "| web-dev | web-app | development | Cloudflare;development route | "
            f'http://localhost | {"a" * 40} | {"a" * 40} | deployment-dev | '
            "development route answered the smoke check | 2026-09-03T11:00:00Z | PASS |",
        )
        private_architecture = RELEASE_ARCHITECTURE.replace(
            "Public discoverability: yes", "Public discoverability: no"
        )
        private_development_http = public_development_http

        for label, deployment, architecture in (
            ("production-loopback", production_http, RELEASE_ARCHITECTURE),
            ("public-development", public_development_http, RELEASE_ARCHITECTURE),
        ):
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        deployment, architecture_text=architecture
                    )
                )
                self.assertIn("hosted endpoint must use HTTPS", findings)

        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                private_development_http,
                architecture_text=private_architecture,
            ),
        )

    def test_api_android_and_desktop_targets_join_a_multi_surface_architecture(self) -> None:
        findings = check_deployment.check_deployment_text(
            multi_surface_deployment(),
            architecture_text=multi_surface_architecture(),
        )
        self.assertEqual([], findings)

    def test_linux_pass_needs_install_evidence_not_a_page_check(self) -> None:
        page_only = multi_surface_deployment().replace(
            "Flatpak installed from Flathub and passed smoke", "listing page returned 200", 1,
        )
        findings = check_deployment.check_deployment_text(
            page_only, architecture_text=multi_surface_architecture(),
        )
        self.assertEqual([
            "Release Target Status: PASS target linux-prod availability evidence "
            "must name install/download proof; upload-only evidence stays pending"
        ], findings)

    def test_store_upload_only_evidence_stays_pending(self) -> None:
        uploaded = multi_surface_deployment().replace(
            "approved build installed and passed smoke",
            "signed AAB build artifact uploaded to Play Console", 1,
        )
        findings = check_deployment.check_deployment_text(
            uploaded, architecture_text=multi_surface_architecture(),
        )
        self.assertEqual([
            "Release Target Status: PASS target android-prod availability evidence "
            "must name install/download proof; upload-only evidence stays pending"
        ], findings)
        pending = uploaded.replace(
            "uploaded to Play Console | 2026-09-03T12:01:00Z | PASS |",
            "uploaded to Play Console | 2026-09-03T12:01:00Z | pending |", 1,
        )
        self.assertEqual([], check_deployment.check_deployment_text(
            pending, architecture_text=multi_surface_architecture(),
        ))
        # A package index has no install gate; its published artifact still passes.
        published = TYPED_DEPLOYMENT.replace(
            "wheel installed and passed smoke", "wheel build artifact uploaded to PyPI", 1,
        )
        self.assertEqual([], check_deployment.check_deployment_text(
            published, architecture_text=TYPED_ARCHITECTURE,
        ))

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

    def test_native_pass_requires_install_evidence_not_url_parity(self) -> None:
        findings = "\n".join(
            check_deployment.check_deployment_text(
                NATIVE_DEPLOYMENT, architecture_text=NATIVE_ARCHITECTURE
            )
        )
        self.assertIn(
            "must name install/download proof; upload-only evidence stays pending",
            findings,
        )

    def test_typed_listing_and_resource_targets_pass(self) -> None:
        findings = check_deployment.check_deployment_text(
            TYPED_DEPLOYMENT, architecture_text=TYPED_ARCHITECTURE
        )
        self.assertEqual([], findings)

    def test_listing_target_needs_listing_url_or_exact_artifact_disposition(self) -> None:
        bad_url = TYPED_DEPLOYMENT.replace(
            "https://pypi.org/project/example-mcp/",
            "https://pypi.org/project/example-mcp/?utm=x",
            1,
        )
        self.assertIn(
            "native/store endpoint must be a credential-free canonical https listing/download URL",
            "\n".join(
                check_deployment.check_deployment_text(
                    bad_url, architecture_text=TYPED_ARCHITECTURE
                )
            ),
        )
        artifact_only = TYPED_DEPLOYMENT.replace(
            "https://pypi.org/project/example-mcp/",
            "n/a — artifact-only:wheel-9; no network endpoint",
            1,
        )
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                artifact_only, architecture_text=TYPED_ARCHITECTURE
            ),
        )
        bad_artifact_disposition = artifact_only.replace(
            "n/a — artifact-only:wheel-9; no network endpoint", "x", 1
        )
        self.assertIn(
            "native/store artifact-only disposition must exactly match the artifact/build identity",
            "\n".join(
                check_deployment.check_deployment_text(
                    bad_artifact_disposition, architecture_text=TYPED_ARCHITECTURE
                )
            ),
        )
        bad_channel_disposition = TYPED_DEPLOYMENT.replace(
            "n/a — channel-only:Assistant Store;featured placement; no network endpoint",
            "n/a — channel-only:Other Store;featured placement; no network endpoint",
            1,
        )
        self.assertIn(
            "native/store channel-only disposition must exactly match Provider;channel and artifact n/a",
            "\n".join(
                check_deployment.check_deployment_text(
                    bad_channel_disposition, architecture_text=TYPED_ARCHITECTURE
                )
            ),
        )

    def test_listing_target_availability_requires_install_or_artifact_evidence(self) -> None:
        findings = "\n".join(
            check_deployment.check_deployment_text(
                TYPED_DEPLOYMENT.replace(
                    "wheel installed and passed smoke", "URL returned HTTP 200", 1
                ),
                architecture_text=TYPED_ARCHITECTURE,
            )
        )
        self.assertIn("install/download or artifact/build proof", findings)

    def test_resource_target_needs_substantive_typed_identity(self) -> None:
        absent = TYPED_DEPLOYMENT.replace(
            "https://bot-gateway.example.com", "n/a", 1
        )
        self.assertIn(
            "endpoint/domain is missing",
            "\n".join(
                check_deployment.check_deployment_text(
                    absent, architecture_text=TYPED_ARCHITECTURE
                )
            ),
        )
        nonsubstantive = TYPED_DEPLOYMENT.replace(
            "https://bot-gateway.example.com", "n/a — maintenance window", 1
        )
        self.assertIn(
            "typed endpoint/resource identity is not substantive",
            "\n".join(
                check_deployment.check_deployment_text(
                    nonsubstantive, architecture_text=TYPED_ARCHITECTURE
                )
            ),
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
            f'| development | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | 2026-09-03T10:00:00Z | PASS |',
            f'| development | https://abc.example.pages.dev | {"a" * 40} | {"b" * 40} | 2026-09-03T10:00:00Z | PASS |',
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn(
            "PASS requires Expected head and Deployed SHA to be identical", findings
        )

    def test_environment_status_uses_a_closed_vocabulary(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| development | https://abc.example.pages.dev | "
            f'{"a" * 40} | {"a" * 40} | 2026-09-03T10:00:00Z | PASS |',
            "| development | https://abc.example.pages.dev | "
            f'{"a" * 40} | {"a" * 40} | 2026-09-03T10:00:00Z | verified |',
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

    def test_a_pass_row_without_url_or_checked_time_fails(self) -> None:
        # An empty URL and Checked cell must not skip the status and SHA checks.
        deployment = GOOD_DEPLOYMENT.replace(
            "| production | | | | | |",
            f'| production | | {"a" * 40} | {"b" * 40} | | PASS |',
            1,
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn("production is recorded but has no URL", findings)
        self.assertIn("status 'PASS' requires a Checked value", findings)
        self.assertIn(
            "PASS requires Expected head and Deployed SHA to be identical", findings
        )

    def test_a_checked_value_must_be_an_rfc3339_time(self) -> None:
        deployment = GOOD_DEPLOYMENT.replace(
            "| 2026-09-03T10:00:00Z | PASS |", "| yesterday-ish | PASS |", 1
        )

        findings = "\n".join(check_deployment.check_deployment_text(deployment))

        self.assertIn(
            "development Checked must be RFC3339 with a real timezone", findings
        )

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

    def test_cli_reports_malformed_utf8_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            deployment = root / "DEPLOYMENT.md"
            architecture = root / "architecture.md"
            deployment.write_text(GOOD_DEPLOYMENT, encoding="utf-8")
            architecture.write_bytes(b"\xff")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = check_deployment.main(
                    [
                        "--deployment",
                        str(deployment),
                        "--architecture",
                        str(architecture),
                    ]
                )
            self.assertEqual(2, status)
            self.assertIn("cannot read architecture record", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


LITERAL = "n/a — initial delivery: production is the first deployed environment"
DEV_UNIT_ROW = (
    "| web-app | web | example-web | example-web-dev | "
    "Cloudflare;production route | Cloudflare;development route |"
)
DEV_ENVIRONMENT_ROW = (
    f'| development | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | '
    "2026-09-03T10:00:00Z | PASS |"
)


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new)


def with_delivery_kind(text: str, value: str | None) -> str:
    """Append a Branch Promotion section; None leaves the Delivery kind line out."""

    line = "- Run branch: refs/heads/run/example" if value is None else f"- Delivery kind: {value}"
    return text + f"\n## Branch Promotion\n\n{line}\n"


def literal_variants() -> dict[str, tuple[str, str]]:
    """One GOOD_DEPLOYMENT variant per cell or line that may hold the literal."""

    def variant(old: str, new: str) -> str:
        return replace_once(GOOD_DEPLOYMENT, old, new)

    return {
        "Record Preview URL pattern": (
            variant(
                "- Preview URL pattern: <hash>.example.pages.dev",
                f"- Preview URL pattern: {LITERAL}",
            ),
            "Record Preview URL pattern",
        ),
        "Record protected resources": (
            variant(
                "- Protected resources preview must never bind: prod-db",
                f"- Protected resources preview must never bind: {LITERAL}",
            ),
            "Record Protected resources preview must never bind",
        ),
        "development release name": (
            variant(DEV_UNIT_ROW, DEV_UNIT_ROW.replace("example-web-dev", LITERAL)),
            "Release Unit Names web-app development release name",
        ),
        "development provider": (
            variant(
                DEV_UNIT_ROW,
                DEV_UNIT_ROW.replace("Cloudflare;development route", LITERAL),
            ),
            "Release Unit Names web-app development provider / channel",
        ),
        "development resource": (
            variant(
                "| D1 database | d1-prod-001 | d1-preview-001 |",
                f"| D1 database | d1-prod-001 | {LITERAL} |",
            ),
            "Resource Isolation D1 database development resource",
        ),
        "preview placement": (
            variant("Cloudflare preview Worker secret", LITERAL),
            "Required Secrets and Variables AUTH_SECRET preview placement",
        ),
        "external preview target": (
            variant("https://abc.example.pages.dev/callback", LITERAL),
            "External Console Setup Auth provider preview / non-production",
        ),
        "development environment row": (
            variant(DEV_ENVIRONMENT_ROW, f"| development | {LITERAL} | | | | |"),
            "Environment Status development URL",
        ),
    }


class DeliveryKindTests(unittest.TestCase):
    def test_both_delivery_kinds_are_accepted(self) -> None:
        for kind in ("initial_delivery", "enhancement"):
            with self.subTest(kind):
                self.assertEqual(
                    (kind, ""),
                    check_deployment.parse_delivery_kind(
                        with_delivery_kind(GOOD_DEPLOYMENT, kind)
                    ),
                )

    def test_a_missing_unfilled_or_unknown_kind_is_rejected(self) -> None:
        fenced = GOOD_DEPLOYMENT + (
            "\n## Branch Promotion\n\n```\n- Delivery kind: initial_delivery\n```\n"
        )
        repeated = with_delivery_kind(GOOD_DEPLOYMENT, "enhancement") + (
            "- Delivery kind: initial_delivery\n"
        )
        cases = (
            ("no section", GOOD_DEPLOYMENT, "the Delivery kind line is missing"),
            ("no line", with_delivery_kind(GOOD_DEPLOYMENT, None), "line is missing"),
            ("fenced line", fenced, "line is missing"),
            (
                "placeholder",
                with_delivery_kind(GOOD_DEPLOYMENT, "<initial_delivery | enhancement>"),
                "is not filled in",
            ),
            ("empty", with_delivery_kind(GOOD_DEPLOYMENT, ""), "is not filled in"),
            (
                "unknown",
                with_delivery_kind(GOOD_DEPLOYMENT, "hotfix"),
                "'hotfix' is not initial_delivery or enhancement",
            ),
            (
                "wrong case",
                with_delivery_kind(GOOD_DEPLOYMENT, "Initial_Delivery"),
                "'Initial_Delivery' is not initial_delivery or enhancement",
            ),
            ("repeated", repeated, "appears more than once"),
        )
        for label, text, reason in cases:
            with self.subTest(label):
                kind, found = check_deployment.parse_delivery_kind(text)
                self.assertIsNone(kind)
                self.assertIn(reason, found)

    def test_a_second_branch_promotion_section_makes_the_kind_unusable(self) -> None:
        for first, second in (
            ("initial_delivery", "enhancement"),
            ("enhancement", "initial_delivery"),
            ("initial_delivery", "initial_delivery"),
        ):
            with self.subTest(f"{first} then {second}"):
                text = with_delivery_kind(
                    with_delivery_kind(GOOD_DEPLOYMENT, first), second
                )
                self.assertEqual(
                    (None, "Branch Promotion appears more than once"),
                    check_deployment.parse_delivery_kind(text),
                )
                self.assertIn(
                    "Branch Promotion: duplicate required level-2 section",
                    check_deployment.check_deployment_text(text),
                )

    def test_a_single_branch_promotion_section_is_not_a_duplicate(self) -> None:
        self.assertNotIn(
            "Branch Promotion: duplicate required level-2 section",
            check_deployment.check_deployment_text(
                with_delivery_kind(GOOD_DEPLOYMENT, "enhancement")
            ),
        )

    def test_an_unusable_kind_is_a_finding_only_where_the_literal_is_used(self) -> None:
        unusable = (
            ("missing", None),
            ("placeholder", "<initial_delivery | enhancement>"),
            ("unknown", "hotfix"),
        )
        for label, (record, place) in literal_variants().items():
            for kind_label, value in unusable:
                with self.subTest(f"{label}, {kind_label}"):
                    findings = "\n".join(
                        check_deployment.check_deployment_text(
                            with_delivery_kind(record, value)
                        )
                    )
                    self.assertIn("requires Delivery kind: initial_delivery", findings)
                    self.assertIn(place, findings)
        for kind_label, value in unusable:
            with self.subTest(f"no literal, {kind_label}"):
                self.assertEqual(
                    [],
                    check_deployment.check_deployment_text(
                        with_delivery_kind(GOOD_DEPLOYMENT, value)
                    ),
                )

    def test_a_usable_kind_leaves_only_the_architecture_finding_for_the_literal(
        self,
    ) -> None:
        record = literal_variants()["Record Preview URL pattern"][0]
        self.assertEqual(
            [
                "Branch Promotion: the initial-delivery literal in Record Preview "
                "URL pattern requires --architecture declaring Initial delivery: "
                "production-first/1"
            ],
            check_deployment.check_deployment_text(
                with_delivery_kind(record, "initial_delivery")
            ),
        )

    def test_the_literal_in_a_cell_that_does_not_take_it_is_not_a_place(self) -> None:
        # Production cells and unlisted Record lines never count as literal use.
        production = replace_once(
            GOOD_DEPLOYMENT,
            "- Production URL: https://example.com",
            f"- Production URL: {LITERAL}",
        )
        self.assertEqual(
            [],
            check_deployment._initial_delivery_literal_places(production),
        )
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                with_delivery_kind(production, "hotfix")
            ),
        )

INITIAL_DELIVERY_MARKER = "Initial delivery: production-first/1"


def marked(architecture: str) -> str:
    return replace_once(
        architecture,
        "Expected deployable surfaces: web-app",
        "Release source policy: main-preview/1\n"
        f"{INITIAL_DELIVERY_MARKER}\n\n"
        "Expected deployable surfaces: web-app",
    )


def production_only(architecture: str) -> str:
    head, remainder = architecture.split("### Release Target: web-dev\n", 1)
    return head + "### Release Target: web-prod\n" + remainder.split(
        "### Release Target: web-prod\n", 1
    )[1]


MARKED_ARCHITECTURE = marked(RELEASE_ARCHITECTURE)
PRODUCTION_FIRST_ARCHITECTURE = marked(production_only(RELEASE_ARCHITECTURE))


def initial_delivery_record(development_row: str = "literal") -> str:
    """ARCHITECTURE_BACKED_DEPLOYMENT as a first delivery with no development stage."""

    preview_lines = "\n".join(
        f"- {label}: {LITERAL}"
        for label in (
            "Preview mechanism",
            "Preview URL pattern",
            "Fixed Preview deployment URL / ID",
            "Preview candidate SHA and acceptance",
        )
    )
    text = ARCHITECTURE_BACKED_DEPLOYMENT
    for old, new in (
        ("- Preview URL pattern: <hash>.example.pages.dev", preview_lines),
        (
            "- Protected resources preview must never bind: prod-db",
            f"- Protected resources preview must never bind: {LITERAL}",
        ),
        (
            DEV_UNIT_ROW,
            DEV_UNIT_ROW.replace("example-web-dev", LITERAL).replace(
                "Cloudflare;development route", LITERAL
            ),
        ),
        ("| d1-prod-001 | d1-preview-001 |", f"| d1-prod-001 | {LITERAL} |"),
        ("| kv-prod-001 | kv-preview-001 |", f"| kv-prod-001 | {LITERAL} |"),
        ("Cloudflare preview Worker secret", LITERAL),
        ("Cloudflare preview Worker variable", LITERAL),
        ("https://abc.example.pages.dev/callback", LITERAL),
        (
            "| web-dev | web-app | development | Cloudflare;development route | "
            "pending | pending | pending | pending | pending | pending | pending |\n",
            "",
        ),
        (
            DEV_ENVIRONMENT_ROW,
            f"| development | {LITERAL} | | | | |"
            if development_row == "literal"
            else "",
        ),
    ):
        text = replace_once(text, old, new)
    return with_delivery_kind(text, "initial_delivery")


class ProductionFirstTests(unittest.TestCase):
    def setUp(self) -> None:
        # Until release_targets parses the marker itself, stand in for it, so
        # these tests run against the real parser once it supports the marker.
        fields = {
            field.name
            for field in dataclasses.fields(release_targets.ReleaseTargetContract)
        }
        if "initial_delivery_protocol" in fields:
            return
        real_parse = check_deployment.parse_release_targets

        def parse(architecture_text: str):
            contract, findings = real_parse(architecture_text)
            if INITIAL_DELIVERY_MARKER in architecture_text.splitlines():
                findings = [
                    item
                    for item in findings
                    if "is missing development release targets" not in item
                ]
                object.__setattr__(
                    contract, "initial_delivery_protocol", "production-first/1"
                )
            return contract, findings

        patcher = mock.patch.object(check_deployment, "parse_release_targets", parse)
        patcher.start()
        self.addCleanup(patcher.stop)

    def check(
        self, record: str, architecture: str = PRODUCTION_FIRST_ARCHITECTURE
    ) -> str:
        return "\n".join(
            check_deployment.check_deployment_text(
                record, architecture_text=architecture
            )
        )

    def test_a_full_initial_delivery_record_passes_with_zero_findings(self) -> None:
        for label in ("literal", "absent"):
            with self.subTest(f"development environment row: {label}"):
                self.assertEqual(
                    [],
                    check_deployment.check_deployment_text(
                        initial_delivery_record(label),
                        architecture_text=PRODUCTION_FIRST_ARCHITECTURE,
                    ),
                )

    def test_the_same_record_passes_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            architecture = root / "architecture.md"
            architecture.write_text(PRODUCTION_FIRST_ARCHITECTURE, encoding="utf-8")
            for kind, status in (("initial_delivery", 0), ("enhancement", 1)):
                with self.subTest(kind):
                    deployment = root / f"DEPLOYMENT-{kind}.md"
                    deployment.write_text(
                        initial_delivery_record().replace(
                            "- Delivery kind: initial_delivery",
                            f"- Delivery kind: {kind}",
                        ),
                        encoding="utf-8",
                    )
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        code = check_deployment.main(
                            [
                                "--deployment",
                                str(deployment),
                                "--architecture",
                                str(architecture),
                            ]
                        )
                    self.assertEqual(status, code, stdout.getvalue())

    def test_every_listed_cell_needs_an_architecture_for_the_literal(self) -> None:
        for label, (record, place) in literal_variants().items():
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        with_delivery_kind(record, "initial_delivery")
                    )
                )
                self.assertIn(
                    "requires --architecture declaring Initial delivery: "
                    "production-first/1",
                    findings,
                )
                self.assertIn(place, findings)

    def test_the_literal_stays_a_finding_for_surfaces_without_a_marked_architecture(
        self,
    ) -> None:
        literal_row = DEV_UNIT_ROW.replace("example-web-dev", LITERAL).replace(
            "Cloudflare;development route", LITERAL
        )
        record = with_delivery_kind(
            replace_once(
                GOOD_DEPLOYMENT,
                DEV_UNIT_ROW,
                literal_row
                + f"\n| api | api | example-api | {LITERAL} | Cloudflare;production route | {LITERAL} |",
            ),
            "initial_delivery",
        )
        findings = "\n".join(check_deployment.check_deployment_text(record))
        self.assertIn("requires --architecture declaring Initial delivery", findings)
        self.assertIn(
            "web-app development release name must be lowercase kebab case", findings
        )

    def test_a_record_without_an_architecture_never_gets_the_relaxation(self) -> None:
        for label in ("literal", "absent"):
            with self.subTest(f"development environment row: {label}"):
                findings = "\n".join(
                    check_deployment.check_deployment_text(initial_delivery_record(label))
                )
                self.assertIn(
                    "requires --architecture declaring Initial delivery: "
                    "production-first/1",
                    findings,
                )
        absent = "\n".join(
            check_deployment.check_deployment_text(initial_delivery_record("absent"))
        )
        self.assertIn("Environment Status: missing the development row", absent)

    def test_the_cli_rejects_the_literal_without_an_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            deployment = Path(temp) / "DEPLOYMENT.md"
            deployment.write_text(initial_delivery_record(), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = check_deployment.main(["--deployment", str(deployment)])
            self.assertEqual(1, code, stdout.getvalue())
            self.assertIn("requires --architecture declaring", stdout.getvalue())

    def test_other_n_a_forms_and_other_columns_keep_todays_findings(self) -> None:
        def unit_row(development: str, production: str = "example-web") -> str:
            return DEV_UNIT_ROW.replace("example-web-dev", development).replace(
                "| example-web |", f"| {production} |"
            )

        cases = (
            (
                "hyphen instead of an em dash",
                replace_once(
                    GOOD_DEPLOYMENT, DEV_UNIT_ROW, unit_row(LITERAL.replace("—", "-"))
                ),
                "development release name must be lowercase kebab case",
            ),
            (
                "bare n/a",
                replace_once(GOOD_DEPLOYMENT, DEV_UNIT_ROW, unit_row("n/a")),
                "web-app has no development release name",
            ),
            (
                "literal as a production name",
                replace_once(
                    GOOD_DEPLOYMENT, DEV_UNIT_ROW, unit_row(LITERAL, LITERAL)
                ),
                "production release name must be lowercase kebab case",
            ),
            (
                "placeholder beside the literal",
                replace_once(
                    GOOD_DEPLOYMENT,
                    "- Preview URL pattern: <hash>.example.pages.dev",
                    f"- Preview mechanism: {LITERAL}\n- Preview URL pattern: <pattern>",
                ),
                "unresolved placeholder '<pattern>'",
            ),
        )
        for label, record, expected in cases:
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        with_delivery_kind(record, "initial_delivery")
                    )
                )
                self.assertIn(expected, findings)

    def test_the_literal_requires_delivery_kind_initial_delivery(self) -> None:
        for label, (record, place) in literal_variants().items():
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        with_delivery_kind(record, "enhancement")
                    )
                )
                self.assertIn(
                    "requires Delivery kind: initial_delivery, not enhancement",
                    findings,
                )
                self.assertIn(place, findings)

    def test_conflicting_branch_promotion_sections_reject_the_literal(self) -> None:
        initial = initial_delivery_record()
        enhancement = initial.replace(
            "- Delivery kind: initial_delivery", "- Delivery kind: enhancement"
        )
        cases = (
            ("initial_delivery then enhancement", with_delivery_kind(initial, "enhancement")),
            ("enhancement then initial_delivery", with_delivery_kind(enhancement, "initial_delivery")),
        )
        for label, record in cases:
            with self.subTest(label):
                findings = self.check(record)
                self.assertIn(
                    "Branch Promotion: duplicate required level-2 section", findings
                )
                self.assertIn(
                    "requires Delivery kind: initial_delivery; "
                    "Branch Promotion appears more than once",
                    findings,
                )

    def test_the_literal_needs_an_architecture_that_declares_the_marker(self) -> None:
        record = initial_delivery_record()
        for label, architecture in (
            ("both targets, no marker", RELEASE_ARCHITECTURE),
            ("production only, no marker", production_only(RELEASE_ARCHITECTURE)),
        ):
            with self.subTest(label):
                self.assertIn(
                    "architecture does not declare Initial delivery: production-first/1",
                    self.check(record, architecture),
                )

    def test_an_initial_delivery_without_the_literal_is_unchanged_by_the_marker(
        self,
    ) -> None:
        ordinary = with_delivery_kind(
            ARCHITECTURE_BACKED_DEPLOYMENT, "initial_delivery"
        )
        for label, architecture in (
            ("unmarked architecture", RELEASE_ARCHITECTURE),
            ("marked architecture with a development target", MARKED_ARCHITECTURE),
        ):
            with self.subTest(label):
                self.assertEqual("", self.check(ordinary, architecture))

    def test_an_enhancement_needs_the_development_target(self) -> None:
        enhancement = with_delivery_kind(ARCHITECTURE_BACKED_DEPLOYMENT, "enhancement")
        self.assertIn(
            "enhancement requires the development release target for web-app; "
            "production-first covers only the initial delivery",
            self.check(enhancement),
        )
        for label, architecture in (
            ("marked, development target present", MARKED_ARCHITECTURE),
            ("unmarked", RELEASE_ARCHITECTURE),
        ):
            with self.subTest(label):
                self.assertEqual("", self.check(enhancement, architecture))

    def test_release_unit_names_must_hold_the_literal_without_a_development_target(
        self,
    ) -> None:
        ordinary = with_delivery_kind(
            ARCHITECTURE_BACKED_DEPLOYMENT, "initial_delivery"
        )
        findings = self.check(ordinary)
        self.assertIn("web-app development release name must be", findings)
        self.assertIn("web-app development provider / channel must be", findings)
        self.assertIn("declares no development target", findings)

    def test_a_present_development_target_is_validated_as_today(self) -> None:
        findings = self.check(initial_delivery_record(), MARKED_ARCHITECTURE)
        self.assertIn(
            "development release name must equal architecture 'example-web-dev'",
            findings,
        )
        self.assertIn("development provider/channel must equal architecture", findings)
        self.assertIn("architecture release targets are missing: web-dev", findings)

    def test_the_development_environment_row_is_optional_only_for_production_first(
        self,
    ) -> None:
        no_row = replace_once(GOOD_DEPLOYMENT, DEV_ENVIRONMENT_ROW + "\n", "")
        cases = (
            (
                "initial delivery without architecture or literal",
                with_delivery_kind(no_row, "initial_delivery"),
                None,
            ),
            (
                "initial delivery, unmarked architecture",
                initial_delivery_record("absent"),
                RELEASE_ARCHITECTURE,
            ),
            (
                "enhancement",
                initial_delivery_record("absent").replace(
                    "- Delivery kind: initial_delivery", "- Delivery kind: enhancement"
                ),
                PRODUCTION_FIRST_ARCHITECTURE,
            ),
        )
        for label, record, architecture in cases:
            with self.subTest(label):
                findings = "\n".join(
                    check_deployment.check_deployment_text(
                        record, architecture_text=architecture
                    )
                )
                self.assertIn(
                    "Environment Status: missing the development row", findings
                )

    def test_the_production_row_stays_required_and_the_literal_row_stays_empty(
        self,
    ) -> None:
        no_production = replace_once(
            initial_delivery_record(), "| production | | | | | |\n", ""
        )
        self.assertIn(
            "Environment Status: missing the production row", self.check(no_production)
        )
        filled = replace_once(
            initial_delivery_record(),
            f"| development | {LITERAL} | | | | |",
            f"| development | {LITERAL} | {'a' * 40} | | | |",
        )
        self.assertIn(
            "development row holding the initial-delivery literal must leave every other cell empty",
            self.check(filled),
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
