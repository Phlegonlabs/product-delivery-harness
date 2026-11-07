#!/usr/bin/env python3
"""Capture a HiFi surface x state x target matrix and its product interactions in one offline browser session.

Each page loads once. Targets and states change through the real reviewer shell
controls, never by reloading. The matrix pass clicks no product control; the
interaction pass then clicks and keyboard-activates every manifest interaction
at every source target. Output: one PNG per case, ``ui-output.json``
(``ui-output/3``: matrix, ``interactions`` rows, ``navigation`` events and the
``reviewer`` object) and ``matrix-capture.json`` (per-case fingerprints,
geometry, carried rows, axis runs, interaction records and reviewer
measurements).

The browser is Node Playwright, the repo's pinned test dependency
(``PLAYWRIGHT_MODULE`` or ``node_modules/playwright`` under ``--repo-root``).
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import importlib.util
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from check_ui_design_contract import HIFI_SURFACE_RECEIPT_METHOD, _offline_transcript_findings, parse_ui_contract_view
from hifi_reviewer import ReviewerParser, _is_na_state, _target_widths, reviewer_contract, reviewer_evidence_findings
from review_evidence import HIFI_MANIFEST_RE, build_receipt, safe_path
from ui_design_v3 import intermediate_width_findings

SIDECAR_SCHEMA = "hifi-matrix-capture/1"
OUTPUT_NAME = "ui-output.json"
SIDECAR_NAME = "matrix-capture.json"
INTERMEDIATE_DIR = "intermediate"
CHECK = "hifi-browser"
AXES = ("dark", "reduced-motion", "forced-colors", "zoom-200")
TRIGGERS = ("click", "keyboard")
INTERACT_KINDS = ("navigate", "state")
DRIVER_BASE = "https://hifi.invalid/pkg/"
SETTLE_CAP_MS = 2000
SETTLE_MARGIN_MS = 50
CASE_TIMEOUT_S = 30
MAX_RESTARTS = 3
OVERFLOW_TOLERANCE_PX = 1
WIDTH_TOLERANCE_PX = 1
SANDBOX = {"network": "disabled", "topNavigation": "allowlisted-local-pages",
           "popups": "blocked", "forms": "blocked"}
TRANSCRIPT_KINDS = ("console", "network", "navigation", "popups", "forms")


class UsageError(Exception):
    """Bad arguments or an unusable package; nothing was observed."""


class DriverError(Exception):
    def __init__(self, message, events=None):
        super().__init__(message)
        self.events = events or {}


class DriverTimeout(DriverError):
    """The browser driver gave no reply before the deadline."""


# --- Node Playwright driver -------------------------------------------------
# One JSON request per stdin line, one JSON reply per stdout line. Every reply
# carries the console/network/navigation/popup/form and product-focus events
# seen since the last reply. CDP Log and Runtime are enabled before the first
# load and never cleared.
DRIVER_JS = r"""
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const readline = require('readline');
const moduleDir = process.argv[2];
const { chromium } = require(moduleDir);
const BASE = 'https://hifi.invalid/pkg/';
const STYLE_PROPS = ['display', 'position', 'color', 'background-color', 'background-image', 'font-family',
  'font-size', 'font-weight', 'font-style', 'line-height', 'letter-spacing', 'text-align', 'text-transform',
  'text-decoration-line', 'border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width',
  'border-top-color', 'border-top-style', 'border-radius', 'box-shadow', 'opacity', 'transform', 'overflow-x',
  'overflow-y', 'z-index', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'margin-top',
  'margin-right', 'margin-bottom', 'margin-left', 'gap', 'grid-template-columns', 'flex-direction',
  'visibility', 'cursor', 'mask-image', 'border-image', 'fill', 'stroke', 'stroke-width'];
const sha = text => crypto.createHash('sha256').update(text).digest('hex');
const emptyEvents = () => ({ console: [], network: [], navigation: [], popups: [], forms: [], focus: [] });
let events = emptyEvents();
let browser, context, page, pages = {};
let currentPage = null;
let baseColorScheme = 'light';   // the run's context theme; an axis reset returns to it, not to plain light
let opening = null;   // the page name the driver is loading itself: only that first document request is not a navigation
const drain = () => { const out = events; events = emptyEvents(); return out; };
const quote = value => '"' + String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
const level = type => (type === 'error' || type === 'assert') ? 'error' : (type === 'warning' ? 'warning' : 'info');
const packageVersion = () => {
  for (const dir of [moduleDir, path.dirname(moduleDir)]) {
    try { return require(path.join(dir, 'package.json')).version; } catch (_) {}
  }
  return 'unknown';
};

const SET_CANVAS_WIDTH = px => {
  const canvas = document.querySelector('[data-hifi-canvas]');
  if (px) canvas.style.setProperty('width', px + 'px'); else canvas.style.removeProperty('width');
};

const SETTLE = async ({ cap, margin }) => {
  await document.fonts.ready;
  const canvas = document.querySelector('[data-hifi-canvas]');
  const live = () => document.getAnimations().filter(a => {
    const target = a.effect && a.effect.target;
    return target && canvas.contains(target) && (a.playState === 'running' || a.playState === 'pending');
  });
  const finite = a => Number.isFinite(a.effect.getComputedTiming().endTime);
  let need = 0;
  for (const a of live()) {
    if (finite(a)) need = Math.max(need, (a.effect.getComputedTiming().endTime - (a.currentTime || 0)) / (a.playbackRate || 1));
  }
  need = Math.ceil(need);
  const waited = need > 0 ? Math.min(cap, need + margin) : 0;
  if (waited > 0) await new Promise(resolve => setTimeout(resolve, waited));
  let finished = 0, paused = 0;
  for (const a of live()) {
    try {
      if (finite(a)) { a.finish(); finished++; } else { a.pause(); a.currentTime = 0; paused++; }
    } catch (_) {}
  }
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return { waitedMs: waited, finished, paused, capped: need > 0 && need + margin > cap };
};

const PROBE = ({ surfaceId, state, limit, reportLimit, props }) => {
  const canvas = document.querySelector('[data-hifi-canvas]');
  const surface = canvas && Array.from(canvas.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surfaceId);
  if (!surface) return null;
  const round = value => Math.round(value * 100) / 100;
  const visible = el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const describe = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
    + (el.classList.length ? '.' + Array.from(el.classList).slice(0, 3).join('.') : '');
  const origin = canvas.getBoundingClientRect();
  const all = [surface].concat(Array.from(surface.querySelectorAll('*')))
    .filter(el => !['SCRIPT', 'STYLE', 'TEMPLATE'].includes(el.tagName) && visible(el));
  const boxes = all.slice(0, limit).map(el => {
    const r = el.getBoundingClientRect();
    return { el, x: r.left - origin.left, y: r.top - origin.top, w: r.width, h: r.height };
  });
  let overlapCount = 0;
  const overlaps = [];
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
      const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
      if (ox > 1 && oy > 1) {
        overlapCount++;
        if (overlaps.length < reportLimit) overlaps.push({ a: describe(a.el), b: describe(b.el), px: Math.round(ox), py: Math.round(oy) });
      }
    }
  }
  const box = surface.getBoundingClientRect();
  const geometry = {
    canvasWidth: round(origin.width), canvasHeight: round(origin.height),
    surface: { x: round(box.left - origin.left), y: round(box.top - origin.top), width: round(box.width), height: round(box.height) },
    scrollWidth: surface.scrollWidth, clientWidth: surface.clientWidth,
    scrollHeight: surface.scrollHeight, clientHeight: surface.clientHeight,
    overflowX: Math.max(surface.scrollWidth - surface.clientWidth, canvas.scrollWidth - canvas.clientWidth),
    elementCount: all.length, scanned: boxes.length, overlapCount, overlaps,
    stateViews: Array.from(surface.querySelectorAll('[data-hifi-state-view]'))
      .filter(v => v.dataset.hifiStateView === state && !v.hidden && visible(v)).length,
  };
  const shown = new Set(all);
  const attrs = (el, names) => names.map(n => n + '=' + (el.getAttribute(n) || '')).join(',');
  const imageInput = el => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'img') return attrs(el, ['src', 'srcset', 'sizes']) + ',currentSrc=' + el.currentSrc;
    if (tag === 'video') return attrs(el, ['src', 'poster']) + ',currentSrc=' + el.currentSrc;
    if (tag === 'source') return attrs(el, ['src', 'srcset', 'sizes', 'media', 'type']);
    if (tag === 'svg') return el.outerHTML;
    if (tag === 'use') {
      const href = el.getAttribute('href') || el.getAttribute('xlink:href') || '';
      const target = href.startsWith('#') ? document.getElementById(href.slice(1)) : null;
      return 'use=' + href + (target ? target.outerHTML : '');
    }
    return '';
  };
  const inputs = Array.from(surface.querySelectorAll('img, source, video, svg, use'))
    .filter(el => shown.has(el) || shown.has(el.parentElement)).map(imageInput).join('\n');
  const rects = boxes.map(b => [describe(b.el), round(b.x), round(b.y), round(b.w), round(b.h)].join(',')).join('\n');
  const styleLine = el => {
    const cs = getComputedStyle(el);
    return describe(el) + '|' + props.map(p => cs.getPropertyValue(p)).join(';');
  };
  const styles = boxes.map(b => styleLine(b.el)).join('\n') + '\n' + surface.innerText;
  // The screenshot covers the whole canvas, so its own paint and every visible
  // element outside the product surface join the fingerprint too.
  const outside = Array.from(canvas.querySelectorAll('*'))
    .filter(el => el !== surface && !surface.contains(el) && !['SCRIPT', 'STYLE', 'TEMPLATE'].includes(el.tagName) && visible(el));
  const paint = [canvas].concat(outside.slice(0, limit)).map(styleLine).join('\n');
  return { geometry, rects, styles: styles + '\n#canvas\n' + paint, inputs,
           incomplete: all.length > limit || outside.length > limit };
};

