"""Fixed specimen-book chrome: gallery CSS, gallery runtime and plate runtime.

These bytes are renderer styling and behavior only. They never style product
specimens, which keep the approved HiFi CSS inside sandboxed plates.
"""

GALLERY_CSS = """
:root{--paper:#f1f3ef;--sheet:#fff;--ink:#1d2422;--muted:#56605c;--rule:#c5ccc6;--proof:#2542b8;
--display:"Iowan Old Style","Palatino Linotype",Palatino,"URW Palladio L",P052,Georgia,serif;
--text:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,"Noto Sans CJK TC","Microsoft JhengHei",sans-serif;
--code:ui-monospace,"Cascadia Mono",Consolas,"Liberation Mono",monospace}
*{box-sizing:border-box}html{background:var(--paper);color:var(--ink);font:1rem/1.55 var(--text);-webkit-text-size-adjust:100%}
body{margin:0}a{color:var(--proof);text-underline-offset:.18em}
:focus-visible{outline:3px solid var(--proof);outline-offset:3px}
.skip{position:absolute;left:1rem;top:-4rem;background:var(--sheet);padding:.5rem .75rem;z-index:3}.skip:focus{top:1rem}
.masthead{padding:clamp(2rem,6vw,5.5rem) clamp(1.25rem,5vw,4.5rem) clamp(1.5rem,4vw,3rem);border-bottom:1px solid var(--ink);
display:grid;grid-template-columns:minmax(0,1.6fr) minmax(16rem,1fr);gap:2rem clamp(2rem,5vw,5rem);align-items:end}
.masthead h1{font:400 clamp(2.6rem,7.2vw,6rem)/.98 var(--display);letter-spacing:-.015em;margin:0;max-width:14ch;overflow-wrap:anywhere}
.masthead .lede{font:400 clamp(1.1rem,1.7vw,1.35rem)/1.45 var(--display);margin:1.25rem 0 0;max-width:40ch;color:var(--muted)}
.provenance{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:.35rem 1rem;font-size:.82rem;align-self:end}
.provenance dt{color:var(--muted)}.provenance dd{margin:0;overflow-wrap:anywhere}
code,.hash{font-family:var(--code);font-size:.86em}
.book{display:grid;grid-template-columns:minmax(11rem,14rem) minmax(0,1fr);gap:clamp(1.5rem,4vw,4rem);padding:0 clamp(1.25rem,5vw,4.5rem) 5rem}
.index{position:sticky;top:0;align-self:start;padding-top:2.25rem;max-height:100vh;overflow:auto}
.index ol{list-style:none;margin:0;padding:0;border-left:1px solid var(--rule)}
.index a{display:flex;justify-content:space-between;gap:1rem;padding:.4rem 0 .4rem 1rem;color:var(--ink);text-decoration:none}
.index a:hover{color:var(--proof)}.index span{color:var(--muted);font-variant-numeric:tabular-nums}
.chapter{padding-top:2.75rem;border-bottom:1px solid var(--rule);padding-bottom:2.5rem}
.chapter>h2{font:400 clamp(2rem,4vw,3.1rem)/1.05 var(--display);margin:0 0 .6rem}
.chapter>p{max-width:68ch;color:var(--muted);margin:0 0 1.75rem}
h3{font:600 1.05rem/1.3 var(--text);margin:2.25rem 0 .75rem}h4{font:600 .95rem/1.3 var(--text);margin:1.5rem 0 .5rem}
.meta{color:var(--muted);font-size:.9rem;margin:-.4rem 0 1rem}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:.5rem 0 1rem}
th,td{text-align:left;vertical-align:top;padding:.55rem .75rem .55rem 0;border-bottom:1px solid var(--rule);overflow-wrap:anywhere}
th{font-weight:600}thead th{color:var(--muted);font-weight:500;border-bottom-color:var(--ink)}
.table-scroll{overflow-x:auto}
.swatches{display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:1.5rem 1rem;margin:0;padding:0;list-style:none}
.chip{height:5.5rem;border:1px solid rgba(0,0,0,.18)}.swatches p{margin:.5rem 0 0;font-size:.85rem;line-height:1.35}
.ladder{list-style:none;margin:0;padding:0}.ladder li{display:grid;grid-template-columns:minmax(8rem,12rem) minmax(0,1fr);gap:1rem;align-items:baseline;border-bottom:1px solid var(--rule);padding:.6rem 0}
.ladder .sample{overflow-wrap:anywhere;line-height:1.15}
.bar{height:.9rem;background:var(--ink);max-width:100%}.shape{width:4.5rem;height:3rem;border:1px solid var(--ink);background:var(--sheet)}
.range{font-size:.9rem;color:var(--muted)}
.track{position:relative;height:2.25rem;border:1px solid var(--rule);background:var(--sheet);overflow:hidden;max-width:26rem}
.dot{position:absolute;left:.4rem;top:.45rem;width:1.3rem;height:1.3rem;border-radius:50%;background:var(--proof);transition-property:left}
.track.is-run .dot{left:calc(100% - 1.7rem)}
[data-ds-reduced] .dot{transition:none!important}
.plates{display:flex;flex-wrap:wrap;gap:2.25rem 2rem;align-items:flex-start}
.plate{position:relative;margin:0;max-width:100%}
.plate-stage{position:relative;padding:.9rem;background:var(--sheet);border:1px solid var(--rule);width:fit-content;max-width:100%;overflow-x:auto}
.plate-stage::before,.plate-stage::after{content:"";position:absolute;width:.8rem;height:.8rem;border-color:var(--ink);border-style:solid;pointer-events:none}
.plate-stage::before{top:-.45rem;left:-.45rem;border-width:1px 0 0 1px}.plate-stage::after{right:-.45rem;bottom:-.45rem;border-width:0 1px 1px 0}
.plate iframe{display:block;border:0;background:transparent;max-width:none;height:8rem}
.facts{max-width:36rem}.facts th{width:12rem}td.hash{white-space:nowrap}
.plate figcaption{font-size:.85rem;margin-top:.6rem;max-width:44rem;line-height:1.45}
.plate figcaption b{font-weight:600}.status{color:var(--muted);font-size:.85rem;min-height:1.3em;margin:.25rem 0 0}
.native{display:inline-block;border:1px solid var(--ink);padding:.05rem .45rem;margin:.25rem 0;font-size:.8rem}
.controls{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;margin:.75rem 0}
.controls fieldset{border:0;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center}
.controls legend{float:left;margin-right:.5rem;font-size:.85rem;color:var(--muted)}
button,select,input{font:inherit}
button{border:1px solid var(--ink);background:var(--sheet);color:var(--ink);padding:.3rem .8rem;border-radius:2px;min-height:2.25rem;cursor:pointer}
button[aria-pressed="true"]{background:var(--ink);color:var(--sheet)}
select{min-height:2.25rem;border:1px solid var(--ink);background:var(--sheet);padding:0 .5rem;border-radius:2px}
label{font-size:.85rem;color:var(--muted);display:inline-flex;gap:.5rem;align-items:center}
input[type=range]{width:min(18rem,60vw);accent-color:var(--proof)}
.toolbar{position:sticky;top:0;z-index:2;background:var(--paper);border-bottom:1px solid var(--rule);padding:.6rem 0;margin-bottom:1rem}
.coverage{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1rem;margin:0 0 1.5rem}
.coverage div{border-top:3px solid var(--ink);padding-top:.5rem}.coverage strong{display:block;font:400 2rem/1.1 var(--display)}
@media (max-width:60rem){.book{grid-template-columns:minmax(0,1fr)}.index{position:static;padding-top:1.25rem;max-height:none}
.index ol{display:flex;flex-wrap:wrap;border-left:0;gap:.25rem 1.25rem}.index a{padding:.25rem 0}.masthead{grid-template-columns:minmax(0,1fr)}}
@media (prefers-reduced-motion:reduce){.dot{transition:none!important}}
"""

