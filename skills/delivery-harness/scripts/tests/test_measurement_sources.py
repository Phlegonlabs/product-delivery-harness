#!/usr/bin/env python3
"""check_deployment.py Measurement Sources table checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_deployment  # noqa: E402


SHA_A = "a" * 40

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
| development | https://abc.example.pages.dev | {SHA_A} | {SHA_A} | 2026-09-03T10:00:00Z | PASS |
| production | | | | | |
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
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| web-dev | web-app | development | Cloudflare;development route | pending | pending | pending | pending | pending | pending | pending |
| web-prod | web-app | production | Cloudflare;production route | https://example.com | {SHA_A} | {SHA_A} | deployment-1 | production route answered the API smoke check | 2026-09-03T12:00:00Z | PASS |
"""

MEASUREMENT_HEADER = (
    "| MS ID | Signals | Target | Environment | Retrieval | Source role | "
    "Release bindings | Owner | Status | Verified at | Evidence |"
)

VERIFIED_ROW = (
    "| MS-001 | weekly signups and activated accounts | web-prod | production | "
    "GA4 API weekly pull | ga4 | "
    f"web-prod@{SHA_A}#deployment-1 | operator | verified | "
    "2026-09-03T12:00:00Z | GA4 export retained in docs/metrics/signups.csv |"
)

PENDING_ROW = (
    "| MS-002 | search impressions | web-prod | production | "
    "Search Console API weekly pull | search_console | "
    "web-prod@pending#pending | operator | planned | pending | pending |"
)


def measurement_deployment(*rows: str, base: str = GOOD_DEPLOYMENT) -> str:
    table = "\n".join(
        (MEASUREMENT_HEADER, "| " + " | ".join(["---"] * 11) + " |", *rows)
    )
    return base + "\n\n## Measurement Sources\n\n" + table + "\n"