async function start(request) {
  for (const [name, file] of Object.entries(request.files)) pages[name] = fs.readFileSync(file);
  baseColorScheme = request.colorScheme === 'dark' ? 'dark' : 'light';
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({
    viewport: request.viewport, serviceWorkers: 'block', acceptDownloads: false,
    colorScheme: baseColorScheme, reducedMotion: 'no-preference', forcedColors: 'none', deviceScaleFactor: 1,
  });
  await context.route('**/*', route => {
    const req = route.request();
    const url = new URL(req.url());
    const name = url.origin + '/' === 'https://hifi.invalid/' && url.pathname.startsWith('/pkg/')
      ? decodeURIComponent(url.pathname.slice(5)) : null;
    if (name !== null && req.resourceType() === 'document' && req.method() === 'GET' && !url.search
        && Object.prototype.hasOwnProperty.call(pages, name)) {
      if (opening === name) opening = null;
      else events.navigation.push({ url: req.url(), method: req.method(), resourceType: 'document', allowlisted: true });
      return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: pages[name] });
    }
    const row = { url: req.url(), method: req.method(), resourceType: req.resourceType() };
    if (req.resourceType() === 'document') events.navigation.push(row); else events.network.push(row);
    return route.abort('blockedbyclient');
  });
  await context.addInitScript(() => {
    const record = form => window.__pdhForm && window.__pdhForm({ action: String(form.action), method: String(form.method) });
    addEventListener('submit', event => { event.preventDefault(); record(event.target); }, true);
    HTMLFormElement.prototype.submit = function () { record(this); };
    addEventListener('focusin', event => {
      const el = event.target;
      const id = el && el.dataset && (el.dataset.navigationId || el.dataset.controlId);
      if (id) window.__pdhFocus({ control: id });
    }, true);
  });
  page = await context.newPage();
  await page.exposeFunction('__pdhForm', info => { events.forms.push(info); });
  await page.exposeFunction('__pdhFocus', info => { events.focus.push(info); });
  context.on('page', popup => { if (popup !== page) { events.popups.push({ url: popup.url() }); popup.close().catch(() => {}); } });
  page.on('dialog', dialog => {
    events.console.push({ source: 'dialog', level: 'error', message: 'dialog ' + dialog.type() + ': ' + dialog.message() });
    dialog.dismiss().catch(() => {});
  });
  const cdp = await context.newCDPSession(page);
  await cdp.send('Log.enable');
  await cdp.send('Runtime.enable');
  cdp.on('Log.entryAdded', ({ entry }) => events.console.push({ source: entry.source, level: entry.level, message: entry.text }));
  cdp.on('Runtime.consoleAPICalled', p => events.console.push({
    source: 'console-api', level: level(p.type),
    message: p.args.map(a => a.value !== undefined ? String(a.value) : (a.description || a.type)).join(' '),
  }));
  cdp.on('Runtime.exceptionThrown', p => events.console.push({
    source: 'javascript', level: 'exception',
    message: (p.exceptionDetails.exception && p.exceptionDetails.exception.description) || p.exceptionDetails.text,
  }));
  return { environment: { playwright: packageVersion(), chromium: browser.version(), node: process.version } };
}

async function openPage(name, timeoutMs) {
  page.setDefaultTimeout(timeoutMs);
  opening = name;
  let response;
  try { response = await page.goto(BASE + encodeURI(name), { waitUntil: 'load' }); } finally { opening = null; }
  if (!response || response.status() !== 200) throw new Error('page did not load: ' + name);
  await page.locator('[data-hifi-reviewer-shell]').first().waitFor({ state: 'attached' });
  await page.locator('[data-hifi-canvas]').first().waitFor({ state: 'attached' });
  await page.evaluate(() => document.fonts.ready.then(() => true));
  currentPage = name;
}

async function open(request) {
  await openPage(request.page, request.timeoutMs);
  return {
    targets: await page.locator('[data-hifi-target-control]').evaluateAll(list => list.map(n => n.dataset.hifiTargetControl)),
    states: await page.locator('[data-hifi-state-control]').evaluateAll(list => list.map(n => n.dataset.hifiStateSurface + ' ' + n.dataset.hifiStateControl)),
  };
}

// One interaction attempt: reset page/target/source state through the reviewer
// shell, then activate the declared product control by click or keyboard. The
// destination surface/state must apply; the control, and only the control, must
// take product focus during the attempt.
async function interact(request) {
  const problems = [];
  const timeout = request.timeoutMs;
  if (currentPage !== request.page) {
    try { await openPage(request.page, timeout); } catch (_) { problems.push('page did not open: ' + request.page); }
  }
  if (!problems.length) {
    const target = page.locator('[data-hifi-target-control=' + quote(request.target) + ']');
    if (await target.count() !== 1) problems.push('target control missing: ' + request.target);
    else {
      if (await target.getAttribute('aria-pressed') !== 'true') await target.click({ timeout });
      const current = await page.evaluate(() => document.querySelector('[data-hifi-canvas]').dataset.hifiTarget);
      if (current !== request.target) problems.push('target did not apply: ' + current);
    }
    const control = page.locator('[data-hifi-state-control=' + quote(request.state) + '][data-hifi-state-surface=' + quote(request.surface) + ']');
    if (await control.count() !== 1) {
      problems.push('state control missing: ' + request.surface + ' ' + request.state);
    } else {
      // Always click the visible shell control: it also re-syncs a shell the product DOM has drifted from.
      if (await control.isVisible()) await control.click({ timeout });
      else await page.evaluate(hash => { location.hash = hash; },
        '#hifi-state=' + encodeURIComponent(request.surface) + '/' + encodeURIComponent(request.state));
      try {
        await page.waitForFunction(([surface, state]) => {
          const el = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surface);
          return Boolean(el) && !el.hidden && el.dataset.hifiState === state;
        }, [request.surface, request.state], { timeout });
      } catch (_) {
        problems.push('state did not apply: ' + request.surface + ' ' + request.state);
      }
    }
  }
  let visible = null, focusCorrect = null, arrivedTo = null;
  if (!problems.length) {
    const surface = '[data-ui-surface=' + quote(request.surface) + ']';
    const product = page.locator(surface + ' [data-navigation-id=' + quote(request.control) + ']:visible,'
      + surface + ' [data-control-id=' + quote(request.control) + ']:visible');
    if (await product.count() !== 1) problems.push('product control is missing or not unique: ' + request.control);
    else {
      const handle = product.first();
      visible = await handle.isVisible();
      let pressedFocused = null;
      if (request.trigger === 'keyboard') {
        await handle.focus({ timeout });
        pressedFocused = await handle.evaluate(el => el === document.activeElement);
        const tag = await handle.evaluate(el => el.tagName.toLowerCase());
        await page.keyboard.press(tag === 'a' || tag === 'area' ? 'Enter' : ' ');
      } else {
        await handle.click({ timeout });
      }
      try {
        await page.waitForFunction(([surface, state]) => {
          const el = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surface);
          return Boolean(el) && !el.hidden && el.dataset.hifiState === state;
        }, [request.destination.surface, request.destination.state], { timeout });
      } catch (_) {
        problems.push('destination surface/state did not apply: ' + request.destination.surface + ' ' + request.destination.state);
      }
      const url = page.url();
      arrivedTo = url.startsWith(BASE) ? decodeURIComponent(new URL(url).pathname.slice('/pkg/'.length)) : null;
      if (arrivedTo && arrivedTo !== currentPage) currentPage = arrivedTo;
      // Both triggers must land product focus on the control alone; keyboard also had to press from it.
      focusCorrect = events.focus.length === 1 && events.focus[0].control === request.control
        && (request.trigger !== 'keyboard' || Boolean(pressedFocused));
    }
  }
  return { problems, visible, focusCorrect, arrivedTo };
}

async function runCase(request) {
  const problems = [];
  const timeout = request.timeoutMs;
  page.setDefaultTimeout(timeout);
  const target = page.locator('[data-hifi-target-control=' + quote(request.target) + ']');
  if (await target.count() !== 1) {
    problems.push('target control missing: ' + request.target);
  } else {
    if (await target.getAttribute('aria-pressed') !== 'true') await target.click({ timeout });
    const current = await page.evaluate(() => document.querySelector('[data-hifi-canvas]').dataset.hifiTarget);
    if (current !== request.target) problems.push('target did not apply: ' + current);
  }
  const control = page.locator('[data-hifi-state-control=' + quote(request.state) + '][data-hifi-state-surface=' + quote(request.surface) + ']');
  if (await control.count() !== 1) {
    problems.push('state control missing: ' + request.surface + ' ' + request.state);
  } else {
    if (await control.isVisible()) {
      if (await control.getAttribute('aria-pressed') !== 'true') await control.click({ timeout });
    } else {
      await page.evaluate(hash => { location.hash = hash; },
        '#hifi-state=' + encodeURIComponent(request.surface) + '/' + encodeURIComponent(request.state));
    }
    try {
      await page.waitForFunction(([surface, state]) => {
        const el = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surface);
        return Boolean(el) && !el.hidden && el.dataset.hifiState === state;
      }, [request.surface, request.state], { timeout });
    } catch (_) {
      problems.push('state did not apply: ' + request.surface + ' ' + request.state);
    }
  }
  if (problems.length) return { problems, settle: null, probe: null };
  await page.evaluate(px => {
    const canvas = document.querySelector('[data-hifi-canvas]');
    if (px) canvas.style.setProperty('width', px + 'px'); else canvas.style.removeProperty('width');
  }, request.widthPx || null);
  const settle = await page.evaluate(SETTLE, { cap: request.settleCapMs, margin: request.marginMs });
  const probe = await page.evaluate(PROBE, {
    surfaceId: request.surface, state: request.state, limit: 400, reportLimit: 10, props: STYLE_PROPS,
  });
  if (!probe) return { problems: ['product surface not found: ' + request.surface], settle, probe: null };
  return {
    problems, settle,
    probe: {
      geometry: probe.geometry, rectsSha256: sha(probe.rects), styleSha256: sha(probe.styles),
      inputsSha256: sha(probe.inputs), incomplete: probe.incomplete,
    },
  };
}

