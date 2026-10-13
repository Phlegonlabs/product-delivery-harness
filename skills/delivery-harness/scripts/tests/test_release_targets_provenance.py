#!/usr/bin/env python3
"""Tests for shared release-source authority parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PRODUCT_SCRIPTS = (
    Path(__file__).resolve().parents[3]
    / "product-definition-builder"
    / "scripts"
)
if str(PRODUCT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_SCRIPTS))

from release_targets import parse_source_policy  # noqa: E402


class ParseSourcePolicyTests(unittest.TestCase):
    def test_candidate_and_dual_branch_select_expected_authorities(self) -> None:
        candidate = parse_source_policy(
            "stage=development; ref=run.integration.branch; "
            "sha=run.integration.integration_head_sha",
            expected_stage="development",
        )
        self.assertEqual("run.integration.branch", candidate[0].ref)
        self.assertEqual(
            "run.integration.integration_head_sha", candidate[0].sha
        )

        dual = parse_source_policy(
            "stage=development; ref=refs/heads/development; "
            "sha=promotion.verified_development_sha",
            expected_stage="development",
            source_policy_protocol="dual-branch/1",
        )
        self.assertEqual("refs/heads/development", dual[0].ref)
        self.assertEqual("promotion.verified_development_sha", dual[0].sha)

    def test_wrong_ref_sha_and_protocol_fail(self) -> None:
        wrong_ref = parse_source_policy(
            "stage=development; ref=refs/heads/development; "
            "sha=run.integration.integration_head_sha",
            expected_stage="development",
        )
        self.assertIsNone(wrong_ref[0])
        self.assertTrue(
            any("ref=run.integration.branch" in item for item in wrong_ref[1])
        )

        wrong_sha = parse_source_policy(
            "stage=production; ref=refs/heads/main; sha=other",
            expected_stage="production",
            source_policy_protocol="dual-branch/1",
        )
        self.assertIsNone(wrong_sha[0])
        self.assertTrue(
            any("sha=promotion.verified_main_sha" in item for item in wrong_sha[1])
        )

        bad_protocol = parse_source_policy(
            "stage=development; ref=refs/heads/development; sha=x",
            expected_stage="development",
            source_policy_protocol="candidate/2",
        )
        self.assertIsNone(bad_protocol[0])


if __name__ == "__main__":
    unittest.main()
