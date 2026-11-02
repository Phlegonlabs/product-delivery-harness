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


KERNEL_ROW = "| kernel | KRN | Shared kernel | Party, item, currency | none | 1 | approved |\n"
INVENTORY_ROW = "| inventory | INV | Inventory | Stock ledger, warehouses | kernel | 2 | approved |\n"


class ModuleMapTests(ProgramCase):
    def add_module(self, row: str) -> list[str]:
        self.edit("PRD.md", INVENTORY_ROW, INVENTORY_ROW + row)
        return self.run_checks()

    def test_planned_module_with_new_scope_passes(self) -> None:
        self.assertEqual([], self.add_module("| sales | SAL | Sales | Orders | kernel | 3 | planned |\n"))

    def test_repeated_module_id_and_scope_are_reported(self) -> None:
        problems = self.add_module("| kernel | KRX | Copy | Nothing | none | 3 | planned |\n")
        self.assertFinding("program: Module Map repeats module id 'kernel'", problems)
        self.setUp()
        problems = self.add_module("| sales | KRN | Sales | Orders | kernel | 3 | planned |\n")
        self.assertFinding("program: Module Map repeats scope 'KRN'", problems)

    def test_module_id_must_be_kebab_case(self) -> None:
        problems = self.add_module("| Sales_Ledger | SLG | Sales | Orders | kernel | 3 | planned |\n")
        self.assertFinding("module id 'Sales_Ledger' must be lowercase kebab-case", problems)

    def test_scope_must_be_two_to_five_uppercase_characters(self) -> None:
        for scope in ("sal", "S", "SALESX", "1AB"):
            with self.subTest(scope=scope):
                self.setUp()
                problems = self.add_module(f"| sales | {scope} | Sales | Orders | kernel | 3 | planned |\n")
                self.assertFinding(f"Module Map scope '{scope}' of 'sales' must be 2-5 uppercase", problems)

    def test_reserved_scopes_are_rejected(self) -> None:
        for scope in ("PRD", "ARCH", "UI", "UX", "TEST", "DS", "RA", "MR", "MS", "TRUST", "AI", "BR", "PRG", "E2E", "MIG"):
            with self.subTest(scope=scope):
                self.setUp()
                problems = self.add_module(f"| sales | {scope} | Sales | Orders | kernel | 3 | planned |\n")
                self.assertFinding(f"Module Map scope '{scope}' of 'sales' is reserved", problems)

    def test_unknown_dependency_is_reported(self) -> None:
        problems = self.add_module("| sales | SAL | Sales | Orders | billing | 3 | planned |\n")
        self.assertFinding("'sales' depends on unknown module 'billing'", problems)

    def test_order_must_follow_dependencies(self) -> None:
        self.edit("PRD.md", KERNEL_ROW, KERNEL_ROW.replace("| 1 |", "| 3 |"))
        self.assertFinding("Module Map Order puts 'inventory' before its dependency 'kernel'", self.run_checks())

    def test_order_must_be_a_unique_integer(self) -> None:
        self.edit("PRD.md", KERNEL_ROW, KERNEL_ROW.replace("| 1 |", "| first |"))
        self.assertFinding("Order of 'kernel' must be an integer", self.run_checks())
        self.setUp()
        self.edit("PRD.md", KERNEL_ROW, KERNEL_ROW.replace("| 1 |", "| 2 |"))
        self.assertFinding("Module Map repeats Order 2", self.run_checks())

    def test_dependency_cycle_is_reported(self) -> None:
        self.edit("PRD.md", KERNEL_ROW, KERNEL_ROW.replace("| none |", "| inventory |"))
        self.assertFinding("Module Map Depends on cycle: kernel -> inventory -> kernel", self.run_checks())

    def test_missing_module_map_heading_is_reported(self) -> None:
        self.edit("PRD.md", "## Module Map\n", "## Modules\n")
        self.assertFinding("program: missing required heading '## Module Map'", self.run_checks())

    def test_placeholder_cells_fail_only_when_filled_is_required(self) -> None:
        self.edit("PRD.md", "| Receipt | Goods booked into a warehouse | inventory | delivery |", "| Receipt | Goods booked into a warehouse | inventory | [avoid] |")
        self.assertEqual([], self.run_checks())
        self.assertFinding("program: Glossary row contains an empty value or placeholder", self.run_checks(require_filled=True))

    def test_table_with_the_wrong_header_is_reported(self) -> None:
        self.edit("PRD.md", "| Entity | Owner module |", "| Entity | Steward |")
        self.assertFinding("program: Shared Data must use the canonical table", self.run_checks())


