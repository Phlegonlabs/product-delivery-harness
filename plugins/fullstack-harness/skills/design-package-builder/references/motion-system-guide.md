# Motion System Guide

Use this guide when motion communicates hierarchy, feedback, continuity, orientation, state, or brand storytelling. Do not add motion only to make a static design appear more polished.

## Technology Selection

Verify current APIs, packages, versions, pricing, and licenses from official sources before finalizing.

| Option | Use for | Avoid or escalate when |
| --- | --- | --- |
| [CSS transitions and keyframes](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations) | Hover/focus/state feedback, simple one-shot entrances, and dependency-free showcases | Playback coordination, dynamic sequencing, or complex interruption is required |
| [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API) | Dependency-free DOM keyframes, sequencing, and play/pause/cancel controls | The project needs framework-native layout or gesture orchestration |
| [Motion](https://motion.dev/docs) | React or JavaScript variants, staggered sequences, gestures, layout motion, and accessible orchestration | Core APIs do not cover the required effect or paid Motion+ features would be required |
| [GSAP](https://gsap.com/docs/v3/) | Complex timelines, SVG choreography, scroll-linked sequences, and cross-framework imperative control | A simpler native/CSS solution is sufficient; reverify current package and license terms |
| [Rive](https://rive.app/docs/runtimes/state-machines) | Art-directed interactive vector heroes and state-machine-driven illustrations | A static/vector asset is sufficient, runtime cost is unjustified, or playback/cleanup cannot be controlled |
| Native platform motion APIs | Platform-specific mobile or desktop experiences | The result must behave identically across unrelated platforms |

Prefer the smallest stack that expresses the approved choreography. Do not add two animation libraries for one surface without a documented boundary.

## Motion Tokens

Use these as starting ranges, then tune against product density and device evidence:

- `motion-instant`: 80–140ms for direct press, hover, and compact state feedback
- `motion-fast`: 140–220ms for controls, menus, and small transitions
- `motion-standard`: 220–360ms for panels, content changes, and short entrances
- `motion-expressive`: 360–700ms for bounded brand moments or large visual reveals
- `motion-stagger`: 40–90ms between related items; cap the sequence so late content does not feel blocked
- Distances: 4–8px for controls, 8–20px for content entrances; avoid large viewport travel by default
- Scale: keep routine entrances close to the final size, usually around 0.98–1, to avoid zoom-like vestibular motion

Define named easing or spring tokens. Use ease-out for entrances, ease-in for exits, and ease-in-out for repositioning unless product evidence supports another behavior.

## Motion Personality

Tie token choices to the product's taste statement instead of leaving duration and easing generic. Name which archetype the taste statement maps to and justify token choices against it in `design-system.md`.

| Archetype | Easing bias | Duration bias | Stagger | Distance / scale | Avoid |
| --- | --- | --- | --- | --- | --- |
| Precise / technical | Linear-ish, minimal overshoot | Low end of `motion-fast`/`motion-standard` | Minimal or none | Small (near the 4–8px control range) | Bounce, overshoot, long settles |
| Warm / editorial | Soft ease-out | `motion-standard`/`motion-expressive` | Visible, toward the 90ms end of `motion-stagger` | Larger content-entrance distances (toward 20px) | Mechanical linear motion |
| Playful | Spring/overshoot permitted | `motion-fast`/`motion-standard` | Faster, energetic | Moderate, with light overshoot | Overly restrained or flat motion |
| Premium / restrained | Ease-out, no overshoot | Longest allowed (`motion-expressive` range) | None | Moderate, unhurried | Bounce, overshoot, stagger flourish |

A product does not have to fit one archetype exactly — blend adjacent rows when the taste statement justifies it, but state the blend explicitly rather than defaulting to generic middle-of-the-road values.

## Hero Section Blueprint

Build the hero in its final, readable state first. Run animation as progressive enhancement; if JavaScript, an animation dependency, or media fails, the headline, copy, CTA, and product proof must remain visible and operable.

| Phase | Typical element | Start | Recommended motion | Purpose |
| --- | --- | --- | --- | --- |
| 1 | Eyebrow or brand cue | 0ms | Opacity plus 4–8px vertical settle | Establish context without delaying the headline |
| 2 | Headline | 60–120ms after phase 1 | Opacity plus 8–16px settle | Lead attention to the core proposition |
| 3 | Supporting copy and CTA group | 80–140ms after headline starts | Short opacity/translate stagger | Reveal explanation and action in reading order |
| 4 | Product media or subject | Overlap phases 2–3 | Opacity plus subtle scale/translate or masked reveal | Connect the claim to real product proof |
| 5 | Decorative accent | After critical content is stable | One-shot or low-amplitude bounded motion | Add brand character without competing with conversion |

Target a coherent entrance of roughly 700–1000ms rather than serially animating every word or control. Keep the CTA interactive throughout. Run once per page navigation by default, not on every small scroll reversal.

For mobile, reduce layers, distance, parallax, and simultaneous media work. For reduced motion, remove spatial transforms, parallax, auto-playing video, and continuous ambience; use immediate rendering or a short opacity change. Do not communicate meaning only through animation.

## Non-Hero Choreography Blueprints

Most motion in a real product lives outside the hero. Specify these patterns whenever they are in scope, using the same static-first, progressive-enhancement discipline as the hero.

| Pattern | Entrance | Exit / reversal | Notes |
| --- | --- | --- | --- |
| Modal / sheet open-close | Backdrop opacity fade; panel translate/scale in at `motion-standard` | Exact reverse of entrance at `motion-fast`/`motion-standard` | Trap focus only after the panel is visible; lock body scroll or reserve `scrollbar-gutter` so the page does not shift width |
| List add / remove / reorder | New items: opacity + translate at `motion-fast`/`motion-standard` | Removed items: reverse of entrance, then unmount | Reposition surviving siblings with a FLIP-style transform-only animation, never by animating `height`/`top`, to avoid layout shift |
| Toast / notification | Opacity + translate in, `motion-fast` | Auto-dismiss after a stated duration, or manual dismiss; reverse of entrance | Stack with a fixed offset in a fixed-position layer so toasts never push document flow |
| Skeleton-to-content swap | Skeleton renders immediately, no entrance needed | Crossfade to resolved content at `motion-fast` | Skeleton must match the resolved content's box dimensions exactly |
| Form validation feedback | Inline error: opacity + settle at `motion-fast`; success: opacity confirmation | Error clears on correction | Any attention cue (e.g. shake) stays low-amplitude and capped to one repetition |
| Drag-and-drop | Lift: scale/shadow increase on pickup | Drop: settle to final position; invalid drop snaps back at `motion-standard` | — |
| Scroll-triggered reveal (grids/sections) | Opacity + translate at `motion-standard`, staggered at `motion-stagger` | One-shot by default; do not re-animate on scroll-back unless the pattern is explicitly decorative/ambient | Trigger via an IntersectionObserver at roughly 10–20% visibility |
| Empty-state illustration | Single bounded one-shot entrance, or a low-amplitude capped loop (a few pixels, several-second period) | — | Reduced motion: static illustration, no loop |

Interruption rules for these patterns:

- Toast: an auto-dismiss timer pauses on hover/focus; a new toast does not restart other toasts' timers.
- Modal: rapid re-toggling cancels the in-flight animation cleanly rather than queuing a backlog of open/close transitions.
- List reorder: a reorder triggered while a prior reorder animation is still in flight re-measures current positions before starting the new FLIP pass, rather than animating from stale coordinates.

For removal, delay DOM/unmount until the exit transition completes — use the framework's exit-animation primitive (for example a React `AnimatePresence`-equivalent or Vue's built-in leave hooks), an `animationend`/`transitionend` listener, or a timeout matched to the token duration as a fallback. Do not remove the node immediately on state change and let the exit animation get cut off.

## Demonstration Contract

When the user asks to see motion, create a runnable `motion-showcase.html` or bounded demo in the target stack. Use `assets/templates/MOTION_SHOWCASE.template.html` for a dependency-free baseline. When the Motion Pattern Inventory includes non-hero surfaces in scope, the showcase or `motion-demos/` folder must include one runnable, controllable section per in-scope pattern (for example a toast trigger, a modal open/close demo, a reorderable list), not only the hero entrance.

The showcase must include:

- Final static content in the source markup
- Play, pause/restart, and reduced-motion preview controls
- Motion token values and choreography visible in the accompanying design-system tables
- Desktop and mobile behavior or an explicit viewport-switching method
- No production claims, metrics, logos, or testimonials invented for the demo
- A stable artifact path recorded in `design-system.md` and `ui-mockups.md`

Video or GIF may document the approved result but must not be the only source of truth. Preserve runnable code or a keyframe/storyboard specification.

## Performance and Accessibility

- Prefer opacity and transform for routine DOM animation. Treat layout properties, filters, blur, large shadows, masks, and canvas/WebGL work as measured exceptions.
- Do not delay first access to critical content while waiting for animation or assets. Avoid layout shifts by reserving the hero media dimensions.
- Respect `prefers-reduced-motion` in CSS and JavaScript. If using Motion, configure reduced motion at the application boundary; if using GSAP or Rive, implement equivalent media-query and playback control.
- Provide pause/stop/hide controls for qualifying auto-running movement, and avoid unnecessary interaction-triggered parallax or zoom.
- Never flash content more than three times in one second. Avoid bright alternating flashes entirely.
- Stop or pause offscreen continuous animation, cancel timelines on unmount/navigation, and clean up runtime resources.
- Verify keyboard operation, focus visibility, readable content, responsive behavior, and low-power/mobile performance with motion enabled and reduced.

## Acceptance Evidence

- Runnable demo or implementation reference linked to its Motion ID
- Choreography table with purpose, trigger, properties, timing, dependencies, and fallback
- Normal, mobile, reduced-motion, interrupted, and dependency-failure checks
- Performance trace for complex, scroll-linked, video, canvas, WebGL, Rive, or filter-heavy motion
- Confirmation that motion does not block CTA interaction, change document reading order, or hide essential content