async function shot(request) {
  await page.evaluate(() => { const el = document.activeElement; if (el && el.blur) el.blur(); });
  await page.locator('[data-hifi-canvas]').screenshot({ path: request.path, animations: 'disabled', caret: 'hide', timeout: request.timeoutMs });
  return {};
}

async function axis(request) {
  const name = request.name;
  await page.emulateMedia({
    colorScheme: (name === 'dark' || baseColorScheme === 'dark') ? 'dark' : 'light',
    reducedMotion: name === 'reduced-motion' ? 'reduce' : 'no-preference',
    forcedColors: name === 'forced-colors' ? 'active' : 'none',
  });
  await page.evaluate(zoom => {
    for (const surface of document.querySelectorAll('[data-ui-surface]')) {
      if (zoom) surface.style.setProperty('zoom', '2'); else surface.style.removeProperty('zoom');
    }
  }, name === 'zoom-200');
  return {};
}

// The reviewer pass, once per page after the interaction pass: one fresh open
// (the reviewer's stored selections are cleared first), the entry observations,
// the page-bound specimen source reads at the default target, the contract's
// viewport rows, and the entry-side specimen display reads. Only reviewer shell
// controls are clicked; no product control is touched.
async function reviewer(request) {
  const timeout = request.timeoutMs;
  const press = async (attribute, value) => {
    const control = page.locator('[' + attribute + '=' + quote(value) + ']');
    if (await control.count() !== 1) throw new Error('reviewer control missing: ' + value);
    if (await control.getAttribute('aria-pressed') !== 'true') await control.click({ timeout });
  };
  const selectSurface = async (surface, state) => {
    const control = page.locator('[data-hifi-state-control=' + quote(state) + '][data-hifi-state-surface=' + quote(surface) + ']');
    if (await control.count() !== 1) return;
    if (await control.isVisible()) await press('data-hifi-state-control', state);
    else {
      await page.evaluate(hash => { location.hash = hash; },
        '#hifi-state=' + encodeURIComponent(surface) + '/' + encodeURIComponent(state));
      await page.waitForFunction(surface => {
        const el = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surface);
        return Boolean(el) && !el.hidden;
      }, surface, { timeout }).catch(() => {});
    }
  };
  const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.evaluate(() => {
    for (const key of Object.keys(sessionStorage)) if (key.startsWith('hifi-reviewer:')) sessionStorage.removeItem(key);
  });
  await openPage(request.page, timeout);
  const result = {};
  if (request.entry) {
    result.entry = await page.evaluate(() => {
      const collect = selector => {
        const found = [];
        const walk = root => {
          if (!root) return;
          let all;
          try { found.push(...root.querySelectorAll(selector)); all = root.querySelectorAll('*'); } catch (_) { return; }
          for (const el of all) if (el.shadowRoot) walk(el.shadowRoot);
        };
        walk(document);
        return found;
      };
      const visible = Array.from(document.querySelectorAll('[data-ui-surface]'))
        .filter(el => !el.hidden && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0)
        .map(el => el.dataset.uiSurface);
      const defaultSurface = (document.body.dataset || {}).hifiDefaultSurface || null;
      return { defaultSurface, defaultVisible: visible.includes(defaultSurface),
        overviewInitiallyHidden: collect('[data-hifi-panel]').every(panel => panel.hidden) };
    });
  }
  if (request.sources && request.sources.length) {
    result.sources = await page.evaluate(specs => {
      const host = document.querySelector('[data-hifi-canvas]') || document.body;
      const identity = spec => ({ kind: spec.kind, name: spec.name, sourcePage: spec.sourcePage, source: spec.source,
        property: spec.property, variant: spec.variant, state: spec.state, element: spec.element,
        sharedGroup: spec.sharedGroup || null });
      return specs.map(spec => {
        const row = { ...identity(spec), sourceValue: null, sourceComputedValue: null };
        try {
          if (spec.kind === 'token') {
            row.sourceValue = getComputedStyle(document.documentElement).getPropertyValue(spec.property).trim() || null;
            if (spec.previewProperty && row.sourceValue) {
              const probe = document.createElement(spec.element || 'span');
              probe.style.setProperty(spec.previewProperty, 'var(' + spec.property + ')');
              host.appendChild(probe);
              row.sourceComputedValue = getComputedStyle(probe).getPropertyValue(spec.previewProperty).trim() || null;
              probe.remove();
            }
          } else {
            const attr = (el, name, fallback) => el.getAttribute(name) || el.getAttribute(fallback) || 'default';
            const candidates = Array.from(host.querySelectorAll(spec.source)).filter(el =>
              attr(el, 'data-specimen-variant', 'data-variant') === spec.variant
              && attr(el, 'data-specimen-state', 'data-state') === spec.state);
            const el = candidates.find(item => { const view = item.closest('[data-hifi-state-view]'); return !view || !view.hidden; })
              || candidates[0];
            if (el) row.sourceValue = getComputedStyle(el).getPropertyValue(spec.property).trim() || null;
          }
        } catch (_) {}
        return row;
      });
    }, request.sources);
  }
  if (request.viewport && request.viewport.length) {
    result.viewport = [];
    for (const row of request.viewport) {
      if (row.state) await selectSurface(row.surface, row.state);
      await press('data-hifi-target-control', row.target);
      await page.waitForFunction(t => {
        const el = document.querySelector('[data-hifi-canvas]');
        return Boolean(el) && el.dataset.hifiTarget === t;
      }, row.target, { timeout });
      await settle();
      result.viewport.push(await page.evaluate(surface => {
        const el = document.querySelector('[data-hifi-canvas]');
        const mediaApplied = () => {
          let applied = false;
          const scan = sheet => {
            try {
              for (const rule of sheet.cssRules || []) {
                if (rule.media && /\b(?:width|height|inline-size|block-size)\b|device-(?:width|height)|orientation|aspect-ratio|resolution/i.test(rule.media.mediaText || '')
                    && matchMedia(rule.media.mediaText).matches) applied = true;
                if (rule.styleSheet) scan(rule.styleSheet);
              }
            } catch (_) {}
          };
          for (const sheet of document.styleSheets) scan(sheet);
          return applied;
        };
        return { surface, target: el.dataset.hifiTarget,
          measuredProductWidth: Math.round(el.getBoundingClientRect().width * 100) / 100,
          containerQueryApplied: getComputedStyle(el).containerType === 'inline-size',
          hostMediaQueryApplied: mediaApplied(),
          visibleSurfaces: Array.from(document.querySelectorAll('[data-ui-surface]'))
            .filter(item => !item.hidden && item.getBoundingClientRect().width > 0 && item.getBoundingClientRect().height > 0)
            .map(item => item.dataset.uiSurface) };
      }, row.surface));
    }
  }
  if (request.reads && request.reads.length) {
    const defaults = request.defaults || {};
    if (defaults.state && defaults.surface) await selectSurface(defaults.surface, defaults.state);
    if (defaults.target) await press('data-hifi-target-control', defaults.target);
    const tokens = page.locator('[data-hifi-review-view="design-tokens"]');
    if (await tokens.count() === 1) {
      await tokens.click({ timeout });
      await page.waitForFunction(() => {
        const open = root => {
          if (!root) return false;
          for (const el of root.querySelectorAll('[data-hifi-panel]')) if (el.dataset.hifiPanel === 'design-tokens' && !el.hidden) return true;
          for (const el of root.querySelectorAll('*')) if (el.shadowRoot && open(el.shadowRoot)) return true;
          return false;
        };
        return open(document);
      }, { timeout });
      result.reads = await page.evaluate(specs => {
        const identity = spec => ({ kind: spec.kind, name: spec.name, sourcePage: spec.sourcePage, source: spec.source,
          property: spec.property, variant: spec.variant, state: spec.state, element: spec.element,
          sharedGroup: spec.sharedGroup || null });
        const identityOf = el => ({ kind: el.getAttribute('data-hifi-spec'), name: el.getAttribute('data-name') || '',
          sourcePage: el.getAttribute('data-source-page') || '', source: el.getAttribute('data-source') || '',
          property: el.getAttribute('data-property') || '', variant: el.getAttribute('data-variant') || '',
          state: el.getAttribute('data-state') || '', element: el.getAttribute('data-specimen-element') || '',
          sharedGroup: el.getAttribute('data-shared-group') || null });
        const collect = selector => {
          const found = [];
          const walk = root => {
            if (!root) return;
            let all;
            try { found.push(...root.querySelectorAll(selector)); all = root.querySelectorAll('*'); } catch (_) { return; }
            for (const el of all) if (el.shadowRoot) walk(el.shadowRoot);
          };
          walk(document);
          return found;
        };
        const groups = new Map();
        for (const spec of collect('[data-hifi-spec]')) {
          const key = JSON.stringify(identityOf(spec));
          if (!groups.has(key)) groups.set(key, []);
          groups.get(key).push(spec);
        }
        return specs.map(spec => {
          const queue = groups.get(JSON.stringify(identity(spec))) || [];
          const el = queue.length ? queue.shift() : null;
          const read = { ...identity(spec), specimenValue: null, displayValue: null, specimenComputedValue: null };
          if (!el) return read;
          const sample = el.querySelector('[data-hifi-specimen-content]');
          const output = el.querySelector('output');
          if (sample) {
            const computed = getComputedStyle(sample);
            read.specimenValue = computed.getPropertyValue(spec.property).trim() || null;
            if (spec.kind === 'token' && spec.previewProperty) {
              read.specimenComputedValue = computed.getPropertyValue(spec.previewProperty).trim() || null;
            }
          }
          const shown = output && output.textContent ? output.textContent.trim() : '';
          read.displayValue = shown || read.specimenValue || null;
          return read;
        });
      }, request.reads);
      await page.evaluate(() => { location.hash = ''; });
      await settle();
    }
  }
  return result;
}