class SharedContractTests(ProgramCase):
    def test_shared_data_owner_and_readers_must_exist_and_depend(self) -> None:
        anchor = "| Party | kernel | inventory | party_id | Owner writes; readers keep party_id |\n"
        cases = (
            ("| Stock | billing | inventory | sku | Owner writes |\n", "owner 'billing' is not in the Module Map"),
            ("| Stock | inventory | billing | sku | Owner writes |\n", "reader 'billing' is not in the Module Map"),
            ("| Stock | inventory | kernel | sku | Owner writes |\n", "reader 'kernel' must depend on owner 'inventory'"),
        )
        for row, expected in cases:
            with self.subTest(expected=expected):
                self.setUp()
                self.edit("PRD.md", anchor, anchor + row)
                self.assertFinding("program: Shared Data 'Stock' " + expected, self.run_checks())

    def test_glossary_terms_are_unique_with_a_known_owner(self) -> None:
        anchor = "| Item | A stocked product | kernel | product |\n"
        self.edit("PRD.md", anchor, anchor + "| item | Another meaning | kernel | none |\n")
        self.assertFinding("program: Glossary repeats term 'item'", self.run_checks())
        self.setUp()
        self.edit("PRD.md", anchor, anchor + "| Invoice | A bill | billing | none |\n")
        self.assertFinding("Glossary term 'Invoice' owning module 'billing' is not in the Module Map", self.run_checks())

    def test_roles_are_unique(self) -> None:
        anchor = "| kernel-admin | Maintains master data | Company |\n"
        self.edit("PRD.md", anchor, anchor + "| Kernel-Admin | Again | Company |\n")
        self.assertFinding("program: Roles repeats role 'Kernel-Admin'", self.run_checks())

    def test_separation_of_duties_pair_names_an_existing_test(self) -> None:
        pair = "| inventory:post-receipt | inventory:approve-adjustment | No role holds both | TEST-PRG-009 |"
        self.edit("PRD.md", pair, pair.replace("TEST-PRG-009", "see the controller"))
        self.assertFinding(
            "Segregation of Duties pair inventory:post-receipt / inventory:approve-adjustment names no TEST ID",
            self.run_checks(),
        )
        self.setUp()
        self.edit("PRD.md", pair, pair.replace("TEST-PRG-009", "TEST-PRG-099"))
        self.assertFinding("names unknown TEST-PRG-099", self.run_checks())


class CapacityTests(ProgramCase):
    def test_capacity_row_must_name_existing_nfrs(self) -> None:
        row = "| Peak concurrent users | 150 | Interviews, 400 named users | PRD-PRG-021 |"
        self.edit("PRD.md", row, row.replace("PRD-PRG-021", "see interviews"))
        self.assertFinding("Capacity driver 'Peak concurrent users' names no NFR ID", self.run_checks())
        self.setUp()
        self.edit("PRD.md", row, row.replace("PRD-PRG-021", "PRD-PRG-099"))
        self.assertFinding("Capacity driver 'Peak concurrent users' names unknown NFR PRD-PRG-099", self.run_checks())

    def test_every_performance_or_scalability_nfr_needs_a_capacity_row(self) -> None:
        row = "| Transactions per day | 120,000 | Last 12 months of legacy volume | PRD-PRG-022 |\n"
        self.edit("PRD.md", row, "")
        problems = self.run_checks()
        self.assertFinding("program: PRD-PRG-022 (Scalability) is not named by any Capacity Assumptions row", problems)
        self.assertFalse(any("PRD-PRG-021" in problem for problem in problems))


