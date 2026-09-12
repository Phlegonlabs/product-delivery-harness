#!/usr/bin/env python3
"""Dedicated CLI tests for validate_harness_plan.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import plan_digest  # noqa: E402
from harness_design_contract import generated_contract_block  # noqa: E402
from harness_contract_join import (  # noqa: E402
    full_product_package_checker_errors,
    full_wireframe_checker_errors,
    validate_frozen_contract_joins,
    validate_plan_prd_text,
)
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from manifest_fixtures import manifest_markdown, wireframes_html  # noqa: E402


HOME_SURFACE = {
    "id": "UI-001",
    "trace_ids": ["REQ-001"],
    "route": "/home",
    "breakpoints": ["390", "1200"],
    "states": ["ready"],
    "evidence_gate": "required",
}


class ValidateHarnessPlanCliTests(unittest.TestCase):
    @staticmethod
    def bind_prd(plan: dict, root: Path, text: str) -> Path:
        source = next(source for source in plan["sources"] if source["kind"] == "prd")
        path = root / source["location"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        source["content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    def run_cli(
        self,
        plan_path: Path,
        run_path: Path | None,
        design_system: Path | None = None,
        design_system_markdown: Path | None = None,
        repo_root: Path | None = None,
        prd: Path | None = None,
        wireframes: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPTS_DIR / "validate_harness_plan.py"), "--plan", str(plan_path)]
        if run_path is not None:
            command.extend(["--run", str(run_path)])
        if repo_root is None and run_path is not None:
            repo_root = plan_path.parent
        if repo_root is not None:
            command.extend(["--repo-root", str(repo_root)])
        if design_system is not None:
            command.extend(["--design-system", str(design_system)])
        if design_system_markdown is not None:
            command.extend(
                ["--design-system-markdown", str(design_system_markdown)]
            )
        if prd is not None:
            command.extend(["--prd", str(prd)])
        if wireframes is not None:
            command.extend(["--wireframes", str(wireframes)])
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def cross_check(self, registry: dict[str, object]) -> dict[str, object]:
        """Validate a one-surface PLAN against `registry`; return the CLI payload."""
        complete_registry: dict[str, object] = {
            "schema": "design-system/1",
            "product": "Fixture Product",
            "platform": "web",
            "stylingMechanism": "plain CSS",
            "enforcement": "blocking",
            "tokenSources": ["src/styles/tokens.css"],
            "primitiveSources": [],
            "tokens": {},
            "primitives": {},
            "productComponents": {},
            "signatureRules": [],
            "motionVariants": [],
        }
        complete_registry.update(registry)
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            registry_path = root / "design-system.json"
            registry_path.write_text(
                json.dumps(complete_registry), encoding="utf-8"
            )
            result = self.run_cli(
                plan_path, None, design_system=registry_path, prd=prd_path
            )
        return json.loads(result.stdout)

    def test_valid_plan_and_run_report_pass(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "harness@example.invalid"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", run["integration"]["branch"]],
                cwd=root, check=True, capture_output=True, text=True,
            )
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "base"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            head_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root, check=True, capture_output=True, text=True,
            ).stdout.strip()
            run["integration"]["integration_head_sha"] = head_sha
            for source in plan["sources"]:
                location = source["location"]
                contents = f"{source['id']} frozen source\n".encode()
                source_path = root / location
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(contents)
                source["content_sha256"] = hashlib.sha256(contents).hexdigest()
            run["plan"]["digest_sha256"] = plan_digest(plan)

            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )

            result = self.run_cli(
                plan_path,
                run_path,
                prd=root / plan["sources"][0]["location"],
            )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual([], payload["errors"])
        self.assertEqual(plan["plan_id"], payload["plan_id"])

    def test_plan_only_invocation_skips_run_validation(self) -> None:
        plan = valid_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(plan, root, "# Product contract\n")
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None, prd=prd_path)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("PASS", json.loads(result.stdout)["status"])

    def test_canonical_template_requires_its_frozen_prd_at_file_join(self) -> None:
        plan_path = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"
        result = self.run_cli(plan_path, None)

        self.assertEqual(1, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertTrue(any("requires --prd" in error for error in payload["errors"]))

    def test_repo_root_binds_current_plan_sources_when_requested(self) -> None:
        plan = valid_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None, repo_root=root)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertTrue(any("does not exist under --repo-root" in error for error in payload["errors"]))

    def test_invalid_plan_reports_fail_with_exit_code_one(self) -> None:
        plan = valid_plan()
        plan["missions"] = []
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertTrue(payload["errors"])

    def test_recipe_state_coverage_is_cross_checked_against_the_registry(self) -> None:
        payload = self.cross_check(
            {
                "viewports": [390, 1200],
                "stateMatrix": ["ready", "loading", "empty", "n/a"],
            }
        )

        self.assertEqual("FAIL", payload["status"])
        joined = " ".join(payload["errors"])
        self.assertIn("omits state loading", joined)
        self.assertIn("omits state empty", joined)
        self.assertIn("omits state n/a", joined)
        self.assertNotIn("/settings", joined)

    def test_registry_cross_check_enforces_responsive_values_per_surface(self) -> None:
        payload = self.cross_check(
            {"viewports": [390, 768], "stateMatrix": ["ready", "error"]}
        )

        joined = " ".join(payload["errors"])
        self.assertIn("surface UI-001 route /home omits state error", joined)
        self.assertIn("surface UI-001 route /home omits responsive target 768", joined)
        self.assertNotIn("/settings", joined)

    def test_registry_cross_check_rejects_malformed_evidence_contract(self) -> None:
        payload = self.cross_check(
            {
                "viewports": [0],
                "stateMatrix": ["ready", " "],
                "$note": "both halves malformed; stateMatrix is reported first",
            }
        )

        joined = " ".join(payload["errors"])
        # A malformed stateMatrix stops the cross-check before the responsive
        # set is read, so only the first defect is reported per run.
        self.assertIn("stateMatrix: must be a non-empty string list", joined)

    def test_registry_cross_check_is_skipped_without_the_flag(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")

            result = self.run_cli(plan_path, None, prd=prd_path)

        self.assertEqual(0, result.returncode)

    def test_prd_cross_check_requires_matching_ui_surface_sets(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE, id="UI-001")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None, prd=prd_path)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("PASS", json.loads(result.stdout)["status"])

            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n\n"
                "- `responsive`: viewports: 390, 1200\n"
                "### UI-002 — Settings\n\n"
                "- `route`: /settings\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            plan["sources"][0]["content_sha256"] = hashlib.sha256(
                prd_path.read_bytes()
            ).hexdigest()
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any(
                    "PRD surfaces absent from the PLAN: UI-002" in error
                    for error in payload["errors"]
                )
            )

    def test_frozen_prd_source_requires_a_hash_matching_prd_argument(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE, id="UI-001")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            prd_path = root / "PRD.md"
            prd_path.write_text(
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- Route(s): /home\n"
                "- States: ready\n",
                encoding="utf-8",
            )

            # A frozen PRD source without --prd fails outright.
            result = self.run_cli(plan_path, None)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any("requires --prd" in error for error in payload["errors"])
            )

            # A decoy file with the same ids but different bytes fails the
            # frozen hash, so the join cannot be redirected.
            plan["sources"][0]["content_sha256"] = hashlib.sha256(
                b"the real frozen bytes\n"
            ).hexdigest()
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any(
                    "does not match the frozen PRD source content hash" in error
                    for error in payload["errors"]
                )
            )

            # A source revision cannot substitute for the frozen byte hash at
            # this file join.
            plan["sources"][0]["content_sha256"] = None
            plan["sources"][0]["source_revision"] = "a" * 40
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any("requires content_sha256" in error for error in payload["errors"])
            )

    def test_wireframes_join_compares_routes_and_states(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/home",
                "breakpoints": ["390", "1200"],
                "states": ["ready"],
                "evidence_gate": "required",
            }
        ]
        wireframes = wireframes_html(
            [{"id": "UI-001", "route": "/home", "states": ["ready"]}]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            wireframes_path = root / "wireframes.html"
            wireframes_path.write_text(wireframes, encoding="utf-8")
            plan["sources"].append(
                {
                    "id": "SRC-WIREFRAMES",
                    "kind": "wireframe",
                    "location": "wireframes.html",
                    "owner": "product",
                    "status": "frozen",
                    "content_sha256": hashlib.sha256(
                        wireframes_path.read_bytes()
                    ).hexdigest(),
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "approved UI projection",
                }
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                wireframes=wireframes_path,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("PASS", json.loads(result.stdout)["status"])

            plan["ui_surfaces"][0]["breakpoints"] = ["390", "768"]
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                wireframes=wireframes_path,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any(
                    "breakpoints" in error and "responsive" in error
                    for error in payload["errors"]
                ),
                payload["errors"],
            )
            plan["ui_surfaces"][0]["breakpoints"] = ["390", "1200"]

            drifted = wireframes_html(
                [{"id": "UI-001", "route": "/dashboard", "states": ["ready", "empty"]}]
            )
            wireframes_path.write_text(drifted, encoding="utf-8")
            plan["sources"][-1]["content_sha256"] = hashlib.sha256(
                wireframes_path.read_bytes()
            ).hexdigest()
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                wireframes=wireframes_path,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            joined = " ".join(payload["errors"])
            self.assertIn("route", joined)
            self.assertIn("states", joined)

    def test_prd_responsive_targets_must_match_plan_breakpoints(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        prd = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 768\n"
            "<!-- ui-surface-contract:end -->\n"
        )

        errors = validate_plan_prd_text(plan, prd)

        self.assertTrue(
            any(
                "breakpoints" in error and "responsive targets" in error
                for error in errors
            ),
            errors,
        )

    def test_prd_join_rejects_missing_responsive_anchor(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        prd = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n"
        )

        errors = validate_plan_prd_text(plan, prd)

        self.assertTrue(
            any(
                "requires exactly one `responsive` anchor" in error
                for error in errors
            ),
            errors,
        )

    def test_wireframes_join_runs_the_full_builder_checker(self) -> None:
        """Frozen wireframes must pass the sibling skill's checker, not just the
        reduced PLAN join: reviewer shell, self-containment, and approved
        status are enforced on the frozen bytes."""

        valid = wireframes_html(
            [{"id": "UI-001", "route": "/home", "states": ["ready"]}]
        ).encode("utf-8")
        prd = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 1200\n"
            "<!-- ui-surface-contract:end -->\n"
        ).encode("utf-8")
        self.assertEqual([], full_wireframe_checker_errors(valid, prd))

        bare_block = (
            '<script id="wireframe-data" type="application/json">'
            + json.dumps(
                {
                    "screens": [
                        {
                            "id": "UI-001",
                            "route": "/home",
                            "states": [{"id": "ready"}],
                        }
                    ]
                }
            )
            + "</script>"
        ).encode("utf-8")
        joined = " ".join(full_wireframe_checker_errors(bare_block, prd))
        self.assertIn("reviewer-shell marker", joined)
        self.assertIn("wireframe-data.product", joined)
        self.assertIn("approvalStatus", joined)

        non_object = (
            '<script id="wireframe-data" type="application/json">[]</script>'
        ).encode("utf-8")
        joined = " ".join(full_wireframe_checker_errors(non_object, prd))
        self.assertIn("wireframe-data: must be a JSON object", joined)

        draft = wireframes_html(
            [{"id": "UI-001", "route": "/home", "states": ["ready"]}],
            approval_status="draft",
        ).encode("utf-8")
        joined = " ".join(full_wireframe_checker_errors(draft, prd))
        self.assertIn("wireframe-data.approvalStatus", joined)
        self.assertIn("must be 'approved'", joined)

        external = valid.replace(
            b"<main></main>", b'<main><img src="https://example.invalid/x.png"></main>'
        )
        joined = " ".join(full_wireframe_checker_errors(external, prd))
        self.assertIn("must not load external resources", joined)

        drifted_prd = prd.replace(b"- `route`: /home", b"- `route`: /alias")
        joined = " ".join(full_wireframe_checker_errors(valid, drifted_prd))
        self.assertIn("differs from the PRD route", joined)

        missing = full_wireframe_checker_errors(
            valid, prd, sibling_scripts=Path("nowhere") / "product-definition-builder"
        )
        self.assertEqual(1, len(missing))
        self.assertIn("full wireframe checker is unavailable", missing[0])

    def test_approved_product_package_runs_the_full_builder_checker(self) -> None:
        prd = self.approved_prd().encode("utf-8")
        architecture = self.approved_architecture().encode("utf-8")
        stack = self.approved_stack().encode("utf-8")
        self.assertEqual(
            [], full_product_package_checker_errors(prd, architecture, stack)
        )

        recommended = stack.replace(b"| Framework | React | Approved |", b"| Framework | React | Recommended |")
        errors = full_product_package_checker_errors(prd, architecture, recommended)
        self.assertTrue(any("owner approval is required" in error for error in errors))

        missing = full_product_package_checker_errors(
            prd,
            architecture,
            stack,
            sibling_scripts=Path("nowhere") / "product-definition-builder",
        )
        self.assertEqual(1, len(missing))
        self.assertIn("Product Definition checker is unavailable", missing[0])

    def test_approval_marker_requires_and_joins_frozen_core_package(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(plan, root, self.approved_prd())
            architecture_source = next(
                source for source in plan["sources"] if source["kind"] == "architecture"
            )
            architecture_path = root / architecture_source["location"]
            architecture_path.parent.mkdir(parents=True, exist_ok=True)
            architecture_path.write_text(self.approved_architecture(), encoding="utf-8")
            architecture_source["content_sha256"] = hashlib.sha256(
                architecture_path.read_bytes()
            ).hexdigest()
            stack_path = root / "docs/product/stack-decisions.md"
            stack_path.write_text(self.approved_stack(), encoding="utf-8")
            plan["sources"].append(
                {
                    "id": "SRC-STACK",
                    "kind": "stack decisions",
                    "location": "docs/product/stack-decisions.md",
                    "owner": "product",
                    "status": "frozen",
                    "content_sha256": hashlib.sha256(stack_path.read_bytes()).hexdigest(),
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "approved stack",
                }
            )
            self.assertTrue(prd_path.is_file())
            self.assertEqual([], validate_frozen_contract_joins(plan, root))

            plan["sources"] = [
                source for source in plan["sources"] if source["kind"] != "stack decisions"
            ]
            errors = validate_frozen_contract_joins(plan, root)
            self.assertTrue(
                any("requires exactly one frozen stack-decisions.md" in error for error in errors)
            )

    @staticmethod
    def approved_prd() -> str:
        headings = (
            "At a Glance",
            "Problem Statement",
            "Goals",
            "Non-Goals",
            "Users and Personas",
            "User Journeys",
        )
        text = "# PRD: Fixture\n\n" + "\n".join(
            f"## {heading}\nFilled." for heading in headings
        )
        return text + """
## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-001 | Complete fixture | Must | Completion is observable |
## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-002 | Reliability | Fixture run | Passing executions | 100% | TEST-002 |
## UX Requirements
Filled.
## Data and Integration Requirements
Filled.
## Data and Trust
Data and Trust Gate: not_required — no sensitive data, decided by Owner
## AI and Automation
AI and Automation Gate: not_required — no AI, decided by Owner
## Business Rules
Filled.
## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization Infrastructure Gate | not_required | No commercial surface | approved | n/a |
| Partner Channel Gate | not_required | No outside sellers | approved | n/a |
## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Completion | Completed | 0 | 90% | 30 days | Events | Owner |
## Risks
Filled.
## Assumptions
| Assumption | Impact if wrong | Validation | Owner | Decision date | Status |
| --- | --- | --- | --- | --- | --- |
## Open Questions
| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |
| --- | --- | --- | --- | --- | --- |
## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Complete fixture | integration | Yes | PRD-001 | Completion observed |
| TEST-002 | Reliable fixture | reliability | Yes | PRD-002 | All runs pass |
## Product Definition Decisions
### Research Gate
Research Gate: go — assessed 2026-09-12, decided by Owner
<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: new
- Package revision: PD-R1
- Decision: approved
- Decision owner: Owner
- Decided on: 2026-09-12
- Approved artifacts: PRD.md, architecture.md, stack-decisions.md
- Market research reconciliation: completed
- Stack Decision Checkpoint: approved
- Accepted assumptions and non-blocking questions: none
- Blocking items: none
<!-- product-definition-approval:end -->
"""

    @staticmethod
    def approved_architecture() -> str:
        headings = (
            "Architecture Summary",
            "Product Archetype",
            "System Context",
            "Component Architecture",
            "Data Model",
            "API and Interface Contracts",
            "Workflow and Data Flow",
            "Auth, Permissions, and Security",
            "Data and Trust Architecture",
            "AI and Automation Architecture",
            "Integrations",
            "Deployment and Operations",
            "Observability",
            "Scaling and Reliability",
            "Technical Risks and Tradeoffs",
            "Architecture Trace Index",
        )
        return "# Architecture: Fixture\n\n" + "\n".join(
            f"## {heading}\nFilled." for heading in headings
        )

    @staticmethod
    def approved_stack() -> str:
        return """# Stack Decisions: Fixture
