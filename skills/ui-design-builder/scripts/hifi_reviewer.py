"""Reviewer DOM and evidence checks; product interaction evidence stays separate."""

import json
import math
import re
from html.parser import HTMLParser

from check_wireframe_html import _decode_css_escapes, _strip_css_comments
from reviewer_shell import shared_css_drift

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
INERT_CONTAINERS = {"template", "noscript"}
TOKEN_PREVIEW_PROPERTIES = {
    "color", "background-color", "background-image", "font-family", "font-size", "font-weight",
    "line-height", "letter-spacing", "width", "height", "gap", "padding",
    "border-radius", "border-width", "box-shadow", "opacity", "z-index",
    "transition-duration", "transition-timing-function",
}


class ReviewerParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []
        self.errors = []
        self.inert_nodes = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        parents = [attrs for _, attrs in self.stack]
        if tag in INERT_CONTAINERS or any(parent_tag in INERT_CONTAINERS for parent_tag, _ in self.stack):
            self.inert_nodes.add(id(values))
        marked = any(key.startswith("data-hifi-") and key not in {"data-hifi-state-view"} for key in values)
        if marked and any("data-ui-surface" in item for item in parents + [values]):
            self.errors.append("HiFi reviewer markers must stay outside product surfaces")
        if any("data-hifi-reviewer-shell" in item or "data-hifi-panel" in item for item in parents + [values]):
            if any(key in values for key in ("data-control-id", "data-navigation-id", "data-ui-surface")):
                self.errors.append("HiFi reviewer UI cannot count as product controls or surfaces")
        self.nodes.append((tag, values, parents))
        if tag not in VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def reviewer_contract(documents, manifest):
    try:
        return _reviewer_contract(documents, manifest)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return ["HiFi reviewer source manifest or DOM bindings are invalid"], None


def _page_css(html):
    css = "\n".join(re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", html, re.I))
    css = _strip_css_comments(css)
    return _decode_css_escapes(css)


def _token_css(html):
    css = _page_css(html)
    css = re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", '""', css, flags=re.S)
    return _decode_css_escapes(css)


def _ordered_targets(surfaces):
    return list(dict.fromkeys(str(target) for row in surfaces for target in row["responsive"]["targets"]))


def _page_targets(surfaces, page, fallback=None):
    targets = list(dict.fromkeys(
        str(target)
        for row in surfaces
        if row.get("page") == page
        for target in row["responsive"]["targets"]
    ))
    return targets or list(fallback or [])


def _is_na_state(value):
    normalized = str(value).strip().casefold().lstrip(":")
    return normalized in {"n/a", "na"} or normalized.endswith(":n/a") or normalized.endswith(":na")


def _target_number(value):
    text = str(value).strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    try:
        number = float(text)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0 or number > 1_000_000:
        return None
    return int(number) if number.is_integer() else number


def _target_widths(attrs, targets):
    """Return the measured CSS width represented by each reviewer target.

    Viewport targets are self-describing (390 -> 390px). Native or named
    size-class targets must carry an explicit JSON width map on the canvas so
    the reviewer never guesses a pixel width from a label.
    """
    target_values = [str(target) for target in targets]
    raw = attrs.get("data-hifi-target-widths")
    if raw:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None, "HiFi product canvas target width map must be valid JSON"
        if not isinstance(parsed, dict) or set(parsed) != set(target_values):
            return None, "HiFi product canvas target width map must cover every manifest target exactly"
        widths = {}
        for target in target_values:
            value = parsed.get(target)
            try:
                finite = math.isfinite(value)
            except (OverflowError, TypeError, ValueError):
                finite = False
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not finite or value <= 0 or value > 1_000_000):
                return None, "HiFi product canvas target width map values must be positive numbers"
            widths[target] = int(value) if int(value) == value else value
        return widths, None
    widths = {target: _target_number(target) for target in target_values}
    if any(value is None for value in widths.values()):
        return None, "HiFi non-numeric responsive targets require data-hifi-target-widths"
    return widths, None


def _host_media_reflow(css):
    findings = []
    for match in re.finditer(r"@media\s*([^{}]*)\{", css, re.I):
        condition = match.group(1)
        if re.search(
            r"\b(?:width|height|inline-size|block-size)\b|"
            r"(?:device-width|device-height|orientation|aspect-ratio|resolution)",
            condition,
            re.I,
        ):
            findings.append("HiFi product reflow must use container queries, not host media queries")
            break
    return findings


def _exact_width_rule(css, target, width):
    target_pattern = re.escape(str(target))
    width_pattern = re.escape(str(width))
    return re.search(
        rf"\[data-hifi-canvas\]\s*\[\s*data-hifi-target\s*=\s*(['\"]){target_pattern}\1\s*\]"
        rf"\s*\{{[^{{}}]*?\bwidth\s*:\s*{width_pattern}px\b",
        css,
        re.I | re.S,
    ) is not None


