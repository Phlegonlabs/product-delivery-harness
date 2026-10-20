"""Static animation-name provenance for a closed CSS subset.

This is not a browser CSS engine. Unsupported animation/custom-property rules
fail closed rather than supplying evidence for an approved specimen.
"""

import re
import math


IDENT = r"[A-Za-z_][\w-]*"
COMPOUND = re.compile(rf"(?:[A-Za-z][\w-]*|\*)?(?:[.#]{IDENT})*")
SENSITIVE = re.compile(r"(?:^|[;{])\s*(?:(?:-webkit-)?animation(?:-[\w-]+)?|all|--[\w-]+)\s*:", re.I)
ANIMATION_ONLY = re.compile(r"(?:^|[;{])\s*(?:(?:-webkit-)?animation(?:-[\w-]+)?|all)\s*:", re.I)
VAR_REF = re.compile(r"var\(\s*(--[\w-]+)")
CONDITIONAL_VAR = re.compile(r"(--[\w-]+)\s*:")
PROPERTY_NAME = re.compile(rf"@(?:-webkit-)?property\s+(--{IDENT})", re.I)


def _split(value, separator):
    """Split only outside functions; quoted/escaped CSS is outside this subset."""
    if any(char in value for char in "\"'\\"):
        raise ValueError("quoted or escaped CSS")
    parts, start, depth = [], 0, 0
    for index, char in enumerate(value):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth < 0:
            raise ValueError("unbalanced function")
        if depth == 0 and (char.isspace() if separator == " " else char == separator):
            if value[start:index].strip():
                parts.append(value[start:index].strip())
            elif separator != " ":
                raise ValueError("empty CSS item")
            start = index + 1
    if depth or not value[start:].strip():
        raise ValueError("incomplete CSS value")
    return parts + [value[start:].strip()]


def _rules(css, *, static_only=False):
    rules, keyframes, conditional, registrations = [], {}, [], []
    cursor = 0
    sensitive = ANIMATION_ONLY if static_only else SENSITIVE
    css = re.sub(r"/\*[\s\S]*?\*/", "", css)
    if "\\" in css:
        raise ValueError("escaped CSS")
    while cursor < len(css):
        start = css.find("{", cursor)
        if start < 0:
            if css[cursor:].strip():
                raise ValueError("unsupported trailing CSS")
            break
        header = css[cursor:start].strip()
        depth, end = 1, start + 1
        while end < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[end], 0)
            end += 1
        if depth:
            raise ValueError("unclosed CSS rule")
        body, cursor = css[start + 1:end - 1], end
        keyframe = re.fullmatch(rf"@(?:-webkit-)?keyframes\s+({IDENT})", header, re.I)
        if keyframe:
            keyframes[keyframe.group(1)] = body
        elif header.startswith("@"):
            if ANIMATION_ONLY.search(body) or ";" in header:
                raise ValueError("conditional or layered animation CSS")
            if (property_name := PROPERTY_NAME.fullmatch(header)) is not None:
                registrations.append(property_name.group(1))
            if CONDITIONAL_VAR.search(body):
                conditional.append(body)
        elif sensitive.search(body):
            if "{" in body or "}" in body:
                raise ValueError("nested animation CSS")
            selectors = [item.strip() for item in header.split(",")]
            if not all(item == ":root" or (item and COMPOUND.fullmatch(item)) for item in selectors):
                raise ValueError("unsupported animation selector")
            rules.append((selectors, body))
    return rules, keyframes, conditional, registrations


def _specificity(node, selector):
    if selector == ":root":
        return (0, 1, 0) if node["parent"] is None and node["tag"] == "html" else None
    tokens = re.findall(rf"[.#]{IDENT}|[A-Za-z][\w-]*|\*", selector)
    classes = (node["map"].get("class") or "").split()
    for token in tokens:
        matches = (token[1:] in classes if token.startswith(".") else
                   node["map"].get("id") == token[1:] if token.startswith("#") else
                   token == "*" or node["tag"] == token.lower())
        if not matches:
            return None
    return (sum(token.startswith("#") for token in tokens),
            sum(token.startswith(".") for token in tokens),
            sum(token[0] not in ".#*" for token in tokens))


def _cascade(rules, node):
    winners = {}
    sources = []
    for selectors, body in rules:
        ranks = [rank for selector in selectors if (rank := _specificity(node, selector)) is not None]
        if ranks:
            sources.append(((0, *max(ranks)), body))
    sources.append(((1, 0, 0, 0), node["map"].get("style") or ""))
    for order, (specificity, body) in enumerate(sources):
        if "\\" in body:
            raise ValueError("escaped inline CSS")
        for position, declaration in enumerate(body.split(";")):
            if ":" not in declaration:
                continue
            prop, value = (item.strip() for item in declaration.split(":", 1))
            prop = prop if prop.startswith("--") else prop.lower()
            if prop.startswith("-webkit-animation"):
                prop = prop.removeprefix("-webkit-")
            important = bool(re.search(r"!\s*important\s*$", value, re.I))
            value = re.sub(r"!\s*important\s*$", "", value, flags=re.I).strip()
            rank = (important, *specificity, order, position)
            targets = [prop]
            if prop in {"animation", "all"}:
                targets.append("animation-name")
            for target in targets:
                if target not in winners or rank >= winners[target][0]:
                    winners[target] = (rank, prop, value)
    return winners


