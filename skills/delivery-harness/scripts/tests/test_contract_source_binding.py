"""Harness 0.59 binds ui-design/3, design-system/4 and one frozen derived HTML package.

Older pins keep their contracts: 0.56-0.58 consume ui-design/2 only. Fixture
bytes are synthetic validator inputs, not product approvals.
"""
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import re
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_contract_join as join  # noqa: E402
import harness_design_contract as design_contract  # noqa: E402
from harness_schema import version_at_least  # noqa: E402

SKILLS = Path(__file__).resolve().parents[3]


@contextmanager
def _sibling_paths():
    """Expose sibling-suite fixtures only while they run.

    This module sorts before test_skill_contract; a lingering sibling test dir
    would make discovery import the wrong suite's module of that name.
    """
    saved = list(sys.path)
    try:
        for folder in ("delivery-harness/scripts/tests", "ui-design-builder/scripts/tests", "ui-design-builder/scripts",
                       "design-system-compiler/scripts/tests", "design-system-compiler/scripts",
                       "product-definition-builder/scripts/tests"):
            sys.path.insert(0, str(SKILLS / folder))
        yield
    finally:
        sys.path[:] = saved


def _fixtures():
    with _sibling_paths():
        # Import the sibling fixtures first: the strict-authority module's own
        # imports rewrite sys.path.
        import test_design_system_showcase as showcase_tests
        from test_ui_design_v3 import v3_publication
        import test_harness_strict_authority as legacy
        return legacy, showcase_tests, v3_publication


def _run_version(run, version):
    run["runtime_capabilities"]["runtime_adapter"]["version_gate"]["required_harness_version"] = version


def _mark_release_policy(root, protocol):
    architecture = root / "docs/product/architecture.md"
    text = architecture.read_text(encoding="utf-8")
    marker = f"## Release Targets\n\nRelease source policy: {protocol}\n"
    if f"Release source policy: {protocol}" not in text:
        text = text.replace("## Release Targets\n", marker, 1)
        text = re.sub(
            r"^- Source policy: stage=development; .*$",
            "- Source policy: stage=development; " + (
                "ref=run.integration.branch; sha=run.integration.integration_head_sha"
                if protocol == "main-preview/1" else
                "ref=refs/heads/development; sha=promotion.verified_development_sha"
            ),
            text,
            count=1,
            flags=re.MULTILINE,
        )
    architecture.write_text(text, encoding="utf-8")


def _marked_release_architecture(original, protocol, *arguments, **keyword_arguments):
    text = original(*arguments, **keyword_arguments)
    if f"Release source policy: {protocol}" not in text:
        text = text.replace(
            "## Release Targets\n",
            f"## Release Targets\n\nRelease source policy: {protocol}\n", 1)
        text = re.sub(
            r"^- Source policy: stage=development; .*$",
            "- Source policy: stage=development; " + (
                "ref=run.integration.branch; sha=run.integration.integration_head_sha"
                if protocol == "main-preview/1" else
                "ref=refs/heads/development; sha=promotion.verified_development_sha"
            ),
            text, count=1, flags=re.MULTILINE)
    return text


@contextmanager
def _marked_publications(protocol):
    """Build test publications with the selected version's release marker."""

    import test_ui_design_contract as ui_contract_tests
    import test_structure_publication as structure_tests
    import test_product_package_checker as product_tests
    original = ui_contract_tests.materialize_publication
    original_release = product_tests.release_architecture

    def marked_materialization(root, *arguments, **keyword_arguments):
        result = original(root, *arguments, **keyword_arguments)
        _mark_release_policy(root, protocol)
        return result

    import test_harness_strict_authority as harness_tests
    for owner in (harness_tests, product_tests):
        owner.release_architecture = lambda *arguments, **keyword_arguments: (
            _marked_release_architecture(original_release, protocol, *arguments, **keyword_arguments))
    for owner in (harness_tests, ui_contract_tests, structure_tests):
        owner.materialize_publication = marked_materialization
    try:
        yield
    finally:
        for owner in (harness_tests, ui_contract_tests, structure_tests):
            owner.materialize_publication = original
        for owner in (harness_tests, product_tests):
            owner.release_architecture = original_release


