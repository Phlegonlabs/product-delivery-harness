"""Real Product -> UI -> Harness hybrid publication joins."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
UI_TESTS_DIR = Path(__file__).resolve().parents[3] / "ui-design-builder" / "scripts" / "tests"
PDB_TESTS_DIR = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
DS_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts"
DS_TESTS_DIR = Path(__file__).resolve().parents[3] / "design-system-compiler" / "scripts" / "tests"
for candidate in (TESTS_DIR, SCRIPTS_DIR, UI_TESTS_DIR, PDB_TESTS_DIR, DS_SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from harness_contract_join import validate_frozen_contract_joins  # noqa: E402
from manifest_fixtures import valid_plan, valid_run  # noqa: E402
from test_ui_design_contract import bundle_output, materialize_publication  # noqa: E402
from test_product_package_checker import strictize_approved_package  # noqa: E402
from test_wireframe_contract import render_html  # noqa: E402
from check_design_system_pair import replace_generated_contract  # noqa: E402
import check_ui_design_contract  # noqa: E402

for candidate in (UI_TESTS_DIR, PDB_TESTS_DIR, DS_SCRIPTS_DIR):
    while str(candidate) in sys.path:
        sys.path.remove(str(candidate))


class HybridCrossSkillPublicationTests(unittest.TestCase):
    @staticmethod
    def _release_block(surface: str, surface_class: str, suffix: str, provider: str, channel: str, artifact: str) -> str:
        name = f"fixture-{suffix}"
        return f"""
### Release Target: {suffix}-development
- Surface: {surface}
- Surface class: {surface_class}
- Public discoverability: {'yes' if surface_class == 'hosted_web' else 'no'}
- Surface suffix: {suffix}
- Release name: {name}-dev
- Provider: {provider}
- Stage: development
- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha
- Artifact kind: {artifact}
- Signing requirement: {'not required' if surface_class == 'hosted_web' else 'release signing'}
- Exact channel / track: {channel} development
- Submission / promotion / review / manual approval path: candidate checks, owner approval, release
- Availability signal: installed or downloadable and the smoke check passes
- Rollout: staged rollout with owner halt criteria
- Rollback / forward-fix: halt rollout and ship a signed forward-fix

### Release Target: {suffix}-production
- Surface: {surface}
- Surface class: {surface_class}
- Public discoverability: {'yes' if surface_class == 'hosted_web' else 'no'}
- Surface suffix: {suffix}
- Release name: {name}
- Provider: {provider}
- Stage: production
- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha
- Artifact kind: {artifact}
- Signing requirement: {'not required' if surface_class == 'hosted_web' else 'release signing'}
- Exact channel / track: {channel} production
- Submission / promotion / review / manual approval path: candidate checks, owner approval, release
- Availability signal: installed or downloadable and the smoke check passes
- Rollout: staged rollout with owner halt criteria
- Rollback / forward-fix: halt rollout and ship a signed forward-fix
"""

    @classmethod
    def _materialize(cls, root: Path, platform: str) -> dict[str, Path]:
        original_path = list(sys.path)
        try:
            for candidate in (UI_TESTS_DIR, PDB_TESTS_DIR, DS_SCRIPTS_DIR, DS_TESTS_DIR):
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
            product, architecture, stack, wireframe, hifi, pair = materialize_publication(root, required=True)
        finally:
            sys.path[:] = original_path
        second_id = "UI-IOS" if platform == "ios" else "UI-EXT"
        second_route = "/ios-home" if platform == "ios" else "/extension"
        second_class = "ios" if platform == "ios" else "browser_extension"
        second_mode = "native" if platform == "ios" else "browser-extension"
        second_surface = "ios-app" if platform == "ios" else "browser-extension"
        second_targets = ["compact", "regular"] if platform == "ios" else [390, 768, 1200]
        second_kind = "sizeClasses" if platform == "ios" else "viewports"

        prd = product.read_text(encoding="utf-8")
        marker = "<!-- ui-surface-contract:end -->"
        second_prd = f"""
