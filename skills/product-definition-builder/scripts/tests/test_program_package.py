import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(TESTS_DIR.parent))

import program_fixtures as fx  # noqa: E402
import program_package  # noqa: E402


class ProgramCase(unittest.TestCase):
    def setUp(self) -> None:
        self.files = fx.program_files()
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def write(self) -> Path:
        return fx.write_program(Path(self._dir.name), self.files)

    def edit(self, name: str, old: str, new: str) -> None:
        fx.edit(self.files, name, old, new)

    def run_checks(self, **options) -> list[str]:
        return program_package.validate_program(self.write(), **options)

    def assertFinding(self, expected: str, problems: list[str]) -> None:
        self.assertTrue(
            any(expected in problem for problem in problems),
            f"{expected!r} not found in {problems}",
        )


class DiscoveryTests(ProgramCase):
    def test_baseline_program_has_no_findings(self) -> None:
        self.assertEqual([], self.run_checks(require_filled=True))

    def test_discovers_map_rows_with_directories(self) -> None:
        root = self.write()
        modules = program_package.discover_modules(root)
        self.assertEqual(["kernel", "inventory"], [m.module_id for m in modules])
        kernel, inventory = modules
        self.assertEqual(("KRN", (), 1, "approved"), (kernel.scope, kernel.depends_on, kernel.order, kernel.status))
        self.assertEqual(("INV", ("kernel",), 2), (inventory.scope, inventory.depends_on, inventory.order))
        self.assertEqual(root / "modules" / "inventory", inventory.directory)
        self.assertTrue(kernel.mapped and inventory.mapped)

    def test_directory_without_map_row_is_unmapped_and_reported(self) -> None:
        self.files["modules/billing/PRD.md"] = "# PRD: Fixture\n"
        root = self.write()
        extra = [m for m in program_package.discover_modules(root) if m.module_id == "billing"]
        self.assertEqual([False], [m.mapped for m in extra])
        self.assertFinding("program: modules/billing has no Module Map row", program_package.validate_program(root))

    def test_non_planned_row_without_directory_is_reported(self) -> None:
        self.edit(
            "PRD.md",
            "| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |\n",
            "| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |\n"
            "| sales | SAL | Sales | Orders | kernel, inventory | 3 | approved |\n",
        )
        self.assertFinding(
            "program: Module Map row 'sales' has status 'approved' but no modules/sales directory",
            self.run_checks(),
        )

    def test_planned_row_without_directory_is_allowed(self) -> None:
        self.edit(
            "PRD.md",
            "| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |\n",
            "| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |\n"
            "| sales | SAL | Sales | Orders | kernel, inventory | 3 | planned |\n",
        )
        self.assertEqual([], self.run_checks())

    def test_unreadable_module_file_is_reported_with_its_scope(self) -> None:
        del self.files["modules/inventory/architecture.md"]
        self.assertFinding("INV: cannot read UTF-8 file", self.run_checks())


class RegistryAndContextTests(ProgramCase):
    def test_registry_lists_defined_ids_by_scope(self) -> None:
        registry = program_package.load_program(self.write()).registry
        self.assertEqual(
            frozenset({"PRD-KRN-001", "PRD-KRN-002", "PRD-KRN-003"}), registry["KRN"]["PRD"]
        )
        self.assertEqual(frozenset({"BR-INV-001"}), registry["INV"]["BR"])
        self.assertEqual(frozenset({"ARCH-INV-001", "ARCH-INV-002"}), registry["INV"]["ARCH"])
        self.assertEqual(frozenset({"TEST-E2E-001"}), registry["E2E"]["TEST"])
        self.assertIn("TEST-PRG-009", registry["PRG"]["TEST"])
        self.assertNotIn("UX", registry["KRN"])

    def test_misscoped_id_is_not_registered_for_the_module(self) -> None:
        self.edit("modules/kernel/PRD.md", "| PRD-KRN-001 | Complete the fixture |", "| PRD-INV-009 | Complete the fixture |")
        registry = program_package.load_program(self.write()).registry
        self.assertNotIn("PRD-INV-009", registry["INV"]["PRD"])
        self.assertNotIn("PRD-INV-009", registry["KRN"]["PRD"])

    def test_ui_headings_are_registered(self) -> None:
        self.edit(
            "modules/kernel/PRD.md",
            "## Test Obligations\n",
            "## UI Surface Contract\n### UI-KRN-001 — Home\n- Main purpose: Show fixture state.\n## Test Obligations\n",
        )
        registry = program_package.load_program(self.write()).registry
        self.assertEqual(frozenset({"UI-KRN-001"}), registry["KRN"]["UI"])

    def test_module_context_carries_scope_dependencies_and_program_text(self) -> None:
        program = program_package.load_program(self.write())
        context = program_package.module_context(program, "inventory")
        self.assertEqual(("inventory", "INV"), (context.module_id, context.scope))
        self.assertEqual(frozenset({"KRN"}), context.depends_on)
        self.assertEqual(self.files["PRD.md"], context.program_prd)
        self.assertEqual(self.files["architecture.md"], context.program_architecture)
        self.assertEqual(program.digest, context.program_digest)
        self.assertEqual(frozenset(), program_package.module_context(program, "kernel").depends_on)

    def test_other_ids_excludes_the_modules_own_scope(self) -> None:
        context = program_package.module_context(program_package.load_program(self.write()), "inventory")
        others = context.other_ids("PRD")
        self.assertIn("PRD-KRN-001", others)
        self.assertIn("PRD-PRG-021", others)
        self.assertNotIn("PRD-INV-001", others)
        self.assertEqual(frozenset({"BR-KRN-001"}), context.other_ids("BR"))

    def test_module_context_does_no_io(self) -> None:
        program = program_package.load_program(self.write())
        self._dir.cleanup()
        self.assertEqual("KRN", program_package.module_context(program, "kernel").scope)

    def test_module_context_rejects_unknown_module(self) -> None:
        program = program_package.load_program(self.write())
        with self.assertRaises(ValueError):
            program_package.module_context(program, "billing")

    def test_program_digest_is_sha256_of_canonical_prd_bytes(self) -> None:
        prd = "# PRD: X\n"
        expected = hashlib.sha256(
            b'{"architecture":"","prd":"# PRD: X","stack":""}'
        ).hexdigest()
        self.assertEqual("sha256:" + expected, program_package.program_prd_digest(prd))

    def test_program_digest_ignores_the_approval_block(self) -> None:
        block = (
            "<!-- product-definition-approval:start -->\n- Decision: approved\n"
            "<!-- product-definition-approval:end -->\n"
        )
        self.assertEqual(
            program_package.program_prd_digest("# PRD: X\n"),
            program_package.program_prd_digest("# PRD: X\n\n" + block),
        )


if __name__ == "__main__":
    unittest.main()
