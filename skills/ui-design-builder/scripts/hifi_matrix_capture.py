#!/usr/bin/env python3
"""Capture a HiFi surface x state x target matrix and its product interactions in offline browser sessions.

One browser is the default; ``--workers N`` splits the work over up to N. A
browser loads a page once for each run of cases on it; every interaction attempt
and reviewer pass starts from a fresh load. Targets and states change through
the real reviewer shell controls, never by reloading between cases. The matrix pass
clicks no product control; the interaction pass then clicks every manifest
interaction at every source target and keyboard-activates it once, at the
smallest source target. Output:
one PNG per case, ``ui-output.json``
(``ui-output/3``: matrix, ``interactions`` rows, ``navigation`` events and the
``reviewer`` object) and ``matrix-capture.json`` (per-case fingerprints,
geometry, carried rows, axis runs, interaction records, reviewer
measurements and, with ``--measure-a11y``, an ``a11y`` object).

The browser is Node Playwright, the repo's pinned test dependency
(``PLAYWRIGHT_MODULE`` or ``node_modules/playwright`` under ``--repo-root``).
"""

from __future__ import annotations

import argparse
import collections
import copy
import ctypes
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

from check_ui_design_contract import HIFI_SURFACE_RECEIPT_METHOD, _offline_transcript_findings, parse_ui_contract_view, _hifi_state_href
from hifi_reviewer import ReviewerParser, _is_na_state, _target_widths, reviewer_contract, reviewer_evidence_findings
from review_evidence import HIFI_MANIFEST_RE, build_receipt, safe_path
from reviewer_shell import runtime_source
from ui_design_v3 import intermediate_width_findings

SIDECAR_SCHEMA = "hifi-matrix-capture/1"
OUTPUT_NAME = "ui-output.json"
SIDECAR_NAME = "matrix-capture.json"
INTERMEDIATE_DIR = "intermediate"
CHECK = "hifi-browser"
AXES = ("dark", "reduced-motion", "forced-colors", "zoom-200", "reflow-320")
A11Y_MEASURES = ("contrast", "target-size", "text-clip", "text-split", "focus-visible", "text-growth")
A11Y_BASE = ("contrast", "target-size", "text-clip", "text-split")      # measured on every base case
A11Y_AXIS = {"dark": ("contrast",), "zoom-200": ("text-clip", "text-split", "text-growth"), "forced-colors": ("focus-visible",)}
TRIGGERS = ("click", "keyboard")
INTERACT_KINDS = ("navigate", "state", "feedback")
DRIVER_BASE = "https://hifi.invalid/pkg/"
SETTLE_CAP_MS = 2000
SETTLE_MARGIN_MS = 50
CASE_TIMEOUT_S = 30
DESTINATION_WAIT_S = 10  # for a destination on the source page; an attempt that loads a page keeps CASE_TIMEOUT_S
MAX_RESTARTS = 3
MAX_WORKERS = 4         # one headless Chromium each; more than this overloads a laptop
OVERFLOW_TOLERANCE_PX = 1
WIDTH_TOLERANCE_PX = 1
REFLOW_WIDTH_PX = 320
SANDBOX = {"network": "disabled", "topNavigation": "allowlisted-local-pages",
           "popups": "blocked", "forms": "blocked"}
TRANSCRIPT_KINDS = ("console", "network", "navigation", "popups", "forms")
INTERACTIONS_UNOPENED = "page did not open, so its interactions were not observed"
REVIEWER_UNOPENED = "page did not open, so its reviewer rows were not measured"


def axis_unopened(axis):
    return f"page did not open, so axis {axis} was not applied"


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
let surfaceDefaults = {}, observingNavigation = false, observingFocus = false;
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
  if (canvas.style.zoom === '2') {
    const target = canvas.dataset.hifiTarget;
    const widths = JSON.parse(canvas.dataset.hifiTargetWidths || '{}');
    const nominal = px || widths[target] || Number(target);
    if (!Number.isFinite(nominal) || nominal <= 0) throw Error('zoom target has no numeric width');
    canvas.style.setProperty('width', nominal / 2 + 'px');
  } else if (px) canvas.style.setProperty('width', px + 'px');
  else canvas.style.removeProperty('width');
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
    containerInlineSize: round(parseFloat(getComputedStyle(canvas).width)),
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

