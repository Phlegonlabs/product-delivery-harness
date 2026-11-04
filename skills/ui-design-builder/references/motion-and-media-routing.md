# Motion And Media Routing

## Intent Before Assets

Ask the human owner whether shipped motion is:

- `not_required`: no decorative motion beyond platform-standard functional feedback;
- `functional_only`: motion explains state, progress, continuity, or spatial relationship;
- `expressive`: selected surfaces may use motion for hierarchy or brand, without hiding content; or
- `recommend`: the UI Design Builder proposes one of the above from product evidence for owner approval.

When the owner states no posture, base the `recommend` proposal on what each page actually shows. Propose `expressive` only for a region whose content gains from being shown in motion, such as a product demonstration, portfolio work, a 3D product model or a step-by-step story. Propose `functional_only` elsewhere. Play the proposal in the direction study; it still needs the owner's selection.

In the same intake, ask whether a generation provider such as Higgsfield may be used, for which MM rows, and within what credit or cost limit. Record the answer as that row's exact provider/action authorization. Do not infer it from a motion or hero request; an unanswered question leaves the provider route unauthorized.

Generated motion, autoplay or sound, material performance budgets, accessibility exceptions, and new product scope always return to the owner. Every motion decision includes an equivalent reduced-motion path.

For page-specific defaults, use `page-design-profiles.md`. Landing/portfolio expressive motion is proposed through this same intake and becomes required only when selected; accepted no-motion decisions stay valid. Once selected, demonstrate the actual effect and reduced-motion equivalent under the rules below.

After the Motion and Media Intent is recorded, a representative direction study may play a small deterministic motion option locally with CSS/WAAPI or GSAP when that stays within the approved scope, with normal and reduced-motion behavior. It helps the owner judge selection only; it is not Required motion evidence, native proof, or permission to invoke a generation provider. A provider route stays deferred until after direction selection receives its exact provider/action authorization, and the selected effect still needs complete final HiFi motion evidence.

## Typed Motion Intent Records

For every marquee or media-bearing screen region, record one treatment:

| Treatment | Intent and direction representation | Later route |
| --- | --- | --- |
| `none` | No media placeholder | No provider or animation skill |
| `image` | Labeled static frame with purpose and content contract | Existing asset or a later explicitly authorized image-generation pass |
| `motion` | Labeled poster/frame with trigger, purpose, duration intent, and reduced-motion fallback | CSS/WAAPI, GSAP, or an explicitly authorized generation provider |
| `image + motion` | Labeled static base plus motion layer and fallback | Approved image route plus approved motion route |

The intent record contains no final asset and invokes no provider. Its `MM-*` Motion And Media Intent row carries `treatment`, `purpose`, `trigger`, `draft prompt`, `source`, reduced-motion fallback, generation route, status and `deferred` generation status. Direction studies may render it as a labeled placeholder or bounded local demonstration; HiFi renders and reviews the selected treatment.

An explicit hero or animation request is a required intent, not optional inspiration. A hero intent still records the product message, CTA, composition, media treatment, and mobile destination; a direction study may show the proposed treatment without an approved generated asset. An admin or native surface does not receive a marketing hero unless the owner explicitly requests that surface treatment.

After direction selection, a deterministic `motion` or `image + motion` row must demonstrate its trigger, behavior, end state, and reduced-motion fallback in the HiFi review. A static poster, gray placeholder, screenshot, or documented note cannot satisfy a required effect. The MM record's `generationStatus: deferred` remains an intent-time record; it is never edited to claim HiFi completion. Record actual output identity, authorization and review separately in the existing Style Integration evidence. A missing generated asset required by a `motion` or `image + motion` intent keeps its evidence gate blocked until delivered or explicitly removed from scope. Image-only intents remain under connected-HiFi and H6 human media review, including authorization, actual output identity, placement and usage constraints; they do not use normal/reduced-motion receipts. CSS/WAAPI and GSAP serve Web implementation and HTML projections; native implementation uses its approved platform/framework tools and later native evidence.

