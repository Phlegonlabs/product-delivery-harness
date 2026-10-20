"""Synthetic ds-showcase/2 source-runtime fixture: "Kiln Timer".

SYNTHETIC FIXTURE, NOT AN APPROVED PRODUCT. One HiFi surface with ready and
running states at two widths. Its own product script plays a viewport-entry
Web Animations reveal on the kiln stage and timer-driven step animations in
the running belt, whose stripes are a CSS animation on ::before. The UI
record carries only the sections the runtime join parses.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
UI_SCRIPTS = SCRIPTS.parents[1] / "ui-design-builder" / "scripts"
if str(UI_SCRIPTS) not in sys.path:
    sys.path.append(str(UI_SCRIPTS))

import reviewer_shell  # noqa: E402  canonical UI-builder reviewer bytes

HIFI = "docs/design/ui-references/kiln/index.html"
UI = "docs/design/ui-design.md"
PRODUCT_CSS = """
:root{--clay:#7a3b1d;--ash:#eceae6;--ink:#231a14;--glow:#d9822b}
body{margin:0;font:16px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--ash)}
[data-hifi-canvas]{container-type:inline-size}[data-hifi-canvas][data-hifi-target="390"]{width:390px}
[data-hifi-canvas][data-hifi-target="768"]{width:768px}
.shell{padding:16px}.intro{min-height:120px;margin:0}
.field{font:inherit;border:2px solid var(--clay);padding:8px;min-height:44px}
[data-ui-surface] :focus-visible{outline:3px solid var(--glow);outline-offset:2px}
.kiln-side{height:12px;background:var(--clay);margin:16px 0 8px}
.kiln{position:relative;height:160px;background:#fff;border:2px solid var(--ink);overflow:hidden}
.kiln-mark{position:absolute;top:24px;width:40px;height:40px;background:var(--clay)}
.kiln-mark:nth-child(1){left:20px}.kiln-mark:nth-child(2){left:90px}.kiln-mark:nth-child(3){left:160px}
:root[data-kiln-arm]:not([data-kiln-done]) .kiln-mark{opacity:0}
.belt{display:grid;gap:8px;margin-top:16px}
.belt-bar{position:relative;height:10px;border:2px solid var(--ink);overflow:hidden}
.belt-bar::before{content:"";position:absolute;inset:0 0 0 -16px;background:repeating-linear-gradient(90deg,var(--glow) 0 8px,transparent 8px 16px);animation:belt-move 400ms linear 6}
@keyframes belt-move{to{transform:translateX(16px)}}
[data-belt-spent] .belt-bar::before{animation:none}
.belt-count{font-variant-numeric:tabular-nums}
@media (prefers-reduced-motion:reduce){[data-ui-surface] *,[data-ui-surface] *::before,[data-ui-surface] *::after{animation:none!important;transition:none!important}}
"""

KILN_PLAY = """function rise(stage) {
    const marks = Array.from(stage.querySelectorAll(".kiln-mark"));
    const anims = marks.map((mark, i) => mark.animate([{transform: "translateY(90px)", opacity: 0}, {transform: "none", opacity: 1}],
      {duration: 900, delay: i * 150, fill: "both", easing: "ease-out"}));
    if (typeof ResizeObserver === "function") {
      const width = Math.round(stage.getBoundingClientRect().width);
      const ro = new ResizeObserver(() => { if (Math.abs(Math.round(stage.getBoundingClientRect().width) - width) > 1) { anims.forEach(a => a.finish()); ro.disconnect(); } });
      ro.observe(stage);
    }
    return Promise.all(anims.map(a => a.finished)).then(() => { document.documentElement.dataset.kilnDone = "1"; anims.forEach(a => a.cancel()); });
  }"""

BELT_STEP = 'if (!reduced()) bars[step].animate([{transform: "scaleX(.2)"}, {transform: "none"}], {duration: 300, easing: "ease-out"});'

PRODUCT_SCRIPT = """(function () {
  "use strict";
  const surface = document.querySelector("[data-ui-surface]");
  const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  let played = false;
  %KILN%
  function arm() {
    const stages = Array.from(surface.querySelectorAll('[data-hifi-state-view="ready"] .kiln'));
    if (!stages.length) return;
    if (reduced() || typeof IntersectionObserver !== "function") { document.documentElement.dataset.kilnDone = "1"; return; }
    document.documentElement.dataset.kilnArm = "1";
    const io = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (played || !entry.isIntersecting || entry.target.closest("[hidden]")) continue;
        played = true; io.disconnect(); rise(entry.target);
      }
    }, {threshold: 0.5});
    stages.forEach(stage => io.observe(stage));
  }
  let run = null;
  function startBelt(view) {
    const belt = view.querySelector(".belt");
    if (!belt || run) return;
    const ends = performance.now() + 2400;
    const count = belt.querySelector(".belt-count");
    const bars = Array.from(belt.querySelectorAll(".belt-bar"));
    let step = 0;
    run = {still: setTimeout(() => belt.setAttribute("data-belt-spent", ""), 2400), tick: setInterval(() => {
      count.textContent = String(Number(count.textContent) + 1);
      if (step < bars.length - 1 && performance.now() < ends - 200) { step += 1; bars[step].setAttribute("data-step", "current"); %STEP% }
    }, 600)};
  }
  function watch() {
    const view = Array.from(surface.querySelectorAll("[data-hifi-state-view]")).find(item => !item.hidden);
    if (view && view.dataset.hifiStateView === "running") startBelt(view);
  }
  if (typeof MutationObserver === "function") new MutationObserver(watch).observe(surface, {subtree: true, attributes: true, attributeFilter: ["hidden"]});
  document.addEventListener("DOMContentLoaded", () => { setTimeout(arm, 0); watch(); });
})();""".replace("%KILN%", KILN_PLAY).replace("%STEP%", BELT_STEP)

# The genuine canonical reviewer runtime and shell, exactly as the UI builder assembles a ui-hifi/2 page.
REVIEWER_RUNTIME = reviewer_shell.runtime_block()
INTENTS = (("MM-001", "UI-001 / kiln demonstration", "Plays once when the kiln first enters the viewport"),
           ("MM-002", "UI-001 / belt steps", "Step changes while running"),
           ("MM-003", "UI-001 / belt stripes", "Stripes move while running"))


def _view(state: str, target: str) -> str:
    common = ('<h1>Kiln two</h1><p class="intro">Bisque firing for the spring stoneware batch.</p>'
              '<label>Batch name <input class="field" value="Stoneware 14" data-control-id="batch" '
              'data-specimen-variant="default" data-specimen-state="default"></label> <a href="log.html">Firing log</a>')
    if state == "ready":
        body = ('<div class="kiln-side" aria-hidden="true"></div><section class="kiln" aria-label="Kiln loading demonstration" '
                'data-specimen-variant="demo" data-specimen-state="final">'
                + '<span class="kiln-mark"></span>' * 3 + "</section>")
    else:
        body = ('<p class="belt-note">Cone 04</p><div class="belt" data-specimen-variant="progress" data-specimen-state="running">'
                '<p>Firing for <span class="belt-count">0</span> s</p>' + '<div class="belt-bar"></div>' * 3 + "</div>")
    return f'<div data-hifi-state-view="{state}" data-responsive-target="{target}">{common}{body}</div>'


def pages(script: str = PRODUCT_SCRIPT, *, css: str = PRODUCT_CSS, views: str | None = None, scripts_after: str = "") -> dict[str, str]:
    manifest = {"schema": "ui-hifi/2", "pages": [], "interactions": [], "surfaces": [
        {"id": "UI-001", "page": "index.html", "route": "/kiln", "states": ["ready", "running", "not_found:n/a"],
         "responsive": {"kind": "viewports", "targets": [390, 768]}, "navigation": [], "controls": ["batch"]}]}
    views = views if views is not None else "".join(_view(state, target) for state in ("ready", "running") for target in ("390", "768"))
    shell = "<!-- reviewer:start -->\n" + reviewer_shell.build_shell(manifest, "index.html") + "\n<!-- reviewer:end -->"
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Kiln timer</title>'
            f"<style>{css}</style></head><body>{shell}"
            '<main><div data-hifi-canvas data-hifi-targets="390 768" data-hifi-target="390">'
            f'<section class="shell" data-ui-surface="UI-001" data-ui-route="/kiln">{views}</section></div></main>'
            f"<script>{script}</script>{scripts_after}{REVIEWER_RUNTIME}"
            '<script>connectHifiReviewer({"packageId": "ui-hifi/2:kiln"})</script>'
            f'<script id="ui-hifi-manifest" type="application/json">{json.dumps(manifest)}</script></body></html>')
    return {"index.html": html}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trigger(mechanism: str, intent: str, state: str, activation: str, script: str = PRODUCT_SCRIPT, **extra) -> dict:
    return dict({"kind": "source-runtime", "mechanism": mechanism, "intent": intent, "surface": "UI-001", "state": state,
                 "target": "390", "scriptSha256": sha(script), "activation": {"kind": activation}}, **extra)


def registry(script: str = PRODUCT_SCRIPT) -> dict:
    na = "not_applicable"
    field = {"kind": "primitive", "name": "TextField"}
    return {
        "schema": "design-system/4", "product": "Kiln Timer (synthetic fixture)", "platform": "web",
        "sourceBindings": {"uiDesign": {"path": UI, "sha256": "0" * 64}, "hifi": {"path": HIFI, "sha256": "0" * 64}},
        "tokens": {"color": {"--clay": "#7a3b1d", "--ink": "#231a14", "--glow": "#d9822b"}},
        "primitives": {"TextField": {"layer": "control", "class": "field", "variants": ["default"]},
                       "KilnStage": {"layer": "surface", "class": "kiln"}, "FiringBelt": {"layer": "surface", "class": "belt"}},
        "productComponents": {}, "motionVariants": ["kiln-rise", "belt-step", "belt-stripes"],
        "showcase": {
            "schema": "ds-showcase/2",
            "specimens": [
                {"id": "field-default", "subject": field, "axes": {"variants": "default"},
                 "source": {"page": "index.html", "selector": ".field", "variant": "default", "state": "default"}},
                {"id": "kiln-demo", "subject": {"kind": "primitive", "name": "KilnStage"}, "axes": {},
                 "source": {"page": "index.html", "selector": ".kiln", "variant": "demo", "state": "final"}},
                {"id": "belt-progress", "subject": {"kind": "primitive", "name": "FiringBelt"}, "axes": {},
                 "source": {"page": "index.html", "selector": ".belt", "variant": "progress", "state": "running"}}],
            "states": [
                {"subject": field, "state": "default", "mode": "rendered", "specimen": "field-default"},
                {"subject": field, "state": "focus-visible", "mode": "pseudo", "specimen": "field-default"},
                {"subject": field, "state": "hover", "mode": na, "reason": "Fields keep their border on hover."},
                {"subject": field, "state": "active", "mode": na, "reason": "Text entry has no pressed look."},
                {"subject": field, "state": "disabled", "mode": na, "reason": "The batch name is always editable."}],
            "motion": [
                {"variant": "kiln-rise", "specimen": "kiln-demo", "trigger": trigger("waapi", "MM-001", "ready", "viewport", script)},
                {"variant": "belt-step", "specimen": "belt-progress", "trigger": trigger("waapi", "MM-002", "running", "state-entry", script)},
                {"variant": "belt-stripes", "specimen": "belt-progress",
                 "trigger": trigger("css-animation", "MM-003", "running", "state-entry", script)}]},
    }


def evidence_files() -> dict[str, bytes]:
    return {f"docs/design/evidence/{intent.lower()}-{case}.json": json.dumps({"intent": intent, "case": case}).encode()
            for intent, _, _ in INTENTS for case in ("normal", "reduced")}


def ui_record(files: dict[str, bytes], *, status: str = "approved", rows: tuple = INTENTS) -> str:
    header = ("| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | "
              "Static / reduced-motion fallback | Generation route | Status | Generation status |\n" + "| --- " * 11 + "|\n")
    intents = "".join(f"| {i} | {scope} | motion | Fixture motion | {trig} | Fixture prompt | Synthetic fixture | "
                      f"Final state at rest | CSS-WAAPI | {status} | deferred |\n" for i, scope, trig in rows)
    evidence = "".join(
        f"| {i} | {scope} | {trig} | At rest | "
        + " | ".join(f"PASS — evidence={path} @ sha256:{hashlib.sha256(files[path]).hexdigest()}"
                     for path in (f"docs/design/evidence/{i.lower()}-normal.json", f"docs/design/evidence/{i.lower()}-reduced.json")
                     if path in files)
        + " | PASS |\n" for i, scope, trig in rows)
    return ("# UI Design Contract\n\n## Motion And Media Intent\n\nMotion direction: expressive — owner Fixture Owner\n\n"
            + header + intents + "\n## Style Integration\n\n### Required motion evidence\n\n"
            "| Intent ID | UI scope / region | Trigger observed | End state observed | Normal-motion evidence | "
            "Reduced-motion evidence | Verdict |\n" + "| --- " * 7 + "|\n" + evidence)


def reader(files: dict[str, bytes]) -> Callable[[str], bytes | None]:
    return files.get


def repo_files(page_set: dict[str, str] | None = None) -> dict[str, bytes]:
    files = evidence_files()
    files[UI] = ui_record(files).encode("utf-8")
    for name, html in (page_set or pages()).items():
        files["docs/design/ui-references/kiln/" + name] = html.encode("utf-8")
    return files


def render(page_set: dict[str, str] | None = None, data: dict | None = None, files: dict[str, bytes] | None = None) -> str:
    """Render the specimen book exactly as render_view does after its joins pass."""
    import design_system_showcase
    import showcase_runtime
    from design_system_gallery import render_gallery

    page_set, data = page_set or pages(), data or registry()
    files = files or repo_files(page_set)
    manifest = json.loads(design_system_showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
    resolved, problems = design_system_showcase.resolve(data, page_set)
    runtime, runtime_problems = showcase_runtime.resolve_runtime(data, page_set, manifest, reader(files))
    if problems or runtime_problems:
        raise ValueError("\n".join(problems + runtime_problems))
    payload = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return render_gallery(data, payload, b"# Kiln Timer (synthetic fixture)\n", page_set, manifest, resolved,
                          {"path": HIFI, "sha256": sha(page_set["index.html"])}, runtime=runtime)
