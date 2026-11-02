"""`check_product_package.py main` on a `program` package: the CLI wiring."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(TESTS_DIR.parent))

import check_product_package  # noqa: E402
import program_fixtures as fx  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    finalize_approval_digests,
    strictize_approved_package,
)


class Result:
    def __init__(self, code: int, out: str, err: str) -> None:
        self.code = code
        self.out = out
        self.err = err


def approved(files: dict[str, str]) -> dict[str, str]:
    """Bind every approval block: the program to its stack, each module to itself alone."""

    bound = dict(files)
    bound["PRD.md"], bound["architecture.md"], bound["stack-decisions.md"] = strictize_approved_package(
        files["PRD.md"], files["architecture.md"], files["stack-decisions.md"]
    )
    for module_id, _scope in fx.MODULES:
        prd, architecture = f"modules/{module_id}/PRD.md", f"modules/{module_id}/architecture.md"
        bound[prd], bound[architecture], _ = finalize_approval_digests(files[prd], files[architecture], "")
    return bound


class ProgramCheckerWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.files = fx.program_files()

    def check(self, *flags: str, files: dict[str, str] | None = None) -> Result:
        with tempfile.TemporaryDirectory() as tmp:
            root = fx.write_program(Path(tmp), self.files if files is None else files)
            argv = [
                "--prd", str(root / "PRD.md"),
                "--architecture", str(root / "architecture.md"),
                "--stack-decisions", str(root / "stack-decisions.md"),
                *flags,
            ]
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = check_product_package.main(argv)
        return Result(code, out.getvalue(), err.getvalue())

    def failures(self, result: Result) -> list[str]:
        return [line.removeprefix("FAIL ") for line in result.err.splitlines() if line.startswith("FAIL ")]

    def test_fixture_program_passes_each_mode(self) -> None:
        for flags in ((), ("--require-filled",)):
            result = self.check(*flags)
            self.assertEqual((0, ""), (result.code, result.err), flags)
            self.assertIn("PASS program Product Definition package", result.out)

    def test_fixture_program_passes_complete_and_approved(self) -> None:
        bound = approved(self.files)
        for flags in (("--require-approved",), ("--require-filled", "--require-approved")):
            result = self.check(*flags, files=bound)
            self.assertEqual((0, ""), (result.code, result.err), flags)
        self.assertIn("PASS program Product Definition package is complete and owner-approved", result.out)

    def test_module_approval_covers_its_own_prd_and_architecture_only(self) -> None:
        bound = approved(self.files)
        # A stack edit reopens the program approval, not the module approvals.
        fx.edit(bound, "stack-decisions.md", "Fits deployment", "Fits the deployment")
        failures = self.failures(self.check("--require-approved", files=bound))
        self.assertTrue(any(f.startswith("prd approval: Package digest does not match") for f in failures))
        self.assertFalse(any(f.startswith(("kernel:", "inventory:")) for f in failures))

        bound["PRD.md"], bound["architecture.md"], bound["stack-decisions.md"] = strictize_approved_package(
            bound["PRD.md"], bound["architecture.md"], bound["stack-decisions.md"]
        )
        self.assertEqual(0, self.check("--require-approved", files=bound).code)

        # A module digest taken over the stack too is not the module's digest.
        prd, architecture = "modules/inventory/PRD.md", "modules/inventory/architecture.md"
        bound[prd], _, _ = finalize_approval_digests(self.files[prd], bound[architecture], bound["stack-decisions.md"])
        result = self.check("--require-approved", files=bound)
        self.assertIn("inventory: prd approval: Package digest does not match", "\n".join(self.failures(result)))

    def test_module_option_limits_the_module_pass(self) -> None:
        fx.edit(self.files, "modules/kernel/PRD.md", "A deterministic contract validation fixture", "Short")
        fx.edit(self.files, "modules/inventory/PRD.md", "A deterministic contract validation fixture", "Short")
        both = self.failures(self.check("--require-filled"))
        self.assertIn("kernel: prd: At a Glance row 'What it is' is not meaningful", both)
        self.assertIn("inventory: prd: At a Glance row 'What it is' is not meaningful", both)

        only = self.check("--module", "inventory", "--require-filled")
        self.assertEqual(1, only.code)
        self.assertEqual(
            ["inventory: prd: At a Glance row 'What it is' is not meaningful"], self.failures(only)
        )
        kernel = self.check("--module", "kernel", "--require-filled")
        self.assertEqual(
            ["kernel: prd: At a Glance row 'What it is' is not meaningful"], self.failures(kernel)
        )

    def test_unknown_module_fails_and_standard_prd_rejects_the_option(self) -> None:
        self.assertEqual(["program: unknown module 'sales'"], self.failures(self.check("--module", "sales")))

        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp)
            for name, text in (
                ("PRD.md", self.files["modules/kernel/PRD.md"]),
                ("architecture.md", self.files["modules/kernel/architecture.md"]),
                ("stack-decisions.md", self.files["stack-decisions.md"]),
            ):
                (module / name).write_text(text, encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = check_product_package.main([
                    "--prd", str(module / "PRD.md"),
                    "--architecture", str(module / "architecture.md"),
                    "--stack-decisions", str(module / "stack-decisions.md"),
                    "--module", "kernel",
                ])
        self.assertEqual(1, code)
        self.assertIn("FAIL package: --module applies only to a PRD whose Delivery profile is program", err.getvalue())

    def test_reference_to_a_dependency_resolves(self) -> None:
        self.assertIn("PRD-INV-001, PRD-KRN-001", self.files["modules/inventory/PRD.md"])
        self.assertEqual(0, self.check("--require-filled").code)

    def test_reference_to_a_module_not_in_depends_on_fails(self) -> None:
        fx.edit(
            self.files, "modules/kernel/PRD.md",
            "| Yes | PRD-KRN-001 | Completion observed |",
            "| Yes | PRD-KRN-001, PRD-INV-001 | Completion observed |",
        )
        result = self.check()
        self.assertEqual(1, result.code)
        self.assertIn("kernel: prd: references PRD-INV-001 from module not in Depends on", self.failures(result))
        self.assertNotIn("kernel: prd: TEST-KRN-001 references unknown upstream PRD-INV-001", self.failures(result))

    def test_reference_to_an_undefined_id_stays_unknown(self) -> None:
        fx.edit(
            self.files, "modules/inventory/PRD.md",
            "| Yes | PRD-INV-001, PRD-KRN-001 | Completion observed |",
            "| Yes | PRD-INV-001, PRD-KRN-099 | Completion observed |",
        )
        self.assertIn(
            "inventory: prd: TEST-INV-001 references unknown upstream PRD-KRN-099",
            self.failures(self.check()),
        )

    def test_program_test_may_cite_module_requirements(self) -> None:
        fx.edit(
            self.files, "PRD.md",
            "| TEST-E2E-001 | Goods receipt on fixture PF-BASE from party to stock | E2E | Yes | PRD-PRG-001 |",
            "| TEST-E2E-001 | Goods receipt on fixture PF-BASE from party to stock | E2E | Yes | PRD-PRG-001, PRD-INV-001 |",
        )
        self.assertEqual(0, self.check("--require-filled").code)

        fx.edit(self.files, "PRD.md", "PRD-PRG-001, PRD-INV-001 |", "PRD-PRG-001, PRD-INV-099 |")
        self.assertIn(
            "prd: TEST-E2E-001 references unknown upstream PRD-INV-099",
            self.failures(self.check("--require-filled")),
        )

    def test_stale_program_revision_is_a_note_not_a_failure(self) -> None:
        fx.edit(
            self.files, "PRD.md",
            "Do not contact external systems from this fixture.",
            "Do not contact external systems from this program fixture.",
        )
        result = self.check("--require-filled")
        self.assertEqual((0, ""), (result.code, result.err))
        notes = [line for line in result.out.splitlines() if line.startswith("INFO warning: stale_program_revision")]
        self.assertEqual(2, len(notes), result.out)
        self.assertIn("KRN:", notes[0])
        self.assertIn("INV:", notes[1])
        self.assertIn("PASS program Product Definition package", result.out)

    def test_program_without_a_modules_directory_fails_clearly(self) -> None:
        bare = {name: text for name, text in self.files.items() if not name.startswith("modules/")}
        result = self.check(files=bare)
        self.assertEqual(1, result.code)
        self.assertEqual(
            [
                "program: Module Map row 'kernel' has status 'approved' but no modules/kernel directory",
                "program: Module Map row 'inventory' has status 'approved' but no modules/inventory directory",
            ],
            [f for f in self.failures(result) if "directory" in f],
        )

    def test_program_only_checks_stay_on_for_the_program_and_are_skipped_for_a_module(self) -> None:
        gate = "### Research Gate\nResearch Gate: go — assessed 2026-09-12, decided by Owner\n"
        for name in ("modules/kernel/PRD.md", "modules/inventory/PRD.md"):
            fx.edit(self.files, name, gate, "")
        result = self.check("--require-filled")
        self.assertEqual((0, ""), (result.code, result.err), result.err)

        fx.edit(self.files, "PRD.md", gate, "")
        self.assertIn("prd: missing Research Gate decision", self.failures(self.check("--require-filled")))

    def test_delivery_profile_names_the_three_values(self) -> None:
        fx.edit(self.files, "PRD.md", "| Delivery profile | program |", "| Delivery profile | portfolio |")
        result = self.check("--require-filled")
        self.assertEqual(1, result.code)
        self.assertIn(
            "prd: At a Glance row 'Delivery profile' must be one of: mvp, standard, program",
            self.failures(result),
        )


if __name__ == "__main__":
    unittest.main()
