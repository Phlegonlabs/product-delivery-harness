#!/usr/bin/env python3
"""Bind the activation seed's readiness and coverage distinction."""

from __future__ import annotations

import unittest
from pathlib import Path


STAGE = (
    Path(__file__).resolve().parents[2]
    / "references"
    / "stages"
    / "product-definition.md"
)


class StageProvenanceWordingTests(unittest.TestCase):
    def test_readiness_is_target_complete_and_coverage_is_separate(self) -> None:
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn(
            "Target Readiness must cover every architecture release target",
            text,
        )
        self.assertIn(
            "Outcome Coverage is a signal subset",
            text,
        )


if __name__ == "__main__":
    unittest.main()
