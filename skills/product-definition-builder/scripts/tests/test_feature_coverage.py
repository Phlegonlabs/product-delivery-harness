import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_feature_coverage as cfc  # noqa: E402
import feature_file as ff  # noqa: E402
import program_fixtures as fx  # noqa: E402

TEMPLATE = SCRIPTS.parent / "assets" / "templates" / "FEATURE.template.feature"

PRD = """# PRD: Fixture
## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Receive the full purchase order | E2E | Yes | PRD-001 | The order closes |
| TEST-002 | Refuse an over-receipt | Integration / security | Yes | PRD-001 | The receipt is refused |
| TEST-003 | Round prices half up | unit | Yes | PRD-002 | 2.345 rounds to 2.35 |
| TEST-004 | Keep the partner API shape | contract | No | PRD-002 | Schema matches |
| TEST-005 | Accept partner callbacks | performance, Contract | Yes | PRD-003 | p95 under 300 ms |
| TEST-006 | Keep non-integration copy | non-integration | Yes | PRD-003 | Copy matches |
"""


def feature(*test_ids: str, name: str = "Fixture") -> str:
    lines = [f"Feature: {name}"]
    for test_id in test_ids:
        lines += [f"  @{test_id}", f"  Scenario: Cover {test_id}", "    When the owner acts", "    Then the result shows"]
    return "\n".join(lines) + "\n"