// Measured accessibility, run in the page visit of the case that was just probed. Plain functions over the same
// capped element list the probe scans; a finding never changes a case result.
const A11Y = ({ surfaceId, limit, measures, axis, baseFonts, fonts }) => {
  const canvas = document.querySelector('[data-hifi-canvas]');
  const surface = canvas && Array.from(canvas.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surfaceId);
  if (!surface) return null;
  const round = value => Math.round(value * 100) / 100;
  const rect = el => el.getBoundingClientRect();
  const visible = el => {
    const r = rect(el), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const all = [surface].concat(Array.from(surface.querySelectorAll('*')))
    .filter(el => !['SCRIPT', 'STYLE', 'TEMPLATE'].includes(el.tagName) && visible(el));
  const scanned = all.slice(0, limit);
  // Visually hidden text is not measured: a box of 1 px or less in the canvas's own CSS px (zoom-200 doubles every
  // rect), or the clip-path or clip that screen-reader-only text uses. clip applies only to absolute and fixed boxes.
  const zoom = parseFloat(getComputedStyle(canvas).zoom) || 1;
  const hidden = el => {
    const r = rect(el), s = getComputedStyle(el);
    return (r.width / zoom <= 1 && r.height / zoom <= 1) || s.clipPath === 'inset(50%)'
      || (['absolute', 'fixed'].includes(s.position) && s.clip === 'rect(0px, 0px, 0px, 0px)');
  };
  const els = scanned.filter(el => el instanceof HTMLElement && !hidden(el));
  const rows = [], checked = {};
  for (const name of measures) checked[name] = 0;
  const selector = el => {
    const parts = [];
    for (let n = el; n && n !== canvas; n = n.parentElement) {
      let part = n.tagName.toLowerCase();
      if (n.id) { parts.unshift(part + '#' + n.id); break; }
      if (n.classList.length) part += '.' + Array.from(n.classList).slice(0, 3).join('.');
      const same = n.parentElement ? Array.from(n.parentElement.children).filter(c => c.tagName === n.tagName) : [];
      if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(n) + 1) + ')';
      parts.unshift(part);
      if (n === surface) break;
    }
    return parts.join(' > ');
  };
  const push = (measure, el, level, data, suffix) => rows.push(Object.assign({ measure, selector: selector(el) + (suffix || ''), level }, data));
  const disabled = el => el.matches(':disabled') || Boolean(el.closest('[aria-disabled="true"]'));
  const hasText = el => Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
  const FIELDS = ['INPUT', 'TEXTAREA', 'SELECT', 'OPTION', 'OPTGROUP', 'NOSCRIPT'];
  const texts = els.filter(el => !FIELDS.includes(el.tagName) && hasText(el));
  const TEXT_INPUTS = ['text', 'search', 'email', 'url', 'tel', 'password', 'number'];
  const canvas2d = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const parse = value => {
    canvas2d.clearRect(0, 0, 1, 1); canvas2d.fillStyle = '#000'; canvas2d.fillStyle = value; canvas2d.fillRect(0, 0, 1, 1);
    const d = canvas2d.getImageData(0, 0, 1, 1).data;
    return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
  };
  const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = c => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };

  if (measures.includes('contrast')) {
    const MEDIA = ['IMG', 'VIDEO', 'CANVAS', 'PICTURE', 'SVG', 'OBJECT', 'EMBED', 'IFRAME'];
    const layers = scanned.filter(el => MEDIA.includes(el.tagName.toUpperCase()) || getComputedStyle(el).backgroundImage !== 'none');
    const background = el => {
      let found = null;     // the walk goes on past the background: an ancestor's opacity still fades text and background
      for (let n = el; n; n = n.parentElement) {
        const s = getComputedStyle(n);
        if (parseFloat(s.opacity) < 1) return { why: 'an opacity below 1 applies to the text or one of its ancestors' };
        if (found) continue;
        if (s.backgroundImage !== 'none') return { why: 'a background image or gradient sits between the text and its background' };
        const c = parse(s.backgroundColor);
        if (c.a === 1) found = { color: c, css: s.backgroundColor };
        else if (c.a > 0) return { why: 'a translucent background color sits between the text and its background' };
      }
      return found || { why: 'no ancestor has an opaque background color' };
    };
    const textPoint = el => {
      let r = rect(el);
      const node = Array.from(el.childNodes).find(n => n.nodeType === 3 && n.textContent.trim());
      if (node) { const range = document.createRange(); range.selectNodeContents(node); r = range.getClientRects()[0] || r; }
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    };
    const targets = [];
    for (const el of els) {
      if (disabled(el)) continue;
      const s = getComputedStyle(el);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if (el.tagName === 'INPUT' && !TEXT_INPUTS.includes(el.type)) continue;
        if (el.value) targets.push({ el, color: s.webkitTextFillColor || s.color, suffix: '' });
        else if (el.placeholder) targets.push({ el, color: getComputedStyle(el, '::placeholder').color, suffix: '::placeholder' });
      } else if (el.tagName === 'SELECT') targets.push({ el, color: s.webkitTextFillColor || s.color, suffix: '' });
      else if (texts.includes(el)) targets.push({ el, color: s.webkitTextFillColor || s.color, suffix: '' });
    }
    for (const { el, color, suffix } of targets) {
      const s = getComputedStyle(el);
      const size = parseFloat(s.fontSize), weight = parseInt(s.fontWeight, 10) || 400;
      const limitRatio = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
      const base = { color, fontPx: round(size), fontWeight: weight, limit: limitRatio };
      const skip = reason => push('contrast', el, 'unmeasured', Object.assign({ reason }, base), suffix);
      const fg = parse(color);
      if (fg.a < 1) { skip('the text color is translucent'); continue; }
      const bg = background(el);
      if (bg.why) { skip(bg.why); continue; }
      const p = textPoint(el);
      if (layers.some(l => !l.contains(el) && rect(l).left <= p.x && p.x <= rect(l).right && rect(l).top <= p.y && p.y <= rect(l).bottom)) {
        skip('a media element or background image sits behind the text'); continue;
      }
      checked.contrast++;
      const got = ratio(fg, bg.color);
      if (got < limitRatio) push('contrast', el, 'fail', Object.assign({ ratio: round(got), background: bg.css }, base), suffix);
    }
  }

  const native = el => {
    const t = el.tagName;
    return t === 'BUTTON' || t === 'SELECT' || t === 'TEXTAREA' || t === 'SUMMARY' || (t === 'A' && el.hasAttribute('href'))
      || (t === 'INPUT' && el.type !== 'hidden');
  };
  const tabbable = el => { const v = el.getAttribute('tabindex'); return v !== null && parseInt(v, 10) >= 0; };

  if (measures.includes('target-size')) {
    const ROLES = ['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem', 'menuitemcheckbox', 'menuitemradio', 'option',
      'switch', 'slider', 'spinbutton', 'combobox', 'textbox', 'searchbox', 'treeitem'];
    const narrow = rect(canvas).width < 600;
    for (const el of els) {
      if (!(native(el) || tabbable(el) || ROLES.includes((el.getAttribute('role') || '').toLowerCase()))) continue;
      const inRun = el.tagName === 'A' && getComputedStyle(el).display === 'inline'
        && Array.from(el.parentNode.childNodes).some(n => n.nodeType === 3 && n.textContent.trim());
      if (inRun) continue;
      checked['target-size']++;
      const w = round(rect(el).width), h = round(rect(el).height);
      if (w < 24 || h < 24) push('target-size', el, 'fail', { width: w, height: h, limit: 24 });
      else if (narrow && (w < 44 || h < 44)) push('target-size', el, 'note', { width: w, height: h, limit: 44 });
    }
  }

  // text cut by its own box: what text-clip reports, and what text-split leaves to it
  const clips = (el, which) => { const o = getComputedStyle(el)['overflow' + which]; return o === 'hidden' || o === 'clip'; };
  const beyond = (inner, outer, which) => which === 'X'
    ? rect(inner).right > rect(outer).right + 1 || rect(inner).left < rect(outer).left - 1
    : rect(inner).bottom > rect(outer).bottom + 1 || rect(inner).top < rect(outer).top - 1;
  const cuts = el => FIELDS.includes(el.tagName) ? [] : ['X', 'Y'].filter(which => clips(el, which))
    .map(which => ({ which, scroll: which === 'X' ? el.scrollWidth : el.scrollHeight, client: which === 'X' ? el.clientWidth : el.clientHeight }))
    .filter(({ which, scroll, client }) => scroll > client + 1
      && (hasText(el) || texts.some(t => t !== el && el.contains(t) && beyond(t, el, which))));

  if (measures.includes('text-clip')) {
    for (const el of els) {
      if (FIELDS.includes(el.tagName)) continue;
      for (const { which, scroll, client } of cuts(el))
        push('text-clip', el, 'fail', { kind: 'overflow-' + which.toLowerCase(), overflow: scroll - client, scroll, client, limit: 1 });
      if (hasText(el) || texts.some(t => el.contains(t))) checked['text-clip']++;
    }
    for (const el of els) {
      if (el.tagName !== 'INPUT' || !TEXT_INPUTS.includes(el.type) || el.value || !el.placeholder) continue;
      const s = getComputedStyle(el);
      canvas2d.font = [s.fontStyle, s.fontWeight, s.fontSize, s.fontFamily].join(' ');
      const text = s.textTransform === 'uppercase' ? el.placeholder.toUpperCase() : el.placeholder;
      const wide = canvas2d.measureText(text).width + (parseFloat(s.letterSpacing) || 0) * text.length;
      const content = el.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
      checked['text-clip']++;
      if (wide > content + 1)
        push('text-clip', el, 'fail', { kind: 'placeholder', overflow: round(wide - content), scroll: round(wide), client: round(content), limit: 1 }, '::placeholder');
    }
  }

  if (measures.includes('text-split')) {
    // A figure, or a CJK word of 2 to 6 characters in a text of 24 characters or fewer, drawn on more than one line.
    // A text node belongs to the nearest box that is not display:inline, so a token may cross an inline child
    // (a currency span or a <br>) but never a block, cell or flex item. Text that text-clip reports is left to it.
    const CODES = 'USD|HKD|MOP|CNY|RMB|TWD|JPY|KRW|SGD|MYR|THB|PHP|IDR|VND|INR|AUD|NZD|CAD|EUR|GBP|CHF|SEK|NOK|DKK|BRL|MXN|ZAR|AED|SAR';
    const UNITS = String.raw`%|\u2030|\uFF05|\u00B0[CF]?|[\u4E07\u842C\u4EBF\u5104]?(?:[\u6E2F\u7F8E]?\u5143|\u5713|\u5706|\u5186|\uC6D0)`
      + String.raw`|[\u4E07\u842C\u4EBF\u5104]|(?:${CODES}|kg|g|km|m|cm|mm|ml|mL|L|h|hr|hrs|min|s|ms|kWh|kW|W|GB|MB|KB|TB|px|pt|x|k|K|M|bn)(?![A-Za-z])`;
    const MONTH = String.raw`(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?`;
    const DATE = [String.raw`\d{4}\u5E74\d{1,2}\u6708(?:\d{1,2}\u65E5)?`, String.raw`\d{1,2}\u6708\d{1,2}\u65E5`,
      String.raw`\d{4}[-/.]\d{1,2}[-/.]\d{1,2}`, String.raw`\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}`,
      String.raw`${MONTH}\s+\d{1,2}(?:,?\s+\d{4})?`, String.raw`\d{1,2}\s+${MONTH}(?:,?\s+\d{4})?`].join('|');
    const SIGN = String.raw`[+\-\u2212\u00B1]`;
    const FIGURE = new RegExp(String.raw`(?<![A-Za-z\d])(?:${DATE}|${SIGN}?(?:(?:[A-Z]{0,2}\p{Sc}|(?:${CODES})(?![A-Za-z]))\s*)?`
      + String.raw`${SIGN}?\d+(?:[,.'\u00A0\u202F]\d+)*(?:\s*(?:${UNITS}))?)`, 'gu');
    const CJK = /^[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\u30FC]{2,6}$/u;
    const segmenters = new Map();
    const segmenter = box => {
      const tag = box.closest('[lang]'), lang = (tag && tag.getAttribute('lang')) || undefined;
      if (!segmenters.has(lang)) {
        let made;
        try { made = new Intl.Segmenter(lang, { granularity: 'word' }); } catch (_) { made = new Intl.Segmenter(undefined, { granularity: 'word' }); }
        segmenters.set(lang, made);
      }
      return segmenters.get(lang);
    };
    const cut = els.filter(el => cuts(el).length);
    const range = document.createRange();
    for (const box of els) {
      if (FIELDS.includes(box.tagName) || getComputedStyle(box).display === 'inline' || cut.some(c => c.contains(box))) continue;
      const nodes = [];
      let text = '';
      const visit = parent => {
        for (const n of parent.childNodes) {
          if (n.nodeType === 3) {
            if (getComputedStyle(n.parentElement).visibility === 'visible') { nodes.push({ node: n, at: text.length }); text += n.data; }
          } else if (n.nodeType === 1) {
            if (n instanceof HTMLElement && getComputedStyle(n).display === 'inline') visit(n);
            else text += '\uFFFC';     // not white space, so no token runs across another box
          }
        }
      };
      visit(box);
      if (!text.trim()) continue;
      const locate = i => {
        const hit = nodes.find(({ node, at }) => at <= i && i < at + node.data.length);
        return hit ? [hit.node, i - hit.at] : null;
      };
      const lines = (start, end) => {
        let count = 0, last = null;
        for (let i = start, size; i < end; i += size) {
          size = text.codePointAt(i) > 0xffff ? 2 : 1;
          const at = /\s/.test(text[i]) ? null : locate(i);
          if (!at) continue;
          range.setStart(at[0], at[1]);
          range.setEnd(at[0], Math.min(at[1] + size, at[0].data.length));
          const r = Array.from(range.getClientRects()).find(c => c.height > 0);
          if (!r) continue;
          if (!last || Math.abs(r.top + r.bottom - last.top - last.bottom) / 2 >= Math.max(r.height, last.height) / 2) count++;
          last = r;
        }
        return count;
      };
      const measure = (start, end) => {
        checked['text-split']++;
        const count = lines(start, end);
        if (count < 2) return;
        const first = locate(start), final = locate(end - 1);
        range.setStart(first[0], first[1]);
        range.setEnd(final[0], final[1] + 1);
        const common = range.commonAncestorContainer;
        push('text-split', common.nodeType === 3 ? common.parentElement : common, 'fail',
          { token: text.slice(start, end).replace(/\s+/g, ' '), lines: count, limit: 1 });
      };
      const figures = [];
      for (const found of text.matchAll(FIGURE)) {
        if ([...found[0].replace(/\s/g, '')].length < 2) continue;
        figures.push([found.index, found.index + found[0].length]);
        measure(found.index, found.index + found[0].length);
      }
      if ([...text.replace(/[\s\uFFFC]+/g, ' ').trim()].length > 24) continue;
      for (const { segment, index, isWordLike } of segmenter(box).segment(text)) {
        const end = index + segment.length;
        if (isWordLike && CJK.test(segment) && !figures.some(([a, b]) => index < b && a < end)) measure(index, end);
      }
    }
  }

  if (measures.includes('focus-visible')) {
    const forced = axis === 'forced-colors';
    const state = s => ({
      outline: s.outlineStyle === 'none' ? 'none' : s.outlineStyle + ' ' + s.outlineWidth,
      border: ['Top', 'Right', 'Bottom', 'Left'].map(side => s['border' + side + 'Width'] + ' ' + s['border' + side + 'Style'] + ' ' + s['border' + side + 'Color']).join(' '),
      shadow: s.boxShadow, background: s.backgroundColor,
    });
    const settleTransitions = el => { getComputedStyle(el).outlineWidth; el.getAnimations().forEach(a => { try { a.finish(); } catch (_) {} }); };
    // the Tab press that sets keyboard modality may have landed on a product control: read every "before" unfocused
    const held = document.activeElement;
    if (held && held !== document.body && held.blur) { held.blur(); settleTransitions(held); }
    for (const el of els) {
      if (!(native(el) || tabbable(el)) || disabled(el)) continue;
      const before = state(getComputedStyle(el));
      el.focus({ preventScroll: true });
      if (document.activeElement !== el) { push('focus-visible', el, 'unmeasured', { reason: 'the element did not take focus' }); continue; }
      settleTransitions(el);
      const s = getComputedStyle(el), after = state(s);
      checked['focus-visible']++;
      const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0;
      const changed = (forced ? ['border'] : ['border', 'shadow', 'background']).filter(key => before[key] !== after[key]);
      if (!outline && !changed.length)
        push('focus-visible', el, 'fail', { outline: after.outline, limit: forced ? 'an outline, or a border change' : 'an outline, or a border, box-shadow or background-color change' });
      el.blur();
      settleTransitions(el);
    }
  }

  // text whose size is compared across the 200% axis: text elements and the form controls that render text
  const sized = texts.concat(els.filter(el => el.tagName === 'TEXTAREA' || el.tagName === 'SELECT'
    || (el.tagName === 'INPUT' && TEXT_INPUTS.includes(el.type))));

  if (measures.includes('text-growth') && baseFonts) {
    const zoom = canvas.style.zoom === '2' ? 2 : 1;
    for (const el of sized) {
      const was = baseFonts[selector(el)];
      if (!was) continue;
      checked['text-growth']++;
      const now = parseFloat(getComputedStyle(el).fontSize);
      const grew = now * zoom / was;
      if (grew < 1.9) push('text-growth', el, 'fail', { baseFontPx: round(was), fontPx: round(now), zoom, ratio: round(grew), limit: 1.9 });
    }
  }

  const sizes = {};
  if (fonts) for (const el of sized) sizes[selector(el)] = parseFloat(getComputedStyle(el).fontSize);
  return { rows, checked, incomplete: all.length > limit, fonts: fonts ? sizes : null };
};