def _retention_probe(nodes):
    """Find applicable product controls without inventing controls on a page."""
    product = [(tag, attrs, parents) for tag, attrs, parents in nodes if _in_product(attrs, parents)]
    input_marked = [(tag, attrs, parents) for tag, attrs, parents in product if "data-retention-input" in attrs]
    errors = []
    if len(input_marked) > 1:
        errors.append("HiFi page may mark only one retention input")

    def eligible_input(item):
        tag, attrs, _ = item
        if tag == "textarea":
            return True
        if tag != "input":
            return False
        return (attrs.get("type") or "text").casefold() not in {"hidden", "button", "submit", "reset", "file", "image"}

    inputs = [item for item in product if eligible_input(item)]
    input_item = input_marked[0] if input_marked else (inputs[0] if inputs else None)
    if input_item is not None and not eligible_input(input_item):
        errors.append("HiFi retention input must be an actual editable product input")

    def option_bound_to_select(item):
        _, _, parents = item
        return any(
            tag == "select" and any(parent is select_attrs for parent in parents)
            for tag, select_attrs, _ in product
        )

    def eligible_selection(item):
        tag, attrs, _ = item
        if tag == "select":
            return True
        if tag == "option":
            return "selected" in attrs and option_bound_to_select(item)
        if tag == "input":
            return (attrs.get("type") or "text").casefold() in {"checkbox", "radio"} and (
                "checked" in attrs or attrs.get("aria-checked") == "true"
            )
        role = (attrs.get("role") or "").casefold()
        selected = attrs.get("aria-selected") == "true" and role in {"button", "menuitem", "option", "tab", "radio"}
        pressed = attrs.get("aria-pressed") == "true" and tag in {"a", "button"}
        checked = attrs.get("aria-checked") == "true" and role in {"checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"}
        return selected or pressed or checked

    selection_marked = [item for item in product if "data-retention-selected" in item[1] and eligible_selection(item)]
    if len(selection_marked) > 1:
        errors.append("HiFi page may mark only one retention selection")
    selections = [item for item in product if eligible_selection(item)]
    selection_item = selection_marked[0] if selection_marked else (selections[0] if selections else None)

    def value_for_input(item):
        if item is None:
            return None
        tag, attrs, _ = item
        return attrs.get("value") if tag != "textarea" else attrs.get("data-value")

    def value_for_selection(item):
        if item is None:
            return None
        tag, attrs, _ = item
        if tag != "select":
            return attrs.get("value")
        for child_tag, child_attrs, child_parents in product:
            if child_tag == "option" and any(parent is attrs for parent in child_parents) and "selected" in child_attrs:
                return child_attrs.get("value") or child_attrs.get("data-value")
        for child_tag, child_attrs, child_parents in product:
            if child_tag == "option" and any(parent is attrs for parent in child_parents):
                return child_attrs.get("value") or child_attrs.get("data-value")
        return attrs.get("value")

    return {
        "input": value_for_input(input_item),
        "selected": value_for_selection(selection_item),
        "inputApplicable": input_item is not None,
        "selectedApplicable": selection_item is not None,
    }, errors


def has_current_reviewer_shell(documents):
    """Detect current v2 or v3 reviewer markup through parsed HTML."""
    for html in documents.values():
        parser = ReviewerParser()
        parser.feed(html)
        parser.close()
        if any("data-hifi-reviewer-shell" in attrs and attrs.get("data-hifi-reviewer-version") in {"2", "3"} for _, attrs, _ in parser.nodes):
            return True
    return False


def _simple_selector_matches(tag, attrs, selector):
    if selector == ":root":
        return tag == "html"
    if re.fullmatch(r"[A-Za-z][\w-]*", selector):
        return tag == selector.lower()
    if selector.startswith(".") and re.fullmatch(r"[A-Za-z][\w-]*", selector[1:]):
        return selector[1:] in (attrs.get("class") or "").split()
    if selector.startswith("#") and re.fullmatch(r"[A-Za-z][\w-]*", selector[1:]):
        return attrs.get("id") == selector[1:]
    return False


def _in_product(attrs, parents):
    return any("data-ui-surface" in item for item in parents + [attrs])


def _specimen_element(spec, nodes):
    identity = spec["_wrapper"]
    candidates = []
    for tag, attrs, parents in nodes:
        if tag != spec["element"] or not attrs.get("data-hifi-specimen-content"):
            continue
        if any(id(item) == identity for item in parents):
            candidates.append(attrs)
    return candidates