async function close() {
  if (browser) await browser.close();
  return {};
}

const handlers = { start, open, case: runCase, interact, reviewer, shot, axis, close };
let chain = Promise.resolve();
const lines = readline.createInterface({ input: process.stdin });
lines.on('line', line => {
  chain = chain.then(async () => {
    let message;
    try { message = JSON.parse(line); } catch (_) { return; }
    let reply;
    try {
      reply = { id: message.id, ok: true, result: await handlers[message.op](message) };
    } catch (error) {
      reply = { id: message.id, ok: false, error: String((error && error.message) || error).split('\n')[0] };
    }
    reply.events = drain();
    process.stdout.write(JSON.stringify(reply) + '\n');
    if (message.op === 'close') process.exit(0);
  });
});
lines.on('close', () => { chain.then(() => (browser ? browser.close().catch(() => {}) : null)).then(() => process.exit(0)); });
"""


class NodeDriver:
    """Speaks the JSON-lines protocol to one Node Playwright process."""

    def __init__(self, node, module, files, scratch, color_scheme="light"):
        self.node, self.module, self.files, self.scratch = node, module, files, Path(scratch)
        self.color_scheme = color_scheme
        self.proc = None
        self.environment = {}
        self._lines = queue.Queue()
        self._stderr = collections.deque(maxlen=20)
        self._seq = 0

    def start(self):
        script = self.scratch / "driver.js"
        if not script.exists():
            script.write_text(DRIVER_JS, encoding="utf-8")
        self._lines = queue.Queue()
        self.proc = subprocess.Popen(
            [self.node, str(script), str(self.module)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._pump, args=(self.proc.stdout, self._lines), daemon=True).start()
        threading.Thread(target=self._pump, args=(self.proc.stderr, None), daemon=True).start()
        reply = self.call("start", timeout=90, files={n: str(p) for n, p in self.files.items()},
                          viewport={"width": 1920, "height": 1080}, colorScheme=self.color_scheme)
        self.environment = reply["result"]["environment"]

    def _pump(self, stream, sink):
        queue_out = sink
        for line in stream:
            if queue_out is not None:
                queue_out.put(line)
            else:
                self._stderr.append(line.rstrip())
        if queue_out is not None:
            queue_out.put(None)

    def call(self, op, timeout=CASE_TIMEOUT_S + 10, **fields):
        self._seq += 1
        try:
            # id and op go last so a payload field of the same name cannot clobber the reply correlation.
            self.proc.stdin.write(json.dumps({**fields, "op": op, "id": self._seq}) + "\n")
            self.proc.stdin.flush()
        except OSError as error:
            raise DriverError("driver is not running: " + self._tail()) from error
        deadline = time.monotonic() + timeout
        while True:
            try:
                line = self._lines.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise DriverTimeout(f"{op} gave no reply within {timeout}s") from None
            if line is None:
                raise DriverError("driver exited: " + self._tail())
            reply = json.loads(line)
            if reply.get("id") == self._seq:
                break
        if not reply["ok"]:
            raise DriverError(reply["error"], reply.get("events"))
        return reply

    def _tail(self):
        return " | ".join(self._stderr)[-400:] or "no driver output"

    def stop(self):
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                self._seq += 1
                proc.stdin.write(json.dumps({"id": self._seq, "op": "close"}) + "\n")
                proc.stdin.flush()
                proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if proc.poll() is None:
            kill_tree(proc)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                stream.close()
            except OSError:
                pass

    def restart(self):
        self.stop()
        self.start()


def kill_tree(proc):
    """Stop only the process we spawned and its children."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, check=False)
    else:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def find_playwright(repo_root, node):
    """Return the Node Playwright package directory, or raise UsageError."""
    candidates = []
    if os.environ.get("PLAYWRIGHT_MODULE"):
        candidates.append(Path(os.environ["PLAYWRIGHT_MODULE"]))
    candidates.append(repo_root / "node_modules" / "playwright")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    result = subprocess.run([node, "-p", "require.resolve('playwright')"], cwd=repo_root,
                            text=True, capture_output=True, timeout=15, check=False)
    if result.returncode == 0 and result.stdout.strip():
        resolved = Path(result.stdout.strip())
        return resolved.parent if resolved.is_file() else resolved
    raise UsageError("Node Playwright is required: run `npm ci` and `npx playwright install chromium`, "
                     "or set PLAYWRIGHT_MODULE to the playwright package directory")


# --- Package, matrix, fingerprints ------------------------------------------
def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Case:
    surface: str
    page: str
    state: str
    target: str
    axis: str | None = None

    @property
    def key(self):
        return (self.surface, self.state, self.target)


@dataclass
class Package:
    manifest: dict
    files: dict
    sha: dict
    keys: dict
    widths: dict


def page_key(name, html, manifest, data):
    """Identity used for carry-forward. An entry page ignores its manifest page hashes."""
    if name != "index.html":
        return sha256_bytes(data)
    blanked = copy.deepcopy(manifest)
    for row in blanked.get("pages", []):
        row["sha256"] = ""
    match = HIFI_MANIFEST_RE.search(html)
    return sha256_bytes((html[:match.start("data")] + canonical(blanked) + html[match.end("data"):]).encode("utf-8"))


def package_file(package_dir, name):
    """A manifest path resolved inside the package. Traversal, absolute and drive paths and links fail before any read."""
    try:
        return safe_path(package_dir, name)
    except (ValueError, TypeError) as error:
        raise UsageError(f"unsafe package path {name!r}: {error}") from None


def read_package(package_dir):
    entry = package_file(package_dir, "index.html")
    if not entry.is_file():
        raise UsageError(f"{package_dir} has no index.html")
    html = entry.read_text(encoding="utf-8")
    found = HIFI_MANIFEST_RE.findall(html)
    if len(found) != 1:
        raise UsageError("index.html must contain exactly one ui-hifi manifest")
    manifest = json.loads(found[0])
    if manifest.get("schema") != "ui-hifi/2" or not manifest.get("surfaces"):
        raise UsageError("the manifest must be ui-hifi/2 with surfaces")
    try:
        declared = {row["path"]: row["sha256"] for row in manifest.get("pages", [])}
    except (KeyError, TypeError):
        raise UsageError("every manifest page needs a path and a sha256") from None
    names = ["index.html"] + list(declared)
    files, sha, keys, widths = {}, {}, {}, {}
    for name in names:
        path = package_file(package_dir, name)
        if not path.is_file():
            raise UsageError(f"package page is missing: {name}")
        data = path.read_bytes()
        if name in declared and sha256_bytes(data) != declared[name]:
            raise UsageError(f"{name} differs from its manifest hash; assemble the package again")
        page_html = data.decode("utf-8")
        files[name], sha[name] = path, sha256_bytes(data)
        keys[name] = page_key(name, page_html, manifest, data)
        widths[name] = canvas_widths(name, page_html, manifest)
    for row in manifest["surfaces"]:
        if row["page"] not in files:
            raise UsageError(f"surface {row['id']} names a page that is not in the package: {row['page']}")
    return Package(manifest, files, sha, keys, widths)


def canvas_widths(name, html, manifest):
    """Target label -> CSS pixel width, read from the page's canvas like the reviewer check does."""
    targets = list(dict.fromkeys(str(t) for row in manifest["surfaces"] if row["page"] == name
                                 for t in row["responsive"]["targets"]))
    parser = ReviewerParser()
    parser.feed(html)
    parser.close()
    attrs = next((a for _, a, _ in parser.nodes if "data-hifi-canvas" in a), None)
    if attrs is None:
        raise UsageError(f"{name} has no [data-hifi-canvas]")
    widths, error = _target_widths(attrs, targets)
    if error:
        raise UsageError(f"{name}: {error}")
    return widths


def representative_targets(targets):
    """(smallest, largest) by the list rule check_ui_design_contract.representative_targets uses:
    numeric widths compare by value; named size classes keep their listed order."""
    values = [str(t) for t in targets]
    if values and all(v.strip().lstrip("-").isdigit() for v in values):
        ordered = sorted(values, key=lambda v: (int(v), values.index(v)))
        return ordered[0], ordered[-1]
    return values[0], values[-1]


def smallest_target(targets, widths=None):
    return representative_targets(targets)[0]


def largest_target(targets, widths=None):
    return representative_targets(targets)[1]


def expand_matrix(package, only=None, derived=None):
    """Applicable surface x state x target cases in manifest order.

    A derived state is observed once, at its surface's smallest target."""
    cases = []
    for row in package.manifest["surfaces"]:
        if only and row["id"] not in only:
            continue
        targets = [str(t) for t in row["responsive"]["targets"]]
        for state in row["states"]:
            if _is_na_state(state):
                continue
            chosen = targets
            if derived and str(state) in derived.get(row["id"], ()):
                chosen = [smallest_target(targets, package.widths[row["page"]])]
            cases.extend(Case(row["id"], row["page"], str(state), target) for target in chosen)
    return cases


def sample_axis_cases(rows, page, widths, counts, derived=None):
    """`ready` (or the first state) plus the busiest state, at the smallest and largest target.

    A derived state takes no stress axis, so neither pick comes from the derived states."""
    cases = []
    for row in rows:
        skipped = set((derived or {}).get(row["id"], ()))
        states = [str(s) for s in row["states"] if not _is_na_state(s) and str(s) not in skipped]
        if not states:
            continue
        busiest = max(states, key=lambda s: counts.get((row["id"], s), -1))
        targets = [str(t) for t in row["responsive"]["targets"]]
        picks = list(dict.fromkeys([smallest_target(targets, widths), largest_target(targets, widths)]))
        for state in dict.fromkeys(["ready" if "ready" in states else states[0], busiest]):
            cases.extend(Case(row["id"], page, state, target) for target in picks)
    return cases


def group_by_page(cases):
    grouped = {}
    for case in cases:
        grouped.setdefault(case.page, []).append(case)
    return grouped


