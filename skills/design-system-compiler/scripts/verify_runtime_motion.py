#!/usr/bin/env python3
"""Browser acceptance for ds-showcase/2 source-runtime motion in an exact preview.

Rendering emits an unverified candidate. This separate read-only check proves
playback on those exact bytes: it validates the pair, requires the preview to
equal a fresh render, drives every source-runtime row at every bound target in
fresh Chromium contexts and writes a new receipt bound to the preview, pair,
HiFi pages and renderer module hashes. Exit 0 only for PASS.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
RENDERER_MODULES = ("render_design_system_preview.py", "check_design_system_pair.py", "design_system_showcase.py",
                    "showcase_runtime.py", "design_system_gallery.py", "design_system_gallery_assets.py",
                    "design_system_gallery_runtime.py", "design_system_runtime_assets.py", "verify_runtime_motion.py")

PROBE = r"""
const [,, url, module, plan] = process.argv;
const {chromium} = require(module);
(async () => {
  const browser = await chromium.launch();
  const results = [];
  for (const row of JSON.parse(plan)) for (const target of row.targets) {
    const context = await browser.newContext({viewport: {width: 1280, height: 800}});
    const page = await context.newPage();
    const errors = [], requests = [], popups = [];
    page.on("pageerror", error => errors.push(String(error)));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    context.on("request", request => { if (!/^(file|about|data):/.test(request.url())) requests.push(request.url()); });
    page.on("popup", popup => popups.push(popup.url()));
    await page.goto(url);
    const figure = "#m-" + row.slug + " + figure";
    const phase = () => page.$eval(figure, item => item.getAttribute("data-ds-phase"));
    const press = selector => page.$eval(selector, item => item.click());
    const until = async (wanted, limit) => {
      const end = Date.now() + limit, seen = [];
      while (Date.now() < end) {
        const value = await phase();
        if (seen[seen.length - 1] !== value) seen.push(value);
        if (wanted.includes(value)) return {value, seen};
        await page.waitForTimeout(40);
      }
      return {value: await phase(), seen};
    };
    const settle = async limit => {
      const end = Date.now() + limit, seen = [];
      let since = null;
      while (Date.now() < end) {
        const value = await phase();
        if (seen[seen.length - 1] !== value) seen.push(value);
        if (value === "invalid") return {value, seen};
        since = value === "settled" ? since || Date.now() : null;
        if (since && Date.now() - since >= 1500) return {value, seen};
        await page.waitForTimeout(40);
      }
      return {value: await phase(), seen};
    };
    const running = async () => (await (await page.$(figure + " iframe")).contentFrame())
      .evaluate(() => document.getAnimations().filter(item => item.playState === "running").length);
    const result = {variant: row.variant, target};
    const offscreen = await page.$eval(figure, item => {
      const top = item.getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, Math.max(0, top - window.innerHeight - 400));
      return item.getBoundingClientRect().top > window.innerHeight;
    });
    await press(figure + ' button[data-ds-runtime-target="' + target + '"]');
    await page.waitForTimeout(900);
    result.offscreen = offscreen;
    result.beforeView = await phase();
    await page.$eval(figure, item => item.scrollIntoView({block: "center"}));
    const first = await settle(20000);
    Object.assign(result, {first: first.value, firstSeen: first.seen, firstStatus: await page.$eval(figure + " .status", item => item.textContent)});
    await press(figure + ' button[data-ds-runtime="replay"]');
    const replay = await settle(20000);
    Object.assign(result, {replay: replay.value, replaySeen: replay.seen});
    await press(figure + ' button[data-ds-runtime="replay"]');
    result.playingBeforeStop = (await until(["playing"], 8000)).value;
    await press(figure + ' button[data-ds-runtime="stop"]');
    result.stop = (await until(["stopped"], 3000)).value;
    await page.waitForTimeout(1200);
    Object.assign(result, {stopAfter: await phase(), stopRunning: await running()});
    await press("[data-ds-reduced-toggle]");
    result.reduced = (await until(["reduced", "invalid"], 8000)).value;
    result.reducedRunning = await running();
    await press("[data-ds-reduced-toggle]");
    Object.assign(result, {errors, requests, popups});
    result.pass = (row.activation !== "viewport" || !offscreen || result.beforeView === "pending")
      && result.first === "settled" && result.replay === "settled" && result.playingBeforeStop === "playing"
      && result.stop === "stopped" && result.stopAfter === "stopped" && result.stopRunning === 0
      && result.reduced === "reduced" && result.reducedRunning === 0 && !errors.length && !requests.length && !popups.length;
    results.push(result);
    await context.close();
  }
  console.log(JSON.stringify({browser: browser.version(), results}));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
"""


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "item"


def acceptance_plan(registry: dict, runtime: dict) -> list[dict]:
    rows = [row for row in registry["showcase"]["motion"] if row["variant"] in runtime]
    return [{"variant": row["variant"], "slug": _slug(row["variant"]), "activation": row["trigger"]["activation"]["kind"],
             "targets": [target for target in runtime[row["variant"]]["targets"] if target in runtime[row["variant"]]["subjects"]]}
            for row in rows]


def run_acceptance(preview: Path, plan: list[dict], *, timeout: int | None = None) -> dict:
    """Drive the exact preview file in Chromium; return the raw observation report."""
    node = shutil.which("node")
    module = os.environ.get("PLAYWRIGHT_MODULE") or "playwright"
    if not node:
        raise RuntimeError("Node.js is required for source-runtime browser acceptance")
    cases = sum(len(row["targets"]) for row in plan)
    completed = subprocess.run([node, "-", preview.resolve().as_uri(), module, json.dumps(plan)], input=PROBE, text=True,
                               encoding="utf-8", capture_output=True, timeout=timeout or 90 + 75 * cases)
    if completed.returncode != 0:
        raise RuntimeError("browser acceptance failed to run: " + completed.stderr[-2000:])
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    package = Path(module) / "package.json"
    report["playwright"] = json.loads(package.read_text(encoding="utf-8")).get("version") if package.is_file() else "unknown"
    report["verdict"] = "PASS" if report["results"] and all(item.get("pass") for item in report["results"]) else "FAIL"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("--repo-root", "--registry", "--markdown", "--preview", "--receipt"):
        parser.add_argument(name, type=Path, required=True)
    args = parser.parse_args(argv)
    from check_design_system_pair import compare, load_showcase_sources, read_repo_file
    from render_design_system_preview import render_view
    import showcase_runtime

    try:
        registry_bytes, markdown_bytes = args.registry.read_bytes(), args.markdown.read_bytes()
        preview_bytes = args.preview.read_bytes()
        registry = json.loads(registry_bytes.decode("utf-8"))
        problems = compare(markdown_bytes.decode("utf-8"), registry, require_filled=True, repo_root=args.repo_root)
        if problems:
            raise ValueError("\n".join(problems))
        if render_view(registry_bytes, markdown_bytes, args.repo_root).encode("utf-8") != preview_bytes:
            raise ValueError("preview is not the exact generated HTML for the current pair and sources")
        root = args.repo_root.resolve()
        documents, manifest, binding, _ = load_showcase_sources(registry, root)
        runtime, _ = showcase_runtime.resolve_runtime(registry, documents, manifest, lambda path: read_repo_file(root, path))
        plan = acceptance_plan(registry, runtime)
        report = run_acceptance(args.preview, plan) if plan else {"results": [], "verdict": "NOT_APPLICABLE"}
    except (OSError, UnicodeError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    receipt = {"schema": "ds-runtime-acceptance/1", "createdAt": datetime.now(timezone.utc).isoformat(),
               "verdict": report["verdict"], "preview": {"path": args.preview.as_posix(), "sha256": _sha(preview_bytes)},
               "registry": _sha(registry_bytes), "markdown": _sha(markdown_bytes), "hifi": binding,
               "pages": {page: _sha(html.encode("utf-8")) for page, html in sorted(documents.items())},
               "renderer": {name: _sha((SCRIPTS / name).read_bytes()) for name in RENDERER_MODULES},
               "browser": report.get("browser"), "playwright": report.get("playwright"), "results": report["results"]}
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
    print(f"{receipt['verdict']} source-runtime acceptance; receipt {args.receipt}")
    return 0 if receipt["verdict"] in {"PASS", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