async function start(request) {
  for (const [name, file] of Object.entries(request.files)) pages[name] = fs.readFileSync(file);
  surfaceDefaults = request.surfaceDefaults;
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
  await context.addInitScript(reviewerFocusSites => {
    const record = form => window.__pdhForm && window.__pdhForm({ action: String(form.action), method: String(form.method) });
    addEventListener('submit', event => { event.preventDefault(); record(event.target); }, true);
    HTMLFormElement.prototype.submit = function () { record(this); };
    const shown = panel => panel.isConnected && !panel.hidden && Boolean(panel.getClientRects().length)
      && getComputedStyle(panel).visibility === 'visible';
    let focusStep = null;
    window.__pdhFocusTrace = {
      begin(target, [step, destination, activate]) {
        const root = target.closest('[data-ui-surface]');
        const layers = new Map();
        if (activate) {
          const unique = panel => panel.id && document.querySelectorAll('#' + CSS.escape(panel.id)).length === 1;
          for (const opener of root.querySelectorAll('button[data-product-menu],button[data-product-tab],button[data-product-disclosure]')) {
            const id = opener.getAttribute('aria-controls');
            const panel = id && document.getElementById(id);
            const peers = Array.from(root.querySelectorAll('button[aria-controls]'))
              .filter(el => el.getAttribute('aria-controls') === id);
            if (!panel || !unique(panel) || panel.closest('[data-ui-surface]') !== root
                || panel.contains(opener) || peers.length !== 1) continue;
            const expanded = opener.getAttribute(opener.hasAttribute('data-product-tab') ? 'aria-selected' : 'aria-expanded');
            layers.set(panel, { id, panel, opener, visible: shown(panel), open: expanded === 'true' && shown(panel),
              entry: opener === target });
          }
          for (const panel of document.querySelectorAll('dialog,[role="dialog"],[role="alertdialog"]')) {
            if (!unique(panel) || panel.closest('[data-ui-surface]')?.dataset.uiSurface !== destination) continue;
            if (layers.has(panel)) layers.get(panel).entry = true;
            else layers.set(panel, { id: panel.id, panel, visible: shown(panel), open: false, entry: true });
          }
        }
        const returnLayers = Array.from(layers.values()).filter(layer => layer.open && layer.panel.contains(target));
        // Snapshot the containing panels before activation, from innermost outward.
        returnLayers.sort((a, b) => a.panel.contains(b.panel) ? 1 : b.panel.contains(a.panel) ? -1 : 0);
        // What the destination surface already showed, so the end of the operation can tell new content from old.
        const shownBefore = new WeakSet();
        if (activate && step === 'operation')
          for (const surface of document.querySelectorAll('[data-ui-surface]'))
            if (surface.dataset.uiSurface === destination)
              for (const el of [surface, ...surface.querySelectorAll('*')]) if (shown(el)) shownBefore.add(el);
        focusStep = { step, target, destination, layers: Array.from(layers.values()), returnLayers, shownBefore };
      },
      outcome() {
        const layers = focusStep?.layers || [];
        return {
          entered: layers.filter(layer => layer.entry && !layer.visible && shown(layer.panel)
            && layer.panel.contains(document.activeElement)).map(layer => layer.id),
          returned: (focusStep?.returnLayers || []).filter(layer => !shown(layer.panel)
            && layer.opener === document.activeElement).map(layer => layer.id),
        };
      },
      end() {
        const active = document.activeElement, target = focusStep?.target;
        const surface = active && active !== document.body ? active.closest('[data-ui-surface]') : null;
        const inDestination = Boolean(surface) && surface.dataset.uiSurface === focusStep?.destination && shown(active);
        // A control that was hidden while it held focus keeps no focus the user can see.
        const targetShown = Boolean(target) && shown(target);
        return { ...this.outcome(), onTarget: targetShown && active === target, targetShown, inDestination,
          fresh: inDestination && !focusStep?.shownBefore?.has(active),
          closedPanel: (focusStep?.returnLayers || []).some(layer => !shown(layer.panel)) };
      },
    };
    addEventListener('focusin', event => {
      if (window.__pdhNoFocusLog) return;     // a measured-accessibility pass moves focus on purpose
      const el = event.target;
      if (!el?.closest('[data-ui-surface]')) return;
      const id = el && el.dataset && (el.dataset.navigationId || el.dataset.controlId);
      const opener = el && el.matches && el.matches('button[data-product-menu],button[data-product-tab],button[data-product-disclosure]')
        ? el.getAttribute('aria-controls') : null;
      const layers = focusStep?.layers || [];
      // These facts must be captured synchronously, before a focus handler continues.
      const returned = (focusStep?.returnLayers || []).find(layer => layer.opener === el && !shown(layer.panel));
      const entered = layers.find(layer => layer.entry && !layer.visible && shown(layer.panel) && layer.panel.contains(el));
      // Only the direct focus call in an exact supported runtime is reviewer setup.
      const caller = String(new Error().stack).split('\n').map(line =>
        line.match(/(https:\/\/hifi\.invalid\/pkg\/[^()\s]+):(\d+):(\d+)/)).find(Boolean);
      const site = caller && reviewerFocusSites[decodeURIComponent(new URL(caller[1]).pathname.slice(5))];
      const reviewer = Boolean(site && Number(caller[2]) === site.line && Number(caller[3]) === site.column);
      window.__pdhFocus({ control: id || null, opener, supporting: el.getAttribute('data-control-for'),
        step: focusStep?.step, target: focusStep?.target === el,
        returned: returned?.id || null, entered: entered?.id || null, reviewer });
    }, true);
  }, request.reviewerFocusSites || {});
  page = await context.newPage();
  await page.exposeFunction('__pdhForm', info => { events.forms.push(info); });
  await page.exposeFunction('__pdhFocus', info => { if (observingFocus) events.focus.push(info); });
  context.on('page', popup => { if (popup !== page) { events.popups.push({ url: popup.url() }); popup.close().catch(() => {}); } });
  page.on('dialog', dialog => {
    events.console.push({ source: 'dialog', level: 'error', message: 'dialog ' + dialog.type() + ': ' + dialog.message() });
    dialog.dismiss().catch(() => {});
  });
  const cdp = await context.newCDPSession(page);
  await cdp.send('Log.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Page.enable');
  cdp.on('Page.navigatedWithinDocument', event => {
    if (observingNavigation) events.navigation.push({ url: event.url, method: 'GET', resourceType: 'document', allowlisted: true });
  });
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
  observingNavigation = false;
  observingFocus = false;
  page.setDefaultTimeout(timeoutMs);
  page.setDefaultNavigationTimeout(timeoutMs);
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

// One interaction attempt: reload the page, reset target/source state through the
// reviewer shell, then activate the declared product control by click or keyboard. The
// destination surface/state must apply, and focus must end where assessOperationFocus accepts.
const FEEDBACK_SNAPSHOT = surfaceId => {
  const surface = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surfaceId);
  return surface ? JSON.stringify([surface.outerHTML, Array.from(surface.querySelectorAll('input,select,textarea'))
    .map(el => [el.value, el.checked, el.selectedIndex])]) : null;
};

// A preparatory opener takes focus once and may move it once into its newly opened panel.
async function assessOpenerFocus(step, from) {
  const outcome = await page.evaluate(() => window.__pdhFocusTrace.outcome()).catch(() => ({ entered: [] }));
  const focus = events.focus.slice(from).filter(event => !event.reviewer);
  const entered = Boolean(focus[1]?.entered) && outcome.entered.includes(focus[1].entered);
  return { correct: (focus.length === 1 || (focus.length === 2 && entered))
      && focus.every(event => event.step === step) && focus[0]?.target === true, next: events.focus.length };
}

// An operation is judged by where focus ends. The control takes focus first and may keep it. While the
// control is still shown, focus may move only into content the activation showed. When a panel that held
// the control closed, focus returns to that panel's opener or moves into new content. When the control went
// for another reason, focus stays inside the destination surface. A page the operation loads keeps its own
// initial focus.
async function assessOperationFocus(from, loadsPage) {
  const focus = events.focus.slice(from).filter(event => !event.reviewer);
  if (focus[0]?.target !== true || focus[0]?.step !== 'operation')
    return { problem: 'did not start on the control', entered: null, returned: null };
  const end = loadsPage ? null : await page.evaluate(() => window.__pdhFocusTrace.end()).catch(() => null);
  const problem = loadsPage ? null : !end ? 'could not be read' : end.onTarget ? null
    : end.targetShown ? (end.fresh ? null : 'left the shown control for content that was already shown')
    : end.closedPanel ? (end.returned.length || end.fresh ? null : "did not return to the closed panel's opener")
    : end.inDestination ? null : 'was lost';
  return { problem, entered: (!problem && end?.entered[0]) || null, returned: (!problem && end?.returned[0]) || null };
}

