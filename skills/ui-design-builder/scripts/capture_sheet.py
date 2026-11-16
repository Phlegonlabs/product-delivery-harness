#!/usr/bin/env python3
"""Write one self-contained HTML sheet of labelled image rows.

A one-image row is a reference-board entry; consecutive entries share one grid. A row of two or
more images sits side by side at full width, for example selected direction next to HiFi candidate.
The sheet is for people to judge by eye.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import sys

from review_evidence import safe_path

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

CSS = """
:root{color-scheme:light dark;--bg:#f7f7f6;--fg:#1d1e20;--muted:#66696f;--line:#dcdcd9;--well:#ececea}
@media (prefers-color-scheme:dark){:root{--bg:#1b1c1e;--fg:#e8e8e6;--muted:#9a9da3;--line:#37393d;--well:#242528}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1440px;margin:0 auto;padding:40px 16px 64px}
h1{margin:0 0 32px;font-size:1.5rem;font-weight:600;line-height:1.25}
h2{margin:0 0 12px;font-size:1rem;font-weight:600}
.pair,.board{padding:24px 0;border-top:1px solid var(--line)}
h1+.pair,h1+.board{border-top:0;padding-top:0}
.shots{display:grid;gap:16px;grid-template-columns:repeat(var(--n),minmax(0,1fr));align-items:start}
.board{display:grid;gap:32px 16px;grid-template-columns:repeat(auto-fill,minmax(min(400px,100%),1fr));align-items:start}
figure{margin:0;min-width:0}
.well{padding:8px;background:var(--well);border:1px solid var(--line);border-radius:6px}
.board .well{max-height:70vh;overflow:auto}
img{display:block;max-width:100%;height:auto;margin:0 auto}
.board img{width:100%}
figcaption{margin-top:8px;font-size:.8125rem;color:var(--muted);overflow-wrap:anywhere}
figcaption b{display:block;color:var(--fg);font-weight:600}
code{display:block;font:.75rem/1.4 ui-monospace,Consolas,monospace}
@media (max-width:640px){.shots{grid-template-columns:1fr}main{padding-top:24px}}
"""
CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"


def locate(root: Path, text: str, suffixes: set[str]) -> tuple[str, Path]:
    path = Path(text)
    if not path.is_absolute():
        path = root / path
    try:
        relative = Path(os.path.normpath(path)).relative_to(root).as_posix()
    except ValueError:
        raise ValueError("path escapes the repository root: " + text) from None
    if path.suffix.lower() not in suffixes:
        raise ValueError("unsupported file type (use " + ", ".join(sorted(suffixes)) + "): " + text)
    return relative, safe_path(root, relative)


def read_image(root: Path, text: str) -> dict:
    relative, path = locate(root, text, set(MIME))
    if not path.is_file():
        raise ValueError("image is missing: " + text)
    data = path.read_bytes()
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
            "uri": "data:" + MIME[path.suffix.lower()] + ";base64," + base64.b64encode(data).decode("ascii")}


def render(title: str, rows: list[dict], columns: list[str]) -> str:
    esc = html.escape
    out = ['<!doctype html>', '<html lang="en">', "<head>", '<meta charset="utf-8">',
           f'<meta http-equiv="Content-Security-Policy" content="{CSP}">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f"<title>{esc(title)}</title>", f"<style>{CSS}</style>", "</head>", "<body>",
           "<main>", f"<h1>{esc(title)}</h1>"]
    in_board = False
    for row in rows:
        # Consecutive one-image rows share one board grid of scrollable captures. A row of
        # several images is a full-width comparison whose captures scroll with the page.
        single = len(row["images"]) == 1
        if single != in_board:
            out.append('<div class="board">' if single else "</div>")
            in_board = single
        out += ["<section>" if single else '<section class="pair">', f"<h2>{esc(row['label'])}</h2>"]
        if not single:
            out.append(f'<div class="shots" style="--n:{len(row["images"])}">')
        for index, image in enumerate(row["images"]):
            heading = f"<b>{esc(columns[index])}</b>" if index < len(columns) else ""
            alt = esc(row["label"] + (" - " + columns[index] if index < len(columns) else ""))
            out += ["<figure>", f'<div class="well" tabindex="0"><img src="{image["uri"]}" alt="{alt}"></div>',
                    f'<figcaption>{heading}{esc(image["path"])}<code>sha256:{image["sha256"]}</code></figcaption>',
                    "</figure>"]
        out += ["</section>"] if single else ["</div>", "</section>"]
    if in_board:
        out.append("</div>")
    return "\n".join(out + ["</main>", "</body>", "</html>"]) + "\n"


def build(root: Path, title: str, row_args: list[list[str]], columns: list[str], out: str, overwrite: bool) -> dict:
    if not title.strip():
        raise ValueError("--title must not be empty")
    rows = []
    for spec in row_args:
        if len(spec) < 2:
            raise ValueError("--row needs a label and at least one image: " + " ".join(spec))
        if columns and len(spec) - 1 > len(columns):
            raise ValueError("row has more images than --columns names: " + spec[0])
        rows.append({"label": spec[0], "images": [read_image(root, item) for item in spec[1:]]})
    relative, target = locate(root, out, {".html"})
    if target.exists() and not overwrite:
        raise ValueError("output exists; pass --overwrite to replace it: " + relative)
    data = render(title, rows, columns).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"schema": "capture-sheet/1", "out": {"path": relative, "sha256": hashlib.sha256(data).hexdigest()},
            "rows": [{"label": row["label"], "images": [{"path": i["path"], "sha256": i["sha256"]} for i in row["images"]]}
                     for row in rows]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--row", nargs="+", action="append", required=True, metavar=("LABEL", "IMAGE"),
                        help="row label then one or more images; repeat for more rows")
    parser.add_argument("--columns", nargs="+", default=[], metavar="NAME",
                        help="column names for the images in each row, in order")
    parser.add_argument("--out", required=True, help="HTML file to write inside the repository root")
    parser.add_argument("--overwrite", action="store_true")
    options = parser.parse_args(argv)
    try:
        result = build(options.repo_root.resolve(), options.title, options.row, options.columns,
                       options.out, options.overwrite)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, "capture sheet blocked: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
