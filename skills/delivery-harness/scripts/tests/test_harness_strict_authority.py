"""Durable regression coverage for the Harness 0.38 authority join."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
UI_TESTS_DIR = Path(__file__).resolve().parents[3] / "ui-design-builder" / "scripts" / "tests"
PDB_TESTS_DIR = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
DS_TESTS_DIR = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts" / "tests"
DS_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts"
for candidate in (TESTS_DIR, SCRIPTS_DIR, UI_TESTS_DIR, PDB_TESTS_DIR, DS_TESTS_DIR, DS_SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from harness_contract_join import _strict_ui_surface_errors, validate_frozen_contract_joins  # noqa: E402
from harness_manifest import validate_current_plan_run  # noqa: E402
from manifest_fixtures import valid_plan, valid_run  # noqa: E402
from check_design_system_pair import replace_generated_contract  # noqa: E402
from test_product_package_checker import release_architecture, valid_prd, valid_stack  # noqa: E402
from test_ui_design_contract import materialize_publication  # noqa: E402

# Cross-skill fixture modules add their own test directories to ``sys.path``.
# Remove those paths after importing the named helpers so unittest discovery
# cannot later resolve another skill's same-named ``test_skill_contract``.
for candidate in (UI_TESTS_DIR, PDB_TESTS_DIR, DS_TESTS_DIR):
    while str(candidate) in sys.path:
        sys.path.remove(str(candidate))


class StrictAuthorityJoinTests(unittest.TestCase):
    @staticmethod
    def _row(source_id: str, kind: str, path: Path, root: Path) -> dict[str, object]:
        return {
            "id": source_id,
            "kind": kind,
            "location": path.relative_to(root).as_posix(),
            "owner": "owner",
            "status": "frozen",
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_revision": None,
            "staged_revision": None,
            "notes": "strict authority fixture",
        }

    @classmethod
    def _run(cls, plan: dict[str, object]) -> dict[str, object]:
        run = valid_run(plan)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "0.38.0"
        return run

    @classmethod
    def _headless_fixture(cls, root: Path) -> tuple[dict[str, object], dict[str, object]]:
        files = {
            "docs/product/PRD.md": valid_prd(),
            "docs/product/architecture.md": release_architecture(),
            "docs/product/stack-decisions.md": valid_stack(),
        }
        for relative, text in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        plan = valid_plan()
        plan["sources"] = [
            cls._row("SRC-PRD", "prd", root / "docs/product/PRD.md", root),
            cls._row(
                "SRC-ARCH", "architecture", root / "docs/product/architecture.md", root
            ),
            cls._row(
                "SRC-STACK",
                "stack decisions",
                root / "docs/product/stack-decisions.md",
                root,
            ),
        ]
        for trace in plan["traces"]:
            trace["source_ids"] = ["SRC-PRD"]
        plan["ui_surfaces"] = []
        return plan, cls._run(plan)

    @classmethod
    def _ui_fixture(
        cls, root: Path, *, required: bool
    ) -> tuple[dict[str, object], dict[str, object], dict[str, Path]]:
        original_path = list(sys.path)
        try:
            for candidate in (UI_TESTS_DIR, PDB_TESTS_DIR, DS_TESTS_DIR):
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
            product, architecture, stack, wireframe, hifi, pair = (
                materialize_publication(root, required=required)
            )
        finally:
            sys.path[:] = original_path
        paths = {
            "prd": product,
            "architecture": architecture,
            "stack": stack,
            "ui": root / "docs/design/ui-design.md",
            "wireframe": wireframe,
            "target": hifi,
        }
        plan = valid_plan()
        plan["sources"] = [
            cls._row("SRC-PRD", "prd", product, root),
            cls._row("SRC-ARCH", "architecture", architecture, root),
            cls._row("SRC-STACK", "stack decisions", stack, root),
            cls._row("SRC-UI", "ui design", paths["ui"], root),
            cls._row("SRC-WIREFRAME", "wireframe", wireframe, root),
            cls._row("SRC-TARGET", "approved ui target", hifi, root),
        ]
        if required:
            assert pair is not None
            paths["design_markdown"] = pair[0]
            paths["design_json"] = pair[1]
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            registry["stateMatrix"] = ["ready"]
            cls._refresh_pair(root, paths, registry)
            next(
                source for source in plan["sources"] if source["kind"] == "ui design"
            )["content_sha256"] = hashlib.sha256(
                paths["ui"].read_bytes()
            ).hexdigest()
            plan["sources"].extend(
                [
                    cls._row("SRC-DS-MD", "design system", pair[0], root),
                    cls._row("SRC-DS-JSON", "design system json", pair[1], root),
                ]
            )
            plan["traces"].append(
                {
                    "id": "DS-LAY-001",
                    "source_ids": ["SRC-DS-JSON"],
                    "priority": "must",
                    "requirement": "Use the registered layout primitive",
                    "disposition": "planned",
                    "rationale": None,
                }
            )
            # Keep the real publication fixture's pair and PLAN surface
            # aligned for the positive authority case.
            plan["ui_surfaces"] = [
                {
                    "id": "UI-001",
                    "trace_ids": ["REQ-001", "DS-LAY-001"],
                    "route": "/home",
                    "breakpoints": ["390", "768", "1200"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                    "capture_mode": "hosted-browser",
                }
            ]
        else:
            plan["ui_surfaces"] = [
                {
                    "id": "UI-001",
                    "trace_ids": ["REQ-001"],
                    "route": "/home",
                    "breakpoints": ["390", "768", "1200"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                    "capture_mode": "hosted-browser",
                }
            ]
        return plan, cls._run(plan), paths

    @staticmethod
    def _refresh_pair(root: Path, paths: dict[str, Path], registry: dict[str, object]) -> None:
        json_path = paths["design_json"]
        markdown_path = paths["design_markdown"]
        json_path.write_text(json.dumps(registry), encoding="utf-8")
        markdown_path.write_text(
            replace_generated_contract("# Pair\n", registry), encoding="utf-8"
        )
        ui_path = paths["ui"]
        ui_text = ui_path.read_text(encoding="utf-8")
        ui_text = re.sub(
            r"^Compiled design system pair: .*?$",
            "Compiled design system pair: "
            f"{paths['design_markdown'].relative_to(root).as_posix()} @ sha256:{hashlib.sha256(markdown_path.read_bytes()).hexdigest()} and "
            f"{paths['design_json'].relative_to(root).as_posix()} @ sha256:{hashlib.sha256(json_path.read_bytes()).hexdigest()}",
            ui_text,
            flags=re.MULTILINE,
        )
        ui_path.write_text(ui_text, encoding="utf-8")

    def test_headless_core_sources_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = self._headless_fixture(root)
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))

    def test_headless_missing_wrong_core_and_rootless_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = self._headless_fixture(root)
            plan["sources"] = [
                source for source in plan["sources"] if source["kind"] != "stack decisions"
            ]
            self.assertTrue(any("exactly one frozen stack" in error for error in validate_frozen_contract_joins(plan, root, run=run)))

            plan, run = self._headless_fixture(root)
            plan["sources"][1]["kind"] = "product architecture"
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("canonical kind" in error for error in errors))
            self.assertTrue(any("--repo-root" in error for error in validate_current_plan_run(plan, run)))

    def test_source_revision_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = self._headless_fixture(root)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "sources"], cwd=root, check=True)
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            for source in plan["sources"]:
                source["source_revision"] = revision
            (root / "docs/product/PRD.md").write_text("drift\n", encoding="utf-8")
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("current bytes differ" in error for error in errors))

    def test_ui_not_required_target_and_capture_joins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, paths = self._ui_fixture(root, required=False)
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))
            plan["ui_surfaces"][0]["capture_mode"] = "native"
            self.assertTrue(any("capture_mode" in error for error in validate_frozen_contract_joins(plan, root, run=run)))
            plan["ui_surfaces"][0]["capture_mode"] = "hosted-browser"
            target = next(source for source in plan["sources"] if source["kind"] == "approved ui target")
            target["location"] = "docs/design/ui-references/missing/index.html"
            self.assertTrue(any("approved UI target" in error for error in validate_frozen_contract_joins(plan, root, run=run)))

    def test_not_required_pair_and_trace_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, paths = self._ui_fixture(root, required=False)
            ds_path = root / "docs/design/design-system.json"
            ds_path.write_text("{}", encoding="utf-8")
            plan["sources"].append(self._row("SRC-DS", "design system json", ds_path, root))
            plan["traces"].append(
                {
                    "id": "DS-LAY-001",
                    "source_ids": ["SRC-DS"],
                    "priority": "must",
                    "requirement": "bad trace",
                    "disposition": "planned",
                    "rationale": None,
                }
            )
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("not_required" in error for error in errors))

    def test_required_ds2_registry_trace_state_and_responsive_joins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, paths = self._ui_fixture(root, required=True)
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            registry["stateMatrix"] = ["ready", "loading", "missing"]
            registry["viewports"] = [390, 768, 1200, 1440]
            self._refresh_pair(root, paths, registry)
            for source in plan["sources"]:
                source_path = root / source["location"]
                source["content_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            errors = validate_frozen_contract_joins(plan, root, run=run)
            joined = " ".join(errors)
            self.assertIn("omits state missing", joined)
            self.assertIn("omits responsive target 1440", joined)

            plan, run, paths = self._ui_fixture(root, required=True)
            plan["traces"].append(
                {
                    "id": "DS-LAY-999",
                    "source_ids": ["SRC-DS-JSON"],
                    "priority": "must",
                    "requirement": "missing trace",
                    "disposition": "planned",
                    "rationale": None,
                }
            )
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("DS-LAY-999" in error and "absent" in error for error in errors))

    def test_required_missing_and_legacy_pair_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, paths = self._ui_fixture(root, required=True)
            plan["sources"] = [source for source in plan["sources"] if source["kind"] != "design system json"]
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("design-system.md and design-system.json" in error for error in errors))

            plan, run, paths = self._ui_fixture(root, required=True)
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            registry["schema"] = "design-system/1"
            self._refresh_pair(root, paths, registry)
            for source in plan["sources"]:
                source_path = root / source["location"]
                source["content_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(any("design-system/2" in error for error in errors))

    def test_hybrid_plan_surface_join_keeps_web_and_native_matrices_separate(self) -> None:
        plan = {
            "ui_surfaces": [
                {
                    "id": "UI-WEB",
                    "route": "/home",
                    "states": ["ready"],
                    "breakpoints": ["390", "768", "1200"],
                    "capture_mode": "hosted-browser",
                    "surface_class": "hosted_web",
                    "release_surface": "web",
                },
                {
                    "id": "UI-IOS",
                    "route": "/ios-home",
                    "states": ["ready"],
                    "breakpoints": ["compact", "regular"],
                    "capture_mode": "native",
                    "surface_class": "ios",
                    "release_surface": "ios",
                },
            ]
        }
        view = {
            "capture_mode": "mixed",
            "target_scope": {
                "surfaces": [
                    {
                        "id": "UI-WEB",
                        "route": "/home",
                        "states": ["ready"],
                        "surfaceClass": "hosted_web",
                        "releaseSurface": "web",
                        "captureMode": "hosted-browser",
                        "responsive": {"kind": "viewports", "targets": [390, 768, 1200]},
                    },
                    {
                        "id": "UI-IOS",
                        "route": "/ios-home",
                        "states": ["ready"],
                        "surfaceClass": "ios",
                        "releaseSurface": "ios",
                        "captureMode": "native",
                        "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]},
                    },
                ],
                "responsive": {"kind": "per-surface", "targets": []},
            },
        }
        self.assertEqual([], _strict_ui_surface_errors(plan, view))


if __name__ == "__main__":
    unittest.main()