### {second_id} — Secondary surface
- `route`: {second_route}
- `releaseSurface`: {second_surface}
- `surfaceClass`: {second_class}
- `captureMode`: {second_mode}
- Main purpose: Let the owner inspect the secondary hybrid surface.
- Content responsibilities: Show secondary completion data with source, order, format, count, length, and fallback bounds.
- Actions and transitions: Refresh the secondary record, show success feedback, and expose recoverable failure behavior.
- `states`: ready
- `responsive`: {second_kind}: {', '.join(map(str, second_targets))}
- `copy`: approved — owner-approved copy
- Responsive obligations: Never drop status or recovery actions; support keyboard input and long content.
- Accessibility: Preserve headings, labels, focus order, announcements, and meaningful alternative text.
- SEO metadata: n/a — non-public secondary surface.
- Trace IDs: PRD-001, UX-001, ARCH-001, TEST-001
"""
        prd = prd.replace(marker, second_prd + marker)
        product.write_text(prd, encoding="utf-8")

        arch = architecture.read_text(encoding="utf-8")
        arch = arch.replace(
            "Expected deployable surfaces: web-app",
            f"Expected deployable surfaces: web-app, {second_surface}",
        )
        arch = arch.replace(
            "## Observability",
            cls._release_block(
                second_surface,
                second_class,
                "ios" if platform == "ios" else "extension",
                "TestFlight" if platform == "ios" else "Chrome Web Store",
                "App Store" if platform == "ios" else "Chrome Web Store",
                "signed app bundle" if platform == "ios" else "signed extension bundle",
            )
            + "\n## Observability",
        )
        architecture.write_text(arch, encoding="utf-8")
        if platform == "ios":
            mobile_section = """
