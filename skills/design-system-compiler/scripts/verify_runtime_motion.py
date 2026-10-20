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
import sys

from runtime_acceptance_process import AcceptanceRunError, run_probe

SCRIPTS = Path(__file__).resolve().parent
RENDERER_MODULES = ("render_design_system_preview.py", "check_design_system_pair.py", "design_system_showcase.py",
                    "showcase_runtime.py", "design_system_gallery.py", "design_system_gallery_assets.py",
                    "design_system_gallery_runtime.py", "design_system_runtime_assets.py", "verify_runtime_motion.py",
                    "runtime_acceptance_process.py", "animation_provenance.py", "surface_adapter.py")

PROBE = r"""
const [,, url, playwrightModule, plan, limit] = process.argv;
const {chromium} = require(require.resolve(playwrightModule, {paths: [process.cwd()]}));
const owned = row => console.log("ds-owned " + JSON.stringify(row));
owned({role: "node", pid: process.pid, started: Math.floor(performance.timeOrigin)});
const WINDOW = 3200;
let browser = null;
// Backstop if the probe outlives its supervisor (at most 30 minutes); the owned Job/process group stays the guarantee.
setTimeout(() => { console.error("acceptance backstop reached"); process.exit(124); },
  Math.min(Number(limit) * 1000 + 10000, 1800000)).unref();
(async () => {
  browser = await chromium.launch();
  try {
    const cdp = await browser.newBrowserCDPSession();
    const info = await cdp.send("SystemInfo.getProcessInfo");
    for (const item of info.processInfo || []) owned({role: "chromium-" + item.type, pid: item.id, started: Date.now(), command: "chromium " + item.type});
    await cdp.detach();
  } catch (_) { /* the owned tree still contains every Chromium process */ }
  const startedAt = new Date().toISOString();
  const results = [];
  for (const row of JSON.parse(plan)) for (const target of row.targets) {
    for (const mode of ["normal", "system"]) {
      const context = await browser.newContext(mode === "system" ? {viewport: {width: 1280, height: 800}, reducedMotion: "reduce"}
        : {viewport: {width: 1280, height: 800}});
      try { results.push(await (mode === "system" ? systemCase : normalCase)(context, row, target)); }
      finally { await context.close().catch(() => {}); }
    }
  }
  console.log(JSON.stringify({browser: browser.version(), startedAt, finishedAt: new Date().toISOString(),
    node: process.version, platform: process.platform + "-" + process.arch, results}));
})().catch(error => { console.error(error); process.exitCode = 1; })
  .finally(() => browser ? Promise.race([browser.close(), new Promise(done => setTimeout(done, 10000))]) : null);

async function open(context, row, target) {
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
  const running = async () => (await (await page.$(figure + " iframe")).contentFrame())
    .evaluate(() => document.getAnimations().filter(item => item.playState === "running").length);
  const until = async (wanted, wait) => {
    const end = Date.now() + wait, seen = [];
    while (Date.now() < end) {
      const value = await phase();
      if (seen[seen.length - 1] !== value) seen.push(value);
      if (wanted.includes(value)) return {value, seen};
      await page.waitForTimeout(40);
    }
    return {value: await phase(), seen};
  };
  // Keep one realm alive for the whole window: every phase and running count is sampled, none is assumed.
  const hold = async (wanted, wait) => {
    const end = Date.now() + wait, seen = [];
    let peak = 0, broken = false;
    while (Date.now() < end) {
      const value = await phase();
      if (seen[seen.length - 1] !== value) seen.push(value);
      peak = Math.max(peak, await running());
      if (value !== wanted) broken = true;
      await page.waitForTimeout(60);
    }
    const last = await phase();
    return {value: last, seen, peak, held: !broken && last === wanted, status: await page.$eval(figure + " .status", item => item.textContent)};
  };
  return {page, errors, requests, popups, figure, phase, press, running, until, hold};
}

async function systemCase(context, row, target) {
  // System reduced preference applies at first paint and wins over the gallery toggle.
  const {page, errors, requests, popups, figure, press, until, hold} = await open(context, row, target);
  await press(figure + ' button[data-ds-runtime-target="' + target + '"]');
  await page.$eval(figure, item => item.scrollIntoView({block: "center"}));
  const result = {variant: row.variant, target, mode: "system"};
  result.first = await until(["reduced", "invalid"], 8000);
  if (result.first.value !== "reduced") return Object.assign(result, {errors, requests, popups, pass: false});
  result.window = await hold("reduced", WINDOW);
  await press("[data-ds-reduced-toggle]");
  result.afterToggle = await until(["reduced", "invalid"], 8000);
  result.toggleWindow = await hold("reduced", WINDOW);
  Object.assign(result, {errors, requests, popups});
  result.pass = result.first.value === "reduced" && result.window.held && result.window.peak === 0
    && /system preference/.test(result.window.status) && result.toggleWindow.held && result.toggleWindow.peak === 0
    && !errors.length && !requests.length && !popups.length;
  return result;
}

async function normalCase(context, row, target) {
  {
    const {page, errors, requests, popups, figure, phase, press, running, until, hold} = await open(context, row, target);
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
    const result = {variant: row.variant, target, mode: "normal"};
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
    if (first.value !== "settled") return Object.assign(result, {errors, requests, popups, pass: false});
    await press(figure + ' button[data-ds-runtime="replay"]');
    const replay = await settle(20000);
    Object.assign(result, {replay: replay.value, replaySeen: replay.seen});
    await press(figure + ' button[data-ds-runtime="replay"]');
    result.playingBeforeStop = (await until(["playing"], 8000)).value;
    await press(figure + ' button[data-ds-runtime="stop"]');
    result.stop = (await until(["stopped"], 3000)).value;
    const stopped = await hold("stopped", 1200);
    Object.assign(result, {stopAfter: stopped.value, stopHeld: stopped.held, stopRunning: stopped.peak});
    await press("[data-ds-reduced-toggle]");
    result.reducedFirst = await until(["reduced", "invalid"], 8000);
    // The reduced realm stays mounted for the full window so delayed timers, callbacks and CSS states are observed.
    const reduced = await hold("reduced", WINDOW);
    Object.assign(result, {reduced: reduced.value, reducedHeld: reduced.held, reducedSeen: reduced.seen, reducedRunning: reduced.peak,
      reducedStatus: reduced.status});
    await press("[data-ds-reduced-toggle]");
    Object.assign(result, {errors, requests, popups});
    result.pass = (row.activation !== "viewport" || !offscreen || result.beforeView === "pending")
      && result.first === "settled" && result.replay === "settled" && result.playingBeforeStop === "playing"
      && result.stop === "stopped" && result.stopHeld && result.stopRunning === 0
      && result.reducedFirst.value === "reduced" && result.reducedHeld && result.reducedRunning === 0
      && !errors.length && !requests.length && !popups.length;
    return result;
  }
}
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


def run_acceptance(preview: Path, plan: list[dict], *, timeout: int | None = None, probe: str = PROBE) -> dict:
    """Drive the exact preview file in Chromium as an owned process tree; return the raw observation report."""
    module = os.environ.get("PLAYWRIGHT_MODULE") or "playwright"
    cases = sum(len(row["targets"]) for row in plan)
    limit = timeout or 90 + 75 * cases
    stdout, processes = run_probe(probe, [preview.resolve().as_uri(), module, json.dumps(plan), str(limit)],
                                  timeout=limit, purpose="ds-runtime-acceptance " + preview.name)
    report = json.loads(stdout.strip().splitlines()[-1])
    package = Path(module) / "package.json"
    report["playwright"] = json.loads(package.read_text(encoding="utf-8")).get("version") if package.is_file() else "unknown"
    report["processes"] = processes
    report["verdict"] = "PASS" if report["results"] and all(item.get("pass") for item in report["results"]) else "FAIL"
    return report


def _inputs(args: argparse.Namespace, documents: dict[str, str]) -> dict:
    """Current hashes of every input the receipt binds; re-read after playback to refuse stale acceptance."""
    return {"preview": _sha(args.preview.read_bytes()), "registry": _sha(args.registry.read_bytes()),
            "markdown": _sha(args.markdown.read_bytes()),
            "pages": {page: _sha(html.encode("utf-8")) for page, html in sorted(documents.items())},
            "renderer": {name: _sha((SCRIPTS / name).read_bytes()) for name in RENDERER_MODULES}}


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
        bound = _inputs(args, documents)
        if bound["preview"] != _sha(preview_bytes) or bound["registry"] != _sha(registry_bytes) or bound["markdown"] != _sha(markdown_bytes):
            raise ValueError("an input changed while the preview was being checked")
        report = run_acceptance(args.preview, plan) if plan else {"results": [], "verdict": "NOT_APPLICABLE"}
        after = _inputs(args, load_showcase_sources(registry, root)[0])
        if after != bound:
            raise ValueError("an input changed during browser acceptance; the observation is stale")
    except AcceptanceRunError as error:
        print(f"FAIL {error}", file=sys.stderr)
        print("owned processes: " + json.dumps(error.processes), file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError, KeyError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    receipt = {"schema": "ds-runtime-acceptance/1", "createdAt": datetime.now(timezone.utc).isoformat(),
               "verdict": report["verdict"], "preview": {"path": args.preview.as_posix(), "sha256": bound["preview"]},
               "registry": bound["registry"], "markdown": bound["markdown"], "hifi": binding, "pages": bound["pages"],
               "renderer": bound["renderer"], "browser": report.get("browser"), "playwright": report.get("playwright"),
               "observation": {key: report.get(key) for key in ("startedAt", "finishedAt", "node", "platform")},
               "environment": {"python": sys.version.split()[0], "os": sys.platform}, "processes": report.get("processes", []),
               "results": report["results"]}
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
    print(f"{receipt['verdict']} source-runtime acceptance; receipt {args.receipt}")
    return 0 if receipt["verdict"] in {"PASS", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