async function interact(request) {
  const problems = [];
  if (request.kind === 'state' && request.surface === request.destination.surface && request.state === request.destination.state)
    return { problems: ['state interaction needs a different destination state'], visible: false, focusCorrect: false };
  const timeout = request.timeoutMs;
  // Every attempt starts from a fresh load of its source page. Product scripts keep state and can move the
  // browser on their own, so an attempt must not depend on the ones before it: the result is the same wherever
  // a parallel run starts it.
  try { await openPage(request.page, timeout); }
  catch (_) { return { problems: ['page did not open: ' + request.page], pageOpenFailed: true, visible: false, focusCorrect: false }; }
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
  let visible = null, focusCorrect = null, focusProblem = null, arrivedTo = null, observed = null;
  if (!problems.length) {
    observingFocus = true;
    let focusCursor = events.focus.length, openerFocusCorrect = true;
    const surface = '[data-ui-surface=' + quote(request.surface) + ']';
    const attached = page.locator(surface + ' [data-navigation-id=' + quote(request.control) + '],'
      + surface + ' [data-control-id=' + quote(request.control) + ']');
    const product = page.locator(surface + ' [data-navigation-id=' + quote(request.control) + ']:visible,'
      + surface + ' [data-control-id=' + quote(request.control) + ']:visible');
    const opened = [];
    if (await product.count() === 0 && await attached.count() > 0) {
      const chain = await attached.evaluateAll(list => {
        for (const el of list) {
          const surface = el.closest('[data-ui-surface]');
          const target = surface.closest('[data-hifi-canvas]').dataset.hifiTarget;
          const buttons = Array.from(surface.querySelectorAll('button[data-product-menu],button[data-product-tab],button[data-product-disclosure]'));
          const panels = [];
          let reachable = true;
          for (let panel = el; panel; panel = panel.parentElement) {
            if ((panel.hasAttribute('data-hifi-state-view') && panel.dataset.hifiStateView !== surface.dataset.hifiState)
                || (panel.hasAttribute('data-responsive-target') && panel.dataset.responsiveTarget !== target)) {
              reachable = false; break;
            }
            const openers = panel !== el && panel !== surface && panel.id
              ? buttons.filter(button => button.getAttribute('aria-controls') === panel.id
                && button.closest('[data-ui-surface]') === surface && !panel.contains(button)) : [];
            const opener = openers.length === 1 && document.querySelectorAll('#' + CSS.escape(panel.id)).length === 1
              ? openers[0] : null;
            const style = getComputedStyle(panel);
            const hidesVisibility = (style.visibility === 'hidden' || style.visibility === 'collapse')
              && (!panel.parentElement || getComputedStyle(panel.parentElement).visibility !== style.visibility);
            // Author CSS often hides a closed details element's content as well; its summary still reveals it.
            const closedDetails = panel.parentElement?.closest('details:not([open])');
            const inClosedDetails = Boolean(closedDetails)
              && !closedDetails.querySelector(':scope > summary')?.contains(panel);
            if ((panel.hidden || style.display === 'none' || hidesVisibility) && !opener && !inClosedDetails) {
              reachable = false; break;
            }
            if (opener)
              panels.unshift({ panel: panel.id, index: buttons.indexOf(opener), selected: opener.hasAttribute('data-product-tab') });
            // A closed native details element is a disclosure that its own summary opens.
            const summary = panel.tagName === 'DETAILS' && panel !== el ? panel.querySelector(':scope > summary') : null;
            if (summary && !panel.open && !summary.contains(el)) {
              const unique = panel.id && document.querySelectorAll('#' + CSS.escape(panel.id)).length === 1;
              panels.unshift({ panel: unique ? panel.id : null,
                details: Array.from(surface.querySelectorAll('details')).indexOf(panel) });
            }
            if (panel === surface) break;
          }
          if (reachable) return panels;
        }
        return [];
      });
      const buttons = page.locator(surface + ' button[data-product-menu],'
        + surface + ' button[data-product-tab],' + surface + ' button[data-product-disclosure]');
      for (const step of chain) {
        // A details without a unique id is named by its place among the surface's details elements.
        const isDetails = typeof step.details === 'number';
        const name = step.panel || 'details:' + step.details;
        const panel = step.panel ? page.locator('[id=' + quote(step.panel) + ']') : page.locator(surface + ' details').nth(step.details);
        const open = () => isDetails ? panel.evaluate(el => el.open) : panel.isVisible();
        if (await open()) continue;
        const opener = isDetails ? panel.locator(':scope > summary') : buttons.nth(step.index);
        if (!await opener.isVisible()) { problems.push('declared opener is hidden: ' + name); break; }
        const focusStep = 'opener:' + opened.length;
        await opener.evaluate((el, setup) => window.__pdhFocusTrace.begin(el, setup), [focusStep, request.surface, true]);
        await opener.click({ timeout });
        opened.push(name);
        try {
          if (isDetails) await page.waitForFunction(el => el.open, await panel.elementHandle(), { timeout });
          else await panel.waitFor({ state: 'visible', timeout });
        } catch (_) { problems.push('declared opener did not reveal its panel: ' + name); break; }
        if ((isDetails ? !await open() : await opener.getAttribute(step.selected ? 'aria-selected' : 'aria-expanded') !== 'true')
            || !await panel.isVisible()) { problems.push('declared opener did not reveal its panel: ' + name); break; }
        const focus = await assessOpenerFocus(focusStep, focusCursor);
        openerFocusCorrect = openerFocusCorrect && focus.correct;
        focusCursor = focus.next;
      }
    }
    const instances = await product.count();
    observed = { instances, ...(opened.length ? { openers: opened } : {}) };
    if (instances < 1) problems.push('product control is missing or hidden; no instance is reachable: ' + request.control);
    else {
      const unselected = instances > 1 ? await product.evaluateAll(list => list.findIndex(el => {
        const selected = ['aria-pressed', 'aria-selected', 'aria-checked'].some(name => el.getAttribute(name) === 'true');
        const current = el.getAttribute('aria-current');
        return !selected && (!current || current === 'false');
      })) : 0;
      const instanceIndex = Math.max(0, unselected);
      observed.instanceIndex = instanceIndex;
      const handle = product.nth(instanceIndex);
      const stateHref = request.destinationPage + '#hifi-state=' + encodeURIComponent(request.destination.surface)
        + '/' + encodeURIComponent(request.destination.state);
      const navigateHrefs = [stateHref];
      if (request.destination.state === surfaceDefaults[request.destination.surface]) navigateHrefs.push(request.destinationPage);
      if (request.kind === 'navigate' && !await attached.evaluateAll((list, hrefs) =>
          list.every(el => el.tagName === 'A' && hrefs.includes(el.getAttribute('href'))), navigateHrefs))
        return { problems: ['navigate controls must link to the declared page'], visible: false, focusCorrect: false, observed };
      if (request.kind === 'state' && request.page !== request.destinationPage) {
        const href = request.destinationPage + '#hifi-state=' + encodeURIComponent(request.destination.surface)
          + '/' + encodeURIComponent(request.destination.state);
        if (!await attached.evaluateAll((list, href) => list.every(el => el.tagName === 'A' && el.getAttribute('href') === href), href))
          return { problems: ['cross-page state controls must link to the declared page and state'], visible: false, focusCorrect: false };
      }
      visible = await handle.isVisible();
      const field = await handle.evaluate(el => {
        if (el.tagName === 'SELECT') return 'select';
        if (el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT'
            && ['text', 'search', 'email', 'url', 'tel', 'password'].includes(el.type))) return 'text';
        return null;
      });
      if (field && (!await handle.isEnabled() || await handle.getAttribute('readonly') !== null))
        return { problems: ['data-entry control is disabled or read-only'], visible, focusCorrect: false, observed };
      // A control disabled in the declared source state (natively or by aria-disabled) cannot be activated, and
      // a click on it waits out the action limit: name it instead.
      if (await handle.evaluate(el => el.disabled === true || el.getAttribute('aria-disabled') === 'true'))
        return { problems: ['the control is disabled in ' + request.state + '; start the operation from the state that '
          + 'enables it, or declare the step that enables it first'], visible, focusCorrect: false, observed };
      let pressedFocused = null;
      let before = null;
      await handle.evaluate((el, setup) => window.__pdhFocusTrace.begin(el, setup), ['operation', request.destination.surface, false]);
      if (request.trigger === 'keyboard' || request.kind === 'feedback') {
        await handle.focus({ timeout });
        pressedFocused = await handle.evaluate(el => el === document.activeElement);
      }
      if (request.kind === 'feedback') {
        await page.evaluate(SETTLE, { cap: Math.min(timeout, 2000), margin: 50 });
        before = await page.evaluate(FEEDBACK_SNAPSHOT, request.surface);
      }
      await handle.evaluate((el, setup) => window.__pdhFocusTrace.begin(el, setup), ['operation', request.destination.surface, true]);
      observingNavigation = request.kind === 'navigate';
      if (field) {
        if (request.trigger !== 'keyboard') await handle.click({ timeout });
        const arrivedAfterClick = request.trigger !== 'keyboard'
          && (request.surface !== request.destination.surface || request.state !== request.destination.state)
          && await page.evaluate(destination => {
            const surface = Array.from(document.querySelectorAll('[data-ui-surface]'))
              .find(el => el.dataset.uiSurface === destination.surface);
            return Boolean(surface) && !surface.hidden && surface.dataset.hifiState === destination.state;
          }, request.destination);
        if (field === 'text' && !arrivedAfterClick) {
          const probe = await handle.inputValue() === 'HiFi probe' ? 'HiFi entry' : 'HiFi probe';
          await handle.press('ControlOrMeta+A', { timeout });
          await handle.pressSequentially(probe, { timeout });
        } else if (field === 'select' && !arrivedAfterClick) {
          const option = await handle.evaluate(el => {
            const enabled = Array.from(el.options).map((o, index) => ({ o, index }))
              .filter(({ o }) => !o.disabled && !o.hidden && !o.closest('optgroup[disabled]'));
            const next = enabled.find(({ index }) => index > el.selectedIndex)
              || enabled.slice().reverse().find(({ index }) => index < el.selectedIndex);
            return next ? { index: next.index, direction: next.index > el.selectedIndex ? 'ArrowDown' : 'ArrowUp' } : null;
          });
          if (!option) problems.push('select control has no different enabled option');
          else if (request.trigger === 'keyboard') await handle.press(option.direction, { timeout });
          else await handle.selectOption({ index: option.index }, { timeout });
        }
      } else if (request.trigger === 'keyboard') {
        const tag = await handle.evaluate(el => el.tagName.toLowerCase());
        await page.keyboard.press(tag === 'a' || tag === 'area' ? 'Enter' : ' ');
      } else {
        await handle.click({ timeout });
      }
      if (request.kind === 'feedback') {
        try {
          await page.waitForFunction(({ surfaceId, before }) => {
            const surface = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surfaceId);
            return surface && JSON.stringify([surface.outerHTML, Array.from(surface.querySelectorAll('input,select,textarea'))
              .map(el => [el.value, el.checked, el.selectedIndex])]) !== before;
          }, { surfaceId: request.surface, before }, { timeout: Math.min(timeout, 2000) });
        } catch (_) { problems.push('feedback did not change the source surface'); }
        const after = await page.evaluate(FEEDBACK_SNAPSHOT, request.surface);
        if (before && after) observed.change = { beforeSha256: sha(before), afterSha256: sha(after) };
      }
      // Loading a heavy page can take most of the action limit, so an attempt that loads a page keeps it.
      // A state change on the source page that has not applied after destinationWaitMs does not apply.
      const loadsPage = request.kind === 'navigate' || request.page !== request.destinationPage;
      try {
        await page.waitForFunction(([surface, state]) => {
          const el = Array.from(document.querySelectorAll('[data-ui-surface]')).find(n => n.dataset.uiSurface === surface);
          return Boolean(el) && !el.hidden && el.dataset.hifiState === state;
        }, [request.destination.surface, request.destination.state],
        { timeout: loadsPage ? timeout : Math.min(timeout, request.destinationWaitMs ?? timeout) });
      } catch (_) {
        problems.push('destination surface/state did not apply: ' + request.destination.surface + ' ' + request.destination.state);
      }
      const url = page.url();
      arrivedTo = url.startsWith(BASE) ? decodeURIComponent(new URL(url).pathname.slice('/pkg/'.length)) : null;
      if (request.kind === 'navigate') {
        if (!navigateHrefs.some(href => url === BASE + href)) problems.push('browser did not reach the declared navigation URL');
      } else if (request.kind === 'state' && request.page !== request.destinationPage) {
        const href = request.destinationPage + '#hifi-state=' + encodeURIComponent(request.destination.surface)
          + '/' + encodeURIComponent(request.destination.state);
        if (url !== BASE + href) problems.push('browser did not reach the declared state URL');
      }
      if (arrivedTo && arrivedTo !== currentPage) currentPage = arrivedTo;
      observingNavigation = false;
      const focus = await assessOperationFocus(focusCursor, loadsPage);
      focusProblem = !openerFocusCorrect ? 'did not stay on an opener or move into its panel'
        : request.trigger === 'keyboard' && !pressedFocused ? 'did not start on the control' : focus.problem;
      focusCorrect = !focusProblem;
      if (focusCorrect && focus.returned) observed.focusReturn = focus.returned;
      else if (focusCorrect && focus.entered) observed.focusEntry = focus.entered;
    }
  }
  return { problems, visible, focusCorrect, focusProblem, arrivedTo, observed };
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
  await page.evaluate(SET_CANVAS_WIDTH, request.widthPx || null);
  const settle = await page.evaluate(SETTLE, { cap: request.settleCapMs, margin: request.marginMs });
  if (request.a11y && request.a11y.only) return { problems, settle, probe: null, a11y: await measureA11y(request) };
  const probe = await page.evaluate(PROBE, {
    surfaceId: request.surface, state: request.state, limit: 400, reportLimit: 10, props: STYLE_PROPS,
  });
  if (!probe) return { problems: ['product surface not found: ' + request.surface], settle, probe: null };
  const result = {
    problems, settle,
    probe: {
      geometry: probe.geometry, rectsSha256: sha(probe.rects), styleSha256: sha(probe.styles),
      inputsSha256: sha(probe.inputs), incomplete: probe.incomplete,
    },
  };
  if (request.a11y) result.a11y = await measureA11y(request);
  return result;
}

