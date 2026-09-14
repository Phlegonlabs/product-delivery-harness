"""Tests for the UI design contract checker."""

import importlib
import hashlib
import inspect
import json
import re
import sys
import unittest
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
PDB_TESTS = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
if str(PDB_TESTS) not in sys.path:
    sys.path.insert(0, str(PDB_TESTS))
DS_TESTS = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts" / "tests"
if str(DS_TESTS) not in sys.path:
    sys.path.insert(0, str(DS_TESTS))

checker = importlib.import_module("check_ui_design_contract")

A_HASH = hashlib.sha256(b"prd").hexdigest()
B_HASH = hashlib.sha256(b"architecture").hexdigest()
C_HASH = hashlib.sha256(b"stack").hexdigest()
D_HASH = hashlib.sha256(b"wireframes").hexdigest()
E_HASH = hashlib.sha256(b"hifi").hexdigest()
U_HASH = hashlib.sha256(b"ui-design").hexdigest()
EVIDENCE_HASH = "e" * 64


def contract(*, wireframe="approved", visual="approved", author="frontend-design"):
    return f"""# UI Design Contract

## Source Product Definition

PRD source: docs/product/PRD.md @ sha256:{A_HASH}
Architecture source: docs/product/architecture.md @ sha256:{B_HASH}
Stack source: docs/product/stack-decisions.md @ sha256:{C_HASH}
Product Definition Approval: approved
Stack Decision Checkpoint: approved

## UI Design Intake

Decision owner: Product owner
Decided on: 2026-09-13
Visual Preference Brief: Precise, calm, information-dense UI; avoid generic cards
Direction mode: one recommended direction

## Motion And Media Intent

Motion direction: functional_only — Product owner

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | motion | Explain data flow | on entry | A restrained data-flow motion placeholder | owner decision | Static diagram | CSS-WAAPI | approved | deferred |

## Wireframe Approval

Wireframe: docs/design/wireframes.html @ sha256:{D_HASH}
Frozen PRD basis: docs/product/PRD.md @ sha256:{A_HASH}
Copy Freeze: approved
Copy owner: Product owner
Copy locale: en-US
Copy approved on: 2026-09-13
Responsive surface check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:{EVIDENCE_HASH}
UI grading: PASS — evidence=docs/evidence/wireframe-grading.json @ sha256:{EVIDENCE_HASH}
Wireframe score: 90
Wireframe lowest dimension: 90
Wireframe blocks: none
Decision: {wireframe}
Decision owner: Product owner
Decided on: 2026-09-13

## Style Integration

Design author: {author}
Selected direction: VD-R1-01 precise operations
Direction decision: approved
Direction decision owner: Product owner
Direction decided on: 2026-09-13
Candidate theme: blue-gray palette, sans type, compact rhythm
Connected HiFi reference: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}

## HiFi Review

Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}
Impeccable audit: PASS — evidence=docs/evidence/impeccable-audit.json @ sha256:{EVIDENCE_HASH}
UI grading: PASS — evidence=docs/evidence/hifi-grading.json @ sha256:{EVIDENCE_HASH}
HiFi surface check: PASS — evidence=docs/evidence/hifi-browser.json @ sha256:{EVIDENCE_HASH}
HiFi score: 94
H2 score: 95
H4 score: 94
H8 score: 96
HiFi lowest dimension: 88
HiFi blocks or disputes: none

## Visual Approval

Decision: {visual}
Decision owner: Product owner
Decided on: 2026-09-13
Approved target: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; scope=surfaces=[{{"id":"UI-001","route":"/home","states":["ready"]}}]|routes=["/home"]|states=["ready"]|responsive={{"kind":"viewports","targets":[390,768,1200]}}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser

## Design System Need Gate

Decision: not_required
Decision owner: Product owner
Decided on: 2026-09-13
Reason: One surface with a binding all-screens target
Existing design-system pair disposition: none — no prior formal pair; owner=Product owner; decided=2026-09-13
Replacement visual contract when_not_required: target=docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; ui-design=docs/design/ui-design.md @ sha256:{U_HASH}; wireframe=docs/design/wireframes.html @ sha256:{D_HASH}; prd=docs/product/PRD.md @ sha256:{A_HASH}
"""

def wireframe_html(data: object) -> str:
    return (
        '<script id="wireframe-data" type="application/json">'
        + json.dumps(data)
        + "</script>"
    )


