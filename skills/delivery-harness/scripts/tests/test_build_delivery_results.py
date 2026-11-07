#!/usr/bin/env python3
"""Tests for build_delivery_results.py."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for directory in (SCRIPTS_DIR, TESTS_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import check_delivery_acceptance as checker  # noqa: E402
from build_delivery_results import main as build_main  # noqa: E402
from render_delivery_acceptance import main as render_main  # noqa: E402
from test_render_delivery_acceptance import FEATURE, PRD, PROFILE  # noqa: E402


CANDIDATE = "a" * 40
FULL = "TEST-001/receive-the-full-quantity"
OVER = "TEST-002/over-receipt-is-refused"


def section(scenario: str, test_id: str, status: str, cleanup: str | None, *asserts: str) -> str:
    lines = [f"## {scenario} ({test_id}) — row status: {status}"]
    if cleanup:
        lines.append(f"fixture_cleanup: {cleanup}")
    for item in asserts:
        lines += [f"### {item}", "observed: the runner line below", "  ✓ fixture test"]
    return "\n".join(lines) + "\n\n"


class BuildDeliveryResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.prd = self.root / "PRD.md"
        self.prd.write_text(PRD, encoding="utf-8")
        features = self.root / "features"
        features.mkdir()
        (features / "product.feature").write_text(FEATURE, encoding="utf-8")
        self.profile = self.root / "acceptance-profile.json"
        self.contract = self.root / "verification" / "delivery-acceptance.json"
        self.out = self.root / "verification" / "delivery-results.json"
        self.evidence_dir = self.root / "verification" / "evidence"
        self.evidence_dir.mkdir(parents=True)
        self.render(PROFILE)

    def render(self, profile: dict) -> None:
        self.profile.write_text(json.dumps(profile), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = render_main(["--prd", str(self.prd), "--features", str(self.root / "features"),
                                "--profile", str(self.profile), "--out", str(self.contract)])
        self.assertEqual(0, code)

    def evidence(self, name: str, text: str) -> Path:
        path = self.evidence_dir / name
        path.write_text("# run on candidate H1\n\n" + text + "## raw log\n## not a section\n", encoding="utf-8")
        return path

    def build(self, *evidence: Path, **overrides: str) -> tuple[int, str]:
        options = {
            "--repo-root": str(self.root), "--prd": str(self.prd), "--contract": str(self.contract),
            "--contract-sha256": hashlib.sha256(self.contract.read_bytes()).hexdigest(),
            "--candidate-sha": CANDIDATE, "--out": str(self.out), **overrides,
        }
        argv = [item for pair in options.items() for item in pair]
        for path in evidence:
            argv += ["--evidence", str(path)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = build_main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue()

    def check(self) -> dict:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            checker.main([
                "--repo-root", str(self.root), "--prd", str(self.prd), "--contract", str(self.contract),
                "--contract-sha256", hashlib.sha256(self.contract.read_bytes()).hexdigest(),
                "--results", str(self.out), "--candidate-sha", CANDIDATE,
            ])
        return json.loads(output.getvalue())

    def rows(self) -> dict[str, dict]:
        return {row["scenario_id"]: row for row in json.loads(self.out.read_text(encoding="utf-8"))["results"]}

    def test_rows_built_from_passing_sections_pass_the_unchanged_checker(self) -> None:
        first = self.evidence("web.md", section(FULL, "TEST-001", "pass", "cleaned", "ASSERT-001 — pass", "ASSERT-002 — pass"))
        second = self.evidence("api.md", section(OVER, "TEST-002", "pass", "cleaned", "ASSERT-001 — pass", "ASSERT-002 — pass"))
        code, output = self.build(first, second)
        self.assertEqual(0, code, output)
        payload = self.check()
        self.assertEqual("PASS", payload["status"], payload["errors"])
        rows = self.rows()
        register = json.loads(self.contract.read_text(encoding="utf-8"))
        frozen = register["tests"][1]["scenarios"][0]
        self.assertEqual(frozen["execution"], rows[OVER]["execution"])
        self.assertEqual(("real", "staging"), (rows[OVER]["auth_mode"], rows[OVER]["environment"]))
        self.assertEqual("verification/evidence/api.md", rows[OVER]["evidence"]["path"])
        self.assertEqual(hashlib.sha256(second.read_bytes()).hexdigest(), rows[OVER]["evidence"]["sha256"])
        before = self.out.read_bytes()
        self.assertEqual(0, self.build(first, second)[0])
        self.assertEqual(before, self.out.read_bytes())

    def test_missing_values_stay_unvalidated_or_pending_and_missing_sections_are_left_out(self) -> None:
        evidence = self.evidence("web.md", section(FULL, "TEST-001", "unvalidated", None, "ASSERT-002 — pass"))
        code, output = self.build(evidence)
        self.assertEqual(0, code, output)
        self.assertIn(f"no evidence section, left out: {OVER} (TEST-002)", output)
        row = self.rows()[FULL]
        self.assertEqual({"ASSERT-001": "unvalidated", "ASSERT-002": "pass"}, row["assertion_results"])
        self.assertEqual("pending", row["fixture_cleanup"])
        self.assertEqual([FULL], list(self.rows()))
        self.assertIn(f"required TEST-002/{OVER} has no exact passing evidence", self.check()["errors"])

        self.render({**PROFILE, "fixtures": []})
        self.out.unlink()
        self.assertEqual(0, self.build(evidence)[0])
        self.assertEqual("not_required", self.rows()[FULL]["fixture_cleanup"])

    def test_findings_exit_1_and_write_nothing(self) -> None:
        good = section(FULL, "TEST-001", "pass", "cleaned", "ASSERT-001 — pass")
        cases = {
            "unknown scenario": section("TEST-001/ghost", "TEST-001", "pass", None),
            "wrong TEST ID": section(FULL, "TEST-002", "pass", None),
            "unknown assertion": section(FULL, "TEST-001", "pass", None, "ASSERT-009 — pass"),
            "bad row status": section(FULL, "TEST-001", "passed", None),
            "bad assertion status": section(FULL, "TEST-001", "pass", None, "ASSERT-001 — ok"),
            "bad cleanup": section(FULL, "TEST-001", "pass", "done"),
            "second section": good + good,
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                code, output = self.build(self.evidence("case.md", text))
                self.assertEqual(1, code, output)
                self.assertFalse(self.out.exists())
        code, output = self.build(self.evidence("one.md", good), self.evidence("two.md", good))
        self.assertEqual(1, code)
        self.assertIn("already has a section at verification/evidence/one.md:3", output)
        code, output = self.build(self.evidence("one.md", good), **{"--contract-sha256": "0" * 64})
        self.assertEqual((1, "contract bytes do not match --contract-sha256\n"), (code, output))
        self.assertFalse(self.out.exists())

    def test_bad_arguments_exit_2(self) -> None:
        good = self.evidence("web.md", section(FULL, "TEST-001", "pass", None))
        stray = self.root / "verification" / "stray.md"
        stray.write_text("x\n", encoding="utf-8")
        for evidence, overrides in (
            ([good], {"--candidate-sha": "abc"}),
            ([good], {"--contract-sha256": "ABC"}),
            ([stray], {}),
            ([self.evidence_dir / "missing.md"], {}),
            ([good, good], {}),
            ([good], {"--out": str(self.root.parent / "elsewhere.json")}),
        ):
            with self.subTest(evidence=evidence, overrides=overrides):
                code, _ = self.build(*evidence, **overrides)
                self.assertEqual(2, code)
                self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