## Mobile/Desktop Technology Decision
### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why it fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Target operating systems | iOS | Approved | Owner decision | Required native target | Keep store signing current |
| Client strategy | Native | Approved | Owner decision | Platform UI fidelity | Keep native modules bounded |
| Framework | SwiftUI | Approved | Owner decision | iOS target fit | Keep SDK current |
| Toolchain | Xcode | Approved | Owner decision | Store distribution | Signing account remains owner-managed |
| Navigation and state | SwiftUI navigation | Approved | Owner decision | Typed state flow | Preserve deep-link behavior |
| Local persistence | SQLite | Approved | Owner decision | Offline notes | Migrations are tested |
| Secure storage | Keychain | Approved | Owner decision | Local secrets | No secret values in repo |
| Offline sync | n/a — local-only fixture | Approved | Owner decision | No sync scope | Revisit if backend sync is added |
| Push and native modules | n/a — no push scope | Approved | Owner decision | No push scope | Revisit with a PRD delta |
| Backend/API integration | n/a — local-only fixture | Approved | Owner decision | No API scope | Revisit with a PRD delta |
| Distribution mechanism | App Store | Approved | Owner decision | Named production channel | Store review is manual |
| Testing | XCTest | Approved | Owner decision | Native coverage | Keep smoke matrix current |
| Styling approach | platform theme | Approved | Owner decision | Uses native platform styling | Keep platform tokens current |
"""
            arch_stack = stack.read_text(encoding="utf-8")
            arch_stack = arch_stack.replace(
                "| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |",
                "| OPT-FE-02 | Frontend | Astro islands bundle | Content-led app | Team owns integrations | rejected |\n"
                "| OPT-MOB-01 | Mobile or desktop | Native SwiftUI iOS bundle | iOS companion | Owner maintains native client | approved |\n"
                "| OPT-MOB-02 | Mobile or desktop | Flutter bundle | Multi-platform reach | Adds cross-platform runtime | rejected |",
            )
            mobile_start = arch_stack.find("## Mobile/Desktop Technology Decision")
            mobile_end = arch_stack.find("\n## ", mobile_start + 1)
            if mobile_start >= 0:
                if mobile_end < 0:
                    mobile_end = len(arch_stack)
                arch_stack = arch_stack[:mobile_start] + mobile_section.lstrip("\n") + arch_stack[mobile_end:]
            else:
                backend_start = arch_stack.find("## Backend and Data Technology Decision")
                arch_stack = arch_stack[:backend_start] + mobile_section.lstrip("\n") + "\n" + arch_stack[backend_start:]
            stack.write_text(arch_stack, encoding="utf-8")
        else:
            # Browser-extension hybrids remain on the approved browser stack.
            pass

        refreshed_prd, refreshed_architecture, refreshed_stack = strictize_approved_package(
            product.read_text(encoding="utf-8"),
            architecture.read_text(encoding="utf-8"),
            stack.read_text(encoding="utf-8"),
        )
        product.write_text(refreshed_prd, encoding="utf-8")
        architecture.write_text(refreshed_architecture, encoding="utf-8")
        stack.write_text(refreshed_stack, encoding="utf-8")

        data = json.loads(re.search(r'<script id="wireframe-data" type="application/json">([\s\S]*?)</script>', wireframe.read_text(encoding="utf-8")).group(1))
        second_screen = copy.deepcopy(data["screens"][0])
        second_screen["id"] = second_id
        second_screen["name"] = "Secondary surface"
        second_screen["route"] = second_route
        for region in second_screen.get("regions", []):
            region["id"] = str(region.get("id", "R1")).replace("UI-001", second_id)
        region_ids = [region["id"] for region in second_screen.get("regions", [])]
        second_screen["neverDrop"] = region_ids
        if platform == "ios":
            second_screen["responsiveLayouts"] = {
                target: copy.deepcopy(next(iter(second_screen["responsiveLayouts"].values())))
                for target in second_targets
            }
        else:
            second_screen["responsiveLayouts"] = {
                target: copy.deepcopy(second_screen["responsiveLayouts"][str(target)])
                for target in second_targets
            }
        data["screens"].append(second_screen)
        data.setdefault("flows", []).append(copy.deepcopy(data["flows"][0]))
        data["flows"][-1]["from"] = second_id
        data.pop("viewports", None)
        data.pop("canvasWidths", None)
        data["responsiveBySurface"] = {
            "UI-001": {
                "kind": "viewports",
                "targets": [390, 768, 1200],
                "canvasWidths": {"390": 390, "768": 768, "1200": 1200},
            },
            second_id: {
                "kind": second_kind,
                "targets": second_targets,
                "canvasWidths": (
                    {"compact": 390, "regular": 768}
                    if platform == "ios"
                    else {"390": 390, "768": 768, "1200": 1200}
                ),
            },
        }
        wireframe.write_text(render_html(data), encoding="utf-8")

        hifi_text = hifi.read_text(encoding="utf-8")
        manifest_match = re.search(r'<script id="ui-hifi-manifest" type="application/json">([\s\S]*?)</script>', hifi_text)
        manifest = json.loads(manifest_match.group(1))
        manifest["surfaces"].append({
            "id": second_id,
            "page": "index.html",
            "route": second_route,
            "states": ["ready"],
            "responsive": {"kind": second_kind, "targets": second_targets},
            "navigation": ["home"],
            "controls": ["refresh"],
        })
        manifest["interactions"].extend({
            "id": second_id + "-" + control,
            "source": {"surface": second_id, "state": "ready"},
            "control": control, "kind": "navigate",
            "destination": {"surface": second_id, "state": "ready"},
        } for control in ("home", "refresh"))
        second_dom = (
            f'<main data-ui-surface="{second_id}" data-ui-route="{second_route}">'
            f'<a data-navigation-id="home" href="index.html">Pages</a><h1>Secondary hybrid surface with meaningful content</h1>'
            f'<a role="button" data-control-id="refresh" href="index.html">Refresh</a>'
            + "".join(f'<span data-state="ready" data-responsive-target="{target}"></span>' for target in second_targets)
            + "</main>"
        )
        hifi_text = hifi_text.replace('<script id="ui-hifi-manifest"', second_dom + '<script id="ui-hifi-manifest"')
        hifi_text = re.sub(
            r'(<script id="ui-hifi-manifest" type="application/json">)[\s\S]*?(</script>)',
            lambda match: match.group(1) + json.dumps(manifest) + match.group(2),
            hifi_text,
        )
        hifi.write_text(hifi_text, encoding="utf-8")

        evidence_cases = [
            {"surface": "UI-001", "state": "ready", "target": str(target)}
            for target in (390, 768, 1200)
        ] + [
            {"surface": second_id, "state": "ready", "target": str(target)}
            for target in second_targets
        ]
        evidence_specs = {
            "wireframe-browser.json": "wireframe-mixed",
            "wireframe-grading.json": "wireframe-mixed-grading",
            "impeccable-critique.json": "hifi-mixed-impeccable-critique",
            "impeccable-audit.json": "hifi-mixed-impeccable-audit",
            "hifi-grading.json": "hifi-mixed-grading",
            "hifi-browser.json": "hifi-mixed",
        }
        evidence_dir = root / "docs/evidence"
        for name, check_name in evidence_specs.items():
            is_wireframe = name.startswith("wireframe")
            reviewed_path = wireframe if is_wireframe else hifi
            reviewed = {
                "path": reviewed_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(reviewed_path.read_bytes()).hexdigest(),
            }
            evidence_path = evidence_dir / name
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["check"] = check_name
            evidence["reviewedArtifact"] = reviewed
            receipt = evidence["receipt"]
            receipt["tool"] = "rubric-grader" if check_name.endswith("grading") else "impeccable" if "impeccable" in check_name else "platform-review"
            receipt["method"] = "rubric-grading" if check_name.endswith("grading") else "impeccable-critique" if "critique" in check_name else "impeccable-audit" if "audit" in check_name else "sandboxed-offline-browser" if check_name == "hifi-mixed" else "mixed-platform-matrix"
            receipt["matrix"] = {"cases": evidence_cases}
            receipt["results"] = [dict(case, result="PASS") for case in evidence_cases]
            output_path = root / receipt["outputArtifact"]["path"]
            output = json.loads(output_path.read_text(encoding="utf-8"))
            if receipt["method"] != "sandboxed-offline-browser":
                for key in ("sandbox", "console", "network", "navigation"):
                    output.pop(key, None)
            else:
                output.update(bundle_output(manifest))
                output["schema"] = "ui-output/2"
            output.update({"check": check_name, "subject": reviewed, "matrix": receipt["matrix"], "results": receipt["results"]})
            output_path.write_text(json.dumps(output), encoding="utf-8")
            receipt["outputArtifact"]["sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        ui = root / "docs/design/ui-design.md"
        ui_text = ui.read_text(encoding="utf-8")
        scope_surfaces = [
            {"id": "UI-001", "route": "/home", "states": ["ready"], "releaseSurface": "web-app", "surfaceClass": "hosted_web", "captureMode": "hosted-browser", "responsive": {"kind": "viewports", "targets": [390, 768, 1200]}, "stackSemantics": {"platform": "web", "renderingModel": "SPA", "componentFoundation": "shadcn/ui owned source", "stylingMechanism": "Tailwind CSS"}},
            {"id": second_id, "route": second_route, "states": ["ready"], "releaseSurface": second_surface, "surfaceClass": second_class, "captureMode": second_mode, "responsive": {"kind": second_kind, "targets": second_targets}, "stackSemantics": {"platform": "ios" if platform == "ios" else "web", "renderingModel": "Native" if platform == "ios" else "SPA", "componentFoundation": "SwiftUI" if platform == "ios" else "shadcn/ui owned source", "stylingMechanism": "platform theme" if platform == "ios" else "Tailwind CSS"}},
        ]
        target_scope = (
            f"Approved target: docs/design/ui-references/run-1/index.html @ sha256:{hashlib.sha256(hifi.read_bytes()).hexdigest()}; "
            f"scope=surfaces={json.dumps(scope_surfaces, separators=(',', ':'))}|routes=[\"/home\",\"{second_route}\"]|states=[\"ready\"]|responsive={json.dumps({'kind':'per-surface','targets':[]}, separators=(',', ':'))}|tolerance=\"exact\"|allowedDeviations=[]|captureMode=mixed"
        )
        ui_text = re.sub(r"^Approved target:.*$", target_scope, ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^PRD source:.*$", f"PRD source: docs/product/PRD.md @ sha256:{hashlib.sha256(product.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^Architecture source:.*$", f"Architecture source: docs/product/architecture.md @ sha256:{hashlib.sha256(architecture.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^Stack source:.*$", f"Stack source: docs/product/stack-decisions.md @ sha256:{hashlib.sha256(stack.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^Wireframe:.*$", f"Wireframe: docs/design/wireframes.html @ sha256:{hashlib.sha256(wireframe.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^Frozen PRD basis:.*$", f"Frozen PRD basis: docs/product/PRD.md @ sha256:{hashlib.sha256(product.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        ui_text = re.sub(r"^Connected HiFi reference:.*$", f"Connected HiFi reference: docs/design/ui-references/run-1/index.html @ sha256:{hashlib.sha256(hifi.read_bytes()).hexdigest()}", ui_text, flags=re.MULTILINE)
        for name in evidence_specs:
            evidence_path = evidence_dir / name
            ui_text = re.sub(
                rf"evidence=docs/evidence/{re.escape(name)} @ sha256:[0-9a-f]{{64}}",
                f"evidence=docs/evidence/{name} @ sha256:{hashlib.sha256(evidence_path.read_bytes()).hexdigest()}",
                ui_text,
            )
        ui_digest = check_ui_design_contract.canonical_ui_approval_sha256(ui_text)
        replacement = (
            "Replacement visual contract when not_required: "
            f"target=docs/design/ui-references/run-1/index.html @ sha256:{hashlib.sha256(hifi.read_bytes()).hexdigest()}; "
            f"ui-design=docs/design/ui-design.md @ sha256:{ui_digest}; "
            f"wireframe=docs/design/wireframes.html @ sha256:{hashlib.sha256(wireframe.read_bytes()).hexdigest()}; "
            f"prd=docs/product/PRD.md @ sha256:{hashlib.sha256(product.read_bytes()).hexdigest()}"
        )
        ui_text = re.sub(r"^Replacement visual contract when(?:_| )not_required:.*$", replacement, ui_text, flags=re.MULTILINE)
        ui.write_text(ui_text, encoding="utf-8")
        registry_path = pair[1]
        markdown_path = pair[0]
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for key in ("platform", "stylingMechanism", "viewports", "sizeClasses"):
            registry.pop(key, None)
        registry["surfaceContracts"] = {
            "UI-001": {
                "releaseSurface": "web-app",
                "surfaceClass": "hosted_web",
                "captureMode": "hosted-browser",
                "responsive": {"kind": "viewports", "targets": [390, 768, 1200]},
            },
            second_id: {
                "releaseSurface": second_surface,
                "surfaceClass": second_class,
                "captureMode": second_mode,
                "responsive": {"kind": second_kind, "targets": second_targets},
            },
        }
        registry["stackSemantics"] = {
            "UI-001": {
                "platform": "web",
                "renderingModel": "SPA",
                "componentFoundation": "shadcn/ui owned source",
                "stylingMechanism": "Tailwind CSS",
            },
            second_id: {
                "platform": "ios" if platform == "ios" else "web",
                "renderingModel": "Native" if platform == "ios" else "SPA",
                "componentFoundation": "SwiftUI" if platform == "ios" else "shadcn/ui owned source",
                "stylingMechanism": "platform theme" if platform == "ios" else "Tailwind CSS",
            },
        }
        registry["stateMatrix"] = ["ready"]
        bindings = registry["sourceBindings"]
        bindings["prd"]["sha256"] = hashlib.sha256(product.read_bytes()).hexdigest()
        bindings["architecture"]["sha256"] = hashlib.sha256(architecture.read_bytes()).hexdigest()
        bindings["stack"]["sha256"] = hashlib.sha256(stack.read_bytes()).hexdigest()
        bindings["wireframe"]["sha256"] = hashlib.sha256(wireframe.read_bytes()).hexdigest()
        bindings["hifi"]["sha256"] = hashlib.sha256(hifi.read_bytes()).hexdigest()
        bindings["uiDesign"]["sha256"] = check_ui_design_contract.canonical_ui_approval_sha256(ui_text)
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        markdown_path.write_text(replace_generated_contract("# Pair\n", registry), encoding="utf-8")
        ui_text = re.sub(
            r"^Compiled design system pair:.*$",
            f"Compiled design system pair: docs/design/design-system.md @ sha256:{hashlib.sha256(markdown_path.read_bytes()).hexdigest()} and docs/design/design-system.json @ sha256:{hashlib.sha256(registry_path.read_bytes()).hexdigest()}",
            ui_text,
            flags=re.MULTILINE,
        )
        ui.write_text(ui_text, encoding="utf-8")
        # Recompute the canonical UI digest after replacing source/target fields.
        return {"product": product, "architecture": architecture, "stack": stack, "wireframe": wireframe, "hifi": hifi, "ui": ui, "design_markdown": pair[0], "design_json": pair[1]}

    def test_web_ios_hybrid_product_ui_harness_publication(self) -> None:
        self._run_hybrid("ios")

    def test_web_extension_hybrid_product_ui_harness_publication(self) -> None:
        self._run_hybrid("extension")

    def _run_hybrid(self, platform: str) -> None:
        # Fixture construction is intentionally local and real: the sibling
        # Product/UI materialization helpers provide canonical approvals,
        # evidence files, wireframe shell, and HiFi target bytes.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._materialize(root, platform)
            product_errors = __import__("harness_contract_join").full_product_package_checker_errors(
                paths["product"].read_bytes(), paths["architecture"].read_bytes(), paths["stack"].read_bytes(), repo_root=root
            )
            self.assertEqual([], product_errors)
            ui_errors = check_ui_design_contract.validate(
                paths["ui"], repo_root=root, prd_path=paths["product"], wireframes_path=paths["wireframe"], hifi_path=paths["hifi"],
                design_system_markdown_path=paths["design_markdown"], design_system_registry_path=paths["design_json"],
                require_filled=True, require_wireframe_approved=True, require_visual_approved=True,
            )
            self.assertEqual([], ui_errors)
            second_id = "UI-IOS" if platform == "ios" else "UI-EXT"
            second_surface = "ios-app" if platform == "ios" else "browser-extension"
            second_class = "ios" if platform == "ios" else "browser_extension"
            second_mode = "native" if platform == "ios" else "browser-extension"
            second_targets = ["compact", "regular"] if platform == "ios" else [390, 768, 1200]
            plan = valid_plan()
            plan["sources"] = []
            for source_id, kind, path in (
                ("SRC-PRD", "prd", paths["product"]),
                ("SRC-ARCH", "architecture", paths["architecture"]),
                ("SRC-STACK", "stack decisions", paths["stack"]),
                ("SRC-UI", "ui design", paths["ui"]),
                ("SRC-WIREFRAME", "wireframe", paths["wireframe"]),
                ("SRC-TARGET", "approved ui target", paths["hifi"]),
                ("SRC-DS-MD", "design system", paths["design_markdown"]),
                ("SRC-DS-JSON", "design system json", paths["design_json"]),
            ):
                plan["sources"].append(
                    {
                        "id": source_id,
                        "kind": kind,
                        "location": path.relative_to(root).as_posix(),
                        "owner": "owner",
                        "status": "frozen",
                        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source_revision": None,
                        "staged_revision": None,
                        "notes": "hybrid publication fixture",
                    }
                )
            plan["ui_surfaces"] = [
                {
                    "id": "UI-001",
                    "trace_ids": ["REQ-001"],
                    "route": "/home",
                    "breakpoints": ["390", "768", "1200"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                    "capture_mode": "hosted-browser",
                    "surface_class": "hosted_web",
                    "release_surface": "web-app",
                },
                {
                    "id": second_id,
                    "trace_ids": ["REQ-001"],
                    "route": "/ios-home" if platform == "ios" else "/extension",
                    "breakpoints": [str(item) for item in second_targets],
                    "states": ["ready"],
                    "evidence_gate": "required",
                    "capture_mode": second_mode,
                    "surface_class": second_class,
                    "release_surface": second_surface,
                },
            ]
            plan["traces"].append({
                "id": "DS-LAY-001",
                "source_ids": ["SRC-DS-JSON"],
                "priority": "must",
                "requirement": "Use the registered layout primitive",
                "disposition": "planned",
                "rationale": None,
            })
            run = valid_run(plan)
            run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                "required_harness_version"
            ] = "0.38.0"
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))
