"""design-system/4 showcase: source-bound specimens, coverage and frame sources.

The registry never stores styles. Each specimen names an element in the
approved, hash-checked HiFi package; the gallery copies that element, its
ancestor chain and the page's product CSS verbatim. Anything that cannot be
resolved to approved source is a finding, never a guessed sample.
"""

from __future__ import annotations

import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any, Callable

from animation_provenance import source_status

SHOWCASE_SCHEMA = "ds-showcase/1"
# ds-showcase/2 keeps every /1 rule and adds source-runtime motion (showcase_runtime).
SHOWCASE_SCHEMAS = (SHOWCASE_SCHEMA, "ds-showcase/2")
SPECIMEN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SELECTOR_RE = re.compile(r"^(?:[A-Za-z][\w-]*|\.[A-Za-z][\w-]*|#[A-Za-z][\w-]*)$")
PAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.html$")
CONTROL_STATES = ("default", "hover", "focus-visible", "active", "disabled")
PSEUDO_STATES = ("hover", "focus", "focus-visible", "focus-within", "active")
STATE_MODES = ("rendered", "pseudo", "not_applicable")
MOTION_KINDS = ("attribute", "class", "animation")
PRIMITIVE_META_KEYS = {"layer", "dsId", "class", "defaults"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
REVIEWER_SEGMENT_RE = re.compile(
    r"<!-- hifi-reviewer:(css|runtime):start -->[\s\S]*?<!-- hifi-reviewer:\1:end -->")
RUNTIME_SEGMENT_RE = re.compile(
    r"<!-- hifi-reviewer:runtime:start -->([\s\S]*?)<!-- hifi-reviewer:runtime:end -->")
MANIFEST_RE = re.compile(
    r'<script\s+id=["\']ui-hifi-manifest["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>", re.IGNORECASE)
STYLE_RE = re.compile(r"<style\b[^>]*>([\s\S]*?)</style>", re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script\b([^>]*)>([\s\S]*?)</script>", re.IGNORECASE)
REVIEWER_CALL_RE = re.compile(r"^\s*(?:window\.)?connectHifiReviewer\(\)\s*;?\s*$")


class SourceTree(HTMLParser):
    """Element tree with exact source offsets for verbatim extraction."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self.html = html
        self.line_starts = [0] + [match.end() for match in re.finditer(r"\n", html)]
        self.nodes: list[dict[str, Any]] = []
        self._stack: list[dict[str, Any]] = []
        self.feed(html)
        self.close()
        for node in self._stack:
            node["end"] = node["inner_end"] = len(html)

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def _open(self, tag: str, attrs: list[tuple[str, str | None]], void: bool) -> None:
        start = self._offset()
        text = self.get_starttag_text() or ""
        node = {"tag": tag, "attrs": attrs, "map": dict(attrs), "start": start,
                "start_end": start + len(text), "end": None, "inner_end": None,
                "parent": self._stack[-1]["index"] if self._stack else None, "index": len(self.nodes)}
        self.nodes.append(node)
        if void:
            node["end"] = node["inner_end"] = node["start_end"]
        else:
            self._stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, tag in VOID)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        start = self._offset()
        close = self.html.find(">", start)
        end = close + 1 if close >= 0 else len(self.html)
        for position in range(len(self._stack) - 1, -1, -1):
            if self._stack[position]["tag"] == tag:
                for node in self._stack[position + 1:]:
                    node["end"] = node["inner_end"] = start
                self._stack[position]["inner_end"] = start
                self._stack[position]["end"] = end
                del self._stack[position:]
                break

    def ancestors(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        chain = []
        parent = node["parent"]
        while parent is not None:
            chain.append(self.nodes[parent])
            parent = self.nodes[parent]["parent"]
        return list(reversed(chain))

    def in_product(self, node: dict[str, Any]) -> bool:
        return any("data-ui-surface" in item["map"] for item in self.ancestors(node) + [node])

    def first(self, predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
        return next((node for node in self.nodes if predicate(node)), None)


def selector_matches(node: dict[str, Any], selector: str) -> bool:
    if selector.startswith("."):
        return selector[1:] in (node["map"].get("class") or "").split()
    if selector.startswith("#"):
        return node["map"].get("id") == selector[1:]
    return node["tag"] == selector.lower()


def product_html(html: str) -> str:
    """Remove the reviewer CSS/runtime segments; product source stays verbatim."""
    return REVIEWER_SEGMENT_RE.sub("", html)


def product_css(html: str) -> str:
    return "\n".join(STYLE_RE.findall(product_html(html)))


def analysis_css(html: str) -> str:
    return re.sub(r"/\*[\s\S]*?\*/", "", product_css(html))


def _reduced_motion_ranges(css: str) -> list[tuple[int, int, int, int]]:
    blocks = []
    for match in re.finditer(r"@media\b([^{}]*)\{", css, re.IGNORECASE):
        if not re.search(r"prefers-reduced-motion\s*:\s*reduce", match.group(1), re.IGNORECASE):
            continue
        depth, cursor = 1, match.end()
        while cursor < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[cursor], 0)
            cursor += 1
        blocks.append((match.start(), cursor, match.end(), cursor - 1))
    return blocks


def reduced_motion_css(css: str) -> str:
    """Return the bodies of the source prefers-reduced-motion: reduce blocks."""
    return "\n".join(css[body_start:body_end] for _, _, body_start, body_end in _reduced_motion_ranges(css))


def animation_source_backed(css: str, node: dict[str, Any], ancestors=()) -> bool:
    """Resolve unconditional animation provenance outside reduced-motion rules."""
    return animation_source_status(css, node, ancestors) == "source_backed"


def animation_source_status(css: str, node: dict[str, Any], ancestors=()) -> str:
    """Classify source only; registry triggers and coverage remain compiler-owned."""
    for start, end, _, _ in reversed(_reduced_motion_ranges(css)):
        css = css[:start] + css[end:]
    return source_status(css, node, ancestors)


def source_preflight(documents: dict[str, str]) -> list[str]:
    """Report bounded source limitations without a registry or approval verdict."""
    findings = []
    animation_declaration = re.compile(r"(?:^|[;{])\s*(?:-webkit-)?animation(?:-[\w-]+)?\s*:", re.I)
    for page, html in documents.items():
        tree = SourceTree(product_html(html))
        css = analysis_css(html)
        specimens = [node for node in tree.nodes if tree.in_product(node)
                     and "data-specimen-variant" in node["map"] and "data-specimen-state" in node["map"]]
        if not animation_declaration.search(css) and not any(
                animation_declaration.search(node["map"].get("style") or "") for node in specimens):
            continue
        for node in specimens:
            if animation_source_status(css, node, tree.ancestors(node)) == "unresolved":
                findings.append(f"{page}: static animation provenance is unresolved for an annotated specimen; "
                                "confirm its intended registry trigger before compilation")
                break
    if len(findings) > 25:
        return findings[:25] + [f"{len(findings) - 25} additional pages have source limitations"]
    return findings


def container_rules(css: str) -> list[str]:
    return sorted({" ".join(item.split()) for item in re.findall(r"@container\b([^{}]*)\{", css)})


def product_scripts(html: str, *, with_controls: bool) -> list[str]:
    """Executable scripts for live surface plates, in source order."""
    scripts = []
    if with_controls:
        for segment in RUNTIME_SEGMENT_RE.findall(html):
            scripts.extend(body for attrs, body in SCRIPT_RE.findall(segment) if _executable(attrs, body))
        scripts.extend(body for attrs, body in SCRIPT_RE.findall(product_html(html)) if _executable(attrs, body))
    return scripts


def _executable(attrs: str, body: str) -> bool:
    kind = re.search(r"\btype\s*=\s*[\"']?([^\"'\s>]+)", attrs, re.IGNORECASE)
    if kind and kind.group(1).casefold() not in {"text/javascript", "module", "application/javascript"}:
        return False
    return "src=" not in attrs.casefold() and bool(body.strip()) and REVIEWER_CALL_RE.match(body) is None


def load_hifi_package(entry_bytes: bytes, read_child: Callable[[str], bytes | None]) -> tuple[dict[str, str], dict[str, Any], list[str]]:
    """Return {page: html} for the entry and every hash-checked manifest child."""
    import hashlib

    problems: list[str] = []
    try:
        entry = entry_bytes.decode("utf-8")
        matches = list(MANIFEST_RE.finditer(entry))
        manifest = json.loads(matches[0].group("data")) if len(matches) == 1 else None
    except (UnicodeError, json.JSONDecodeError) as exc:
        return {}, {}, [f"design-system/4 HiFi entry cannot be read: {exc}"]
    if not isinstance(manifest, dict) or manifest.get("schema") != "ui-hifi/2":
        return {}, {}, ["design-system/4 requires an approved ui-hifi/2 entry with one manifest"]
    documents = {"index.html": entry}
    for row in manifest.get("pages", []) if isinstance(manifest.get("pages"), list) else []:
        name = row.get("path") if isinstance(row, dict) else None
        if not isinstance(name, str) or PAGE_RE.fullmatch(name) is None:
            problems.append("design-system/4 HiFi manifest page names must be sibling HTML files")
            continue
        payload = read_child(name)
        if payload is None:
            problems.append(f"design-system/4 HiFi page {name} is missing or not a safe regular file")
        elif hashlib.sha256(payload).hexdigest() != row.get("sha256"):
            problems.append(f"design-system/4 HiFi page {name} does not match its manifest sha256")
        else:
            documents[name] = payload.decode("utf-8", errors="strict")
    return documents, manifest, problems


def _subject_key(subject: Any) -> tuple[str, str] | None:
    if isinstance(subject, dict) and set(subject) == {"kind", "name"} and subject["kind"] in {"primitive", "component"} \
            and isinstance(subject["name"], str):
        return subject["kind"], subject["name"]
    return None


def primitive_axes(spec: Any) -> dict[str, list[str]]:
    """Closed variant axes: every list-of-strings field except metadata."""
    if not isinstance(spec, dict):
        return {}
    return {key: value for key, value in spec.items() if key not in PRIMITIVE_META_KEYS
            and isinstance(value, list) and value and all(isinstance(item, str) for item in value)}


def registry_findings(registry: dict[str, Any]) -> list[str]:
    """Closed shape and complete coverage against the registry itself."""
    showcase = registry.get("showcase")
    if not isinstance(showcase, dict) or set(showcase) != {"schema", "specimens", "states", "motion"} \
            or showcase.get("schema") not in SHOWCASE_SCHEMAS:
        return ["design-system.json design-system/4 showcase must be ds-showcase/1 or ds-showcase/2 with exactly "
                "schema, specimens, states and motion"]
    v2 = showcase["schema"] == SHOWCASE_SCHEMAS[1]
    problems: list[str] = []
    primitives = registry.get("primitives") if isinstance(registry.get("primitives"), dict) else {}
    components = registry.get("productComponents") if isinstance(registry.get("productComponents"), dict) else {}
    specimens: dict[str, dict[str, Any]] = {}
    covered_axes: set[tuple[str, str, str]] = set()
    specimen_subjects: set[tuple[str, str]] = set()
    for row in showcase.get("specimens") if isinstance(showcase.get("specimens"), list) else [None]:
        if not isinstance(row, dict) or set(row) != {"id", "subject", "axes", "source"}:
            problems.append("showcase specimens must contain exactly id, subject, axes and source")
            continue
        specimen_id, subject, axes, source = row["id"], _subject_key(row["subject"]), row["axes"], row["source"]
        if not isinstance(specimen_id, str) or SPECIMEN_ID_RE.fullmatch(specimen_id) is None or specimen_id in specimens:
            problems.append(f"showcase specimen id {specimen_id!r} must be unique lowercase kebab-case")
            continue
        specimens[specimen_id] = row
        if subject is None or subject[1] not in (primitives if subject[0] == "primitive" else components):
            problems.append(f"showcase specimen {specimen_id} names an unregistered subject")
            continue
        specimen_subjects.add(subject)
        if not isinstance(source, dict) or set(source) != {"page", "selector", "variant", "state"} or not all(
                isinstance(source.get(key), str) and source[key].strip() for key in source):
            problems.append(f"showcase specimen {specimen_id} source must contain page, selector, variant and state")
            continue
        if PAGE_RE.fullmatch(source["page"]) is None or SELECTOR_RE.fullmatch(source["selector"]) is None:
            problems.append(f"showcase specimen {specimen_id} source must name a package page and a simple selector")
        allowed = primitive_axes(primitives.get(subject[1])) if subject[0] == "primitive" else {}
        if not isinstance(axes, dict) or any(key not in allowed or value not in allowed[key] for key, value in axes.items()):
            problems.append(f"showcase specimen {specimen_id} axes must use the subject's closed variant sets")
            continue
        variant_tokens = source["variant"].split()
        for key, value in axes.items():
            if value not in variant_tokens:
                problems.append(f"showcase specimen {specimen_id} source variant must carry axis value {value}")
            covered_axes.add((subject[1], key, value))
    for name, spec in primitives.items():
        axes = primitive_axes(spec)
        if ("primitive", name) not in specimen_subjects:
            problems.append(f"showcase is missing a source specimen for primitive {name}")
        for key, values in axes.items():
            for value in values:
                if (name, key, value) not in covered_axes:
                    problems.append(f"showcase is missing primitive {name} {key}={value}")
    for name in components:
        if ("component", name) not in specimen_subjects:
            problems.append(f"showcase is missing a source specimen for product component {name}")
    required_states = {("primitive", name, state) for name, spec in primitives.items()
                       if isinstance(spec, dict) and spec.get("layer") == "control" for state in CONTROL_STATES}
    required_states |= {("component", name, state) for name, spec in components.items() if isinstance(spec, dict)
                        for state in spec.get("states", []) if isinstance(state, str)}
    seen_states: set[tuple[str, str, str]] = set()
    for row in showcase.get("states") if isinstance(showcase.get("states"), list) else [None]:
        key_set = {"subject", "state", "mode"} | ({"reason"} if isinstance(row, dict) and row.get("mode") == "not_applicable" else {"specimen"})
        subject = _subject_key(row.get("subject")) if isinstance(row, dict) else None
        if not isinstance(row, dict) or set(row) != key_set or subject is None or row["mode"] not in STATE_MODES \
                or not isinstance(row["state"], str):
            problems.append("showcase states must use subject, state, mode and a specimen or not_applicable reason")
            continue
        key = (subject[0], subject[1], row["state"])
        if key in seen_states:
            problems.append(f"showcase states duplicate {subject[1]} {row['state']}")
        seen_states.add(key)
        if row["mode"] == "not_applicable":
            if not isinstance(row["reason"], str) or len(row["reason"].strip()) < 8:
                problems.append(f"showcase state {subject[1]} {row['state']} not_applicable needs a concrete reason")
            continue
        specimen = specimens.get(row["specimen"])
        if specimen is None or _subject_key(specimen["subject"]) != subject:
            problems.append(f"showcase state {subject[1]} {row['state']} must name a specimen of that subject")
        elif row["mode"] == "rendered" and specimen["source"].get("state") != row["state"]:
            problems.append(f"showcase rendered state {subject[1]} {row['state']} needs a source element in that state")
        elif row["mode"] == "pseudo" and row["state"] not in PSEUDO_STATES:
            problems.append(f"showcase pseudo state {row['state']} must be one of " + ", ".join(PSEUDO_STATES))
    for kind, name, state in sorted(required_states - seen_states):
        problems.append(f"showcase is missing {kind} {name} state {state}")
    variants = registry.get("motionVariants") if isinstance(registry.get("motionVariants"), list) else []
    motion_covered, intents = set(), set()
    kinds = MOTION_KINDS + (("source-runtime",) if v2 else ())
    for row in showcase.get("motion") if isinstance(showcase.get("motion"), list) else [None]:
        trigger = row.get("trigger") if isinstance(row, dict) else None
        if not isinstance(row, dict) or set(row) != {"variant", "specimen", "trigger"} or not isinstance(trigger, dict) \
                or trigger.get("kind") not in kinds:
            problems.append("showcase motion rows must contain variant, specimen and an attribute, class or animation trigger"
                            + (" or a source-runtime trigger" if v2 else ""))
            continue
        if trigger["kind"] == "source-runtime":
            from showcase_runtime import trigger_findings
            problems.extend(trigger_findings(row["variant"], trigger))
            if str(trigger.get("intent")) in intents:
                problems.append(f"showcase motion intent {trigger['intent']} is bound by more than one source-runtime row")
            intents.add(str(trigger.get("intent")))
        else:
            expected = {"attribute": {"kind", "name", "from", "to"}, "class": {"kind", "name"}, "animation": {"kind"}}[trigger["kind"]]
            if set(trigger) != expected or not all(isinstance(trigger[key], str) and trigger[key] for key in expected):
                problems.append(f"showcase motion {row['variant']} {trigger['kind']} trigger must contain exactly " + ", ".join(sorted(expected)))
        if row["variant"] not in variants:
            problems.append(f"showcase motion names unregistered variant {row['variant']!r}")
        if row["specimen"] not in specimens:
            problems.append(f"showcase motion {row['variant']} names an unknown specimen")
        motion_covered.add(row["variant"])
    for variant in variants:
        if variant not in motion_covered:
            problems.append(f"showcase is missing a source motion specimen for {variant}")
    return problems


def resolve(registry: dict[str, Any], documents: dict[str, str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Bind every specimen to its first matching approved product element."""
    problems: list[str] = []
    trees = {page: SourceTree(html) for page, html in documents.items()}
    css = {page: analysis_css(html) for page, html in documents.items()}
    resolved: dict[str, dict[str, Any]] = {}
    showcase = registry.get("showcase", {})
    v2 = showcase.get("schema") == SHOWCASE_SCHEMAS[1]
    if v2:
        from showcase_runtime import closed_open_claim, shared_pseudo_rule
    for row in showcase.get("specimens", []):
        source = row["source"]
        tree = trees.get(source["page"])
        if tree is None:
            problems.append(f"showcase specimen {row['id']} page {source['page']} is not in the approved HiFi package")
            continue
        node = tree.first(lambda item: selector_matches(item, source["selector"]) and tree.in_product(item)
                          and item["map"].get("data-specimen-variant") == source["variant"]
                          and item["map"].get("data-specimen-state") == source["state"])
        if node is None:
            problems.append(
                f"showcase specimen {row['id']} does not resolve to a product {source['selector']} with "
                f"data-specimen-variant={source['variant']!r} and data-specimen-state={source['state']!r} on {source['page']}")
            continue
        resolved[row["id"]] = {"row": row, "tree": tree, "node": node}
    for row in showcase.get("states", []):
        bound = resolved.get(row.get("specimen", ""))
        if row["mode"] == "pseudo" and bound:
            selector = bound["row"]["source"]["selector"]
            pattern = re.escape(selector) + r"(?![\w-])[^\s{},>+~]*:" + re.escape(row["state"]) + r"(?![\w-])"
            page_css = css[bound["row"]["source"]["page"]]
            if re.search(pattern, page_css) is None and not (
                    v2 and shared_pseudo_rule(page_css, bound["tree"], bound["node"], row["state"])):
                problems.append(f"showcase pseudo state {row['state']} has no {selector}:{row['state']} rule in approved CSS")
        if v2 and row["mode"] == "rendered" and bound and row["state"] == "open" \
                and closed_open_claim(bound["tree"], bound["node"]):
            problems.append(f"showcase rendered state open on {row['specimen']} is a closed <details> source node")
    for row in showcase.get("motion", []):
        bound = resolved.get(row["specimen"])
        if not bound:
            continue
        page_css = css[bound["row"]["source"]["page"]]
        trigger = row["trigger"]
        if not reduced_motion_css(page_css).strip():
            problems.append(f"showcase motion {row['variant']} page lacks an approved prefers-reduced-motion rule")
        if trigger["kind"] == "source-runtime":
            continue  # joined by showcase_runtime.resolve_runtime and proven in a browser
        if trigger["kind"] == "animation":
            ok = animation_source_backed(page_css, bound["node"], bound["tree"].ancestors(bound["node"]))
        elif trigger["kind"] == "class":
            ok = re.search(r"\." + re.escape(trigger["name"]) + r"(?![\w-])", page_css) and "transition" in page_css
        else:
            ok = ("[" + trigger["name"]) in page_css and ("transition" in page_css or "animation" in page_css) \
                and bound["node"]["map"].get(trigger["name"]) == trigger["from"]
        if not ok:
            problems.append(f"showcase motion {row['variant']} trigger is not backed by the approved source element and CSS")
    return resolved, problems


def serialize_start(tag: str, attrs: list[tuple[str, str | None]], *, drop: set[str] = frozenset(),
                    extra: dict[str, str] | None = None) -> str:
    parts, seen = [tag], set()
    for name, value in attrs:
        if name in drop or name in seen:
            continue
        seen.add(name)
        value = (extra or {}).get(name, value)
        parts.append(name if value is None else f'{name}="{escape(value, quote=True)}"')
    parts.extend(f'{name}="{escape(value, quote=True)}"' for name, value in (extra or {}).items() if name not in seen)
    return "<" + " ".join(parts) + ">"


def specimen_target(tree: SourceTree, node: dict[str, Any]) -> str | None:
    """The canvas target a specimen renders at: its state view's, else the default."""
    chain = tree.ancestors(node) + [node]
    canvas = next((item for item in chain if "data-hifi-canvas" in item["map"]), None)
    if canvas is None:
        return None
    targets = (canvas["map"].get("data-hifi-targets") or "").split()
    for item in reversed(chain):
        target = item["map"].get("data-responsive-target") if "data-hifi-state-view" in item["map"] else None
        if target in targets:
            return target
    return canvas["map"].get("data-hifi-target")


def fragment(tree: SourceTree, node: dict[str, Any], *, marker: str) -> tuple[str, str, str]:
    """Return (html start tag, body start tag, body content) copied from source.

    Ancestors keep their source attributes so descendant selectors, custom
    properties and container queries apply. Only ``hidden`` on a reviewer
    state view is dropped and the canvas selects that view's target, exactly
    as the reviewer runtime shows a state at a size.
    """
    chain = tree.ancestors(node)
    html_node = next((item for item in chain if item["tag"] == "html"), None)
    body_node = next((item for item in chain if item["tag"] == "body"), None)
    target = specimen_target(tree, node)
    opening, closing = [], []
    for item in chain:
        if item["tag"] in {"html", "body"}:
            continue
        drop = {"hidden"} if "data-hifi-state-view" in item["map"] else set()
        extra = {"data-hifi-target": target} if target and "data-hifi-canvas" in item["map"] else None
        opening.append(serialize_start(item["tag"], item["attrs"], drop=drop, extra=extra))
        closing.insert(0, f"</{item['tag']}>")
    drop = {"hidden"} if "data-hifi-state-view" in node["map"] else set()
    element = serialize_start(node["tag"], node["attrs"], drop=drop, extra={"data-ds-subject": marker})
    if node["tag"] not in VOID and node["end"] > node["start_end"]:
        element += tree.html[node["start_end"]:node["inner_end"]] + f"</{node['tag']}>"
    html_start = serialize_start("html", html_node["attrs"]) if html_node else "<html>"
    body_start = serialize_start("body", body_node["attrs"], drop={"data-hifi-default-surface"}) if body_node else "<body>"
    return html_start, body_start, "".join(opening) + element + "".join(closing)


def surface_node(tree: SourceTree, surface_id: str) -> dict[str, Any] | None:
    return tree.first(lambda item: item["map"].get("data-ui-surface") == surface_id)


def canvas_widths(tree: SourceTree) -> dict[str, float]:
    canvas = tree.first(lambda item: "data-hifi-canvas" in item["map"])
    if canvas is None:
        return {}
    targets = (canvas["map"].get("data-hifi-targets") or "").split()
    try:
        mapped = json.loads(canvas["map"].get("data-hifi-target-widths") or "{}")
    except json.JSONDecodeError:
        mapped = {}
    widths = {}
    for target in targets:
        value = mapped.get(target) if isinstance(mapped, dict) else None
        if value is None and re.fullmatch(r"\d+(?:\.\d+)?", target):
            value = float(target)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            widths[target] = float(value)
    return widths


def page_of(path: str) -> str:
    return PurePosixPath(path).name