def _token_property_use(css, token, prop):
    """Follow declared aliases without treating an unused alias cycle as use."""
    aliases = {token}
    definitions = re.findall(r"(?:^|[;{])\s*(--[\w-]+)\s*:([^;{}]*)", css)
    while True:
        parents = {name for name, value in definitions
                   if aliases.intersection(re.findall(r"var\(\s*(--[\w-]+)", value))}
        if parents <= aliases:
            break
        aliases.update(parents)
    properties = {
        "width": ("width", "min-width", "max-width", "inline-size", "min-inline-size", "max-inline-size"),
        "height": ("height", "min-height", "max-height", "block-size", "min-block-size", "max-block-size"),
        "gap": ("gap", "row-gap", "column-gap"),
        "border-width": ("border-width", "border"),
        "background-color": ("background-color", "background"),
        "background-image": ("background-image", "background"),
        "transition-duration": ("transition-duration", "transition"),
        "transition-timing-function": ("transition-timing-function", "transition"),
    }.get(prop, (prop,))
    for property_name in properties:
        values = re.findall(rf"(?:^|[;{{])\s*{re.escape(property_name)}\s*:([^;{{}}]*)", css)
        if any(aliases.intersection(re.findall(r"var\(\s*(--[\w-]+)", value)) for value in values):
            return True
    return False


def _source_binding_findings(spec, nodes, css):
    selector = spec["source"]
    findings = []
    if not re.fullmatch(r":root|[A-Za-z][\w-]*|\.[A-Za-z][\w-]*|#[A-Za-z][\w-]*", selector):
        return ["HiFi specimen source selectors must be a simple element, class, ID, or :root binding"]
    if not re.search(rf"(?:^|[;{{])\s*{re.escape(spec['property'])}\s*:", css, re.I):
        findings.append("HiFi specimen property must be declared in the actual source-page CSS")
    if spec["kind"] == "token":
        prop = spec.get("previewProperty", "")
        if prop not in TOKEN_PREVIEW_PROPERTIES:
            findings.append("HiFi token specimens require a supported data-token-preview CSS property")
        elif not _token_property_use(css, spec["property"], prop):
            findings.append("HiFi token preview must use a property that consumes that token in the source-page CSS")
        return findings if selector == ":root" else findings + ["HiFi token specimens must source CSS custom properties from :root"]
    candidates = [attrs for tag, attrs, parents in nodes if _simple_selector_matches(tag, attrs, selector) and _in_product(attrs, parents)]
    if not candidates:
        return findings + ["HiFi specimen source selector must bind an actual product element"]
    if not any(attrs.get("data-specimen-variant") == spec["variant"] and attrs.get("data-specimen-state") == spec["state"] for attrs in candidates):
        findings.append("HiFi specimen variant and state must exist on the bound product source")
    return findings


