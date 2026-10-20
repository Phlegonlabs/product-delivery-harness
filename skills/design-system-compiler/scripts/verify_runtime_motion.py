#!/usr/bin/env python3
"""Browser acceptance for ds-showcase/2 source-runtime motion in an exact preview.

Rendering emits an unverified candidate. This separate read-only check proves
playback on those exact bytes: it validates the pair, requires the preview to
equal a fresh render, drives every source-runtime row at every bound target in
fresh Chromium contexts and writes a new receipt bound to the preview, pair,
source documents, motion evidence, HiFi pages and renderer module hashes.
After playback it reruns every join and refuses the receipt on any change.
Reduced realms are held for a window derived from the observed normal
lifecycle; the receipt records it. Exit 0 only for PASS.
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
                    "runtime_acceptance_process.py", "animation_provenance.py", "surface_adapter.py",
                    "source_script_order.py")

PROBE = r"""
const [,, url, playwrightModule, plan, limit] = process.argv;
const {chromium} = require(require.resolve(playwrightModule, {paths: [process.cwd()]}));
const owned = row => console.log("ds-owned " + JSON.stringify(row));
owned({role: "node", pid: process.pid, started: Math.floor(performance.timeOrigin)});
// Each reduced realm is held for a window derived from the observed normal lifecycle of the same row and target.
const FLOOR = 3200, CEILING = 30000;
const reducedWindow = lifecycle => Math.max(FLOOR, Math.ceil(lifecycle + Math.max(1600, lifecycle / 3)));
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
    let window = null;
    for (const mode of ["normal", "system"]) {
      const context = await browser.newContext(mode === "system" ? {viewport: {width: 1280, height: 800}, reducedMotion: "reduce"}
        : {viewport: {width: 1280, height: 800}});
      try {
        const result = await (mode === "system" ? systemCase(context, row, target, window) : normalCase(context, row, target));
        if (mode === "normal") window = result.reducedWindowMs || null;
        results.push(result);
      } finally { await context.close().catch(() => {}); }
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
  const realm = async () => (await (await page.$(figure + " iframe")).contentFrame())
    .evaluate(() => [document.getAnimations().filter(item => item.playState === "running").length,
      JSON.parse(document.getElementById("ds-mount").textContent).generation]);
  const running = async () => (await realm())[0];
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
  // Keep one realm (one source generation) alive for the whole window: every phase and running count is sampled, none is assumed.
  const hold = async (wanted, wait) => {
    const started = Date.now(), end = started + wait, seen = [];
    let peak = 0, broken = false, generation = null, sameGeneration = true;
    while (Date.now() < end) {
      const value = await phase();
      if (seen[seen.length - 1] !== value) seen.push(value);
      const [count, mounted] = await realm();
      peak = Math.max(peak, count);
      if (generation === null) generation = mounted;
      else if (mounted !== generation) sameGeneration = false;
      if (value !== wanted) broken = true;
      await page.waitForTimeout(60);
    }
    const last = await phase();
    return {value: last, seen, peak, generation, sameGeneration, windowMs: wait, observedMs: Date.now() - started,
      held: !broken && sameGeneration && last === wanted, status: await page.$eval(figure + " .status", item => item.textContent)};
  };
  // Natively scroll the bound subject the runtime observes (the last node naming this target) into view, so the
  // product's own observer threshold decides entry; a tall plate centred as a whole can leave the subject below it.
  const reveal = async () => {
    const element = await page.$(figure + " iframe");
    const frame = element && await element.contentFrame();
    const box = frame && await frame.evaluate(name => {
      let subject = null;
      for (const node of document.querySelectorAll("[data-ds-motion-subject]"))
        if (node.getAttribute("data-ds-motion-subject").split(" ").indexOf(name) >= 0) subject = node;
      if (!subject) return null;
      let rect = subject.getBoundingClientRect();
      if (rect.top < 0 || rect.bottom > window.innerHeight) {
        window.scrollTo(0, Math.max(0, rect.top + window.scrollY - Math.max(0, (window.innerHeight - rect.height) / 2)));
        rect = subject.getBoundingClientRect();
      }
      return {top: rect.top, bottom: rect.bottom, height: rect.height};
    }, target);
    if (!box) { await page.$eval(figure, item => item.scrollIntoView({block: "center"})); return {subject: false}; }
    return Object.assign({subject: true}, await element.evaluate((item, box) => {
      const offset = () => item.getBoundingClientRect().top + item.clientTop;
      const room = Math.max(0, (window.innerHeight - Math.min(box.height, window.innerHeight)) / 2);
      window.scrollTo(window.scrollX, Math.max(0, offset() + window.scrollY + box.top - room));
      const frame = item.getBoundingClientRect(), top = offset() + box.top, bottom = offset() + box.bottom;
      const shown = Math.min(bottom, frame.bottom, window.innerHeight) - Math.max(top, frame.top, 0);
      return {top: Math.round(top), height: Math.round(box.height), ratio: box.height ? Math.round(Math.max(0, shown) / box.height * 1000) / 1000 : 0};
    }, box));
  };
  return {page, errors, requests, popups, figure, phase, press, running, until, hold, reveal};
}

