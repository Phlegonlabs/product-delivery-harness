"""Fixed source-runtime motion chrome for ds-showcase/2 specimen books.

RUNTIME_FRAME runs in the plate head before any product script. It makes the
effective reduced-motion preference (system OR gallery request) visible to the
product's own matchMedia calls, tracks timers, observers and Element.animate
so Stop can halt them, and observes native evidence on the bound subject.
It never calls product functions, fabricates observer entries or animates.
RUNTIME_GALLERY remounts a plate as a fresh srcdoc realm for Replay, size and
reduced-motion changes and accepts only current-generation plate messages.
Legacy ds-showcase/1 constants in design_system_gallery_assets stay unchanged.
"""

INITIAL_MOUNT = '<script type="application/json" id="ds-mount">{"generation":0,"reduced":false,"target":null}</script>'

RUNTIME_CSS = """
.plate.runtime .status{border-left:3px solid var(--rule);padding:.15rem 0 .15rem .6rem;max-width:46rem}
.plate.runtime[data-ds-phase="playing"] .status{border-left-color:var(--proof)}
.plate.runtime[data-ds-phase="settled"] .status,.plate.runtime[data-ds-phase="reduced"] .status{border-left-color:var(--ink)}
.plate.runtime[data-ds-phase="stopped"] .status{border-left-style:dashed;border-left-color:var(--muted)}
.plate.runtime[data-ds-phase="invalid"] .status{border-left-color:#a3261b;color:var(--ink)}
"""

