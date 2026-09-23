from hifi_review_fixture import add_shell, observations
"""Tests for the UI design contract checker."""

import importlib
import hashlib
import inspect
import json
import io
import re
import sys
import unittest
import tempfile
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
PDB_TESTS = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
if str(PDB_TESTS) not in sys.path:
    sys.path.append(str(PDB_TESTS))
DS_TESTS = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts" / "tests"
if str(DS_TESTS) not in sys.path:
    sys.path.append(str(DS_TESTS))

checker = importlib.import_module("check_ui_design_contract")

A_HASH = hashlib.sha256(b"prd").hexdigest()
B_HASH = hashlib.sha256(b"architecture").hexdigest()
C_HASH = hashlib.sha256(b"stack").hexdigest()
D_HASH = hashlib.sha256(b"wireframes").hexdigest()
E_HASH = hashlib.sha256(b"hifi").hexdigest()
U_HASH = hashlib.sha256(b"ui-design").hexdigest()
EVIDENCE_HASH = "e" * 64
def capture_fixture(color):
    """Synthetic image bytes for validator tests, not product review evidence."""
    output = io.BytesIO()
    Image.new("RGB", (2, 2), color).save(output, format="PNG")
    return output.getvalue()


PRIMARY_CAPTURE = capture_fixture("white")
STRESS_CAPTURE = capture_fixture("black")
PRIMARY_HASH = hashlib.sha256(PRIMARY_CAPTURE).hexdigest()
STRESS_HASH = hashlib.sha256(STRESS_CAPTURE).hexdigest()


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
W5 score: 90
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
Review medium: HTML projection only
Connected HiFi reference: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}

### Direction comparison

| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | Approved home copy and normal data | docs/design/directions/primary.png @ sha256:{PRIMARY_HASH} | Compact primary action hierarchy |
| VD-R1-01 | UI-001 | ready | 1200 | stress | Approved home copy with bounded dense data | docs/design/directions/stress.png @ sha256:{STRESS_HASH} | Dense data stays aligned and readable |

### Required motion evidence

| Intent ID | UI scope / region | Trigger observed | End state observed | Normal-motion evidence | Reduced-motion evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | on entry | Data-flow overlay ends in the approved resting state | PASS — evidence=docs/evidence/motion-normal.json @ sha256:{EVIDENCE_HASH} | PASS — evidence=docs/evidence/motion-reduced.json @ sha256:{EVIDENCE_HASH} | PASS |

### Platform rules

| Platform | Navigation and input | Typography | Icons | Density and layout | Feedback and motion | Native proof | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| web | Sidebar, keyboard and visible focus | Sans text with CJK fallback | Lucide with named fallback | Compact rows with responsive reflow | Functional state feedback | not_applicable | Inspected official font and icon sources with retrieval date |

## HiFi Review

Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}
Impeccable audit: PASS — evidence=docs/evidence/impeccable-audit.json @ sha256:{EVIDENCE_HASH}
UI grading: PASS — evidence=docs/evidence/hifi-grading.json @ sha256:{EVIDENCE_HASH}
HiFi surface check: PASS — evidence=docs/evidence/hifi-browser.json @ sha256:{EVIDENCE_HASH}
HiFi score: 94
H2 score: 95
H4 score: 94
H5 score: 90
H7 score: 90
H8 score: 96
H9 score: 92
HiFi lowest dimension: 88
HiFi blocks or disputes: none

## Visual Approval

Decision: {visual}
Decision owner: Product owner
Decided on: 2026-09-13
Approved target: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; scope=surfaces=[{{"id":"UI-001","route":"/home","states":["ready","updated"],"stackSemantics":{{"platform":"web","renderingModel":"SPA","componentFoundation":"shadcn/ui owned source","stylingMechanism":"Tailwind CSS"}}}}]|routes=["/home"]|states=["ready","updated"]|responsive={{"kind":"viewports","targets":[390,768,1200]}}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser

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