GALLERY_RUNTIME = """(() => {
  const frames = new Map();
  for (const frame of document.querySelectorAll("iframe[data-ds-frame]")) frames.set(frame.dataset.dsFrame, frame);
  const post = (id, message) => { const frame = frames.get(id); if (frame && frame.contentWindow) frame.contentWindow.postMessage(message, "*"); };
  const root = document.documentElement;
  const toggle = document.querySelector("[data-ds-reduced-toggle]");
  let reduced = Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  function applyReduced() {
    root.toggleAttribute("data-ds-reduced", reduced);
    if (toggle) toggle.setAttribute("aria-pressed", String(reduced));
    for (const id of frames.keys()) post(id, {type: "ds-reduced", on: reduced});
  }
  window.addEventListener("message", event => {
    let frame = null;
    for (const candidate of frames.values()) if (candidate.contentWindow === event.source) frame = candidate;
    const data = event.data;
    if (!frame || !data || typeof data !== "object") return;
    if (data.type === "ds-frame-size" && Number.isFinite(data.height)) {
      frame.style.height = Math.min(Math.max(Math.ceil(data.height), 40), 4000) + "px";
      if (!frame.dataset.dsReady) { frame.dataset.dsReady = "1"; post(frame.dataset.dsFrame, {type: "ds-reduced", on: reduced}); }
    } else if (data.type === "ds-navigation") {
      for (const status of document.querySelectorAll("[data-ds-status]")) {
        if (status.dataset.dsStatus === frame.dataset.dsFrame) status.textContent = "Product link to " + String(data.href).slice(0, 120) + " is part of the approved HiFi; the gallery stays on this plate.";
      }
    }
  });
  function nearest(slider, width) {
    let chosen = null;
    for (const item of JSON.parse(slider.dataset.dsTargets || "[]")) if (item[1] <= width || chosen === null) chosen = item[0];
    return chosen;
  }
  document.addEventListener("click", event => {
    const button = event.target.closest ? event.target.closest("button") : null;
    if (!button) return;
    if (button.hasAttribute("data-ds-reduced-toggle")) { reduced = !reduced; applyReduced(); return; }
    const id = button.dataset.dsFor;
    if (button.dataset.dsTarget && id) {
      const width = Number(button.dataset.dsWidth);
      post(id, {type: "ds-target", target: button.dataset.dsTarget});
      if (frames.get(id) && width) frames.get(id).style.width = width + "px";
      for (const peer of document.querySelectorAll("button[data-ds-target]")) if (peer.dataset.dsFor === id) peer.setAttribute("aria-pressed", String(peer === button));
      for (const slider of document.querySelectorAll("input[data-ds-width-for]")) if (slider.dataset.dsWidthFor === id && width) { slider.value = String(width); slider.nextElementSibling.textContent = width + " px"; }
    } else if (button.dataset.dsMotion && id) {
      post(id, {type: "ds-motion", action: button.dataset.dsMotion});
    } else if (button.dataset.dsTokenMotion) {
      const track = document.getElementById(button.dataset.dsTokenMotion);
      if (!track) return;
      if (button.dataset.action === "stop") { track.classList.remove("is-run"); return; }
      track.classList.remove("is-run"); void track.offsetWidth; track.classList.add("is-run");
    }
  });
  document.addEventListener("input", event => {
    const slider = event.target;
    if (!slider.matches || !slider.matches("input[data-ds-width-for]")) return;
    const id = slider.dataset.dsWidthFor;
    const width = Number(slider.value);
    if (frames.get(id)) frames.get(id).style.width = width + "px";
    post(id, {type: "ds-target", target: nearest(slider, width), width});
    slider.nextElementSibling.textContent = width + " px";
    for (const peer of document.querySelectorAll("button[data-ds-target]")) if (peer.dataset.dsFor === id) peer.setAttribute("aria-pressed", String(Number(peer.dataset.dsWidth) === width));
  });
  document.addEventListener("change", event => {
    const select = event.target;
    if (select.matches && select.matches("select[data-ds-state-for]")) post(select.dataset.dsStateFor, {type: "ds-state", state: select.value});
  });
  applyReduced();
})();"""