def _reviewer_contract(documents, manifest):
    """Return static findings and the source-bound browser observation matrix."""
    errors, specimens = [], []
    surfaces = manifest["surfaces"]
    if not isinstance(surfaces, list) or not surfaces:
        return ["HiFi reviewer requires nonempty surfaces"], None
    pages = list(documents)
    overview = [{"surface": row["id"], "route": row["route"], "states": row["states"],
                 "targets": [str(target) for target in row["responsive"]["targets"]]} for row in surfaces]
    target_values = _ordered_targets(surfaces)
    page_targets = {page: _page_targets(surfaces, page, target_values) for page in pages}
    page_widths = {}
    page_retention = {}
    page_shell_versions = {}
    for name, html in documents.items():
        parser = ReviewerParser()
        parser.feed(html)
        parser.close()
        errors.extend(parser.errors)
        nodes = parser.nodes
        page_surface_ids = [row["id"] for row in surfaces if row["page"] == name]
        applicable_targets = page_targets[name]
        shells = [(tag, attrs) for tag, attrs, _ in nodes if "data-hifi-reviewer-shell" in attrs]
        navs = [(tag, parents) for tag, attrs, parents in nodes if "data-hifi-page-nav" in attrs]
        if len(shells) != 1 or shells[0][0] != "aside":
            errors.append(f"HiFi {name} requires one reviewer aside")
        elif shells[0][1].get("data-hifi-reviewer-version") not in {"2", "3"}:
            errors.append(f"HiFi {name} requires the current version-2 or version-3 reviewer shell")
        shell_version = shells[0][1].get("data-hifi-reviewer-version") if len(shells) == 1 and shells[0][0] == "aside" else None
        page_shell_versions[name] = shell_version
        if len(navs) != 1 or navs[0][0] != "nav" or not any("data-hifi-reviewer-shell" in p for p in navs[0][1]):
            errors.append(f"HiFi {name} requires one sidebar page navigation")
        page_links = [attrs for tag, attrs, parents in nodes if tag == "a" and any("data-hifi-page-nav" in p for p in parents)]
        links = [attrs.get("href") for attrs in page_links]
        if sorted(str(link) for link in links) != sorted(pages):
            errors.append(f"HiFi {name} sidebar must link every bundle page exactly once")
        else:
            for attrs in page_links:
                if attrs.get("href") == name:
                    if attrs.get("aria-current") != "page":
                        errors.append(f"HiFi {name} sidebar must mark its current product screen")
        views = [(tag, attrs, parents) for tag, attrs, parents in nodes if "data-hifi-review-view" in attrs]
        if sorted(attrs.get("data-hifi-review-view", "") for _, attrs, _ in views) != ["design-tokens", "overview"]:
            errors.append(f"HiFi {name} requires Overview and Design Tokens controls")
        for tag, attrs, parents in views:
            if tag != "a" or attrs.get("href") != "index.html#" + attrs["data-hifi-review-view"] or not any("data-hifi-reviewer-shell" in p for p in parents):
                errors.append("HiFi reviewer views must link to their entry panels from the sidebar")
        responsive = [(tag, attrs, parents) for tag, attrs, parents in nodes if "data-hifi-responsive-controls" in attrs]
        if (len(responsive) != 1 or responsive[0][0] != "fieldset"
                or not any("data-hifi-reviewer-shell" in p for p in responsive[0][2])):
            errors.append(f"HiFi {name} requires one sidebar responsive target control group")
        target_buttons = [(tag, attrs) for tag, attrs, parents in nodes
                          if "data-hifi-target-control" in attrs and any("data-hifi-responsive-controls" in p for p in parents)]
        if [attrs.get("data-hifi-target-control") for _, attrs in target_buttons] != applicable_targets or any(tag != "button" for tag, _ in target_buttons):
            errors.append(f"HiFi {name} responsive target controls must exactly match manifest targets as real buttons")
        if target_buttons and sum(attrs.get("aria-pressed") == "true" for _, attrs in target_buttons) != 1:
            errors.append(f"HiFi {name} must show one selected responsive target control")
        if shell_version == "3":
            expected_controls = [(row["id"], str(state)) for row in surfaces if row["page"] == name
                                 for state in row["states"] if not _is_na_state(state)]
            state_controls = [(attrs.get("data-hifi-state-surface"), attrs.get("data-hifi-state-control"))
                              for tag, attrs, parents in nodes if tag == "button" and "data-hifi-state-control" in attrs
                              and any("data-hifi-state-controls" in parent for parent in parents)]
            if state_controls != expected_controls:
                errors.append(f"HiFi {name} state controls must match manifest surface states in order")
            for surface, state in expected_controls:
                expected_pairs = {(state, target) for target in applicable_targets}
                actual_pairs = {(attrs.get("data-hifi-state-view"), attrs.get("data-responsive-target"))
                                for _, attrs, parents in nodes if "data-hifi-state-view" in attrs
                                and any(parent.get("data-ui-surface") == surface for parent in parents)}
                if not expected_pairs <= actual_pairs:
                    errors.append(f"HiFi {name} product state {surface} {state} requires a visible-state source for every target")
        canvases = [(tag, attrs) for tag, attrs, _ in nodes if "data-hifi-canvas" in attrs]
        if len(canvases) != 1 or canvases[0][0] not in {"div", "main", "section"}:
            errors.append(f"HiFi {name} requires one exact-width product container")
            page_widths[name] = {}
        else:
            canvas_attrs = canvases[0][1]
            if canvas_attrs.get("data-hifi-targets", "").split() != applicable_targets or canvas_attrs.get("data-hifi-target") not in applicable_targets:
                errors.append(f"HiFi {name} product container must declare and select exact manifest targets")
            widths, width_error = _target_widths(canvas_attrs, applicable_targets)
            page_widths[name] = widths or {}
            if width_error:
                errors.append(width_error)
        surface_nodes = [(tag, attrs, parents) for tag, attrs, parents in nodes if "data-ui-surface" in attrs]
        if [attrs.get("data-ui-surface") for _, attrs, _ in surface_nodes] != page_surface_ids:
            errors.append(f"HiFi {name} must render exactly its assigned product surfaces")
        if surface_nodes and any(not parents or "data-hifi-canvas" not in parents[-1] for _, _, parents in surface_nodes):
            errors.append(f"HiFi {name} product surface must be the direct child of its exact-width container")
        retention, retention_errors = _retention_probe(nodes)
        page_retention[name] = retention
        errors.extend(retention_errors)
        css = _page_css(html)
        if shell_version == "3":
            errors.extend(f"HiFi {name}: {finding}" for finding in shared_css_drift(html))
        errors.extend(f"HiFi {name}: {finding}" for finding in _host_media_reflow(css))
        if re.search(r"transform\s*:\s*scale\s*\(", css, re.I):
            errors.append(f"HiFi {name} exact-width product container cannot use visual scaling")
        if re.search(r"\[data-hifi-canvas\][^{}]*\{[^{}]*container-type\s*:\s*inline-size", css, re.S) is None:
            errors.append(f"HiFi {name} exact-width product container requires inline-size containment")
        if "@container" not in css:
            errors.append(f"HiFi {name} requires product container queries")
        if re.search(r"\[data-hifi-reviewer-shell\][^{}]*\{[^{}]*position\s*:\s*(?:fixed|sticky)", css, re.S) is None:
            errors.append(f"HiFi {name} reviewer shell must remain fixed")
        for target in applicable_targets:
            width = page_widths.get(name, {}).get(target)
            if width is not None and not _exact_width_rule(css, target, width):
                errors.append(f"HiFi {name} requires an exact CSS width of {target}px for its product container")
        panels = [attrs for _, attrs, _ in nodes if "data-hifi-panel" in attrs]
        if name != "index.html":
            if panels:
                errors.append("HiFi reviewer panels live only on index.html")
            continue
        if sorted(p.get("data-hifi-panel", "") for p in panels) != ["design-tokens", "overview"] or any("hidden" not in p for p in panels):
            errors.append("HiFi entry requires initially hidden Overview and Design Tokens panels")
        default = [attrs.get("data-hifi-default-surface") for _, attrs, _ in nodes if "data-hifi-default-surface" in attrs]
        if default != [surfaces[0]["id"]] or surfaces[0]["page"] != "index.html":
            errors.append("HiFi entry must default to its first product surface")
        summaries = []
        state_coverage = []
        for tag, attrs, parents in nodes:
            if "data-hifi-summary" in attrs:
                if not any(p.get("data-hifi-panel") == "overview" for p in parents):
                    errors.append("HiFi page summaries must be in Overview")
                summaries.append({"surface": attrs["data-hifi-summary"], "route": attrs.get("data-route"),
                                  "states": attrs.get("data-states", "").split(), "targets": attrs.get("data-targets", "").split()})
            if "data-hifi-spec" in attrs:
                if not any(p.get("data-hifi-panel") == "design-tokens" for p in parents):
                    errors.append("HiFi design specimens must be in Design Tokens")
                spec = {key: attrs.get("data-" + key, "") for key in ("name", "source", "property", "variant", "state")}
                spec["kind"] = attrs["data-hifi-spec"]
                spec["sourcePage"] = attrs.get("data-source-page", "")
                spec["sharedGroup"] = attrs.get("data-shared-group") or None
                spec["element"] = attrs.get("data-specimen-element", "")
                spec["marker"] = ""
                if spec["kind"] == "token":
                    spec["previewProperty"] = attrs.get("data-token-preview", "")
                    if shell_version == "3" and not attrs.get("data-token-purpose", "").strip():
                        errors.append("HiFi v3 token specimens require a named purpose")
                spec["_wrapper"] = id(attrs)
                if spec["sourcePage"] not in pages:
                    errors.append("HiFi specimen source page must belong to the bundle")
                if spec["kind"] not in {"token", "component", "pattern"} or not all(str(value).strip() for key, value in spec.items() if key not in {"sharedGroup", "marker"}):
                    errors.append("HiFi specimens require kind, name, source selector, property, variant and state")
                elements = _specimen_element(spec, nodes)
                if (spec["kind"] == "token" and not elements) or (spec["kind"] != "token" and (not elements or spec["element"] not in {"a", "button", "input", "select", "textarea", "section", "article"})):
                    errors.append("HiFi specimens must render a real styled element with a visible content marker")
                elif elements:
                    spec["marker"] = elements[0]["data-hifi-specimen-content"]
                    if spec["kind"] != "token" and not any(
                        _simple_selector_matches(element_tag, element_attrs, spec["source"])
                        for element_tag, element_attrs, _ in nodes
                        if any(id(parent) == spec["_wrapper"] for parent in _)
                    ):
                        errors.append("HiFi component and pattern specimens must use the source selector styling")
                spec.pop("_wrapper", None)
                specimens.append(spec)
            if "data-hifi-state-coverage" in attrs:
                if not any(p.get("data-hifi-panel") == "overview" for p in parents):
                    errors.append("HiFi state coverage is allowed only in Overview")
                coverage_parts = attrs["data-hifi-state-coverage"].split(None, 1)
                state_coverage.append({
                    "surface": coverage_parts[0] if coverage_parts else "",
                    "tag": tag,
                    "href": attrs.get("href"),
                    "state": coverage_parts[1] if len(coverage_parts) == 2 else None,
                    "destination": attrs.get("data-state-destination"),
                    "reason": attrs.get("data-state-reason", "").strip(),
                })
        if summaries != overview:
            errors.append("HiFi Overview must cover exact manifest surfaces, routes, states and targets in order")
        expected_states = [(row["id"], state) for row in surfaces for state in row["states"]]
        if [(row["surface"], row["state"]) for row in state_coverage] != expected_states:
            errors.append("HiFi Overview state coverage must exactly match manifest states in order")
        else:
            state_surfaces = [row for row in surfaces for _ in row["states"]]
            state_values = [state for surface in surfaces for state in surface["states"]]
            for row, surface, state in zip(state_coverage, state_surfaces, state_values):
                if row["state"] != state and not _is_na_state(state):
                    errors.append("HiFi Overview state links must target their actual product page")
                elif _is_na_state(state):
                    if row["tag"] == "a" or row["href"] or row["destination"] or not row["reason"]:
                        errors.append("HiFi Overview n/a state coverage must explain why no product destination exists")
                elif row["tag"] != "a" or row["href"] != surface["page"] or row["destination"] != state:
                    errors.append("HiFi Overview state links must target their actual product page")
        if {s["kind"] for s in specimens} != {"token", "component", "pattern"}:
            errors.append("HiFi Design Tokens requires token, component and pattern specimens")
        for specimen_name in {row["name"] for row in specimens}:
            group = [row for row in specimens if row["name"] == specimen_name]
            if len({row["sharedGroup"] for row in group}) != 1 or (len(group) > 1 and group[0]["sharedGroup"] is None):
                errors.append("HiFi shared specimen names require one shared group identity")
            if len({(row["kind"], row["source"], row["property"], row["variant"], row["state"], row["element"]) for row in group}) != 1:
                errors.append("HiFi shared specimen groups must keep one source-bound identity")
        # Cover page-specific values: matching token names do not imply equal styles.
        for source_page, source_html in documents.items():
            source_parser = ReviewerParser()
            source_parser.feed(source_html)
            source_parser.close()
            source_nodes = source_parser.nodes
            css = _token_css(source_html)
            tokens = {item for item in re.findall(r"(?:^|[;{])\s*(--[\w-]+)\s*:", css) if not item.startswith("--review-")}
            declared = {item["property"] for item in specimens if item["kind"] == "token" and item["sourcePage"] == source_page}
            if not tokens or tokens != declared:
                errors.append(f"HiFi token specimens must match actual product CSS custom properties on {source_page}")
            kinds = {item["kind"] for item in specimens if item["sourcePage"] == source_page}
            if kinds != {"token", "component", "pattern"}:
                errors.append(f"HiFi {source_page} requires page-bound token, component and pattern specimens")
            component_specs = [row for row in specimens if row["sourcePage"] == source_page and row["kind"] == "component"]
            component_elements = {row["element"] for row in component_specs}
            product_elements = {tag for tag, attrs, parents in source_nodes
                                if tag in {"button", "input", "select", "textarea"} and _in_product(attrs, parents)}
            product_elements.update("a" for tag, attrs, parents in source_nodes
                                    if tag == "a" and _in_product(attrs, parents)
                                    and ("data-navigation-id" in attrs or "data-control-id" in attrs))
            if not product_elements <= component_elements:
                errors.append(f"HiFi {source_page} component specimens must cover its actual styled form controls")
            for tag, attrs, parents in source_nodes:
                if not _in_product(attrs, parents) or tag not in {"button", "input", "select", "textarea"}:
                    if not (tag == "a" and _in_product(attrs, parents)
                            and ("data-navigation-id" in attrs or "data-control-id" in attrs)):
                        continue
                bound = [spec for spec in component_specs
                         if spec["element"] == tag and _simple_selector_matches(tag, attrs, spec["source"])]
                if not bound:
                    errors.append(f"HiFi {source_page} product control has no source-bound component specimen")
                    continue
                variant = attrs.get("data-specimen-variant") or attrs.get("data-variant") or "default"
                state = attrs.get("data-specimen-state") or attrs.get("data-state") or "default"
                if not any(spec["variant"] == variant and spec["state"] == state for spec in bound):
                    errors.append(f"HiFi {source_page} component specimens must cover every bound product variant/state")
            for row in specimens:
                    if row["sourcePage"] == source_page:
                        errors.extend(_source_binding_findings(row, source_nodes, css))
    targets = _ordered_targets(surfaces)
    surfaces_by_page = {
        page: [row["id"] for row in surfaces if row["page"] == page][:1]
        for page in pages
    }
    views = [{"from": origin, "view": view, "target": target, "trigger": trigger,
              "visible": True, "productVisible": False, "visibleSurfaces": [], "focusCorrect": True, "result": "PASS"}
             for origin in pages for view in ("overview", "design-tokens")
             for target in page_targets.get(origin, targets) for trigger in ("click", "keyboard")]
    navigation_edges = {
        (origin, dest)
        for origin in pages
        for dest in pages
    }
    if set(page_shell_versions.values()) == {"3"} and pages:
        first = pages[0]
        navigation_edges = {
            (origin, first)
            for origin in pages
        }
        navigation_edges.update((first, dest) for dest in pages)
        navigation_edges.update(
            (pages[index], pages[index + 1])
            for index in range(len(pages) - 1)
        )
    navigation = [{"from": origin, "to": dest, "target": target, "trigger": trigger,
                   "destinationTarget": target if target in page_targets.get(dest, targets) else (page_targets.get(dest, targets) or [None])[0],
                   "visible": True, "productVisible": True, "visibleSurfaces": surfaces_by_page[dest],
                   "focusCorrect": True, "result": "PASS"}
                  for origin, dest in navigation_edges
                  for target in page_targets.get(origin, targets) for trigger in ("click", "keyboard")]
    recovery = [{"from": origin, "case": case, "target": target,
                 "surfaces": surfaces_by_page[origin], "selectedTarget": target,
                 "productVisible": True, "panelsHidden": True, "result": "PASS"}
                for origin in pages for case in ("unknown-hash", "back-from-overview", "back-from-design-tokens")
                for target in page_targets.get(origin, targets)]
    recovery.extend({"from": "index.html", "case": "final-default-restoration", "target": target,
                     "surfaces": [surfaces[0]["id"]], "selectedTarget": target,
                     "productVisible": True, "panelsHidden": True, "result": "PASS"}
                    for target in page_targets.get("index.html", targets))
    viewport = []
    retention = []
    for row in surfaces:
        for target in row["responsive"]["targets"]:
            target = str(target)
            measured_width = page_widths.get(row["page"], {}).get(target)
            viewport.append({"page": row["page"], "surface": row["id"], "target": target,
                             "requestedWidth": target, "measuredProductWidth": measured_width,
                             "visibleSurfaces": [row["id"]], "containerQueryApplied": True,
                             "hostMediaQueryApplied": False, "result": "PASS"})
            row_targets = page_targets.get(row["page"], targets)
            previous = row_targets[(row_targets.index(target) - 1) % len(row_targets)] if len(row_targets) > 1 else target
            probe = page_retention.get(row["page"], {"input": None, "selected": None,
                                                      "inputApplicable": False, "selectedApplicable": False})
            for case in ("target-switch", "overview", "design-tokens"):
                retention.append({"page": row["page"], "surface": row["id"], "target": target, "case": case,
                                  "selectedTargetBefore": previous if case == "target-switch" else target,
                                  "selectedTargetAfter": target,
                                  "inputValueBefore": probe["input"], "inputValueAfter": probe["input"],
                                  "selectedValueBefore": probe["selected"], "selectedValueAfter": probe["selected"],
                                  "inputApplicable": probe["inputApplicable"],
                                  "selectedApplicable": probe["selectedApplicable"],
                                  "productVisible": case == "target-switch", "visibleSurfaces": [] if case != "target-switch" else [row["id"]],
                                  "result": "PASS"})
    return errors, {"defaultSurface": surfaces[0]["id"], "defaultVisible": True,
                    "overviewInitiallyHidden": True, "overview": overview,
                    "views": views, "navigation": navigation, "recovery": recovery,
                    "viewport": viewport, "retention": retention, "specimens": specimens}


