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

## Composition Before Motion

Settle composition first and add motion second. A direction study fixes layout, type and spacing before its motion option is added. HiFi authoring finishes and self-checks the static pass before the motion pass begins. The rule that a landing or portfolio region with a proposed or selected `expressive` row has at least one direction playing the motion live stays in [`ui-design-pass.md`](ui-design-pass.md).

## Motion References And Notes

A motion reference is a recording, captured under the [Reference Board](design-reference-guide.md#reference-board) rule. Before implementing from it, the author reads the recording frame by frame (or from frame samples) and writes **motion notes** in its `REF-*` record. Per movement, the notes give the element, trigger, property or distance, duration, easing and order.

Take lessons from several recordings; reproduce none exactly, unless the owner named one a page-faithful target with its scope and tolerance. The notes inform the `MM-*` row and the implementation route below; they never replace the row's trigger, reduced-motion fallback or approved scope.

## Typed Motion Intent Records

For every marquee or media-bearing screen region, record one treatment:

| Treatment | Intent and direction representation | Later route |
| --- | --- | --- |
| `none` | No media placeholder | No provider or animation skill |
| `image` | Labeled static frame with purpose and content contract | Existing asset or a later explicitly authorized image-generation pass |
| `motion` | Labeled poster/frame with trigger, purpose, duration intent, and reduced-motion fallback | A code route from [Implementation Routing](#implementation-routing-after-direction-selection), or an explicitly authorized generation provider |
| `image + motion` | Labeled static base plus motion layer and fallback | Approved image route plus approved motion route |

The intent record contains no final asset and invokes no provider. Its `MM-*` Motion And Media Intent row carries `treatment`, `purpose`, `trigger`, `draft prompt`, `source`, reduced-motion fallback, generation route, status and `deferred` generation status. Direction studies may render it as a labeled placeholder or bounded local demonstration; HiFi renders and reviews the selected treatment.

An explicit hero or animation request is a required intent, not optional inspiration. A hero intent still records the product message, CTA, composition, media treatment, and mobile destination; a direction study may show the proposed treatment without an approved generated asset. An admin or native surface does not receive a marketing hero unless the owner explicitly requests that surface treatment.

After direction selection, a deterministic `motion` or `image + motion` row must demonstrate its trigger, behavior, end state, and reduced-motion fallback in the HiFi review. A static poster, gray placeholder, screenshot, or documented note cannot satisfy a required effect. The MM record's `generationStatus: deferred` remains an intent-time record; it is never edited to claim HiFi completion. Record actual output identity, authorization and review separately in the existing Style Integration evidence. A missing generated asset required by a `motion` or `image + motion` intent keeps its evidence gate blocked until delivered or explicitly removed from scope. Image-only intents remain under connected-HiFi and H6 human media review, including authorization, actual output identity, placement and usage constraints; they do not use normal/reduced-motion receipts. CSS/WAAPI and GSAP serve Web implementation and HTML projections; native implementation uses its approved platform/framework tools and later native evidence.

## Annotated Animation Boundaries

For newly authored motion regions, keep `motionSpec` detail in the MM record or the existing direction/HiFi evidence: non-empty `scope`, `behavior`, `space`, `compact`, `playback` and `cost` descriptions. Scope names the whole region or exact element; behavior includes the end state; space includes reserved height/pinning/scroll need; compact describes phone behavior; playback includes loop, interruption and replay; cost names loading/performance and dependency limits. Existing trigger and reducedMotionFallback remain authoritative. A direction study may show the proposed effect or a visibly deferred placeholder. Never imply that annotated motion is implemented. New providers or dependencies keep their existing authorization/stack gates.

## Implementation Routing After Direction Selection

Pick the lowest route that delivers the approved effect.

Motion, GSAP, Three.js, Lottie and Rive are production dependencies. Use one only when the approved stack decision's `motion` layer includes it ([Motion Layer](../../product-definition-builder/references/frontend-stack-selection.md#motion-layer)). A stack decision without a `motion` row keeps the earlier rule: use a library only when the approved stack already names it. Otherwise return the choice to `product-definition-builder`. CSS transitions, the Web Animations API, the View Transitions API and CSS scroll-driven animations need no stack entry. The last two are progressive enhancement: content and tasks must be complete without them.

- Use CSS transitions or the Web Animations API for small, deterministic state feedback. Do not add GSAP merely because motion exists.
- Use Motion (route `Motion`) for springs, sequences, layout and exit animation, gestures, or simple scroll and in-view effects. React stacks use Motion for React.
- Load `gsap-core` when the approved effect needs a scripted tween, responsive matchMedia behavior, or precise reusable easing.
- Add `gsap-timeline` only when multiple approved movements need choreography or shared playback control.
- Add `gsap-scrolltrigger` only when the approved behavior is scroll-driven, pinned, scrubbed, or intersection-timed.
- Use Three.js (route `Three.js`; React Three Fiber in a React stack) only for an approved 3D region such as a product model, spatial data or a brand scene. Record its poster, the content shown when WebGL is unavailable, the asset budget and the reduced-motion behavior.
- Use Lottie (route `Lottie`; a `.lottie` or Lottie JSON file played by its runtime) for a designed vector animation or an illustration loop.
- Use Rive (route `Rive`; a `.riv` file with a state machine) when the illustration must respond to input or state.
- Neither Lottie nor Rive is for buttons, navigation, state feedback or accessibility behavior. Record the poster, the reduced-motion behavior and the file budget for each. The animation file is an asset with its own source, license and identity, separate from the route.
- Use Higgsfield MCP only when it is installed, its live capability has been observed, and the owner grants exact provider/action authorization for the generated or curated motion request. Treat it as a media provider, never as the implementation source for buttons, navigation, state feedback, or accessibility behavior. [Generated Clips And Models](#generated-clips-and-models) says how to get a usable asset.

For motion craft (timing, easing, choreography), consult `motion-doctrine` or Impeccable's animate guidance when available. They inform the author; `frontend-design` stays the single design author.

## Generated Clips And Models

A provider such as the Higgsfield MCP, which the owner has connected, gives media. It gives:

- still images;
- video clips from a few seconds up to about thirty, with a chosen first and last frame and optional audio; and
- 3D models as GLB, from an image or text, optionally with materials, a rig and a stock animation clip.

It does not give interface motion, Lottie or Rive files, or code. Control feedback, navigation and state changes stay on the code routes. Do not generate a product demonstration of the interface: generated footage invents copy and controls, and the rules reject both. Record the HiFi or the implementation instead.

The authorization rules in [Intent Before Assets](#intent-before-assets) and [Implementation Routing](#implementation-routing-after-direction-selection) apply to every step below.

1. **Order.** Generate after the static pass has passed the author self-check ([Composition Before Motion](#composition-before-motion)). Credits then do not go to a layout that still moves. Iterate on a draft or low-resolution tier when the provider has one. Produce the final asset once, for the candidate that goes to review.
2. **Looping clip** (hero or section background). Make or choose the key still first. Make the clip with that still as both first and last frame, so the loop has no seam. Use no audio and about five seconds. The still is the poster and the reduced-motion fallback.
3. **3D model.** The GLB is a provider asset. The scene uses the `Three.js` route under the stack rule. In HiFi, the approximation may be a short pre-rendered turntable clip of the same model.
4. **Preparation.** Remove the audio track unless the row approves sound. Encode for the web (for example H.264 MP4, plus WebM where the stack wants it) and size it to the row's performance budget. Inside HiFi, the [embedding limit](#hifi-embedding-limits) applies. This `ffmpeg` command is an example, not a required tool:

   ```text
   ffmpeg -i in.mp4 -an -c:v libx264 -crf 28 -vf scale=1280:-2 -movflags +faststart out.mp4
   ```

5. **Record** the fields that [HiFi Embedding Limits](#hifi-embedding-limits) lists, in the Style Integration evidence for that `MM-*` row.
6. **Failure.** A provider failure, or a result that breaks the rules, never authorizes a substitute treatment. Keep the typed static placeholder and name the gap.

## Motion Evidence Per Intent

Observe each required motion intent at one representative responsive target: the smallest approved target of its surface (the lowest viewport width, or the first listed size class). Evidence is:

- a trigger frame, taken when the declared trigger fires;
- an end-state frame, taken at the approved resting state; and
- a reduced-motion check that reads the computed animation and transition duration and confirms the end state arrives in place.

The normal receipt holds the frames and the reduced-motion receipt holds the check; each required intent gets both. Each receipt is validated as an offline receipt of that one intent, not as the HiFi surface check; the Typed motion transcript section of the [output contract](output-contract.md) names its sandbox and navigation rule. Video clips and frame sampling are optional supplements.

## HiFi Embedding Limits

HiFi pages allow only embedded `data:` media. Keep each embedded clip short and compressed (aim for about 2 MB per clip) and always include its poster. A small library such as Motion's `animate()` may be inlined when the page still passes the offline surface check. When a library cannot run inside HiFi, never rename, strip or obfuscate library code to pass. Three.js, Lottie and Rive are such libraries: the Three.js source contains network API names that the surface check rejects, and the Lottie and Rive runtimes cannot run in the closed page. Show the effect with a deterministic approximation instead: CSS 3D, canvas 2D, a CSS approximation or a short pre-rendered clip of the scene or animation. The approximation still needs its normal and reduced-motion receipts. Mark the row as `HiFi approximation — <library> verified in first implementation slice` in the Style Integration notes and the Harness UI evidence. The real library behavior becomes an implementation obligation, like native proof. The first implementation slice also [compares it with the approximation](../../delivery-harness/references/ui-implementation-contract.md#motion-approximation-comparison).

Generated assets remain provider-neutral in the canonical contract. Record the provider, the model or route when known, the provider's job or generation id, the prompt, each input image's repository path and SHA-256, the settings that change the result (duration, resolution, seed when the provider exposes one), the credits or cost spent against the approved limit, the output file's path and SHA-256, license or usage constraints, placement, fallback, and the review decision. A generated asset that invents copy, controls, states, routes, or product claims is rejected.