def _refresh_pair_for_marker(root, design):
    """Rebuild derived fixture bytes after adding the release marker."""

    markdown = design / "design-system.md"
    registry_path = design / "design-system.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    architecture = root / "docs/product/architecture.md"
    data["sourceBindings"]["architecture"]["sha256"] = hashlib.sha256(
        architecture.read_bytes()).hexdigest()
    registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with _sibling_paths():
        from check_design_system_pair import replace_generated_contract
        from render_design_system_preview import render_view
    markdown.write_text(replace_generated_contract("# Pair\n", data), encoding="utf-8")
    digests = {path: hashlib.sha256(path.read_bytes()).hexdigest()
               for path in (markdown, registry_path)}
    ui = design / "ui-design.md"
    ui.write_text(re.sub(
        r"^Compiled design system pair: .*$",
        "Compiled design system pair: docs/design/design-system.md "
        f"@ sha256:{digests[markdown]} and docs/design/design-system.json "
        f"@ sha256:{digests[registry_path]}",
        ui.read_text(encoding="utf-8"), flags=re.MULTILINE), encoding="utf-8")
    view = design / "design-system-preview.html"
    view.write_bytes(render_view(registry_path.read_bytes(), markdown.read_bytes(), root).encode("utf-8"))


def _start_release_base(root, protocol):
    """Create a real ordinary-flow base before any package bytes exist."""

    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=root, check=True, capture_output=True, timeout=30)
    branch = "main" if protocol == "main-preview/1" else "development"
    (root / ".fixture-base").write_text(f"observed {branch} base\n", encoding="utf-8")
    subprocess.run(["git", "add", ".fixture-base"], cwd=root, check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "commit", "-qm", "base"], cwd=root, check=True, capture_output=True, timeout=30)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True, timeout=30).stdout.strip()
    subprocess.run(["git", "update-ref", f"refs/remotes/origin/{branch}", base], cwd=root,
                   check=True, capture_output=True, timeout=30)
    return base


def _freeze_release_base(plan, run, root, base, protocol):
    """Commit the real candidate and bind its ancestry to the frozen base."""

    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "commit", "-qm", "fixture"], cwd=root, check=True, capture_output=True, timeout=30)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True, timeout=30).stdout.strip()
    plan["branch_policy"] = {
        "protocol": protocol,
        "kind": "ordinary",
        "base_ref": "refs/remotes/origin/main" if protocol == "main-preview/1" else "refs/remotes/origin/development",
        "base_sha": base,
    }
    run["integration"]["batch_base_sha"] = base
    run["integration"]["integration_head_sha"] = head


class VersionSelectionTests(unittest.TestCase):
    def test_each_pin_consumes_exactly_one_ui_contract(self):
        def errors(version, pin, retained=False, current=True):
            run = None if pin is None else {"runtime_capabilities": {"runtime_adapter": {
                "version_gate": {"required_harness_version": pin}}}}
            return "\n".join(join._ui_contract_version_errors(version, run=run, current=current, retained=retained))

        self.assertEqual("", errors("ui-design/3", "0.59.0"))
        self.assertEqual("", errors("ui-design/3", "0.59.1-rc.1"))
        self.assertIn("requires UI contract: ui-design/3", errors("ui-design/2", "0.59.0"))
        self.assertEqual("", errors("ui-design/2", "0.59.0", retained=True))
        self.assertIn("pinned pre-0.59 RUN cannot consume ui-design/3", errors("ui-design/3", "0.58.0"))
        self.assertEqual("", errors("ui-design/2", "0.58.0"))
        self.assertIn("Harness 0.56+ requires UI contract: ui-design/2", errors("legacy", "0.59.0"))
        self.assertIn("pinned legacy RUN cannot consume ui-design/3", errors("ui-design/3", "0.55.0", current=False))
        self.assertEqual("", errors("ui-design/3", None))
        self.assertEqual("", errors("ui-design/2", None))
        self.assertFalse(join.ui_design_v3_required({"runtime_capabilities": {"runtime_adapter": {
            "version_gate": {"required_harness_version": "0.59"}}}}))


