"""ds-showcase/2 source-runtime motion: closed triggers and static source joins.

A source-runtime row binds one approved Motion And Media Intent with current
normal and reduced-motion evidence, one hash-identified inline product script,
and the specimen copy inside the exact manifest surface, state and target.
These checks prove source identity and association only. Playback is proven
in a real browser by verify_runtime_motion.py; a resolved association or an
API name in source text is never a playback PASS.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Callable

import design_system_showcase as source

SCHEMA_V2 = "ds-showcase/2"
RUNTIME_KIND = "source-runtime"
TRIGGER_KEYS = frozenset({"kind", "mechanism", "intent", "surface", "state", "target", "scriptSha256", "activation"})
MECHANISMS = ("waapi", "css-animation")
ACTIVATIONS = ("viewport", "state-entry")
_LITERALS = {
    "intent": re.compile(r"^MM-[A-Z0-9]+(?:-[A-Z0-9]+)*$"),
    "surface": re.compile(r"^UI-[A-Z0-9]+(?:-[A-Z0-9]+)*$"),
    "state": re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    "target": re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    "scriptSha256": re.compile(r"^[0-9a-f]{64}$"),
}
# One ancestor-scoped bare pseudo-class rule, such as "[data-ui-surface] :focus-visible".
_SHARED_PSEUDO_RE = re.compile(
    r"^(?P<scope>\[[A-Za-z][\w-]*(?:=(?:\"[^\"\\]*\"|'[^'\\]*'|[A-Za-z0-9_-]+))?\]"
    r"|\.[A-Za-z][\w-]*|#[A-Za-z][\w-]*|[a-z][a-z0-9]*) :(?P<state>[a-z-]+)$")
# The reviewer connect call, with or without its closed options object, is reviewer code.
REVIEWER_CONNECT_RE = re.compile(r"^\s*(?:window\.)?connectHifiReviewer\((?:\s*\{[^<>()]*\}\s*)?\)\s*;?\s*$")
UI_SCRIPTS = Path(__file__).resolve().parents[2] / "ui-design-builder" / "scripts"


def is_runtime(row: Any) -> bool:
    return isinstance(row, dict) and isinstance(row.get("trigger"), dict) and row["trigger"].get("kind") == RUNTIME_KIND


def trigger_findings(variant: Any, trigger: dict[str, Any]) -> list[str]:
    """Closed shape only: no unknown keys, code, callbacks or URLs."""
    label = f"showcase motion {variant} source-runtime trigger"
    if set(trigger) != TRIGGER_KEYS:
        return [f"{label} must contain exactly " + ", ".join(sorted(TRIGGER_KEYS))]
    problems = []
    if trigger["mechanism"] not in MECHANISMS:
        problems.append(f"{label} mechanism must be waapi or css-animation")
    for key, pattern in _LITERALS.items():
        if not isinstance(trigger[key], str) or pattern.fullmatch(trigger[key]) is None:
            problems.append(f"{label} {key} is not a closed literal")
    activation = trigger["activation"]
    if not isinstance(activation, dict) or set(activation) != {"kind"} or activation["kind"] not in ACTIVATIONS:
        problems.append(f'{label} activation must be exactly {{"kind": "viewport" or "state-entry"}}')
    return problems


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plate_scripts(html: str) -> list[str]:
    """Surface-plate scripts in source order, without the reviewer connect call."""
    return [body for body in source.product_scripts(html, with_controls=True) if not REVIEWER_CONNECT_RE.match(body)]


def script_finding(html: str, digest: str) -> str | None:
    """Bind exactly one executable inline product script by its raw body hash."""
    inline = source.SCRIPT_RE.findall(source.product_html(html))
    product = [body for attrs, body in inline if source._executable(attrs, body) and not REVIEWER_CONNECT_RE.match(body)]
    matches = sum(_sha(body) == digest for body in product)
    if matches == 1:
        return None
    if matches > 1:
        return "matches more than one inline product script"
    reviewer = [body for segment in source.RUNTIME_SEGMENT_RE.findall(html) for _, body in source.SCRIPT_RE.findall(segment)]
    reviewer += [body for _, body in inline if source.REVIEWER_CALL_RE.match(body) or REVIEWER_CONNECT_RE.match(body)]
    if any(_sha(body) == digest for body in reviewer):
        return "names a reviewer script, not product source"
    return "matches no executable inline product script on its page"


def _nearest(tree: source.SourceTree, node: dict[str, Any], attribute: str) -> dict[str, Any] | None:
    return next((item for item in reversed(tree.ancestors(node) + [node]) if attribute in item["map"]), None)


def scoped_copies(tree: source.SourceTree, spec: dict[str, str], surface: str, state: str,
                  targets: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Specimen copies inside one surface and state view, per approved target."""
    copies: dict[str, list[dict[str, Any]]] = {target: [] for target in targets}
    for node in tree.nodes:
        if not (source.selector_matches(node, spec["selector"])
                and node["map"].get("data-specimen-variant") == spec["variant"]
                and node["map"].get("data-specimen-state") == spec["state"]):
            continue
        owner = _nearest(tree, node, "data-ui-surface")
        view = _nearest(tree, node, "data-hifi-state-view")
        if owner is None or owner["map"].get("data-ui-surface") != surface or owner is node \
                or view is None or view["map"].get("data-hifi-state-view") != state:
            continue
        only = view["map"].get("data-responsive-target")
        for target in targets:
            if only is None or only == target:
                copies[target].append(node)
    return copies


