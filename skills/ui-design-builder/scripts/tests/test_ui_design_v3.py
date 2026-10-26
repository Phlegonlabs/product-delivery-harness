"""ui-design/3 full packages: required design-system package, studies and widths.

Fixture bytes are synthetic validator inputs, never product approvals or browser
observations.
"""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

from test_structure_publication import build_receipt, checker, digest
from test_ui_design_contract import capture_fixture
from test_wireframe_free_publication import current_publication

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts"))
import check_product_package  # noqa: E402

STUDY_AUTHOR = "frontend_worker claude-opus-5-5 attempt-1"


def _study_html(title):
    csp = checker.check_wireframe_html.REQUIRED_HIFI_CSP
    return (f'<!doctype html><html lang="en"><head><meta http-equiv="Content-Security-Policy" content="{csp}">'
            f'<title>{title}</title><style>body{{margin:0;font:16px/1.5 serif}}</style></head>'
            f'<body><main><h1>{title}</h1><p>Synthetic rendered direction study for validator tests.</p></main></body></html>')


def intermediate_receipt(root, text, targets, *, results=None):
    """Synthetic ui-output/3 HiFi browser observation at in-between widths.

    It copies the fixture's HiFi surface observation and changes only its case
    matrix; it is validator input, not an actual browser run.
    """
    surface = re.search(r"^HiFi surface check: PASS — evidence=(\S+) @", text, re.M).group(1)
    source = json.loads((root / surface).read_text(encoding="utf-8"))
    output = json.loads((root / source["receipt"]["outputArtifact"]["path"]).read_text(encoding="utf-8"))
    states = sorted({case["state"] for case in output["matrix"]["cases"]})
    cases = [{"surface": "UI-001", "state": state, "target": target} for target in targets for state in states]
    output["matrix"] = {"cases": cases}
    output["results"] = results or [dict(case, result="PASS") for case in cases]
    out_path = root / "docs/evidence/hifi-intermediate-widths-output.json"
    out_path.write_text(json.dumps(output), encoding="utf-8")
    receipt = root / "docs/evidence/hifi-intermediate-widths.json"
    receipt.write_text(json.dumps(build_receipt(root, out_path.relative_to(root).as_posix())), encoding="utf-8")
    return f"{receipt.relative_to(root).as_posix()} @ sha256:{digest(receipt)}"


def v3_publication(root, *, action="compile", disposition="none"):
    """Derive a ui-design/3 package from the synthetic ui-design/2 fixture."""
    ui, prd, hifi = current_publication(root)
    text = ui.read_text(encoding="utf-8")
    text = text.replace("UI contract: ui-design/2", "UI contract: ui-design/3", 1)
    text = text.replace("Direction mode: one recommended direction", "Direction mode: three comparable directions")
    directions = root / "docs/design/directions/round-1"
    directions.mkdir(parents=True, exist_ok=True)
    rows = ["| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    studies = ["### Direction studies", "",
               "| Direction | Study | Author | Self-check by | Self-check |", "| --- | --- | --- | --- | --- |"]
    palette = (("white", "black"), ("red", "blue"), ("green", "yellow"))
    for number, colors in enumerate(palette, 1):
        direction = f"VD-R1-0{number}"
        for (target, scenario, basis), color in zip(
                (("390", "primary", "Approved home copy and normal data"),
                 ("1200", "stress", "Approved home copy with bounded dense data")), colors):
            capture = directions / f"vd-0{number}-{scenario}.png"
            capture.write_bytes(capture_fixture(color))
            rows.append(f"| {direction} | UI-001 | ready | {target} | {scenario} | {basis} | "
                        f"{capture.relative_to(root).as_posix()} @ sha256:{digest(capture)} | Distinct hierarchy {number} |")
        study = directions / f"vd-0{number}.html"
        study.write_text(_study_html(f"Direction {number}"), encoding="utf-8")
        studies.append(f"| {direction} | {study.relative_to(root).as_posix()} @ sha256:{digest(study)} | "
                       f"{STUDY_AUTHOR} | {STUDY_AUTHOR} | pass |")
    start, end = text.index("### Direction comparison"), text.index("### Required motion evidence")
    text = (text[:start] + "### Direction comparison\n\n" + "\n".join(rows) + "\n\n"
            + "\n".join(studies) + "\n\n" + text[end:])
    evidence = intermediate_receipt(root, text, ("560", "980"))
    text = text.replace("HiFi score:", f"Intermediate width check: PASS — evidence={evidence}\nHiFi score:", 1)
    gate = text.index("## Design System Need Gate")
    head, tail = text[:gate], text[gate:]
    tail = tail.replace("Decision: not_required", "Decision: required", 1)
    tail = re.sub(r"^Existing design-system pair disposition: none", f"Existing design-system pair disposition: {disposition}",
                  tail, flags=re.M)
    tail = re.sub(r"^Replacement visual contract when_not_required:.*$",
                  f"Package action: {action}\nCompiled design system pair: pending — design-system-compiler", tail, flags=re.M)
    ui.write_text(head + tail, encoding="utf-8")
    return ui, prd, hifi