def interaction_plan(package, only=None):
    """Selected manifest interactions to observe, in manifest order; a malformed manifest refuses before any browser work."""
    actions = package.manifest.get("interactions")
    if not isinstance(actions, list):
        raise UsageError("the manifest must declare an interactions list")
    surfaces = {row["id"]: row for row in package.manifest["surfaces"]}
    plan, seen = [], set()
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("source"), dict) or not isinstance(action.get("destination"), dict):
            raise UsageError("every interaction needs id, source, control, kind and destination")
        ident, kind, control = action.get("id"), action.get("kind"), action.get("control")
        if any(not isinstance(value, str) or not value.strip() for value in (ident, kind, control)):
            raise UsageError("every interaction needs id, source, control, kind and destination")
        if ident in seen:
            raise UsageError(f"duplicate interaction id: {ident}")
        seen.add(ident)
        if kind not in INTERACT_KINDS:
            raise UsageError(f"interaction {ident} has an unknown kind: {kind}")
        for field in ("source", "destination"):
            surface, state = action[field].get("surface"), action[field].get("state")
            row = surfaces.get(surface) if isinstance(surface, str) else None
            if row is None or not isinstance(state, str) or state not in [str(s) for s in row["states"]]:
                raise UsageError(f"interaction {ident} names an unknown {field} surface state: {surface} {state}")
        source_row = surfaces[action["source"]["surface"]]
        plan.append({"id": ident, "kind": kind, "control": control, "source": action["source"],
                     "destination": action["destination"], "page": source_row["page"],
                     "destinationPage": surfaces[action["destination"]["surface"]]["page"],
                     "targets": [str(t) for t in source_row["responsive"]["targets"]]})
    return [a for a in plan if only is None or a["source"]["surface"] in only]


def intermediate_widths(row):
    """Sorted numeric viewport targets of a surface, or None when it has no web interval to sweep."""
    responsive = row.get("responsive") or {}
    if responsive.get("kind") != "viewports":
        return None
    try:
        widths = sorted({float(target) for target in responsive.get("targets", [])})
    except (TypeError, ValueError):
        return None
    return widths if len(widths) > 1 else None


def midpoint_width(low, high):
    value = (low + high) / 2
    return str(int(value)) if value.is_integer() else str(value)


def intermediate_plan(package, only=None):
    """One case per non-n/a state, at the midpoint of each adjacent pair of numeric viewport targets."""
    cases = []
    for row in package.manifest["surfaces"]:
        if only and row["id"] not in only:
            continue
        widths = intermediate_widths(row)
        states = [str(state) for state in row["states"] if not _is_na_state(state)]
        if not widths or not states:
            continue
        for state in states:
            for low, high in zip(widths, widths[1:]):
                cases.append(Case(row["id"], row["page"], state, midpoint_width(low, high)))
    return cases


def intermediate_scope(package, plan):
    """The checker-scope shape `ui_design_v3.intermediate_width_findings` reads: exactly what the plan covers."""
    rows = {row["id"]: row for row in package.manifest["surfaces"]}
    surfaces = []
    for surface in dict.fromkeys(case.surface for case in plan):
        states = sorted({case.state for case in plan if case.surface == surface})
        surfaces.append({"id": surface, "states": states,
                         "responsive": {"kind": "viewports", "targets": intermediate_widths(rows[surface])}})
    return {"surfaces": surfaces}


def intermediate_findings(package, plan, results):
    """The checker's own intermediate-width coverage rule over a written intermediate output."""
    observed = [{key: row[key] for key in ("surface", "state", "target")} for row in results]
    return intermediate_width_findings(observed, intermediate_scope(package, plan))


def tuple_hash(case):
    return sha256_bytes("\x1f".join((case.surface, case.state, case.target, case.axis or "")).encode("utf-8"))[:10]


def capture_name(case):
    def slug(text):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "x"
    parts = [slug(case.surface), slug(case.state), slug(case.target)] + ([slug(case.axis)] if case.axis else [])
    return "-".join(parts) + "-" + tuple_hash(case) + ".png"


def render_fingerprint(probe):
    """SHA-256 over the geometry probe, the element rects, the computed-style/text digest and the image inputs."""
    return sha256_bytes(canonical({"geometry": probe["geometry"], "rects": probe["rectsSha256"],
                                   "style": probe["styleSha256"], "inputs": probe["inputsSha256"]}).encode("utf-8"))


def console_row_fails(row):
    """The checker's own console rule, including its one exempt CSP row."""
    return bool(_offline_transcript_findings({
        "sandbox": {"network": "disabled", "topNavigation": "blocked", "popups": "blocked", "forms": "blocked"},
        "console": [row], "network": [], "navigation": [], "popups": [], "forms": [],
        "popupAttempts": 0, "formAttempts": 0}))


def event_reasons(events):
    reasons = []
    for row in events.get("console", []):
        if console_row_fails(row):
            reasons.append(f"console {row.get('level')}: {str(row.get('message'))[:160]}")
    reasons += [f"external request: {row.get('url')}" for row in events.get("network", [])]
    reasons += [f"navigation attempt: {row.get('url')}" for row in events.get("navigation", [])]
    reasons += [f"popup attempt: {row.get('url')}" for row in events.get("popups", [])]
    reasons += [f"form attempt: {row.get('action')}" for row in events.get("forms", [])]
    return reasons


# --- Carry-forward ------------------------------------------------------------
def load_carry(root, carry_path):
    """Previous base-case records keyed by (surface, state, target), plus the source output identity."""
    output_rel = carry_path.resolve().relative_to(root).as_posix()
    data = safe_path(root, output_rel).read_bytes()
    output = json.loads(data.decode("utf-8"))
    if output.get("schema") != "ui-output/3":
        raise UsageError("--carry-from must be a ui-output/3 file")
    binding = next((b for b in output.get("execution", {}).get("artifacts", [])
                    if b.get("path", "").rsplit("/", 1)[-1] == SIDECAR_NAME), None)
    if binding is None:
        raise UsageError(f"--carry-from output does not bind a {SIDECAR_NAME}")
    sidecar_bytes = safe_path(root, binding["path"]).read_bytes()
    if sha256_bytes(sidecar_bytes) != binding["sha256"]:
        raise UsageError(f"{binding['path']} differs from the hash in the previous output")
    sidecar = json.loads(sidecar_bytes.decode("utf-8"))
    if sidecar.get("schema") != SIDECAR_SCHEMA:
        raise UsageError(f"{binding['path']} is not a {SIDECAR_SCHEMA} file")
    records = {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}
    return records, {"path": output_rel, "sha256": sha256_bytes(data)}


def carry_folders(root, carry_path, records):
    """Folders that hold the carry source: its output and the captures it points at."""
    folders = {carry_path.parent}
    for record in records.values():
        for capture in (record.get("capture"), (record.get("carriedFrom") or {}).get("capture")):
            if capture:
                folders.add((root / capture["path"]).resolve().parent)
    return folders


def related(left, right):
    """True when the folders are the same or one sits inside the other."""
    return left == right or left in right.parents or right in left.parents


# --- Reviewer object ----------------------------------------------------------
def reviewer_plan(package):
    """The reviewer rows ``hifi_reviewer.reviewer_contract`` derives, grouped per page in contract order.

    The rows describe what a correct package shows; the run measures every row in
    the browser and writes the rows as measured, whatever they show."""
    try:
        documents = {name: path.read_text(encoding="utf-8") for name, path in package.files.items()}
    except (OSError, UnicodeError):
        return None
    errors, contract = reviewer_contract(documents, package.manifest)
    if contract is None:
        return None
    first_states = {row["id"]: next((str(state) for state in row["states"] if not _is_na_state(state)), None)
                    for row in package.manifest["surfaces"]}
    pages = {}
    for row in contract["viewport"]:
        page = pages.setdefault(row["page"], {"entry": False, "viewport": [], "sources": [], "reads": [], "defaults": None})
        page["viewport"].append({"surface": row["surface"], "target": row["target"], "state": first_states.get(row["surface"]),
                                 "expectedWidth": row["measuredProductWidth"]})
    entry = pages.setdefault("index.html", {"entry": False, "viewport": [], "sources": [], "reads": [], "defaults": None})
    entry["entry"] = True
    entry["sources"] = [spec for spec in contract["specimens"] if spec["sourcePage"] == "index.html"]
    entry["reads"] = list(contract["specimens"])
    entry["defaults"] = {"surface": contract["defaultSurface"], "state": first_states.get(contract["defaultSurface"]),
                         "target": contract["viewport"][0]["target"] if contract["viewport"] else None}
    for page in pages:
        if page != "index.html":
            pages[page]["sources"] = [spec for spec in contract["specimens"] if spec["sourcePage"] == page]
    return {"contract": contract, "pages": pages}


