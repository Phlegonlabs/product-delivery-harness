# Motion System Guide

Use this guide when motion does real work for the user. Do not add motion only to make a static design appear more polished.

`references/ui-architecture-guide.md`'s Motion Architecture is the contract this guide implements. Four rules carry most of it:

- Every animation has exactly one purpose: feedback, continuity, processing, or storytelling. Nothing outside those four, and no decoration. An animation that fits none of them gets deleted, not documented.
- Motion never carries information that exists nowhere else. Remove the animation and the interface still tells the whole story.
- Call sites reference registered motion variants by name. A page, a product component, or a mockup never writes a duration, distance, easing, or spring value.
- The reduced-motion policy is set once, globally, and every variant inherits it.

## Mechanism Split

Split motion by mechanism and give each mechanism the work it is actually good at. A surface that needs two mechanisms for one effect needs a documented boundary.

| Mechanism | Owns | Does not own |
| --- | --- | --- |
| Style-layer transitions | Hover, focus, pressed, selected, color and simple opacity transitions | Sequencing, interruption, exit animation, layout change |
| Animation runtime | Enter/exit, layout change, list insertion and removal, dialogs and drawers, gesture, shared element, state choreography | State styling the style layer already handles |
| Route-level transitions | Continuity across navigation | Anything inside a single route |

Do not hydrate or wake an interactive runtime on a static page just to fade content in. The style layer, plus route-level transitions where the target supports them, covers that case with no runtime at all.

Record which mechanism each Motion Pattern Inventory row uses. A row whose mechanism does not match its work — a modal exit on the style layer, a hover color change on the runtime — is a finding.

## Technology Selection

Verify current APIs, packages, versions, pricing, and licenses from official sources before finalizing.