class TemplateTests(unittest.TestCase):
    def test_template_parses_and_shows_every_convention(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        feature = ff.parse_feature_text(text, TEMPLATE.name)
        self.assertEqual(["@PRD-001"], feature.tags)
        self.assertTrue(feature.background)
        self.assertEqual(2, len(feature.scenarios))
        self.assertEqual({"TEST-001", "TEST-002"}, feature.test_ids())
        self.assertEqual([{"platform": "web", "auth": "mock"}, {}], [s.profile for s in feature.scenarios])
        comments = [line for line in text.splitlines() if line.lstrip().startswith("#")]
        self.assertLessEqual(len(comments), 6)
        for word in ("Given", "When", "Then", "@TEST", "<TEST-ID>/<slug"):
            self.assertIn(word, "\n".join(comments))


class PrdTemplateTests(unittest.TestCase):
    def test_test_obligations_tables_still_parse_with_the_scenario_pointer(self):
        templates = SCRIPTS.parent / "assets" / "templates"
        for name, rows, pointer in (
            ("MODULE_PRD", ["TEST-<SCOPE>-001", "TEST-<SCOPE>-002"], "`docs/product/features/<scope>.feature`"),
            ("PROGRAM_PRD", ["TEST-PRG-001", "TEST-PRG-002", "TEST-E2E-001", "TEST-E2E-002", "TEST-E2E-003"],
             "`docs/product/features/program.feature`"),
        ):
            text = (templates / f"{name}.template.md").read_text(encoding="utf-8")
            self.assertEqual(rows, list(cfc.obligation_rows(text)), name)
            section = text.split("## Test Obligations", 1)[1].split("\n## ", 1)[0]
            self.assertIn(f"Scenarios for these rows live in {pointer}", section)

    def test_delta_template_and_contract_list_changed_scenarios(self):
        delta = (SCRIPTS.parent / "assets" / "templates" / "PRD_DELTA.template.md").read_text(encoding="utf-8")
        contract = (SCRIPTS.parent / "references" / "output-contract.md").read_text(encoding="utf-8")
        contract = contract.split("## `docs/product/deltas/PRD-DELTA-<EPIC-ID>.md`", 1)[1]
        for text in (delta, contract):
            changed = text.index("## Changed Requirements")
            scenarios = text.index("## Changed Scenarios")
            self.assertLess(changed, scenarios)
            self.assertLess(scenarios, text.index("## Decisions"))
            self.assertIn("| Scenario ID | Change | TEST ID |", text[scenarios:])
            self.assertIn("new / revised / retired", text[scenarios:text.index("## Decisions")])


class CoverageTests(unittest.TestCase):
    def check(self, files: dict[str, str], prd: str = PRD) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in files.items():
                (root / name).write_text(text, encoding="utf-8")
            problems = cfc.feature_coverage_problems(prd, root)
        return [problem.replace(root.as_posix() + "/", "") for problem in problems]

    def test_every_required_row_is_covered(self):
        required = ("TEST-001", "TEST-002", "TEST-003", "TEST-005", "TEST-006")
        self.assertEqual([], self.check({"product.feature": feature(*required)}))
        # A Required: No obligation may have a scenario.
        self.assertEqual([], self.check({"product.feature": feature(*required, "TEST-004")}))

    def test_missing_scenario_names_the_row(self):
        self.assertEqual(
            [
                "TEST-003 is a required unit obligation with no scenario",
                "TEST-005 is a required performance, Contract obligation with no scenario",
                "TEST-006 is a required non-integration obligation with no scenario",
            ],
            self.check({"product.feature": feature("TEST-001", "TEST-002")}),
        )
        self.assertEqual(5, len(self.check({})))

    def test_scenario_tag_must_name_a_row(self):
        problems = self.check({"product.feature": feature("TEST-001", "TEST-002", "TEST-003", "TEST-005", "TEST-006", "TEST-009")})
        self.assertEqual(["product.feature:23: TEST-009 is not a Test Obligations row"], problems)

    def test_parse_error_is_the_finding(self):
        bad = "Feature: F\n@TEST-001\nScenario Outline: S\nWhen x\nThen y\n"
        problems = self.check({"product.feature": feature("TEST-002", "TEST-005"), "bad.feature": bad})
        self.assertIn("bad.feature:3: Scenario Outline is not supported", problems)

    def test_scenario_ids_are_unique_across_files(self):
        problems = self.check({
            "a.feature": feature("TEST-001", "TEST-002", "TEST-003"),
            "b.feature": feature("TEST-001", "TEST-005", "TEST-006"),
        })
        self.assertEqual(["b.feature:3: duplicate scenario id TEST-001/cover-test-001 (first at a.feature:3)"], problems)

    def test_file_names_are_lowercase_feature_files(self):
        problems = self.check({
            "Product.feature": feature("TEST-001", "TEST-002", "TEST-003", "TEST-005", "TEST-006"),
            "notes.md": "notes\n",
        })
        self.assertEqual(
            [
                "Product.feature: feature file names are lowercase and end in .feature",
                "notes.md: feature file names are lowercase and end in .feature",
            ],
            problems,
        )

    def test_missing_directory(self):
        missing = Path(tempfile.gettempdir()) / "pdh-no-such-features-dir"
        self.assertEqual([f"features directory not found: {missing}"], cfc.feature_coverage_problems(PRD, missing))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cfc.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd = root / "PRD.md"
            prd.write_text(PRD, encoding="utf-8")
            features = root / "features"
            features.mkdir()
            (features / "product.feature").write_text(feature("TEST-001", "TEST-002", "TEST-003", "TEST-005", "TEST-006"), encoding="utf-8")
            code, out, _ = self.run_cli("--prd", str(prd), "--features", str(features))
            self.assertEqual((0, "PASS"), (code, out[:4]))
            (features / "product.feature").write_text(feature("TEST-001"), encoding="utf-8")
            code, _, err = self.run_cli("--prd", str(prd), "--features", str(features))
            self.assertEqual(1, code)
            self.assertIn("FAIL TEST-002 is a required", err)
            self.assertEqual(2, self.run_cli("--prd", str(root / "missing.md"), "--features", str(features))[0])
            self.assertEqual(2, self.run_cli("--prd", str(prd), "--features", str(root / "missing"))[0])
            self.assertEqual(2, self.run_cli("--prd", str(prd))[0])
            (root / "empty.md").write_text("# PRD: Empty\n", encoding="utf-8")
            code, _, err = self.run_cli("--prd", str(root / "empty.md"), "--features", str(features))
            self.assertEqual(1, code)
            self.assertIn("no Test Obligations rows", err)

    def test_program_package_reads_module_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            product = fx.write_program(Path(directory), fx.program_files())
            features = product / "features"
            features.mkdir()
            (features / "program.feature").write_text(feature("TEST-PRG-001", "TEST-PRG-002", "TEST-PRG-003", "TEST-PRG-004", "TEST-PRG-005", "TEST-PRG-009", "TEST-E2E-001"), encoding="utf-8")
            (features / "krn.feature").write_text(feature("TEST-KRN-001", "TEST-KRN-002", "TEST-KRN-003", "TEST-KRN-004"), encoding="utf-8")
            argv = ("--prd", str(product / "PRD.md"), "--features", str(features))
            code, _, err = self.run_cli(*argv)
            self.assertEqual(1, code)
            self.assertIn("TEST-INV-001 is a required integration obligation with no scenario", err)
            (features / "inv.feature").write_text(feature("TEST-INV-001", "TEST-INV-002", "TEST-INV-003", "TEST-INV-004"), encoding="utf-8")
            self.assertEqual(0, self.run_cli(*argv)[0])


if __name__ == "__main__":
    unittest.main()
