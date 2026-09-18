#!/usr/bin/env python3
"""Render or check a read-only HTML view of a validated design-system pair."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys

from check_design_system_pair import compare


STYLE = """
*{box-sizing:border-box}body{margin:0;background:#fafafa;color:#202020;
font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:40px 24px}
h1{font-size:36px;line-height:1.15}h2{font-size:24px}p{max-width:72ch}
section{border-top:1px solid #ccc;margin-top:32px;padding-top:16px}
table{width:100%;border-collapse:collapse;table-layout:fixed;text-align:left}
th,td{vertical-align:top;padding:12px 8px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}code{font-size:13px}
.sample{display:block;max-width:100%;overflow-wrap:anywhere}.swatch{height:48px;border:1px solid #777}
.measure{background:#ddd;height:16px}.shape{width:72px;height:48px;border:1px solid #555}
.muted{color:#555}a{color:inherit}a:focus-visible{outline:2px solid #222;outline-offset:4px}
@media(max-width:600px){main{padding:24px 16px}h1{font-size:28px}th,td{padding:8px 4px}}
"""


def specimen(group: str, value: object) -> str:
    """Preview only closed scalar CSS values; never execute registry text as CSS."""
    if not isinstance(value, str):
        return "Recorded value; no browser specimen"
    if group == "color" and re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value):
        return f'<span class="sample swatch" style="background:{value}" aria-label="Color swatch"></span>'
    if group in {"space", "radius", "fontSize"} and re.fullmatch(r"(?:0|[0-9]+(?:\.[0-9]+)?)(?:px|rem|em)", value):
        prop, css, label = {
            "space": ("width", "measure", ""),
            "radius": ("border-radius", "shape", ""),
            "fontSize": ("font-size", "", "Aa 字"),
        }[group]
        return f'<span class="sample {css}" style="{prop}:{value}">{label}</span>'
    if group == "lineHeight" and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        return f'<span class="sample" style="line-height:{value}">First line<br>Second line</span>'
    return "Recorded value; no browser specimen"


def render_preview(registry_bytes: bytes, markdown_bytes: bytes) -> str:
    registry = json.loads(registry_bytes.decode("utf-8"))
    title = escape(str(registry["product"]))
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{title} — Design System</title><style>{STYLE}</style></head><body><main>',
        f'<h1>{title} — Design System</h1>',
        '<p>Derived registry view. Pair and source checks passed when generated. This view does not grant Visual Approval; recheck it against current sources before use.</p>',
        '<p class="muted">Token specimens illustrate supported scalar values. Component appearance, font loading, interaction states and native rendering remain defined by the approved HiFi and platform evidence. No component styles are inferred from names.</p>',
        '<nav aria-label="Design system sections"><a href="#tokens">Tokens</a> · <a href="#primitives">Primitives</a> · <a href="#components">Product components</a> · <a href="#rules">States and responsive rules</a> · <a href="#sources">Sources</a></nav>',
        '<section id="tokens"><h2>Tokens</h2>',
    ]
    for group, entries in registry.get("tokens", {}).items():
        if not isinstance(entries, dict):
            entries = {group: entries}
        parts.append(f'<h3>{escape(group)}</h3><table><thead><tr><th scope="col">Token</th><th scope="col">Value</th><th scope="col">Specimen</th></tr></thead><tbody>')
        for name, value in entries.items():
            display = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            parts.append(f'<tr><th scope="row"><code>{escape(name)}</code></th><td><code>{escape(display)}</code></td><td>{specimen(group, value)}</td></tr>')
        parts.append('</tbody></table>')
    parts.append('</section>')
    for anchor, heading, key in (
        ("primitives", "Primitives and declared variants", "primitives"),
        ("components", "Product components and content order", "productComponents"),
    ):
        parts.append(f'<section id="{anchor}"><h2>{heading}</h2>')
        for name, contract in registry.get(key, {}).items():
            parts.append(f'<h3>{escape(name)}</h3><pre>{escape(json.dumps(contract, ensure_ascii=False, indent=2))}</pre>')
        parts.append('</section>')
    parts.append('<section id="rules"><h2>States, motion and responsive rules</h2>')
    rules = {key: registry[key] for key in (
        "platform", "stackSemantics", "surfaceContracts", "viewports", "sizeClasses",
        "stateMatrix", "motionVariants", "signatureRules",
    ) if key in registry}
    parts.append(f'<pre>{escape(json.dumps(rules, ensure_ascii=False, indent=2))}</pre></section>')
    parts.append('<section id="sources"><h2>Source identities</h2>')
    for name, payload in (("Registry", registry_bytes), ("Markdown", markdown_bytes)):
        parts.append(f'<p>{name} SHA-256: <code>{hashlib.sha256(payload).hexdigest()}</code></p>')
    parts.append(f'<pre>{escape(json.dumps(registry.get("sourceBindings", {}), ensure_ascii=False, indent=2))}</pre></section>')
    parts.append('</main></body></html>\n')
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--check", type=Path, help="check an existing HTML view instead of emitting HTML")
    args = parser.parse_args(argv)
    try:
        registry_bytes = args.registry.read_bytes()
        markdown_bytes = args.markdown.read_bytes()
        registry = json.loads(registry_bytes.decode("utf-8"))
        if not isinstance(registry, dict):
            raise ValueError("registry must be an object")
        problems = compare(markdown_bytes.decode("utf-8"), registry, require_filled=True, repo_root=args.repo_root)
        if problems:
            raise ValueError("\n".join(problems))
        output = render_preview(registry_bytes, markdown_bytes).encode("utf-8")
        if args.check:
            if args.check.read_bytes() != output:
                raise ValueError("design-system preview is stale or modified; regenerate from the current validated pair")
            print("PASS design-system preview matches the current pair and sources")
        else:
            sys.stdout.buffer.write(output)
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