def preflight(ui, root, prd, hifi):
    return checker._validate_for_design_system_preflight(ui, repo_root=root, prd_path=prd,
                                                         wireframes_path=None, hifi_path=hifi)


def width_scope(*, hybrid=False, native=True):
    """Parse a real Approved-target scope before testing the width-specific gate."""
    web = {"id": "UI-001", "route": "/home", "states": ["ready", "updated"],
           "releaseSurface": "web-app", "surfaceClass": "hosted_web", "captureMode": "hosted-browser",
           "responsive": {"kind": "viewports", "targets": [390, 768, 1200]}}
    ios = {"id": "UI-IOS" if hybrid else "UI-001", "route": "/ios-home" if hybrid else "/home",
           "states": ["ready", "updated"], "releaseSurface": "ios-app", "surfaceClass": "ios",
           "captureMode": "native", "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]}}
    surfaces = [web, ios] if hybrid else [ios if native else web]
    responsive = {"kind": "per-surface", "targets": []} if hybrid else surfaces[0]["responsive"]
    capture = "mixed" if hybrid else surfaces[0]["captureMode"]
    source = ("docs/design/ui-references/run-1/index.html @ sha256:" + "a" * 64
              + "; scope=surfaces=" + json.dumps(surfaces, separators=(",", ":"))
              + "|routes=" + json.dumps([row["route"] for row in surfaces], separators=(",", ":"))
              + '|states=["ready","updated"]|responsive=' + json.dumps(responsive, separators=(",", ":"))
              + '|tolerance="exact"|allowedDeviations=[]|captureMode=' + capture)
    findings = []
    scope = checker._target_scope(source, "Approved target", findings)
    if findings:
        raise AssertionError(findings)
    return source, scope


class UiDesignV3Tests(unittest.TestCase):
    def test_native_scope_accepts_only_the_exact_width_exemption(self):
        sentinel = checker.ui_design_v3.INTERMEDIATE_WIDTH_NOT_APPLICABLE
        _, scope = width_scope()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            findings = []
            checker._intermediate_width_evidence(sentinel, scope, root, findings)
            self.assertEqual([], findings)
            for value in (None, "not_applicable", "not_applicable — native app", "PASS"):
                with self.subTest(value=value):
                    findings = []
                    checker._intermediate_width_evidence(value, scope, root, findings)
                    self.assertTrue(findings)
            for invalid in (None, {}, {"surfaces": []},
                            {"surfaces": [{"captureMode": "native"}]},
                            {"captureMode": "mixed", "responsive": scope["responsive"], "surfaces": [{}]}):
                with self.subTest(scope=invalid):
                    findings = []
                    checker._intermediate_width_evidence(sentinel, invalid, root, findings)
                    self.assertIn("requires PASS evidence", "\n".join(findings))

    def test_native_contract_text_keeps_ordinary_hifi_evidence_required(self):
        sentinel = checker.ui_design_v3.INTERMEDIATE_WIDTH_NOT_APPLICABLE
        source, _ = width_scope()
        with tempfile.TemporaryDirectory() as directory:
            ui, _, hifi = v3_publication(Path(directory))
            text = ui.read_text(encoding="utf-8")
            source = source.replace("a" * 64, digest(hifi))
            text = re.sub(r"^Approved target:.*$", "Approved target: " + source, text, flags=re.M)
            text = re.sub(r"^Intermediate width check:.*$", "Intermediate width check: " + sentinel, text, flags=re.M)
            text = re.sub(r"^\| web \|.*$", "| ios | Native tabs and back; keyboard safe area | system text styles with Dynamic Type | SF Symbols with documented custom fallback | Touch rows | System feedback | required before expansion | Apple HIG inspected 2026-09-13 |", text, flags=re.M)
            text = text.replace("| ready | 390 |", "| ready | compact |").replace("| ready | 1200 |", "| ready | regular |")
            self.assertEqual([], checker.validate_text(text, require_filled=True, require_visual_approved=True,
                                                      allow_pending_design_system_pair=True))
            broken = re.sub(r"^HiFi surface check:.*$", "HiFi surface check: not_applicable", text, flags=re.M)
            self.assertIn("HiFi surface check", "\n".join(checker.validate_text(
                broken, require_filled=True, require_visual_approved=True, allow_pending_design_system_pair=True)))

    def test_web_preflight_rejects_the_native_width_exemption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            text = re.sub(r"^Intermediate width check:.*$", "Intermediate width check: " +
                          checker.ui_design_v3.INTERMEDIATE_WIDTH_NOT_APPLICABLE,
                          ui.read_text(encoding="utf-8"), flags=re.M)
            ui.write_text(text, encoding="utf-8")
            self.assertIn("requires PASS evidence", "\n".join(preflight(ui, root, prd, hifi)))

    def test_hybrid_intermediate_receipt_covers_web_intervals_only(self):
        _, scope = width_scope(hybrid=True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, _, _ = v3_publication(root)
            text = ui.read_text(encoding="utf-8")
            subject = re.search(r"^Connected HiFi reference: (.+)$", text, re.M).group(1)
            artifact = subject.split(" @ ", 1)[0]
            for targets, expected in ((("560", "980"), None), (("560",), "between 768px and 1200px"),
                                      (("compact", "regular"), "strictly between")):
                with self.subTest(targets=targets):
                    evidence = intermediate_receipt(root, text, targets)
                    findings = []
                    checker._intermediate_width_evidence("PASS — evidence=" + evidence, scope, root, findings,
                                                        expected_artifact=artifact, expected_check="hifi-browser")
                    if expected is None:
                        self.assertEqual([], findings)
                    else:
                        self.assertIn(expected, "\n".join(findings))
            findings = []
            checker._intermediate_width_evidence(checker.ui_design_v3.INTERMEDIATE_WIDTH_NOT_APPLICABLE,
                                                scope, root, findings)
            self.assertIn("requires PASS evidence", "\n".join(findings))

    def test_full_package_passes_compiler_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            self.assertEqual("ui-design/3", checker.ui_contract_version(ui.read_text(encoding="utf-8")))
            self.assertEqual([], preflight(ui, root, prd, hifi))
            view, findings = checker.parse_ui_contract_view(ui.read_text(encoding="utf-8"))
            self.assertEqual([], findings)
            self.assertEqual("compile", view["gate"]["package_action"])
            # The pending marker never passes the ordinary gate.
            self.assertIn("only valid during the exact compiler preflight", "\n".join(checker.validate(
                ui, repo_root=root, prd_path=prd, hifi_path=hifi, require_visual_approved=True)))

    def test_package_gate_rejects_skips_and_mismatched_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            base = ui.read_text(encoding="utf-8")
            cases = {
                "not_required": (base.replace("Decision: required", "Decision: not_required"),
                                 "requires Design System Need Gate Decision: required"),
                "no action": (re.sub(r"^Package action:.*\n", "", base, flags=re.M), "exactly one Package action"),
                "open action": (base.replace("Package action: compile", "Package action: skip"), "Package action must be one of"),
                "reuse without pair": (base.replace("Package action: compile", "Package action: reuse"),
                                       "Package action reuse requires existing pair disposition retain"),
            }
            for label, (text, expected) in cases.items():
                with self.subTest(label):
                    ui.write_text(text, encoding="utf-8")
                    self.assertIn(expected, "\n".join(preflight(ui, root, prd, hifi)))

    def test_studies_need_three_rendered_directions_by_one_self_checking_author(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            base = ui.read_text(encoding="utf-8")
            rows =[line for line in base.splitlines() if line.startswith("| VD-R1-03 | docs/design/directions")]
            cases = {
                "one mode over three directions": (
                    base.replace("Direction mode: three comparable directions", "Direction mode: one recommended direction"),
                    "Direction comparison requires exactly 1 directions"),
                "other checker": (base.replace(f"{STUDY_AUTHOR} | pass |", "independent reviewer | pass |", 1),
                                  "self-check must be made by its own author"),
                "split authors": (base.replace(rows[0], rows[0].replace(STUDY_AUTHOR, "second author")),
                                  "one frontend author"),
                "failed self-check": (base.replace(f"{STUDY_AUTHOR} | pass |", f"{STUDY_AUTHOR} | blocked |", 1),
                                      "self-check must be pass"),
                "missing study": (base.replace(rows[0] + "\n", ""), "exactly the compared directions"),
                "outside round": (base.replace("docs/design/directions/round-1/vd-01.html", "docs/design/vd-01.html"),
                                  "docs/design/directions/<round>/<name>.html"),
            }
            for label, (text, expected) in cases.items():
                with self.subTest(label):
                    ui.write_text(text, encoding="utf-8")
                    self.assertIn(expected, "\n".join(preflight(ui, root, prd, hifi)))
            ui.write_text(base, encoding="utf-8")
            study = root / "docs/design/directions/round-1/vd-02.html"
            study.write_text(study.read_text(encoding="utf-8") + "<!-- edited -->", encoding="utf-8")
            self.assertIn("Direction study", "\n".join(preflight(ui, root, prd, hifi)))

    def test_explicit_owner_single_direction_needs_matching_rows_and_intake_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            three = ui.read_text(encoding="utf-8")
            ui.write_text(three.replace("Direction mode: three comparable directions",
                                        "Direction mode: THREE Comparable Directions"), encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            others = [line for line in three.splitlines() if re.match(r"\| VD-R1-0[23] \|", line)]
            one = three.replace("Direction mode: three comparable directions", "Direction mode: one recommended direction")
            for line in others:
                one = one.replace(line + "\n", "")
            ui.write_text(one, encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            ui.write_text(one.replace("Direction mode: one recommended direction",
                                      "Direction mode: ONE Recommended Direction"), encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            intake = one.index("## UI Design Intake")
            owner = re.compile(r"^Decision owner: .*$", re.M)
            studies = [line for line in others if "docs/design/directions/round-1/vd-0" in line and ".html" in line]
            cases = {
                "missing owner": (one[:intake] + owner.sub("Decision owner: [human owner]", one[intake:], 1),
                                  "ui-design/3 one recommended direction requires the owner's explicit intake decision"),
                "agent owner": (one[:intake] + owner.sub("Decision owner: AI agent", one[intake:], 1),
                                "ui-design/3 one recommended direction requires the owner's explicit intake decision"),
                "undated decision": (one[:intake] + one[intake:].replace("Decided on:", "Decided on: soon //", 1),
                                     "ui-design/3 one recommended direction requires the owner's explicit intake decision"),
                "unrecorded mode": (one.replace("Direction mode: one recommended direction", "Direction mode:"),
                                    "UI Design Intake Direction mode must be one of"),
                "three mode over one direction": (
                    one.replace("Direction mode: one recommended direction", "Direction mode: three comparable directions"),
                    "Direction comparison requires exactly 3 directions"),
                "mixed-case three mode over one direction": (
                    one.replace("Direction mode: one recommended direction", "Direction mode: THREE Comparable Directions"),
                    "Direction comparison requires exactly 3 directions"),
                "three studies for one direction": (
                    one.replace("| VD-R1-01 | docs/design/directions", "\n".join(studies) + "\n| VD-R1-01 | docs/design/directions", 1),
                    "Direction studies must cover exactly the compared directions"),
            }
            for label, (text, expected) in cases.items():
                with self.subTest(label):
                    self.assertNotEqual(one, text)
                    ui.write_text(text, encoding="utf-8")
                    self.assertIn(expected, "\n".join(preflight(ui, root, prd, hifi)))

    def test_mvp_direction_mode_needs_no_separate_direction_approval_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            three = ui.read_text(encoding="utf-8")
            others = [line for line in three.splitlines() if re.match(r"\| VD-R1-0[23] \|", line)]
            one = three.replace("Direction mode: three comparable directions",
                                "Direction mode: one recommended direction (mvp)")
            for line in others:
                one = one.replace(line + "\n", "")
            ui.write_text(one, encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            joined = "\n".join(checker.validate_text(one, require_filled=True, require_visual_approved=True,
                                                     allow_pending_design_system_pair=True))
            self.assertNotIn("Direction mode must be one of", joined)
            self.assertNotIn("requires the owner's explicit intake decision", joined)

    def test_modified_direction_adds_one_revised_study_to_the_round(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            text = ui.read_text(encoding="utf-8")
            directions = root / "docs/design/directions/round-1"

            def identity(path):
                return f"{path.relative_to(root).as_posix()} @ sha256:{digest(path)}"

            for scenario, color in (("primary", "purple"), ("stress", "orange")):
                capture = directions / f"vd-04-{scenario}.png"
                capture.write_bytes(capture_fixture(color))
                text = text.replace(identity(directions / f"vd-01-{scenario}.png"), identity(capture))
            base_study = directions / "vd-01.html"
            revised = directions / "vd-04.html"
            revised.write_text(_study_html("Direction 1 revised"), encoding="utf-8")
            text = text.replace(identity(base_study), identity(revised))
            self.assertIn("Direction decision: approved", text)
            text = (text.replace("| VD-R1-01 |", "| VD-R1-04 |")
                    .replace("Selected direction: VD-R1-01", "Selected direction: VD-R1-04")
                    .replace("Direction decision: approved", "Direction decision: modified-and-approved"))
            ui.write_text(text, encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            self.assertTrue(base_study.is_file())
            ui.write_text(text.replace("Direction decision: modified-and-approved", "Direction decision: rejected"),
                          encoding="utf-8")
            self.assertIn("Direction decision is not approved", "\n".join(preflight(ui, root, prd, hifi)))

            other_round = root / "docs/design/directions/round-2"
            other_round.mkdir()
            moved = other_round / "vd-04.html"
            moved.write_bytes(revised.read_bytes())
            ui.write_text(text.replace(identity(revised), identity(moved)), encoding="utf-8")
            self.assertIn("must share one docs/design/directions/<round>/ folder",
                          "\n".join(preflight(ui, root, prd, hifi)))

    def test_study_html_must_be_self_contained(self):
        findings = "\n".join(checker.ui_design_v3.study_html_findings(
            _study_html("x").replace("</head>", '<link rel="stylesheet" href="https://cdn.invalid/a.css"></head>'),
            "docs/design/directions/r/x.html"))
        self.assertIn("must not load linked, imported or external resources", findings)

    def test_intermediate_widths_cover_every_adjacent_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            self.assertEqual([], preflight(ui, root, prd, hifi))
            base = ui.read_text(encoding="utf-8")
            field = re.search(r"^Intermediate width check: PASS — evidence=(.+)$", base, re.M).group(1)

            def check(evidence):
                ui.write_text(base.replace(field, evidence), encoding="utf-8")
                return "\n".join(preflight(ui, root, prd, hifi))

            for label, targets, expected in (
                ("gap", ("560",), "between 768px and 1200px"),
                ("edge width", ("390", "980"), "strictly between two adjacent approved widths"),
            ):
                with self.subTest(label):
                    self.assertIn(expected, check(intermediate_receipt(root, base, targets)))
            with self.subTest("failed observation"):
                failed = [{"surface": "UI-001", "state": "ready", "target": "560", "result": "FAIL"}]
                self.assertIn("Intermediate width check evidence must record", check(
                    intermediate_receipt(root, base, ("560", "980"), results=failed)))
            with self.subTest("declared but unobserved width"):
                evidence = intermediate_receipt(root, base, ("560", "980"), results=[
                    {"surface": "UI-001", "state": "ready", "target": "560", "result": "PASS"}])
                receipt = root / "docs/evidence/hifi-intermediate-widths.json"
                data = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual("MISSING", data["result"])
                data["result"] = "PASS"  # a hand-edited summary must not supply coverage
                receipt.write_text(json.dumps(data), encoding="utf-8")
                self.assertIn("must observe exactly its matrix cases",
                              check(f"docs/evidence/hifi-intermediate-widths.json @ sha256:{digest(receipt)}"))
                self.assertTrue(evidence)
            with self.subTest("stale subject"):
                evidence = intermediate_receipt(root, base, ("560", "980"))
                output = root / "docs/evidence/hifi-intermediate-widths-output.json"
                data = json.loads(output.read_text(encoding="utf-8"))
                data["subject"]["sha256"] = "0" * 64
                output.write_text(json.dumps(data), encoding="utf-8")
                self.assertIn("Intermediate width check", check(evidence))
            with self.subTest("hand-written boolean record"):
                legacy = root / "docs/evidence/intermediate-widths.json"
                legacy.write_text(json.dumps({"schema": "ui-intermediate-widths/1", "subject": {}, "cases": [
                    {"surface": "UI-001", "width": 560, "between": [390, 768], "horizontalOverflow": False,
                     "clipping": False, "result": "PASS"}]}), encoding="utf-8")
                self.assertIn("Intermediate width check evidence has an invalid", check(
                    f"docs/evidence/intermediate-widths.json @ sha256:{digest(legacy)}"))
            ui.write_text(re.sub(r"^Intermediate width check:.*\n", "", base, flags=re.M), encoding="utf-8")
            self.assertIn("Intermediate width check must use", "\n".join(preflight(ui, root, prd, hifi)))

    def test_version_family_and_schema_mapping_stay_closed(self):
        self.assertEqual("design-system/4", checker.expected_design_system_schema("ui-design/3"))
        self.assertEqual("design-system/3", checker.expected_design_system_schema("ui-design/2"))
        self.assertEqual("design-system/2", checker.expected_design_system_schema("legacy"))
        with self.assertRaises(ValueError):
            checker.ui_contract_version("# UI Design Contract\n\nUI contract: ui-design/4\n")
        view, _ = checker.parse_ui_contract_view("# UI Design Contract\n\nUI contract: ui-design/2\n")
        self.assertNotIn("package_action", view["gate"])

    def test_product_preflight_accepts_only_known_ui_contracts(self):
        self.assertEqual("ui-design/3", check_product_package.parse_args(
            ["--prd", "p", "--architecture", "a", "--stack-decisions", "s", "--ui-contract", "ui-design/3"]).ui_contract)
        with self.assertRaises(ValueError):
            check_product_package.validate_texts("", "", "", ui_contract="ui-design/9")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, prd, _ = v3_publication(root)
            paths = (prd, root / "docs/product/architecture.md", root / "docs/product/stack-decisions.md")
            self.assertEqual(check_product_package.validate(*paths, require_filled=True, require_approved=True,
                                                            repo_root=root, ui_contract="ui-design/2"),
                             check_product_package.validate(*paths, require_filled=True, require_approved=True,
                                                            repo_root=root, ui_contract="ui-design/3"))


if __name__ == "__main__":
    unittest.main()