def materialize_publication(root: Path, *, required: bool, legacy_hifi: bool = False, motion_route: str = "CSS-WAAPI", reviewer_version: int = 2) -> tuple[Path, Path, Path, Path, Path, Path | None]:
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
    data = json.loads(json.dumps(data).replace('"generationRoute": "CSS-WAAPI"',
                                             '"generationRoute": ' + json.dumps(motion_route)))
    data["screens"][0]["states"].append({
        "id": "updated", "label": "Updated",
        "treatments": {"R1": {"layout": "Keep the retained input visible", "copy": [
            {"kind": "static", "role": "success status", "text": "Review input retained.",
             "status": "approved", "source": "Owner-approved fixture copy"}
        ]}},
    })
    product_text = product_text.replace("- `states`: ready", "- `states`: ready, updated")
    architecture_text = __import__("test_product_package_checker").release_architecture()
    stack_text = valid_stack()
    product_text, architecture_text, stack_text = __import__(
        "test_product_package_checker"
    ).strictize_approved_package(product_text, architecture_text, stack_text)
    for path, content in (
        (product, product_text),
        (architecture, architecture_text),
        (stack, stack_text),
        (wireframe, render_html(data)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    hifi.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.dumps({
        "schema": "ui-hifi/2",
        "pages": [],
        "interactions": [{"id": control, "source": {"surface": "UI-001", "state": "ready"},
                          "control": control, "kind": "navigate",
                          "destination": {"surface": "UI-001", "state": "ready"}}
                         for control in ("home", "refresh")]
                        + [{"id": "filter", "source": {"surface": "UI-001", "state": "ready"},
                            "control": "filter", "kind": "state",
                            "destination": {"surface": "UI-001", "state": "updated"}}],
        "surfaces": [{
            "id": "UI-001",
            "page": "index.html",
            "route": "/home",
            "states": ["ready", "updated"],
            "responsive": {"kind": "viewports", "targets": [390, 768, 1200]},
            "navigation": ["home"],
            "controls": ["refresh", "filter"],
        }],
    })
    hifi.write_text(
        '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'
        + checker.check_wireframe_html.REQUIRED_HIFI_CSP.replace("navigate-to 'none'", "navigate-to 'self'")
        + '"></head><body><main data-ui-surface="UI-001" data-ui-route="/home"><a class="product-link" data-navigation-id="home" href="index.html">Pages</a><h1>HiFi review surface with meaningful content</h1><a role="button" class="product-link" data-retention-selected aria-selected="true" data-specimen-variant="default" data-specimen-state="default" data-control-id="refresh" href="index.html">Refresh</a><input class="product-input" data-retention-input data-specimen-variant="default" data-specimen-state="default" data-control-id="filter" value="Retained input" aria-label="Filter"><section class="product-feedback" data-specimen-variant="default" data-specimen-state="default">Saved locally.</section><span data-state="ready" data-responsive-target="390"></span><span data-state="ready" data-responsive-target="768"></span><span data-state="ready" data-responsive-target="1200"></span><span data-state="updated" data-responsive-target="390"></span><span data-state="updated" data-responsive-target="768"></span><span data-state="updated" data-responsive-target="1200"></span></main>'
        '<script id="ui-hifi-manifest" type="application/json">' + manifest + "</script></body></html>",
        encoding="utf-8",
    )
    if not legacy_hifi:
        product_html = hifi.read_text(encoding="utf-8")
        if reviewer_version == 3:
            product_html = re.sub(r' data-state="([^"]+)"',
                                  r' data-state="\1" data-hifi-state-view="\1"', product_html)
        hifi.write_text(add_shell(product_html, json.loads(manifest), component_types=("a", "input"), version=reviewer_version), encoding="utf-8")
    if legacy_hifi:
        legacy = json.loads(manifest)
        legacy = {"schema": "ui-hifi/1", "surfaces": [
            {key: value for key, value in row.items() if key != "page"}
            for row in legacy["surfaces"]
        ]}
        hifi.write_text(hifi.read_text(encoding="utf-8").replace(
            manifest, json.dumps(legacy)
        ).replace("navigate-to 'self'", "navigate-to 'none'").replace(
            'href="index.html"', 'href="#home"'
        ), encoding="utf-8")
    captures = root / "docs/design/directions"
    captures.mkdir(parents=True, exist_ok=True)
    (captures / "primary.png").write_bytes(PRIMARY_CAPTURE)
    (captures / "stress.png").write_bytes(STRESS_CAPTURE)
    ui = contract().replace("| CSS-WAAPI |", f"| {motion_route} |")
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
        {"surface": "UI-001", "state": state, "target": str(target)}
        for state in ("ready", "updated") for target in (390, 768, 1200)
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
            output.update(bundle_output(json.loads(manifest), component_types=("a", "input"), version=reviewer_version))
            output["schema"] = "ui-output/2"
            if legacy_hifi:
                output["schema"] = "ui-output/1"
                output.pop("interactions")
                output.pop("reviewer", None)
                output["navigation"] = []
                output["sandbox"]["topNavigation"] = "blocked"
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
    for name, state in (("motion-normal.json", "normal"), ("motion-reduced.json", "reduced-motion")):
        motion_cases = [{"surface": "UI-001", "state": state, "target": str(target)} for target in (390, 768, 1200)]
        output_path = evidence_dir / name.replace(".json", "-output.json")
        output = bundle_output(json.loads(manifest), component_types=("a", "input"), version=reviewer_version)
        output.update({
            "schema": "ui-output/1" if legacy_hifi else "ui-output/2",
            "check": "motion-preview",
            "subject": subject,
            "matrix": {"cases": motion_cases},
            "results": [dict(case, result="PASS") for case in motion_cases],
        })
        if legacy_hifi:
            output.pop("interactions", None)
            output.pop("reviewer", None)
            output["navigation"] = []
            output["sandbox"]["topNavigation"] = "blocked"
        output["motion"] = {
            "intent": "MM-001", "scope": "UI-001 / hero",
            "mode": "normal" if state == "normal" else "reduced",
            "reducedMotion": state != "normal", "asset": None,
            "observations": [
                {"target": str(target), "state": "ready", "trigger": "on entry",
                 "endState": "Data-flow overlay ends in the approved resting state" if state == "normal" else "Static diagram", "fallbackObserved": state != "normal",
                 "samples": [
                     {"atMs": 0, "values": {"opacity": "0" if state == "normal" else "1"}},
                     {"atMs": 100, "values": {"opacity": "0.5" if state == "normal" else "1"}},
                     {"atMs": 200, "values": {"opacity": "1"}},
                 ]}
                for target in (390, 768, 1200)
            ],
        }
        output_path.write_text(json.dumps(output), encoding="utf-8")
        receipt = {
            "tool": "playwright",
            "method": "sandboxed-offline-browser",
            "matrix": {"cases": motion_cases},
            "results": [dict(case, result="PASS") for case in motion_cases],
            "outputArtifact": {"path": output_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()},
            "executedAt": "2020-01-01T00:00:00Z",
        }
        evidence = {
            "schema": "ui-evidence/2",
            "check": "motion-preview",
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


def materialize_hifi_bundle(root):
    """Two real linked pages, with a hash-bound child and product controls."""
    path = root / "index.html"
    surfaces = [
        {"id": surface, "page": page, "route": route, "states": ["ready", "updated"],
         "responsive": {"kind": "viewports", "targets": [390, 1200]},
         "navigation": ["next"], "controls": ["refresh", "filter", "view"]}
        for surface, page, route in (("UI-001", "index.html", "/home"), ("UI-002", "details.html", "/details"))
    ]
    manifest = {"schema": "ui-hifi/2", "pages": [], "surfaces": surfaces, "interactions": []}
    policy = checker.check_wireframe_html.REQUIRED_HIFI_CSP.replace("navigate-to 'none'", "navigate-to 'self'")
    def page(row, other):
        return ('<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="' + policy
                + '"></head><body><main data-ui-surface="' + row["id"] + '" data-ui-route="' + row["route"]
                + '"><h1>Connected product page with real navigation</h1><a class="product-link" data-specimen-variant="default" data-specimen-state="default" data-navigation-id="next" href="' + other["page"]
                + '">Next page</a><button class="product-button" data-specimen-variant="default" data-specimen-state="default" data-control-id="refresh">Refresh</button>'
                + '<input class="product-input" data-retention-input data-specimen-variant="default" data-specimen-state="default" data-control-id="filter" value="Retained input" aria-label="Filter">'
                + '<select class="product-select" data-retention-selected data-specimen-variant="default" data-specimen-state="default" data-control-id="view" aria-label="View"><option value="ready" selected>Ready</option></select>'
                + '<section class="product-feedback" data-specimen-variant="default" data-specimen-state="default">Saved locally.</section>'
                + ''.join('<span data-state="' + state + '" data-responsive-target="' + str(target) + '"></span>' for target in (390, 1200) for state in ("ready", "updated"))
                + '</main></body></html>')
    for source, destination in ((surfaces[0], surfaces[1]), (surfaces[1], surfaces[0])):
        for control, kind, target in (("next", "navigate", destination), ("refresh", "state", source), ("filter", "state", source), ("view", "state", source)):
            manifest["interactions"].append({"id": source["id"] + "-" + control, "source": {"surface": source["id"], "state": "ready"},
                                            "control": control, "kind": kind, "destination": {"surface": target["id"], "state": "updated" if kind == "state" else "ready"}})
    child = root / "details.html"
    child.write_text(add_shell(page(surfaces[1], surfaces[0]), manifest, "details.html"), encoding="utf-8")
    manifest["pages"] = [{"path": "details.html", "sha256": hashlib.sha256(child.read_bytes()).hexdigest()}]
    html = page(surfaces[0], surfaces[1]).replace('</body>', '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + '</script></body>')
    path.write_text(add_shell(html, manifest), encoding="utf-8")
    return path, manifest, {"surfaces": [{key: value for key, value in row.items() if key != "page"} for row in surfaces]}


def bundle_output(manifest, component_types=("button", "input", "select", "a"), version=2):
    output = {"sandbox": {"network": "disabled", "topNavigation": "allowlisted-local-pages", "popups": "blocked", "forms": "blocked"},
              "console": [], "network": [], "navigation": [], "popups": [], "forms": [], "popupAttempts": 0, "formAttempts": 0, "interactions": []}
    surfaces = {row["id"]: row for row in manifest["surfaces"]}
    for action in manifest["interactions"]:
        source = surfaces[action["source"]["surface"]]
        destination = surfaces[action["destination"]["surface"]]
        for target in source["responsive"]["targets"]:
            for trigger in ("click", "keyboard"):
                output["interactions"].append({"id": action["id"], "target": str(target), "trigger": trigger, "source": action["source"],
                                               "destination": action["destination"], "control": action["control"], "visible": True, "focusCorrect": True, "result": "PASS"})
                if action["kind"] == "navigate":
                    output["navigation"].append({"id": action["id"], "target": str(target), "trigger": trigger, "from": source["page"], "to": destination["page"]})
    output["reviewer"] = observations(manifest, component_types, version=version)
    return output


class UiDesignContractTests(unittest.TestCase):
    def test_public_hifi_checker_binds_product_menu_and_tab_panels(self):
        for kind, state_attr, panel in (("menu", "aria-expanded", "menu-panel"),
                                        ("tab", "aria-selected", "tab-panel")):
            for target, state, expected in ((panel, "false", None),
                                            ("missing-panel", "false", "bind an existing panel"),
                                            (panel, "invalid", f"declare {'expanded' if kind == 'menu' else 'selected'} state")):
                with self.subTest(kind=kind, target=target, state=state), tempfile.TemporaryDirectory() as temp:
                    path, _, scope = materialize_hifi_bundle(Path(temp))
                    html = path.read_text(encoding="utf-8")
                    html = html.replace('data-control-id="refresh"',
                                        f'data-control-id="refresh" data-product-{kind} aria-controls="{target}" {state_attr}="{state}"', 1)
                    html = html.replace('</main>', f'<section id="{panel}">Product panel</section></main>', 1)
                    path.write_text(html, encoding="utf-8")
                    problems = []
                    checker._validate_hifi_surface(path, problems, scope)
                    if expected is None:
                        self.assertEqual([], problems)
                    else:
                        self.assertTrue(any(expected in problem for problem in problems), problems)

    def test_bundle_rejects_surfaces_on_the_wrong_page(self):
        for surface in ("UI-001", "UI-999"):
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as temp:
                path, manifest, scope = materialize_hifi_bundle(Path(temp))
                child = path.parent / "details.html"
                child.write_text(child.read_text(encoding="utf-8").replace(
                    "</body>", '<section data-ui-surface="' + surface + '">Extra product surface</section></body>'
                ), encoding="utf-8")
                manifest["pages"][0]["sha256"] = hashlib.sha256(child.read_bytes()).hexdigest()
                path.write_text(checker.HIFI_MANIFEST_RE.sub(
                    lambda _: '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + '</script>',
                    path.read_text(encoding="utf-8")), encoding="utf-8")
                problems = []
                checker._validate_hifi_surface(path, problems, scope)
                self.assertTrue(any("assigned to this page" in problem for problem in problems), problems)

    def test_malformed_bundle_surface_fields_fail_closed_without_scope(self):
        for key, value in (("states", None), ("responsive", []), ("responsive", {"kind": "viewports", "targets": [[]]}), ("navigation", [False]), ("controls", {})):
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as temp:
                path, manifest, _ = materialize_hifi_bundle(Path(temp))
                manifest["surfaces"][0][key] = value
                text = checker.HIFI_MANIFEST_RE.sub(lambda _: '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + '</script>', path.read_text(encoding="utf-8"))
                path.write_text(text, encoding="utf-8")
                problems = []
                checker._validate_hifi_surface(path, problems)
                self.assertTrue(problems)

    def test_bundle_receipt_cannot_downgrade_to_static_schema_one_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest, _ = materialize_hifi_bundle(root)
            subject = {"path": "index.html", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            cases = [{"surface": row["id"], "state": state, "target": str(target)} for row in manifest["surfaces"] for state in row["states"] for target in row["responsive"]["targets"]]
            matrix = {"cases": cases}
            results = [dict(case, result="PASS") for case in cases]
            for legacy in (False, True):
                with self.subTest(legacy=legacy):
                    output = dict(bundle_output(manifest), schema="ui-output/2", check="hifi-browser", subject=subject, matrix=matrix, results=results)
                    if legacy:
                        output["schema"] = "ui-output/1"
                        output.pop("interactions")
                        output.pop("reviewer", None)
                        output["navigation"] = []
                        output["sandbox"]["topNavigation"] = "blocked"
                    output_path = root / "output.json"
                    output_path.write_text(json.dumps(output), encoding="utf-8")
                    evidence = {"schema": "ui-evidence/2", "check": "hifi-browser", "result": "PASS", "reviewedArtifact": subject,
                                "attestation": "human-attested", "owner": "Fixture human owner", "receipt": {
                                    "tool": "playwright", "method": "sandboxed-offline-browser", "matrix": matrix, "results": results,
                                    "outputArtifact": {"path": "output.json", "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}, "executedAt": "2020-01-01T00:00:00Z"}}
                    evidence_path = root / "evidence.json"
                    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                    problems = []
                    checker._resolve_evidence("PASS — evidence=evidence.json @ sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                                              repo_root=root, label="HiFi surface check", problems=problems, expected_artifact="index.html", expected_matrix=matrix)
                    if legacy:
                        self.assertTrue(problems)
                    else:
                        self.assertEqual(problems, [])

    def test_multi_page_hifi_validates_child_hashes_and_product_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest, scope = materialize_hifi_bundle(root)
            problems = []
            checker._validate_hifi_surface(path, problems, scope)
            self.assertEqual(problems, [])
            self.assertEqual(checker._bundle_transcript_findings(bundle_output(manifest), manifest), [])
            child = root / "details.html"
            child.write_text(child.read_text(encoding="utf-8") + '<!-- changed -->', encoding="utf-8")
            problems = []
            checker._validate_hifi_surface(path, problems, scope)
            self.assertTrue(any("stale" in value for value in problems), problems)

    def test_multi_page_hifi_rejects_wrong_link_and_dead_control(self):
        for old, new, error in ((
            'href="details.html"', 'href="index.html"', "declared page"), (
            'href="details.html"', 'href="https://example.test/"', "external"), (
            '</main>', '<button>Unwired tab</button></main>', "needs a navigation/control ID")):
            with self.subTest(new=new), tempfile.TemporaryDirectory() as temp:
                path, _, scope = materialize_hifi_bundle(Path(temp))
                path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
                problems = []
                checker._validate_hifi_surface(path, problems, scope)
                self.assertTrue(any(error in value for value in problems), problems)

    def test_multi_page_hifi_rejects_missing_page_and_path_escape(self):
        for name in ("missing.html", "../outside.html", "/absolute.html", "index.html", "DETAILS.html", "details.html?query=1"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                path, manifest, scope = materialize_hifi_bundle(Path(temp))
                manifest["pages"].append({"path": name, "sha256": "a" * 64})
                html = checker.HIFI_MANIFEST_RE.sub(lambda _: '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + '</script>', path.read_text(encoding="utf-8"))
                path.write_text(html, encoding="utf-8")
                problems = []
                checker._validate_hifi_surface(path, problems, scope)
                self.assertTrue(problems)

    def test_multi_page_evidence_requires_actual_destinations_and_keyboard_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            _, manifest, _ = materialize_hifi_bundle(Path(temp))
            for mutation in ("missing-click", "wrong-target", "hidden", "focus", "extra-navigation", "network", "popup"):
                with self.subTest(mutation=mutation):
                    output = bundle_output(manifest)
                    if mutation == "missing-click":
                        output["interactions"].pop()
                    elif mutation == "wrong-target":
                        output["interactions"][0]["destination"] = {"surface": "UI-001", "state": "ready"}
                    elif mutation == "hidden":
                        output["interactions"][0]["visible"] = False
                    elif mutation == "focus":
                        output["interactions"][0]["focusCorrect"] = False
                    elif mutation == "extra-navigation":
                        output["navigation"].append({"to": "outside.html"})
                    elif mutation == "network":
                        output["network"].append({"url": "https://example.test/"})
                    else:
                        output["popups"].append({"url": "details.html"})
                        output["popupAttempts"] = 1
                    self.assertTrue(checker._bundle_transcript_findings(output, manifest))

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

    def test_required_motion_effects_need_hashed_normal_and_reduced_evidence(self):
        missing = contract().replace("\n### Required motion evidence", "", 1)
        problems = checker.validate_text(missing, require_visual_approved=True)
        self.assertIn("ui-design: Style Integration requires exactly one '### Required motion evidence'", problems)

        static_only = contract().replace(
            "PASS — evidence=docs/evidence/motion-normal.json @ sha256:" + EVIDENCE_HASH,
            "Static poster retained",
        )
        joined = "\n".join(checker.validate_text(static_only, require_visual_approved=True))
        self.assertIn("MM-001 normal-motion evidence must use", joined)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, _, _, wireframe, hifi, _ = materialize_publication(root, required=False)
            ui_path = root / "docs/design/ui-design.md"
            evidence_path = root / "docs/evidence/motion-normal.json"
            output_path = root / "docs/evidence/motion-normal-output.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            output = json.loads(output_path.read_text(encoding="utf-8"))
            evidence["receipt"]["matrix"]["cases"].pop()
            output["matrix"] = evidence["receipt"]["matrix"]
            output["results"] = output["results"][:-1]
            output_path.write_text(json.dumps(output), encoding="utf-8")
            evidence["receipt"]["outputArtifact"]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            new = "evidence=docs/evidence/motion-normal.json @ sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            ui_path.write_text(
                re.sub(r"evidence=docs/evidence/motion-normal\.json @ sha256:[0-9a-f]{64}", new, ui_path.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            problems = checker.validate(
                ui_path, repo_root=root, prd_path=product, wireframes_path=wireframe, hifi_path=hifi,
                require_filled=True, require_wireframe_approved=True, require_visual_approved=True,
            )
            self.assertTrue(any("receipt.matrix must exactly match" in item for item in problems), problems)

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

    def test_stack_semantics_join_rejects_each_executable_mutation(self):
        from test_product_package_checker import valid_stack

        base = {
            "surfaces": [{
                "id": "UI-001",
                "surfaceClass": "hosted_web",
                "stackSemantics": {
                    "platform": "web",
                    "renderingModel": "SPA",
                    "componentFoundation": "shadcn/ui owned source",
                    "stylingMechanism": "Tailwind CSS",
                },
            }]
        }
        problems: list[str] = []
        checker._validate_stack_semantics_join(base, stack_text=valid_stack(), problems=problems)
        self.assertEqual([], problems)
        for key, value in (
            ("platform", "ios"),
            ("renderingModel", "SSR"),
            ("componentFoundation", "Other UI"),
            ("stylingMechanism", "plain CSS"),
        ):
            candidate = json.loads(json.dumps(base))
            candidate["surfaces"][0]["stackSemantics"][key] = value
            findings: list[str] = []
            checker._validate_stack_semantics_join(
                candidate, stack_text=valid_stack(), problems=findings
            )
            self.assertTrue(findings, key)

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

    def test_image_plus_code_motion_requires_retained_media(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, _, _, wireframe, hifi, _ = materialize_publication(root, required=False)
            ui_path = root / "docs/design/ui-design.md"
            ui = ui_path.read_text(encoding="utf-8")
            old_digest = checker.canonical_ui_approval_sha256(ui)
            old_wire_hash = hashlib.sha256(wireframe.read_bytes()).hexdigest()
            wireframe.write_text(wireframe.read_text(encoding="utf-8").replace(
                '"treatment": "motion"', '"treatment": "image + motion"'), encoding="utf-8")
            new_wire_hash = hashlib.sha256(wireframe.read_bytes()).hexdigest()
            ui = ui.replace('| MM-001 | UI-001 / hero | motion |',
                            '| MM-001 | UI-001 / hero | image + motion |').replace(old_wire_hash, new_wire_hash)
            for name in ("wireframe-browser.json", "wireframe-grading.json"):
                path = root / "docs/evidence" / name
                old_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                receipt = json.loads(path.read_text(encoding="utf-8"))
                output_path = root / receipt["receipt"]["outputArtifact"]["path"]
                output_path.write_text(output_path.read_text(encoding="utf-8").replace(
                    old_wire_hash, new_wire_hash), encoding="utf-8")
                receipt["reviewedArtifact"]["sha256"] = new_wire_hash
                receipt["receipt"]["outputArtifact"]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
                path.write_text(json.dumps(receipt), encoding="utf-8")
                ui = ui.replace(old_hash, hashlib.sha256(path.read_bytes()).hexdigest())
            ui = ui.replace(old_digest, checker.canonical_ui_approval_sha256(ui))
            ui_path.write_text(ui, encoding="utf-8")
            problems = checker.validate(ui_path, repo_root=root, prd_path=product,
                wireframes_path=wireframe, hifi_path=hifi, require_filled=True,
                require_wireframe_approved=True, require_visual_approved=True)
            self.assertEqual(problems, [
                f"ui-design: MM-001 {mode} motion evidence: generated or existing media requires a completed asset identity and review"
                for mode in ("normal", "reduced")])

    def test_motion_cannot_use_the_none_route(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, _, _, wireframe, hifi, _ = materialize_publication(
                root, required=False, motion_route="none")
            problems = checker.validate(root / "docs/design/ui-design.md", repo_root=root,
                prd_path=product, wireframes_path=wireframe, hifi_path=hifi, require_filled=True,
                require_wireframe_approved=True, require_visual_approved=True)
            self.assertEqual(list(dict.fromkeys(problems)), [
                "ui-design: MM-001 motion requires an implementation or media route, not none"])

    def test_media_routes_accept_authorized_assets_and_reject_wrong_actions(self):
        for route, provider, action, passes in (
            ("existing asset", "Owner asset library", "reuse", True),
            ("existing asset", "Owner asset library", "generate", False),
            ("Higgsfield", "Higgsfield", "generate", True),
            ("Higgsfield", "Other provider", "generate", False),
            ("authorized provider", "authorized provider", "generate", False),
        ):
            with self.subTest(route=route, provider=provider, action=action), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                product, _, _, wireframe, hifi, _ = materialize_publication(
                    root, required=False, motion_route=route)
                asset_path = root / "docs/evidence/hero.svg"
                asset_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
                asset_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
                ui_path = root / "docs/design/ui-design.md"
                ui = ui_path.read_text(encoding="utf-8")
                old_digest = checker.canonical_ui_approval_sha256(ui)
                for mode in ("normal", "reduced"):
                    receipt_path = root / f"docs/evidence/motion-{mode}.json"
                    old_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    output_path = root / receipt["receipt"]["outputArtifact"]["path"]
                    output = json.loads(output_path.read_text(encoding="utf-8"))
                    output["motion"]["asset"] = {
                        "path": "docs/evidence/hero.svg", "sha256": asset_hash, "review": "approved",
                        "authorization": {"decision": "approved", "owner": "Product owner",
                            "provider": provider, "action": action,
                            "path": "docs/evidence/hero.svg", "sha256": asset_hash}}
                    output_path.write_text(json.dumps(output), encoding="utf-8")
                    receipt["receipt"]["outputArtifact"]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    ui = ui.replace(old_hash, hashlib.sha256(receipt_path.read_bytes()).hexdigest())
                ui = ui.replace(old_digest, checker.canonical_ui_approval_sha256(ui))
                ui_path.write_text(ui, encoding="utf-8")
                problems = checker.validate(ui_path, repo_root=root, prd_path=product,
                    wireframes_path=wireframe, hifi_path=hifi, require_filled=True,
                    require_wireframe_approved=True, require_visual_approved=True)
                if passes:
                    self.assertEqual(problems, [])
                else:
                    expected = (["ui-design: MM-001 requires a concrete generation route, not authorized provider"]
                                if route == "authorized provider" else [])
                    self.assertEqual(list(dict.fromkeys(problems)), expected + [
                        f"ui-design: MM-001 {mode} motion evidence: media authorization must approve the provider action and exact asset"
                        for mode in ("normal", "reduced")])

    def test_motion_semantics_fail_even_with_fresh_hashes(self):
        for mutation in ("generic", "wrong-region", "static", "wrong-preference", "wrong-trigger", "wrong-end-state", "wrong-fallback", "native-tool", "pending-asset", "unbound-asset"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                product, _, _, wireframe, hifi, _ = materialize_publication(root, required=False)
                mode = "reduced" if mutation == "wrong-fallback" else "normal"
                receipt_path = root / f"docs/evidence/motion-{mode}.json"
                output_path = root / f"docs/evidence/motion-{mode}-output.json"
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                old_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
                output = json.loads(output_path.read_text(encoding="utf-8"))
                if mutation == "generic":
                    del output["motion"]
                elif mutation == "wrong-region":
                    output["motion"]["scope"] = "UI-001 / footer"
                elif mutation == "static":
                    for observation in output["motion"]["observations"]:
                        for sample in observation["samples"]:
                            sample["values"] = {"opacity": "1"}
                elif mutation == "wrong-preference":
                    output["motion"]["reducedMotion"] = True
                elif mutation in {"wrong-trigger", "wrong-end-state", "wrong-fallback"}:
                    for observation in output["motion"]["observations"]:
                        observation["trigger" if mutation == "wrong-trigger" else "endState"] = "Hover spinner visible"
                elif mutation == "native-tool":
                    receipt["receipt"]["tool"] = "xcode-simulator"
                else:
                    asset_path = root / "docs/evidence/hero.svg"
                    asset_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
                    asset_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
                    authorization = "pending owner approval" if mutation == "pending-asset" else {
                        "decision": "approved", "owner": "Product owner", "provider": "Example provider",
                        "action": "generate", "path": "docs/evidence/other.svg", "sha256": asset_hash,
                    }
                    output["motion"]["asset"] = {"path": "docs/evidence/hero.svg", "sha256": asset_hash,
                                                "authorization": authorization, "review": "approved"}
                output_path.write_text(json.dumps(output), encoding="utf-8")
                receipt["receipt"]["outputArtifact"]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                ui_path = root / "docs/design/ui-design.md"
                ui = ui_path.read_text(encoding="utf-8")
                old_digest = checker.canonical_ui_approval_sha256(ui)
                ui = ui.replace(old_hash, hashlib.sha256(receipt_path.read_bytes()).hexdigest())
                ui = ui.replace(old_digest, checker.canonical_ui_approval_sha256(ui))
                ui_path.write_text(ui, encoding="utf-8")
                problems = checker.validate(ui_path, repo_root=root, prd_path=product,
                    wireframes_path=wireframe, hifi_path=hifi, require_filled=True,
                    require_wireframe_approved=True, require_visual_approved=True)
                self.assertTrue(problems)
                self.assertTrue(any("motion" in problem for problem in problems), problems)
                self.assertFalse(any("hash mismatch" in problem for problem in problems), problems)
                self.assertFalse(any("replacement ui-design" in problem for problem in problems), problems)

    def test_legacy_hifi_is_readable_but_cannot_pass_visual_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, _, _, wireframe, hifi, _ = materialize_publication(
                root, required=False, legacy_hifi=True,
            )
            inspection = []
            checker._validate_hifi_surface(hifi, inspection)
            self.assertEqual([], inspection)
            problems = checker.validate(
                root / "docs/design/ui-design.md", repo_root=root,
                prd_path=product, wireframes_path=wireframe, hifi_path=hifi,
                require_filled=True, require_wireframe_approved=True,
                require_visual_approved=True,
            )
            self.assertEqual([
                "ui-design: Visual approval requires ui-hifi/2; schema-1 HiFi is inspection-only"
            ], problems)

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

    def test_visual_quality_dimensions_cannot_be_averaged_away(self):
        for dimension, original in (("H5", 90), ("H7", 90), ("H9", 92)):
            for score in (60, 79, 101, "80.0", "PASS"):
                with self.subTest(dimension=dimension, score=score):
                    candidate = contract().replace("HiFi score: 94", "HiFi score: 100")
                    candidate = candidate.replace(f"{dimension} score: {original}", f"{dimension} score: {score}")
                    problems = checker.validate_text(candidate, require_visual_approved=True)
                    self.assertIn(f"ui-design: {dimension} score must be an integer from 80 to 100", problems)

    def test_visual_quality_floor_accepts_boundary_and_requires_each_score(self):
        for dimension, original in (("H5", 90), ("H7", 90), ("H9", 92)):
            with self.subTest(dimension=dimension):
                candidate = contract().replace(f"{dimension} score: {original}", f"{dimension} score: 80")
                self.assertEqual([], checker.validate_text(candidate, require_visual_approved=True))
                missing = candidate.replace(f"{dimension} score: 80\n", "")
                self.assertTrue(any(f"missing '{dimension} score'" in p for p in checker.validate_text(missing, require_visual_approved=True)))
                self.assertEqual([], checker.validate_text(missing, require_wireframe_approved=True))

    def test_two_weak_visual_dimensions_block_a_ninety_one_overall(self):
        candidate = contract().replace("HiFi score: 94", "HiFi score: 91")
        candidate = candidate.replace("H5 score: 90", "H5 score: 60").replace("H7 score: 90", "H7 score: 60")
        problems = checker.validate_text(candidate, require_visual_approved=True)
        for dimension in ("H5", "H7"):
            self.assertIn(f"ui-design: {dimension} score must be an integer from 80 to 100", problems)

    def test_direction_comparison_requires_rendered_matching_cases(self):
        base = contract()
        start = base.index("### Direction comparison")
        end = base.index("## HiFi Review")
        table = base[start:end]
        mutations = {
            "missing": base[:start] + base[end:],
            "duplicate": base[:end] + table + base[end:],
            "outside scope": base.replace("| UI-001 | ready | 390 |", "| UI-099 | ready | 390 |"),
            "wrong target": base.replace("| ready | 390 |", "| ready | 400 |"),
            "no stress": base.replace("| stress |", "| primary |"),
            "missing capture": base.replace(f"docs/design/directions/primary.png @ sha256:{PRIMARY_HASH}", "TBD"),
            "text capture": base.replace("directions/primary.png", "directions/primary.md"),
            "noncanonical capture directory": base.replace("docs/design/directions/primary.png", "docs/evidence/primary.png"),
            "uncompared selection": base.replace("Selected direction: VD-R1-01", "Selected direction: VD-R1-99"),
            "wrong count": base.replace("Direction mode: one recommended direction", "Direction mode: three comparable directions"),
        }
        for name, candidate in mutations.items():
            with self.subTest(name=name):
                problems = checker.validate_text(candidate, require_visual_approved=True)
                self.assertTrue(any("comparison" in p or "compared" in p for p in problems), problems)

    def test_three_directions_compare_the_same_content_and_distinct_captures(self):
        base = contract().replace("Direction mode: one recommended direction", "Direction mode: three comparable directions")
        rows = "\n".join(line for line in base.splitlines() if line.startswith("| VD-R1-01 |"))
        extras = "\n".join(rows.replace("VD-R1-01", f"VD-R1-0{n}")
                           .replace(PRIMARY_HASH, str(n) * 64).replace(STRESS_HASH, str(n + 3) * 64)
                           for n in (2, 3))
        base = base.replace("\n### Required motion evidence", "\n" + extras + "\n\n### Required motion evidence")
        self.assertEqual([], checker.validate_text(base, require_visual_approved=True))
        mixed_case = base.replace("Direction mode: three comparable directions", "Direction mode: Three comparable directions")
        self.assertEqual([], checker.validate_text(mixed_case, require_visual_approved=True))
        for candidate in (
            base.replace("2" * 64, PRIMARY_HASH),
            base.replace("Approved home copy and normal data", "different content", 1),
            base.replace("| VD-R1-02 | UI-001 | ready | 390 |", "| VD-R1-02 | UI-001 | ready | 768 |"),
        ):
            self.assertTrue(any("comparison" in p for p in checker.validate_text(candidate, require_visual_approved=True)))

    def test_direction_capture_hashes_and_paths_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product, _, _, wireframe, hifi, _ = materialize_publication(root, required=False)
            capture = root / "docs/design/directions/primary.png"
            capture.write_bytes(b"changed fixture")
            problems = checker.validate(root / "docs/design/ui-design.md", repo_root=root,
                                        prd_path=product, wireframes_path=wireframe, hifi_path=hifi,
                                        require_visual_approved=True)
            self.assertTrue(any("Direction comparison Screenshot" in p for p in problems), problems)
            style = checker._section(contract(), "## Style Integration")
            style = style.replace("docs/design/directions/primary.png", "../primary.png")
            problems = []
            checker._direction_comparison(style, "Direction mode: one recommended direction", None, problems, repo_root=root)
            self.assertTrue(any("canonical POSIX segments" in p for p in problems), problems)

    def test_design_tables_do_not_ignore_rows_with_optional_outer_pipes(self):
        base = contract()
        for remove in ("left", "right", "both"):
            def strip_outer(row):
                if remove in {"left", "both"}:
                    row = row.lstrip("|").lstrip()
                if remove in {"right", "both"}:
                    row = row.rstrip("|").rstrip()
                return row
            with self.subTest(remove=remove):
                candidate = "\n".join(strip_outer(row) if row.startswith("|") and (
                    row.startswith("| VD-") or row.startswith("| web |")
                ) else row for row in base.splitlines())
                self.assertEqual([], checker.validate_text(candidate, require_visual_approved=True))
                extra_direction = next(row for row in base.splitlines() if row.startswith("| VD-R1-01 |"))
                extra_direction = strip_outer(extra_direction.replace("VD-R1-01", "VD-R1-02"))
                candidate = base.replace("\n### Required motion evidence", "\n" + extra_direction + "\n\n### Required motion evidence")
                self.assertTrue(any("requires exactly 1 directions" in p for p in checker.validate_text(candidate, require_visual_approved=True)))
                extra_platform = next(row for row in base.splitlines() if row.startswith("| web |"))
                extra_platform = strip_outer(extra_platform.replace("| web |", "| ios |"))
                candidate = base.replace("\n## HiFi Review", "\n" + extra_platform + "\n\n## HiFi Review")
                self.assertTrue(any("Platform rules must exactly cover" in p for p in checker.validate_text(candidate, require_visual_approved=True)))

    def test_platform_rules_match_platforms_and_keep_native_proof_separate(self):
        web = checker._section(contract(), "## Style Integration")
        ios_row = "| ios | Native tabs and back; keyboard safe area | system text styles with Dynamic Type | SF Symbols with documented custom fallback | Touch rows | System feedback | required before expansion | Apple HIG inspected 2026-09-13 |\n"
        scope = {"surfaces": [{"stackSemantics": {"platform": platform}} for platform in ("web", "ios")]}
        both = web + ios_row
        problems = []
        checker._platform_rules(both, scope, problems)
        self.assertEqual([], problems)
        mutations = {
            "missing ios": web,
            "duplicate": both + ios_row,
            "extra platform": both + ios_row.replace("| ios |", "| android |"),
            "web typography on ios": both.replace("system text styles with Dynamic Type", "fixed CSS font size"),
            "web icons only": both.replace("SF Symbols with documented custom fallback", "Lucide"),
            "html native claim": both.replace("required before expansion", "verified in HTML"),
            "blank source": both.replace("Apple HIG inspected 2026-09-13", "TBD"),
        }
        for name, style in mutations.items():
            with self.subTest(name=name):
                problems = []
                checker._platform_rules(style, scope, problems)
                self.assertTrue(problems)

    def test_visual_contract_cannot_claim_native_validation_from_html(self):
        candidate = contract().replace("Review medium: HTML projection only", "Review medium: native verified")
        problems = checker.validate_text(candidate, require_visual_approved=True)
        self.assertTrue(any("it is not native verification" in p for p in problems), problems)

    def test_direction_comparison_requires_each_platform(self):
        scope = {"surfaces": [
            {"id": "UI-001", "states": ["ready"], "stackSemantics": {"platform": "web"}, "responsive": {"targets": [390, 1200]}},
            {"id": "UI-IOS", "states": ["ready"], "stackSemantics": {"platform": "ios"}, "responsive": {"targets": ["compact", "regular"]}},
        ]}
        problems = []
        checker._direction_comparison(checker._section(contract(), "## Style Integration"),
                                      "Direction mode: one recommended direction", scope, problems)
        self.assertTrue(any("for platform ios" in p for p in problems), problems)

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

    def test_w5_cannot_be_averaged_away_or_omitted(self):
        for value in ("79", "101", "not scored", ""):
            with self.subTest(value=value):
                candidate = contract().replace("W5 score: 90", f"W5 score: {value}")
                problems = checker.validate_text(candidate, require_wireframe_approved=True)
                self.assertIn("W5 score must be an integer from 80 to 100", "\n".join(problems))
        candidate = contract().replace("W5 score: 90\n", "")
        self.assertIn("W5 score", "\n".join(checker.validate_text(candidate, require_wireframe_approved=True)))

    def test_literal_brackets_inside_a_filled_value_are_allowed(self):
        candidate = contract().replace(
            "Plain synthetic fixture UI",
            "Use the existing [Human] review label in the connected UI",
        )
        self.assertEqual([], checker.validate_text(candidate, require_filled=True))


if __name__ == "__main__":
    unittest.main()