class FlowTests(ProgramCase):
    def test_register_system_must_be_in_the_architecture_integrations(self) -> None:
        self.edit("architecture.md", "| Carrier API | Ship stock |", "| Courier API | Ship stock |")
        self.assertFinding(
            "Integrations Register system 'Carrier API' is not in the architecture Integrations table",
            self.run_checks(),
        )

    def test_register_modules_must_exist(self) -> None:
        row = "| Warehouse manager | inventory | TEST-INV-004 |"
        self.edit("PRD.md", row, row.replace("inventory", "billing"))
        self.assertFinding("Integrations Register system 'Carrier API' module 'billing' is not in the Module Map", self.run_checks())
        self.setUp()
        self.edit("PRD.md", row, row.replace("inventory", "none"))
        self.assertFinding("Integrations Register system 'Carrier API' names no module", self.run_checks())

    def test_process_modules_must_exist_and_follow_map_order(self) -> None:
        row = "| goods-receipt | kernel, inventory | TEST-E2E-001 |"
        self.edit("PRD.md", row, row.replace("kernel, inventory", "inventory, kernel"))
        self.assertFinding("Business Process 'goods-receipt' must list its modules in Module Map order", self.run_checks())
        self.setUp()
        self.edit("PRD.md", row, row.replace("kernel, inventory", "kernel, billing"))
        self.assertFinding("Business Process 'goods-receipt' module 'billing' is not in the Module Map", self.run_checks())

    def test_process_needs_a_required_yes_e2e_test(self) -> None:
        row = "| goods-receipt | kernel, inventory | TEST-E2E-001 |"
        expected = "Business Process 'goods-receipt' needs a Required Yes TEST-E2E-* test"
        for replacement in ("TEST-PRG-004", "TEST-E2E-099"):
            with self.subTest(replacement=replacement):
                self.setUp()
                self.edit("PRD.md", row, row.replace("TEST-E2E-001", replacement))
                self.assertFinding(expected, self.run_checks())
        self.setUp()
        test_row = "| E2E | Yes | PRD-PRG-001 | Stock value equals expected/receipt.json |"
        self.edit("PRD.md", test_row, test_row.replace("| Yes |", "| No |"))
        self.assertFinding(expected, self.run_checks())

    def add_gl(self) -> None:
        self.edit("PRD.md", INVENTORY_ROW, INVENTORY_ROW + "| gl | GL | General ledger | Postings | kernel | 3 | planned |\n")

    def test_gl_module_needs_a_period_close_e2e_test(self) -> None:
        self.add_gl()
        self.assertFinding("a gl module requires a Required Yes TEST-E2E-* period-close test", self.run_checks())

    def test_period_close_test_satisfies_the_gl_rule(self) -> None:
        self.add_gl()
        self.edit("PRD.md", "## UI Design Handoff Status\n", fx.PERIOD_CLOSE_TEST_ROW + "## UI Design Handoff Status\n")
        self.assertEqual([], self.run_checks())

    def test_period_close_test_must_be_required(self) -> None:
        self.add_gl()
        row = fx.PERIOD_CLOSE_TEST_ROW.replace("| Yes |", "| No |")
        self.edit("PRD.md", "## UI Design Handoff Status\n", row + "## UI Design Handoff Status\n")
        self.assertFinding("a gl module requires", self.run_checks())

    def test_program_ids_use_program_scopes(self) -> None:
        self.edit("PRD.md", "| PRD-PRG-001 | Complete the fixture |", "| PRD-001 | Complete the fixture |")
        self.assertFinding("program: PRD-001 must use a program scope (PRG, E2E or MIG)", self.run_checks())
        self.setUp()
        self.edit("architecture.md", "| ARCH-PRG-001 |", "| ARCH-KRN-001 |")
        self.assertFinding("program: ARCH-KRN-001 must use a program scope", self.run_checks())