| Option | Mechanism | Use for | Avoid or escalate when |
| --- | --- | --- | --- |
| [CSS transitions and keyframes](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations) | Style layer | Hover/focus/state feedback, simple one-shot entrances, and dependency-free showcases | Playback coordination, dynamic sequencing, or complex interruption is required |
| [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API) | Animation runtime | Dependency-free DOM keyframes, sequencing, and play/pause/cancel controls | The project needs framework-native layout or gesture orchestration |
| [Motion](https://motion.dev/docs) | Animation runtime | React or JavaScript variants, staggered sequences, gestures, layout motion, and accessible orchestration | Core APIs do not cover the required effect or paid Motion+ features would be required |
| [GSAP](https://gsap.com/docs/v3/) | Animation runtime | Complex timelines, SVG choreography, scroll-linked sequences, and cross-framework imperative control | A simpler native/CSS solution is sufficient; reverify current package and license terms |
| [Rive](https://rive.app/docs/runtimes/state-machines) | Animation runtime | Art-directed interactive vector heroes and state-machine-driven illustrations | A static/vector asset is sufficient, runtime cost is unjustified, or playback/cleanup cannot be controlled |
| [View Transitions](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) | Route level | Continuity across navigation, including for a page that ships no animation runtime | The transition must run inside one route, or the target's support is unverified |
| Native platform motion APIs | Style layer and animation runtime, per platform | Platform-specific mobile or desktop experiences | The result must behave identically across unrelated platforms |

Prefer the smallest stack that expresses the approved choreography. One animation runtime per project. Do not add two animation libraries for one surface without a documented boundary, and record the chosen runtime in `design-system.md`'s Motion Principles & Stack table against the mechanism it serves.

## Motion Tokens

Motion tokens are the only place a duration, distance, easing, or spring value lives. Every other layer references a token, and call sites reference a registered variant that references the token. A raw `300ms`, `24px`, or `cubic-bezier(...)` in a page, product component, or mockup is a contract violation, not a shortcut.

Use these as starting ranges, then tune against product density and device evidence:

- `motion-instant`: 80–140ms for direct press, hover, and compact state feedback
- `motion-fast`: 140–220ms for controls, menus, and small transitions
- `motion-standard`: 220–360ms for panels, content changes, and short entrances
- `motion-expressive`: 360–700ms for bounded brand moments or large visual reveals
- `motion-stagger`: 40–90ms between related items; cap the sequence so late content does not feel blocked
- Distances: 4–8px for controls, 8–20px for content entrances; avoid large viewport travel by default
- Scale: keep routine entrances close to the final size, usually around 0.98–1, to avoid zoom-like vestibular motion

Define named easing or spring tokens. Use ease-out for entrances, ease-in for exits, and ease-in-out for repositioning unless product evidence supports another behavior.

## Registered Variants

A registered variant is the unit a call site is allowed to name. Each one records:

- Its variant name, in the product's own vocabulary
- Its mechanism, from the Mechanism Split above
- Its purpose — feedback, continuity, processing, or storytelling
- Its trigger, properties, and the motion tokens it composes
- Its repeat and interruption behavior
- What it must not be used for

Every variant goes in the Motion Pattern Inventory and in `ui-registry.json`. A variant in one but not the other fails the registry check. When a surface needs motion the variant set does not cover, add a variant and register it — a reviewable change in one place — instead of writing values at the call site. A variant with no stated purpose gets deleted, not documented.

## Reduced Motion Policy

Set the policy once, at the application boundary, and let every variant inherit it. Do not repeat a `prefers-reduced-motion` check at each call site — a policy scattered across call sites is a policy with holes, and the one surface that forgets the check is the one that makes a user ill.

One global configuration does three things:

- Reduced motion shows the final state, not a slower version of the entrance. Opacity-only is an acceptable substitute; a longer duration is not.
- Spatial transforms, parallax, auto-playing video, continuous ambience, and scale are off.
- Each token carries its reduced-motion value, so a variant that inherits the policy needs no per-surface override.

Record the single configuration point in `design-system.md`'s Motion Principles & Stack table: the style layer's media query, the runtime's global reduced-motion setting, and the route-level transition's opt-out. A variant that needs to differ from the policy states why in its inventory row; that is an exception, not the pattern.

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

| Phase | Typical element | Start | Recommended motion | Purpose and rationale |
| --- | --- | --- | --- | --- |
| 1 | Eyebrow or brand cue | 0ms | Opacity plus 4–8px vertical settle | storytelling — establish context without delaying the headline |
| 2 | Headline | 60–120ms after phase 1 | Opacity plus 8–16px settle | storytelling — lead attention to the core proposition |
| 3 | Supporting copy and CTA group | 80–140ms after headline starts | Short opacity/translate stagger | storytelling — reveal explanation and action in reading order |
| 4 | Product media or subject | Overlap phases 2–3 | Opacity plus subtle scale/translate or masked reveal | storytelling — connect the claim to real product proof |
| 5 | Brand accent | After critical content is stable | One-shot or low-amplitude bounded motion | storytelling — reinforce a documented brand cue without competing with conversion |

Target a coherent entrance of roughly 700–1000ms rather than serially animating every word or control. Keep the CTA interactive throughout. Run once per page navigation by default, not on every small scroll reversal.

The millisecond ranges above are how you pick tokens, not what the hero markup contains. Register the entrance as one storytelling variant per phase, and let the hero name those variants. The whole entrance is an animation-runtime job; the CTA's hover and focus stay on the style layer.

For mobile, reduce layers, distance, parallax, and simultaneous media work. Reduced motion follows the global policy — the final hero state renders immediately, with an opacity change at most. Do not communicate meaning only through animation.

## Non-Hero Choreography Blueprints

Most motion in a real product lives outside the hero. Specify these patterns whenever they are in scope, using the same static-first, progressive-enhancement discipline as the hero.

Every pattern below is animation-runtime work — each one needs sequencing, an exit, or interruption handling that the style layer cannot express. Register each as a named variant with its purpose, and let the surface name the variant.

| Pattern | Entrance | Exit / reversal | Notes |
| --- | --- | --- | --- |
| Modal / sheet open-close | Backdrop opacity fade; panel translate/scale in at `motion-standard` | Exact reverse of entrance at `motion-fast`/`motion-standard` | Trap focus only after the panel is visible; lock body scroll or reserve `scrollbar-gutter` so the page does not shift width |
| List add / remove / reorder | New items: opacity + translate at `motion-fast`/`motion-standard` | Removed items: reverse of entrance, then unmount | Reposition surviving siblings with a FLIP-style transform-only animation, never by animating `height`/`top`, to avoid layout shift |
| Toast / notification | Opacity + translate in, `motion-fast` | Auto-dismiss after a stated duration, or manual dismiss; reverse of entrance | Stack with a fixed offset in a fixed-position layer so toasts never push document flow |
| Skeleton-to-content swap | Skeleton renders immediately, no entrance needed | Crossfade to resolved content at `motion-fast` | Skeleton must match the resolved content's box dimensions exactly |
| Form validation feedback | Inline error: opacity + settle at `motion-fast`; success: opacity confirmation | Error clears on correction | Any attention cue (e.g. shake) stays low-amplitude and capped to one repetition |
| Drag-and-drop | Lift: scale/shadow increase on pickup | Drop: settle to final position; invalid drop snaps back at `motion-standard` | — |
| Scroll-triggered reveal (grids/sections) | Opacity + translate at `motion-standard`, staggered at `motion-stagger` | One-shot by default; do not re-animate on scroll-back | Trigger via an IntersectionObserver at roughly 10–20% visibility; use only when the reveal has one canonical purpose |
| Empty-state illustration | Single bounded one-shot entrance | — | No permanent loop. If a repeat is genuinely wanted, cap it at a stated number of cycles and register it as storytelling. Reduced motion: static illustration |

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
- The registered variant name beside each demo section, so the demo and the registry read as one system
- Desktop and mobile behavior or an explicit viewport-switching method
- No production claims, metrics, logos, or testimonials invented for the demo
- A stable artifact path recorded in `design-system.md` and `page-recipes.md`

Video or GIF may document the approved result but must not be the only source of truth. Preserve runnable code or a keyframe/storyboard specification.

## Performance and Accessibility

- Prefer opacity and transform for routine DOM animation. Treat layout properties, filters, blur, large shadows, masks, and canvas/WebGL work as measured exceptions.
- Do not delay first access to critical content while waiting for animation or assets. Avoid layout shifts by reserving the hero media dimensions.
- Apply the one global reduced-motion policy above rather than a per-call-site check. Whatever the stack, the configuration point is single: Motion's application-boundary setting, an equivalent GSAP or Rive media-query and playback wrapper, or one style-layer media query.
- Provide pause/stop/hide controls for qualifying auto-running movement, and avoid unnecessary interaction-triggered parallax or zoom. Avoid scale and parallax on large regions entirely — a full-width band that scales reads as camera movement and is a common source of vestibular discomfort.
- No permanent looping animation. Cap any repeat at a stated number of cycles.
- Never flash content more than three times in one second. Avoid bright alternating flashes entirely.
- Stop or pause offscreen continuous animation, cancel timelines on unmount/navigation, and clean up runtime resources.
- Verify keyboard operation, focus visibility, readable content, responsive behavior, and low-power/mobile performance with motion enabled and reduced.

## Acceptance Evidence

- Runnable demo or implementation reference linked to its Motion ID
- Choreography table with purpose, mechanism, trigger, properties, timing, dependencies, and fallback
- Every variant present in both the Motion Pattern Inventory and `ui-registry.json`, with no call site naming an unregistered variant and no raw duration, distance, or easing value outside the token layer
- One global reduced-motion configuration point, with any per-variant exception stated and justified
- Normal, mobile, reduced-motion, interrupted, and dependency-failure checks
- Performance trace for complex, scroll-linked, video, canvas, WebGL, Rive, or filter-heavy motion
- Confirmation that motion does not block CTA interaction, change document reading order, or hide essential content
