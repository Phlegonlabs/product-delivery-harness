"""ds-showcase/2 Surface plates: the approved page's own reviewer infrastructure.

A schema2 Surface plate runs the real public reviewer runtime, so product code
that calls the reviewer runtime (for example a product `go` that selects a
state) works as it does in the approved HiFi. The adapter copies the page's
genuine target and state controls and page navigation verbatim into one hidden,
inert container outside the product surface. It never copies the reviewer shell
root, token panels, overview links or other visible reviewer chrome. The page's
own connect call is filtered and replaced by exactly one public
`connectHifiReviewer` call with closed literal data: the approved package
identity, the approved page and no storage.

SURFACE_FRAME drives approved targets and states only by clicking those copied
source controls, and reports the runtime's public snapshot. It runs after the
connect call and selects the initial target and state before the product
scripts run from their source slots (source_script_order). SURFACE_GALLERY
reflects that snapshot into the gallery controls. Legacy ds-showcase/1 Surface
plates, component plates and source-runtime motion plates do not use this
module.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import design_system_showcase as source
import source_script_order as script_order

# SHA-256 of the reviewed public reviewer runtime bodies whose connect contract this adapter uses.
SUPPORTED_REVIEWER_RUNTIMES = frozenset({"854fc83eca20f90bbb976cd8555dba241018cf6adc891be6e7b604d011427597"})
CALL_START_RE = re.compile(r"^\s*(?:window\.)?connectHifiReviewer\s*\(")
CONNECT_CALL_RE = re.compile(r"^\s*(?:window\.)?connectHifiReviewer\((?P<options>\s*\{[^<>()]*\}\s*)?\)\s*;?\s*$")
PACKAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:/._-]{0,127}$")
INFRASTRUCTURE_OPEN = ('<div data-ds-reviewer-infrastructure hidden inert aria-hidden="true" '
                       'style="display:none!important">')
UNSAFE_MARKUP_RE = re.compile(r"<\s*(?:script|form|iframe|object|embed|style|link|meta|base)\b", re.IGNORECASE)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _outer(tree: source.SourceTree, node: dict[str, Any]) -> str:
    return tree.html[node["start"]:node["end"]]


def _inside(node: dict[str, Any], outer: dict[str, Any]) -> bool:
    return outer["start"] <= node["start"] and node["end"] <= outer["end"]


def _scripts(tree: source.SourceTree) -> list[tuple[int, str, str]]:
    """(offset, attributes, body) of every script element, from exact source offsets."""
    rows = []
    for node in tree.nodes:
        if node["tag"] == "script":
            attrs = tree.html[node["start"] + len("<script"):node["start_end"] - 1]
            rows.append((node["start"], attrs, tree.html[node["start_end"]:node["inner_end"]]))
    return rows


def _usable(node: dict[str, Any]) -> bool:
    attrs = node["map"]
    return (node["tag"] == "button" and (attrs.get("type") or "").casefold() == "button"
            and "disabled" not in attrs and (attrs.get("aria-disabled") or "").casefold() != "true")


def _connect_options(body: str, label: str, problems: list[str]) -> dict[str, str] | None:
    match = CONNECT_CALL_RE.fullmatch(body)
    if match is None:
        problems.append(f"{label} reviewer connect call is not the supported public call shape")
        return None
    if not match.group("options"):
        return {}
    try:
        options = json.loads(match.group("options"))
    except json.JSONDecodeError:
        options = None
    if not isinstance(options, dict) or set(options) - {"packageId"} or not all(
            isinstance(value, str) and PACKAGE_ID_RE.fullmatch(value) for value in options.values()):
        problems.append(f"{label} reviewer connect call options must be a closed literal packageId")
        return None
    return options


def surface_binding(tree: source.SourceTree, page: str, row: dict[str, Any],
                    pages: set[str]) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate and extract one Surface plate's reviewer infrastructure and script order."""
    surface_id = str(row.get("id"))
    label = f"Surface {surface_id} on {page}"
    problems: list[str] = []
    nodes = [node for node in tree.nodes if node["map"].get("data-ui-surface") == surface_id]
    canvas = tree.first(lambda item: "data-hifi-canvas" in item["map"])
    if len(nodes) != 1 or canvas is None:
        return None, [f"{label} needs exactly one product surface inside a HiFi canvas"]
    surface = nodes[0]
    states = [str(item) for item in row.get("states", []) if "n/a" not in str(item).casefold()]
    targets = [str(item) for item in (row.get("responsive") or {}).get("targets", [])]
    segments = [match.span() for match in source.REVIEWER_SEGMENT_RE.finditer(tree.html)]
    runtime_spans = [match.span() for match in source.RUNTIME_SEGMENT_RE.finditer(tree.html)]

    def in_segment(offset: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= offset < end for start, end in spans)

    scripts = [item for item in _scripts(tree) if source._executable(item[1], item[2]) or CALL_START_RE.match(item[2])]
    runtime = [body for offset, attrs, body in scripts if in_segment(offset, runtime_spans)]
    if len(runtime) != 1 or _sha(runtime[0]) not in SUPPORTED_REVIEWER_RUNTIMES:
        problems.append(f"{label} needs exactly one supported public reviewer runtime")
    product = [(offset, body) for offset, attrs, body in scripts if not in_segment(offset, segments)]
    calls = [(offset, body) for offset, body in product if CALL_START_RE.match(body)]
    options = None
    if len(calls) != 1:
        problems.append(f"{label} needs exactly one reviewer connect call; found {len(calls)}")
    else:
        options = _connect_options(calls[0][1], label, problems)
        if surface["start"] <= calls[0][0] < surface["end"]:
            problems.append(f"{label} reviewer connect call is inside the product surface")
    slices = []
    for marker in ("data-hifi-page-nav", "data-hifi-responsive-controls", "data-hifi-state-controls"):
        found = [node for node in tree.nodes if marker in node["map"]]
        if len(found) != 1 or tree.in_product(found[0]) or _inside(found[0], canvas):
            problems.append(f"{label} needs exactly one {marker} element outside the product")
        else:
            slices.append(found[0])
    if len(slices) == 3:
        nav, target_box, state_box = slices
        links = [node["map"].get("href") for node in tree.nodes if node["tag"] == "a" and _inside(node, nav) and node is not nav]
        if len(set(links)) != len(links) or page not in links or not all(isinstance(href, str) and href in pages for href in links):
            problems.append(f"{label} page navigation must list each approved package page once, including {page}")
        target_nodes = [node for node in tree.nodes if "data-hifi-target-control" in node["map"]]
        values = [node["map"]["data-hifi-target-control"] for node in target_nodes]
        if values != targets or not all(_usable(node) and _inside(node, target_box) for node in target_nodes):
            problems.append(f"{label} target controls must be enabled buttons for exactly the approved targets {targets}")
        if (canvas["map"].get("data-hifi-targets") or "").split() != targets:
            problems.append(f"{label} canvas targets do not match the approved targets {targets}")
        state_nodes = [node for node in tree.nodes if "data-hifi-state-control" in node["map"]]
        mine = [node for node in state_nodes if node["map"].get("data-hifi-state-surface") == surface_id]
        if [node["map"]["data-hifi-state-control"] for node in mine] != states or len(mine) != len(state_nodes) \
                or not all(_usable(node) and _inside(node, state_box) for node in state_nodes):
            problems.append(f"{label} state controls must be enabled buttons for exactly the approved states {states}")
        markup = "".join(_outer(tree, node) for node in sorted(slices, key=lambda item: item["start"]))
        if UNSAFE_MARKUP_RE.search(markup):
            problems.append(f"{label} reviewer controls contain executable or document-level markup")
    order, found = script_order.inventory(tree, surface, label)
    problems.extend(found)
    if problems:
        return None, problems
    data = dict(options or {}, page=page, storage=None)
    connect = "connectHifiReviewer(" + json.dumps(data, sort_keys=True, ensure_ascii=True) + ")"
    # Reviewer definitions and the pinned connect are infrastructure; product scripts run later from their source slots.
    infrastructure = [body for offset, attrs, body in scripts if in_segment(offset, runtime_spans)] + [connect]
    return {"surface": surface_id, "infrastructure": INFRASTRUCTURE_OPEN + markup + "</div>",
            "connect": connect, "scripts": infrastructure, "order": order, "states": states, "targets": targets}, []