class MigrationTests(ProgramCase):
    LEGACY = "## Migration and Cutover\n### Legacy Sources\n| ARCH ID | Legacy source | Owner | Extract method | Volume | Target module |\n| --- | --- | --- | --- | --- | --- |\n| ARCH-MIG-001 | Old stock file | Warehouse manager | CSV export | 40k rows | inventory |\n"

    def use_legacy_section(self) -> None:
        self.edit(
            "architecture.md",
            "## Migration and Cutover\nnot_required — greenfield program with no legacy data to load.\n",
            self.LEGACY,
        )

    def test_missing_section_is_reported(self) -> None:
        self.edit("architecture.md", "## Migration and Cutover\n", "## Cutover Notes\n")
        self.assertFinding("architecture is missing required heading '## Migration and Cutover'", self.run_checks())

    def test_not_required_needs_a_concrete_reason(self) -> None:
        self.edit("architecture.md", "not_required — greenfield program with no legacy data to load.", "not_required — none")
        self.assertFinding("Migration and Cutover not_required needs a concrete reason", self.run_checks())

    def test_legacy_sources_need_all_four_migration_tests(self) -> None:
        self.use_legacy_section()
        problems = self.run_checks()
        for number in range(1, 5):
            self.assertFinding(f"Migration and Cutover requires TEST-MIG-00{number} as a Required Yes obligation", problems)

    def test_four_required_migration_tests_pass(self) -> None:
        self.use_legacy_section()
        self.edit("PRD.md", "## UI Design Handoff Status\n", fx.MIGRATION_TEST_ROWS + "## UI Design Handoff Status\n")
        self.assertEqual([], self.run_checks())

    def test_a_migration_test_that_is_not_required_fails(self) -> None:
        self.use_legacy_section()
        rows = fx.MIGRATION_TEST_ROWS.replace("| TEST-MIG-004 | Rollback rehearsal restores legacy | migration | Yes |", "| TEST-MIG-004 | Rollback rehearsal restores legacy | migration | No |")
        self.edit("PRD.md", "## UI Design Handoff Status\n", rows + "## UI Design Handoff Status\n")
        problems = self.run_checks()
        self.assertEqual(["program: Migration and Cutover requires TEST-MIG-004 as a Required Yes obligation"], problems)


KERNEL = "modules/kernel/PRD.md"
INVENTORY = "modules/inventory/PRD.md"
CLERK_ROW = "| warehouse-clerk | inventory:post-receipt | Own warehouse | Within BR-INV-001 |\n"
MANAGER_ROW = "| warehouse-manager | inventory:approve-adjustment | All warehouses | none |\n"
SECURITY_GATE = "Security Requirements Gate: required — executable fixture input can create unsafe writes, decided by Owner"
DATA_GATE = "Data and Trust Gate: not_required — no personal or regulated data, decided by Owner"


class ModuleScopeTests(ProgramCase):
    def test_ids_defined_in_a_module_must_use_its_scope(self) -> None:
        self.edit(KERNEL, "| PRD-KRN-001 | Complete the fixture |", "| PRD-001 | Complete the fixture |")
        self.assertFinding("KRN: PRD-001 does not use the module scope KRN", self.run_checks())

    def test_architecture_ids_must_use_the_module_scope(self) -> None:
        self.edit("modules/kernel/architecture.md", "| ARCH-KRN-001 |", "| ARCH-INV-001 |")
        self.assertFinding("KRN: ARCH-INV-001 does not use the module scope KRN", self.run_checks())

    def test_ui_and_ux_ids_must_use_the_module_scope(self) -> None:
        self.edit(
            KERNEL,
            "## Test Obligations\n",
            "## UI Surface Contract\n### UI-INV-001 — Home\n- Main purpose: Show fixture state.\n"
            "## Test Obligations\n",
        )
        self.assertFinding("KRN: UI-INV-001 does not use the module scope KRN", self.run_checks())
        self.setUp()
        self.edit(
            KERNEL,
            "not_required — the fixture exposes no shipped user interface.",
            "| ID | User / task | Requirement | Success and failure signal | Evidence status |\n"
            "| --- | --- | --- | --- | --- |\n| UX-001 | Owner | Review state | Pass or fail shown | draft |",
        )
        self.assertFinding("KRN: UX-001 does not use the module scope KRN", self.run_checks())