def ui_motion_records(ui_text: str) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Parse intents and recorded normal/reduced evidence with the UI checker's own parsers."""
    if str(UI_SCRIPTS) not in sys.path:
        sys.path.append(str(UI_SCRIPTS))
    import check_ui_design_contract as ui
    from markdown_contract import active_text

    active = active_text(ui_text)
    scratch: list[str] = []
    intents = ui._validate_motion_table(ui._section(active, "## Motion And Media Intent") or "",
                                        require_filled=False, problems=scratch)
    evidence = ui._motion_effect_evidence(ui._section(active, "## Style Integration") or "", intents, scratch)
    return intents, evidence


def _intent_findings(label: str, trigger: dict[str, Any], intents: dict[str, dict[str, str]],
                     evidence: dict[str, dict[str, str]], read_repo: Callable[[str], bytes | None]) -> list[str]:
    intent_id = trigger["intent"]
    intent = intents.get(intent_id)
    if intent is None:
        return [f"{label} intent {intent_id} is not in the approved Motion And Media Intent table"]
    problems = []
    if intent.get("status", "").casefold() != "approved" or "motion" not in intent.get("treatment", "").casefold():
        problems.append(f"{label} intent {intent_id} must be an approved motion intent")
    if intent.get("scope", "").split("/", 1)[0].strip() != trigger["surface"]:
        problems.append(f"{label} intent {intent_id} scope does not name surface {trigger['surface']}")
    for case in ("normal", "reduced"):
        record = evidence.get(f"{intent_id}:{case}")
        if record is None:
            problems.append(f"{label} intent {intent_id} has no {case}-motion PASS evidence")
            continue
        payload = read_repo(record["path"])
        if payload is None or hashlib.sha256(payload).hexdigest() != record["sha256"]:
            problems.append(f"{label} intent {intent_id} {case}-motion evidence is missing or stale")
    return problems


