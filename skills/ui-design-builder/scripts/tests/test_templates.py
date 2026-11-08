"""The skill's fill-in templates parse with the checkers and carry the named fields."""

import json
import re
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = SKILL_ROOT / "assets" / "templates"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import check_ui_design_contract as checker  # noqa: E402

# Problems about a missing or misshapen heading, field or table, as opposed to an unfilled value.
STRUCTURAL = re.compile(
    r"UI contract marker|heading|is missing '|duplicate '|requires exactly one '|declared columns"
    r"|eleven-column|Stage, Skill, Artifact, Application"
)


def read(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


class UiDesignTemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = read("UI_DESIGN.template.md")

    def test_template_passes_the_checker_structural_parse(self):
        self.assertEqual("ui-design/3", checker.ui_contract_version(self.text))
        self.assertEqual([], checker.validate_text(self.text))

    def test_template_carries_every_heading_field_and_table_the_visual_gate_reads(self):
        mvp = self.text
        for field, value in (("Direction mode", "one recommended direction (mvp)"),
                             ("Direction decision", "deferred to Visual Approval (mvp)")):
            mvp, count = re.subn(rf"^{field}: \[.*\]$", f"{field}: {value}", mvp, flags=re.MULTILINE)
            self.assertEqual(1, count, field)
        for text, profile in ((self.text, None), (mvp, "mvp")):
            with self.subTest(profile=profile):
                problems = checker.validate_text(text, require_visual_approved=True, delivery_profile=profile)
                self.assertTrue(problems)
                self.assertEqual([], [problem for problem in problems if STRUCTURAL.search(problem)])
        for removed in ("Candidate theme:", "### Direction studies", "Covers direction:"):
            with self.subTest(removed=removed):
                broken = mvp.replace(removed, "Removed:")
                problems = checker.validate_text(broken, require_visual_approved=True, delivery_profile="mvp")
                self.assertTrue([problem for problem in problems if STRUCTURAL.search(problem)])


def options(value):
    return {item.strip() for item in value.split("|")}


class DefectLedgerTemplateTests(unittest.TestCase):
    def test_ledger_template_has_the_closed_field_set(self):
        ledger = json.loads(read("UI_DEFECT_LEDGER.template.json"))
        case = {"surface", "state", "target"}
        identity = {"path", "sha256"}
        self.assertEqual({"schema", "candidate", "waves", "families", "carriedRows"}, set(ledger))
        self.assertEqual("ui-defect-ledger/1", ledger["schema"])
        self.assertEqual(identity, set(ledger["candidate"]))
        wave = ledger["waves"][0]
        self.assertEqual({"kind", "inputSha256", "outputSha256", "assessment", "receipts"}, set(wave))
        self.assertEqual({"diagnostic", "re-review", "scoped-1", "scoped-2"}, options(wave["kind"]))
        self.assertEqual(identity, set(wave["assessment"]))
        self.assertEqual(identity, set(wave["receipts"][0]))
        family = ledger["families"][0]
        self.assertEqual({"id", "rootCause", "dimensions", "findingSources", "variants", "cases", "repairObjective",
                          "route", "repairClass", "changedSources", "directConsumers", "acceptanceCases",
                          "earlierAttemptSha256", "status"}, set(family))
        self.assertEqual({"impeccable", "rubric", "browser"}, options(family["findingSources"][0]))
        self.assertEqual({"hifi", "prd"}, options(family["route"]))
        self.assertEqual({"copy", "visual"}, options(family["repairClass"]))
        self.assertEqual({"open", "closed", "advisory", "block"}, options(family["status"]))
        self.assertEqual(case, set(family["cases"][0]))
        self.assertEqual(case, set(family["acceptanceCases"][0]))
        self.assertEqual({"page", "state"}, set(family["directConsumers"][0]))
        carried = ledger["carriedRows"][0]
        self.assertEqual({"case", "sourceReceipt", "pageSha256"}, set(carried))
        self.assertEqual(case, set(carried["case"]))
        self.assertEqual(identity, set(carried["sourceReceipt"]))

    def test_rubric_and_lifecycle_name_the_ledger_path_and_template(self):
        for source in ("references/ui-grading-rubric.md", "references/artifact-lifecycle.md"):
            text = (SKILL_ROOT / source).read_text(encoding="utf-8")
            with self.subTest(source=source):
                self.assertEqual(1, text.count("docs/design/evidence/<run-id>/defect-ledger.json"))
                self.assertIn("(../assets/templates/UI_DEFECT_LEDGER.template.json)", text)


class ReviewPacketTemplateTests(unittest.TestCase):
    def setUp(self):
        text = read("UI_REVIEW_PACKET.template.md")
        self.packet = text.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.blocks = {}
        block = None
        for line in self.packet.splitlines():
            if line and not line.startswith("- "):
                block = line.rstrip(":")
                self.blocks[block] = []
            elif line.startswith("- "):
                self.blocks[block].append(line[2:].split(": ", 1)[0] if ": " in line else line[2:])

    def test_packet_template_has_the_closed_field_set(self):
        self.assertEqual({
            "Assignment": ["Assignment ID", "Attempt", "Role", "Route caps"],
            "Frozen inputs (path @ sha256)": ["PRD", "Architecture", "Stack", "ui-design.md", "HiFi entry",
                                              "HiFi pages", "Selected direction", "Journey map",
                                              "Impeccable authorization"],
            "Scoped re-review only": ["Defect ledger", "Prior candidate", "Source diff", "Direct consumers",
                                      "Closure cases", "Tolerance source"],
            "Return": ["Verdict", "Candidate SHA-256", "Findings", "ui-output/3", "Receipt", "Commands run"],
        }, {name: fields for name, fields in self.blocks.items() if name not in {"Read", "Do not read", "Write scope"}})
        self.assertIn("time <seconds> / turns <n> / max_message_bytes <n>", self.packet)
        self.assertIn("lead grader | Impeccable operator | scoped re-review", self.packet)
        self.assertEqual(["docs/design/evidence/<run-id>/ only"], self.blocks["Write scope"])

    def test_packet_read_lists_are_existing_sections_and_the_rubric_exclusions(self):
        headings = {}
        for line in self.blocks["Read"]:
            if not line.startswith("<ui-design-builder-skill-root>/"):
                self.assertTrue(line.startswith("Impeccable SKILL.md"), line)
                continue
            relative, _, anchor = line.removeprefix("<ui-design-builder-skill-root>/").partition("#")
            path = SKILL_ROOT / relative
            self.assertTrue(path.is_file(), relative)
            if anchor:
                if relative not in headings:
                    headings[relative] = {
                        re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", heading.lstrip("#").strip().lower()))
                        for heading in path.read_text(encoding="utf-8").splitlines() if heading.startswith("#")}
                self.assertIn(anchor, headings[relative], line)
        excluded = [name.strip() for name in self.blocks["Do not read"][0].split(",")]
        for name in excluded:
            self.assertTrue((SKILL_ROOT / "references" / name).is_file(), name)
        rubric = (SKILL_ROOT / "references/ui-grading-rubric.md").read_text(encoding="utf-8")
        self.assertIn("Graders do not read the intake, translation, reference, motion-routing, page-profile or "
                      "enhancement guides", rubric)
        self.assertEqual(6, len(excluded))
        self.assertEqual(2, rubric.count("(../assets/templates/UI_REVIEW_PACKET.template.md)"))
        self.assertNotIn("The repair packet contains", rubric)


if __name__ == "__main__":
    unittest.main()