class BusinessRuleTests(ProgramCase):
    ROW = "| BR-KRN-001 | Fixture package submitted | Package lacks owner approval | Package is rejected | none | Delivery owner | TEST-KRN-004 |"

    def test_rule_with_a_required_test_that_names_it_passes(self) -> None:
        self.assertEqual([], self.run_checks())

    def test_rule_must_name_a_test(self) -> None:
        self.edit(KERNEL, self.ROW, self.ROW.replace("TEST-KRN-004", "see the review"))
        self.assertFinding("KRN: BR-KRN-001 names no TEST ID", self.run_checks())

    def test_rule_test_must_exist(self) -> None:
        self.edit(KERNEL, self.ROW, self.ROW.replace("TEST-KRN-004", "TEST-KRN-099"))
        self.assertFinding("KRN: BR-KRN-001 references unknown TEST-KRN-099", self.run_checks())

    def test_rule_test_must_be_required_yes(self) -> None:
        row = "| integration | Yes | PRD-KRN-001, BR-KRN-001 |"
        self.edit(KERNEL, row, row.replace("| Yes |", "| No |"))
        self.assertFinding("KRN: BR-KRN-001 test TEST-KRN-004 must be Required Yes", self.run_checks())

    def test_test_upstream_must_name_the_rule(self) -> None:
        self.edit(KERNEL, "PRD-KRN-001, BR-KRN-001 |", "PRD-KRN-001 |")
        self.assertFinding("KRN: TEST-KRN-004 upstream trace IDs must name BR-KRN-001", self.run_checks())

    def test_bullet_list_is_not_the_rule_table(self) -> None:
        self.edit(KERNEL, fx.BUSINESS_RULES.format(scope="KRN"), "## Business Rules\n- Reject unapproved packages.\n")
        self.assertFinding("KRN: Business Rules must use the canonical table", self.run_checks())

    def test_explicit_absence_is_allowed(self) -> None:
        self.edit(KERNEL, fx.BUSINESS_RULES.format(scope="KRN"), "## Business Rules\nnot_required — kernel owns no business rules.\n")
        self.assertEqual([], self.run_checks())


class RoleTests(ProgramCase):
    def test_document_state_roles_must_be_program_roles(self) -> None:
        self.edit(INVENTORY, "| Post | warehouse-clerk |", "| Post | stranger |")
        self.assertFinding("INV: Document States role 'stranger' is not in the program Roles table", self.run_checks())

    def test_every_document_table_is_checked(self) -> None:
        self.edit(
            INVENTORY,
            fx.DOCUMENT_STATES,
            fx.DOCUMENT_STATES
            + "Document: Stock transfer. Terminal states: Received.\n"
            + fx.DOCUMENT_STATES.split("\n", 2)[2].replace("warehouse-clerk", "courier"),
        )
        self.assertFinding("INV: Document States role 'courier' is not in the program Roles table", self.run_checks())

    def test_document_states_need_the_canonical_table(self) -> None:
        self.edit(INVENTORY, "| From | To | Action |", "| From | To | Step |")
        self.assertFinding("INV: Document States must use the canonical table", self.run_checks())

    def test_permission_matrix_roles_must_be_program_roles(self) -> None:
        self.edit(INVENTORY, CLERK_ROW, CLERK_ROW.replace("warehouse-clerk", "auditor"))
        self.assertFinding("INV: Permission Matrix role 'auditor' is not in the program Roles table", self.run_checks())

    def test_permission_matrix_actions_use_the_module_prefix(self) -> None:
        self.edit(INVENTORY, CLERK_ROW, CLERK_ROW.replace("inventory:post-receipt", "sales:post-receipt"))
        self.assertFinding("INV: Permission Matrix action 'sales:post-receipt' must start with 'inventory:'", self.run_checks())

    def test_role_holding_both_duties_in_one_module_is_reported(self) -> None:
        self.edit(INVENTORY, CLERK_ROW, CLERK_ROW + CLERK_ROW.replace("post-receipt", "approve-adjustment"))
        self.assertFinding(
            "INV: role 'warehouse-clerk' holds both inventory:post-receipt and inventory:approve-adjustment "
            "(segregation of duties)",
            self.run_checks(),
        )

    def test_role_holding_both_duties_across_modules_is_reported(self) -> None:
        pair = "| inventory:post-receipt | inventory:approve-adjustment |"
        self.edit("PRD.md", pair, "| kernel:maintain-party | inventory:approve-adjustment |")
        self.edit(INVENTORY, MANAGER_ROW, MANAGER_ROW + MANAGER_ROW.replace("warehouse-manager", "kernel-admin"))
        self.assertFinding(
            "INV: role 'kernel-admin' holds both kernel:maintain-party and inventory:approve-adjustment",
            self.run_checks(),
        )

    def test_roles_that_split_a_pair_pass(self) -> None:
        self.assertEqual([], self.run_checks())