def product_control_findings(documents):
    """Validate native product controls and their same-surface panels."""

    errors = []
    for page, html in documents.items():
        parser = ReviewerParser()
        parser.feed(html)
        parser.close()
        errors.extend(parser.errors)
        nodes = parser.nodes
        node_ids = {}
        for _, attrs, parents in nodes:
            if attrs.get("id"):
                node_ids.setdefault(attrs["id"], []).append((attrs, parents))

        def product_surface(parents):
            return next((parent for parent in reversed(parents) if "data-ui-surface" in parent), None)

        for tag, attrs, parents in nodes:
            if "data-product-menu" not in attrs and "data-product-tab" not in attrs:
                continue
            surface = product_surface(parents)
            if surface is None:
                errors.append(f"HiFi {page} product menu/tab controls must stay inside a product surface")
            kind = "menu" if "data-product-menu" in attrs else "tab"
            if tag != "button":
                errors.append(f"HiFi {page} product {kind} control must be a native button")
            if id(attrs) in parser.inert_nodes:
                errors.append(f"HiFi {page} product {kind} control must be a live product button outside template/noscript")
            target_id = attrs.get("aria-controls")
            matches = node_ids.get(target_id, [])
            if not matches:
                errors.append(f"HiFi {page} product {kind} control must bind an existing panel")
            elif (len(matches) != 1 or matches[0][0] is attrs or surface is None
                  or product_surface(matches[0][1]) is not surface
                  or "data-ui-surface" in matches[0][0]
                  or any("data-hifi-panel" in item or "data-hifi-reviewer-shell" in item
                         or "data-reviewer-shell" in item for item in [matches[0][0], *matches[0][1]])):
                errors.append(f"HiFi {page} product {kind} control must bind one distinct panel inside the same product surface")
            elif id(matches[0][0]) in parser.inert_nodes:
                errors.append(f"HiFi {page} product {kind} panel must be a live product panel outside template/noscript")
            if kind == "menu":
                expanded = attrs.get("aria-expanded")
                if expanded not in {"true", "false"}:
                    errors.append(f"HiFi {page} product menu control must declare expanded state")
            else:
                selected = attrs.get("aria-selected")
                if selected not in {"true", "false"}:
                    errors.append(f"HiFi {page} product tab control must declare selected state")
    return errors


