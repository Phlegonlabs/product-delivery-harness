# Motion And Media Routing

## Intent Before Assets

Ask the human owner whether shipped motion is:

- `not_required`: no decorative motion beyond platform-standard functional feedback;
- `functional_only`: motion explains state, progress, continuity, or spatial relationship;
- `expressive`: selected surfaces may use motion for hierarchy or brand, without hiding content; or
- `recommend`: the UI Design Builder proposes one of the above from product evidence for owner approval.

Generated motion, autoplay or sound, material performance budgets, accessibility exceptions, and new product scope always return to the owner. Every motion decision includes an equivalent reduced-motion path.

## Typed Wireframe Placeholders

For every marquee or media-bearing screen region, record one treatment:

| Treatment | Wireframe representation | Later route |
| --- | --- | --- |
| `none` | No media placeholder | No provider or animation skill |
| `image` | Labeled static frame with purpose and content contract | Existing asset or a later explicitly authorized image-generation pass |
| `motion` | Labeled poster/frame with trigger, purpose, duration intent, and reduced-motion fallback | CSS/WAAPI, GSAP, or an explicitly authorized generation provider |
| `image + motion` | Labeled static base plus motion layer and fallback | Approved image route plus approved motion route |

The wireframe contains no final asset and invokes no provider. Its `mediaIntent` record uses a stable `id` equal to its `MM-*` row plus `treatment`, `purpose`, `trigger`, `draftPrompt`, `source`, `reducedMotionFallback`, `generationRoute`, and `generationStatus: deferred`.

## Implementation Routing After Wireframe Approval

- Use CSS transitions or the Web Animations API for small, deterministic state feedback. Do not add GSAP merely because motion exists.
- Load `gsap-core` when the approved effect needs a scripted tween, responsive matchMedia behavior, or precise reusable easing.
- Add `gsap-timeline` only when multiple approved movements need choreography or shared playback control.
- Add `gsap-scrolltrigger` only when the approved behavior is scroll-driven, pinned, scrubbed, or intersection-timed.
- Use Higgsfield MCP only when it is installed, its live capability has been observed, and the owner grants exact provider/action authorization for the generated or curated motion request. Treat it as a media provider, never as the implementation source for buttons, navigation, state feedback, or accessibility behavior.

Generated assets remain provider-neutral in the canonical contract. Record the prompt, provider, model or route when known, output identity, license or usage constraints, placement, fallback, and review decision. A generated asset that invents copy, controls, states, routes, or product claims is rejected.
