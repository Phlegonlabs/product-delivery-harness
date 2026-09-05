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

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| preview | https://abc.example.pages.dev | {"a" * 40} | {"a" * 40} | 2026-09-03 | PASS |
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

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| preview | | | | | |
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

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| preview | https://abc.example.pages.dev | {"b" * 40} | {"b" * 40} | 2026-09-03 | PASS |
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
        self.assertIn("missing the preview row", joined)
        self.assertIn("unresolved placeholder", joined)
        self.assertIn("must be a full lowercase SHA once checked", joined)
        self.assertIn("checked but has no status", joined)


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