class MeasurementSourcesTests(unittest.TestCase):
    def test_an_absent_section_is_optional_without_the_flag(self) -> None:
        self.assertEqual([], check_deployment.check_deployment_text(GOOD_DEPLOYMENT))

    def test_an_absent_section_is_required_with_the_flag(self) -> None:
        findings = check_deployment.check_deployment_text(
            GOOD_DEPLOYMENT, require_measurement_sources=True
        )
        self.assertEqual(["Measurement Sources section is required"], findings)

    def test_a_bad_header_names_the_expected_columns(self) -> None:
        short_header = (
            "| MS ID | Signals | Target | Environment | Source role | "
            "Release bindings | Owner | Status | Verified at | Evidence |"
        )
        short_row = (
            f"| MS-001 | weekly signups | web-prod | production | ga4 | "
            f"web-prod@{SHA_A}#deployment-1 | operator | verified | "
            "2026-09-03T12:00:00Z | GA4 export retained in docs/metrics |"
        )
        deployment = GOOD_DEPLOYMENT + "\n\n## Measurement Sources\n\n" + "\n".join(
            (short_header, "| " + " | ".join(["---"] * 10) + " |", short_row)
        ) + "\n"
        findings = check_deployment.check_deployment_text(deployment)
        self.assertEqual(1, len(findings))
        self.assertIn("Measurement Sources: expected columns", findings[0])
        self.assertIn("retrieval", findings[0])

    def test_duplicate_ms_ids_fail(self) -> None:
        deployment = measurement_deployment(VERIFIED_ROW, VERIFIED_ROW)
        findings = check_deployment.check_deployment_text(deployment)
        self.assertEqual(
            ["Measurement Sources: duplicate measurement source 'MS-001'"],
            findings,
        )

    def test_an_invalid_source_role_fails(self) -> None:
        bad_row = VERIFIED_ROW.replace("| ga4 |", "| vibes |")
        findings = check_deployment.check_deployment_text(
            measurement_deployment(bad_row)
        )
        self.assertEqual(
            ["Measurement Sources: MS-001 has invalid source role 'vibes'"],
            findings,
        )

    def test_an_invalid_status_fails(self) -> None:
        bad_row = VERIFIED_ROW.replace(
            "| operator | verified |", "| operator | done |"
        )
        findings = check_deployment.check_deployment_text(
            measurement_deployment(bad_row)
        )
        self.assertEqual(
            ["Measurement Sources: MS-001 has invalid status 'done'"],
            findings,
        )

    def test_a_malformed_release_binding_fails(self) -> None:
        bad_row = VERIFIED_ROW.replace(
            f"web-prod@{SHA_A}#deployment-1", "web-prod@ABC123#deployment-1"
        )
        findings = check_deployment.check_deployment_text(
            measurement_deployment(bad_row)
        )
        self.assertEqual(
            [
                "Measurement Sources: MS-001 release binding "
                "'web-prod@ABC123#deployment-1' must be <target>@<sha>#<artifact>"
            ],
            findings,
        )

    def test_a_bound_target_must_exist_in_the_architecture(self) -> None:
        unknown_row = PENDING_ROW.replace(
            "web-prod@pending#pending", "missing-target@pending#pending"
        )
        deployment = measurement_deployment(
            VERIFIED_ROW,
            unknown_row,
            base=ARCHITECTURE_BACKED_DEPLOYMENT,
        )
        findings = check_deployment.check_deployment_text(
            deployment, architecture_text=RELEASE_ARCHITECTURE
        )
        self.assertEqual(
            [
                "Measurement Sources: MS-002 release binding target "
                "'missing-target' is not an architecture release target"
            ],
            findings,
        )

    def test_architecture_backed_rows_bound_to_real_targets_pass(self) -> None:
        deployment = measurement_deployment(
            VERIFIED_ROW, PENDING_ROW, base=ARCHITECTURE_BACKED_DEPLOYMENT
        )
        findings = check_deployment.check_deployment_text(
            deployment, architecture_text=RELEASE_ARCHITECTURE
        )
        self.assertEqual([], findings)

    def test_a_verified_row_needs_sha_artifact_timestamp_and_evidence(self) -> None:
        bad_row = (
            "| MS-001 | weekly signups | web-prod | production | GA4 API weekly pull "
            "| ga4 | web-prod@pending#pending | operator | verified | pending | pending |"
        )
        findings = check_deployment.check_deployment_text(
            measurement_deployment(bad_row)
        )
        joined = "\n".join(findings)
        self.assertIn(
            "Measurement Sources: verified MS-001 release binding web-prod@pending "
            "needs a full lowercase SHA",
            joined,
        )
        self.assertIn(
            "Measurement Sources: verified MS-001 release binding needs an exact artifact",
            joined,
        )
        self.assertIn(
            "Measurement Sources: verified MS-001 verified-at must be RFC3339 "
            "with a real timezone",
            joined,
        )
        self.assertIn("Measurement Sources: verified MS-001 needs evidence", joined)

    def test_a_verified_row_rejects_absent_evidence_sentinels(self) -> None:
        for sentinel in ("n/a", "none", "N/A"):
            with self.subTest(sentinel=sentinel):
                bad_row = VERIFIED_ROW.replace(
                    "GA4 export retained in docs/metrics/signups.csv", sentinel
                )
                findings = check_deployment.check_deployment_text(
                    measurement_deployment(bad_row)
                )
                self.assertEqual(
                    ["Measurement Sources: verified MS-001 needs evidence"], findings
                )

    def test_a_verified_row_passes(self) -> None:
        findings = check_deployment.check_deployment_text(
            measurement_deployment(VERIFIED_ROW)
        )
        self.assertEqual([], findings)

    def test_a_non_verified_pending_row_passes(self) -> None:
        findings = check_deployment.check_deployment_text(
            measurement_deployment(PENDING_ROW)
        )
        self.assertEqual([], findings)

    def test_the_cli_flag_requires_the_section(self) -> None:
        findings = check_deployment.check_deployment_text(
            GOOD_DEPLOYMENT,
            architecture_text=RELEASE_ARCHITECTURE,
            require_measurement_sources=True,
        )
        self.assertIn("Measurement Sources section is required", findings)

    def test_parse_measurement_sources_returns_rows_and_absent_is_empty(self) -> None:
        self.assertEqual([], check_deployment.parse_measurement_sources(GOOD_DEPLOYMENT))
        parsed = check_deployment.parse_measurement_sources(
            measurement_deployment(VERIFIED_ROW, PENDING_ROW)
        )
        self.assertEqual(
            [
                {
                    "ms id": "MS-001",
                    "signals": "weekly signups and activated accounts",
                    "target": "web-prod",
                    "environment": "production",
                    "retrieval": "GA4 API weekly pull",
                    "source role": "ga4",
                    "release bindings": f"web-prod@{SHA_A}#deployment-1",
                    "owner": "operator",
                    "status": "verified",
                    "verified at": "2026-09-03T12:00:00Z",
                    "evidence": "GA4 export retained in docs/metrics/signups.csv",
                },
                {
                    "ms id": "MS-002",
                    "signals": "search impressions",
                    "target": "web-prod",
                    "environment": "production",
                    "retrieval": "Search Console API weekly pull",
                    "source role": "search_console",
                    "release bindings": "web-prod@pending#pending",
                    "owner": "operator",
                    "status": "planned",
                    "verified at": "pending",
                    "evidence": "pending",
                },
            ],
            parsed,
        )
        bad_header = GOOD_DEPLOYMENT + "\n\n## Measurement Sources\n\n" + "\n".join(
            (
                "| MS ID | Signals |",
                "| --- | --- |",
                "| MS-001 | weekly signups |",
            )
        ) + "\n"
        self.assertEqual([], check_deployment.parse_measurement_sources(bad_header))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
