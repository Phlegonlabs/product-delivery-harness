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

## Resource Isolation

| Binding class | Production resource | Preview resource |
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

## Resource Isolation

| Binding class | Production resource | Preview resource |
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


class DeploymentRecordTests(unittest.TestCase):
    def test_a_resolved_record_with_one_verified_row_passes(self) -> None:
        findings = check_deployment.check_deployment_text(GOOD_DEPLOYMENT)
        self.assertEqual([], findings)

    def test_a_ci_connected_record_passes_the_same_checks(self) -> None:
        findings = check_deployment.check_deployment_text(CI_CONNECTED_DEPLOYMENT)
        self.assertEqual([], findings)

    def test_a_shared_resource_id_fails_the_isolation_check(self) -> None:
        findings = check_deployment.check_deployment_text(SHARED_RESOURCE_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn(
            "must not share one resource between production and preview", joined
        )

    def test_placeholders_and_incoherent_rows_fail(self) -> None:
        findings = check_deployment.check_deployment_text(BAD_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn("missing the development row", joined)
        self.assertIn("unresolved placeholder", joined)
        self.assertIn("must be a full lowercase SHA once checked", joined)
        self.assertIn("checked but has no status", joined)

    def test_missing_handoff_sections_fail(self) -> None:
        findings = check_deployment.check_deployment_text(BAD_DEPLOYMENT)
        joined = "\n".join(findings)
        self.assertIn("Required Secrets and Variables: missing section", joined)
        self.assertIn("External Console Setup: missing section", joined)

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
            (root / "AGENTS.md").write_text(
                "# Rules\n\n| design_direction | UI | `design-taste-frontend` | "
                + "0" * 64 + " |\n",
                encoding="utf-8",
            )
            self.assertEqual([], configure_project_context.unresolved_placeholders(root))


if __name__ == "__main__":
    unittest.main()
