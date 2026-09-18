"""Check a UI publication checkout at final logical paths without publishing it."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import check_ui_design_contract as ui

HARNESS = Path(__file__).resolve().parents[2] / "delivery-harness" / "scripts"
sys.path.insert(0, str(HARNESS))
from harness_git import run_git, _path_has_reparse_or_link  # noqa: E402
import check_product_package as product  # noqa: E402

COMPILER = Path(__file__).resolve().parents[2] / "design-system-compiler" / "scripts"
sys.path.insert(0, str(COMPILER))
from render_design_system_preview import render_preview  # noqa: E402


def _git(root: Path, *args: str) -> str:
    result = run_git(root, *args, encoding="utf-8", errors="strict")
    if result.returncode:
        raise ValueError("publication requires an accessible Git checkout and history")
    return result.stdout.strip()


def inventory(root: Path) -> dict[str, str]:
    ignored = _git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", "docs/design")
    for name in ignored.split("\0"):
        if name and not name.startswith("docs/design/.ui-staging/"):
            raise ValueError(f"publication artifacts must not be ignored: {name}")
    paths = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    result = {}
    for name in sorted(set(paths.split("\0")) - {""}):
        path = root / name
        if not path.is_file() or _path_has_reparse_or_link(path):
            raise ValueError(f"publication source must be a regular non-link file: {name}")
        if path.name in {".env", ".dev.vars"} or (
            path.name.startswith((".env.", ".dev.vars.")) and not path.name.endswith(".example")
        ):
            raise ValueError(f"value-bearing environment file must not be tracked: {name}")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate(source: Path, root: Path, *, hifi: Path, required: bool = False,
             published: bool = False) -> list[str]:
    source, root = source.resolve(), root.resolve()
    try:
        if source == root:
            raise ValueError("source and publication checkout must be distinct")
        for checkout in (source, root):
            if Path(_git(checkout, "rev-parse", "--show-toplevel")).resolve() != checkout:
                raise ValueError("each root must be a Git checkout root")
        head = _git(source, "rev-parse", "HEAD")
        if head != _git(root, "rev-parse", "HEAD"):
            raise ValueError("publication checkout HEAD differs from source HEAD")
        before, candidate = inventory(source), inventory(root)
        def upstream(items):
            return {k: v for k, v in items.items() if not k.startswith("docs/design/")}
        if upstream(before) != upstream(candidate):
            raise ValueError("upstream/source files differ between publication and source checkout")
        if published and before != candidate:
            raise ValueError("published bytes differ from the checked publication set")
        if hifi.is_absolute() or ".." in hifi.parts:
            raise ValueError("HiFi must name its final repository-relative path")
        problems = product.validate(root / "docs/product/PRD.md",
                                    root / "docs/product/architecture.md",
                                    root / "docs/product/stack-decisions.md",
                                    repo_root=root, require_filled=True, require_approved=True)
        problems += ui.validate(root / "docs/design/ui-design.md", repo_root=root,
                                prd_path=root / "docs/product/PRD.md",
                                wireframes_path=root / "docs/design/wireframes.html",
                                hifi_path=root / hifi,
                                design_system_markdown_path=root / "docs/design/design-system.md" if required else None,
                                design_system_registry_path=root / "docs/design/design-system.json" if required else None,
                                require_filled=True, require_wireframe_approved=True,
                                require_visual_approved=True)
        if required:
            # ui.validate above verifies the formal pair and its source bindings.
            # The view is derived; it must not drift or disappear during transfer.
            preview = root / "docs/design/design-system-preview.html"
            expected = render_preview(
                (root / "docs/design/design-system.json").read_bytes(),
                (root / "docs/design/design-system.md").read_bytes(),
            ).encode("utf-8") if not problems else None
            if not preview.is_file():
                problems.append("required design-system preview is missing")
            elif expected is not None and preview.read_bytes() != expected:
                problems.append("design-system preview is stale or modified")
        if before != inventory(source) or candidate != inventory(root) or any(
            _git(checkout, "rev-parse", "HEAD") != head for checkout in (source, root)
        ):
            raise ValueError("source/publication inputs changed during validation")
        return problems
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--hifi", required=True, type=Path)
    parser.add_argument("--design-system-required", action="store_true")
    parser.add_argument("--published", action="store_true")
    args = parser.parse_args()
    problems = validate(args.source_root, args.repo_root, hifi=args.hifi,
                        required=args.design_system_required, published=args.published)
    print(json.dumps({"problems": problems, "published": args.published}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
