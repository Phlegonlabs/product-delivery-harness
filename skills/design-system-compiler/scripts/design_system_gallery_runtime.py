"""Source-runtime motion plates for ds-showcase/2 specimen books.

A plate is the full approved surface (ancestors, product CSS, product and
control scripts) copied verbatim into a sandboxed srcdoc frame; the reviewer
connect call is never run, so no reviewer shell or state store mounts. The only
additions are the gallery marker attributes on the bound surface and its
per-target subject copies, the frame configuration, the pinned head runtime,
the inert stopped stylesheet, the pinned focus guard (a background plate never
takes gallery focus), the pinned bootstrap that selects the target and state
view after the copied markup, and the source script order: every product
script occurrence stays at its source position as an inert slot that the pinned
loader activates natively, in source order, after the bootstrap.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

import design_system_showcase as source
import source_script_order as script_order
from design_system_runtime_assets import INITIAL_MOUNT, RUNTIME_BOOT, RUNTIME_FRAME, STOPPED_CSS
from showcase_runtime import reviewer_definitions
from surface_adapter import SURFACE_FOCUS_GUARD

MECHANISM_TEXT = {"waapi": "Web Animations created by the bound product script",
                  "css-animation": "a CSS animation in the state the bound product script establishes"}
ACTIVATION_TEXT = {"viewport": "when the bound subject enters the viewport", "state-entry": "when its state view appears"}


def _subject_edits(subjects: dict[str, dict[str, Any]]) -> tuple[tuple[int, int, str], ...]:
    """Add data-ds-motion-subject="<targets>" to each bound copy's start tag; all other bytes stay verbatim."""
    marks: dict[int, tuple[dict[str, Any], list[str]]] = {}
    for target, node in subjects.items():
        marks.setdefault(node["index"], (node, []))[1].append(target)
    return tuple((node["start"], node["start_end"],
                  source.serialize_start(node["tag"], node["attrs"], extra={"data-ds-motion-subject": " ".join(targets)}))
                 for node, targets in marks.values())


def runtime_plate(gallery: Any, row: dict[str, Any], binding: dict[str, Any]) -> str:
    """Return the figure for one source-runtime motion row."""
    trigger, page, tree = row["trigger"], binding["page"], binding["tree"]
    gallery.frame_count += 1
    frame_id = f"plate-{gallery.frame_count:03d}"
    html = gallery.documents[page]
    order, problems = script_order.inventory(tree, binding["surface"], f"Motion {row['variant']} surface {trigger['surface']}")
    if problems:
        raise ValueError("\n".join(problems))
    html_start, body_start, content = script_order.plate_markup(tree, binding["surface"], order, frame_marker=frame_id,
                                                                edits=_subject_edits(binding["subjects"]))
    css = source.product_css(html)
    reduced = source.reduced_motion_css(css)
    scripts = reviewer_definitions(html) + [script_order.LOADER]
    targets = [target for target in binding["targets"] if target in binding["subjects"]]
    config = {"id": frame_id, "kind": "runtime", "variant": row["variant"], "mechanism": trigger["mechanism"],
              "activation": trigger["activation"]["kind"], "state": trigger["state"], "target": trigger["target"],
              "targets": targets}
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    document = ("<!doctype html>" + html_start + '<head><meta charset="utf-8">'
                + f'<meta http-equiv="Content-Security-Policy" content="{escape(gallery.csp, quote=True)}">'
                + '<meta name="viewport" content="width=device-width,initial-scale=1">'
                + "<style>html,body{margin:0}</style>" + f"<style>{css}</style>"
                + (f'<style data-ds-reduced media="not all">{reduced}</style>' if reduced.strip() else "")
                + f'<style data-ds-stopped media="not all">{STOPPED_CSS}</style>'
                + f'<script type="application/json" id="ds-frame-config">{payload}</script>' + INITIAL_MOUNT
                + script_order.inventory_json(order) + f"<script>{RUNTIME_FRAME}</script><script>{SURFACE_FOCUS_GUARD}</script></head>"
                + body_start + content + f"<script>{RUNTIME_BOOT}</script>"
                + "".join(f"<script>{item}</script>" for item in scripts) + "</body></html>")
    widths = source.canvas_widths(tree)
    width = widths.get(trigger["target"], 0.0) or 360.0
    spec = binding["row"]["specimen"]
    selector = next(item["source"]["selector"] for item in gallery.registry["showcase"]["specimens"] if item["id"] == spec)
    iframe = (f'<iframe data-ds-frame="{frame_id}" data-ds-runtime-frame data-ds-runtime-default="{escape(trigger["target"], quote=True)}" '
              f'title="{escape("Motion " + row["variant"] + " source runtime", quote=True)}" sandbox="allow-scripts" '
              f'referrerpolicy="no-referrer" style="width:{width:g}px" srcdoc="{escape(document, quote=True)}"></iframe>')
    sizes = "".join(
        f'<button type="button" data-ds-for="{frame_id}" data-ds-runtime-target="{escape(target, quote=True)}" '
        f'data-ds-width="{widths.get(target, 0):g}" aria-pressed="{str(target == trigger["target"]).lower()}">{escape(target)}</button>'
        for target in targets)
    controls = (f'<div class="controls"><fieldset><legend>Size</legend>{sizes}</fieldset>'
                f'<button type="button" data-ds-for="{frame_id}" data-ds-runtime="replay">Replay</button>'
                f'<button type="button" data-ds-for="{frame_id}" data-ds-runtime="stop">Stop</button></div>')
    badge = ('<p class="native">HTML demonstration of an approved native design. Not native evidence.</p>'
             if gallery.native(page) else "")
    caption = (f"<b>{escape(row['variant'])}</b> replays {MECHANISM_TEXT[trigger['mechanism']]} for intent "
               f"<code>{escape(trigger['intent'])}</code> on <code>{escape(trigger['surface'])}</code> state "
               f"<code>{escape(trigger['state'])}</code>, starting {ACTIVATION_TEXT[trigger['activation']['kind']]}.<br>"
               f"Bound to <code>{escape(page)}</code> <code>{escape(selector)}</code>; script sha256 "
               f'<code class="hash" title="{escape(trigger["scriptSha256"])}">{escape(trigger["scriptSha256"][:12])}</code>')
    return (f'<figure class="plate runtime" id="{frame_id}" data-ds-phase="pending"><div class="plate-stage">{iframe}</div>'
            f"<figcaption>{caption}{badge}</figcaption>{controls}"
            f'<p class="status" data-ds-status="{frame_id}" aria-live="polite">Pending at target {escape(trigger["target"])}: '
            "loading the source frame.</p></figure>")
