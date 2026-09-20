"""Reviewer DOM and evidence checks; product interaction evidence stays separate."""

import json
import re
from html.parser import HTMLParser

from check_wireframe_html import _decode_css_escapes, _strip_css_comments

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class ReviewerParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        parents = [attrs for _, attrs in self.stack]
        marked = any(key.startswith("data-hifi-") for key in values)
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


def _reviewer_contract(documents, manifest):
    """Return static findings and the source-bound browser observation matrix."""
    errors, specimens = [], []
    surfaces = manifest["surfaces"]
    if not isinstance(surfaces, list) or not surfaces:
        return ["HiFi reviewer requires nonempty surfaces"], None
    pages = list(documents)
    overview = [{"surface": row["id"], "route": row["route"], "states": row["states"],
                 "targets": [str(target) for target in row["responsive"]["targets"]]} for row in surfaces]
    for name, html in documents.items():
        parser = ReviewerParser()
        parser.feed(html)
        parser.close()
        errors.extend(parser.errors)
        nodes = parser.nodes
        shells = [(tag, attrs) for tag, attrs, _ in nodes if "data-hifi-reviewer-shell" in attrs]
        navs = [(tag, parents) for tag, attrs, parents in nodes if "data-hifi-page-nav" in attrs]
        if len(shells) != 1 or shells[0][0] != "aside":
            errors.append(f"HiFi {name} requires one reviewer aside")
        if len(navs) != 1 or navs[0][0] != "nav" or not any("data-hifi-reviewer-shell" in p for p in navs[0][1]):
            errors.append(f"HiFi {name} requires one sidebar page navigation")
        links = [attrs.get("href") for tag, attrs, parents in nodes if tag == "a" and any("data-hifi-page-nav" in p for p in parents)]
        if sorted(str(link) for link in links) != sorted(pages):
            errors.append(f"HiFi {name} sidebar must link every bundle page exactly once")
        views = [(tag, attrs, parents) for tag, attrs, parents in nodes if "data-hifi-review-view" in attrs]
        if sorted(attrs.get("data-hifi-review-view", "") for _, attrs, _ in views) != ["design-tokens", "overview"]:
            errors.append(f"HiFi {name} requires Overview and Design Tokens controls")
        for tag, attrs, parents in views:
            if tag != "a" or attrs.get("href") != "index.html#" + attrs["data-hifi-review-view"] or not any("data-hifi-reviewer-shell" in p for p in parents):
                errors.append("HiFi reviewer views must link to their entry panels from the sidebar")
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
        for _, attrs, parents in nodes:
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
                if spec["sourcePage"] not in pages:
                    errors.append("HiFi specimen source page must belong to the bundle")
                if spec["kind"] not in {"token", "component", "pattern"} or not all(spec.values()):
                    errors.append("HiFi specimens require kind, name, source selector, property, variant and state")
                specimens.append(spec)
        if summaries != overview:
            errors.append("HiFi Overview must cover exact manifest surfaces, routes, states and targets in order")
        if {s["kind"] for s in specimens} != {"token", "component", "pattern"}:
            errors.append("HiFi Design Tokens requires token, component and pattern specimens")
        if len({s["name"] for s in specimens}) != len(specimens):
            errors.append("HiFi specimen names must be unique")
        # Cover page-specific values: matching token names do not imply equal styles.
        for source_page, source_html in documents.items():
            css = "\n".join(re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", source_html, re.I))
            css = _strip_css_comments(css)
            # Strings may contain declaration-shaped examples; they are values.
            css = re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", '""', css, flags=re.S)
            css = _decode_css_escapes(css)
            tokens = {item for item in re.findall(r"(?:^|[;{])\s*(--[\w-]+)\s*:", css) if not item.startswith("--review-")}
            declared = {item["property"] for item in specimens if item["kind"] == "token" and item["sourcePage"] == source_page}
            if not tokens or tokens != declared:
                errors.append(f"HiFi token specimens must match actual product CSS custom properties on {source_page}")
            kinds = {item["kind"] for item in specimens if item["sourcePage"] == source_page}
            if kinds != {"token", "component", "pattern"}:
                errors.append(f"HiFi {source_page} requires page-bound token, component and pattern specimens")
    targets = sorted({str(target) for row in surfaces for target in row["responsive"]["targets"]})
    views = [{"from": origin, "view": view, "target": target, "trigger": trigger, "visible": True, "focusCorrect": True, "result": "PASS"}
             for origin in pages for view in ("overview", "design-tokens") for target in targets for trigger in ("click", "keyboard")]
    navigation = [{"from": origin, "to": dest, "target": target, "trigger": trigger, "visible": True, "focusCorrect": True, "result": "PASS"}
                  for origin in pages for dest in pages for target in targets for trigger in ("click", "keyboard")]
    return errors, {"defaultSurface": surfaces[0]["id"], "defaultVisible": True,
                    "overviewInitiallyHidden": True, "overview": overview,
                    "views": views, "navigation": navigation, "specimens": specimens}


def reviewer_evidence_findings(actual, expected):
    if not isinstance(actual, dict) or set(actual) != set(expected):
        return ["HiFi reviewer evidence requires its closed source-bound observation record"]
    errors = []
    for key in ("defaultSurface", "defaultVisible", "overviewInitiallyHidden", "overview", "views", "navigation"):
        # Order is meaningful for overview; all other lists are observation sets.
        left, right = actual[key], expected[key]
        if key in {"views", "navigation"} and isinstance(left, list):
            left = sorted(json.dumps(row, sort_keys=True) for row in left)
            right = sorted(json.dumps(row, sort_keys=True) for row in right)
        if left != right:
            errors.append(f"HiFi reviewer {key} does not match required browser observations")
    rows = actual["specimens"]
    if not isinstance(rows, list) or len(rows) != len(expected["specimens"]):
        return errors + ["HiFi computed specimen coverage is incomplete"]
    for row, spec in zip(rows, expected["specimens"]):
        if not isinstance(row, dict) or set(row) != set(spec) | {"sourceValue", "specimenValue", "displayValue"} or any(row.get(key) != value for key, value in spec.items()):
            errors.append("HiFi computed specimen identity differs from its DOM source binding")
            continue
        value = row["sourceValue"]
        if not isinstance(value, str) or not value.strip() or value != row["specimenValue"] or value != row["displayValue"]:
            errors.append("HiFi displayed values and computed specimens must equal the actual style source")
    return errors
