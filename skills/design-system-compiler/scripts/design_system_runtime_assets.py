"""Fixed source-runtime motion chrome for ds-showcase/2 specimen books.

RUNTIME_FRAME runs in the plate head before any product script. It makes the
effective reduced-motion preference (system OR gallery request) visible to the
product's own matchMedia calls, tracks timers, observers and Element.animate
so Stop can halt them, gates Animation playback calls once stopped, and
credits an effect only after a sampled visible, subject-owned rendered change.
RUNTIME_BOOT follows the copied markup and precedes the first product script:
it selects the requested target and state view so product code starts there.
They never call product functions, fabricate observer entries or animate.
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
    animate: Element.prototype.animate, IO: window.IntersectionObserver, RO: window.ResizeObserver,
    style: window.getComputedStyle.bind(window), cancel: window.Animation && Animation.prototype.cancel
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
  let stopped = false, booted = false, subject = null, canvas = null, readyAt = null, seenAt = null, navigation = "", last = "";
  let violation = "";
  const timers = new Set(), loops = new Set(), frames = new Set(), observers = new Set(), entries = [], errors = [];
  // Stop gates the native playback lifecycle of every Animation (retained, returned or constructed) in this realm.
  const gate = (owner, key) => {
    const method = owner && owner.prototype && owner.prototype[key];
    if (typeof method === "function") owner.prototype[key] = function (...args) { if (!stopped) return method.apply(this, args); };
  };
  for (const key of ["play", "reverse", "finish", "cancel", "updatePlaybackRate"]) gate(window.Animation, key);
  gate(window.AnimationEffect, "updateTiming");
  gate(window.KeyframeEffect, "setKeyframes");
  for (const key of ["currentTime", "startTime", "playbackRate"]) {
    const field = window.Animation && Object.getOwnPropertyDescriptor(Animation.prototype, key);
    if (field && field.set) Object.defineProperty(Animation.prototype, key, {configurable: true, enumerable: field.enumerable,
      get: field.get, set(value) { if (!stopped) field.set.call(this, value); }});
  }
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
  // Rendered values are compared canonically so equal computed values (none vs translateX(0)) cannot fake change.
  const SKIP = ["offset", "computedOffset", "easing", "composite"];
  const round = list => Array.from(list, number => Math.round(number * 1000) / 1000).join(",");
  const MATRIX = {transform: text => text, translate: text => (text.split(" ").length > 2 ? "translate3d(" : "translate(") + text.split(" ").join(",") + ")",
    scale: text => (text.split(" ").length > 2 ? "scale3d(" : "scale(") + text.split(" ").join(",") + ")", rotate: text => "rotate(" + text + ")"};
  function canonical(property, value) {
    const text = String(value === undefined || value === null ? "" : value).trim().replace(/\s+/g, " ");
    if (property === "opacity" && text !== "" && Number.isFinite(Number(text))) return String(Math.round(Number(text) * 1000) / 1000);
    if (MATRIX[property] && typeof DOMMatrixReadOnly === "function") {
      try { return round(new DOMMatrixReadOnly(text === "none" ? undefined : MATRIX[property](text)).toFloat64Array()); } catch (_) { return text; }
    }
    return text;
  }
  // Supported evidence: standard properties whose keyframe values differ, or that fill an implicit end from the underlying value.
  function profile(keyframes) {
    const values = new Map();
    for (const frame of keyframes) {
      const offset = Number(frame.computedOffset !== undefined ? frame.computedOffset : frame.offset);
      for (const key of Object.keys(frame)) {
        if (SKIP.indexOf(key) >= 0) continue;
        const property = key === "cssFloat" ? "float" : key.replace(/[A-Z]/g, letter => "-" + letter.toLowerCase());
        if (property.startsWith("--")) continue;
        if (!values.has(property)) values.set(property, {seen: new Set(), ends: new Set()});
        values.get(property).seen.add(canonical(property, frame[key]));
        if (offset === 0 || offset === 1) values.get(property).ends.add(offset);
      }
    }
    return values;
  }
  function varying(keyframes) {
    return Array.from(profile(keyframes)).filter(([, item]) => item.ends.size < 2 || item.seen.size > 1).map(([property]) => property);
  }
  function implicit(keyframes) {
    return Array.from(profile(keyframes)).filter(([, item]) => item.ends.size < 2).map(([property]) => property);
  }
  // An implicit end renders the underlying value, so another effect on the same owner and property could lend it a change.
  // That property never earns credit; this is bounded fail-closed evidence, not a composite-order engine.
  function shared(entry) {
    if (!entry.implicit.length) return [];
    const others = entries.filter(item => item !== entry && item.owner === entry.owner && item.pseudo === entry.pseudo).map(item => item.varying);
    const live = entry.owner.getAnimations ? entry.owner.getAnimations({subtree: true}) : [];
    for (const animation of live) {
      const effect = animation.effect;
      if (animation === entry.animation || !effect || effect.target !== entry.owner || (effect.pseudoElement || "") !== entry.pseudo) continue;
      others.push(Array.from(profile(effect.getKeyframes ? effect.getKeyframes() : []).keys()));
    }
    return entry.implicit.filter(property => others.some(list => list.indexOf(property) >= 0));
  }
  function renderable(entry) {
    const node = entry.owner;
    if (!node || !node.isConnected || !node.getClientRects || !node.getClientRects().length) return false;
    if (typeof node.checkVisibility === "function" && !node.checkVisibility({visibilityProperty: true})) return false;
    if (native.style(node).visibility !== "visible") return false;
    if (!entry.pseudo) return true;
    const style = native.style(node, entry.pseudo);
    return style.display !== "none" && style.content !== "none" && style.content !== "normal";
  }
  function capture(animation, owner, css) {
    const effect = animation.effect;
    const timing = effect && effect.getComputedTiming ? effect.getComputedTiming() : {};
    const keyframes = effect && effect.getKeyframes ? effect.getKeyframes() : [];
    const properties = new Set();
    for (const frame of keyframes) for (const key of Object.keys(frame))
      if (SKIP.indexOf(key) < 0) properties.add(key);
    const entry = {animation, owner, css, inside: false, pseudo: (effect && effect.pseudoElement) || "",
      name: css ? String(animation.animationName || "") : "", duration: Number(timing.duration), delay: Number(timing.delay) || 0,
      iterations: Number(timing.iterations), active: Number(timing.activeDuration), keyframes: keyframes.length,
      properties: Array.from(properties).sort().join(","), varying: varying(keyframes), implicit: implicit(keyframes), blocked: [],
      at: now(), done: false, cancelled: false, baseline: null, visible: false, changed: false};
    // The finish microtask runs before product continuations, so a filled end state finished early is still sampled.
    animation.finished.then(() => { entry.done = true; observe(entry); }, () => { entry.cancelled = true; });
    entries.push(entry);
    observe(entry);
    return entry;
  }
  // Credit needs a sample where the effect is in effect, live-owned by the subject, renderable and visibly different.
  function observe(entry) {
    if (!subject || !within(entry.owner)) return;
    entry.inside = true;
    const timing = entry.animation.effect ? entry.animation.effect.getComputedTiming() : {};
    if (timing.progress === null || timing.progress === undefined || !entry.varying.length || !renderable(entry)) return;
    const lent = shared(entry).filter(property => entry.blocked.indexOf(property) < 0);
    // A newly shared property revokes any credit it may have lent and restarts sampling on the remaining properties.
    if (lent.length) { entry.blocked = entry.blocked.concat(lent); entry.baseline = null; entry.changed = false; }
    const own = entry.varying.filter(property => entry.blocked.indexOf(property) < 0);
    if (!own.length) return;
    const style = native.style(entry.owner, entry.pseudo || null);
    const values = own.map(property => style.getPropertyValue(property)).filter(value => value !== "");
    if (!values.length) return;
    const mark = own.map(property => canonical(property, style.getPropertyValue(property))).join("|");
    entry.visible = true;
    if (entry.baseline === null) entry.baseline = mark;
    else if (mark !== entry.baseline) entry.changed = true;
  }
  Element.prototype.animate = function (keyframes, options) {
    const animation = native.animate.call(this, keyframes, options);
    // An effect created after Stop never renders a frame: it is cancelled through the ungated native method.
    if (stopped) native.cancel.call(animation);
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
      observe(entry);
      if (entry.animation.playState === "finished") entry.done = true;
    }
    // Under reduced motion any running native animation (WAAPI, CSS animation or transition) on the subject is a violation.
    if (reduced && subject && !violation) for (const animation of document.getAnimations()) {
      const owner = animation.effect && animation.effect.target;
      if (animation.playState === "running" && within(owner)) {
        violation = label(owner) + ((animation.effect && animation.effect.pseudoElement) || "") + " " + String(animation.animationName || animation.transitionProperty || "animation");
        break;
      }
    }
  }
  const structural = entry => Number.isFinite(entry.active) && entry.active > 0 && entry.keyframes > 0 &&
    (!entry.css || (entry.duration > 0 && Number.isFinite(entry.iterations) && entry.name !== "" &&
      ["", "::before", "::after"].indexOf(entry.pseudo) >= 0));
  function evaluate() {
    if (stopped) return "stopped";
    if (errors.length) return "invalid";
    if (readyAt === null) return "pending";
    if (!booted || !subject) return "invalid";
    const relevant = entries.filter(entry => entry.inside);
    if (reduced) return relevant.length || violation ? "invalid" : "reduced";
    if (config.activation === "viewport" && relevant.some(entry => seenAt === null || entry.at + 1 < seenAt)) return "invalid";
    const valid = relevant.filter(structural);
    const start = config.activation === "viewport" ? seenAt : readyAt;
    if (!valid.length) return start !== null && now() - start > LIMIT ? "invalid" : "pending";
    const credited = valid.filter(entry => entry.changed).length;
    if (valid.some(entry => !entry.done && !entry.cancelled))
      return credited ? "playing" : start !== null && now() - start > LIMIT ? "invalid" : "pending";
    // Every finished effect needs its own visible rendered change; constant, hidden or detached effects fail.
    return credited === valid.length ? "settled" : "invalid";
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
        keyframes: entry.keyframes, properties: entry.properties, varying: entry.varying.join(","), shared: entry.blocked.join(","),
        at: entry.at, done: entry.done, visible: entry.visible, changed: entry.changed})),
      error: errors.length ? errors[0] : "", booted, violation, navigation, height: measure(),
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
    // New CSS animations start paused and new transitions are instant; Animation playback calls are gated above.
    const frozen = document.querySelector("style[data-ds-stopped]");
    if (frozen) frozen.media = "all";
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
  // RUNTIME_BOOT selects the target and state view after the copied markup and before the first product script.
  document.addEventListener("ds-runtime-boot", () => {
    if (booted) return;
    booted = true;
    canvas = document.querySelector("[data-hifi-canvas]");
    for (const node of document.querySelectorAll("[data-ds-motion-subject]"))
      if (node.getAttribute("data-ds-motion-subject").split(" ").indexOf(target) >= 0) subject = node;
    // entry.time is when the browser computed the intersection, before any observer callback ran.
    if (subject && typeof native.IO === "function")
      new native.IO(items => { for (const item of items) if (item.isIntersecting && seenAt === null) seenAt = Math.floor(item.time); }).observe(subject);
  }, {once: true});
  document.addEventListener("DOMContentLoaded", () => {
    if (typeof window.connectProductControls === "function") { try { window.connectProductControls(document); } catch (_) {} }
    readyAt = now();
    if (typeof native.RO === "function") new native.RO(report).observe(canvas || document.body);
    tick();
  }, {once: true});
})();"""

RUNTIME_BOOT = r"""(() => {
  "use strict";
  const read = id => JSON.parse(document.getElementById(id).textContent);
  const config = read("ds-frame-config"), mount = read("ds-mount");
  const target = typeof mount.target === "string" && config.targets.indexOf(mount.target) >= 0 ? mount.target : config.target;
  const canvas = document.querySelector("[data-hifi-canvas]");
  if (canvas) canvas.setAttribute("data-hifi-target", target);
  for (const view of document.querySelectorAll("[data-hifi-state-view]")) {
    const only = view.getAttribute("data-responsive-target");
    view.hidden = view.getAttribute("data-hifi-state-view") !== config.state || (only !== null && only !== target);
  }
  document.dispatchEvent(new CustomEvent("ds-runtime-boot"));
})();"""

STOPPED_CSS = "*,*::before,*::after{animation-play-state:paused!important;transition-duration:0s!important;transition-delay:0s!important}"

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
    return "Invalid" + at + ": " + (data.error ? "source script error: " + clip(data.error, 120)
      : data.violation ? "source motion ran under reduced motion on " + clip(data.violation, 80) + "."
      : "no valid source motion was observed on the bound subject.");
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
