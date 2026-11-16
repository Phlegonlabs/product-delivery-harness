"""Visual handoff assembly uses synthetic sources, not product acceptance proof."""

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import review_evidence
import visual_inputs
from visual_inputs import build_visual_inputs


class VisualInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prd = self.write("docs/product/PRD.md", "# Product\n")
        self.architecture = self.write("docs/product/architecture.md", "# Architecture\n")
        self.stack = self.write("docs/product/stack-decisions.md", "# Stack\n")
        self.screen = self.write("docs/design/directions/selected.png", b"synthetic selected capture")
        self.other = self.write("docs/design/directions/rejected.png", b"synthetic rejected capture")
        self.study = self.write("docs/design/directions/R1/selected.html",
                                '<style>@font-face{font-family:Study;src:url(data:font/woff2;base64,AA==)}</style><h1>Editorial</h1>')
        self.other_study = self.write("docs/design/directions/R1/rejected.html", "<h1>Cards</h1>")
        self.child = self.write("docs/design/ui-references/run/child.html", "<h1>Details</h1>")
        manifest = {"schema": "ui-hifi/2", "surfaces": [], "interactions": [],
                    "pages": [{"path": "child.html", "sha256": self.digest(self.child)}]}
        self.hifi = self.write("docs/design/ui-references/run/index.html",
                               '<script id="ui-hifi-manifest" type="application/json">'
                               + json.dumps(manifest) + '</script><style>@font-face{font-family:Brand;src:url(data:font/woff2;base64,AA==)}</style>')
        self.ui = "docs/design/ui-design.md"

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return relative

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def binding(self, relative):
        return relative + " @ sha256:" + self.digest(relative)

    def contract(self, *, selected="VD-R1-01 editorial", target=False, hifi=False, studies=False):
        scope = ('; scope=surfaces=[{"id":"UI-001","route":"/","states":["ready"],'
                 '"stackSemantics":{"platform":"web","renderingModel":"SPA",'
                 '"componentFoundation":"shadcn/ui owned source","stylingMechanism":"Tailwind CSS"}}]'
                 '|routes=["/"]|states=["ready"]'
                 '|responsive={"kind":"viewports","targets":[390,768,1200]}'
                 '|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser')
        text = f"""# UI Design Contract
UI contract: ui-design/2

## Source Product Definition
PRD source: {self.binding(self.prd)}
Architecture source: {self.binding(self.architecture)}
Stack source: {self.binding(self.stack)}

## UI Design Intake
Direction mode: three comparable directions
### Design Brief
Reference lessons: editorial composition; avoid repeated cards.

## Motion And Media Intent
Motion direction: functional_only

## Style Integration
Selected direction: {selected}
Candidate theme: Brand font, editorial heading contrast, warm ink.
Connected HiFi reference: {self.binding(self.hifi) if hifi else 'pending'}
### Direction comparison
| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | Approved copy | {self.binding(self.screen)} | Editorial hierarchy |
| VD-R1-02 | UI-001 | ready | 390 | primary | Approved copy | {self.binding(self.other)} | Rejected cards |

## Visual Approval
Approved target: {self.binding(self.hifi) + scope if target else 'pending'}

## Design System Need Gate
Decision: not_required
"""
        if studies:
            text = text.replace("UI contract: ui-design/2", "UI contract: ui-design/3").replace(
                "## Visual Approval", f"""### Direction studies
| Direction | Study | Author | Self-check by | Self-check |
| --- | --- | --- | --- | --- |
| VD-R1-01 | {self.binding(self.study)} | frontend | frontend | pass |
| VD-R1-02 | {self.binding(self.other_study)} | frontend | frontend | pass |

## Visual Approval""")
        self.write(self.ui, text)
        return text

    def test_direction_exploration_allows_selection_and_target_pending(self):
        self.contract(selected="pending")
        packet = build_visual_inputs(self.root, self.ui, "direction")
        self.assertIn("- Selected direction: pending", packet)
        self.assertIn(self.binding(self.prd), packet)
        self.assertIn(self.binding(self.screen), packet)
        self.assertIn(self.binding(self.other), packet)

    def test_hifi_handoff_selects_owner_direction_without_final_target(self):
        self.contract()
        packet = build_visual_inputs(self.root, self.ui, "hifi")
        self.assertIn(self.binding(self.screen), packet)
        self.assertNotIn(self.other, packet)
        self.assertIn("- Approved target: pending", packet)

    def test_selected_study_is_retained_for_hifi_and_implementation(self):
        for stage in ("hifi", "implementation"):
            with self.subTest(stage=stage):
                self.contract(studies=True, target=stage == "implementation")
                packet = build_visual_inputs(self.root, self.ui, stage)
                self.assertIn(self.binding(self.study), packet)
                self.assertNotIn(self.other_study, packet)

    def test_selected_study_missing_or_stale_blocks_hifi(self):
        self.contract(studies=True)
        path = self.root / self.study
        original = path.read_bytes()
        path.write_bytes(original + b" changed")
        with self.assertRaisesRegex(ValueError, "stale"):
            build_visual_inputs(self.root, self.ui, "hifi")
        path.rename(self.root / "preserved-study.html")
        with self.assertRaisesRegex(ValueError, "missing"):
            build_visual_inputs(self.root, self.ui, "hifi")

    def test_v3_selected_study_identity_is_required(self):
        text = self.contract(studies=True)
        for value in ("pending", self.binding(self.study).replace("sha256:", "bad:")):
            with self.subTest(value=value):
                self.write(self.ui, text.replace(self.binding(self.study), value))
                with self.assertRaises(ValueError):
                    build_visual_inputs(self.root, self.ui, "hifi")
        text = self.contract().replace("UI contract: ui-design/2", "UI contract: ui-design/3")
        self.write(self.ui, text)
        with self.assertRaisesRegex(ValueError, "retained study"):
            build_visual_inputs(self.root, self.ui, "hifi")

    def test_initial_direction_permits_explicit_pending_captures_and_studies(self):
        text = self.contract(selected="pending", studies=True)
        for source, value in zip((self.screen, self.other, self.study, self.other_study),
                                 ("pending", "draft", "draft", "pending")):
            text = text.replace(self.binding(source), value)
        self.write(self.ui, text)
        packet = build_visual_inputs(self.root, self.ui, "direction")
        self.assertIn("pending", packet)
        for source in (self.screen, self.other, self.study, self.other_study):
            self.assertNotIn(source, packet)
        with self.assertRaisesRegex(ValueError, "selected direction"):
            build_visual_inputs(self.root, self.ui, "hifi")

    def test_pending_selected_capture_still_blocks_hifi(self):
        text = self.contract().replace(self.binding(self.screen), "pending")
        self.write(self.ui, text)
        with self.assertRaises(ValueError):
            build_visual_inputs(self.root, self.ui, "hifi")

    def test_direction_keeps_recorded_source_checks_with_mixed_pending_rows(self):
        text = self.contract(selected="pending", studies=True).replace(self.binding(self.other), "pending")
        self.write(self.ui, text)
        packet = build_visual_inputs(self.root, self.ui, "direction")
        self.assertIn(self.binding(self.screen), packet)
        self.assertIn(self.binding(self.study), packet)
        self.assertIn("VD-R1-02 capture", packet)
        for source in (self.screen, self.study):
            for fault in ("stale", "malformed"):
                with self.subTest(source=source, fault=fault):
                    text = self.contract(selected="pending", studies=True).replace(self.binding(self.other), "pending")
                    path = self.root / source
                    original = path.read_bytes()
                    if fault == "stale":
                        path.write_bytes(original + b" changed")
                    else:
                        text = text.replace(self.binding(source), "malformed recorded identity")
                    self.write(self.ui, text)
                    with self.assertRaises(ValueError):
                        build_visual_inputs(self.root, self.ui, "direction")
                    path.write_bytes(original)

    def test_implementation_retains_selected_capture_and_complete_hifi(self):
        self.contract(target=True, hifi=True)
        packet = build_visual_inputs(self.root, self.ui, "implementation")
        self.assertIn(self.binding(self.screen), packet)
        self.assertNotIn(self.other, packet)
        self.assertIn(self.binding(self.hifi), packet)
        self.assertIn(self.binding(self.child), packet)
        self.assertIn('"targets": [390, 768, 1200]', packet)
        self.assertIn("- Fonts:", packet)
        self.assertIn("- Assets:", packet)
        self.assertIn("- Visual features:", packet)
        self.assertEqual(packet, build_visual_inputs(self.root, self.ui, "implementation"))

    def test_missing_selection_or_target_blocks_dependent_stage(self):
        self.contract(selected="pending")
        with self.assertRaisesRegex(ValueError, "selected direction"):
            build_visual_inputs(self.root, self.ui, "hifi")
        self.contract()
        with self.assertRaisesRegex(ValueError, "approved target"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_required_legacy_pair_is_transferred_without_redefining_values(self):
        markdown = self.write("docs/design/design-system.md", "# Approved system\n")
        registry = self.write("docs/design/design-system.json", '{"schema":"design-system/3"}')
        text = self.contract(target=True, hifi=True).replace(
            "Decision: not_required", "Decision: required\nCompiled design system pair: "
            + self.binding(markdown) + " and " + self.binding(registry) + "\nPackage action: compile")
        self.write(self.ui, text)
        packet = build_visual_inputs(self.root, self.ui, "implementation")
        for source in (markdown, registry):
            self.assertIn(self.binding(source), packet)
        (self.root / registry).rename(self.root / "preserved-registry.json")
        with self.assertRaisesRegex(ValueError, "missing"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_missing_or_malformed_visual_material_is_blocked(self):
        self.contract(target=True, hifi=True)
        (self.root / self.screen).rename(self.root / "preserved-capture.png")
        with self.assertRaisesRegex(ValueError, "missing"):
            build_visual_inputs(self.root, self.ui, "implementation")
        (self.root / "preserved-capture.png").rename(self.root / self.screen)
        self.write(self.hifi, '<script id="ui-hifi-manifest" type="application/json">[]</script>')
        self.contract(target=True, hifi=True)
        with self.assertRaisesRegex(ValueError, "ui-hifi/2"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_stale_prd_capture_and_child_are_rejected(self):
        for source in (self.prd, self.screen, self.child):
            with self.subTest(source=source):
                self.contract(target=True, hifi=True)
                path = self.root / source
                original = path.read_bytes()
                path.write_bytes(original + b" changed")
                with self.assertRaisesRegex(ValueError, "stale"):
                    build_visual_inputs(self.root, self.ui, "implementation")
                path.write_bytes(original)

    def maintenance_context(self, impact="style"):
        self.contract(target=True, hifi=True, studies=True)
        record = self.write("docs/epics/EPIC-maintenance.md",
                            "Design workflow: maintenance\nUI impact: " + impact + "\n")
        for command in (("init", "-q"), ("config", "core.autocrlf", "false"), ("add", "."),
                        ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                         "commit", "-qm", "retain approved design")):
            subprocess.run(["git", *command], cwd=self.root, check=True,
                           capture_output=True, timeout=15)
        for source in (self.prd, self.architecture, self.stack):
            path = self.root / source
            path.write_bytes(path.read_bytes() + b"Accepted maintenance clarification.\n")
        return record

    def test_maintenance_uses_current_product_and_retains_design_bytes(self):
        for impact in ("none", "style"):
            with self.subTest(impact=impact):
                record = self.maintenance_context(impact)
                before = {str(path): path.read_bytes() for path in (self.root / "docs").rglob("*") if path.is_file()}
                with self.assertRaisesRegex(ValueError, "stale"):
                    build_visual_inputs(self.root, self.ui, "implementation")
                packet = build_visual_inputs(self.root, self.ui, "implementation", task_record=record)
                for source in (self.prd, self.architecture, self.stack, self.hifi, self.study, record):
                    self.assertIn(self.binding(source), packet)
                self.assertIn("historical provenance", packet)
                result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "visual_inputs.py"),
                                         "--repo-root", str(self.root), "--ui-design", self.ui,
                                         "--stage", "implementation", "--task-record", record],
                                        capture_output=True, text=True, encoding="utf-8", timeout=15)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(packet, result.stdout)
                self.assertEqual(before, {str(path): path.read_bytes() for path in (self.root / "docs").rglob("*") if path.is_file()})

    def test_maintenance_context_cannot_relax_design_or_classification_checks(self):
        record = self.maintenance_context()
        valid = (self.root / record).read_text(encoding="utf-8")
        for text in (valid.replace("style", "structure"), valid.replace("style", "both"),
                     valid + "UI impact: none\n", "```\n" + valid + "```\n",
                     valid.replace("maintenance", "initial_design")):
            with self.subTest(text=text):
                self.write(record, text)
                with self.assertRaises(ValueError):
                    build_visual_inputs(self.root, self.ui, "implementation", task_record=record)
        self.write(record, valid)
        with self.assertRaisesRegex(ValueError, "implementation maintenance"):
            build_visual_inputs(self.root, self.ui, "hifi", task_record=record)
        for source in (self.screen, self.study, self.hifi, self.child):
            with self.subTest(source=source):
                path = self.root / source
                original = path.read_bytes()
                path.write_bytes(original + b" changed")
                with self.assertRaisesRegex(ValueError, "stale"):
                    build_visual_inputs(self.root, self.ui, "implementation", task_record=record)
                path.write_bytes(original)

    def test_no_input_bytes_are_written_and_cli_uses_same_packet(self):
        self.contract(target=True, hifi=True)
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "visual_inputs.py"),
                                 "--repo-root", str(self.root), "--ui-design", self.ui,
                                 "--stage", "implementation"], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(build_visual_inputs(self.root, self.ui, "implementation"), result.stdout)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_preview_above_the_read_limit_is_still_checked_against_a_fresh_render(self):
        markdown = self.write("docs/design/design-system.md", "# Approved system\n")
        registry = self.write("docs/design/design-system.json", '{"schema":"design-system/4"}')
        rendered = "<!doctype html>" + "x" * 65536
        preview = self.write("docs/design/design-system-preview.html", rendered)
        text = self.contract(target=True, hifi=True).replace(
            "Decision: not_required", "Decision: required\nCompiled design system pair: "
            + self.binding(markdown) + " and " + self.binding(registry) + "\nPackage action: compile")
        self.write(self.ui, text)
        renderer = types.ModuleType("render_design_system_preview")
        renderer.render_view = lambda registry_bytes, markdown_bytes, root: rendered
        cap = 32768
        with mock.patch.dict(sys.modules, {"render_design_system_preview": renderer}), \
                mock.patch.object(visual_inputs, "MAX_BYTES", cap), \
                mock.patch.object(review_evidence, "MAX_BYTES", cap):
            self.assertGreater((self.root / preview).stat().st_size, cap)
            packet = build_visual_inputs(self.root, self.ui, "implementation")
            self.assertIn("current derived view matches the bound pair and HiFi", packet)
            self.assertIn("  - " + self.binding(preview), packet.split("- Source files:", 1)[1])
            self.write(preview, rendered + "modified")
            with self.assertRaisesRegex(ValueError, "stale or modified"):
                build_visual_inputs(self.root, self.ui, "implementation")

    def link_directory(self, link, target):
        """Symlinks need a privilege on Windows; fall back to a junction."""
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           check=True, capture_output=True, timeout=15)

    def unlink_directory(self, link):
        """A directory symlink is removed with unlink; a Windows junction with rmdir."""
        if os.name != "nt" and os.path.islink(link):
            os.unlink(link)
        else:
            os.rmdir(link)

    def board(self, *names, round_id="R1"):
        folder = "docs/design/directions/" + round_id + "/references/"
        for name in names:
            self.write(folder + name, b"capture " + round_id.encode() + b" " + name.encode())
        return [folder + name for name in sorted(names)]

    def test_reference_board_follows_the_round_of_the_direction_ids(self):
        first = self.board("a.png", round_id="R1")
        second = self.board("b.png", round_id="R2")
        text = self.contract(selected="VD-R2-01 editorial", studies=True).replace("VD-R1-", "VD-R2-")
        self.write(self.ui, text)
        for stage in ("direction", "hifi"):
            with self.subTest(stage=stage):
                line = next(row for row in build_visual_inputs(self.root, self.ui, stage).splitlines()
                            if row.startswith("- Reference board: "))
                self.assertEqual("- Reference board: " + self.binding(second[0]), line)
        # During exploration the studies may span rounds; every referenced round is listed.
        mixed = self.contract(selected="pending", studies=True).replace("VD-R1-02", "VD-R2-02")
        self.write(self.ui, mixed)
        line = next(row for row in build_visual_inputs(self.root, self.ui, "direction").splitlines()
                    if row.startswith("- Reference board: "))
        self.assertEqual("- Reference board: " + "; ".join(self.binding(path) for path in first + second), line)

    def test_unreadable_reference_folder_is_an_error_not_an_empty_board(self):
        self.board("a.png")
        self.contract(studies=True)
        with mock.patch.object(visual_inputs.os, "scandir", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                build_visual_inputs(self.root, self.ui, "hifi")

    def test_reference_folder_with_unreadable_metadata_is_an_error_and_the_cli_exits_two(self):
        self.board("a.png")
        self.contract(studies=True)
        folder = (self.root / "docs/design/directions/R1/references").resolve()
        real_stat = Path.stat

        def denied(path, *args, **kwargs):
            if Path(path) == folder:
                raise PermissionError(13, "metadata denied", str(path))
            return real_stat(path, *args, **kwargs)

        with mock.patch.object(Path, "stat", denied):
            with self.assertRaises(PermissionError):
                build_visual_inputs(self.root, self.ui, "hifi")
            with self.assertRaises(SystemExit) as stopped, mock.patch.object(sys, "stderr", io.StringIO()) as stderr:
                visual_inputs.main(["--repo-root", str(self.root), "--ui-design", self.ui, "--stage", "hifi"])
        self.assertEqual(2, stopped.exception.code)
        self.assertIn("visual inputs blocked", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_reference_board_lists_captures_in_sorted_order_with_hashes(self):
        paths = self.board("b-hero.png", "a-nav.png", "sub/c-detail.jpg")
        self.write("docs/design/directions/R2/references/other-round.png", b"later round")
        for stage, target in (("direction", False), ("hifi", False)):
            with self.subTest(stage=stage):
                self.contract(studies=True, target=target)
                packet = build_visual_inputs(self.root, self.ui, stage)
                line = next(row for row in packet.splitlines() if row.startswith("- Reference board: "))
                self.assertEqual("- Reference board: " + "; ".join(self.binding(path) for path in sorted(paths)), line)
                self.assertNotIn("other-round.png", packet)
                self.assertEqual(packet, build_visual_inputs(self.root, self.ui, stage))

    def test_reference_board_round_comes_from_the_direction_ids_even_when_pending(self):
        paths = self.board("a.png")
        text = self.contract(selected="pending", studies=True)
        for source in (self.screen, self.other, self.study, self.other_study):
            text = text.replace(self.binding(source), "pending")
        self.write(self.ui, text)
        packet = build_visual_inputs(self.root, self.ui, "direction")
        self.assertIn("- Reference board: " + self.binding(paths[0]), packet)

    def test_missing_or_empty_reference_board_is_not_an_error(self):
        self.contract(studies=True)
        for stage in ("direction", "hifi"):
            with self.subTest(layout="missing", stage=stage):
                self.assertIn("- Reference board: none recorded", build_visual_inputs(self.root, self.ui, stage))
        (self.root / "docs/design/directions/R1/references/empty").mkdir(parents=True)
        for stage in ("direction", "hifi"):
            with self.subTest(layout="empty", stage=stage):
                self.assertIn("- Reference board: none recorded", build_visual_inputs(self.root, self.ui, stage))

    def test_reference_board_rejects_linked_entries_and_non_folders(self):
        self.contract(studies=True)
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "stray.png").write_bytes(b"outside the repository")
        self.board("a.png")
        self.link_directory(self.root / "docs/design/directions/R1/references/linked", outside.name)
        with self.assertRaisesRegex(ValueError, "links or reparse points"):
            build_visual_inputs(self.root, self.ui, "hifi")
        self.assertTrue((Path(outside.name) / "stray.png").is_file())
        self.unlink_directory(self.root / "docs/design/directions/R1/references/linked")
        shutil.rmtree(self.root / "docs/design/directions/R1/references")
        self.write("docs/design/directions/R1/references", "not a folder")
        with self.assertRaisesRegex(ValueError, "must be a folder"):
            build_visual_inputs(self.root, self.ui, "direction")

    def test_linked_reference_folder_is_rejected(self):
        self.contract(studies=True)
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "stray.png").write_bytes(b"outside the repository")
        self.link_directory(self.root / "docs/design/directions/R1/references", outside.name)
        with self.assertRaisesRegex(ValueError, "links or reparse points"):
            build_visual_inputs(self.root, self.ui, "hifi")
        self.unlink_directory(self.root / "docs/design/directions/R1/references")

    def test_implementation_stage_ignores_the_reference_board(self):
        self.board("a.png")
        self.contract(target=True, hifi=True)
        packet = build_visual_inputs(self.root, self.ui, "implementation")
        self.assertNotIn("Reference board", packet)
        self.assertNotIn("references/a.png", packet)

    def test_reference_board_cli_matches_the_function_and_writes_nothing(self):
        self.board("a.png")
        self.contract(studies=True)
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "visual_inputs.py"),
                                 "--repo-root", str(self.root), "--ui-design", self.ui,
                                 "--stage", "hifi"], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(build_visual_inputs(self.root, self.ui, "hifi"), result.stdout)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