class ReportsTests(ProgramCase):
    def test_reports_heading_is_required(self) -> None:
        self.edit(KERNEL, "## Reports\n", "## Report Notes\n")
        self.assertFinding("KRN: missing required heading '## Reports'", self.run_checks())

    def test_reports_need_the_canonical_header(self) -> None:
        self.edit(KERNEL, "| PRD ID | Report | Audience |", "| PRD ID | Report | Readers |")
        self.assertFinding("KRN: Reports must use the canonical table", self.run_checks())


class GateTests(ProgramCase):
    def test_module_gate_weaker_than_the_program_gate_fails(self) -> None:
        self.edit(KERNEL, SECURITY_GATE, SECURITY_GATE.replace("required —", "not_required —"))
        self.assertFinding("KRN: Security Requirements Gate is not_required but the program gate is required", self.run_checks())

    def test_module_gate_stronger_than_the_program_gate_passes(self) -> None:
        self.edit(KERNEL, DATA_GATE, DATA_GATE.replace("not_required —", "required —"))
        self.assertEqual([], self.run_checks())

    def test_blocked_module_gate_is_never_weaker(self) -> None:
        self.edit(KERNEL, SECURITY_GATE, SECURITY_GATE.replace("required —", "blocked —"))
        self.assertEqual([], self.run_checks())

    def test_blocked_program_gate_only_fails_a_weaker_module_when_approval_is_required(self) -> None:
        self.edit("PRD.md", DATA_GATE, DATA_GATE.replace("not_required —", "blocked —"))
        self.assertEqual([], self.run_checks())
        self.assertFinding(
            "KRN: Data and Trust Gate is not_required but the program gate is blocked",
            self.run_checks(require_approved=True),
        )


class CrossReferenceTests(ProgramCase):
    KERNEL_TEST = "| Yes | PRD-KRN-001 | Completion observed |"
    INVENTORY_TEST = "| Yes | PRD-INV-001, PRD-KRN-001 | Completion observed |"

    def test_reference_to_a_dependency_and_to_program_ids_resolves(self) -> None:
        self.edit(INVENTORY, self.INVENTORY_TEST, self.INVENTORY_TEST.replace("PRD-KRN-001", "PRD-KRN-001, PRD-PRG-001, TEST-E2E-001"))
        self.assertEqual([], self.run_checks())

    def test_reference_to_a_module_outside_depends_on_fails(self) -> None:
        self.edit(KERNEL, self.KERNEL_TEST, self.KERNEL_TEST.replace("PRD-KRN-001", "PRD-KRN-001, PRD-INV-001"))
        self.assertEqual(
            ["KRN: references PRD-INV-001 but 'inventory' is not in Depends on"], self.run_checks()
        )

    def test_reference_that_does_not_resolve_fails(self) -> None:
        for replacement, expected in (
            ("PRD-KRN-099", "INV: references unknown PRD-KRN-099"),
            ("TEST-E2E-099", "INV: references unknown TEST-E2E-099"),
        ):
            with self.subTest(replacement=replacement):
                self.setUp()
                self.edit(INVENTORY, self.INVENTORY_TEST, self.INVENTORY_TEST.replace("PRD-KRN-001", replacement))
                self.assertFinding(expected, self.run_checks())

    def test_reference_to_a_planned_module_has_no_ids_yet(self) -> None:
        self.edit(
            "PRD.md",
            INVENTORY_ROW,
            "| sales | SAL | Sales | Orders | kernel | 2 | planned |\n"
            "| inventory | INV | Inventory | Stock ledger, warehouses | kernel, sales | 3 | approved |\n",
        )
        self.edit(INVENTORY, self.INVENTORY_TEST, self.INVENTORY_TEST.replace("PRD-KRN-001", "PRD-SAL-001"))
        self.assertEqual(["INV: references unknown PRD-SAL-001"], self.run_checks())

    def test_text_that_only_looks_like_an_id_is_ignored(self) -> None:
        self.edit(INVENTORY, "## Test Obligations\n", "Latest delta: docs/product/deltas/PRD-DELTA-EPIC-001.md\n## Test Obligations\n")
        self.assertEqual([], self.run_checks())

    def test_architecture_references_are_checked_too(self) -> None:
        self.edit("modules/inventory/architecture.md", "| ARCH-INV-001 | Fixture service | Complete fixture requests | PRD-INV-001 |", "| ARCH-INV-001 | Fixture service | Complete fixture requests | PRD-INV-001, PRD-KRN-099 |")
        self.assertFinding("INV: references unknown PRD-KRN-099", self.run_checks())