def resolve_runtime(registry: dict[str, Any], documents: dict[str, str], manifest: dict[str, Any],
                    read_repo: Callable[[str], bytes | None]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Join every source-runtime row to approved intent, evidence, script and specimen copies."""
    showcase = registry.get("showcase") if isinstance(registry.get("showcase"), dict) else {}
    rows = [row for row in showcase.get("motion", []) if is_runtime(row)]
    if not rows:
        return {}, []
    problems: list[str] = []
    binding = (registry.get("sourceBindings") or {}).get("uiDesign")
    payload = read_repo(binding["path"]) if isinstance(binding, dict) and isinstance(binding.get("path"), str) else None
    try:
        intents, evidence = ui_motion_records(payload.decode("utf-8")) if payload is not None else ({}, {})
    except UnicodeError:
        payload, intents, evidence = None, {}, {}
    if payload is None:
        problems.append("source-runtime motion requires a readable sourceBindings.uiDesign record")
    specimens = {row.get("id"): row for row in showcase.get("specimens", []) if isinstance(row, dict)}
    surfaces = {row.get("id"): row for row in manifest.get("surfaces", []) if isinstance(row, dict)}
    bound: dict[str, dict[str, Any]] = {}
    for row in rows:
        trigger, label = row["trigger"], f"showcase motion {row['variant']}"
        if payload is not None:
            problems.extend(_intent_findings(label, trigger, intents, evidence, read_repo))
        spec = specimens.get(row["specimen"])
        if spec is None:
            continue
        page, surface = spec["source"]["page"], surfaces.get(trigger["surface"])
        if surface is None or surface.get("page") != page:
            problems.append(f"{label} surface {trigger['surface']} is not the manifest surface of {page}")
            continue
        states = [str(item) for item in surface.get("states", []) if "n/a" not in str(item).casefold()]
        targets = [str(item) for item in (surface.get("responsive") or {}).get("targets", [])]
        if trigger["state"] not in states:
            problems.append(f"{label} state {trigger['state']} is not an approved state of {trigger['surface']}")
            continue
        if trigger["target"] not in targets:
            problems.append(f"{label} target {trigger['target']} is not an approved target of {trigger['surface']}")
            continue
        html = documents.get(page)
        if html is None:
            continue
        finding = script_finding(html, trigger["scriptSha256"])
        if finding:
            problems.append(f"{label} scriptSha256 {finding}")
        tree = source.SourceTree(html)
        copies = scoped_copies(tree, spec["source"], trigger["surface"], trigger["state"], targets)
        ambiguous = [target for target, nodes in copies.items() if len(nodes) > 1]
        if ambiguous:
            problems.append(f"{label} specimen is ambiguous in {trigger['surface']} {trigger['state']} at "
                            + ", ".join(ambiguous))
            continue
        if not copies[trigger["target"]]:
            problems.append(f"{label} specimen does not resolve inside {trigger['surface']} state "
                            f"{trigger['state']} at target {trigger['target']}")
            continue
        bound[row["variant"]] = {"row": row, "page": page, "tree": tree, "targets": targets,
                                 "surface": source.surface_node(tree, trigger["surface"]),
                                 "subjects": {target: nodes[0] for target, nodes in copies.items() if nodes}}
    return bound, problems


def _top_level_preludes(css: str) -> list[str]:
    preludes, depth, start = [], 0, 0
    for index, char in enumerate(css):
        if char == "{":
            if depth == 0:
                preludes.append(css[start:index])
            depth += 1
        elif char == "}":
            depth = max(depth - 1, 0)
            if depth == 0:
                start = index + 1
    return preludes


def _scope_matches(scope: str, node: dict[str, Any]) -> bool:
    if scope.startswith("["):
        name, _, value = scope[1:-1].partition("=")
        return name in node["map"] and (not value or node["map"].get(name) == value.strip("\"'"))
    if scope.startswith("."):
        return scope[1:] in (node["map"].get("class") or "").split()
    if scope.startswith("#"):
        return node["map"].get("id") == scope[1:]
    return node["tag"] == scope


def shared_pseudo_rule(css: str, tree: source.SourceTree, node: dict[str, Any], state: str) -> str | None:
    """Return an unconditional ancestor-scoped pseudo rule whose scope is on the specimen's source path.

    Bounded on purpose: one simple ancestor selector, a descendant combinator and
    a bare pseudo-class. Anything else stays unresolved; this is not a cascade engine.
    """
    ancestors = tree.ancestors(node)
    for prelude in _top_level_preludes(css):
        if prelude.lstrip().startswith("@"):
            continue
        for selector in prelude.split(","):
            text = " ".join(selector.split())
            match = _SHARED_PSEUDO_RE.fullmatch(text)
            if match and match.group("state") == state and any(_scope_matches(match.group("scope"), item) for item in ancestors):
                return text
    return None


def closed_open_claim(tree: source.SourceTree, node: dict[str, Any]) -> bool:
    """A closed native <details> on the source path cannot be a rendered open state."""
    return any(item["tag"] == "details" and "open" not in item["map"] for item in tree.ancestors(node) + [node])