def reviewer_evidence_findings(actual, expected):
    if not isinstance(actual, dict) or not isinstance(expected, dict) or set(actual) != set(expected):
        return ["HiFi reviewer evidence requires its closed source-bound observation record"]
    errors = []
    for key in ("defaultSurface", "defaultVisible", "overviewInitiallyHidden", "overview", "views", "navigation", "recovery", "viewport"):
        # Order is meaningful for overview; all other lists are observation sets.
        left, right = actual.get(key), expected.get(key)
        if key in {"views", "navigation", "recovery"} and isinstance(left, list):
            if not isinstance(right, list):
                errors.append(f"HiFi reviewer {key} does not match required browser observations")
                continue
            try:
                left = sorted(json.dumps(row, sort_keys=True) for row in left)
                right = sorted(json.dumps(row, sort_keys=True) for row in right)
            except (TypeError, ValueError):
                left = None
        if left != right:
            errors.append(f"HiFi reviewer {key} does not match required browser observations")
    rows = actual.get("retention")
    expected_rows = expected.get("retention")
    if not isinstance(expected_rows, list) or not isinstance(rows, list) or len(rows) != len(expected_rows):
        errors.append("HiFi reviewer retention does not match required browser observations")
    else:
        for row, spec in zip(rows, expected_rows):
            if not isinstance(row, dict) or not isinstance(spec, dict) or set(row) != set(spec):
                errors.append("HiFi reviewer retention identity differs from its DOM source binding")
                continue
            value_keys = {
                "inputValueBefore", "inputValueAfter", "selectedValueBefore", "selectedValueAfter",
            }
            if any(row.get(key) != value for key, value in spec.items() if key not in value_keys):
                errors.append("HiFi reviewer retention identity differs from its DOM source binding")
                continue
            for key, applicable_key in (("inputValue", "inputApplicable"), ("selectedValue", "selectedApplicable")):
                before, after = row.get(key + "Before"), row.get(key + "After")
                applicable = spec.get(applicable_key)
                if applicable is False:
                    if before is not None or after is not None:
                        errors.append("HiFi reviewer retention must not invent a product control that the page does not use")
                elif not isinstance(before, str) or not before.strip() or before != after:
                    errors.append("HiFi reviewer retention must observe unchanged nonempty product input and selected values")
    rows = actual.get("specimens")
    expected_specimens = expected.get("specimens")
    if not isinstance(rows, list) or not isinstance(expected_specimens, list) or len(rows) != len(expected_specimens):
        return errors + ["HiFi computed specimen coverage is incomplete"]
    groups = {}
    for row, spec in zip(rows, expected_specimens):
        value_keys = {"sourceValue", "specimenValue", "displayValue"}
        if isinstance(spec, dict) and spec.get("kind") == "token":
            value_keys |= {"sourceComputedValue", "specimenComputedValue"}
        if not isinstance(row, dict) or not isinstance(spec, dict) or set(row) != set(spec) | value_keys or any(row.get(key) != value for key, value in spec.items()):
            errors.append("HiFi computed specimen identity differs from its DOM source binding")
            continue
        value = row.get("sourceValue")
        if not isinstance(value, str) or not value.strip() or value != row.get("specimenValue") or value != row.get("displayValue"):
            errors.append("HiFi displayed values and computed specimens must equal the actual style source")
            continue
        if spec.get("kind") == "token":
            computed = row.get("sourceComputedValue")
            if not isinstance(computed, str) or not computed.strip() or computed != row.get("specimenComputedValue"):
                errors.append("HiFi applied token values must equal the browser-normalized source property")
                continue
        group = row.get("sharedGroup")
        if group is not None and (not isinstance(group, str) or not group.strip()):
            errors.append("HiFi shared specimen group must be null or nonempty text")
            continue
        if group:
            groups.setdefault(group, []).append(row)
    for group in groups.values():
        values = {(row.get("sourceValue"), row.get("specimenValue"), row.get("displayValue"),
                   row.get("sourceComputedValue"), row.get("specimenComputedValue")) for row in group}
        if len(values) != 1:
            errors.append("HiFi shared specimen group values must be equal across every member page")
    return errors