async function systemCase(context, row, target, window) {
  // System reduced preference applies at first paint and wins over the gallery toggle.
  const result = {variant: row.variant, target, mode: "system", reducedWindowMs: window};
  // Without an observed normal lifecycle (or above the ceiling) no window can be derived: fail, never shorten.
  if (!window || window > CEILING) return Object.assign(result, {errors: [], requests: [], popups: [], pass: false,
    windowError: window ? "derived reduced window exceeds " + CEILING + " ms" : "no observed normal lifecycle for this row and target"});
  const {errors, requests, popups, figure, press, until, hold, reveal} = await open(context, row, target);
  await press(figure + ' button[data-ds-runtime-target="' + target + '"]');
  result.reveal = await reveal();
  result.first = await until(["reduced", "invalid"], 8000);
  if (result.first.value !== "reduced") return Object.assign(result, {errors, requests, popups, pass: false});
  result.window = await hold("reduced", window);
  await press("[data-ds-reduced-toggle]");
  result.afterToggle = await until(["reduced", "invalid"], 8000);
  result.toggleWindow = await hold("reduced", window);
  Object.assign(result, {errors, requests, popups});
  result.pass = result.first.value === "reduced" && result.window.held && result.window.peak === 0
    && /system preference/.test(result.window.status) && result.toggleWindow.held && result.toggleWindow.peak === 0
    && !errors.length && !requests.length && !popups.length;
  return result;
}

