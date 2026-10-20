"""ds-showcase/2 source script order for Surface and source-runtime motion plates.

One occurrence inventory per selected surface lists every classic inline
product script in source order: those inside the copied surface and those
whose parent is a retained ancestor of it (for example a body-level script
before or after the canvas). Each occurrence becomes an inert marker at its
own source position, an unexecuted `<script>` that keeps the unchanged body.
After the plate bootstrap (motion target/state selection, or the public
reviewer connect plus source-control selection), the fixed LOADER replaces
each marker exactly once, in source order, with a native script element. The
browser runs it in place, so `document.currentScript`, its parent and its
siblings are the source ones. There is no eval, wrapper or body rewrite.

The contract is a DOM-complete selected surface: every copied element exists
before the first product script runs. It does not reproduce progressive
parsing or `document.write`. Reviewer definitions and the connect call are
plate infrastructure, not part of the product order. Data scripts and
template contents stay intact and inert. External, module, async, defer,
nomodule or attributed scripts, unsupported placement and the reserved slot
type are findings. At runtime, missing or repeated markers, a thrown
exception or a refused script fails the plate closed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import design_system_showcase as source

SLOT_TYPE = "text/x-ds-source-slot"
SLOT_ATTRIBUTE = "data-ds-source-slot"
# The types a browser runs as classic script (HTML "JavaScript MIME type essence match"), plus an absent or empty type.
CLASSIC_TYPES = frozenset({"", "application/ecmascript", "application/javascript", "application/x-ecmascript",
                           "application/x-javascript", "text/ecmascript", "text/javascript", "text/javascript1.0",
                           "text/javascript1.1", "text/javascript1.2", "text/javascript1.3", "text/javascript1.4",
                           "text/javascript1.5", "text/jscript", "text/livescript", "text/x-ecmascript",
                           "text/x-javascript"})
FOREIGN = frozenset({"svg", "math"})


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _kind(node: dict[str, Any]) -> str:
    """classic, module or data, as the browser would treat the element's type."""
    attrs = node["map"]
    value = attrs.get("type") or ""
    if "type" not in attrs and attrs.get("language"):
        value = "text/" + attrs["language"]
    value = value.strip().casefold()
    return "module" if value == "module" else "classic" if value in CLASSIC_TYPES else "data"