def _substitute(value, lookup):
    while (match := re.search(r"var\(", value)) is not None:
        depth, end = 1, match.end()
        while end < len(value) and depth:
            depth += {"(": 1, ")": -1}.get(value[end], 0)
            end += 1
        if depth:
            raise ValueError("unclosed variable")
        parts = _split(value[match.end():end - 1], ",")
        if re.fullmatch(r"--[\w-]+", parts[0]) is None:
            raise ValueError("invalid variable name")
        replacement = lookup(parts[0])
        if replacement is None:
            if len(parts) < 2:
                raise ValueError("unresolved variable")
            replacement = _substitute(",".join(parts[1:]), lookup)
        value = value[:match.start()] + replacement + value[end:]
    return value


def _variables(winners, inherited):
    raw = {name: row[2] for name, row in winners.items() if name.startswith("--")}
    cyclic = set()

    def find_cycles(name, path):
        if name in path:
            cyclic.update(path[path.index(name):])
        elif name in raw:
            if len(path) > 64:
                raise ValueError("variable dependency depth")
            for dependency in VAR_REF.findall(raw[name]):
                find_cycles(dependency, path + [name])

    for name in raw:
        find_cycles(name, [])
    computed = dict(inherited)

    def lookup(name):
        if name in cyclic:
            return None
        if name not in raw:
            return computed.get(name)
        value = raw[name]
        if value in {"inherit", "unset"}:
            return inherited.get(name)
        if value in {"initial", "revert", "revert-layer"}:
            return None
        try:
            return _substitute(value, lookup)
        except ValueError:
            return None

    computed.update({name: lookup(name) for name in raw})
    return computed


def _timing_function(token):
    match = re.fullmatch(r"(cubic-bezier|steps)\(([^()]+)\)", token)
    if match is None:
        return False
    parts = _split(match.group(2), ",")
    number = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
    if match.group(1) == "cubic-bezier":
        return (len(parts) == 4 and all(re.fullmatch(number, item) for item in parts)
                and all(math.isfinite(float(item)) for item in parts)
                and all(0 <= float(parts[index]) <= 1 for index in (0, 2)))
    if len(parts) not in {1, 2} or re.fullmatch(r"[1-9]\d*", parts[0]) is None:
        return False
    return len(parts) == 1 or (parts[1] in {"start", "end", "jump-start", "jump-end", "jump-none", "jump-both"}
                              and (parts[1] != "jump-none" or int(parts[0]) > 1))


def _names(value, shorthand):
    names = set()
    keyword_groups = [
        {"ease", "linear", "ease-in", "ease-out", "ease-in-out", "step-start", "step-end"},
        {"infinite"}, {"normal", "reverse", "alternate", "alternate-reverse"},
        {"forwards", "backwards", "both"}, {"running", "paused"},
    ]
    for item in _split(value, ","):
        if not shorthand:
            if re.fullmatch(IDENT, item) is None:
                raise ValueError("nonliteral animation name")
            name = item
        else:
            name, times, groups, none_count = None, 0, set(), 0
            for token in _split(item, " "):
                if token.lower() == "none":
                    none_count += 1
                    continue
                if re.fullmatch(r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:ms|s)", token):
                    times += 1
                    if times > 2 or (times == 1 and token.startswith("-")):
                        raise ValueError("invalid animation time")
                    continue
                group = next((index for index, keywords in enumerate(keyword_groups) if token.lower() in keywords), None)
                if re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", token):
                    group = 1
                if _timing_function(token):
                    group = 0
                if group is not None:
                    if group in groups:
                        raise ValueError("duplicate animation field")
                    groups.add(group)
                elif re.fullmatch(IDENT, token) and name is None:
                    name = token
                else:
                    raise ValueError("unsupported animation value")
            allowed_none = (1 if name is None else 0) if 3 in groups else (2 if name is None else 1)
            if none_count > allowed_none:
                raise ValueError("duplicate animation none")
            name = name or "none"
        if name.lower() in {"initial", "inherit", "unset", "revert", "revert-layer"}:
            raise ValueError("CSS-wide animation value")
        if name.lower() != "none":
            names.add(name)
    return names


def source_status(css, node, ancestors=()):
    """Classify animation provenance without treating static controls as failures."""
    try:
        rules, keyframes, conditional, registrations = _rules(css)
        variables = {}
        for ancestor in (*ancestors, node):
            winners = _cascade(rules, ancestor)
            variables = _variables(winners, variables)
        winner = winners.get("animation-name")
        if winner is None:
            return "no_animation"
        if winner[1] == "all":
            return "unresolved"
        value = _substitute(winner[2], variables.get)
        names = _names(value, winner[1] == "animation")
        if not names:
            return "no_animation"
        relevant = set(VAR_REF.findall(winner[2]))
        for name, body in keyframes.items():
            if name in names:
                relevant.update(VAR_REF.findall(body))
        queue = set(relevant)
        while queue:
            name = queue.pop()
            value = variables.get(name) or ""
            if name in variables:
                fallbacks = set(VAR_REF.findall(value))
                relevant.update(fallbacks)
                queue.update(fallbacks.difference(relevant))
        if (set(registrations) & relevant
                or any(set(CONDITIONAL_VAR.findall(body)) & relevant
                       for body in conditional)):
            return "unresolved"
        return "source_backed" if names <= set(keyframes) else "unresolved"
    except (ValueError, RecursionError):
        # Custom properties cannot affect a literal absence of animation.
        # This narrower inspection can prove only no_animation, never provenance.
        try:
            rules, _, _, _ = _rules(css, static_only=True)
            winner = _cascade(rules, node).get("animation-name")
            if winner is None or (winner[1] != "all" and not _names(winner[2], winner[1] == "animation")):
                return "no_animation"
        except (ValueError, RecursionError):
            pass
        return "unresolved"


def source_backed(css, node, ancestors=()):
    """Require resolved winning names and their unconditional source keyframes."""
    return source_status(css, node, ancestors) == "source_backed"