FRAME_RUNTIME = """(() => {
  const config = JSON.parse(document.getElementById("ds-frame-config").textContent);
  let subject = document.querySelector("[data-ds-subject]") || document.body;
  const canvas = document.querySelector("[data-hifi-canvas]");
  const reduced = document.querySelector("style[data-ds-reduced]");
  let state = config.state || null;
  const measured = () => canvas || document.body;
  // The root scroll height never drops below the frame viewport, so measure content.
  const report = () => parent.postMessage({type: "ds-frame-size", id: config.id,
    height: Math.ceil(measured().getBoundingClientRect().bottom + window.scrollY)}, "*");
  function showState() {
    if (config.kind !== "surface" || !state) return;
    const target = canvas ? canvas.getAttribute("data-hifi-target") : null;
    for (const view of document.querySelectorAll("[data-hifi-state-view]")) {
      const only = view.getAttribute("data-responsive-target");
      view.hidden = view.getAttribute("data-hifi-state-view") !== state || (only !== null && only !== target);
    }
  }
  function setTarget(target, width) {
    if (!canvas) return;
    if (target) canvas.setAttribute("data-hifi-target", target);
    if (width) canvas.style.width = width + "px"; else canvas.style.removeProperty("width");
    showState();
    requestAnimationFrame(report);
  }
  const animations = () => (document.getAnimations ? document.getAnimations() : []);
  function play() {
    const motion = config.motion;
    if (!motion) return;
    for (const item of animations()) item.cancel();
    if (motion.kind === "attribute") { subject.setAttribute(motion.name, motion.from); void subject.offsetWidth; subject.setAttribute(motion.name, motion.to); }
    else if (motion.kind === "class") { subject.classList.remove(motion.name); void subject.offsetWidth; subject.classList.add(motion.name); }
    else { const clone = subject.cloneNode(true); subject.replaceWith(clone); subject = clone; }
  }
  function stop() { for (const item of animations()) item.pause(); }
  window.addEventListener("message", event => {
    const data = event.data;
    if (event.source !== parent || !data || typeof data !== "object") return;
    if (data.type === "ds-target") setTarget(data.target, data.width);
    else if (data.type === "ds-state") { state = String(data.state); showState(); requestAnimationFrame(report); }
    else if (data.type === "ds-motion") (data.action === "play" ? play : stop)();
    else if (data.type === "ds-reduced" && reduced) reduced.media = data.on ? "all" : "not all";
  });
  document.addEventListener("click", event => {
    const link = event.target.closest ? event.target.closest("a[href]") : null;
    if (link && !link.getAttribute("href").startsWith("#")) { event.preventDefault(); parent.postMessage({type: "ds-navigation", id: config.id, href: link.getAttribute("href")}, "*"); }
  }, true);
  document.addEventListener("submit", event => event.preventDefault(), true);
  if (config.kind === "surface" && typeof window.connectProductControls === "function") { try { window.connectProductControls(document); } catch (_) {} }
  showState();
  if ("ResizeObserver" in window) new ResizeObserver(report).observe(measured());
  window.addEventListener("load", report);
  report();
})();"""