RUNTIME_FRAME = r"""(() => {
  "use strict";
  const read = id => JSON.parse(document.getElementById(id).textContent);
  const config = read("ds-frame-config");
  const mount = read("ds-mount");
  const target = typeof mount.target === "string" && config.targets.indexOf(mount.target) >= 0 ? mount.target : config.target;
  const generation = Number.isInteger(mount.generation) ? mount.generation : 0;
  const requested = mount.reduced === true;
  const LIMIT = 3000;
  const native = {
    match: window.matchMedia.bind(window), set: window.setTimeout.bind(window), clear: window.clearTimeout.bind(window),
    every: window.setInterval.bind(window), stopEvery: window.clearInterval.bind(window),
    frame: window.requestAnimationFrame.bind(window), cancelFrame: window.cancelAnimationFrame.bind(window),
    animate: Element.prototype.animate, IO: window.IntersectionObserver, RO: window.ResizeObserver
  };
  const now = () => Math.round(performance.now());
  const systemReduced = native.match("(prefers-reduced-motion: reduce)").matches;
  const reduced = systemReduced || requested;
  const sheet = document.querySelector("style[data-ds-reduced]");
  if (sheet && requested) sheet.media = "all";
  const QUERY = /^\(\s*prefers-reduced-motion\s*:\s*(reduce|no-preference)\s*\)$/i;
  const quiet = () => {};
  window.matchMedia = query => {
    const match = QUERY.exec(String(query).trim());
    if (!match) return native.match(query);
    return {media: String(query), matches: (match[1].toLowerCase() === "reduce") === reduced, onchange: null,
      addListener: quiet, removeListener: quiet, addEventListener: quiet, removeEventListener: quiet, dispatchEvent: () => false};
  };
  let stopped = false, subject = null, canvas = null, readyAt = null, seenAt = null, navigation = "", last = "";
  const timers = new Set(), loops = new Set(), frames = new Set(), observers = new Set(), entries = [], errors = [];
  window.setTimeout = (callback, delay, ...args) => {
    const id = native.set(() => { timers.delete(id); if (!stopped && typeof callback === "function") callback(...args); }, delay);
    timers.add(id);
    return id;
  };
  window.clearTimeout = id => { timers.delete(id); native.clear(id); };
  window.setInterval = (callback, delay, ...args) => {
    const id = native.every(() => { if (!stopped && typeof callback === "function") callback(...args); }, delay);
    loops.add(id);
    return id;
  };
  window.clearInterval = id => { loops.delete(id); native.stopEvery(id); };
  window.requestAnimationFrame = callback => {
    const id = native.frame(time => { frames.delete(id); if (!stopped) callback(time); });
    frames.add(id);
    return id;
  };
  window.cancelAnimationFrame = id => { frames.delete(id); native.cancelFrame(id); };
  for (const name of ["IntersectionObserver", "ResizeObserver", "MutationObserver"]) {
    const Native = window[name];
    if (typeof Native !== "function") continue;
    const Gated = function (callback, options) {
      const observer = new Native(function (...args) { if (!stopped) return callback.apply(this, args); }, options);
      observers.add(observer);
      return observer;
    };
    Gated.prototype = Native.prototype;
    window[name] = Gated;
  }
  const label = node => !node || !node.tagName ? "detached" :
    node.tagName.toLowerCase() + Array.from(node.classList || []).slice(0, 2).map(item => "." + item).join("");
  const within = node => Boolean(subject && node && node.isConnected && (node === subject || subject.contains(node)));
  function capture(animation, owner, css) {
    const effect = animation.effect;
    const timing = effect && effect.getComputedTiming ? effect.getComputedTiming() : {};
    const keyframes = effect && effect.getKeyframes ? effect.getKeyframes() : [];
    const properties = new Set();
    for (const frame of keyframes) for (const key of Object.keys(frame))
      if (["offset", "computedOffset", "easing", "composite"].indexOf(key) < 0) properties.add(key);
    const entry = {animation, owner, css, inside: undefined, pseudo: (effect && effect.pseudoElement) || "",
      name: css ? String(animation.animationName || "") : "", duration: Number(timing.duration), delay: Number(timing.delay) || 0,
      iterations: Number(timing.iterations), active: Number(timing.activeDuration), keyframes: keyframes.length,
      properties: Array.from(properties).sort().join(","), at: now(), done: false, cancelled: false, progress: null, progressed: false};
    animation.finished.then(() => { entry.done = true; }, () => { entry.cancelled = true; });
    entries.push(entry);
    return entry;
  }
  Element.prototype.animate = function (keyframes, options) {
    const animation = native.animate.call(this, keyframes, options);
    if (stopped) animation.pause();
    else if (config.mechanism === "waapi") capture(animation, this, false);
    return animation;
  };
  function sample() {
    if (config.mechanism === "css-animation" && typeof CSSAnimation === "function") {
      for (const animation of document.getAnimations()) {
        if (animation instanceof CSSAnimation && animation.effect && !entries.some(item => item.animation === animation))
          capture(animation, animation.effect.target, true);
      }
    }
    for (const entry of entries) {
      if (entry.inside === undefined && subject) entry.inside = within(entry.owner);
      const timing = entry.animation.effect ? entry.animation.effect.getComputedTiming() : {};
      const mark = timing.progress === null || timing.progress === undefined ? null : (timing.currentIteration || 0) + timing.progress;
      if (entry.progress !== null && mark !== null && mark !== entry.progress) entry.progressed = true;
      if (mark !== null) entry.progress = mark;
      if (entry.animation.playState === "finished") entry.done = true;
    }
  }
  const structural = entry => Number.isFinite(entry.active) && entry.active > 0 && entry.keyframes > 0 &&
    (!entry.css || (entry.duration > 0 && Number.isFinite(entry.iterations) && entry.name !== "" &&
      ["", "::before", "::after"].indexOf(entry.pseudo) >= 0));
  function evaluate() {
    if (stopped) return "stopped";
    if (errors.length) return "invalid";
    if (readyAt === null) return "pending";
    if (!subject) return "invalid";
    const relevant = entries.filter(entry => entry.inside);
    if (reduced) return relevant.length ? "invalid" : "reduced";
    if (config.activation === "viewport" && relevant.some(entry => seenAt === null || entry.at + 1 < seenAt)) return "invalid";
    const valid = relevant.filter(structural);
    const start = config.activation === "viewport" ? seenAt : readyAt;
    if (!valid.length) return start !== null && now() - start > LIMIT ? "invalid" : "pending";
    if (valid.some(entry => !entry.done && !entry.cancelled)) return "playing";
    return valid.every(entry => entry.done || entry.progressed) ? "settled" : "invalid";
  }
  function measure() {
    const box = canvas || document.body;
    return box ? Math.ceil(box.getBoundingClientRect().bottom + window.scrollY) : 0;
  }
  function report() {
    sample();
    const relevant = entries.filter(entry => entry.inside);
    const body = {type: "ds-runtime", id: config.id, generation, phase: evaluate(), target, reduced, systemReduced, requested,
      mechanism: config.mechanism, activation: config.activation, inView: seenAt !== null, ignored: entries.length - relevant.length,
      evidence: relevant.slice(0, 40).map(entry => ({owner: label(entry.owner), pseudo: entry.pseudo, name: entry.name,
        duration: entry.duration, delay: entry.delay, iterations: Number.isFinite(entry.iterations) ? entry.iterations : -1,
        keyframes: entry.keyframes, properties: entry.properties, at: entry.at, done: entry.done, progressed: entry.progressed})),
      error: errors.length ? errors[0] : "", navigation, height: measure(),
      timing: {ready: readyAt, seen: seenAt, first: relevant.length ? relevant[0].at : null}};
    const text = JSON.stringify(body);
    if (text === last) return;
    last = text;
    parent.postMessage(body, "*");
  }
  function tick() { report(); if (!stopped) native.set(tick, 50); }
  function halt() {
    if (stopped) return;
    sample();
    stopped = true;
    timers.forEach(id => native.clear(id)); loops.forEach(id => native.stopEvery(id)); frames.forEach(id => native.cancelFrame(id));
    timers.clear(); loops.clear(); frames.clear();
    observers.forEach(observer => observer.disconnect());
    for (const animation of document.getAnimations()) animation.pause();
    if (document.body) document.body.inert = true;
    report();
  }
  window.addEventListener("error", event => { errors.push(String(event.message || "error").slice(0, 160)); });
  window.addEventListener("unhandledrejection", event => {
    const reason = event.reason;
    errors.push(String(reason && reason.message ? reason.message : reason).slice(0, 160));
  });
  for (const type of ["click", "pointerdown", "keydown", "input", "change", "submit"]) {
    document.addEventListener(type, event => { if (stopped) { event.stopImmediatePropagation(); event.preventDefault(); } }, true);
  }
  document.addEventListener("click", event => {
    const link = event.target.closest ? event.target.closest("a[href]") : null;
    if (link && !link.getAttribute("href").startsWith("#")) { event.preventDefault(); navigation = link.getAttribute("href").slice(0, 120); }
  }, true);
  document.addEventListener("submit", event => event.preventDefault(), true);
  document.addEventListener("animationstart", () => { if (stopped) for (const animation of document.getAnimations()) animation.pause(); }, true);
  window.addEventListener("message", event => {
    const data = event.data;
    if (event.source !== parent || !data || typeof data !== "object" || data.type !== "ds-runtime-stop") return;
    if (data.id === config.id && data.generation === generation) halt();
  });
  document.addEventListener("DOMContentLoaded", () => {
    canvas = document.querySelector("[data-hifi-canvas]");
    if (canvas) canvas.setAttribute("data-hifi-target", target);
    for (const view of document.querySelectorAll("[data-hifi-state-view]")) {
      const only = view.getAttribute("data-responsive-target");
      view.hidden = view.getAttribute("data-hifi-state-view") !== config.state || (only !== null && only !== target);
    }
    for (const node of document.querySelectorAll("[data-ds-motion-subject]"))
      if (node.getAttribute("data-ds-motion-subject").split(" ").indexOf(target) >= 0) subject = node;
    // entry.time is when the browser computed the intersection, before any observer callback ran.
    if (subject && typeof native.IO === "function")
      new native.IO(items => { for (const item of items) if (item.isIntersecting && seenAt === null) seenAt = Math.floor(item.time); }).observe(subject);
    if (typeof window.connectProductControls === "function") { try { window.connectProductControls(document); } catch (_) {} }
    readyAt = now();
    if (typeof native.RO === "function") new native.RO(report).observe(canvas || document.body);
    tick();
  }, {once: true});
})();"""