// Measured accessibility never fails a case: a measurement that cannot run comes back as an error text.
// Focus is measured after one real Tab press, so :focus-visible rules apply, and is put back afterwards.
async function measureA11y(request) {
  const focus = request.a11y.measures.includes('focus-visible');
  let had = null;
  try {
    if (focus) {
      await page.evaluate(() => { window.__pdhNoFocusLog = true; });
      had = await page.evaluateHandle(() => document.activeElement);
      await page.keyboard.press('Tab');
    }
    return await page.evaluate(A11Y, Object.assign({ surfaceId: request.surface, limit: 400 }, request.a11y));
  } catch (error) {
    return { error: String((error && error.message) || error).split('\n')[0] };
  } finally {
    if (focus) {
      try {
        if (had) await had.evaluate(el => { if (el && el !== document.body && el.focus) el.focus({ preventScroll: true }); else if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); });
        await page.evaluate(() => { window.__pdhNoFocusLog = false; });
      } catch (_) {}
    }
  }
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
    // a reflow case leaves its inline width behind; the next pass must meet the declared widths again
    const canvas = document.querySelector('[data-hifi-canvas]');
    if (canvas) {
      canvas.style.removeProperty('width');
      if (zoom) canvas.style.setProperty('zoom', '2'); else canvas.style.removeProperty('zoom');
    }
  }, name === 'zoom-200');
  await page.evaluate(SET_CANVAS_WIDTH, null);
  return {};
}

// The reviewer pass, once per page after the interaction pass: one fresh open
// (the reviewer's stored selections are cleared first), the entry observations,
// the page-bound specimen source reads at the default target, the contract's
// viewport rows, and the entry-side specimen display reads. Only reviewer shell
// controls are clicked; no product control is touched.
async function reviewer(request) {
  const timeout = request.timeoutMs;
  const press = async (selector, name) => {
    const control = page.locator(selector);
    if (await control.count() !== 1) throw new Error('reviewer control missing: ' + name);
    if (await control.getAttribute('aria-pressed') !== 'true') await control.click({ timeout });
  };
  const selectSurface = async (surface, state) => {
    const selector = '[data-hifi-state-control=' + quote(state) + '][data-hifi-state-surface=' + quote(surface) + ']';
    const control = page.locator(selector);
    if (await control.count() !== 1) return;
    if (await control.isVisible()) await press(selector, state);
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
      await press('[data-hifi-target-control=' + quote(row.target) + ']', row.target);
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
    if (defaults.target) await press('[data-hifi-target-control=' + quote(defaults.target) + ']', defaults.target);
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
      reply = { id: message.id, ok: false, timedOut: error && error.name === 'TimeoutError',
        error: String((error && error.message) || error).split('\n')[0] };
    }
    observingFocus = false;
    reply.events = drain();
    process.stdout.write(JSON.stringify(reply) + '\n');
    if (message.op === 'close') process.exit(0);
  });
});
lines.on('close', () => { chain.then(() => (browser ? browser.close().catch(() => {}) : null)).then(() => process.exit(0)); });
"""


def reviewer_focus_sites(files):
    """Recognize only the heading-focus call in current or accepted historical bytes."""
    script_re = re.compile(r"<script\b[^>]*>(?P<body>[\s\S]*?)</script>", re.IGNORECASE)
    canonical = script_re.search(runtime_source()).group("body")
    trusted = {hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
               "854fc83eca20f90bbb976cd8555dba241018cf6adc891be6e7b604d011427597",
               "e18c759f9f7ecf10fd2798c07ca3d28ac709678b1066b3e7243bf83b8619e146"}
    sites = {}
    for name, path in files.items():
        html = path.read_text(encoding="utf-8")
        for script in script_re.finditer(html):
            body = script.group("body")
            if hashlib.sha256(body.encode("utf-8")).hexdigest() not in trusted:
                continue
            call = re.search(r"(?m)^(?P<indent>[ \t]*)heading\.focus\(\);[ \t]*$", body)
            if call:
                offset = script.start("body") + call.start() + len(call.group("indent")) + len("heading.")
                sites[name] = {"line": html.count("\n", 0, offset) + 1,
                               "column": offset - html.rfind("\n", 0, offset)}
    return sites


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
        self._lock, self._closed = threading.Lock(), False     # a closed driver never creates a process again

    def start(self):
        script = self.scratch / "driver.js"
        if not script.exists():
            script.write_text(DRIVER_JS, encoding="utf-8")
        self._lines = queue.Queue()
        with self._lock:        # close() waits here, so it either stops this process or stops this start
            if self._closed:
                raise DriverError("driver is closed")
            proc = self.proc = subprocess.Popen(
                [self.node, str(script), str(self.module)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._pump, args=(proc.stdout, self._lines), daemon=True).start()
        threading.Thread(target=self._pump, args=(proc.stderr, None), daemon=True).start()
        reply = self.call("start", timeout=90, files={n: str(p) for n, p in self.files.items()},
                          reviewerFocusSites=reviewer_focus_sites(self.files),
                          surfaceDefaults={row["id"]: next((s for s in row["states"] if not _is_na_state(s)), None)
                                           for row in json.loads(HIFI_MANIFEST_RE.search(
                                               self.files["index.html"].read_text(encoding="utf-8")).group("data"))["surfaces"]},
                          viewport={"width": 1920, "height": 1080}, colorScheme=self.color_scheme)
        self.environment = reply["result"]["environment"]

    def _pump(self, stream, sink):
        queue_out = sink
        try:
            for line in stream:
                if queue_out is not None:
                    queue_out.put(line)
                else:
                    self._stderr.append(line.rstrip())
        except (ValueError, OSError):     # stop() closed the pipe under us
            pass
        if queue_out is not None:
            queue_out.put(None)

    def call(self, op, timeout=CASE_TIMEOUT_S + 10, **fields):
        self._seq += 1
        proc = self.proc
        if proc is None:
            raise DriverError("driver is not running")
        try:
            # id and op go last so a payload field of the same name cannot clobber the reply correlation.
            proc.stdin.write(json.dumps({**fields, "op": op, "id": self._seq}) + "\n")
            proc.stdin.flush()
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
            error_type = DriverTimeout if reply.get("timedOut") else DriverError
            raise error_type(reply["error"], reply.get("events"))
        return reply

    def _tail(self):
        return " | ".join(self._stderr)[-400:] or "no driver output"

    def stop(self):
        with self._lock:
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

    def close(self):
        """Stop for good. A start or restart still creating its process either finishes first and is stopped here,
        or finds the driver closed and creates nothing."""
        with self._lock:
            self._closed = True
        self.stop()


def process_rows():
    """{pid: (parent pid, creation time)} of every Windows process; empty when the list cannot be read."""
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Get-CimInstance Win32_Process | ForEach-Object { '{0} {1} {2}' -f $_.ProcessId, $_.ParentProcessId, "
               "$(if ($_.CreationDate) { $_.CreationDate.ToFileTimeUtc() } else { 0 }) }"]
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False).stdout or ""
    except (OSError, subprocess.SubprocessError):
        return {}
    rows = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            rows[int(parts[0])] = (int(parts[1]), int(parts[2]))
    return rows


def descendants_first(rows, root):
    """``root`` and every process below it, deepest first, from ``process_rows()``.

    Windows keeps a dead parent's id on its children and gives that id to new processes, so `taskkill /T` can reach
    an unrelated program. Here a process is a child only when it started no earlier than its parent, and a root
    missing from the list has no known children."""
    if root not in rows:
        return [root]
    order, frontier = [root], [root]
    while frontier:
        parent = frontier.pop()
        born = rows[parent][1]
        for pid, (ppid, created) in rows.items():
            if ppid == parent and pid not in order and created >= born:
                order.append(pid)
                frontier.append(pid)
    return order[::-1]


PROCESS_TERMINATE, PROCESS_QUERY_LIMITED_INFORMATION, SYNCHRONIZE = 0x0001, 0x1000, 0x00100000
ERROR_INVALID_PARAMETER, STILL_ACTIVE, WAIT_OBJECT_0, END_WAIT_MS = 87, 259, 0, 5000


def windows_kernel32():
    """kernel32 with the calls ``end_process`` makes, typed. A HANDLE is pointer-sized."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle, dword, ok = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
    for name, restype, argtypes in (("OpenProcess", handle, [dword, ok, dword]),
                                    ("GetProcessTimes", ok, [handle] + [ctypes.POINTER(ctypes.c_uint64)] * 4),
                                    ("TerminateProcess", ok, [handle, ctypes.c_uint]),
                                    ("GetExitCodeProcess", ok, [handle, ctypes.POINTER(dword)]),
                                    ("WaitForSingleObject", dword, [handle, dword]),
                                    ("CloseHandle", ok, [handle])):
        function = getattr(kernel32, name)
        function.restype, function.argtypes = restype, argtypes
    return kernel32


def end_process(pid, created, kernel32):
    """Terminate ``pid`` only while it is the process ``process_rows()`` listed as created at ``created``.
    Return whether that process has ended.

    The identity check and the termination use one handle, and Windows gives no process's id to another while a
    handle to it is open. WMI keeps creation times to the microsecond: 10 FILETIME ticks."""
    handle = kernel32.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_INVALID_PARAMETER      # no process has this id any more
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *map(ctypes.pointer, times)):
            return False
        if abs(times[0].value - created) > 10:
            return times[0].value > created         # a later process has the id: the listed one has ended
        if kernel32.TerminateProcess(handle, 1):        # it starts the end; the wait sees it finish
            return kernel32.WaitForSingleObject(handle, END_WAIT_MS) == WAIT_OBJECT_0
        code = ctypes.c_uint32()                    # TerminateProcess refuses a process that has already exited
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.pointer(code))) and code.value != STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def kill_tree(proc):
    """Stop only the process we spawned and its children. Without a process list, only the process we spawned.

    The children end through ``end_process``, deepest first; the root last, through its own Popen handle."""
    if os.name == "nt":
        rows, kernel32 = process_rows(), windows_kernel32()
        for pid in descendants_first(rows, proc.pid)[:-1]:
            end_process(pid, rows[pid][1], kernel32)
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


def reflow_axis_cases(rows, sampled, widths):
    """The reflow-320 slice of the sampled cases: every sampled state once, at its surface's smallest target."""
    smallest = {row["id"]: smallest_target([str(t) for t in row["responsive"]["targets"]], widths) for row in rows}
    return [case for case in sampled if case.target == smallest[case.surface]]


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
        if kind == "feedback" and action["source"] != action["destination"]:
            raise UsageError(f"feedback interaction {ident} must keep its source surface and state")
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


