#!/usr/bin/env python3
"""Assemble caller-authored product pages into an offline HiFi review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from reviewer_shell import inject_runtime, inject_shared_css, inject_shell, update_manifest_child_hashes

PAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.html$")
MANIFEST_RE = re.compile(
    r'<script id="ui-hifi-manifest" type="application/json">([\s\S]*?)</script>',
    re.IGNORECASE,
)


def _fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _linked_path(path: Path) -> bool:
    """Reject source/output paths routed through symlinks or Windows junctions."""

    return any(part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction())
               for part in (path, *path.parents))


def _parse_sources(values: list[str]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    lower_seen: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            _fail(f"invalid --source {value!r}; use page=path")
        page, raw_path = value.split("=", 1)
        page = page.strip()
        raw_path = raw_path.strip()
        if not PAGE_RE.fullmatch(page):
            _fail(f"invalid bundle page {page!r}")
        lowered = page.casefold()
        previous = lower_seen.get(lowered)
        if previous:
            _fail(f"case-colliding bundle pages {previous!r} and {page!r}")
        if not raw_path or Path(raw_path).name in {"", ".", ".."}:
            _fail(f"invalid source path for {page!r}")
        path = Path(raw_path)
        if not path.is_file():
            _fail(f"declared source is missing: {path}")
        if _linked_path(path):
            _fail(f"linked source is not allowed: {path}")
        sources[page] = path
        lower_seen[lowered] = page
    if "index.html" not in sources:
        _fail("the entry page index.html is required")
    return sources


def _load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read manifest {path}: {exc}")
    if not isinstance(value, dict) or value.get("schema") != "ui-hifi/2":
        _fail("manifest must be schema ui-hifi/2")
    if not isinstance(value.get("surfaces"), list) or not value["surfaces"]:
        _fail("manifest surfaces must be a non-empty list")
    return value


def _declared_pages(manifest: dict) -> list[str]:
    pages: list[str] = []
    for row in manifest["surfaces"]:
        page = row.get("page") if isinstance(row, dict) else None
        if not isinstance(page, str) or not PAGE_RE.fullmatch(page):
            _fail(f"manifest surface has an invalid page: {page!r}")
        if page not in pages:
            pages.append(page)
    if "index.html" not in pages:
        _fail("manifest must declare index.html")
    return pages


def _check_declared_hashes(manifest: dict, sources: dict[str, Path]) -> None:
    declared = manifest.get("pages")
    if not isinstance(declared, list):
        return
    rows: dict[str, str] = {}
    for row in declared:
        if not isinstance(row, dict) or set(row) < {"path", "sha256"}:
            _fail("manifest child pages must contain path and sha256")
        page = row.get("path")
        digest = row.get("sha256")
        if not isinstance(page, str) or not PAGE_RE.fullmatch(page) or page == "index.html":
            _fail(f"invalid manifest child page {page!r}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            _fail(f"invalid manifest child hash for {page!r}")
        if page in rows:
            _fail(f"duplicate manifest child page: {page}")
        rows[page] = digest
    if set(rows) != set(sources) - {"index.html"}:
        _fail("manifest child hashes must exactly match declared child sources")
    for page, path in sources.items():
        if page == "index.html":
            continue
        if page not in rows:
            _fail(f"manifest child page is missing: {page}")
        try:
            actual = _sha256(path.read_bytes())
        except OSError as exc:
            _fail(f"cannot read declared source {path}: {exc}")
        if actual != rows[page]:
            _fail(f"declared source is stale: {page}")
    extra = sorted(set(rows) - set(sources))
    if extra:
        _fail("manifest lists undeclared child pages: " + ", ".join(extra))


def _require_product_structure(html: str, page: str) -> None:
    if MANIFEST_RE.search(html) and page != "index.html":
        _fail(f"child page must not contain a HiFi manifest: {page}")
    if 'data-hifi-canvas' not in html:
        _fail(f"{page} must provide its own exact-width [data-hifi-canvas] product wrapper")
    if page == "index.html":
        for panel in ("overview", "design-tokens"):
            if f'data-hifi-panel="{panel}"' not in html:
                _fail(f"index.html must provide its author-authored {panel} panel")


def assemble(
    manifest_path: Path,
    source_values: list[str],
    output_dir: Path,
    *,
    overwrite: bool = False,
) -> list[str]:
    sources = _parse_sources(source_values)
    manifest = _load_manifest(manifest_path)
    if _linked_path(manifest_path):
        _fail("linked manifest is not allowed")
    declared = _declared_pages(manifest)
    if sorted(declared, key=str.casefold) != sorted(sources, key=str.casefold):
        _fail(
            "declared sources must exactly match manifest pages: "
            + ", ".join(declared)
        )
    _check_declared_hashes(manifest, sources)
    source_paths = {path.resolve(strict=True) for path in sources.values()}
    if len(source_paths) != len(sources):
        _fail("declared sources must be distinct files")
    if manifest_path.resolve(strict=True) in source_paths:
        _fail("manifest cannot also be a source page")
    if _linked_path(output_dir):
        _fail("linked output directory is not allowed")
    if output_dir.exists() and not output_dir.is_dir():
        _fail(f"output path is not a directory: {output_dir}")
    destinations = [output_dir / page for page in sources]
    if any(_linked_path(path) or path.resolve() in source_paths | {manifest_path.resolve(strict=True)} for path in destinations):
        _fail("output destination aliases an input or is a link")
    existing = [path for path in destinations if path.exists()]
    if existing and not overwrite:
        _fail("output files already exist; pass --overwrite to replace them")

    rendered: dict[str, bytes] = {}
    package_source = json.dumps(
        {"manifest": manifest, "bundleLocation": output_dir.resolve().as_posix()},
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    package_id = f"ui-hifi/2:{_sha256(package_source)[:16]}"
    for page, source in sources.items():
        try:
            html = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            _fail(f"cannot read source {source}: {exc}")
        _require_product_structure(html, page)
        html = inject_shared_css(html)
        html = inject_shell(manifest, html, page, version=3)
        html = inject_runtime(html)
        html = html.replace(
            "<script>connectHifiReviewer()</script>",
            f'<script>connectHifiReviewer({json.dumps({"packageId": package_id})})</script>',
        )
        rendered[page] = html.encode("utf-8")

    if "index.html" in rendered:
        if not MANIFEST_RE.search(rendered["index.html"].decode("utf-8")):
            _fail("index.html must contain the caller-authored ui-hifi manifest")
        entry = rendered["index.html"].decode("utf-8")
        embedded = json.loads(MANIFEST_RE.search(entry).group(1))
        if embedded != manifest:
            _fail("entry manifest must exactly match the supplied manifest")
        rendered["index.html"] = update_manifest_child_hashes(entry, rendered).encode("utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    for page, content in rendered.items():
        (output_dir / page).write_bytes(content)
    return [str(path) for path in destinations]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = assemble(
        args.manifest,
        args.source,
        args.output_dir,
        overwrite=args.overwrite,
    )
    print("PASS assembled " + ", ".join(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