def resolve_surfaces(trees: dict[str, source.SourceTree], manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Bind every manifest Surface whose page and product node exist; any finding fails rendering."""
    rows = [row for row in manifest.get("surfaces", []) if isinstance(row, dict)]
    pages = {"index.html"} | {str(item.get("path")) for item in manifest.get("pages", []) if isinstance(item, dict)}
    bindings: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for row in rows:
        tree = trees.get(row.get("page"))
        if tree is None or source.surface_node(tree, str(row.get("id"))) is None:
            continue
        binding, found = surface_binding(tree, row["page"], row, pages)
        problems.extend(found)
        if binding:
            bindings[binding["surface"]] = binding
    return bindings, problems


# Runs in the plate head before any product code. A background plate never takes focus or scroll from the
# gallery: programmatic focus applies only while this frame already has focus, so user operations keep theirs.
SURFACE_FOCUS_GUARD = r"""(() => {
  "use strict";
  for (const Owner of [window.HTMLElement, window.SVGElement]) {
    const native = Owner && Owner.prototype.focus;
    if (typeof native === "function") Owner.prototype.focus = function (...args) { if (document.hasFocus()) return native.apply(this, args); };
  }
})();"""

SURFACE_FRAME = r"""(() => {
  "use strict";
  const config = JSON.parse(document.getElementById("ds-frame-config").textContent);
  const canvas = document.querySelector("[data-hifi-canvas]");
  const reduced = document.querySelector("style[data-ds-reduced]");
  const boxes = document.querySelectorAll("[data-ds-reviewer-infrastructure]");
  const box = boxes.length === 1 ? boxes[0] : null;
  const runtime = document.__hifiReviewerRuntime;
  let error = !box ? "the hidden reviewer controls are missing"
    : !runtime || typeof runtime.snapshot !== "function" ? "the public reviewer connect did not initialize" : "";
  const measured = () => canvas || document.body;
  let last = "";
  function report() {
    const height = Math.ceil(measured().getBoundingClientRect().bottom + window.scrollY);
    parent.postMessage({type: "ds-frame-size", id: config.id, height}, "*");
    let snap = {};
    if (!error) { try { snap = runtime.snapshot(); } catch (_) { error = "the reviewer snapshot failed"; } }
    const body = {type: "ds-surface", id: config.id, surface: config.surface, error,
      state: typeof snap.productState === "string" ? snap.productState : null, target: typeof snap.target === "string" ? snap.target : null};
    const text = JSON.stringify(body);
    if (text !== last) { last = text; parent.postMessage(body, "*"); }
  }
  // Approved targets and states change only through the copied source controls' own click handlers.
  function press(attribute, value) {
    if (error) return report();
    const matches = Array.from(box.querySelectorAll("button[" + attribute + "]")).filter(item => item.getAttribute(attribute) === value &&
      (attribute !== "data-hifi-state-control" || item.getAttribute("data-hifi-state-surface") === config.surface));
    if (matches.length !== 1) { error = "no unique source control for " + String(value).slice(0, 40); return report(); }
    try { matches[0].click(); } catch (failure) { error = String(failure && failure.message || failure).slice(0, 120); }
    report();
  }
  window.addEventListener("message", event => {
    const data = event.data;
    if (event.source !== parent || !data || typeof data !== "object") return;
    if (data.type === "ds-target" && typeof data.target === "string") {
      if (!error && runtime.snapshot().target !== data.target) press("data-hifi-target-control", data.target);
      // The physical width between approved sizes is gallery geometry, never a target identity.
      if (canvas) { if (Number.isFinite(data.width)) canvas.style.width = data.width + "px"; else canvas.style.removeProperty("width"); }
      requestAnimationFrame(report);
    } else if (data.type === "ds-state" && typeof data.state === "string") {
      if (error || runtime.snapshot().productState !== data.state) press("data-hifi-state-control", data.state);
    } else if (data.type === "ds-reduced" && reduced) reduced.media = data.on ? "all" : "not all";
  });
  document.addEventListener("click", event => {
    const link = event.target.closest ? event.target.closest("a[href]") : null;
    if (link && !link.getAttribute("href").startsWith("#")) { event.preventDefault(); parent.postMessage({type: "ds-navigation", id: config.id, href: link.getAttribute("href")}, "*"); }
  }, true);
  document.addEventListener("submit", event => event.preventDefault(), true);
  // Product operations change the runtime; its own control and canvas attributes signal each change.
  if (box && typeof MutationObserver === "function") {
    const observer = new MutationObserver(report);
    observer.observe(box, {subtree: true, attributes: true, attributeFilter: ["aria-pressed"]});
    if (canvas) observer.observe(canvas, {attributes: true, attributeFilter: ["data-hifi-target"]});
  }
  if ("ResizeObserver" in window) new ResizeObserver(report).observe(measured());
  window.addEventListener("load", report);
  // A missing or repeated source slot, a thrown source script or a refused script makes the plate unavailable.
  document.addEventListener("ds-source-order", event => {
    if (!error) error = String(event.detail && event.detail.error || "a source script failed").slice(0, 120);
    report();
  });
  // This frame runs before the source script loader: select the initial approved target and state through the source controls.
  if (typeof config.target === "string") press("data-hifi-target-control", config.target);
  if (typeof config.state === "string") press("data-hifi-state-control", config.state);
  report();
})();"""

SURFACE_GALLERY = r"""(() => {
  "use strict";
  const frames = new Map();
  for (const frame of document.querySelectorAll("iframe[data-ds-surface-frame]")) frames.set(frame.dataset.dsFrame, frame);
  if (!frames.size) return;
  const clip = value => String(value === null || value === undefined ? "" : value).slice(0, 64);
  window.addEventListener("message", event => {
    const data = event.data;
    if (!data || typeof data !== "object" || data.type !== "ds-surface" || typeof data.id !== "string") return;
    const frame = frames.get(data.id);
    if (!frame || event.source !== frame.contentWindow) return;
    const figure = frame.closest("figure");
    const status = figure && figure.querySelector("[data-ds-status]");
    if (!figure || !status) return;
    if (data.error) {
      figure.setAttribute("data-ds-surface", "invalid");
      status.textContent = "Surface unavailable: " + clip(data.error) + ". The gallery does not substitute a state.";
      return;
    }
    const select = figure.querySelector("select[data-ds-state-for]");
    if (select && Array.from(select.options).some(option => option.value === data.state)) select.value = data.state;
    const width = parseFloat(frame.style.width);
    for (const button of figure.querySelectorAll("button[data-ds-target]"))
      button.setAttribute("aria-pressed", String(button.dataset.dsTarget === data.target && Number(button.dataset.dsWidth) === width));
    const text = "Source state " + clip(data.state) + " at approved target " + clip(data.target) + ".";
    if (figure.getAttribute("data-ds-surface") !== "live" || figure.getAttribute("data-ds-source") !== text) status.textContent = text;
    figure.setAttribute("data-ds-surface", "live");
    figure.setAttribute("data-ds-source", text);
  });
})();"""