def intermediate_plan(package, picks):
    """The axis sample's states of each surface (``picks``: {surface: states}), at the midpoint of each adjacent
    pair of numeric viewport targets."""
    cases = []
    for row in package.manifest["surfaces"]:
        widths = intermediate_widths(row)
        for state in picks.get(row["id"], ()) if widths else ():
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
                 intermediate=False, measure_a11y=False):
        self.driver, self.package, self.root, self.out_dir = driver, package, root, out_dir
        self.measure_a11y, self.a11y_cases, self.a11y_fonts = measure_a11y, {}, {}
        self.axes, self.carry, self.carry_source, self.derived = tuple(axes), carry or {}, carry_source, derived
        self.interactions = list(interactions)
        self.recapture, self.diff_against = recapture, diff_against
        self.settle_cap_ms, self.case_timeout_s = settle_cap_ms, case_timeout_s
        self.intermediate = intermediate
        self.transcript = {kind: [] for kind in TRANSCRIPT_KINDS}
        self.records, self.axis_records, self.interaction_records = {}, [], []
        self.page_reasons, self.unopened = {}, set()
        self.restarts, self.down, self.active_axis = 0, None, None     # down: why the browser is not running
        self.unit_restarts = {}     # restarts spent by each ("page", name) and each ("operation", interaction id)
        self.kinds = {row["id"]: row["responsive"].get("kind") for row in package.manifest["surfaces"]}
        self.reviewer_plan, self.reviewer_records = reviewer_plan(package), []
        self.cancel = None      # a threading.Event a parallel run sets to stop every worker between items

    # events: base-case events join the transcript; axis-case events only decide that case
    def absorb(self, events, page, keep=True):
        if keep:
            for kind in TRANSCRIPT_KINDS:
                self.transcript[kind].extend(dict(row, page=page) for row in events.get(kind, []))
        return event_reasons(events)

    def recover(self, page, unit=None):
        """Replace a hung browser and charge the restart to what hung: its page, or one operation on it."""
        unit = unit or ("page", page)
        self.unit_restarts[unit] = self.unit_restarts.get(unit, 0) + 1
        # Discard the hung browser even when its budget is spent: the fresh one serves the remaining work.
        if not self.fresh_browser() or self.page_blocked(page) or page in self.unopened:
            return
        try:
            reply = self.driver.call("open", page=page, timeoutMs=self.case_timeout_s * 1000)
            self.absorb(reply["events"], page, keep=not self.active_axis)
            if self.active_axis:
                self.driver.call("axis", name=self.active_axis)
        except DriverError as error:
            self.unopened.add(page)
            self.page_reasons[page] = [f"recovery page did not open: {error}"]
            self.absorb(error.events, page, keep=not self.active_axis)
            if isinstance(error, DriverTimeout):
                self.fresh_browser()

    def fresh_browser(self):
        """Restart the browser. One that cannot restart blocks the rest of the current page; the next page tries again."""
        self.restarts += 1
        try:
            self.driver.restart()
        except DriverError as error:
            self.down = f"browser driver could not restart: {error}"
            return False
        self.down = None
        return True

    def blocked(self, unit):
        """Why a page or an operation gets no more browser work: its own budget is spent, or the browser is down."""
        if self.unit_restarts.get(unit, 0) > MAX_RESTARTS:
            return f"{unit[0]} browser driver restart limit ({MAX_RESTARTS}) reached: {unit[1]}"
        return self.down

    def page_blocked(self, page):
        return self.blocked(("page", page))

    def run(self, cases):
        for page, page_cases in group_by_page(cases).items():
            self.run_page(page, page_cases)
        # The intermediate sweep is a width check; interactions and the reviewer object belong to the base output.
        if not self.intermediate:
            self.run_reviewer()

    def open_page(self, page):
        if self.down:       # the last restart failed: a new page starts from a fresh browser
            self.fresh_browser()
        if self.page_blocked(page) or page in self.unopened:       # a failed page stays failed in later phases
            return
        try:
            reply = self.driver.call("open", page=page, timeoutMs=self.case_timeout_s * 1000)
            self.page_reasons[page] = ["page load: " + r for r in self.absorb(reply["events"], page)]
        except DriverError as error:
            self.unopened.add(page)
            self.page_reasons[page] = [f"page did not open: {error}"] + ["page load: " + r for r in self.absorb(error.events, page)]
            if isinstance(error, DriverTimeout):
                self.recover(page)

    def run_page(self, page, cases):
        self.open_page(page)
        for case in cases:
            self.records[case.key] = self.observe(case)
        if self.measure_a11y:
            self.run_focus(page, self.sample_for(page, cases)[1])
        for axis, picked in self.axis_picks(page, cases):
            self.run_axis(page, axis, picked)
        self.run_interactions(page)

    def sample_for(self, page, cases):
        """(surface rows, axis sample) of one page, sampled from the geometry its base cases measured."""
        rows = [row for row in self.package.manifest["surfaces"] if row["page"] == page
                and any(c.surface == row["id"] for c in cases)]
        counts = {}
        for case in cases:
            geometry = self.records[case.key].get("geometry")
            if geometry:
                counts[(case.surface, case.state)] = max(counts.get((case.surface, case.state), 0), geometry["elementCount"])
        return rows, sample_axis_cases(rows, page, self.package.widths[page], counts, self.derived)

    def sampled_states(self, cases):
        """{surface: the axis sample's states}, from the base cases this runner measured."""
        picks = {}
        for page, page_cases in group_by_page(cases).items():
            for case in self.sample_for(page, page_cases)[1]:
                picks.setdefault(case.surface, {})[case.state] = None
        return {surface: list(states) for surface, states in picks.items()}

    def axis_picks(self, page, cases):
        """(axis, sampled cases) for one page."""
        if not self.axes:
            return []
        rows, sampled = self.sample_for(page, cases)
        return [(axis, reflow_axis_cases(rows, sampled, self.package.widths[page]) if axis == "reflow-320" else sampled)
                for axis in self.axes]

    def interaction_attempts(self, page):
        """(action, target, trigger) for every selected manifest interaction: a click at every source target and one
        keyboard activation, at the smallest source target."""
        return [(action, target, trigger) for action in self.interactions if action["page"] == page
                for target in action["targets"] for trigger in TRIGGERS
                if trigger == "click" or target == smallest_target(action["targets"])]

    def interaction_blocked(self, page):
        return (INTERACTIONS_UNOPENED if page in self.unopened
                else self.page_blocked(page))

    def run_interactions(self, page):
        """Click every selected manifest interaction at every source target; keyboard-activate it at the smallest."""
        for action, target, trigger in self.interaction_attempts(page):
            self.interaction_records.append(self.observe_interaction(action, target, trigger, self.interaction_blocked(page)))

    # A parallel run cuts the serial work into items: ("case" | "interaction" | "axis" | "reviewer", page, payload).
    def base_items(self, cases):
        """Weighted items for every base case and interaction, in the serial order. An interaction's attempts are one
        item, so its restart budget is spent in one browser, as in a serial run."""
        items = []
        for page, page_cases in group_by_page(cases).items():
            items += [(("case", page, case), 1) for case in page_cases]
            attempts = {}
            for attempt in self.interaction_attempts(page):
                attempts.setdefault(attempt[0]["id"], []).append(attempt)
            items += [(("interaction", page, group), len(group)) for group in attempts.values()]
        return items

    def axis_items(self, cases):
        """One item per page and axis, from the base records a first phase has merged into this runner."""
        items = []
        for page, page_cases in group_by_page(cases).items():
            if self.measure_a11y:
                sampled = self.sample_for(page, page_cases)[1]
                items.append((("focus", page, sampled), 1 + len(sampled)))
            items += [(("axis", page, (axis, picked)), 1 + len(picked)) for axis, picked in self.axis_picks(page, page_cases)]
        return items

    def reviewer_items(self):
        plan = self.reviewer_plan
        return [(("reviewer", page, page_plan), 3) for page, page_plan in plan["pages"].items()] if plan else []

    def run_items(self, items):
        """One worker's share in serial order. Each item has its page open first, as a serial run would."""
        current = None
        for kind, page, payload in items:
            if self.cancel is not None and self.cancel.is_set():
                return
            if page != current:
                self.open_page(page)
                current = page
            if kind == "case":
                self.records[payload.key] = self.observe(payload)
            elif kind == "interaction":
                for attempt in payload:
                    self.interaction_records.append(self.observe_interaction(*attempt, self.interaction_blocked(page)))
            elif kind == "axis":
                self.run_axis(page, *payload)
            elif kind == "focus":
                self.run_focus(page, payload)
            else:
                self.reviewer_records.append(self.observe_reviewer(page, payload))

    def spawn(self, driver):
        """A Runner with this one's options and none of its results, for one worker."""
        worker = copy.copy(self)
        worker.driver = driver
        worker.transcript = {kind: [] for kind in TRANSCRIPT_KINDS}
        worker.records, worker.axis_records, worker.interaction_records, worker.reviewer_records = {}, [], [], []
        worker.a11y_cases, worker.a11y_fonts = {}, dict(self.a11y_fonts)
        worker.page_reasons, worker.unopened = dict(self.page_reasons), set(self.unopened)
        worker.restarts, worker.down, worker.active_axis = 0, None, None
        worker.unit_restarts = dict(self.unit_restarts)
        return worker

    def adopt_unopened(self, failed):
        """Record the pages another worker could not open ({page: reasons}) as a serial run would have: every row this
        worker measured on such a page becomes the row an unopened page gives. A real failure keeps its own reasons."""
        for page, reasons in failed.items():
            if page in self.unopened:
                continue
            self.unopened.add(page)
            self.page_reasons[page] = reasons
            self.a11y_cases = {key: entry for key, entry in self.a11y_cases.items() if entry["case"].page != page}
            for record in [r for r in self.records.values() if r["page"] == page]:
                self.unopen(record, "FAIL", reasons)
            for record in [r for r in self.axis_records if r["page"] == page]:
                self.unopen(record, "BLOCKED", [axis_unopened(record["axis"])])
            for record in [r for r in self.interaction_records if r["page"] == page]:
                self.unopen(record, "BLOCKED", [INTERACTIONS_UNOPENED])
            for record in [r for r in self.reviewer_records if r["page"] == page]:
                self.unopen(record, "BLOCKED", [REVIEWER_UNOPENED])

    def unopen(self, record, result, reasons):
        """Rewrite one row as its page not having opened. A PASS loses what it measured (and its capture file);
        a row that already failed stays FAIL and keeps its own reasons after the page reasons."""
        if record["result"] == "BLOCKED":
            return
        own = [r for r in record["reasons"] if r not in reasons] if record["result"] == "FAIL" else []
        if record["result"] == "PASS":
            if record.get("capture"):
                (self.root / record["capture"]["path"]).unlink(missing_ok=True)
            for key in ("geometry", "settle", "renderFingerprint", "capture", "carriedFrom", "visible", "focusCorrect",
                        "arrived", "entry"):
                if key in record:
                    record[key] = None
            for key in ("viewport", "sources", "reads"):
                if key in record:
                    record[key] = []
            if "fingerprintIncomplete" in record:
                record["fingerprintIncomplete"] = False
            for key in ("pixelDiff", "observed"):
                record.pop(key, None)
        record["result"] = "FAIL" if record["result"] == "FAIL" else result
        record["reasons"] = list(reasons) + own

    def fold(self, worker):
        """Add a worker's results to this runner. Folding workers in order keeps every list in the serial order."""
        self.unopened |= worker.unopened
        for unit, count in worker.unit_restarts.items():
            self.unit_restarts[unit] = max(self.unit_restarts.get(unit, 0), count)
        for page, reasons in worker.page_reasons.items():
            if page in worker.unopened or page not in self.page_reasons:
                self.page_reasons[page] = reasons
        self.records.update(worker.records)
        self.a11y_cases.update(worker.a11y_cases)
        self.a11y_fonts.update(worker.a11y_fonts)
        self.axis_records += worker.axis_records
        self.interaction_records += worker.interaction_records
        self.reviewer_records += worker.reviewer_records
        for kind in TRANSCRIPT_KINDS:
            self.transcript[kind] += worker.transcript[kind]

    def observe_interaction(self, action, target, trigger, blocked=None):
        record = {"id": action["id"], "surface": action["source"]["surface"], "state": action["source"]["state"],
                  "target": target, "trigger": trigger, "page": action["page"], "kind": action["kind"],
                  "control": action["control"], "destination": action["destination"], "result": None,
                  "reasons": [], "visible": None, "focusCorrect": None, "arrived": None,
                  "startedAt": now_iso(), "finishedAt": None, "durationMs": None}
        began = time.perf_counter()
        reasons = record["reasons"]
        blocked = blocked or self.page_blocked(action["page"]) or self.blocked(("operation", action["id"]))
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
                                     trigger=trigger, timeoutMs=self.case_timeout_s * 1000,
                                     destinationWaitMs=DESTINATION_WAIT_S * 1000)
        except DriverTimeout as error:
            reasons.append(f"interaction timed out after {self.case_timeout_s}s")
            events, result = error.events, {}
            self.recover(action["page"], ("operation", action["id"]))     # a stuck operation spends only its own budget
        except DriverError as error:
            reasons.append(f"driver error: {error}")
            events, result = error.events, {}
        else:
            events, result = reply["events"], reply["result"]
            if result.get("pageOpenFailed"):
                self.unopened.add(action["page"])
                self.page_reasons[action["page"]] = list(result["problems"])
                self.recover(action["page"])
        # A navigate attempt's one arrival row becomes the documented navigation event; every other
        # navigation row stays in the transcript and fails the attempt.
        stray = list(events.get("navigation", []))
        crosses_page = action["kind"] == "state" and action["page"] != action["destinationPage"]
        if action["kind"] == "navigate" or crosses_page:
            urls = {DRIVER_BASE + action["destinationPage"]}
            urls.add(DRIVER_BASE + _hifi_state_href(action["destinationPage"], action["destination"]))
            arrived = [row for row in stray if row.get("url") in urls]
            if len(arrived) == 1:
                record["arrived"] = action["destinationPage"]
                stray.remove(arrived[0])
        for row in stray:
            reasons.append(f"navigation attempt: {row.get('url')}")
        for kind in ("console", "network", "popups", "forms"):
            self.transcript[kind].extend(dict(row, page=action["page"]) for row in events.get(kind, []))
        self.transcript["navigation"].extend(dict(row, page=action["page"]) for row in stray)
        reasons.extend(result.get("problems") or [])
        if result and not result.get("problems"):
            if result.get("visible") is not True:
                reasons.append("product control was not visible")
            if result.get("focusCorrect") is not True:
                reasons.append("product focus " + (result.get("focusProblem") or "was not observed"))
        record["visible"], record["focusCorrect"] = result.get("visible"), result.get("focusCorrect")
        if result.get("observed") is not None:
            record["observed"] = result["observed"]
        if action["kind"] == "navigate" or crosses_page:
            if record["arrived"] is None:
                reasons.append("the destination page did not load")
            elif result.get("arrivedTo") != action["destinationPage"]:
                reasons.append(f"the browser did not land on {action['destinationPage']}")

    def run_axis(self, page, axis, sampled):
        """One row per sampled case. An axis that cannot be applied gives BLOCKED rows, never none."""
        blocked = axis_unopened(axis) if page in self.unopened else self.page_blocked(page)
        if blocked is None:
            try:
                self.driver.call("axis", name=axis)
                self.active_axis = axis
            except DriverError as error:
                blocked = f"axis {axis} could not be set up: {error}"
        for case in sampled:
            self.axis_records.append(self.observe(replace(case, axis=axis), blocked=blocked))
        self.active_axis = None
        if page in self.unopened or self.page_blocked(page):
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
        blocked = blocked or self.page_blocked(case.page)
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

    def case_width(self, case):
        """The inline canvas width a case is driven at: 320 px for a reflow case, the midpoint for an intermediate one."""
        if case.axis == "reflow-320":
            return float(REFLOW_WIDTH_PX)
        return float(case.target) if self.intermediate else None

    def run_case(self, case, record):
        reasons, keep = record["reasons"], case.axis is None
        a11y = self.a11y_request(case)
        try:
            reply = self.driver.call("case", timeout=self.case_timeout_s + 10, surface=case.surface, state=case.state,
                                     target=self.shell_target(case), widthPx=self.case_width(case),
                                     settleCapMs=self.settle_cap_ms, marginMs=SETTLE_MARGIN_MS,
                                     timeoutMs=self.case_timeout_s * 1000, **({"a11y": a11y} if a11y else {}))
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
        if a11y:
            self.record_a11y(case, "case", a11y, result.get("a11y"))
        if self.intermediate:
            if abs(geometry["canvasWidth"] - float(case.target)) > WIDTH_TOLERANCE_PX:
                reasons.append(f"product canvas is {geometry['canvasWidth']}px wide, the intermediate width needs {case.target}px")
        elif case.axis == "reflow-320":
            if abs(geometry["canvasWidth"] - REFLOW_WIDTH_PX) > WIDTH_TOLERANCE_PX:
                reasons.append(f"product canvas is {geometry['canvasWidth']}px wide, the reflow-320 axis needs {REFLOW_WIDTH_PX}px")
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

    # Measured accessibility: observations kept next to the case records, never part of a case result.
    def a11y_request(self, case, measures=None):
        """The measurements the driver takes in this case's page visit, or None when there are none."""
        if not self.measure_a11y or self.intermediate:
            return None
        base_visit = measures is None and case.axis is None
        measures = list(measures or (A11Y_BASE if case.axis is None else A11Y_AXIS.get(case.axis, ())))
        if not measures:
            return None
        request = {"measures": measures, "axis": case.axis}
        if "text-growth" in measures:
            request["baseFonts"] = self.a11y_fonts.get(case.key)
        elif base_visit and "zoom-200" in self.axes:
            request["fonts"] = True       # the 200% axis compares each text with its size in this visit
        return request

    def record_a11y(self, case, kind, request, result):
        """Keep one visit's measurements; a visit that returned nothing (a fake or a failed driver) keeps nothing."""
        if result is None:
            return
        rows, measures = result.get("rows", []), request["measures"]
        if result.get("error"):
            rows = [{"measure": name, "selector": None, "level": "unmeasured",
                     "reason": f"the measurement failed: {result['error']}"} for name in measures]
        elif "text-growth" in measures and request.get("baseFonts") is None:
            rows = rows + [{"measure": "text-growth", "selector": None, "level": "unmeasured",
                            "reason": "the same case without the axis was not measured"}]
        elif result.get("fonts") is not None:
            self.a11y_fonts[case.key] = result["fonts"]
        self.a11y_cases[(kind, case.axis or "", case.key)] = {
            "case": case, "kind": kind, "measures": measures, "rows": rows, "checked": result.get("checked") or {},
            "incomplete": bool(result.get("incomplete")) and not result.get("error")}

    def run_focus(self, page, sampled):
        """Focus visibility on the axis sample in the base scheme: the page's own states, no screenshot, no result."""
        for case in sampled:
            if page in self.unopened or self.page_blocked(page):
                return
            request = dict(self.a11y_request(case, ("focus-visible",)), only=True)
            try:
                reply = self.driver.call("case", timeout=self.case_timeout_s + 10, surface=case.surface, state=case.state,
                                         target=self.shell_target(case), widthPx=self.case_width(case),
                                         settleCapMs=self.settle_cap_ms, marginMs=SETTLE_MARGIN_MS,
                                         timeoutMs=self.case_timeout_s * 1000, a11y=request)
            except DriverTimeout:
                self.recover(page)
                continue
            except DriverError:
                continue
            if not reply["result"]["problems"]:
                self.record_a11y(case, "focus", request, reply["result"].get("a11y"))

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
            if self.down:       # as open_page: each page tries a fresh browser after a failed restart
                self.fresh_browser()
            self.reviewer_records.append(self.observe_reviewer(page, page_plan))

    def observe_reviewer(self, page, page_plan):
        record = {"page": page, "result": None, "reasons": [], "entry": None, "viewport": [], "sources": [],
                  "reads": [], "startedAt": now_iso(), "finishedAt": None, "durationMs": None}
        began = time.perf_counter()
        reasons = record["reasons"]
        blocked = (REVIEWER_UNOPENED if page in self.unopened
                   else self.page_blocked(page))
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