# --- The run --------------------------------------------------------------------
class Runner:
    def __init__(self, driver, package, root, out_dir, *, axes=(), carry=None, carry_source=None, derived=None,
                 interactions=(), recapture=False, diff_against=None, settle_cap_ms=SETTLE_CAP_MS, case_timeout_s=CASE_TIMEOUT_S,
                 intermediate=False):
        self.driver, self.package, self.root, self.out_dir = driver, package, root, out_dir
        self.axes, self.carry, self.carry_source, self.derived = tuple(axes), carry or {}, carry_source, derived
        self.interactions = list(interactions)
        self.recapture, self.diff_against = recapture, diff_against
        self.settle_cap_ms, self.case_timeout_s = settle_cap_ms, case_timeout_s
        self.intermediate = intermediate
        self.transcript = {kind: [] for kind in TRANSCRIPT_KINDS}
        self.records, self.axis_records, self.interaction_records = {}, [], []
        self.page_reasons, self.unopened = {}, set()
        self.restarts, self.aborted, self.active_axis = 0, False, None
        self.kinds = {row["id"]: row["responsive"].get("kind") for row in package.manifest["surfaces"]}
        self.reviewer_plan, self.reviewer_records = reviewer_plan(package), []

    # events: base-case events join the transcript; axis-case events only decide that case
    def absorb(self, events, page, keep=True):
        if keep:
            for kind in TRANSCRIPT_KINDS:
                self.transcript[kind].extend(dict(row, page=page) for row in events.get(kind, []))
        return event_reasons(events)

    def recover(self, page):
        self.restarts += 1
        if self.restarts > MAX_RESTARTS:
            self.aborted = True
            return
        try:
            self.driver.restart()
            reply = self.driver.call("open", page=page, timeoutMs=self.case_timeout_s * 1000)
            self.absorb(reply["events"], page, keep=not self.active_axis)
            if self.active_axis:
                self.driver.call("axis", name=self.active_axis)
        except DriverError:
            self.aborted = True

    def run(self, cases):
        for page, page_cases in group_by_page(cases).items():
            self.run_page(page, page_cases)
        # The intermediate sweep is a width check; the reviewer object belongs to the base output only.
        if not self.intermediate:
            self.run_reviewer()

    def run_page(self, page, cases):
        if not self.aborted:
            try:
                reply = self.driver.call("open", page=page, timeoutMs=self.case_timeout_s * 1000)
                self.page_reasons[page] = ["page load: " + r for r in self.absorb(reply["events"], page)]
            except DriverError as error:
                self.unopened.add(page)
                self.page_reasons[page] = [f"page did not open: {error}"] + ["page load: " + r for r in self.absorb(error.events, page)]
                if isinstance(error, DriverTimeout):
                    self.recover(page)
        for case in cases:
            self.records[case.key] = self.observe(case)
        if self.axes:
            rows = [row for row in self.package.manifest["surfaces"] if row["page"] == page
                    and any(c.surface == row["id"] for c in cases)]
            counts = {}
            for case in cases:
                geometry = self.records[case.key].get("geometry")
                if geometry:
                    counts[(case.surface, case.state)] = max(counts.get((case.surface, case.state), 0), geometry["elementCount"])
            sampled = sample_axis_cases(rows, page, self.package.widths[page], counts, self.derived)
            for axis in self.axes:
                self.run_axis(page, axis, sampled)
        self.run_interactions(page)

    def run_interactions(self, page):
        """Click and keyboard-activate every selected manifest interaction at every source target."""
        actions = [a for a in self.interactions if a["page"] == page]
        if not actions:
            return
        blocked = ("page did not open, so its interactions were not observed" if page in self.unopened
                   else f"browser driver restart limit ({MAX_RESTARTS}) reached" if self.aborted else None)
        for action in actions:
            for target in action["targets"]:
                for trigger in TRIGGERS:
                    self.interaction_records.append(self.observe_interaction(action, target, trigger, blocked))

    def observe_interaction(self, action, target, trigger, blocked=None):
        record = {"id": action["id"], "surface": action["source"]["surface"], "state": action["source"]["state"],
                  "target": target, "trigger": trigger, "page": action["page"], "kind": action["kind"],
                  "control": action["control"], "destination": action["destination"], "result": None,
                  "reasons": [], "visible": None, "focusCorrect": None, "arrived": None,
                  "startedAt": now_iso(), "finishedAt": None, "durationMs": None}
        began = time.perf_counter()
        reasons = record["reasons"]
        blocked = blocked or (f"browser driver restart limit ({MAX_RESTARTS}) reached" if self.aborted else None)
        if blocked:
            record["result"] = "BLOCKED"
            reasons.append(blocked)
        else:
            self.run_interaction(action, target, trigger, record)
            record["result"] = "FAIL" if reasons else "PASS"
        record["finishedAt"] = now_iso()
        record["durationMs"] = round((time.perf_counter() - began) * 1000)
        return record

    def run_interaction(self, action, target, trigger, record):
        reasons = record["reasons"]
        try:
            reply = self.driver.call("interact", timeout=self.case_timeout_s + 10, page=action["page"], interaction=action["id"],
                                     surface=action["source"]["surface"], state=action["source"]["state"],
                                     target=target, control=action["control"], kind=action["kind"],
                                     destination=action["destination"], destinationPage=action["destinationPage"],
                                     trigger=trigger, timeoutMs=self.case_timeout_s * 1000)
        except DriverTimeout as error:
            reasons.append(f"interaction timed out after {self.case_timeout_s}s")
            events, result = error.events, {}
            self.recover(action["page"])
        except DriverError as error:
            reasons.append(f"driver error: {error}")
            events, result = error.events, {}
        else:
            events, result = reply["events"], reply["result"]
        # A navigate attempt's one arrival row becomes the documented navigation event; every other
        # navigation row stays in the transcript and fails the attempt.
        stray = list(events.get("navigation", []))
        if action["kind"] == "navigate":
            arrived = [row for row in stray if row.get("url") == DRIVER_BASE + action["destinationPage"]]
            if len(arrived) == 1:
                record["arrived"] = action["destinationPage"]
                stray.remove(arrived[0])
        for row in stray:
            reasons.append(f"navigation attempt: {row.get('url')}")
        for kind in ("console", "network", "popups", "forms"):
            self.transcript[kind].extend(dict(row, page=action["page"]) for row in events.get(kind, []))
        self.transcript["navigation"].extend(dict(row, page=action["page"]) for row in stray)
        reasons.extend(result.get("problems") or [])
        record["visible"], record["focusCorrect"] = result.get("visible"), result.get("focusCorrect")
        if action["kind"] == "navigate":
            if record["arrived"] is None:
                reasons.append("the destination page did not load")
            elif result.get("arrivedTo") != action["destinationPage"]:
                reasons.append(f"the browser did not land on {action['destinationPage']}")

    def run_axis(self, page, axis, sampled):
        """One row per sampled case. An axis that cannot be applied gives BLOCKED rows, never none."""
        blocked = f"page did not open, so axis {axis} was not applied" if page in self.unopened else None
        if blocked is None and not self.aborted:
            try:
                self.driver.call("axis", name=axis)
                self.active_axis = axis
            except DriverError as error:
                blocked = f"axis {axis} could not be set up: {error}"
        for case in sampled:
            self.axis_records.append(self.observe(replace(case, axis=axis), blocked=blocked))
        self.active_axis = None
        if page in self.unopened or self.aborted:
            return
        try:
            self.driver.call("axis", name="none")
        except DriverError:
            self.recover(page)      # a fresh browser, so the next axis or page does not start from this axis

    def observe(self, case, blocked=None):
        record = {"surface": case.surface, "state": case.state, "target": case.target, "axis": case.axis,
                  "page": case.page, "pageSha256": self.package.sha[case.page], "pageKey": self.package.keys[case.page],
                  "result": None, "reasons": [], "startedAt": now_iso(), "finishedAt": None, "durationMs": None,
                  "renderFingerprint": None, "fingerprintIncomplete": False, "geometry": None, "settle": None,
                  "capture": None, "carriedFrom": None}
        began = time.perf_counter()
        reasons = record["reasons"]
        blocked = blocked or (f"browser driver restart limit ({MAX_RESTARTS}) reached" if self.aborted else None)
        if blocked:
            record["result"] = "BLOCKED"
            reasons.append(blocked)
        else:
            reasons.extend(self.page_reasons.get(case.page, []))
            if case.page not in self.unopened:
                self.run_case(case, record)
            record["result"] = "FAIL" if reasons else "PASS"
        record["finishedAt"] = now_iso()
        record["durationMs"] = round((time.perf_counter() - began) * 1000)
        return record

    def shell_target(self, case):
        """The shell control an intermediate case drives: its surface's smallest target, widened from there."""
        if not self.intermediate:
            return case.target
        row = next(row for row in self.package.manifest["surfaces"] if row["id"] == case.surface)
        return smallest_target([str(t) for t in row["responsive"]["targets"]], self.package.widths[case.page])

    def run_case(self, case, record):
        reasons, keep = record["reasons"], case.axis is None
        try:
            reply = self.driver.call("case", timeout=self.case_timeout_s + 10, surface=case.surface, state=case.state,
                                     target=self.shell_target(case), widthPx=float(case.target) if self.intermediate else None,
                                     settleCapMs=self.settle_cap_ms, marginMs=SETTLE_MARGIN_MS,
                                     timeoutMs=self.case_timeout_s * 1000)
        except DriverTimeout as error:
            reasons.append(f"case timed out after {self.case_timeout_s}s")
            reasons.extend(self.absorb(error.events, case.page, keep))
            self.recover(case.page)
            return
        except DriverError as error:
            reasons.append(f"driver error: {error}")
            reasons.extend(self.absorb(error.events, case.page, keep))
            return
        reasons.extend(self.absorb(reply["events"], case.page, keep))
        result = reply["result"]
        reasons.extend(result["problems"])
        probe = result.get("probe")
        if probe is None:
            return
        geometry = probe["geometry"]
        record.update(geometry=geometry, settle=result["settle"], renderFingerprint=render_fingerprint(probe),
                      fingerprintIncomplete=bool(probe.get("incomplete")))
        if self.intermediate:
            if abs(geometry["canvasWidth"] - float(case.target)) > WIDTH_TOLERANCE_PX:
                reasons.append(f"product canvas is {geometry['canvasWidth']}px wide, the intermediate width needs {case.target}px")
        elif self.kinds[case.surface] == "viewports":
            declared = self.package.widths[case.page][case.target]
            if abs(geometry["canvasWidth"] - declared) > WIDTH_TOLERANCE_PX:
                reasons.append(f"product canvas is {geometry['canvasWidth']}px wide at target {case.target}, declared {declared}px")
        if geometry["overflowX"] > OVERFLOW_TOLERANCE_PX:
            reasons.append(f"horizontal overflow {geometry['overflowX']}px")
        if geometry["stateViews"] < 1:
            reasons.append(f"no visible data-hifi-state-view=\"{case.state}\" variant")
        if case.axis is None:
            record["carriedFrom"] = self.carried(case, record)
        if record["carriedFrom"] is None or self.recapture:
            self.capture(case, record, keep)

    def carried(self, case, record):
        previous = self.carry.get(case.key)
        if not previous or previous.get("axis") or previous["result"] != "PASS" or record["reasons"]:
            return None
        if record["fingerprintIncomplete"] or previous.get("fingerprintIncomplete"):
            return None
        if previous["renderFingerprint"] != record["renderFingerprint"]:
            return None
        capture = previous.get("capture") or (previous.get("carriedFrom") or {}).get("capture")
        try:
            if not capture or sha256_bytes(safe_path(self.root, capture["path"]).read_bytes()) != capture["sha256"]:
                return None
        except (OSError, ValueError):
            return None
        return {"result": "PASS", "pageSha256": previous["pageSha256"], "capture": capture, "sourceOutput": self.carry_source}

    def capture(self, case, record, keep):
        path = self.out_dir / capture_name(case)
        try:
            reply = self.driver.call("shot", path=str(path), timeoutMs=self.case_timeout_s * 1000)
        except DriverTimeout:
            record["reasons"].append(f"screenshot timed out after {self.case_timeout_s}s")
            self.recover(case.page)
            return
        except DriverError as error:
            record["reasons"].append(f"screenshot failed: {error}")
            return
        record["reasons"].extend(self.absorb(reply["events"], case.page, keep))
        record["capture"] = {"path": path.relative_to(self.root).as_posix(), "sha256": sha256_bytes(path.read_bytes())}
        if self.diff_against is not None and (self.diff_against / path.name).is_file():
            record["pixelDiff"] = pixel_diff(self.diff_against / path.name, path)


    def run_reviewer(self):
        """Measure the reviewer viewport and specimen rows in the contract's order, after the interactions."""
        plan = self.reviewer_plan
        if not plan:
            return
        for page, page_plan in plan["pages"].items():
            self.reviewer_records.append(self.observe_reviewer(page, page_plan))

    def observe_reviewer(self, page, page_plan):
        record = {"page": page, "result": None, "reasons": [], "entry": None, "viewport": [], "sources": [],
                  "reads": [], "startedAt": now_iso(), "finishedAt": None, "durationMs": None}
        began = time.perf_counter()
        reasons = record["reasons"]
        blocked = ("page did not open, so its reviewer rows were not measured" if page in self.unopened
                   else f"browser driver restart limit ({MAX_RESTARTS}) reached" if self.aborted else None)
        if blocked:
            record["result"] = "BLOCKED"
            reasons.append(blocked)
        else:
            try:
                reply = self.driver.call("reviewer", timeout=self.case_timeout_s * 3 + 20, page=page,
                                         timeoutMs=self.case_timeout_s * 1000, **page_plan)
            except DriverTimeout as error:
                reasons.append(f"reviewer pass timed out after {self.case_timeout_s * 3 + 20}s")
                reasons.extend(self.absorb(error.events, page))
                self.recover(page)
            except DriverError as error:
                reasons.append(f"driver error: {error}")
                reasons.extend(self.absorb(error.events, page))
            else:
                reasons.extend(self.absorb(reply["events"], page))
                result = reply["result"]
                record["entry"] = result.get("entry")
                record["viewport"] = result.get("viewport") or []
                record["sources"] = result.get("sources") or []
                record["reads"] = result.get("reads") or []
            record["result"] = "FAIL" if reasons else "PASS"
        record["finishedAt"] = now_iso()
        record["durationMs"] = round((time.perf_counter() - began) * 1000)
        return record