def materialize_publication(root: Path, *, required: bool) -> tuple[Path, Path, Path, Path, Path, Path | None]:
    from test_product_package_checker import valid_prd, valid_stack, ui_contract
    from test_wireframe_contract import render_html, wireframe_data

    product = root / "docs/product/PRD.md"
    architecture = root / "docs/product/architecture.md"
    stack = root / "docs/product/stack-decisions.md"
    wireframe = root / "docs/design/wireframes.html"
    hifi = root / "docs/design/ui-references/run-1/index.html"
    ui_design = root / "docs/design/ui-design.md"
    ux = "## UX Requirements\n| ID | User / task | Requirement | Success and failure signal | Evidence status |\n| --- | --- | --- | --- | --- |\n| UX-001 | Delivery owner reviews status | Show fixture completion and recovery actions | Success is visible status; failure is recoverable feedback | approved |\n"
    product_text = valid_prd()
    start = product_text.index("## UX Requirements")
    end = product_text.index("## Data and Integration Requirements", start)
    product_text = product_text[:start] + ux + product_text[end:]
    product_text = product_text.replace("UI design: not_required — fixture is headless", "UI design: pending explicit ui-design-builder request").replace("UI decision owner: n/a for headless", "UI decision owner: Owner")
    approval_end = product_text.index("<!-- product-definition-approval:end -->") + len("<!-- product-definition-approval:end -->")
    product_text = product_text[:approval_end] + "\n" + ui_contract(copy="approved — owner-approved copy") + product_text[approval_end:]
    data = wireframe_data()
    for path, content in (
        (product, product_text),
        (architecture, __import__("test_product_package_checker").release_architecture()),
        (stack, valid_stack()),
        (wireframe, render_html(data)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    hifi.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.dumps({
        "schema": "ui-hifi/1",
        "surfaces": [{
            "id": "UI-001",
            "route": "/home",
            "states": ["ready"],
            "responsive": {"kind": "viewports", "targets": [390, 768, 1200]},
            "navigation": ["home"],
            "controls": ["refresh"],
        }],
    })
    hifi.write_text(
        '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'
        + checker.check_wireframe_html.REQUIRED_HIFI_CSP
        + '"></head><body><main data-ui-surface="UI-001" data-ui-route="/home"><nav data-navigation-id="home">Pages</nav><h1>HiFi review surface with meaningful content</h1><button data-control-id="refresh">Refresh</button><span data-state="ready" data-responsive-target="390"></span><span data-state="ready" data-responsive-target="768"></span><span data-state="ready" data-responsive-target="1200"></span></main>'
        '<script id="ui-hifi-manifest" type="application/json">' + manifest + "</script></body></html>",
        encoding="utf-8",
    )
    ui = contract()
    replacements = {
        A_HASH: hashlib.sha256(product.read_bytes()).hexdigest(),
        B_HASH: hashlib.sha256(architecture.read_bytes()).hexdigest(),
        C_HASH: hashlib.sha256(stack.read_bytes()).hexdigest(),
        D_HASH: hashlib.sha256(wireframe.read_bytes()).hexdigest(),
        E_HASH: hashlib.sha256(hifi.read_bytes()).hexdigest(),
    }
    for old, new in replacements.items():
        ui = ui.replace(old, new)
    evidence_cases = [
        {"surface": "UI-001", "state": "ready", "target": str(target)}
        for target in (390, 768, 1200)
    ]
    evidence_specs = {
        "wireframe-browser.json": "wireframe-browser",
        "wireframe-grading.json": "wireframe-browser-grading",
        "impeccable-critique.json": "hifi-browser-impeccable-critique",
        "impeccable-audit.json": "hifi-browser-impeccable-audit",
        "hifi-grading.json": "hifi-browser-grading",
        "hifi-browser.json": "hifi-browser",
    }
    evidence_dir = root / "docs/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for name, check_name in evidence_specs.items():
        reviewed = "docs/design/wireframes.html" if name.startswith("wireframe") else "docs/design/ui-references/run-1/index.html"
        reviewed_bytes = wireframe.read_bytes() if name.startswith("wireframe") else hifi.read_bytes()
        subject = {"path": reviewed, "sha256": hashlib.sha256(reviewed_bytes).hexdigest()}
        output_path = evidence_dir / (name.replace(".json", "-output.json"))
        output = {
            "schema": "ui-output/1",
            "check": check_name,
            "subject": subject,
            "matrix": {"cases": evidence_cases},
            "results": [dict(case, result="PASS") for case in evidence_cases],
        }
        if check_name == "hifi-browser":
            output.update(
                {
                    "sandbox": {
                        "network": "disabled",
                        "topNavigation": "blocked",
                        "popups": "blocked",
                        "forms": "blocked",
                    },
                    "console": [],
                    "network": [],
                    "navigation": [],
                    "popups": [],
                    "forms": [],
                    "popupAttempts": 0,
                    "formAttempts": 0,
                }
            )
        output_path.write_text(json.dumps(output), encoding="utf-8")
        receipt = {
            "tool": "rubric-grader" if check_name.endswith("grading") else "impeccable" if "impeccable" in check_name else "playwright",
            "method": "rubric-grading" if check_name.endswith("grading") else "impeccable-critique" if "critique" in check_name else "impeccable-audit" if "audit" in check_name else "sandboxed-offline-browser" if check_name == "hifi-browser" else "browser-matrix",
            "matrix": {"cases": evidence_cases},
            "results": [dict(case, result="PASS") for case in evidence_cases],
            "outputArtifact": {"path": output_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()},
            "executedAt": "2020-01-01T00:00:00Z",
        }
        evidence = {
            "schema": "ui-evidence/2",
            "check": check_name,
            "result": "PASS",
            "reviewedArtifact": subject,
            "receipt": receipt,
            "attestation": "human-attested",
            "owner": "Product owner",
        }
        evidence_path = evidence_dir / name
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        ui = ui.replace(
            f"evidence=docs/evidence/{name} @ sha256:{EVIDENCE_HASH}",
            f"evidence=docs/evidence/{name} @ sha256:{hashlib.sha256(evidence_path.read_bytes()).hexdigest()}",
        )
    pair_markdown = pair_registry = None
    if required:
        from test_check_design_system_pair import registry as make_registry
        import check_design_system_pair

        pair_markdown = root / "docs/design/design-system.md"
        pair_registry = root / "docs/design/design-system.json"
        pair_data = make_registry(schema="design-system/2")
        pair_data["stylingMechanism"] = "Tailwind CSS"
        pair_data["stackSemantics"] = {
            "platform": "web",
            "renderingModel": "SPA",
            "componentFoundation": "shadcn/ui owned source",
            "stylingMechanism": "Tailwind CSS",
        }
        pair_data["sourceBindings"] = {
            "prd": {"path": "docs/product/PRD.md", "sha256": replacements[A_HASH]},
            "architecture": {"path": "docs/product/architecture.md", "sha256": replacements[B_HASH]},
            "stack": {"path": "docs/product/stack-decisions.md", "sha256": replacements[C_HASH]},
            "uiDesign": {"path": "docs/design/ui-design.md", "sha256": "0" * 64},
            "wireframe": {"path": "docs/design/wireframes.html", "sha256": replacements[D_HASH]},
            "hifi": {"path": "docs/design/ui-references/run-1/index.html", "sha256": replacements[E_HASH]},
        }
        pair_registry.write_text(json.dumps(pair_data), encoding="utf-8")
        pair_markdown.write_text(check_design_system_pair.replace_generated_contract("# Pair\n", pair_data), encoding="utf-8")
        ui = ui.replace("Decision: not_required", "Decision: required")
        ui = ui.replace(
            "Replacement visual contract when_not_required: target=docs/design/ui-references/run-1/index.html @ sha256:" + replacements[E_HASH] + "; ui-design=docs/design/ui-design.md @ sha256:" + U_HASH + "; wireframe=docs/design/wireframes.html @ sha256:" + replacements[D_HASH] + "; prd=docs/product/PRD.md @ sha256:" + replacements[A_HASH],
            "Compiled design system pair: docs/design/design-system.md @ sha256:" + "0" * 64 + " and docs/design/design-system.json @ sha256:" + "0" * 64,
        )
    ui_design.write_text(ui, encoding="utf-8")
    ui_digest = checker.canonical_ui_approval_sha256(ui_design.read_text(encoding="utf-8"))
    if required:
        pair_data["sourceBindings"]["uiDesign"]["sha256"] = ui_digest
        pair_registry.write_text(json.dumps(pair_data), encoding="utf-8")
        pair_markdown.write_text(check_design_system_pair.replace_generated_contract("# Pair\n", pair_data), encoding="utf-8")
        ui = ui.replace(
            "Compiled design system pair: docs/design/design-system.md @ sha256:" + "0" * 64 + " and docs/design/design-system.json @ sha256:" + "0" * 64,
            "Compiled design system pair: docs/design/design-system.md @ sha256:" + hashlib.sha256(pair_markdown.read_bytes()).hexdigest() + " and docs/design/design-system.json @ sha256:" + hashlib.sha256(pair_registry.read_bytes()).hexdigest(),
        )
        ui_design.write_text(ui, encoding="utf-8")
    else:
        digest = checker.canonical_ui_approval_sha256(ui_design.read_text(encoding="utf-8"))
        ui = ui.replace(U_HASH, digest)
        ui_design.write_text(ui, encoding="utf-8")
    return product, architecture, stack, wireframe, hifi, (pair_markdown, pair_registry) if required else None


class UiDesignContractTests(unittest.TestCase):
    def test_public_validator_has_no_unscoped_pair_bypass_and_preflight_is_exact(self):
        self.assertNotIn("verify_design_system_pair", inspect.signature(checker.validate).parameters)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, architecture, stack, wireframe, hifi, _ = materialize_publication(root, required=False)
            ui = root / "docs/design/ui-design.md"
            text = ui.read_text(encoding="utf-8")
            text = text.replace("Decision: not_required", "Decision: required")
            text = re.sub(
                r"^Replacement visual contract when_not_required:.*$",
                "Compiled design system pair: pending — design-system-compiler",
                text,
                flags=re.MULTILINE,
            )
            ui.write_text(text, encoding="utf-8")
            preflight = checker._validate_for_design_system_preflight(
                ui,
                repo_root=root,
                prd_path=product,
                wireframes_path=wireframe,
                hifi_path=hifi,
            )
            self.assertEqual([], preflight)
            normal = checker.validate(
                ui,
                repo_root=root,
                prd_path=product,
                wireframes_path=wireframe,
                hifi_path=hifi,
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
            self.assertTrue(any("pending pair marker" in item for item in normal))

    def test_not_required_pair_disposition_is_machine_bound_to_existing_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, architecture, stack, wireframe, hifi, _ = materialize_publication(root, required=False)
            pair_dir = root / "docs/design"
            pair_dir.mkdir(parents=True, exist_ok=True)
            (pair_dir / "design-system.md").write_text("retained", encoding="utf-8")
            ui = root / "docs/design/ui-design.md"
            problems = checker.validate(
                ui,
                repo_root=root,
                prd_path=product,
                wireframes_path=wireframe,
                hifi_path=hifi,
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
            self.assertTrue(any("disposition none conflicts" in item for item in problems))

    def test_shared_contract_view_exposes_authority_without_filesystem_io(self):
        view, problems = checker.parse_ui_contract_view(contract())

        self.assertEqual([], problems)
        self.assertEqual(
            "docs/product/PRD.md",
            view["source_identities"]["prd"]["path"],
        )
        self.assertEqual("hosted-browser", view["capture_mode"])
        self.assertEqual("not_required", view["gate_decision"])
        self.assertEqual(
            "docs/design/ui-references/run-1/index.html",
            view["approved_target"]["path"],
        )
        self.assertEqual(view["sources"], view["source_identities"])
        self.assertEqual(view["replacement"], view["gate"]["replacement"])
        self.assertRegex(view["canonical_ui_digest"], r"^[0-9a-f]{64}$")

    def test_hybrid_target_scope_requires_per_surface_release_contract(self):
        self.assertEqual(
            ({"platform-review"}, "sandboxed-offline-browser"),
            checker._receipt_contract("hifi-mixed"),
        )
        target = (
            "docs/design/ui-references/hybrid/index.html @ sha256:"
            + "a" * 64
            + "; scope=surfaces="
            + json.dumps(
                [
                    {
                        "id": "UI-WEB",
                        "route": "/home",
                        "states": ["ready"],
                        "releaseSurface": "web",
                        "surfaceClass": "hosted_web",
                        "captureMode": "hosted-browser",
                        "responsive": {"kind": "viewports", "targets": [390, 768, 1200]},
                    },
                    {
                        "id": "UI-IOS",
                        "route": "/ios-home",
                        "states": ["ready"],
                        "releaseSurface": "ios",
                        "surfaceClass": "ios",
                        "captureMode": "native",
                        "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]},
                    },
                ],
                separators=(",", ":"),
            )
            + "|routes=[\"/home\",\"/ios-home\"]|states=[\"ready\"]|responsive="
            + json.dumps({"kind": "per-surface", "targets": []}, separators=(",", ":"))
            + '|tolerance="exact"|allowedDeviations=[]|captureMode=mixed'
        )
        problems: list[str] = []
        scope = checker._target_scope(target, "Approved target", problems)
        self.assertEqual([], problems)
        self.assertEqual("mixed", scope["captureMode"])
        self.assertEqual("ios", scope["surfaces"][1]["releaseSurface"])

        invalid = target.replace('"releaseSurface":"ios",', "")
        problems = []
        checker._target_scope(invalid, "Approved target", problems)
        self.assertTrue(any("hybrid surfaces require" in item for item in problems))

    def test_full_validate_not_required_publication_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, architecture, stack, wireframe, hifi, _ = materialize_publication(root, required=False)
            ui_design = root / "docs/design/ui-design.md"
            problems = checker.validate(
                ui_design,
                repo_root=root,
                prd_path=product,
                wireframes_path=wireframe,
                hifi_path=hifi,
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
            self.assertEqual([], problems)

    def test_full_validate_required_publication_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, architecture, stack, wireframe, hifi, pair = materialize_publication(root, required=True)
            ui_design = root / "docs/design/ui-design.md"
            problems = checker.validate(
                ui_design,
                repo_root=root,
                prd_path=product,
                wireframes_path=wireframe,
                hifi_path=hifi,
                design_system_markdown_path=pair[0],
                design_system_registry_path=pair[1],
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
            self.assertEqual([], problems)

    def test_complete_visual_contract_passes(self):
        self.assertEqual(
            [],
            checker.validate_text(
                contract(),
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            ),
        )

    def test_wireframe_approval_is_human_and_approved(self):
        problems = checker.validate_text(
            contract(wireframe="blocked").replace(
                "Decision owner: Product owner\nDecided on: 2026-09-13\n\n## Style Integration",
                "Decision owner: AI\nDecided on: later\n\n## Style Integration",
                1,
            ),
            require_filled=True,
            require_wireframe_approved=True,
        )
        joined = "\n".join(problems)
        self.assertIn("Wireframe Approval Decision must be approved", joined)
        self.assertIn("Decision owner must be human", joined)
        self.assertIn("must be a real YYYY-MM-DD date", joined)

    def test_wireframe_approval_requires_copy_freeze_first(self):
        candidate = (
            contract()
            .replace("Copy Freeze: approved", "Copy Freeze: draft")
            .replace("Copy owner: Product owner", "Copy owner: AI")
            .replace("Copy locale: en-US", "Copy locale: not a locale")
            .replace("Copy approved on: 2026-09-13", "Copy approved on: later")
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_wireframe_approved=True)
        )
        self.assertIn("Copy Freeze must be approved", joined)
        self.assertIn("Copy owner must be human", joined)
        self.assertIn("Copy locale must be a BCP 47 locale", joined)
        self.assertIn("Copy approved on must be a real YYYY-MM-DD date", joined)

    def test_visual_contract_requires_frontend_design_and_impeccable(self):
        candidate = contract(author="design-taste-frontend").replace(
            f"Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}\n",
            "",
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Design author must be frontend-design", joined)
        self.assertIn("missing 'Impeccable critique'", joined)

    def test_inactive_markdown_does_not_create_approvals(self):
        candidate = contract().replace(
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
        )
        candidate = candidate.replace(
            "## Visual Approval",
            "<!--\n## Hidden Visual Approval\nDecision: blocked\nDecision owner: AI\nDecided on: 2026-09-13\n-->\n## Visual Approval",
        )
        joined = "\n".join(checker.validate_text(candidate, require_visual_approved=True))
        self.assertNotIn("Visual Approval has duplicate 'Decision' fields", joined)
        self.assertNotIn("Visual Approval Decision must be approved", joined)

    def test_fake_and_inactive_evidence_are_rejected(self):
        candidate = contract().replace(
            "Responsive surface check: PASS", "Responsive surface check: passed"
        )
        candidate = candidate.replace(
            "Impeccable audit: PASS", "<!-- Impeccable audit: PASS -->\nImpeccable audit: not run"
        )
        joined = "\n".join(checker.validate_text(candidate, require_visual_approved=True))
        self.assertIn("Responsive surface check must use", joined)
        self.assertIn("Impeccable audit verdict must use", joined)

    def test_design_system_gate_alternatives_are_exclusive(self):
        required = contract(visual="approved").replace(
            "Decision: not_required", "Decision: required"
        )
        joined = "\n".join(checker.validate_text(required, require_visual_approved=True))
        self.assertIn("missing exactly one compiled pair field", joined)

        both = required.replace(
            "Reason: One surface",
            "Compiled design system pair: docs/design/design-system.md @ "
            + "f" * 64
            + " and docs/design/design-system.json @ "
            + "0" * 64
            + "\nReason: One surface",
        )
        joined = "\n".join(checker.validate_text(both, require_visual_approved=True))
        self.assertIn("must not name a not_required replacement", joined)

    def test_connected_hifi_must_match_approved_target(self):
        candidate = contract().replace(
            "Approved target: docs/design/ui-references/run-1/index.html @ sha256:" + E_HASH,
            "Approved target: docs/design/ui-references/run-2/index.html @ sha256:" + ("f" * 64),
        )
        problems = checker.validate_text(candidate, require_visual_approved=True)
        self.assertTrue(any("Connected HiFi reference must exactly match" in item for item in problems))

    def test_not_required_replacement_is_structured_and_exact(self):
        candidate = contract().replace(
            "Replacement visual contract when_not_required: target=docs/design/ui-references/run-1/index.html @ sha256:" + E_HASH,
            "Replacement visual contract when_not_required: approved target, ui-design.md, wireframes.html, PRD.md",
        )
        problems = checker.validate_text(candidate, require_visual_approved=True)
        self.assertTrue(any("must contain exactly target, ui-design, wireframe, and prd" in item for item in problems))

    def test_structured_pass_requires_hashed_evidence(self):
        candidate = contract().replace(
            "Responsive surface check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:" + EVIDENCE_HASH,
            "Responsive surface check: PASS — complete matrix",
        )
        problems = checker.validate_text(candidate, require_wireframe_approved=True)
        self.assertTrue(any("Responsive surface check must use" in item for item in problems))

    def test_evidence_json_binds_check_artifact_and_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "wireframes.html"
            artifact.write_text("wireframe", encoding="utf-8")
            output = root / "output.json"
            output_json = {
                "schema": "ui-output/1",
                "check": "wireframe-browser",
                "subject": {"path": "wireframes.html", "sha256": hashlib.sha256(b"wireframe").hexdigest()},
                "matrix": {"cases": [{"surface": "UI-001", "state": "ready", "target": "390"}]},
                "results": [{"surface": "UI-001", "state": "ready", "target": "390", "result": "PASS"}],
            }
            output.write_text(json.dumps(output_json), encoding="utf-8")
            evidence = {
                "schema": "ui-evidence/2",
                "check": "wireframe-browser",
                "result": "PASS",
                "reviewedArtifact": {
                    "path": "wireframes.html",
                    "sha256": hashlib.sha256(b"wireframe").hexdigest(),
                },
                "receipt": {
                    "tool": "playwright",
                    "method": "browser-matrix",
                    "matrix": {"cases": [{"surface": "UI-001", "state": "ready", "target": "390"}]},
                    "results": [{"surface": "UI-001", "state": "ready", "target": "390", "result": "PASS"}],
                    "outputArtifact": {
                        "path": "output.json",
                        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    },
                    "executedAt": "2020-01-01T00:00:00Z",
                },
                "attestation": "human-attested",
                "owner": "Product owner",
            }
            evidence_path = root / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            line = "PASS — evidence=evidence.json @ sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            problems: list[str] = []
            checker._resolve_evidence(
                line,
                repo_root=root,
                label="Responsive surface check",
                expected_artifact="wireframes.html",
                problems=problems,
            )
            self.assertEqual([], problems)
            reused: list[str] = []
            checker._resolve_evidence(
                line,
                repo_root=root,
                label="HiFi surface check",
                expected_artifact="wireframes.html",
                problems=reused,
            )
            self.assertTrue(any("check must be hifi-browser" in item for item in reused))

    def test_hifi_surface_rejects_external_and_network_surfaces(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hifi.html"
            manifest = json.dumps({
                "schema": "ui-hifi/1",
                "surfaces": [{
                    "id": "UI-001",
                    "route": "/home",
                    "states": ["ready"],
                    "responsive": {"kind": "viewports", "targets": [390]},
                    "navigation": ["home"],
                    "controls": ["refresh"],
                }],
            })
            path.write_text(
                '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'
                + checker.check_wireframe_html.REQUIRED_HIFI_CSP
                + '"></head><body><nav>Pages</nav><main data-ui-surface="UI-001"><h1>HiFi review surface</h1></main>'
                '<script id="ui-hifi-manifest" type="application/json">' + manifest + "</script></body></html>",
                encoding="utf-8",
            )
            problems: list[str] = []
            checker._validate_hifi_surface(path, problems)
            self.assertEqual([], problems)
            path.write_text(
                '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'
                + checker.check_wireframe_html.REQUIRED_HIFI_CSP
                + '"></head><body><main data-ui-surface="UI-001">Unsafe HiFi</main><base href="https://example.test/"><script id="ui-hifi-manifest" type="application/json">'+manifest+'</script><script>fetch("https://example.test")</script></body></html>',
                encoding="utf-8",
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("active external or executable" in item for item in problems))

    def test_hifi_surface_containers_cannot_be_spoofed_by_global_markers(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hifi.html"
            manifest = json.dumps({
                "schema": "ui-hifi/1",
                "surfaces": [
                    {"id": "UI-001", "route": "/home", "states": ["ready"], "responsive": {"kind": "viewports", "targets": [390]}, "navigation": ["home"], "controls": ["refresh"]},
                    {"id": "UI-002", "route": "/settings", "states": ["ready"], "responsive": {"kind": "viewports", "targets": [390]}, "navigation": ["settings"], "controls": ["save"]},
                ],
            })
            path.write_text(
                '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'
                + checker.check_wireframe_html.REQUIRED_HIFI_CSP
                + '"></head><body><div data-state="ready" data-responsive-target="390">global spoof</div>'
                '<main data-ui-surface="UI-001" data-ui-route="/home" data-navigation-id="home" data-control-id="refresh">Surface one content</main>'
                '<script id="ui-hifi-manifest" type="application/json">' + manifest + "</script></body></html>",
                encoding="utf-8",
            )
            scope = {
                "surfaces": [
                    {"id": "UI-001", "route": "/home", "states": ["ready"]},
                    {"id": "UI-002", "route": "/settings", "states": ["ready"]},
                ],
                "responsive": {"kind": "viewports", "targets": [390]},
            }
            problems: list[str] = []
            checker._validate_hifi_surface(path, problems, scope)
            self.assertTrue(any("UI-002" in item for item in problems))

    def test_hifi_requires_closed_csp_and_offline_safe_url_attributes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hifi.html"
            manifest = json.dumps({
                "schema": "ui-hifi/1",
                "surfaces": [{
                    "id": "UI-001",
                    "route": "/home",
                    "states": ["ready"],
                    "responsive": {"kind": "viewports", "targets": [390]},
                    "navigation": ["home"],
                    "controls": ["refresh"],
                }],
            })

            def render(head: str, body: str) -> None:
                path.write_text(
                    "<!doctype html><html><head>" + head + "</head><body>"
                    + body
                    + '<script id="ui-hifi-manifest" type="application/json">'
                    + manifest
                    + "</script></body></html>",
                    encoding="utf-8",
                )

            valid_meta = (
                '<meta http-equiv="Content-Security-Policy" content="'
                + checker.check_wireframe_html.REQUIRED_HIFI_CSP
                + '">'
            )
            render("", '<main data-ui-surface="UI-001"><h1>Missing CSP</h1></main>')
            problems: list[str] = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("exactly one canonical restrictive CSP" in item for item in problems))

            weakened = checker.check_wireframe_html.REQUIRED_HIFI_CSP.replace(
                "connect-src 'none'", "connect-src https://example.test"
            )
            render(
                '<meta http-equiv="Content-Security-Policy" content="' + weakened + '">',
                '<main data-ui-surface="UI-001"><h1>Weakened CSP</h1></main>',
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("weakened or malformed" in item or "exactly equal" in item for item in problems))

            render(
                valid_meta + valid_meta,
                '<main data-ui-surface="UI-001"><h1>Duplicate CSP</h1></main>',
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("exactly one canonical restrictive CSP" in item for item in problems))

            render(
                valid_meta,
                '<main data-ui-surface="UI-001"><h1>Ping and computed call</h1>'
                '<a href="#ok" ping="https://example.test/ping">Local</a>'
                '<script>globalThis[String.fromCharCode(102,101,116,99,104)]("https://example.test")</script>'
                "</main>",
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("external resources" in item and "ping" in item for item in problems))

            render(
                "",
                '<main data-ui-surface="UI-001"><h1>Computed call without CSP</h1>'
                '<script>globalThis[String.fromCharCode(102,101,116,99,104)]("https://example.test")</script>'
                "</main>",
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("canonical restrictive CSP" in item for item in problems))

            render(
                '<script>globalThis[String.fromCharCode(102,101,116,99,104)]("https://example.test")</script>'
                + valid_meta,
                '<main data-ui-surface="UI-001"><h1>Late CSP after computed network call</h1></main>',
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(
                any("before every script" in item for item in problems),
                problems,
            )

    def test_motion_join_rejects_missing_duplicate_and_mismatch(self):
        intent = {
            "id": "MM-001",
            "scope": "UI-001 / screen",
            "treatment": "motion",
            "purpose": "Explain data flow",
            "trigger": "on entry",
            "reducedMotionFallback": "Static diagram",
            "generationRoute": "CSS-WAAPI",
            "draftPrompt": "A restrained data-flow motion placeholder",
            "source": "owner decision",
            "generationStatus": "deferred",
        }
        row = {"MM-001": intent}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wireframes.html"
            path.write_text(
                wireframe_html({"schema": "wireframes/4", "screens": []}),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("has no wireframe mediaIntent" in item for item in problems))

            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": intent}]}
                ),
                encoding="utf-8",
            )
            self.assertIsNone(checker._join_motion_intents(row, path, problems=[]))

            region_intent = dict(intent, scope="UI-001 / hero")
            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [{"id": "UI-001", "regions": [{"id": "hero", "mediaIntent": region_intent}]}],
                    }
                ),
                encoding="utf-8",
            )
            region_problems: list[str] = []
            checker._join_motion_intents({"MM-001": region_intent}, path, problems=region_problems)
            self.assertEqual([], region_problems)

            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [{"id": "UI-001", "regions": [{"id": "hero", "elements": [{"mediaIntent": intent}]}]}],
                    }
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("attached directly" in item for item in problems))

            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [
                            {"id": "UI-001", "mediaIntent": intent},
                            {"id": "UI-002", "mediaIntent": intent},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("duplicate wireframe mediaIntents" in item for item in problems))

            mismatched = dict(intent, generationRoute="GSAP")
            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": mismatched}]}
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("route authority differs" in item for item in problems))

            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": intent}]}
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents({}, path, problems=problems)
            self.assertTrue(any("has no Motion And Media Intent row" in item for item in problems))

    def test_visual_contract_requires_human_direction_selection(self):
        candidate = (
            contract()
            .replace("Direction decision: approved", "Direction decision: rejected")
            .replace("Direction decision owner: Product owner", "Direction decision owner: AI")
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Direction decision is not approved", joined)
        self.assertIn("Direction decision owner must be human", joined)

    def test_duplicate_approval_fields_are_rejected(self):
        candidate = contract().replace(
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
            "Decision: approved\nDecision: revision_requested\n"
            "Decision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Visual Approval has duplicate 'Decision' fields", joined)

    def test_motion_treatment_is_closed(self):
        candidate = contract().replace("| motion |", "| cinematic |")
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("invalid treatment", joined)

    def test_direction_and_motion_enums_are_closed_and_human_owned(self):
        candidate = (
            contract()
            .replace("Direction mode: one recommended direction", "Direction mode: recommend")
            .replace("Motion direction: functional_only — Product owner", "Motion direction: recommend — AI")
        )
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("Direction mode must be one of", joined)
        self.assertIn("Motion direction must be one of", joined)
        self.assertIn("Motion direction must include a human owner", joined)

    def test_blocked_motion_intent_fails(self):
        candidate = contract().replace("| CSS-WAAPI | approved |", "| CSS-WAAPI | blocked |")
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("has invalid status", joined)

    def test_scores_enforce_wireframe_and_hifi_thresholds(self):
        candidate = (
            contract()
            .replace("Wireframe score: 90", "Wireframe score: 79")
            .replace("H4 score: 94", "H4 score: 89")
            .replace("HiFi blocks or disputes: none", "HiFi blocks or disputes: H7 disputed")
        )
        joined = "\n".join(
            checker.validate_text(
                candidate,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
        )
        self.assertIn("Wireframe score must be an integer from 80 to 100", joined)
        self.assertIn("H4 score must be an integer from 90 to 100", joined)
        self.assertIn("HiFi blocks or disputes must be none", joined)

    def test_literal_brackets_inside_a_filled_value_are_allowed(self):
        candidate = contract().replace(
            "Plain synthetic fixture UI",
            "Use the existing [Human] review label in the connected UI",
        )
        self.assertEqual([], checker.validate_text(candidate, require_filled=True))


if __name__ == "__main__":
    unittest.main()