_FRAME_REPORT = """  const report = () => parent.postMessage({type: "ds-frame-size", id: config.id,
    height: Math.ceil(measured().getBoundingClientRect().bottom + window.scrollY)}, "*");
"""
# ds-showcase/2 component plates inside a native <details> only. An open disclosure
# may paint outside the canvas box (an absolute menu), so the plate also measures
# its visible extent and reports again on every native toggle. Boxes exclude paint such
# as a box-shadow or focus outline, so an open disclosure adds a fixed renderer gutter
# below its lowest box; it is chrome clearance, not a CSS paint model. FRAME_RUNTIME is unchanged.
DISCLOSURE_PAINT_GUTTER = 16
FRAME_RUNTIME_DISCLOSURE = FRAME_RUNTIME.replace(_FRAME_REPORT, """  const bottom = () => Array.from(document.querySelectorAll("details[open] *"), item => item.getBoundingClientRect().bottom + %d)
    .reduce((most, value) => Math.max(most, value), measured().getBoundingClientRect().bottom);""" % DISCLOSURE_PAINT_GUTTER + """
  const report = () => parent.postMessage({type: "ds-frame-size", id: config.id, height: Math.ceil(bottom() + window.scrollY)}, "*");
  document.addEventListener("toggle", () => requestAnimationFrame(report), true);
""")
if FRAME_RUNTIME_DISCLOSURE == FRAME_RUNTIME:
    raise RuntimeError("FRAME_RUNTIME report changed; update FRAME_RUNTIME_DISCLOSURE")