def pixel_diff(before, after):
    """Compare two PNGs with Pillow: a pixel is changed when any RGBA channel differs. The geometry fingerprint stays the primary signal."""
    from PIL import Image, ImageChops
    with Image.open(before) as old, Image.open(after) as new:
        if old.size != new.size:
            return {"against": before.name, "status": "changed", "ratio": 1.0}
        changed_bands = [band.point([0] + [255] * 255) for band in ImageChops.difference(old.convert("RGBA"), new.convert("RGBA")).split()]
        any_channel = changed_bands[0]
        for band in changed_bands[1:]:
            any_channel = ImageChops.lighter(any_channel, band)
        total = new.size[0] * new.size[1]
        changed = total - any_channel.histogram()[0]
    return {"against": before.name, "status": "changed" if changed else "identical", "ratio": round(changed / total, 6)}


# --- Output -----------------------------------------------------------------------
def interaction_rows(runner):
    """The closed ui-output/3 rows: one result per attempt, one navigation event per observed navigate arrival."""
    results, navigation = [], []
    for record in runner.interaction_records:
        results.append({"id": record["id"], "target": record["target"], "trigger": record["trigger"],
                        "source": {"surface": record["surface"], "state": record["state"]},
                        "destination": record["destination"], "control": record["control"],
                        "visible": record["visible"], "focusCorrect": record["focusCorrect"], "result": record["result"]})
        if record["kind"] == "navigate" and record["arrived"]:
            navigation.append({"id": record["id"], "target": record["target"], "trigger": record["trigger"],
                               "from": record["page"], "to": record["arrived"]})
    return results, navigation


def reviewer_identity(row):
    return (row["kind"], row["name"], row["sourcePage"], row["source"], row["property"], row["variant"],
            row["state"], row["element"], row["sharedGroup"])


def reviewer_object(runner):
    """The closed reviewer receipt object: contract identity carrying this run's browser measurements.

    Rows are written as measured; ``validate_output`` fails the output with the
    checker's own reviewer rule when a measured row disagrees with the contract."""
    plan = runner.reviewer_plan
    if plan is None:
        return None
    viewport_rows, source_rows, read_rows, entry = {}, {}, {}, None
    for record in runner.reviewer_records:
        for row in record["viewport"]:
            viewport_rows[(row["surface"], row["target"])] = row
        for row in record["sources"]:
            source_rows[reviewer_identity(row)] = row
        for row in record["reads"]:
            read_rows[reviewer_identity(row)] = row
        if record["page"] == "index.html" and record["entry"] is not None:
            entry = record["entry"]
    contract = plan["contract"]
    viewport = []
    for row in contract["viewport"]:
        got = viewport_rows.get((row["surface"], row["target"]))
        if got is None:
            viewport.append(dict(row, measuredProductWidth=None, containerQueryApplied=None,
                                 hostMediaQueryApplied=None, visibleSurfaces=None, result="BLOCKED"))
            continue
        passed = (got.get("measuredProductWidth") == row["measuredProductWidth"] and got.get("containerQueryApplied")
                  and not got.get("hostMediaQueryApplied") and got.get("visibleSurfaces") == [row["surface"]])
        viewport.append(dict(row, **{key: got.get(key) for key in ("measuredProductWidth", "containerQueryApplied",
                                                                   "hostMediaQueryApplied", "visibleSurfaces")},
                             result="PASS" if passed else "FAIL"))
    specimens = []
    for spec in contract["specimens"]:
        source, read = source_rows.get(reviewer_identity(spec)), read_rows.get(reviewer_identity(spec))
        row = dict(spec, sourceValue=(source or {}).get("sourceValue"), specimenValue=(read or {}).get("specimenValue"),
                   displayValue=(read or {}).get("displayValue"))
        if spec["kind"] == "token":
            row["sourceComputedValue"] = (source or {}).get("sourceComputedValue")
            row["specimenComputedValue"] = (read or {}).get("specimenComputedValue")
        specimens.append(row)
    return {"defaultSurface": (entry or {}).get("defaultSurface", contract["defaultSurface"]),
            "defaultVisible": (entry or {}).get("defaultVisible"),
            "overviewInitiallyHidden": (entry or {}).get("overviewInitiallyHidden"),
            "overview": contract["overview"], "viewport": viewport, "specimens": specimens}


def reviewer_findings(root, output):
    """The checker's own reviewer rule over the output this run wrote."""
    subject = output.get("subject") if isinstance(output, dict) else None
    path = subject.get("path") if isinstance(subject, dict) else None
    if not isinstance(path, str) or not path.endswith("index.html"):
        return []
    try:
        plan = reviewer_plan(read_package((root / path).parent))
    except (OSError, ValueError, TypeError, KeyError, UsageError):
        return []
    if plan is None:
        return []
    return reviewer_evidence_findings(output.get("reviewer"), plan["contract"])