def inventory(tree: source.SourceTree, surface: dict[str, Any], label: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Ordered classic inline product scripts for one selected surface, or findings."""
    from surface_adapter import CALL_START_RE

    reviewer = [match.span() for match in source.REVIEWER_SEGMENT_RE.finditer(tree.html)]
    chain = tree.ancestors(surface)
    retained = {item["index"]: (chain + [surface])[position + 1] for position, item in enumerate(chain) if item["tag"] != "html"}
    slots, problems = [], []
    for node in tree.nodes:
        if node["tag"] != "script" or any(start <= node["start"] < end for start, end in reviewer):
            continue
        ancestors = tree.ancestors(node)
        body = tree.html[node["start_end"]:node["inner_end"]]
        where = f"{label} script at offset {node['start']}"
        if (node["map"].get("type") or "").strip().casefold() == SLOT_TYPE or SLOT_ATTRIBUTE in node["map"]:
            problems.append(f"{where} uses the reserved source slot marker")
            continue
        if any(item["tag"] == "template" for item in ancestors) or _kind(node) == "data":
            continue  # template contents and data scripts never run; they stay verbatim and inert
        inside = surface in ancestors
        if CALL_START_RE.match(body):
            if inside:
                problems.append(f"{where} is a reviewer connect call inside the product surface")
            continue  # outside the surface the connect call is plate infrastructure
        if "src" in node["map"]:
            problems.append(f"{where} is an external script; only classic inline scripts are supported")
        elif _kind(node) == "module":
            problems.append(f"{where} is a module script; only classic inline scripts are supported")
        elif node["attrs"]:
            names = ", ".join(sorted({name for name, _ in node["attrs"]}))
            problems.append(f"{where} has unsupported attributes ({names}); only attribute-free inline scripts are supported")
        elif any(item["tag"] in FOREIGN for item in ancestors):
            problems.append(f"{where} is inside SVG or MathML content")
        elif inside:
            slots.append({"node": node, "body": body, "place": "surface"})
        elif node["parent"] in retained:
            child = retained[node["parent"]]
            slots.append({"node": node, "body": body, "parent": node["parent"],
                          "place": "before" if node["start"] < child["start"] else "after"})
        else:
            problems.append(f"{where} has no retained source parent in the selected surface plate")
    if problems:
        return None, problems
    for index, slot in enumerate(slots):
        slot.update(index=index, sha256=_sha(slot["body"]))
    return {"slots": slots}, []


def marker(slot: dict[str, Any]) -> str:
    return f'<script type="{SLOT_TYPE}" {SLOT_ATTRIBUTE}="{slot["index"]}">{slot["body"]}</script>'


def around(order: dict[str, Any]) -> dict[int, tuple[str, str]]:
    """Markers for slots outside the surface, at their side of the retained child, per retained parent."""
    sides: dict[int, tuple[str, str]] = {}
    for slot in order["slots"]:
        if slot["place"] == "surface":
            continue
        before, after = sides.get(slot["parent"], ("", ""))
        sides[slot["parent"]] = (before + marker(slot), after) if slot["place"] == "before" else (before, after + marker(slot))
    return sides


def edit_surface(tree: source.SourceTree, surface: dict[str, Any], content: str,
                 edits: list[tuple[int, int, str]]) -> str:
    """Apply absolute-offset edits inside the surface's copied inner markup; all other bytes stay verbatim."""
    inner = tree.html[surface["start_end"]:surface["inner_end"]]
    if not inner or content.count(inner) != 1:
        raise ValueError("selected surface is not uniquely addressable for its plate")
    marked, last = inner, None
    for start, end, text in sorted(edits, reverse=True):
        if last is not None and end > last:
            raise ValueError("selected surface plate edits overlap")
        last = start
        offset = surface["start_end"]
        marked = marked[:start - offset] + text + marked[end - offset:]
    return content.replace(inner, marked, 1)


def plate_markup(tree: source.SourceTree, surface: dict[str, Any], order: dict[str, Any], *, frame_marker: str,
                 edits: tuple[tuple[int, int, str], ...] = ()) -> tuple[str, str, str]:
    """The copied surface plate markup with every source script occurrence as an inert marker."""
    html_start, body_start, content = source.fragment(tree, surface, marker=frame_marker, around=around(order))
    slots = [(slot["node"]["start"], slot["node"]["end"], marker(slot)) for slot in order["slots"] if slot["place"] == "surface"]
    return html_start, body_start, edit_surface(tree, surface, content, slots + list(edits))


def inventory_json(order: dict[str, Any]) -> str:
    payload = json.dumps({"count": len(order["slots"]), "sha256": [slot["sha256"] for slot in order["slots"]]})
    return f'<script type="application/json" id="ds-source-order">{payload}</script>'


def bodies(order: dict[str, Any] | None) -> list[str]:
    return [slot["body"] for slot in order["slots"]] if order else []


# Runs once after the plate bootstrap. Each inert marker is replaced by a native classic script with the same body,
# in source order, so the browser executes it in place with the source currentScript, parent and siblings.
LOADER = r"""(() => {
  "use strict";
  const fail = message => document.dispatchEvent(new CustomEvent("ds-source-order", {detail: {error: String(message).slice(0, 160)}}));
  let expected = -1;
  try { expected = JSON.parse(document.getElementById("ds-source-order").textContent).count; } catch (_) {}
  const markers = Array.from(document.querySelectorAll('script[type="text/x-ds-source-slot"]'));
  if (!Number.isInteger(expected) || markers.length !== expected
      || markers.some((item, index) => item.getAttribute("data-ds-source-slot") !== String(index))) {
    fail("source script markers are missing, repeated or out of order");
    return;
  }
  document.addEventListener("securitypolicyviolation", event => {
    if (/^script-src/.test(String(event.effectiveDirective || event.violatedDirective || ""))) fail("the content security policy refused a source script");
  });
  for (const item of markers) {
    let thrown = null;
    const caught = event => { if (thrown === null) thrown = String(event.message || "error"); };
    const native = document.createElement("script");
    native.textContent = item.textContent;
    window.addEventListener("error", caught);
    try { item.replaceWith(native); } finally { window.removeEventListener("error", caught); }
    if (thrown !== null) { fail("source script " + item.getAttribute("data-ds-source-slot") + " failed: " + thrown); return; }
  }
})();"""