<!-- stack-decision-checkpoint:start -->
## Stack Decision Checkpoint
- Decision: approved
- Decision owner: Owner
- Decided on: 2026-09-12
- Approved areas: frontend
- Delegated choices: none
- Open areas: none
<!-- stack-decision-checkpoint:end -->
### Coherent Options Presented
| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-FE-01 | Frontend | React bundle | Synthetic app | Team ownership | approved |
| OPT-FE-02 | Frontend | Astro bundle | Content app | Team ownership | rejected |
## Frontend Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Deployment / runtime | Cloudflare Workers | Approved | Owner | Fits | None |
| Rendering model | SPA | Approved | Owner | Fits | None |
| Language | TypeScript | Approved | Owner | Fits | None |
| Package manager | npm | Approved | Owner | Fits | None |
| Framework | React | Approved | Owner | Fits | None |
| UI library | React | Approved | Owner | Fits | None |
| Component foundation | shadcn/ui owned source | Approved | Owner | Fits | Own source |
| Styling approach | Tailwind CSS | Approved | Owner | Fits | None |
| Build tool | Vite | Approved | Owner | Fits | None |
| Routing and data | React Router | Approved | Owner | Fits | None |
| Testing | Vitest and Playwright | Approved | Owner | Fits | None |
"""

    def test_prd_join_uses_only_structured_entries_and_compares_semantics(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "# Product\n\nMention UI-999 only as historical prose.\n\n"
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            self.assertEqual(0, result.returncode, result.stdout)

            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /dashboard\n"
                "- `states`: ready, empty\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            joined = " ".join(payload["errors"])
            self.assertIn("route", joined)
            self.assertIn("states", joined)
            self.assertNotIn("UI-999", joined)

    def test_prd_join_accepts_localized_prose_but_rejects_multiple_routes(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## 介面契約\n\n"
                "### UI-001 — 首頁\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)
            self.assertEqual(0, result.returncode, result.stdout)

            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home, /alias\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(plan_path, None, prd=prd_path)

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any(
                "requires exactly one route value" in error
                for error in json.loads(result.stdout)["errors"]
            )
        )

    def test_prd_machine_contract_rejects_missing_duplicate_or_ambiguous_anchors(
        self,
    ) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        valid_block = (
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n\n"
            "### UI-001 — 首頁\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 1200\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        cases = (
            (
                "missing boundary",
                "## UI Surface Contract\n\n### UI-001 — Home\n\n"
                "- `route`: /home\n- `states`: ready\n",
                "boundary pair",
            ),
            ("duplicate boundary", valid_block + valid_block, "boundary pair"),
            (
                "heading outside boundary",
                "<!-- ui-surface-contract:start -->\n"
                "## 介面契約\n"
                "<!-- ui-surface-contract:end -->\n"
                "### UI-001 — Outside\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n",
                "headings outside the ui-surface-contract boundary",
            ),
            (
                "duplicate fields",
                valid_block.replace(
                    "- `states`: ready\n",
                    "- `route`: /alias\n"
                    "- `states`: ready\n"
                    "- `responsive`: viewports: 390, 1200\n"
                    "- `states`: empty\n",
                ),
                "exactly one `route` anchor",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            for label, text, expected in cases:
                with self.subTest(label=label):
                    prd_path = self.bind_prd(plan, root, text)
                    plan_path.write_text(
                        manifest_markdown(
                            "## Harness Plan Manifest", "harness_plan", plan
                        ),
                        encoding="utf-8",
                    )
                    result = self.run_cli(plan_path, None, prd=prd_path)
                    self.assertEqual(1, result.returncode, result.stdout)
                    joined = " ".join(json.loads(result.stdout)["errors"])
                    self.assertIn(expected, joined)
                    if label == "duplicate fields":
                        self.assertIn("exactly one `states` anchor", joined)

    def test_design_system_join_binds_bytes_and_resolves_all_ds_traces(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        plan["traces"].append(
            {
                "id": "DS-LAY-001",
                "source_ids": ["SRC-001"],
                "priority": "must",
                "requirement": "Use the registered layout primitive",
                "disposition": "planned",
                "rationale": None,
            }
        )
        plan["missions"][0]["trace_ids"].append("DS-LAY-001")
        plan["missions"][0]["tasks"][0]["trace_ids"].append("DS-LAY-001")
        plan["missions"][0]["tasks"][0]["acceptance_matrix"][0][
            "trace_ids"
        ].append("DS-LAY-001")
        registry = {
            "schema": "design-system/1",
            "product": "Fixture Product",
            "platform": "web",
            "stylingMechanism": "plain CSS",
            "enforcement": "blocking",
            "tokenSources": ["src/styles/tokens.css"],
            "primitiveSources": ["src/ui/primitives.css"],
            "viewports": [390, 1200],
            "tokens": {},
            "stateMatrix": ["ready"],
            "primitives": {
                "Stack": {"dsId": "DS-LAY-001", "layer": "layout"}
            },
            "productComponents": {
                "Card": {
                    "dsId": "DS-COMP-001",
                    "requiredContentOrder": ["title"],
                    "composes": ["Stack"],
                    "states": ["ready"],
                }
            },
            "signatureRules": ["DS-010"],
            "motionVariants": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(
                plan,
                root,
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
            )
            registry_path = root / "design-system.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            markdown_path = root / "design-system.md"
            markdown_path.write_text(
                "# Design system\n\n" + generated_contract_block(registry) + "\n",
                encoding="utf-8",
            )
            for source_id, kind, path in (
                ("SRC-DESIGN-MD", "design system", markdown_path),
                ("SRC-DESIGN-JSON", "design system machine", registry_path),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.name,
                        "owner": "design",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "frozen design contract",
                    }
                )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None, prd=prd_path)
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any("requires --design-system" in error for error in payload["errors"])
            )

            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
            )
            self.assertEqual(0, result.returncode, result.stdout)

            plan["traces"][-1]["id"] = "DS-LAY-999"
            plan["missions"][0]["trace_ids"][-1] = "DS-LAY-999"
            plan["missions"][0]["tasks"][0]["trace_ids"][-1] = "DS-LAY-999"
            plan["missions"][0]["tasks"][0]["acceptance_matrix"][0][
                "trace_ids"
            ][-1] = "DS-LAY-999"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertTrue(
                any(
                    "DS-LAY-999" in error and "absent from design-system.json" in error
                    for error in payload["errors"]
                )
            )

    def test_design_system_join_accepts_the_required_markdown_json_pair(self) -> None:
        plan = valid_plan()
        registry = {
            "schema": "design-system/1",
            "product": "Fixture Product",
            "platform": "web",
            "stylingMechanism": "plain CSS",
            "enforcement": "blocking",
            "tokenSources": ["src/styles/tokens.css"],
            "primitiveSources": [],
            "viewports": [390, 1200],
            "tokens": {},
            "primitives": {},
            "productComponents": {},
            "signatureRules": [],
            "motionVariants": [],
            "stateMatrix": ["ready"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(plan, root, "# Product contract\n")
            architecture_source = next(
                source for source in plan["sources"] if source["kind"] == "architecture"
            )
            architecture_path = root / architecture_source["location"]
            architecture_path.parent.mkdir(parents=True, exist_ok=True)
            architecture_path.write_text("# Architecture\n", encoding="utf-8")
            architecture_source["content_sha256"] = hashlib.sha256(
                architecture_path.read_bytes()
            ).hexdigest()
            markdown_path = root / "design-system.md"
            registry_path = root / "design-system.json"
            markdown_path.write_text(
                "# Design system\n\n" + generated_contract_block(registry) + "\n",
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            for source_id, kind, path in (
                ("SRC-DESIGN-MD", "design system", markdown_path),
                ("SRC-DESIGN-JSON", "design system machine", registry_path),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.name,
                        "owner": "design",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "required pair",
                    }
                )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
                repo_root=root,
            )
            self.assertEqual(0, result.returncode, result.stdout)

            mismatched_registry = dict(registry, product="Different Product")
            markdown_path.write_text(
                "# Design system\n\n"
                + generated_contract_block(mismatched_registry)
                + "\n",
                encoding="utf-8",
            )
            markdown_source = next(
                source
                for source in plan["sources"]
                if source["location"] == "design-system.md"
            )
            markdown_source["content_sha256"] = hashlib.sha256(
                markdown_path.read_bytes()
            ).hexdigest()
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            mismatched = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
                repo_root=root,
            )

        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual("PASS", json.loads(result.stdout)["status"])
        self.assertEqual(1, mismatched.returncode)
        self.assertTrue(
            any(
                "generated contract.product differs" in error
                for error in json.loads(mismatched.stdout)["errors"]
            )
        )

    def test_design_system_join_rejects_compiler_invalid_id_namespaces(self) -> None:
        plan = valid_plan()
        registry = {
            "schema": "design-system/1",
            "product": "Fixture Product",
            "platform": "web",
            "stylingMechanism": "plain CSS",
            "enforcement": "blocking",
            "tokenSources": ["src/styles/tokens.css"],
            "primitiveSources": [],
            "viewports": [390, 1200],
            "tokens": {},
            "primitives": {
                "Stack": {"dsId": "DS-001", "layer": "layout"}
            },
            "productComponents": {
                "Card": {
                    "dsId": "DS-LAY-002",
                    "requiredContentOrder": ["title"],
                    "composes": ["Stack"],
                    "states": ["ready"],
                }
            },
            "signatureRules": [42],
            "motionVariants": [],
            "stateMatrix": ["ready"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd_path = self.bind_prd(plan, root, "# Product contract\n")
            architecture = next(
                source for source in plan["sources"] if source["kind"] == "architecture"
            )
            architecture_path = root / architecture["location"]
            architecture_path.parent.mkdir(parents=True, exist_ok=True)
            architecture_path.write_text("# Architecture\n", encoding="utf-8")
            architecture["content_sha256"] = hashlib.sha256(
                architecture_path.read_bytes()
            ).hexdigest()
            markdown_path = root / "design-system.md"
            registry_path = root / "design-system.json"
            markdown_path.write_text(
                "# Design system\n\n" + generated_contract_block(registry) + "\n",
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            for source_id, kind, path in (
                ("SRC-DESIGN-MD", "design system", markdown_path),
                ("SRC-DESIGN-JSON", "design system machine", registry_path),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.name,
                        "owner": "design",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "frozen design contract",
                    }
                )
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            result = self.run_cli(
                plan_path,
                None,
                prd=prd_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
                repo_root=root,
            )

        self.assertEqual(1, result.returncode, result.stdout)
        joined = " ".join(json.loads(result.stdout)["errors"])
        self.assertIn("primitives.Stack.dsId must match", joined)
        self.assertIn("productComponents.Card.dsId must match", joined)
        self.assertIn("signatureRules entry must match", joined)

    @staticmethod
    def web_floor_registry(viewports: list[int]) -> dict[str, object]:
        return {
            "schema": "design-system/1",
            "product": "Fixture Product",
            "platform": "web",
            "stylingMechanism": "plain CSS",
            "enforcement": "blocking",
            "tokenSources": ["src/styles/tokens.css"],
            "primitiveSources": [],
            "viewports": list(viewports),
            "tokens": {},
            "primitives": {},
            "productComponents": {},
            "signatureRules": [],
            "motionVariants": [],
            "stateMatrix": ["ready"],
        }

    def run_gated_pair_cli(
        self, viewports: list[int], *, gate: str | None
    ) -> dict[str, object]:
        """Validate a fully joined PLAN/RUN pair; return the CLI payload.

        Every responsive surface agrees on `viewports`, so the only possible
        failures are the version-gated three-viewport web floor and whatever
        the test under construction breaks on purpose.
        """

        plan = valid_plan()
        plan["security_review"] = {
            "status": "not_applicable",
            "skill_slot": "code_security_verification",
            "reason": "fixture has no implementation candidate",
        }
        breakpoints = [str(value) for value in viewports]
        plan["ui_surfaces"] = [dict(HOME_SURFACE, breakpoints=breakpoints)]
        prd_text = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            f"- `responsive`: viewports: {', '.join(breakpoints)}\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        wireframes = wireframes_html(
            [{"id": "UI-001", "route": "/home", "states": ["ready"]}],
            schema="wireframes/3" if len(viewports) >= 3 else "wireframes/2",
            viewports=tuple(viewports),
        )
        registry = self.web_floor_registry(viewports)
        run = valid_run(plan)
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        if gate is None:
            adapter.pop("version_gate")
        else:
            adapter["version_gate"]["required_harness_version"] = gate
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "harness@example.invalid"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", run["integration"]["branch"]],
                cwd=root, check=True, capture_output=True, text=True,
            )
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "base"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            run["integration"]["integration_head_sha"] = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root, check=True, capture_output=True, text=True,
            ).stdout.strip()
            prd_path = self.bind_prd(plan, root, prd_text)
            architecture = next(
                source for source in plan["sources"] if source["kind"] == "architecture"
            )
            architecture_path = root / architecture["location"]
            architecture_path.parent.mkdir(parents=True, exist_ok=True)
            architecture_path.write_text("# Architecture\n", encoding="utf-8")
            architecture["content_sha256"] = hashlib.sha256(
                architecture_path.read_bytes()
            ).hexdigest()
            wireframes_path = root / "wireframes.html"
            wireframes_path.write_text(wireframes, encoding="utf-8")
            plan["sources"].append(
                {
                    "id": "SRC-WIREFRAMES",
                    "kind": "wireframe",
                    "location": "wireframes.html",
                    "owner": "product",
                    "status": "frozen",
                    "content_sha256": hashlib.sha256(
                        wireframes_path.read_bytes()
                    ).hexdigest(),
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "approved UI projection",
                }
            )
            markdown_path = root / "design-system.md"
            registry_path = root / "design-system.json"
            markdown_path.write_text(
                "# Design system\n\n" + generated_contract_block(registry) + "\n",
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            for source_id, kind, path in (
                ("SRC-DESIGN-MD", "design system", markdown_path),
                ("SRC-DESIGN-JSON", "design system machine", registry_path),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.name,
                        "owner": "design",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "frozen design contract",
                    }
                )
            run["plan"]["digest_sha256"] = plan_digest(plan)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            result = self.run_cli(
                plan_path,
                run_path,
                design_system=registry_path,
                design_system_markdown=markdown_path,
                repo_root=root,
                prd=prd_path,
                wireframes=wireframes_path,
            )
        return json.loads(result.stdout)

    def test_gated_run_requires_three_viewport_design_system(self) -> None:
        payload = self.run_gated_pair_cli([390, 1200], gate="0.35.0")
        self.assertEqual("FAIL", payload["status"])
        self.assertIn(
            "design_system: web responsive set needs at least three ascending "
            "viewports (harness 0.34.0+)",
            " ".join(payload["errors"]),
        )

        payload = self.run_gated_pair_cli([390, 768, 1200], gate="0.35.0")
        self.assertEqual("PASS", payload["status"])

    def test_gated_run_requires_three_viewport_prd_anchors(self) -> None:
        payload = self.run_gated_pair_cli([390, 1200], gate="0.35.0")
        self.assertEqual("FAIL", payload["status"])
        self.assertIn(
            "prd: UI surface UI-001 `responsive` web responsive set needs at "
            "least three ascending viewports (harness 0.34.0+)",
            " ".join(payload["errors"]),
        )

        payload = self.run_gated_pair_cli([390, 768, 1200], gate="0.35.0")
        self.assertEqual("PASS", payload["status"])

    def test_ungated_run_keeps_the_two_viewport_floor(self) -> None:
        payload = self.run_gated_pair_cli([390, 1200], gate=None)

        self.assertEqual("PASS", payload["status"], payload["errors"])

    def test_frozen_joins_carry_the_viewport_floor_only_for_gated_runs(self) -> None:
        plan = valid_plan()
        registry = self.web_floor_registry([390, 1200])
        ungated = valid_run(plan)
        gated = valid_run(plan)
        gated["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "0.35.0"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.bind_prd(plan, root, "# Product contract\n")
            markdown_path = root / "design-system.md"
            registry_path = root / "design-system.json"
            markdown_path.write_text(
                "# Design system\n\n" + generated_contract_block(registry) + "\n",
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            for source_id, kind, path in (
                ("SRC-DESIGN-MD", "design system", markdown_path),
                ("SRC-DESIGN-JSON", "design system machine", registry_path),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.name,
                        "owner": "design",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "frozen design contract",
                    }
                )

            self.assertEqual([], validate_frozen_contract_joins(plan, root))
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=ungated))
            errors = validate_frozen_contract_joins(plan, root, run=gated)

        self.assertEqual(
            [
                "design_system: web responsive set needs at least three "
                "ascending viewports (harness 0.34.0+)"
            ],
            errors,
        )

    def test_malformed_manifest_reports_error_with_exit_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text("# not a manifest\n", encoding="utf-8")

            result = self.run_cli(plan_path, None)

        self.assertEqual(2, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("ERROR", payload["status"])
        self.assertTrue(payload["errors"])


if __name__ == "__main__":
    unittest.main()
