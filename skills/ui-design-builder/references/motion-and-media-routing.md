# Motion And Media Routing

## Intent Before Assets

Ask the human owner whether shipped motion is:

- `not_required`: no decorative motion beyond platform-standard functional feedback;
- `functional_only`: motion explains state, progress, continuity, or spatial relationship;
- `expressive`: selected surfaces may use motion for hierarchy or brand, without hiding content; or
- `recommend`: the UI Design Builder proposes one of the above from product evidence for owner approval.

Generated motion, autoplay or sound, material performance budgets, accessibility exceptions, and new product scope always return to the owner. Every motion decision includes an equivalent reduced-motion path.

For page-specific defaults, use `page-design-profiles.md`. Landing/portfolio expressive motion is proposed through this same intake and becomes required only when selected; accepted no-motion decisions stay valid. Once selected, demonstrate the actual effect and reduced-motion equivalent under the rules below.

After Wireframe Validation, a representative direction study may play a small deterministic motion option locally with CSS/WAAPI or GSAP when that stays within the approved Motion and Media scope, with normal and reduced-motion behavior. It helps the owner judge selection only; it is not Required motion evidence, native proof, or permission to invoke a generation provider. A provider route stays deferred until after direction selection receives its exact provider/action authorization, and the selected effect still needs complete final HiFi motion evidence.

## Typed Wireframe Placeholders

For every marquee or media-bearing screen region, record one treatment:

| Treatment | Wireframe representation | Later route |
| --- | --- | --- |
| `none` | No media placeholder | No provider or animation skill |
| `image` | Labeled static frame with purpose and content contract | Existing asset or a later explicitly authorized image-generation pass |
| `motion` | Labeled poster/frame with trigger, purpose, duration intent, and reduced-motion fallback | CSS/WAAPI, GSAP, or an explicitly authorized generation provider |
| `image + motion` | Labeled static base plus motion layer and fallback | Approved image route plus approved motion route |

The wireframe contains no final asset and invokes no provider. Its `mediaIntent` record uses a stable `id` equal to its `MM-*` row plus `treatment`, `purpose`, `trigger`, `draftPrompt`, `source`, `reducedMotionFallback`, `generationRoute`, and `generationStatus: deferred`.

An explicit hero or animation request is a required intent, not optional inspiration. A hero intent still records the product message, CTA, composition, media treatment, and mobile destination; the wireframe hero remains a grayscale placeholder. An admin or native surface does not receive a marketing hero unless the owner explicitly requests that surface treatment.

After direction selection, a deterministic `motion` or `image + motion` row must demonstrate its trigger, behavior, end state, and reduced-motion fallback in the HiFi review. A static poster, gray placeholder, screenshot, or documented note cannot satisfy a required effect. The frozen wireframe `generationStatus: deferred` remains an intent-time record; it is never edited to claim HiFi completion. Record actual output identity, authorization and review separately in the existing Style Integration evidence. A missing generated asset required by a `motion` or `image + motion` intent keeps its evidence gate blocked until delivered or explicitly removed from scope. Image-only intents remain under connected-HiFi and H6 human media review, including authorization, actual output identity, placement and usage constraints; they do not use normal/reduced-motion receipts. CSS/WAAPI and GSAP serve Web implementation and HTML projections; native implementation uses its approved platform/framework tools and later native evidence.

## Annotated Animation Boundaries

For newly authored motion regions, attach `motionSpec` to the existing `mediaIntent`: non-empty `scope`, `behavior`, `space`, `compact`, `playback` and `cost` descriptions. Scope names the whole region or exact element; behavior includes the end state; space includes reserved height/pinning/scroll need; compact describes phone behavior; playback includes loop, interruption and replay; cost names loading/performance and dependency limits. Existing trigger and reducedMotionFallback remain authoritative. The canonical wireframe shows these as switchable reviewer annotations over the affected region and retains a visibly deferred placeholder. Never imply that annotated motion is implemented. New providers or dependencies keep their existing authorization/stack gates.

## Implementation Routing After Wireframe Validation

- Use CSS transitions or the Web Animations API for small, deterministic state feedback. Do not add GSAP merely because motion exists.
- Load `gsap-core` when the approved effect needs a scripted tween, responsive matchMedia behavior, or precise reusable easing.
- Add `gsap-timeline` only when multiple approved movements need choreography or shared playback control.
- Add `gsap-scrolltrigger` only when the approved behavior is scroll-driven, pinned, scrubbed, or intersection-timed.
- Use Higgsfield MCP only when it is installed, its live capability has been observed, and the owner grants exact provider/action authorization for the generated or curated motion request. Treat it as a media provider, never as the implementation source for buttons, navigation, state feedback, or accessibility behavior.

Generated assets remain provider-neutral in the canonical contract. Record the prompt, provider, model or route when known, output identity, license or usage constraints, placement, fallback, and review decision. A generated asset that invents copy, controls, states, routes, or product claims is rejected.