class ProgramRevisionTests(ProgramCase):
    ZERO = "sha256:" + "0" * 64

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(
            fx.contract_utils.canonical_product_bytes(self.files["PRD.md"], "", "")
        ).hexdigest()

    def revision(self, name: str) -> str:
        return next(line for line in self.files[name].splitlines() if line.startswith("Program revision:"))

    def test_matching_revision_gives_no_warning(self) -> None:
        notes: list[str] = []
        self.assertEqual([], self.run_checks(notes=notes))
        self.assertEqual([], notes)
        self.assertEqual(f"Program revision: {self.digest()}", self.revision(KERNEL))

    def test_revision_line_is_required_and_must_be_a_sha256_digest(self) -> None:
        expected = "KRN: At a Glance must record 'Program revision: sha256:<64 hex digits>'"
        line = self.revision(KERNEL)
        for replacement in ("", "Program revision: sha256:abc", "Program revision: latest"):
            with self.subTest(replacement=replacement):
                self.setUp()
                self.edit(KERNEL, line + "\n", replacement + "\n" if replacement else "")
                self.assertFinding(expected, self.run_checks())

    def test_stale_revision_is_a_warning_not_a_failure(self) -> None:
        self.edit(KERNEL, self.revision(KERNEL), f"Program revision: {self.ZERO}")
        notes: list[str] = []
        self.assertEqual([], self.run_checks(notes=notes))
        self.assertEqual(
            [f"warning: stale_program_revision KRN: module records {self.ZERO}, program PRD is {self.digest()}"],
            notes,
        )

    def test_program_change_makes_every_recorded_revision_stale(self) -> None:
        self.edit("PRD.md", "- Reject incomplete authority before implementation starts.", "- Reject incomplete authority before implementation starts.\n- Keep modules aligned.")
        notes: list[str] = []
        self.assertEqual([], self.run_checks(notes=notes))
        self.assertEqual(["KRN", "INV"], [note.split()[2].rstrip(":") for note in notes])

    def test_approval_block_change_does_not_stale_modules(self) -> None:
        self.edit("PRD.md", "- Decision owner: Owner", "- Decision owner: Someone Else")
        notes: list[str] = []
        self.assertEqual([], self.run_checks(notes=notes))
        self.assertEqual([], notes)

    def test_notes_are_optional(self) -> None:
        self.edit(KERNEL, self.revision(KERNEL), f"Program revision: {self.ZERO}")
        self.assertEqual([], self.run_checks())


class ModuleFilterTests(ProgramCase):
    def break_both_modules(self) -> None:
        self.edit(KERNEL, "| PRD-KRN-001 | Complete the fixture |", "| PRD-001 | Complete the fixture |")
        self.edit(INVENTORY, "| PRD-INV-001 | Complete the fixture |", "| PRD-002 | Complete the fixture |")

    def test_module_filter_limits_the_module_pass(self) -> None:
        self.break_both_modules()
        problems = self.run_checks(module="inventory")
        self.assertFinding("INV: PRD-002 does not use the module scope INV", problems)
        self.assertFalse(any(problem.startswith("KRN:") for problem in problems))

    def test_without_a_filter_every_module_runs(self) -> None:
        self.break_both_modules()
        problems = self.run_checks()
        self.assertFinding("KRN: PRD-001 does not use", problems)
        self.assertFinding("INV: PRD-002 does not use", problems)

    def test_program_checks_run_even_with_a_module_filter(self) -> None:
        self.edit("PRD.md", INVENTORY_ROW, INVENTORY_ROW.replace("| 2 |", "| first |"))
        self.assertFinding("Order of 'inventory' must be an integer", self.run_checks(module="kernel"))

    def test_unknown_module_filter_is_reported(self) -> None:
        self.assertFinding("program: unknown module 'billing'", self.run_checks(module="billing"))


if __name__ == "__main__":
    unittest.main()