# --- Parallel run -----------------------------------------------------------------
def partition(items, workers):
    """Cut weighted items into at most ``workers`` non-empty, contiguous shares.

    An item goes to the share its weight midpoint falls in. The result depends only on the items and the
    count, so a plan and a worker count always give the same shares."""
    total = sum(weight for _, weight in items)
    shares = [[] for _ in range(workers)]
    done = 0
    for item, weight in items:
        shares[(2 * done + weight) * workers // (2 * total)].append(item)
        done += weight
    return [share for share in shares if share]


class DriverPool:
    """Drivers made on demand; page and operation restart budgets survive phase changes."""

    def __init__(self, make_driver, package, root, scratch, color_scheme):
        self.make_driver, self.package, self.root, self.scratch = make_driver, package, root, Path(scratch)
        self.color_scheme = color_scheme
        self.drivers, self.started, self.state, self.threads = [], [], [], []
        self.cancel = threading.Event()

    def driver(self, index):
        while len(self.drivers) <= index:
            folder = self.scratch / f"worker-{len(self.drivers)}"
            folder.mkdir(parents=True, exist_ok=True)
            self.drivers.append(self.make_driver(self.package, self.root, folder, color_scheme=self.color_scheme))
            self.started.append(False)
            self.state.append((0, None, {}))
        return self.drivers[index]

    @property
    def restarts(self):
        return sum(restarts for restarts, _, _ in self.state)

    def run(self, shares, make_runner):
        """Run each share on its own driver and Runner at once; return the Runners in share order.

        A worker that raises stops the others between items. The first failure, in share order, is raised."""
        runners = [make_runner(self.driver(index)) for index in range(len(shares))]
        failures = [None] * len(shares)

        def work(index):
            runner = runners[index]
            try:
                runner.cancel = self.cancel
                runner.restarts, runner.down, previous_units = self.state[index]
                runner.unit_restarts = dict(getattr(runner, "unit_restarts", {}))
                for unit, count in previous_units.items():
                    runner.unit_restarts[unit] = max(runner.unit_restarts.get(unit, 0), count)
                if not self.started[index] or not runner.down:      # a down browser is retried by the first page
                    # A later phase gets a fresh browser: the reviewer shell keeps its selections in session
                    # storage, so a page opened after another phase's pages could arrive in the wrong state.
                    first = not self.started[index]
                    self.started[index] = True      # a driver that failed to start is still stopped at the end
                    try:
                        runner.driver.start() if first else runner.driver.restart()
                    except DriverError as error:
                        if first:
                            raise UsageError(f"browser could not start: {error}") from error
                        # As a failed recovery restart: the share's first page tries a fresh browser.
                        runner.down = f"browser driver could not restart: {error}"
                runner.run_items(shares[index])
            except BaseException as error:    # carried to the caller; the other workers stop
                failures[index] = error
                self.cancel.set()
            finally:
                self.state[index] = (runner.restarts, runner.down, dict(runner.unit_restarts))

        self.threads = [threading.Thread(target=work, args=(index,), daemon=True) for index in range(len(shares))]
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.join()
        for failure in failures:
            if failure is not None:
                raise failure
        return runners

    def close(self):
        """Stop every driver, all at once, on every exit path.

        A worker may still be inside start() or restart() when this runs, so the drivers are stopped a second
        time once the worker threads have ended. A driver with a close() also refuses any later start."""
        self.cancel.set()
        self.stop_all(lambda driver: getattr(driver, "close", driver.stop)())
        for thread in self.threads:
            thread.join(timeout=30)
        self.stop_all(lambda driver: driver.stop())

    def stop_all(self, stop):
        stoppers = [threading.Thread(target=stop, args=(driver,)) for driver in self.drivers]
        for thread in stoppers:
            thread.start()
        for thread in stoppers:
            thread.join(timeout=30)


def capture_parallel(pool, workers, runner, cases, intermediate_runner=None):
    """The run of ``runner`` (and the intermediate sweep of ``intermediate_runner``) on up to ``workers`` drivers.
    Returns the intermediate cases it ran.

    Phase one is every base case, interaction attempt and reviewer row, which depend on nothing. The axis passes
    and the intermediate sweep follow, because the busiest state of a surface comes from its measured base cases."""
    def phase(merged, items):
        shares = pool.run(partition(items, workers), merged.spawn)
        failed = {}
        for worker in shares:       # a page any worker could not open is unopened for all, with the first failure's reasons
            for page in worker.unopened:
                failed.setdefault(page, worker.page_reasons[page])
        for worker in shares:
            worker.adopt_unopened(failed)
            merged.fold(worker)

    phase(runner, runner.base_items(cases) + runner.reviewer_items())
    if runner.axes or runner.measure_a11y:
        phase(runner, runner.axis_items(cases))
    if intermediate_runner is None:
        return []
    intermediate_cases = intermediate_plan(runner.package, runner.sampled_states(cases))
    intermediate_runner.unopened, intermediate_runner.page_reasons = set(runner.unopened), dict(runner.page_reasons)
    intermediate_runner.unit_restarts = dict(runner.unit_restarts)
    phase(intermediate_runner, intermediate_runner.base_items(intermediate_cases))
    return intermediate_cases


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
        if "observed" in record:
            results[-1]["observed"] = record["observed"]
        if record["kind"] in {"navigate", "state"} and record["arrived"]:
            navigation.append({"id": record["id"], "target": record["target"], "trigger": record["trigger"],
                               "from": record["page"], "to": record["arrived"]})
    return results, navigation


def a11y_object(runner):
    """The sidecar's ``a11y`` object: every finding in one order whatever the worker count, what was cut or not run."""
    surfaces = runner.package.manifest["surfaces"]
    rows = {row["id"]: row for row in surfaces}
    pages = list(dict.fromkeys(row["page"] for row in surfaces))
    ids = list(rows)

    def rank(entry):
        case, row = entry["case"], rows[entry["case"].surface]
        return (pages.index(case.page), {"case": 0, "focus": 1}[entry["kind"]] if case.axis is None else 2,
                runner.axes.index(case.axis) if case.axis else -1, ids.index(case.surface),
                [str(s) for s in row["states"]].index(case.state), [str(t) for t in row["responsive"]["targets"]].index(case.target))

    summary = {name: {"checked": 0, "fail": 0, "note": 0, "unmeasured": 0} for name in A11Y_MEASURES}
    findings, incomplete = [], []
    for entry in sorted(runner.a11y_cases.values(), key=rank):
        case = entry["case"]
        where = {"surface": case.surface, "state": case.state, "target": case.target, "axis": case.axis or "base"}
        for row in entry["rows"]:
            rest = {key: value for key, value in row.items() if key not in ("measure", "selector")}
            findings.append(dict({"measure": row["measure"], **where, "selector": row["selector"]}, **rest))
            summary[row["measure"]][row["level"]] += 1
        for name in entry["measures"]:
            summary[name]["checked"] += entry["checked"].get(name, 0)
            if entry["incomplete"]:
                incomplete.append({"measure": name, **where, "incomplete": True})
    not_run = [{"measure": name, "axis": axis, "reason": f"axis {axis} was not requested; pass --axes {axis}"}
               for axis, names in A11Y_AXIS.items() if axis not in runner.axes for name in names]
    return {"summary": summary, "notRun": not_run, "incomplete": incomplete, "findings": findings}


def row_seconds(rows):
    """Measured browser seconds of some rows, summed over every worker: where a run's time went."""
    return round(sum(row.get("durationMs") or 0 for row in rows) / 1000, 1)


def a11y_line(a11y):
    """The one summary line: failures per measurement, and what did not run."""
    line = {name: a11y["summary"][name]["fail"] for name in A11Y_MEASURES}
    line["notes"] = sum(row["note"] for row in a11y["summary"].values())
    line["unmeasured"] = sum(row["unmeasured"] for row in a11y["summary"].values())
    line["incomplete"] = len(a11y["incomplete"])
    line["notRun"] = [f"{row['measure']} needs --axes {row['axis']}" for row in a11y["notRun"]]
    return line


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
    if runner.measure_a11y:
        sidecar["a11y"] = a11y_object(runner)
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
                        help="also capture each surface's axis-sample states at the midpoints between adjacent viewport targets into OUT/intermediate")
    parser.add_argument("--recapture-carried", action="store_true", help="new screenshot for carried cases too")
    parser.add_argument("--diff-against", type=Path, help="earlier --out directory for a pixel diff (needs Pillow)")
    parser.add_argument("--workers", type=int, default=1,
                        help=f"browsers to run at once, 1 to {MAX_WORKERS} (default 1); the same count splits the work the same way")
    parser.add_argument("--measure-a11y", action="store_true",
                        help="also measure contrast, target size, text clip, text split, focus visibility and text growth into the sidecar's a11y object")
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
    if not 1 <= args.workers <= MAX_WORKERS:
        raise UsageError(f"--workers must be from 1 to {MAX_WORKERS}")
    axes = [a for a in args.axes.split(",") if a]
    unknown = [a for a in axes if a not in AXES]
    if unknown:
        raise UsageError(f"unknown axis {unknown[0]}; choose from {', '.join(AXES)}")
    repeated = [a for index, a in enumerate(axes) if a in axes[:index]]
    if repeated:
        raise UsageError(f"axis {repeated[0]} is repeated; name each axis once")     # two passes would share capture names
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
    selected = {case.surface for case in cases}
    if args.intermediate and not any(intermediate_widths(row) for row in package.manifest["surfaces"] if row["id"] in selected):
        raise UsageError("--intermediate found no surface with two or more numeric viewport widths")
    intermediate_cases = []
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
        intermediate_runner, workers_used = None, None
        if args.workers == 1:
            driver = make_driver(package, root, scratch, color_scheme=color_scheme)
            try:
                try:
                    driver.start()
                except DriverError as error:
                    raise UsageError(f"browser could not start: {error}") from error
                runner = Runner(driver, package, root, out_dir, axes=axes, carry=carry, carry_source=carry_source,
                                derived=derived, interactions=interactions, recapture=args.recapture_carried,
                                diff_against=diff_against, measure_a11y=args.measure_a11y)
                runner.run(cases)
                if args.intermediate:
                    intermediate_cases = intermediate_plan(package, runner.sampled_states(cases))
                    intermediate_dir = out_dir / INTERMEDIATE_DIR
                    intermediate_dir.mkdir(parents=True, exist_ok=True)
                    intermediate_runner = Runner(driver, package, root, intermediate_dir, derived=derived, intermediate=True)
                    intermediate_runner.unopened = set(runner.unopened)
                    intermediate_runner.page_reasons = dict(runner.page_reasons)
                    intermediate_runner.unit_restarts = dict(runner.unit_restarts)
                    intermediate_runner.down = runner.down      # the shared browser may still be down
                    intermediate_runner.run(intermediate_cases)
                environment = dict(driver.environment, python=platform.python_version(), platform=platform.platform())
            finally:
                driver.stop()
            restarts = runner.restarts
        else:
            pool = DriverPool(make_driver, package, root, scratch, color_scheme)
            try:
                runner = Runner(None, package, root, out_dir, axes=axes, carry=carry, carry_source=carry_source,
                                derived=derived, interactions=interactions, recapture=args.recapture_carried,
                                diff_against=diff_against, measure_a11y=args.measure_a11y)
                if args.intermediate:
                    intermediate_dir = out_dir / INTERMEDIATE_DIR
                    intermediate_dir.mkdir(parents=True, exist_ok=True)
                    intermediate_runner = Runner(None, package, root, intermediate_dir, derived=derived, intermediate=True)
                intermediate_cases = capture_parallel(pool, args.workers, runner, cases, intermediate_runner)
                environment = dict(pool.drivers[0].environment, python=platform.python_version(),
                                   platform=platform.platform())
                workers_used, restarts = len(pool.drivers), pool.restarts
            finally:
                pool.close()
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
    if workers_used:
        options["workers"] = workers_used
    output, output_path, summary = build_outputs(runner, package, cases, root, out_dir, subject, started, finished,
                                                 environment, options)
    problems = validate_output(root, output_path, output)
    failed = (any(row["result"] != "PASS" for row in output["results"]) or summary["axisFail"]
              or summary["interactionsFail"]
              or bool(intermediate and (intermediate["fail"] or intermediate["interactionsFail"]
                                        or intermediate["findings"])))
    line = {"result": "invalid" if problems and not failed else ("FAIL" if failed else "PASS"),
            "output": output_path.relative_to(root).as_posix(), **summary,
            "restarts": restarts, "problems": problems[:5], "intermediate": intermediate,
            "seconds": {"cases": row_seconds(runner.records.values()), "interactions": row_seconds(runner.interaction_records),
                        "axes": row_seconds(runner.axis_records), "reviewer": row_seconds(runner.reviewer_records),
                        "intermediate": row_seconds(intermediate_runner.records.values()) if intermediate_runner else 0}}
    if args.measure_a11y:
        line["a11y"] = a11y_line(a11y_object(runner))
    print(json.dumps(line))
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