RUNTIME_GALLERY = r"""(() => {
  "use strict";
  const OPEN = '<script type="application/json" id="ds-mount">', CLOSE = "<\/script>";
  const INITIAL = OPEN + '{"generation":0,"reduced":false,"target":null}' + CLOSE;
  const PHASES = ["pending", "playing", "settled", "reduced", "stopped", "invalid"];
  const plates = new Map();
  for (const frame of document.querySelectorAll("iframe[data-ds-runtime-frame]")) {
    const source = frame.getAttribute("srcdoc") || "";
    const id = frame.dataset.dsFrame;
    if (source.indexOf(INITIAL) < 0) continue;
    plates.set(id, {frame, source, generation: 0, stopWanted: -1, target: frame.dataset.dsRuntimeDefault, figure: frame.closest("figure"),
      status: document.querySelector('[data-ds-status="' + id + '"]')});
  }
  if (!plates.size) return;
  const toggle = document.querySelector("[data-ds-reduced-toggle]");
  const system = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  const clip = (value, size) => String(value === undefined || value === null ? "" : value).slice(0, size);
  function show(plate, phase, text) {
    if (plate.figure) plate.figure.setAttribute("data-ds-phase", phase);
    if (plate.status) plate.status.textContent = text;
  }
  function mount(plate) {
    plate.generation += 1;
    show(plate, "pending", "Pending at target " + clip(plate.target, 32) + ": loading a fresh source frame.");
    const requested = Boolean(toggle && toggle.getAttribute("aria-pressed") === "true");
    const state = JSON.stringify({generation: plate.generation, reduced: requested, target: plate.target});
    plate.frame.srcdoc = plate.source.replace(INITIAL, OPEN + state + CLOSE);
  }
  function describe(data) {
    const evidence = Array.isArray(data.evidence) ? data.evidence.slice(0, 40) : [];
    const at = " at target " + clip(data.target, 32);
    const count = evidence.length + (evidence.length === 1 ? " source animation" : " source animations");
    const kinds = Array.from(new Set(evidence.map(item => item && (item.name || item.properties)).filter(Boolean).map(item => clip(item, 40)))).slice(0, 4).join("; ");
    const owners = Array.from(new Set(evidence.map(item => item && clip(item.owner, 40) + clip(item.pseudo, 10)))).slice(0, 3).join(", ");
    const link = data.navigation ? " Product link to " + clip(data.navigation, 120) + " stays on this plate." : "";
    if (data.phase === "pending") return (data.activation === "viewport" && !data.inView
      ? "Waiting" + at + ": the bound subject has not entered the viewport." : "Pending" + at + ": waiting for source motion on the bound subject.") + link;
    if (data.phase === "playing") return "Playing" + at + ": " + count + " on " + owners + " (" + kinds + ")." + link;
    if (data.phase === "settled") return "Settled" + at + ": " + count + " on " + owners + " (" + kinds + ") finished; the source end state is shown." + link;
    if (data.phase === "reduced") return "Reduced motion" + at + (data.systemReduced ? " (system preference)" : " (gallery request)") +
      ": no source motion ran; the source reduced-motion state is shown." + link;
    if (data.phase === "stopped") return "Stopped" + at + ": timers, observers and animations are halted. Replay starts a fresh source frame.";
    return "Invalid" + at + ": " + (data.error ? "source script error: " + clip(data.error, 120) : "no valid source motion was observed on the bound subject.");
  }
  window.addEventListener("message", event => {
    const data = event.data;
    if (!data || typeof data !== "object" || data.type !== "ds-runtime" || typeof data.id !== "string") return;
    const plate = plates.get(data.id);
    if (!plate || event.source !== plate.frame.contentWindow || data.generation !== plate.generation || PHASES.indexOf(data.phase) < 0) return;
    if (Number.isFinite(data.height)) plate.frame.style.height = Math.min(Math.max(Math.ceil(data.height), 40), 4000) + "px";
    show(plate, data.phase, describe(data));
    if (plate.stopWanted === plate.generation && data.phase !== "stopped") halt(plate);
  });
  function halt(plate) {
    plate.stopWanted = plate.generation;
    if (plate.frame.contentWindow)
      plate.frame.contentWindow.postMessage({type: "ds-runtime-stop", id: plate.frame.dataset.dsFrame, generation: plate.generation}, "*");
  }
  document.addEventListener("click", event => {
    const button = event.target.closest ? event.target.closest("button") : null;
    if (!button) return;
    if (button.hasAttribute("data-ds-reduced-toggle")) { for (const plate of plates.values()) mount(plate); return; }
    const plate = plates.get(button.dataset.dsFor || "");
    if (!plate) return;
    if (button.dataset.dsRuntime === "replay") mount(plate);
    else if (button.dataset.dsRuntime === "stop") halt(plate);
    else if (button.dataset.dsRuntimeTarget) {
      plate.target = button.dataset.dsRuntimeTarget;
      const width = Number(button.dataset.dsWidth);
      if (width) plate.frame.style.width = width + "px";
      for (const peer of plate.figure.querySelectorAll("button[data-ds-runtime-target]")) peer.setAttribute("aria-pressed", String(peer === button));
      mount(plate);
    }
  });
  if (system && system.addEventListener) system.addEventListener("change", () => { for (const plate of plates.values()) mount(plate); });
})();"""