async function normalCase(context, row, target) {
  {
    const {page, errors, requests, popups, figure, phase, press, until, hold, reveal} = await open(context, row, target);
    const settle = async limit => {
      const end = Date.now() + limit, seen = [];
      let since = null;
      while (Date.now() < end) {
        const value = await phase();
        if (seen[seen.length - 1] !== value) seen.push(value);
        if (value === "invalid") return {value, seen, since: null};
        since = value === "settled" ? since || Date.now() : null;
        if (since && Date.now() - since >= 1500) return {value, seen, since};
        await page.waitForTimeout(40);
      }
      return {value: await phase(), seen, since: null};
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
    result.reveal = await reveal();
    const entered = Date.now();
    const first = await settle(20000);
    Object.assign(result, {first: first.value, firstSeen: first.seen, firstStatus: await page.$eval(figure + " .status", item => item.textContent)});
    if (first.value !== "settled") return Object.assign(result, {errors, requests, popups, pass: false});
    const pressed = Date.now();
    await press(figure + ' button[data-ds-runtime="replay"]');
    const replay = await settle(20000);
    Object.assign(result, {replay: replay.value, replaySeen: replay.seen});
    // Lifecycle: from viewport entry or a fresh replay realm to the start of the final settled phase, activation delay included.
    result.lifecycleMs = Math.max(first.since - entered, replay.since ? replay.since - pressed : 0);
    result.reducedWindowMs = reducedWindow(result.lifecycleMs);
    if (result.reducedWindowMs > CEILING) return Object.assign(result, {errors, requests, popups, pass: false,
      windowError: "derived reduced window exceeds " + CEILING + " ms"});
    await press(figure + ' button[data-ds-runtime="replay"]');
    result.playingBeforeStop = (await until(["playing"], 8000)).value;
    await press(figure + ' button[data-ds-runtime="stop"]');
    result.stop = (await until(["stopped"], 3000)).value;
    const stopped = await hold("stopped", 1200);
    Object.assign(result, {stopAfter: stopped.value, stopHeld: stopped.held, stopRunning: stopped.peak});
    await press("[data-ds-reduced-toggle]");
    result.reducedFirst = await until(["reduced", "invalid"], 8000);
    // The reduced realm stays mounted for the full window so delayed timers, callbacks and CSS states are observed.
    const reduced = await hold("reduced", result.reducedWindowMs);
    Object.assign(result, {reduced: reduced.value, reducedHeld: reduced.held, reducedSeen: reduced.seen, reducedRunning: reduced.peak,
      reducedStatus: reduced.status, reducedObservedMs: reduced.observedMs, reducedGeneration: reduced.generation,
      reducedSameGeneration: reduced.sameGeneration});
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


def _inputs(args: argparse.Namespace, registry: dict, documents: dict[str, str]) -> dict:
    """Current hashes of every input the validation reads; re-read after playback to refuse stale acceptance.

    Source bindings use raw SHA-256 except uiDesign, which keeps the canonical UI approval digest.
    Evidence covers every normal/reduced record in the current UI motion evidence table.
    """
    from check_design_system_pair import canonical_ui_approval_sha256, read_repo_file
    import showcase_runtime

    root = args.repo_root.resolve()
    sources, evidence = {}, {}
    for key, binding in sorted((registry.get("sourceBindings") or {}).items()):
        path = binding.get("path") if isinstance(binding, dict) else None
        payload = read_repo_file(root, path) if isinstance(path, str) else None
        if payload is None:
            sources[key] = None
        elif key == "uiDesign":
            sources[key] = canonical_ui_approval_sha256(payload.decode("utf-8"))
            for name, record in sorted(showcase_runtime.ui_motion_records(payload.decode("utf-8"))[1].items()):
                found = read_repo_file(root, record["path"])
                evidence[name] = {"path": record["path"], "sha256": _sha(found) if found is not None else None}
        else:
            sources[key] = _sha(payload)
    return {"preview": _sha(args.preview.read_bytes()), "registry": _sha(args.registry.read_bytes()),
            "markdown": _sha(args.markdown.read_bytes()), "sources": sources, "evidence": evidence,
            "pages": {page: _sha(html.encode("utf-8")) for page, html in sorted(documents.items())},
            "renderer": {name: _sha((SCRIPTS / name).read_bytes()) for name in RENDERER_MODULES}}


def _validated(args: argparse.Namespace) -> tuple[dict, list[dict], dict]:
    """Validate the pair, current sources and runtime joins from disk; return the HiFi binding, plan and input hashes."""
    from check_design_system_pair import compare, load_showcase_sources, read_repo_file
    from render_design_system_preview import render_view
    import showcase_runtime

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
    bound = _inputs(args, registry, documents)
    if bound["preview"] != _sha(preview_bytes) or bound["registry"] != _sha(registry_bytes) or bound["markdown"] != _sha(markdown_bytes):
        raise ValueError("an input changed while the preview was being checked")
    return binding, acceptance_plan(registry, runtime), bound


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("--repo-root", "--registry", "--markdown", "--preview", "--receipt"):
        parser.add_argument(name, type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        binding, plan, bound = _validated(args)
        report = run_acceptance(args.preview, plan) if plan else {"results": [], "verdict": "NOT_APPLICABLE"}
        # Rerun every pair, source and runtime join on fresh bytes; newly stale input refuses the receipt.
        try:
            after = _validated(args)
        except (OSError, UnicodeError, ValueError, KeyError) as error:
            raise ValueError(f"an input changed during browser acceptance; the observation is stale: {error}") from error
        if after != (binding, plan, bound):
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
               "sources": bound["sources"], "evidence": bound["evidence"],
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
