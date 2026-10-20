"""Render the design-system/4 specimen book from a validated pair and HiFi.

Gallery chrome is fixed here. Product specimens are sandboxed srcdoc plates
whose markup and CSS are copied from the approved HiFi (see
design_system_showcase). Every executable script is pinned by a CSP hash.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from html import escape
from typing import Any

import design_system_showcase as source
import showcase_runtime
import surface_adapter
from design_system_gallery_assets import FRAME_RUNTIME, GALLERY_CSS, GALLERY_RUNTIME
from design_system_gallery_runtime import runtime_plate
from design_system_runtime_assets import RUNTIME_BOOT, RUNTIME_CSS, RUNTIME_FRAME, RUNTIME_GALLERY

LAYERS = ("layout", "surface", "typography", "control")
NATIVE_CLASSES = {"ios", "android", "macos", "windows", "desktop"}
HEX = r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})"
COLOR_RE = re.compile(rf"(?:{HEX}|rgba?\([0-9.,% /]+\)|hsla?\([0-9.,% /deg]+\))")
LENGTH_RE = re.compile(r"(?:0|[0-9]+(?:\.[0-9]+)?)(?:px|rem|em)")
NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
DURATION_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:ms|s)")
EASING_RE = re.compile(r"(?:linear|ease|ease-in|ease-out|ease-in-out|step-start|step-end|cubic-bezier\([0-9., -]+\)|steps\([1-9][0-9]*(?:,\s*(?:start|end|jump-start|jump-end|jump-none|jump-both))?\))")
_LEN = r"(?:-?[0-9]+(?:\.[0-9]+)?(?:px|rem|em)|0)"
_SHADOW = rf"(?:inset\s+)?{_LEN}(?:\s+{_LEN}){{1,3}}\s+(?:{HEX}|rgba?\([0-9.,% /]+\))"
SHADOW_RE = re.compile(rf"none|{_SHADOW}(?:\s*,\s*{_SHADOW})*")
FAMILY_RE = re.compile(r"[\w ,\-'\"]+")
WEIGHT_RE = re.compile(r"(?:[1-9][0-9]{0,2}|1000|normal|bold)")

def _hash(script: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"


def content_security_policy(scripts: list[str]) -> str:
    hashes = " ".join(sorted({_hash(item) for item in scripts}))
    return ("default-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'; frame-src 'none'; "
            "object-src 'none'; img-src data:; font-src data:; media-src data:; style-src 'unsafe-inline'; "
            f"script-src {hashes}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "item"


def _num(value: str) -> float | None:
    match = re.fullmatch(r"(-?[0-9]+(?:\.[0-9]+)?)(px|rem|em|ms|s)?", value.strip())
    if not match:
        return None
    number = float(match.group(1))
    return number * 16 if match.group(2) in {"rem", "em"} else number * 1000 if match.group(2) == "s" else number


class Gallery:
    def __init__(self, registry: dict[str, Any], registry_bytes: bytes, markdown_bytes: bytes,
                 documents: dict[str, str], manifest: dict[str, Any], resolved: dict[str, dict[str, Any]],
                 hifi_binding: dict[str, str], runtime: dict[str, dict[str, Any]] | None = None) -> None:
        self.registry, self.documents, self.manifest, self.resolved = registry, documents, manifest, resolved
        self.registry_bytes, self.markdown_bytes, self.hifi = registry_bytes, markdown_bytes, hifi_binding
        self.trees = {page: source.SourceTree(html) for page, html in documents.items()}
        self.surfaces = [row for row in manifest.get("surfaces", []) if isinstance(row, dict)]
        self.v2 = registry["showcase"].get("schema") == showcase_runtime.SCHEMA_V2
        self.runtime = runtime or {}
        runtime_rows = [row for row in registry["showcase"]["motion"] if showcase_runtime.is_runtime(row)]
        if any(row["variant"] not in self.runtime for row in runtime_rows):
            raise ValueError("source-runtime motion rows need resolved runtime bindings before rendering")
        scripts = [GALLERY_RUNTIME, FRAME_RUNTIME] + ([RUNTIME_FRAME, RUNTIME_BOOT, RUNTIME_GALLERY] if runtime_rows else [])
        self.has_runtime = bool(runtime_rows)
        for page in sorted({row.get("page") for row in self.surfaces if row.get("page") in documents}):
            scripts.extend(source.product_scripts(documents[page], with_controls=True))
        # ds-showcase/2 Surface plates run the page's own reviewer infrastructure (surface_adapter).
        self.surface_bindings: dict[str, dict[str, Any]] = {}
        if self.v2:
            self.surface_bindings, problems = surface_adapter.resolve_surfaces(self.trees, manifest)
            if problems:
                raise ValueError("\n".join(problems))
            if self.surface_bindings:
                scripts += [surface_adapter.SURFACE_FOCUS_GUARD, surface_adapter.SURFACE_FRAME, surface_adapter.SURFACE_GALLERY]
                scripts += [binding["connect"] for binding in self.surface_bindings.values()]
        self.csp = content_security_policy(scripts)
        self.frame_count = 0
        self.specimen_frames: dict[str, str] = {}

    # Source-derived plates -------------------------------------------------
    def native(self, page: str) -> bool:
        contracts = self.registry.get("surfaceContracts")
        if isinstance(contracts, dict):
            ids = [row.get("id") for row in self.surfaces if row.get("page") == page]
            return any(isinstance(contracts.get(item), dict) and contracts[item].get("surfaceClass") in NATIVE_CLASSES for item in ids)
        return self.registry.get("platform") not in (None, "web")

    def frame(self, page: str, node: dict[str, Any], *, kind: str, title: str, config: dict[str, Any]) -> tuple[str, str, float]:
        self.frame_count += 1
        frame_id = f"plate-{self.frame_count:03d}"
        tree, html = self.trees[page], self.documents[page]
        html_start, body_start, content = source.fragment(tree, node, marker=frame_id)
        css = source.product_css(html)
        reduced = source.reduced_motion_css(css)
        surface = self.surface_bindings.get(str(config.get("surface"))) if self.v2 and kind == "surface" else None
        if self.v2 and kind == "surface" and surface is None:
            raise ValueError(f"Surface plate {config.get('surface')} has no validated reviewer infrastructure")
        scripts = surface["scripts"] if surface else source.product_scripts(html, with_controls=kind == "surface")
        payload = json.dumps(dict(config, id=frame_id, kind=kind), sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
        document = ("<!doctype html>" + html_start + '<head><meta charset="utf-8">'
                    + f'<meta http-equiv="Content-Security-Policy" content="{escape(self.csp, quote=True)}">'
                    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    + "<style>html,body{margin:0}</style>" + f"<style>{css}</style>"
                    + (f'<style data-ds-reduced media="not all">{reduced}</style>' if reduced.strip() else "")
                    + f'<script type="application/json" id="ds-frame-config">{payload}</script>'
                    + (f"<script>{surface_adapter.SURFACE_FOCUS_GUARD}</script>" if surface else "") + "</head>"
                    + body_start + content + (surface["infrastructure"] if surface else "")
                    + "".join(f"<script>{item}</script>" for item in scripts)
                    + f"<script>{surface_adapter.SURFACE_FRAME if surface else FRAME_RUNTIME}</script></body></html>")
        widths = source.canvas_widths(tree)
        width = widths.get(source.specimen_target(tree, node) or "", 0.0) or 360.0
        marker = " data-ds-surface-frame" if surface else ""
        iframe = (f'<iframe data-ds-frame="{frame_id}"{marker} title="{escape(title, quote=True)}" sandbox="allow-scripts" '
                  f'referrerpolicy="no-referrer" style="width:{width:g}px" srcdoc="{escape(document, quote=True)}"></iframe>')
        return frame_id, iframe, width

    def plate(self, page: str, node: dict[str, Any], *, kind: str, title: str, caption: str,
              config: dict[str, Any] | None = None, controls: str = "") -> tuple[str, str]:
        frame_id, iframe, _ = self.frame(page, node, kind=kind, title=title, config=config or {})
        badge = ('<p class="native">HTML demonstration of an approved native design. Not native evidence.</p>'
                 if self.native(page) else "")
        return frame_id, (f'<figure class="plate" id="{frame_id}"><div class="plate-stage">{iframe}</div>'
                          f"<figcaption>{caption}{badge}</figcaption>{controls}"
                          f'<p class="status" data-ds-status="{frame_id}" aria-live="polite"></p></figure>')

    # Sections ----------------------------------------------------------------
    def foundations(self) -> str:
        parts = ['<section class="chapter" id="foundations" aria-labelledby="foundations-title">',
                 '<h2 id="foundations-title">Foundations</h2>',
                 "<p>Every token the registry records, with its value applied. Values that cannot be applied safely stay as recorded text.</p>"]
        for group, entries in self.registry.get("tokens", {}).items():
            items = entries if isinstance(entries, dict) else {group: entries}
            parts.append(f'<h3 id="tokens-{_slug(group)}">{escape(group)}</h3>{self.range_note(items)}')
            parts.append(self.token_group(group, items))
        parts.append(self.breakpoints())
        parts.append("</section>")
        return "".join(parts)

    @staticmethod
    def range_note(items: dict[str, Any]) -> str:
        values = [(name, value) for name, value in items.items() if isinstance(value, str) and _num(value) is not None]
        if len(values) < 2:
            return ""
        ordered = sorted(values, key=lambda item: _num(item[1]))
        return (f'<p class="range">Range {escape(ordered[0][1])} to {escape(ordered[-1][1])} '
                f"across {len(values)} steps.</p>")

    def token_group(self, group: str, items: dict[str, Any]) -> str:
        key = group.casefold()
        if key in {"color", "colors"}:
            chips = []
            for name, value in items.items():
                chip = (f'<div class="chip" style="background:{value}"></div>' if isinstance(value, str) and COLOR_RE.fullmatch(value)
                        else '<div class="chip" aria-hidden="true"></div>')
                chips.append(f"<li>{chip}<p><code>{escape(name)}</code><br>{escape(self.text(value))}</p></li>")
            return '<ul class="swatches">' + "".join(chips) + "</ul>"
        rows = []
        for index, (name, value) in enumerate(items.items()):
            rows.append(f"<li><div><code>{escape(name)}</code><br><span class=\"range\">{escape(self.text(value))}</span></div>"
                        f"<div>{self.token_sample(key, name, value, f'{_slug(group)}-{index}')}</div></li>")
        return '<ul class="ladder">' + "".join(rows) + "</ul>"

    @staticmethod
    def text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def token_sample(key: str, name: str, value: Any, anchor: str) -> str:
        if not isinstance(value, str):
            return "Recorded value; no browser specimen"
        if key in {"fontsize", "font-size"} and LENGTH_RE.fullmatch(value):
            return f'<span class="sample" style="font-size:{value}">Specimen 字樣 {escape(value)}</span>'
        if key in {"space", "spacing", "size", "sizes", "dimension"} and LENGTH_RE.fullmatch(value):
            return f'<div class="bar" style="width:{value}" role="img" aria-label="{escape(name, quote=True)} length {escape(value, quote=True)}"></div>'
        if key == "radius" and LENGTH_RE.fullmatch(value):
            return f'<div class="shape" style="border-radius:{value}"></div>'
        if key == "shadow" and SHADOW_RE.fullmatch(value):
            return f'<div class="shape" style="box-shadow:{value}"></div>'
        if key in {"lineheight", "line-height"} and NUMBER_RE.fullmatch(value):
            return f'<p class="sample" style="line-height:{value};margin:0;max-width:28rem">Line one of the measure<br>line two keeps this rhythm</p>'
        if key in {"fontweight", "font-weight"} and WEIGHT_RE.fullmatch(value):
            return f'<span class="sample" style="font-weight:{value}">Weight 字重 {escape(value)}</span>'
        if key in {"fontfamily", "font-family"} and FAMILY_RE.fullmatch(value):
            return f'<span class="sample" style="font-family:{escape(value, quote=True)}">The next step 下一步</span>'
        if key in {"duration", "easing"} and (DURATION_RE.fullmatch(value) if key == "duration" else EASING_RE.fullmatch(value)):
            prop = "transition-duration:" + value + ";transition-timing-function:ease" if key == "duration" else \
                "transition-duration:900ms;transition-timing-function:" + value
            track = f"track-{anchor}"
            return (f'<div class="track" id="{track}"><span class="dot" style="{prop}"></span></div>'
                    f'<div class="controls"><button type="button" data-ds-token-motion="{track}">Replay</button>'
                    f'<button type="button" data-ds-token-motion="{track}" data-action="stop">Stop</button></div>')
        return "Recorded value; no browser specimen"

    def breakpoints(self) -> str:
        rows = []
        contracts = self.registry.get("surfaceContracts")
        if isinstance(contracts, dict):
            for surface_id, contract in contracts.items():
                responsive = contract.get("responsive", {}) if isinstance(contract, dict) else {}
                rows.append((surface_id, responsive.get("kind", ""), responsive.get("targets", [])))
        elif "viewports" in self.registry:
            rows.append(("All surfaces", "viewports", self.registry["viewports"]))
        elif "sizeClasses" in self.registry:
            rows.append(("All surfaces", "sizeClasses", self.registry["sizeClasses"]))
        body = "".join(f"<tr><th scope=\"row\">{escape(str(a))}</th><td>{escape(str(b))}</td><td>{escape(', '.join(map(str, c)))}</td></tr>"
                       for a, b, c in rows)
        rules = "".join(f"<tr><th scope=\"row\">{escape(page)}</th><td>{'<br>'.join('<code>@container ' + escape(rule) + '</code>' for rule in source.container_rules(source.analysis_css(html))) or 'None recorded'}</td></tr>"
                        for page, html in self.documents.items())
        return ('<h3 id="tokens-breakpoints">Responsive set and layout rules</h3><div class="table-scroll"><table><thead><tr>'
                '<th scope="col">Scope</th><th scope="col">Kind</th><th scope="col">Approved targets</th></tr></thead>'
                f'<tbody>{body}</tbody></table></div><h4>Container query transitions in approved source CSS</h4>'
                f'<div class="table-scroll"><table><thead><tr><th scope="col">Page</th><th scope="col">Rules</th></tr></thead>'
                f"<tbody>{rules}</tbody></table></div>")

    def components(self) -> str:
        showcase = self.registry["showcase"]
        primitives = self.registry.get("primitives", {})
        components = self.registry.get("productComponents", {}) or {}
        parts = ['<section class="chapter" id="components" aria-labelledby="components-title">',
                 '<h2 id="components-title">Components</h2>',
                 "<p>Each plate is the approved HiFi element itself, copied with its ancestors and page CSS into a sandboxed frame. "
                 "Hover, focus and press the live plates; rendered states come from their own source elements.</p>"]
        ordered = [("primitive", name) for layer in LAYERS for name, spec in primitives.items()
                   if isinstance(spec, dict) and spec.get("layer") == layer]
        ordered += [("primitive", name) for name, spec in primitives.items() if ("primitive", name) not in ordered]
        ordered += [("component", name) for name in components]
        for kind, name in ordered:
            spec = (primitives if kind == "primitive" else components).get(name, {})
            specimens = [row for row in showcase["specimens"] if row["subject"] == {"kind": kind, "name": name}]
            label = f"{spec.get('layer', '').capitalize()} primitive" if kind == "primitive" else "Product component"
            ident = f", <code>{escape(spec['dsId'])}</code>" if isinstance(spec, dict) and spec.get("dsId") else ""
            parts.append(f'<h3 id="c-{_slug(kind + "-" + name)}">{escape(name)}</h3><p class="meta">{label}{ident}</p>')
            parts.append(self.subject_facts(kind, spec))
            plates = []
            for row in specimens:
                bound = self.resolved[row["id"]]
                axes = ", ".join(f"{key} {value}" for key, value in row["axes"].items()) or "base"
                src = row["source"]
                caption = (f"<b>{escape(axes)}</b>, state {escape(src['state'])}<br>"
                           f"Source <code>{escape(src['page'])}</code> <code>{escape(src['selector'])}</code> "
                           f"variant <code>{escape(src['variant'])}</code>")
                frame_id, html = self.plate(src["page"], bound["node"], kind="specimen", title=f"{name} {axes} {src['state']}", caption=caption)
                self.specimen_frames[row["id"]] = frame_id
                plates.append(html)
            parts.append('<div class="plates">' + "".join(plates) + "</div>")
            parts.append(self.state_table(kind, name))
        parts.append("</section>")
        return "".join(parts)

    @staticmethod
    def subject_facts(kind: str, spec: Any) -> str:
        if not isinstance(spec, dict):
            return ""
        rows = []
        if kind == "primitive":
            for key, values in source.primitive_axes(spec).items():
                rows.append((key, ", ".join(values)))
            for key in ("minTargetPx", "requiresAccessibleName", "class"):
                if key in spec:
                    rows.append((key, str(spec[key])))
        else:
            for key in ("requiredContentOrder", "composes", "states"):
                if isinstance(spec.get(key), list):
                    rows.append((key, ", ".join(map(str, spec[key]))))
        if not rows:
            return ""
        return ('<div class="table-scroll"><table class="facts"><tbody>' + "".join(
            f'<tr><th scope="row">{escape(a)}</th><td>{escape(b)}</td></tr>' for a, b in rows) + "</tbody></table></div>")

    def state_table(self, kind: str, name: str) -> str:
        rows = []
        frames = self.specimen_frames
        for row in self.registry["showcase"]["states"]:
            if row["subject"] != {"kind": kind, "name": name}:
                continue
            if row["mode"] == "not_applicable":
                treatment = "Not applicable: " + escape(row["reason"])
            else:
                link = f'<a href="#{frames.get(row["specimen"], "")}">plate {escape(row["specimen"])}</a>'
                selector = self.registry_specimen(row["specimen"])["source"]["selector"]
                rule = f"{selector}:{row['state']}"
                if self.v2 and row["mode"] == "pseudo":
                    rule = self.pseudo_rule(row) or rule
                treatment = (f"Rendered from its own source element, {link}" if row["mode"] == "rendered" else
                             f"Live on {link}: {escape(row['state'])} applies the approved <code>{escape(rule)}</code> rule")
            rows.append(f'<tr><th scope="row">{escape(row["state"])}</th><td>{treatment}</td></tr>')
        if not rows:
            return ""
        return ('<h4>States</h4><div class="table-scroll"><table><thead><tr><th scope="col">State</th>'
                '<th scope="col">Treatment</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")

    def pseudo_rule(self, row: dict[str, Any]) -> str | None:
        """Name the shared ancestor-scoped rule when no direct selector rule backs a pseudo state."""
        bound = self.resolved[row["specimen"]]
        page_css = source.analysis_css(self.documents[bound["row"]["source"]["page"]])
        selector = re.escape(bound["row"]["source"]["selector"])
        if re.search(selector + r"(?![\w-])[^\s{},>+~]*:" + re.escape(row["state"]) + r"(?![\w-])", page_css):
            return None
        return showcase_runtime.shared_pseudo_rule(page_css, bound["tree"], bound["node"], row["state"])

    def registry_specimen(self, specimen_id: str) -> dict[str, Any]:
        return next(row for row in self.registry["showcase"]["specimens"] if row["id"] == specimen_id)

    def surfaces_section(self) -> str:
        parts = ['<section class="chapter" id="surfaces" aria-labelledby="surfaces-title">',
                 '<h2 id="surfaces-title">Surfaces, interaction and responsive behavior</h2>',
                 "<p>Each approved surface runs its own product script inside a sandbox. Switch approved sizes, drag between them "
                 "to inspect intermediate widths, change state, and operate menus, tabs and forms by pointer or keyboard. "
                 "Links and form submissions stay on the plate.</p>"]
        interactions = [row for row in self.manifest.get("interactions", []) if isinstance(row, dict)]
        for surface in self.surfaces:
            page, surface_id = surface.get("page"), surface.get("id")
            tree = self.trees.get(page)
            node = source.surface_node(tree, surface_id) if tree else None
            if node is None:
                continue
            states = [str(item) for item in surface.get("states", []) if "n/a" not in str(item).casefold()]
            widths = source.canvas_widths(tree)
            targets = [str(item) for item in surface.get("responsive", {}).get("targets", [])]
            frame_id = f"plate-{self.frame_count + 1:03d}"
            buttons = "".join(
                f'<button type="button" data-ds-for="{frame_id}" data-ds-target="{escape(target, quote=True)}" '
                f'data-ds-width="{widths.get(target, 0):g}" aria-pressed="{str(index == 0).lower()}">{escape(target)}</button>'
                for index, target in enumerate(targets))
            numeric = sorted((width, target) for target, width in widths.items() if target in targets)
            slider = ""
            if len(numeric) >= 2:
                pairs = json.dumps([[target, width] for width, target in numeric])
                slider = (f'<label>Width <input type="range" min="{numeric[0][0]:g}" max="{numeric[-1][0]:g}" step="1" '
                          f'value="{widths.get(targets[0], numeric[0][0]):g}" data-ds-width-for="{frame_id}" '
                          f"data-ds-targets='{escape(pairs, quote=True)}' aria-label=\"{escape(surface_id)} width in pixels\">"
                          f'<output>{widths.get(targets[0], numeric[0][0]):g} px</output></label>')
            options = "".join(f'<option value="{escape(state, quote=True)}">{escape(state)}</option>' for state in states)
            controls = (f'<div class="controls"><fieldset><legend>Size</legend>{buttons}</fieldset>{slider}'
                        + (f'<label>State <select data-ds-state-for="{frame_id}">{options}</select></label>' if options else "")
                        + "</div>")
            caption = (f"<b>{escape(str(surface_id))}</b> <code>{escape(str(surface.get('route', '')))}</code> "
                       f"from <code>{escape(str(page))}</code>")
            config = {"surface": str(surface_id)} if self.v2 else {"state": states[0] if states else None}
            _, html = self.plate(page, node, kind="surface", title=f"{surface_id} live surface", caption=caption,
                                 config=config, controls=controls)
            parts.append(f'<h3 id="s-{_slug(str(surface_id))}">{escape(str(surface_id))}</h3>{html}')
            rows = [row for row in interactions if isinstance(row.get("source"), dict) and row["source"].get("surface") == surface_id]
            if rows:
                parts.append('<h4>Approved operations</h4><div class="table-scroll"><table><thead><tr><th scope="col">Operation</th>'
                             '<th scope="col">Control</th><th scope="col">From</th><th scope="col">To</th><th scope="col">Kind</th></tr></thead><tbody>'
                             + "".join(
                                 f"<tr><th scope=\"row\">{escape(str(row.get('id')))}</th><td><code>{escape(str(row.get('control')))}</code></td>"
                                 f"<td>{escape(str(row['source'].get('state')))}</td><td>{escape(str(row.get('destination', {}).get('surface')))} "
                                 f"{escape(str(row.get('destination', {}).get('state')))}</td><td>{escape(str(row.get('kind')))}</td></tr>"
                                 for row in rows) + "</tbody></table></div>")
        parts.append("</section>")
        return "".join(parts)

    def motion(self) -> str:
        rows = self.registry["showcase"]["motion"]
        parts = ['<section class="chapter" id="motion" aria-labelledby="motion-title">', '<h2 id="motion-title">Motion</h2>',
                 "<p>Replay each approved motion on its source element or stop it mid-flight. Reduced motion applies the page's own "
                 "<code>prefers-reduced-motion</code> rules; your system preference sets its initial state.</p>",
                 '<div class="toolbar controls"><button type="button" data-ds-reduced-toggle aria-pressed="false">Reduced motion</button></div>']
        if self.has_runtime:
            parts.insert(3, "<p>Source-runtime plates run the approved surface and its hash-bound product script in a fresh "
                         "frame. Their status reports only what the browser observes on the bound subject. This page is a "
                         "render candidate; compilation closes only with a separate browser acceptance receipt for these exact bytes.</p>")
        if not rows:
            parts.append("<p>No motion variants are registered for this product.</p>")
        for row in rows:
            if showcase_runtime.is_runtime(row):
                parts.append(f'<h3 id="m-{_slug(row["variant"])}">{escape(row["variant"])}</h3>'
                             + runtime_plate(self, row, self.runtime[row["variant"]]))
                continue
            bound = self.resolved[row["specimen"]]
            src = bound["row"]["source"]
            trigger = row["trigger"]
            described = {"attribute": f"attribute <code>{escape(trigger.get('name', ''))}</code> {escape(trigger.get('from', ''))} to {escape(trigger.get('to', ''))}",
                         "class": f"class <code>{escape(trigger.get('name', ''))}</code>", "animation": "source keyframes"}[trigger["kind"]]
            frame_id = f"plate-{self.frame_count + 1:03d}"
            controls = (f'<div class="controls"><button type="button" data-ds-for="{frame_id}" data-ds-motion="play">Replay</button>'
                        f'<button type="button" data-ds-for="{frame_id}" data-ds-motion="stop">Stop</button></div>')
            caption = f"<b>{escape(row['variant'])}</b> on plate source <code>{escape(src['page'])}</code> <code>{escape(src['selector'])}</code>, triggered by {described}"
            _, html = self.plate(src["page"], bound["node"], kind="motion", title=f"Motion {row['variant']}", caption=caption,
                                 config={"motion": trigger}, controls=controls)
            parts.append(f'<h3 id="m-{_slug(row["variant"])}">{escape(row["variant"])}</h3>{html}')
        parts.append("</section>")
        return "".join(parts)

    def traceability(self) -> str:
        showcase, primitives = self.registry["showcase"], self.registry.get("primitives", {})
        components = self.registry.get("productComponents", {}) or {}
        axis_total = sum(len(values) for spec in primitives.values() for values in source.primitive_axes(spec).values())
        state_total = len(showcase["states"])
        surface_total = sum(len(row.get("responsive", {}).get("targets", [])) for row in self.surfaces)
        counts = (("Primitive variant values", axis_total), ("Product components", len(components)),
                  ("State treatments", state_total), ("Motion variants", len(self.registry.get("motionVariants", []) or [])),
                  ("Surface sizes", surface_total), ("Source plates", len(showcase["specimens"])))
        frames = self.specimen_frames
        rows = "".join(
            f"<tr><th scope=\"row\"><a href=\"#{frames.get(row['id'], '')}\">{escape(row['id'])}</a></th>"
            f"<td>{escape(row['subject']['kind'])} {escape(row['subject']['name'])}</td>"
            f"<td>{escape(', '.join(f'{k}={v}' for k, v in row['axes'].items()) or 'base')}</td>"
            f"<td><code>{escape(row['source']['page'])}</code> <code>{escape(row['source']['selector'])}</code></td>"
            f"<td>{escape(row['source']['variant'])} / {escape(row['source']['state'])}</td>"
            f"<td class=\"hash\" title=\"{hashlib.sha256(self.documents[row['source']['page']].encode('utf-8')).hexdigest()}\">"
            f"{hashlib.sha256(self.documents[row['source']['page']].encode('utf-8')).hexdigest()[:12]}</td></tr>"
            for row in showcase["specimens"])
        bindings = "".join(
            f"<tr><th scope=\"row\">{escape(key)}</th><td><code>{escape(str(value.get('path')))}</code></td>"
            f"<td class=\"hash\">{escape(str(value.get('sha256')))}</td></tr>"
            for key, value in sorted(self.registry.get("sourceBindings", {}).items()) if isinstance(value, dict))
        return ('<section class="chapter" id="traceability" aria-labelledby="trace-title"><h2 id="trace-title">Traceability</h2>'
                "<p>The pair checker generated this page only after every registered variant, state, motion variant and surface size "
                "resolved to approved source. Change any listed byte and the page check fails until it is regenerated.</p>"
                '<div class="coverage">' + "".join(f"<div><strong>{value}</strong>{escape(label)}</div>" for label, value in counts) + "</div>"
                '<h3>Source plates</h3><div class="table-scroll"><table><thead><tr><th scope="col">Specimen</th><th scope="col">Subject</th>'
                '<th scope="col">Axes</th><th scope="col">Source</th><th scope="col">Variant / state</th><th scope="col">Page sha256</th>'
                f"</tr></thead><tbody>{rows}</tbody></table></div>"
                '<h3>Frozen inputs</h3><div class="table-scroll"><table><thead><tr><th scope="col">Binding</th><th scope="col">Path</th>'
                f'<th scope="col">sha256</th></tr></thead><tbody>{bindings}'
                f'<tr><th scope="row">registry</th><td><code>design-system.json</code></td><td class="hash">{hashlib.sha256(self.registry_bytes).hexdigest()}</td></tr>'
                f'<tr><th scope="row">markdown</th><td><code>design-system.md</code></td><td class="hash">{hashlib.sha256(self.markdown_bytes).hexdigest()}</td></tr>'
                "</tbody></table></div></section>")

    def render(self) -> str:
        product = escape(str(self.registry.get("product", "")))
        components = self.components()
        surfaces = self.surfaces_section()
        motion = self.motion()
        chapters = (("foundations", "Foundations", sum(len(v) if isinstance(v, dict) else 1 for v in self.registry.get("tokens", {}).values())),
                    ("components", "Components", len(self.registry["showcase"]["specimens"])),
                    ("surfaces", "Surfaces", len(self.surfaces)),
                    ("motion", "Motion", len(self.registry["showcase"]["motion"])),
                    ("traceability", "Traceability", None))
        index = "".join(f'<li><a href="#{anchor}">{label}' + (f"<span>{count}</span>" if count is not None else "") + "</a></li>"
                        for anchor, label, count in chapters)
        platform = self.registry.get("platform") or "hybrid"
        return ("<!doctype html>\n" + '<html lang="en"><head><meta charset="utf-8">'
                f'<meta http-equiv="Content-Security-Policy" content="{escape(self.csp, quote=True)}">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>{product}: design system</title><style>{GALLERY_CSS}</style>"
                + (f"<style>{RUNTIME_CSS}</style>" if self.has_runtime else "") + "</head><body>"
                '<a class="skip" href="#main">Skip to the specimens</a>'
                f'<header class="masthead"><div><h1>{product}</h1><p class="lede">Design system specimen book, derived from the approved HiFi. '
                f"Markdown and JSON remain the contract; this page is regenerated from them and cannot approve anything.</p></div>"
                f'<dl class="provenance"><dt>Platform</dt><dd>{escape(str(platform))}</dd><dt>Registry</dt><dd class="hash">{hashlib.sha256(self.registry_bytes).hexdigest()[:16]}</dd>'
                f'<dt>Approved HiFi</dt><dd><code>{escape(str(self.hifi.get("path")))}</code></dd><dt>HiFi sha256</dt><dd class="hash">{escape(str(self.hifi.get("sha256")))[:16]}</dd></dl></header>'
                f'<div class="book"><nav class="index" aria-label="Specimen book contents"><ol>{index}</ol></nav>'
                f'<main id="main" tabindex="-1">{self.foundations()}{components}{surfaces}{motion}{self.traceability()}</main></div>'
                f"<script>{GALLERY_RUNTIME}</script>"
                + (f"<script>{RUNTIME_GALLERY}</script>" if self.has_runtime else "")
                + (f"<script>{surface_adapter.SURFACE_GALLERY}</script>" if self.surface_bindings else "") + "</body></html>\n")


def render_gallery(registry: dict[str, Any], registry_bytes: bytes, markdown_bytes: bytes, documents: dict[str, str],
                   manifest: dict[str, Any], resolved: dict[str, dict[str, Any]], hifi_binding: dict[str, str],
                   runtime: dict[str, dict[str, Any]] | None = None) -> str:
    return Gallery(registry, registry_bytes, markdown_bytes, documents, manifest, resolved, hifi_binding, runtime).render()