def build_outputs(runner, package, cases, root, out_dir, subject, started, finished, environment, options):
    records = [runner.records.get(case.key) for case in cases]
    summary = {
        "cases": len(cases), "pass": sum(1 for r in records if r and r["result"] == "PASS"),
        "carried": sum(1 for r in records if r and r["carriedFrom"]),
        "axisCases": len(runner.axis_records),
        "axisFail": sum(1 for r in runner.axis_records if r["result"] != "PASS"),
        "interactions": len(runner.interaction_records),
        "interactionsFail": sum(1 for r in runner.interaction_records if r["result"] != "PASS"),
        "reviewerFail": sum(1 for r in runner.reviewer_records if r["result"] != "PASS"),
    }
    sidecar = {"schema": SIDECAR_SCHEMA, "subject": subject,
               "run": dict(options, startedAt=started, finishedAt=finished, **summary),
               "cases": [r for r in records if r], "axes": runner.axis_records,
               "interactions": runner.interaction_records, "reviewer": runner.reviewer_records}
    sidecar_bytes = (json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sidecar_path = out_dir / SIDECAR_NAME
    sidecar_path.write_bytes(sidecar_bytes)
    artifacts = [subject] + [{"path": subject["path"].rsplit("/", 1)[0] + "/" + name if "/" in subject["path"] else name,
                              "sha256": package.sha[name]} for name in package.files if name != "index.html"]
    artifacts.append({"path": sidecar_path.relative_to(root).as_posix(), "sha256": sha256_bytes(sidecar_bytes)})
    seen = {a["path"].casefold() for a in artifacts}
    for record in list(records) + runner.axis_records:
        for capture in (record or {}).get("capture"), ((record or {}).get("carriedFrom") or {}).get("capture"):
            if capture and capture["path"].casefold() not in seen:
                seen.add(capture["path"].casefold())
                artifacts.append(dict(capture))
    matrix = [{"surface": c.surface, "state": c.state, "target": c.target} for c in cases]
    interactions, declared_navigation = interaction_rows(runner)
    output = {
        "schema": "ui-output/3", "check": CHECK, "subject": subject, "matrix": {"cases": matrix},
        "results": [dict(case, result=(r["result"] if r else "MISSING")) for case, r in zip(matrix, records)],
        "interactions": interactions,
        "reviewer": reviewer_object(runner),
        "sandbox": SANDBOX, "console": runner.transcript["console"], "network": runner.transcript["network"],
        "navigation": declared_navigation + runner.transcript["navigation"], "popups": runner.transcript["popups"],
        "forms": runner.transcript["forms"], "popupAttempts": len(runner.transcript["popups"]),
        "formAttempts": len(runner.transcript["forms"]),
        "execution": {"startedAt": started, "finishedAt": finished, "tool": "playwright",
                      "method": HIFI_SURFACE_RECEIPT_METHOD, "environment": environment, "artifacts": artifacts},
    }
    output_path = out_dir / OUTPUT_NAME
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, output_path, summary


def validate_output(root, output_path, output):
    """Run the checker's receipt assembler and transcript rule over the written output."""
    problems = []
    try:
        build_receipt(root, output_path.relative_to(root).as_posix())
    except (OSError, ValueError, TypeError, KeyError) as error:
        problems.append(str(error))
    baseline = dict(output, navigation=[], sandbox={"network": "disabled", "topNavigation": "blocked",
                                                    "popups": "blocked", "forms": "blocked"})
    problems.extend(_offline_transcript_findings(baseline))
    problems.extend(reviewer_findings(root, output))
    return problems


# --- CLI ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True, help="directory with index.html and its sibling pages")
    parser.add_argument("--out", type=Path, required=True, help="evidence directory inside the repository")
    parser.add_argument("--carry-from", type=Path, help="previous ui-output.json written by this tool")
    parser.add_argument("--only", help="comma-separated surface IDs")
    parser.add_argument("--axes", default="", help="comma-separated: " + ", ".join(AXES))
    parser.add_argument("--derived-once", action="store_true", help="observe derived states once, at the smallest target")
    parser.add_argument("--ui-design", type=Path, help="ui-design.md whose Approved target scope names the derived states")
    parser.add_argument("--derived", type=Path, help='JSON map {"UI-001": ["state", ...]} that replaces the --ui-design set')
    parser.add_argument("--color-scheme", choices=("light", "dark"), default="light",
                        help="browser context theme for the whole run; dark writes its own base matrix output")
    parser.add_argument("--intermediate", action="store_true",
                        help="also capture every state at the midpoints between adjacent viewport targets into OUT/intermediate")
    parser.add_argument("--recapture-carried", action="store_true", help="new screenshot for carried cases too")
    parser.add_argument("--diff-against", type=Path, help="earlier --out directory for a pixel diff (needs Pillow)")
    parser.add_argument("--overwrite", action="store_true", help="write into a non-empty --out directory")
    return parser.parse_args(argv)


def inside(root, path, label):
    """Resolve a path (relative ones are repo-root-relative) and require it to stay in the repository."""
    resolved = (path if path.is_absolute() else root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise UsageError(f"{label} must be inside --repo-root") from None
    return resolved


def derived_from_ui_design(path):
    """{surface ID: [derived states]} from the Approved target scope of a ui-design.md, read by the checker's parser."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise UsageError(f"cannot read --ui-design: {error}") from None
    view, problems = parse_ui_contract_view(text)
    scope = view.get("target_scope")
    if not scope:
        raise UsageError("--ui-design has no readable Approved target scope" + (f": {problems[0]}" if problems else ""))
    return {item["id"]: list(item["derivedStates"]) for item in scope["surfaces"]
            if isinstance(item.get("derivedStates"), dict) and item["derivedStates"]}


def node_driver(package, root, scratch, color_scheme="light"):
    node = shutil.which("node")
    if node is None:
        raise UsageError("Node.js is required")
    return NodeDriver(node, find_playwright(root, node), package.files, scratch, color_scheme)


def execute(args, make_driver=node_driver):
    root = args.repo_root.resolve()
    package_dir, out_dir = inside(root, args.package, "--package"), inside(root, args.out, "--out")
    color_scheme = args.color_scheme
    axes = [a for a in args.axes.split(",") if a]
    unknown = [a for a in axes if a not in AXES]
    if unknown:
        raise UsageError(f"unknown axis {unknown[0]}; choose from {', '.join(AXES)}")
    for flag, value in (("--derived", args.derived), ("--ui-design", args.ui_design)):
        if value and not args.derived_once:
            raise UsageError(f"{flag} needs --derived-once")
    if args.derived_once and not (args.derived or args.ui_design):
        raise UsageError("--derived-once needs --ui-design <ui-design.md> or --derived <json>")
    ui_design = inside(root, args.ui_design, "--ui-design") if args.ui_design else None
    derived = derived_from_ui_design(ui_design) if ui_design else None
    if args.derived:
        derived = json.loads(args.derived.read_text(encoding="utf-8"))
    if out_dir.exists() and any(out_dir.iterdir()) and not args.overwrite:
        raise UsageError("--out is not empty; choose a new directory or pass --overwrite")
    diff_against = inside(root, args.diff_against, "--diff-against") if args.diff_against else None
    if diff_against is not None and importlib.util.find_spec("PIL") is None:
        raise UsageError("--diff-against needs Pillow (pip install Pillow)")
    package = read_package(package_dir)
    only = set(args.only.split(",")) if args.only else None
    known = {row["id"] for row in package.manifest["surfaces"]}
    if only and only - known:
        raise UsageError("--only names unknown surfaces: " + ", ".join(sorted(only - known)))
    cases = expand_matrix(package, only, derived)
    if not cases:
        raise UsageError("the selection has no applicable cases")
    interactions = interaction_plan(package, only)
    intermediate_cases = intermediate_plan(package, only) if args.intermediate else []
    if args.intermediate and not intermediate_cases:
        raise UsageError("--intermediate found no surface with two or more numeric viewport widths")
    carry_path = inside(root, args.carry_from, "--carry-from") if args.carry_from else None
    carry, carry_source = load_carry(root, carry_path) if carry_path else (None, None)
    if carry and args.overwrite and any(related(out_dir, folder) for folder in carry_folders(root, carry_path, carry)):
        raise UsageError("--overwrite would replace the carry source: --out must not be, hold or sit inside the folder "
                         "of --carry-from or of a capture it carries")
    out_dir.mkdir(parents=True, exist_ok=True)
    subject_dir = package_dir.relative_to(root).as_posix()
    subject = {"path": (subject_dir + "/" if subject_dir != "." else "") + "index.html", "sha256": package.sha["index.html"]}
    started = now_iso()
    with tempfile.TemporaryDirectory(prefix="pdh-matrix-") as scratch:
        driver = make_driver(package, root, scratch, color_scheme=color_scheme)
        intermediate_runner = None
        try:
            try:
                driver.start()
            except DriverError as error:
                raise UsageError(f"browser could not start: {error}") from error
            runner = Runner(driver, package, root, out_dir, axes=axes, carry=carry, carry_source=carry_source,
                            derived=derived, interactions=interactions, recapture=args.recapture_carried,
                            diff_against=diff_against)
            runner.run(cases)
            if intermediate_cases:
                intermediate_dir = out_dir / INTERMEDIATE_DIR
                intermediate_dir.mkdir(parents=True, exist_ok=True)
                intermediate_runner = Runner(driver, package, root, intermediate_dir, derived=derived,
                                             interactions=interactions, intermediate=True)
                intermediate_runner.run(intermediate_cases)
            environment = dict(driver.environment, python=platform.python_version(), platform=platform.platform())
        finally:
            driver.stop()
    finished = now_iso()
    for name, path in package.files.items():
        if sha256_bytes(path.read_bytes()) != package.sha[name]:
            raise UsageError(f"{name} changed while it was being captured")
    intermediate = None
    if intermediate_runner is not None:
        inter_output, inter_path, inter_summary = build_outputs(
            intermediate_runner, package, intermediate_cases, root, out_dir / INTERMEDIATE_DIR, subject, started,
            finished, environment, {"only": sorted(only) if only else None, "intermediate": True})
        findings = intermediate_findings(package, intermediate_cases, inter_output["results"])
        intermediate = {"output": inter_path.relative_to(root).as_posix(), "cases": inter_summary["cases"],
                        "fail": inter_summary["cases"] - inter_summary["pass"],
                        "interactionsFail": inter_summary["interactionsFail"], "findings": findings}
    options = {"only": sorted(only) if only else None, "axes": axes, "derivedOnce": bool(args.derived_once),
               "derived": derived, "derivedFrom": "--derived" if args.derived else ("--ui-design" if ui_design else None),
               "carryFrom": carry_source, "recaptureCarried": bool(args.recapture_carried),
               "colorScheme": None if color_scheme == "light" else color_scheme, "intermediate": intermediate}
    output, output_path, summary = build_outputs(runner, package, cases, root, out_dir, subject, started, finished,
                                                 environment, options)
    problems = validate_output(root, output_path, output)
    failed = (any(row["result"] != "PASS" for row in output["results"]) or summary["axisFail"]
              or summary["interactionsFail"]
              or bool(intermediate and (intermediate["fail"] or intermediate["interactionsFail"]
                                        or intermediate["findings"])))
    print(json.dumps({"result": "invalid" if problems and not failed else ("FAIL" if failed else "PASS"),
                      "output": output_path.relative_to(root).as_posix(), **summary,
                      "restarts": runner.restarts, "problems": problems[:5], "intermediate": intermediate}))
    return 3 if problems and not failed else (1 if failed else 0)


def main(argv=None, make_driver=node_driver):
    try:
        return execute(parse_args(argv), make_driver)
    except UsageError as error:
        print(json.dumps({"result": "invalid", "error": str(error)}))
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