## Annotated Animation Boundaries

For newly authored motion regions, keep `motionSpec` detail in the MM record or the existing direction/HiFi evidence: non-empty `scope`, `behavior`, `space`, `compact`, `playback` and `cost` descriptions. Scope names the whole region or exact element; behavior includes the end state; space includes reserved height/pinning/scroll need; compact describes phone behavior; playback includes loop, interruption and replay; cost names loading/performance and dependency limits. Existing trigger and reducedMotionFallback remain authoritative. A direction study may show the proposed effect or a visibly deferred placeholder. Never imply that annotated motion is implemented. New providers or dependencies keep their existing authorization/stack gates.

## Implementation Routing After Direction Selection

Pick the lowest route that delivers the approved effect. Motion, GSAP and Three.js are production dependencies: use them only when the approved stack includes them, otherwise return the choice to `product-definition-builder`.

- Use CSS transitions or the Web Animations API for small, deterministic state feedback. Do not add GSAP merely because motion exists.
- Use Motion (route `Motion`) for springs, sequences, layout and exit animation, gestures, or simple scroll and in-view effects. React stacks use Motion for React.
- Load `gsap-core` when the approved effect needs a scripted tween, responsive matchMedia behavior, or precise reusable easing.
- Add `gsap-timeline` only when multiple approved movements need choreography or shared playback control.
- Add `gsap-scrolltrigger` only when the approved behavior is scroll-driven, pinned, scrubbed, or intersection-timed.
- Use Three.js (route `Three.js`; React Three Fiber in a React stack) only for an approved 3D region such as a product model, spatial data or a brand scene. Record its poster, the content shown when WebGL is unavailable, the asset budget and the reduced-motion behavior.
- Use Higgsfield MCP only when it is installed, its live capability has been observed, and the owner grants exact provider/action authorization for the generated or curated motion request. Treat it as a media provider, never as the implementation source for buttons, navigation, state feedback, or accessibility behavior.

A Higgsfield `generate_3d` model (GLB) can feed an approved Three.js region. The model is a provider asset with its own authorization and review; the scene code uses the `Three.js` route.

For motion craft (timing, easing, choreography), consult `motion-doctrine` or Impeccable's animate guidance when available. They inform the author; `frontend-design` stays the single design author.

## Motion Evidence Per Intent

Observe each required motion intent at one representative responsive target: the smallest approved target of its surface, unless the intent names another. Its evidence is:

- a trigger frame, taken when the declared trigger fires;
- an end-state frame, taken when the effect rests in its approved end state; and
- a reduced-motion check that reads the computed animation and transition duration and confirms the end state arrives in place.

The normal receipt holds the two frames and the reduced-motion receipt holds the check. Each required intent still gets both receipts. Video clips and frame sampling are optional supplements, never required.

## HiFi Embedding Limits

HiFi pages allow only embedded `data:` media. Keep each embedded clip short and compressed (aim for about 2 MB per clip) and always include its poster. A small library such as Motion's `animate()` may be inlined when the page still passes the offline surface check. When a library cannot run inside HiFi (the Three.js source, for example, contains network API names that the surface check rejects), never rename, strip or obfuscate library code to pass. Show the effect with a deterministic approximation instead: CSS 3D, canvas 2D or a short pre-rendered clip of the scene. The approximation still needs its normal and reduced-motion receipts. Mark the row as `HiFi approximation — <library> verified in first implementation slice` in the Style Integration notes and the Harness UI evidence; the real library behavior becomes an implementation obligation, like native proof.

Generated assets remain provider-neutral in the canonical contract. Record the prompt, provider, model or route when known, output identity, license or usage constraints, placement, fallback, and review decision. A generated asset that invents copy, controls, states, routes, or product claims is rejected.
