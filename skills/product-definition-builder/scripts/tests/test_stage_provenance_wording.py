#!/usr/bin/env python3
"""Bind the measurement-source seed's planned-status and pending-binding distinction."""

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
    def test_seed_rows_are_planned_with_pending_bindings_and_staged_check(self) -> None:
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn(
            "one row per PRD metric and each required `TEST-*` expected signal",
            text,
        )
        self.assertIn(
            "Status `planned`",
            text,
        )
        self.assertIn(
            "`@pending#pending` release bindings",
            text,
        )
        self.assertIn(
            'check_deployment.py" --deployment <staged DEPLOYMENT.md> --architecture <staged architecture.md>',
            text,
        )


if __name__ == "__main__":
    unittest.main()
