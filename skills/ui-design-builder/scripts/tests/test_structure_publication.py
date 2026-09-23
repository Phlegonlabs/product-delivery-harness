"""Synthetic complete packages verify the new gates without inventing product approvals."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

HARNESS_SCRIPTS = Path(__file__).resolve().parents[3] / "delivery-harness" / "scripts"
if str(HARNESS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HARNESS_SCRIPTS))

from test_ui_design_contract import materialize_publication, checker
from test_wireframe_contract import render_html
from review_evidence import build_receipt


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modern_publication(root, *, reviewer_version=3):
    product, architecture, stack, wireframe, hifi, pair = materialize_publication(root, required=False, reviewer_version=reviewer_version)
    ui_path = root / "docs/design/ui-design.md"
    ui_text = ui_path.read_text(encoding="utf-8")
    old_wf = digest(wireframe)
    data = json.loads(checker.check_wireframe_html.DATA_BLOCK_RE.search(wireframe.read_text(encoding="utf-8")).group("data"))
    data.update(schema="wireframes/5", structureStatus="validated", copyInventory={"locale": "en-US"})
    data.pop("approvalStatus")
    data.pop("copyFreeze")
    data["flows"] = []
    actions = []
    operations = []
    for control, trigger, kind, state in (("home", "Home", "page", "ready"), ("refresh", "Refresh", "page", "ready"), ("filter", "Filter", "feedback", "updated")):
        actions.append({"id": control, "label": trigger, "status": "approved", "source": "Synthetic PRD operation"})
        flow = {"from": "UI-001", "sourceState": "ready", "trigger": trigger, "control": control,
                "to": "UI-001" if kind == "page" else "Filter applied", "presentation": kind,
                "destination": {"surface": "UI-001", "state": state}}
        if kind == "feedback":
            flow["feedback"] = {"kind": "static", "role": "success status", "text": "Filter applied", "status": "approved", "source": "Synthetic PRD operation"}
        data["flows"].append(flow)
        operations.append({"id": "OP-" + control, "trigger": trigger, "control": control, "sourceState": "ready",
                           "destination": {"surface": "UI-001", "state": state}, "presentation": kind})
    data["screens"][0]["regions"][0]["actions"] = actions
    data["screens"][0]["regions"][0]["primaryAction"] = "Refresh"
    wireframe.write_text(render_html(data), encoding="utf-8")
    ui_text = ui_text.replace(old_wf, digest(wireframe))
    old_prd = digest(product)
    product.write_text(product.read_text(encoding="utf-8").replace("<!-- ui-surface-contract:end -->",
        "- "+chr(96)+"operations"+chr(96)+": "+json.dumps(operations)+"\n<!-- ui-surface-contract:end -->"), encoding="utf-8")
    from test_product_package_checker import strictize_approved_package
    old_architecture, old_stack = digest(architecture), digest(stack)
    texts = strictize_approved_package(product.read_text(encoding="utf-8"),
                                      architecture.read_text(encoding="utf-8"), stack.read_text(encoding="utf-8"))
    for path, text in zip((product, architecture, stack), texts):
        path.write_text(text, encoding="utf-8")
    ui_text = ui_text.replace(old_prd, digest(product)).replace(old_architecture, digest(architecture)).replace(old_stack, digest(stack))
    start, end = ui_text.index("## Wireframe Approval"), ui_text.index("## Style Integration")
    section = ui_text[start:end].replace("## Wireframe Approval", "## Wireframe Validation")
    section = re.sub(r"^(?:Copy Freeze|Copy owner|Copy approved on|Decision|Decision owner|Decided on):.*\n", "", section, flags=re.M)
    skill_source = root / "docs/design/frontend-design-source/SKILL.md"
    skill_source.parent.mkdir(parents=True, exist_ok=True)
    skill_source.write_text("---\nname: frontend-design\n---\nSynthetic skill source for contract tests.\n", encoding="utf-8")
    section += ("Structure validation: validated\n\n### Frontend Design Usage\n\n"
                f"Frontend Design source: {skill_source.relative_to(root).as_posix()} @ sha256:{digest(skill_source)}\n\n"
                "| Stage | Skill | Artifact | Application |\n| --- | --- | --- | --- |\n")
    for stage, artifact in (("wireframe", wireframe), ("direction", root / "docs/design/directions/primary.png"), ("hifi", hifi)):
        section += f"| {stage} | frontend-design @ sha256:{digest(skill_source)} | {artifact.relative_to(root).as_posix()} @ sha256:{digest(artifact)} | Synthetic application of hierarchy, layout and interaction methods. |\n"
    ui_text = ui_text[:start] + section + "\n" + ui_text[end:]
    ui_text = re.sub(r"^((?:Wireframe|HiFi|W5|H[245789]) score|(?:Wireframe|HiFi) lowest dimension): \d+$", r"\1: 95", ui_text, flags=re.M)
    for receipt_path in (root / "docs/evidence").glob("*.json"):
        if receipt_path.name.endswith("-output.json"):
            continue
        old_receipt_hash = digest(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        out_path = root / receipt["receipt"]["outputArtifact"]["path"]
        output = json.loads(out_path.read_text(encoding="utf-8"))
        subject = output["subject"]
        subject["sha256"] = digest(root / subject["path"])
        output["schema"] = "ui-output/3"
        output["execution"] = {
            "startedAt": "2020-01-01T00:00:00Z", "finishedAt": "2020-01-01T00:00:01Z",
            "tool": receipt["receipt"]["tool"], "method": receipt["receipt"]["method"],
            "environment": {"runtime": "synthetic test fixture"}, "artifacts": [subject] + [
                {"path": artifact.relative_to(root).as_posix(), "sha256": digest(artifact)}
                for artifact in (product, architecture, stack, wireframe)
                if artifact.relative_to(root).as_posix() != subject["path"]],
        }
        if any(word in output["check"] for word in ("grading", "audit", "critique")):
            scores = {("W" if output["check"].startswith("wireframe") else "H") + str(n): 95
                      for n in range(1, 6 if output["check"].startswith("wireframe") else 10)} if "grading" in output["check"] else {}
            captures = []
            for index, case in enumerate(output["matrix"]["cases"]):
                capture = root / "docs/evidence/captures" / f"{out_path.stem}-{index}.json"
                capture.parent.mkdir(parents=True, exist_ok=True)
                capture.write_text(json.dumps({"syntheticFixture": True, "case": case,
                                               "observation": "Fixture state and target capture"}), encoding="utf-8")
                captures.append({"path": capture.relative_to(root).as_posix(), "sha256": digest(capture)})
            output["assessment"] = {"scores": scores, "blocks": [], "observations": [
                dict(case, finding="Synthetic fixture validates current source consistency.", evidence=[captures[index]])
                for index, case in enumerate(output["matrix"]["cases"])]}
        out_path.write_text(json.dumps(output), encoding="utf-8")
        receipt_path.write_text(json.dumps(build_receipt(root, out_path.relative_to(root).as_posix())), encoding="utf-8")
        ui_text = ui_text.replace(old_receipt_hash, digest(receipt_path))
    ui_text = re.sub(r"ui-design=docs/design/ui-design.md @ sha256:[0-9a-f]{64}",
                     "ui-design=docs/design/ui-design.md @ sha256:" + checker.canonical_ui_approval_sha256(ui_text), ui_text)
    ui_path.write_text(ui_text, encoding="utf-8")
    return ui_path, product, wireframe, hifi


class StructurePublicationTests(unittest.TestCase):
    def test_full_new_pipeline_accepts_structure_and_visual_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root)
            self.assertEqual([], checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                hifi_path=hifi, require_filled=True, require_structure_validated=True, require_visual_approved=True))

    def test_harness_and_compiler_use_structure_plus_visual_gates(self):
        from harness_contract_join import full_ui_design_checker_errors_at_paths
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root)
            self.assertEqual([], full_ui_design_checker_errors_at_paths(
                ui, repo_root=root, prd_path=prd, wireframes_path=wf, hifi_path=hifi))
            text = ui.read_text(encoding="utf-8").replace("Decision: not_required", "Decision: required")
            text = re.sub(r"^Replacement visual contract when_not_required:.*$",
                          "Compiled design system pair: pending — design-system-compiler", text, flags=re.M)
            ui.write_text(text, encoding="utf-8")
            self.assertEqual([], checker._validate_for_design_system_preflight(
                ui, repo_root=root, prd_path=prd, wireframes_path=wf, hifi_path=hifi))
            self.assertTrue(checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                hifi_path=hifi, require_structure_validated=True, require_visual_approved=True))

    def test_final_gate_rejects_missing_prd_required_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root)
            data = json.loads(checker.check_wireframe_html.DATA_BLOCK_RE.search(wf.read_text(encoding="utf-8")).group("data"))
            data["flows"] = [row for row in data["flows"] if row["trigger"] != "Home"]
            wf.write_text(render_html(data), encoding="utf-8")
            findings = checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                hifi_path=hifi, require_structure_validated=True, require_visual_approved=True)
            self.assertIn("OP-home", "\n".join(findings))

    def test_new_visual_approval_rejects_historical_version_two_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root, reviewer_version=2)
            findings = checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                hifi_path=hifi, require_structure_validated=True, require_visual_approved=True)
            self.assertIn("reviewer shell version 3", "\n".join(findings))

    def test_changed_frontend_source_snapshot_blocks_current_stage_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root)
            source = root / "docs/design/frontend-design-source/SKILL.md"
            source.write_text(source.read_text(encoding="utf-8") + "Changed source\n", encoding="utf-8")
            findings = checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                hifi_path=hifi, require_structure_validated=True, require_visual_approved=True)
            self.assertIn("Frontend Design source snapshot", "\n".join(findings))

    def test_every_machine_receipt_binds_current_product_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, wf, hifi = modern_publication(root)
            with patch.object(checker, "_resolve_evidence", wraps=checker._resolve_evidence) as resolved:
                self.assertEqual([], checker.validate(ui, repo_root=root, prd_path=prd, wireframes_path=wf,
                    hifi_path=hifi, require_structure_validated=True, require_visual_approved=True))
            calls = {call.kwargs["label"]: call.kwargs for call in resolved.call_args_list}
            for label in ("Responsive surface check", "UI grading", "Impeccable critique",
                          "Impeccable audit", "HiFi surface check", "MM-001 normal motion evidence",
                          "MM-001 reduced motion evidence"):
                self.assertTrue(calls[label]["require_machine"], label)
                inputs = {row["path"] for row in calls[label]["required_inputs"]}
                self.assertIn("docs/product/PRD.md", inputs, label)
                self.assertIn("docs/product/architecture.md", inputs, label)
                self.assertIn("docs/product/stack-decisions.md", inputs, label)
                if label not in {"Responsive surface check", "UI grading"}:
                    self.assertIn("docs/design/wireframes.html", inputs, label)


if __name__ == "__main__":
    unittest.main()