class FrozenPackageJoinTests(unittest.TestCase):
    def ui2_fixture(self, root):
        """Build the current wireframe-free UI2 package and its frozen plan."""

        legacy, _, _ = _fixtures()
        plan, run, _ = legacy.StrictAuthorityJoinTests._ui_fixture(root, required=False)
        with _sibling_paths():
            from test_wireframe_free_publication import current_publication
        ui, prd, target = current_publication(root)
        paths = {
            "prd": prd,
            "architecture": root / "docs/product/architecture.md",
            "stack decisions": root / "docs/product/stack-decisions.md",
            "ui design": ui,
            "approved ui target": target,
        }
        plan["sources"] = [legacy.StrictAuthorityJoinTests._row("SRC-" + str(index), kind, path, root)
                           for index, (kind, path) in enumerate(paths.items())]
        for trace in plan["traces"]:
            trace["source_ids"] = ["SRC-0"]
        return plan, run

    def fixture(self, root, *, pin="0.59.0", preview=True):
        legacy, showcase_tests, _ = _fixtures()
        protocol = "main-preview/1" if version_at_least(pin, (0, 63, 0)) else "dual-branch/1"
        base = _start_release_base(root, protocol)
        # Rebuild the UI package as ui-design/3 with a real design-system/4 pair.
        with _marked_publications(protocol), _sibling_paths():
            plan, run, _ = legacy.StrictAuthorityJoinTests._ui_fixture(root, required=False)
            _, design, hifi = showcase_tests.PairIntegrationTests.build(None, root)
        _refresh_pair_for_marker(root, design)
        markdown, registry = design / "design-system.md", design / "design-system.json"
        ui = design / "ui-design.md"
        digest = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (markdown, registry)}
        ui.write_text(ui.read_text(encoding="utf-8").replace(
            "Compiled design system pair: pending — design-system-compiler",
            f"Compiled design system pair: docs/design/design-system.md @ sha256:{digest[markdown]} "
            f"and docs/design/design-system.json @ sha256:{digest[registry]}"), encoding="utf-8")
        view = design / "design-system-preview.html"
        _freeze_release_base(plan, run, root, base, protocol)
        paths = {"prd": root / "docs/product/PRD.md", "architecture": root / "docs/product/architecture.md",
                 "stack decisions": root / "docs/product/stack-decisions.md", "ui design": ui,
                 "approved ui target": hifi, "design system": markdown, "design system json": registry}
        if preview:
            paths["design system preview"] = view
        plan["sources"] = [legacy.StrictAuthorityJoinTests._row("SRC-" + str(index), kind, path, root)
                           for index, (kind, path) in enumerate(paths.items())]
        for trace in plan["traces"]:
            trace["source_ids"] = ["SRC-0"]
        _run_version(run, pin)
        return plan, run, view, legacy

    def test_current_and_legacy_packages_bind_their_own_release_policy(self):
        from manifest_fixtures import eval_exempt_product_fixture
        for pin, protocol, branch in (
            ("0.62.3", "dual-branch/1", "development"),
            ("0.63.0", "main-preview/1", "main"),
        ):
            with self.subTest(pin=pin), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with _sibling_paths(), eval_exempt_product_fixture():
                    plan, run, _, _ = self.fixture(root, pin=pin)
                self.assertEqual(protocol, plan["branch_policy"]["protocol"])
                self.assertEqual(f"refs/remotes/origin/{branch}", plan["branch_policy"]["base_ref"])
                self.assertEqual([], join.validate_frozen_contract_joins(plan, root, run=run))

    def test_new_full_ui_needs_ui_design_three_and_its_frozen_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, view, _ = self.fixture(root)
            findings = join.validate_frozen_contract_joins(plan, root, run=run)
            self.assertEqual([], findings)
            design_dir = root / "docs/design"
            markdown = design_dir / "design-system.md"
            data = json.loads((design_dir / "design-system.json").read_text(encoding="utf-8"))
            self.assertEqual([], design_contract.validate_design_system_registry(data))
            self.assertEqual([], design_contract.compare_design_system_pair(
                markdown.read_text(encoding="utf-8"), data, repo_root=root))
            view.write_bytes(view.read_bytes() + b"<!-- hand edit -->")
            plan["sources"][-1]["content_sha256"] = hashlib.sha256(view.read_bytes()).hexdigest()
            self.assertIn("frozen design-system-preview.html is stale or modified",
                          "\n".join(join.validate_frozen_contract_joins(plan, root, run=run)))

    def test_missing_html_and_older_pins_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, _, _ = self.fixture(root, preview=False)
            self.assertIn("requires exactly one frozen design-system-preview.html",
                          "\n".join(join.validate_frozen_contract_joins(plan, root, run=run)))
            _run_version(run, "0.58.0")
            self.assertIn("pinned pre-0.59 RUN cannot consume ui-design/3",
                          "\n".join(join.validate_frozen_contract_joins(plan, root, run=run)))

    def test_headless_plan_cannot_freeze_the_html_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, _, _ = self.fixture(root)
            plan["ui_surfaces"] = []
            self.assertIn("headless PLAN must not freeze design-system-preview source",
                          "\n".join(join.validate_frozen_contract_joins(plan, root, run=run)))

    def test_fresh_enhancement_label_cannot_retain_ui_design_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = self.ui2_fixture(root)
            legacy, _, _ = _fixtures()
            record = root / "docs/epics/EPIC-enhancement.md"
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("```\nDesign workflow: maintenance\n```\nDesign workflow: enhancement\n", encoding="utf-8")
            for arguments in (("init", "-q"), ("config", "core.autocrlf", "false"), ("add", "docs/epics/EPIC-enhancement.md"),
                              ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "record")):
                subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True, timeout=15)
            row = legacy.StrictAuthorityJoinTests._row("SRC-TASK", "task record", record, root)
            row["source_revision"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                                                    capture_output=True, text=True, timeout=15).stdout.strip()
            plan["sources"].append(row)
            _run_version(run, "0.59.0")
            findings = join.validate_frozen_contract_joins(plan, root, run=run)
            self.assertIn("Harness 0.59+ new full UI delivery requires UI contract: ui-design/3",
                          "\n".join(findings))

    def test_validated_maintenance_record_retains_ui_design_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = self.ui2_fixture(root)
            legacy, _, _ = _fixtures()
            record = root / "docs/epics/EPIC-maintenance.md"
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("""# Retained UI repair

Design workflow: maintenance
UI impact: none
Plan ID: PLAN-TEST
Plan objective: Deliver a deterministic test plan
Requirement refs: REQ-001
UI scope: UI-001
""", encoding="utf-8")
            for arguments in (("init", "-q"), ("config", "core.autocrlf", "false"),
                              ("add", "docs/epics/EPIC-maintenance.md"),
                              ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                               "commit", "-qm", "record")):
                subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True, timeout=15)
            row = legacy.StrictAuthorityJoinTests._row("SRC-TASK", "task record", record, root)
            row["source_revision"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                                                    capture_output=True, text=True, timeout=15).stdout.strip()
            plan["sources"].append(row)
            next(trace for trace in plan["traces"] if trace["id"] == "REQ-001")["source_ids"].append("SRC-TASK")
            self.assertEqual((True, []), join._frozen_maintenance_record(plan, root))
            _run_version(run, "0.59.0")
            findings = join.validate_frozen_contract_joins(plan, root, run=run)
            self.assertNotIn("Harness 0.59+ new full UI delivery requires UI contract: ui-design/3",
                             findings)
            self.assertIn(
                "architecture: Harness 0.59+ current joins require an active "
                "'Release source policy: dual-branch/1' marker",
                findings,
            )

    def test_ui_three_maintenance_retains_history_without_fresh_preview_approval(self):
        for impact in ("none", "style"):
            with self.subTest(impact=impact), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan, run, _, legacy = self.fixture(root, preview=False)
                record = root / "docs/epics/EPIC-maintenance.md"
                record.parent.mkdir(parents=True, exist_ok=True)
                record.write_text(
                    "# Retained UI repair\n\nDesign workflow: maintenance\n"
                    f"UI impact: {impact}\nPlan ID: PLAN-TEST\n"
                    "Plan objective: Deliver a deterministic test plan\n"
                    "Requirement refs: REQ-001\nUI scope: UI-001\n", encoding="utf-8")
                for arguments in (("add", "docs/epics/EPIC-maintenance.md"),
                                  ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                                   "commit", "-qm", "retain maintenance record")):
                    subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True, timeout=15)
                row = legacy.StrictAuthorityJoinTests._row("SRC-TASK", "task record", record, root)
                row["source_revision"] = subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=root, check=True,
                    capture_output=True, text=True, timeout=15).stdout.strip()
                plan["sources"].append(row)
                next(trace for trace in plan["traces"] if trace["id"] == "REQ-001")["source_ids"].append("SRC-TASK")
                self.assertEqual((True, []), join._frozen_maintenance_record(plan, root))
                self.assertEqual([], join.validate_frozen_contract_joins(plan, root, run=run))
                without_record = copy.deepcopy(plan)
                without_record["sources"] = [source for source in without_record["sources"] if source["id"] != "SRC-TASK"]
                self.assertIn("requires exactly one frozen design-system-preview.html",
                              "\n".join(join.validate_frozen_contract_joins(without_record, root, run=run)))
                frozen_pair = root / "docs/design/design-system.json"
                frozen_pair.write_bytes(frozen_pair.read_bytes() + b" ")
                self.assertTrue(join.validate_frozen_contract_joins(plan, root, run=run))

    def test_ordinary_visual_handoff_checks_the_derived_preview(self):
        from manifest_fixtures import eval_exempt_product_fixture
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _sibling_paths(), eval_exempt_product_fixture():
                _, _, preview, _ = self.fixture(root, pin="0.65.3")
                from visual_inputs import build_visual_inputs
            relative = preview.relative_to(root).as_posix()
            self.assertIn(relative, build_visual_inputs(root, "docs/design/ui-design.md", "implementation"))
            original = preview.read_bytes()
            for content in (original + b"<!-- edited -->", b"<h1>unrelated preview</h1>"):
                preview.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "preview.*stale|stale.*preview"):
                    build_visual_inputs(root, "docs/design/ui-design.md", "implementation")
                self.assertEqual(content, preview.read_bytes())
            preview.write_bytes(original)
            preview.rename(root / "retained-preview.html")
            with self.assertRaisesRegex(ValueError, "missing"):
                build_visual_inputs(root, "docs/design/ui-design.md", "implementation")

    def test_current_maintenance_visual_handoff_retains_the_frozen_package(self):
        from manifest_fixtures import eval_exempt_product_fixture
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _sibling_paths(), eval_exempt_product_fixture():
                plan, run, _, legacy = self.fixture(root, pin="0.65.3")
            with _sibling_paths():
                from visual_inputs import build_visual_inputs
            product_paths = [root / "docs/product" / name
                             for name in ("PRD.md", "architecture.md", "stack-decisions.md")]
            texts = [path.read_text(encoding="utf-8") for path in product_paths]
            texts[0] += "\n<!-- Accepted maintenance clarification. -->\n"
            for path, body in zip(product_paths, legacy.strictize_approved_package(*texts)):
                path.write_text(body, encoding="utf-8")
                next(row for row in plan["sources"] if row["location"] == path.relative_to(root).as_posix())[
                    "content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            record = root / "docs/epics/EPIC-maintenance.md"
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("Design workflow: maintenance\nUI impact: style\n"
                              f"Plan ID: {plan['plan_id']}\nPlan objective: {plan['objective']}\n"
                              "Requirement refs: REQ-001\nUI scope: UI-001\n", encoding="utf-8")
            for command in (("add", "docs/epics/EPIC-maintenance.md"),
                            ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                             "commit", "-qm", "freeze maintenance record")):
                subprocess.run(["git", *command], cwd=root, check=True, capture_output=True, timeout=15)
            row = legacy.StrictAuthorityJoinTests._row("SRC-TASK", "task record", record, root)
            row["source_revision"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                                    check=True, capture_output=True, text=True,
                                                    timeout=15).stdout.strip()
            plan["sources"].append(row)
            next(trace for trace in plan["traces"] if trace["id"] == "REQ-001")["source_ids"].append("SRC-TASK")
            self.assertEqual([], join.validate_frozen_contract_joins(plan, root, run=run))
            before = {path: path.read_bytes() for path in (root / "docs").rglob("*") if path.is_file()}
            packet = build_visual_inputs(root, "docs/design/ui-design.md", "implementation",
                                         task_record="docs/epics/EPIC-maintenance.md")
            for path in product_paths:
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), packet)
            self.assertNotIn("docs/design/design-system-preview.html", packet)
            self.assertEqual(before, {path: path.read_bytes() for path in (root / "docs").rglob("*") if path.is_file()})
            self.assertEqual([], join.validate_frozen_contract_joins(plan, root, run=run))

    def test_source_spec_names_the_canonical_html_path(self):
        spec = join._STRICT_SOURCE_SPECS["design-system-preview"]
        self.assertEqual(("design system preview", "docs/design/design-system-preview.html"),
                         (spec["kind"], spec["canonical"]))
        self.assertEqual({"ui-design/3": "design-system/4", "ui-design/2": "design-system/3"},
                         join.DESIGN_SYSTEM_SCHEMA_BY_UI)


if __name__ == "__main__":
    unittest.main()
