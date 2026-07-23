# Output Contract

Produce a multi-file design package. Every platform (web, native iOS, native Android, Flutter, React Native, macOS, Windows, cross-platform desktop) uses the same file set — HTML is a visual demonstration medium here, used to SHOW what a screen looks like, not the target's production technology.

Always produce:

- `design-system.md`
- `visual-acceptance.md`
- One real, dependency-free static HTML file per important page/route/screen under `mockups/` (for example `mockups/dashboard.html`) — the primary mockup deliverable for every platform, styled to that platform's own visual conventions (see Platform-Conditional Vocabulary below) rather than defaulting to web styling for a native or desktop target. Link mockup pages to each other with plain relative `<a href>` links so the set reads as a connected clickable prototype.
- A slim `ui-mockups.md` index that points at those HTML files and carries the route → trace → test mapping (see below).

Do not produce `page-ui-matrix.md`; the route → breakpoint/size-class → state → component mapping is shown directly in the HTML, and the machine-checkable route → trace → test mapping lives in the `ui-mockups.md` index.

Default all artifact content to English unless the user explicitly asks for another language.

Use the templates in `assets/templates/` when creating these files: `MOCKUP_PAGE.template.html` for every page mockup (style it to the resolved platform), and the Markdown templates for the rest.

## Platform-Conditional Vocabulary

Two different things follow the resolved platform, and they are not the same artifact:

1. **The page mockup's visual styling** (`mockups/*.html`) — always real HTML/CSS, but styled to LOOK like the target platform: web uses ordinary web layout; iOS/macOS uses HIG cues (SF-Symbols-style glyphs, safe-area-style padding, iOS/macOS navigation and control shapes); Android uses Material cues (Material-Symbols-style glyphs, edge-to-edge layout, Material navigation and control shapes); desktop uses window chrome (title bar, menu bar, native-looking controls) instead of a browser viewport. This is a visual demonstration, not the real rendering engine — an "iOS-styled" HTML mockup does not run on iOS, it shows what the iOS screen should look like.
2. **The design-system's reference component code** (`design-system.md`'s "Example Component Reference Design Code" and icon-usage examples) — this is separate implementation guidance for whoever builds the real app, and uses the target's real language: `tsx`/React + Tailwind for web, SwiftUI (or UIKit/AppKit) for iOS/macOS, Jetpack Compose for Android, a Flutter widget for Flutter, a React Native component for React Native, WinUI/.NET (or a cross-platform toolkit) for Windows.

Icon family follows the platform in both places: web (Lucide, Heroicons, Phosphor, Tabler, Font Awesome, or similar), iOS/macOS (SF Symbols), Android (Material Symbols), Windows (for example Fluent UI System Icons), Flutter/React Native (the icon family matching whichever platform convention that build follows).

State the resolved platform in `design-system.md`'s Overview, then keep every icon, component-code, and breakpoint/size-class section consistent with it. Keep the web guidance available for a web target rather than removing it; it just stops being the default for every target.

When Claude Code Dynamic Workflow is used, treat its structured design package as a candidate source. The parent must resolve blocked roles and verifier findings, write the staged files, run the checks below, and preserve the existing publish approval gate.

When the user requests a runnable animation demonstration, also produce `motion-showcase.html` or bounded files under `motion-demos/`. Use `assets/templates/MOTION_SHOWCASE.template.html` as the dependency-free baseline unless the project stack or requested animation requires another implementation. Record every demo path in `design-system.md` and `ui-mockups.md`.

## `design-system.md`

Use this structure:

````markdown
# Design System: [Product Name]

## Overview
[Product archetype, audience, visual intent, density, tone, constraints, and source priority.]

## Source Inputs
| Source | Path / URL | Role | Notes |
| --- | --- | --- | --- |

## Builder UX Direction Handoff
Decision owner: [Human product/design owner or commissioning team]

| Dimension | Upstream direction | Status | Design-system expression | Evidence or validation need |
| --- | --- | --- | --- | --- |
| Experience priority | [Speed / clarity / guided completion / expert control / exploration / conversion / comprehension] | [selected / provisional / assumed] | [Hierarchy, component, content, or interaction consequence] | [User evidence / prototype test / none] |
| Guidance and control | [Direction] | [selected / provisional / assumed] | [System expression] | [Need] |
| Information density | [Direction] | [selected / provisional / assumed] | [System expression] | [Need] |
| Interaction and layout | [Direction] | [selected / provisional / assumed] | [System expression] | [Need] |
| Confirmation and recovery | [Direction] | [selected / provisional / assumed] | [System expression] | [Need] |

Builder approval proves direction conformance only. It does not prove usability; keep unsupported preferences provisional or assumed until separate user evidence exists.

## Product-Specific Visual Thesis
| DS ID | Cue / signature decision | Product or source basis | Upstream trace IDs | System expression | Avoid |
| --- | --- | --- | --- | --- | --- |
| DS-001 | [Stable design decision] | [Evidence] | PRD-001, UI-001, UX-001 | [Expression] | [Avoid] |

## Taste & Anti-Slop Guardrails
Taste statement: [One sentence naming the intended visual character and the concrete typography, composition, color, imagery, or interaction choices that create it.]

| Risk | Default rule | Allowed exception | Review test |
| --- | --- | --- | --- |

### Container & Border Rules
| Surface / region | Default treatment | Primary grouping cue | Border / elevation allowed for | Must avoid |
| --- | --- | --- | --- | --- |
| [Surface] | [open / background band / real container] | [spacing / alignment / background / divider / border / elevation] | [named interaction, hierarchy, state, data, or accessibility purpose] | [unsupported framing or stacked effects] |

## Content & Data Realism
[Domain vocabulary, representative data shapes and lengths, asset constraints, placeholder rules, and claims that must not be fabricated.]

## Landing Page Simplicity & Media Plan
Use this section when a public website, marketing page, or landing page is in scope. Keep one clear value proposition and one primary action in the first viewport. Give each section one job. Do not copy the whole PRD into the page.

| Section / region | Single job | Exact wording / display contract | Style direction | Image / media | Motion | Defer / exclude |
| --- | --- | --- | --- | --- | --- | --- |
| [Region] | [What the user must understand or do] | [Verbatim wording, or what to show + intended takeaway/action + source + constraints] | [Visual job; open/container/background/layout treatment; purpose] | [required / optional / none; purpose; source or creation need; responsive and static fallback] | [required / optional / none; purpose; trigger; reduced-motion fallback] | [Content that belongs elsewhere] |

## Color Palette

Harmony method: [complementary / analogous / monochromatic / triadic / brand-anchored, and why it fits the product-specific visual thesis]

| Token | Value / Direction | Tailwind / CSS reference | Usage | Contrast ratio (if text/UI pairing) |
| --- | --- | --- | --- | --- |

Record each text-on-background, text-on-surface, and text-on-accent pairing's actual computed WCAG 2.2 AA ratio (4.5:1 normal text, 3:1 large text/UI components) in the last column; adjust the token when a pairing fails rather than recording a failing ratio. When dark mode is in scope, add its own token rows with their own contrast ratios, not an assumed inversion of the light tokens. See `visual-decision-guide.md`'s Color Palette Decision for the full method, the colorblind-safety rule for semantic colors, and when to offer `frontend-design` for an expert pairing pass.

## Typography
Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

Pairing rationale: <why these families/roles work together, and the type-scale ratio or logic tying the sizes into one system>

| Role | Font / family | Size | Weight | Line height | Line-height ratio | Usage |
| --- | --- | --- | --- | --- | --- | --- |

Record each role's actual line-height ratio (line height ÷ font size) in the last column and check it against `visual-decision-guide.md`'s Typography Decision thresholds: at least 1.5x for body/paragraph text (WCAG 2.2 Success Criterion 1.4.12) and at least 1.1x for heading/display roles. Adjust the token when a role fails rather than recording a failing ratio. See `visual-decision-guide.md`'s Typography Decision for the full method, the type-scale rationale requirement, and when to offer `frontend-design` for an expert pairing pass.

## Iconography System

### Market Scan & Decision
| Candidate | Official source | Visual fit | Required-icon coverage | Integration | License / checked date | Decision |
| --- | --- | --- | --- | --- | --- | --- |

### Icon Tokens
| Token | Optical size | Stroke / weight / fill | Color behavior | Usage |
| --- | --- | --- | --- | --- |

### Semantic Icon Inventory
| Intent / object | Visible label | Icon name | Source | Token / variant | State behavior | Accessibility behavior |
| --- | --- | --- | --- | --- | --- | --- |

### Source & Exception Rules
[Primary package/import path or asset source, version policy, tree-shaking or subsetting, RTL handling, brand-icon source, custom-icon construction rules, and approved secondary-library exceptions.]

### Example Icon Usage Code
Include stack-appropriate code using the chosen primary library. Show one action with visible text and one icon-only action. Use the exact package import and icon token, place the accessible name on the control, hide a redundant glyph from assistive technology, and define tooltip behavior for the icon-only control. Match the resolved platform: the `tsx`/web example below applies to a web target; for a native or desktop target, show the equivalent shape in the platform's language and icon family (for example SwiftUI with SF Symbols for iOS/macOS, Jetpack Compose with Material Symbols for Android, a Flutter widget with the platform-matched icon family, or WinUI/.NET with a desktop icon family), using that platform's accessibility API for the accessible name.

```tsx
// Example structure only. Replace with the selected library and project primitives.
import { ExampleIcon } from "<approved-icon-package>";

export function IconActions() {
  return (
    <>
      <button><ExampleIcon aria-hidden="true" className="<icon-token>" />Visible action</button>
      <button aria-label="Descriptive action"><ExampleIcon aria-hidden="true" className="<icon-token>" /></button>
    </>
  );
}
```

## Spacing System
| Token | Value | Usage |
| --- | --- | --- |

## Component Styles
| DS ID | Component | Variants | States | Upstream UI / ARCH IDs | Usage Rules |
| --- | --- | --- | --- | --- | --- |

## Shadows & Elevation
| Token | Value / Direction | Usage |
| --- | --- | --- |

## Motion System

### Motion Principles & Stack
| Layer / purpose | Technology | Why | Dependency / version | Performance constraints | Fallback |
| --- | --- | --- | --- | --- | --- |

### Motion Tokens
| Token | Duration | Easing / spring | Distance / scale | Usage | Reduced-motion value |
| --- | --- | --- | --- | --- | --- |

### Motion Pattern Inventory
| Motion ID | Surface / component | Purpose | Trigger | Properties | Token / sequence | Repeat / interruption | Responsive and reduced-motion behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Hero Choreography
| Step | Element | Start / relation | From → to | Purpose | Mobile behavior | Reduced-motion behavior |
| --- | --- | --- | --- | --- | --- | --- |

### Motion Demo Index
| Demo ID | Pattern / page | Artifact path | Stack | Controls | Status |
| --- | --- | --- | --- | --- | --- |

### Example Motion Implementation Code
Include a static-first, stack-appropriate implementation for one important pattern. The final DOM/CSS state must remain usable if animation code does not load. Show reduced-motion handling and cleanup or cancellation when the stack requires it.

## Border Radius
| Token | Value | Usage |
| --- | --- | --- |

## Opacity & Transparency
| Token / Pattern | Value | Usage |
| --- | --- | --- |

## Layout Rules
[Grid, max widths, navigation layout, responsive breakpoints.]

## Common Tailwind CSS Usage In Project
Use this section for a web target. For a native or desktop target, replace it with the platform's recurring styling patterns (for example SwiftUI view modifiers and `Color`/`Font` tokens, Compose `Modifier` chains and `MaterialTheme` tokens, Flutter `ThemeData`/widget style patterns, or WinUI resource/style patterns), keeping the same purpose: the reusable style patterns implementers apply.

| Pattern | Classes / tokens | Usage | Notes |
| --- | --- | --- | --- |

## Example Component Reference Design Code
Include a small reference component that demonstrates the design rules. Use the resolved platform's stack and mark framework assumptions clearly: `tsx`/Tailwind for a web target, SwiftUI for iOS/macOS, Jetpack Compose for Android, a Flutter widget for Flutter, or WinUI/.NET for Windows desktop. The `tsx` example below is the web case.

```tsx
// Example only. Adapt to the target project stack.
export function ExampleContentSection() {
  return <section className="[open layout classes]">...</section>;
}
```

## Interaction Rules
[Focus, hover, active, loading, disabled, selected, expanded, and validation feedback.]

## Accessibility Rules
[Contrast, focus, keyboard, text sizing, motion.]

## Assumptions
- [Assumption]

## Open Questions
- [Question]
````

## `page-ui-matrix.md` — retired

Do not produce this file for any platform. The route → breakpoint/size-class → state → component mapping is shown directly in the `mockups/*.html` files; the machine-checkable route → trace → test mapping and any annotation the HTML can't carry live in the `ui-mockups.md` index below.

## `mockups/*.html`

For every platform, the primary mockup deliverable is one real, static HTML file per important page/route/screen under `mockups/`, named by route or screen (for example `mockups/dashboard.html`, `mockups/settings.html`). Start from `assets/templates/MOCKUP_PAGE.template.html`. Each file must:

- Be dependency-free and runnable in a browser with no build step and no external CDN, exactly like `MOTION_SHOWCASE.template.html`. Inline the design-system tokens as CSS custom properties; you may inline the same Tailwind-style utility classes the design system documents for a web target, but do not fetch anything over the network.
- Be styled to the resolved platform's own visual conventions (see Platform-Conditional Vocabulary above) — this is a visual demonstration medium, not the target's rendering engine. A native or desktop mockup should visually read as that platform, not as a generic web page.
- Render the page's real content with exact wording preserved (no generic mockup placeholders), using the design-system colors, typography, spacing, icons, and components.
- Represent each required state (ready, loading, empty, error, disabled, permission denied, long content) as a visible, labeled `<section>` stacked in the same file — a "state gallery." Every state stays visible with no JavaScript, so the file is reviewable and diff-able as-is. A small JS toggle to switch between states is an optional enhancement layered on top, never the only way to see a state.
- Express responsive/size-class behavior with real CSS media queries in the file, not a separate breakpoint column. The reviewer resizes the browser to see the size range.
- Link to other mockup pages with plain relative `<a href="other-page.html">` links where the real product would navigate between them, so the set of files reviews as a connected clickable prototype.
- Carry the route's trace IDs and DS IDs in an HTML comment at the top of the file (for example `<!-- UI-001 | PRD-001, UX-001, ARCH-001 | DS-001, DS-002 -->`) so the mapping survives in the artifact itself.

Treat these files as reference/prototype artifacts, not production code; `fullstack-harness-engineering` reimplements each screen in the project's real framework (a web stack, SwiftUI, Jetpack Compose, a Flutter widget tree, or WinUI/.NET) using the HTML as the visual and structural source of truth, never as source to port directly.

## `ui-mockups.md`

`ui-mockups.md` is a slim index into the `mockups/*.html` files — the machine-checkable route → trace mapping, plus any annotation the HTML itself can't carry (rationale, asset sourcing, motion choreography). Use this structure:

```markdown
# UI Mockups Index: [Product Name]

| UI ID | Page / screen | Mockup HTML | Upstream trace IDs | DS IDs | States represented | Motion demo | TEST IDs / acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| UI-001 | /example | mockups/example.html | PRD-001, UX-001, ARCH-001 | DS-001 | ready/loading/empty/error | motion-showcase.html#example | TEST-VIS-001 |

## Page Notes

Add one block per page only for what the HTML mockup itself cannot show — do not restate what's already visible in the file.

### [Page Name]
- Product-specific decisions: [signature cues applied; generic patterns intentionally avoided and why]
- Content realism: [representative content/data source, or exact copy / display contract for content that is unavailable or data-driven]
- Container and border treatment: [the default open-layout treatment, and the named purpose of any visible border, accent rail, nested frame, or elevation — a border with no stated purpose fails review]
- Content budget (landing/content-heavy pages only): [single job per region, and what content is intentionally deferred or excluded]
- Asset requirements: [image/media/icon needs — type, required / optional / none, purpose, source or creation need, responsive/static fallback]
- Motion choreography: [element, trigger, sequence/token, reduced-motion fallback — if not already in the motion system]
- Open questions / assumptions: [anything unresolved for this page]
```

## `visual-acceptance.md`

Use this structure:

```markdown
# Visual Acceptance: [Product Name]

## Review Gates
| TEST ID | Gate | Required | Upstream trace IDs | Expected Signal | Evidence |
| --- | --- | --- | --- | --- | --- |
| TEST-VIS-001 | Design system conformance | yes | DS-* | Components use approved tokens and variants | screenshot / code review |
| TEST-VIS-002 | Builder UX Direction conformance | when a Builder UX Direction exists | UX-*, DS-* | Selected decisions are implemented; provisional or assumed decisions and conflicts remain explicit | source review / design review |
| TEST-VIS-003 | Page UI conformance | yes | UI-*, DS-* | Implemented page matches mockup source | screenshot / trace |
| TEST-VIS-004 | Responsive behavior | yes | UI-* | No overflow or broken hierarchy at required breakpoints | screenshot |
| TEST-VIS-005 | State coverage | yes | UI-*, PRD-* | Required loading/empty/error/disabled states exist | screenshot / test |
| TEST-VIS-006 | Accessibility basics | yes | UX-*, UI-* | Focus, computed WCAG 2.2 AA contrast ratio for every recorded text/UI color pairing, computed line-height ratio for every typography role (not just visual intent), labels, keyboard path checked | audit / screenshot |
| TEST-VIS-007 | Icon system conformance | yes | DS-* | Icons use the approved source, tokens, semantics, labels, and documented exceptions | screenshot / code review |
| TEST-VIS-008 | Motion system conformance | yes | DS-*, UI-* | Motion uses approved purpose, tokens, choreography, responsive behavior, and reduced-motion fallbacks, and covers every in-scope non-hero pattern | live demo / code review |
| TEST-VIS-009 | Motion performance | yes | DS-*, UI-* | Critical content is static-first; routine motion avoids layout-heavy properties and does not block interaction | performance trace / live demo |
| TEST-VIS-010 | Taste and anti-slop review | yes | DS-* | The taste statement is visible, product-specific cues recur, and unsupported AI-UI pattern clusters are absent | screenshot / checklist |
| TEST-VIS-011 | Rendered visual review loop | when visual artifacts or an implementation exist | UI-*, DS-* | Required breakpoint renders were critiqued; the highest-impact failure was repaired and rechecked | before/after screenshots / review notes |
| TEST-VIS-012 | Spec-only review path | when rendered visuals do not exist | UI-*, DS-* | The Markdown package was checked for taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and no visual-verification claim is made | text review notes |
| TEST-VIS-013 | Content specificity | yes | PRD-*, UI-* | Every visible region preserves exact wording or a bounded display contract; generic placeholder copy is absent | product source / mockup review |
| TEST-VIS-014 | Container and border purpose | yes | DS-*, UI-* | Regions default to open layouts; every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose | screenshot / border inventory / design review |
| TEST-VIS-015 | Landing-page simplicity | when applicable | PRD-*, UI-* | First viewport has one clear message and primary action; each section has one job; secondary detail is deferred | content review / screenshot |
| TEST-VIS-016 | Media and motion traceability | when applicable | UI-*, DS-* | Every relevant region labels image/media and motion as required, optional, or none with a purpose and fallback | design system / mockup review |

## Page Acceptance
| UI ID | Page / route | Source | TEST IDs | Required evidence | Status |
| --- | --- | --- | --- | --- | --- |

## Known Visual Risks
| Risk | Impact | Decision |
| --- | --- | --- |
```

## Quality Checklist

Before finalizing, verify:

- `design-system.md` and `visual-acceptance.md` are present, one real `mockups/*.html` file exists per important page/route/screen, and `ui-mockups.md` is the slim index into them (`page-ui-matrix.md` is not produced).
- The resolved platform is stated in `design-system.md`'s Overview, and the icon family, component-code language, breakpoint/size-class vocabulary, and styling-pattern section match it rather than defaulting to web/Tailwind.
- Upstream `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, and `TEST-*` IDs are preserved. Design decisions and components use stable `DS-*` IDs, and every page and visual gate carries the IDs it implements or verifies.
- `design-system.md` defines overview, a product-specific visual thesis, taste and anti-slop guardrails, container and border rules, content/data realism, color palette, typography, iconography, spacing, component styles, shadows/elevation, a complete motion system, border radius, opacity/transparency, common Tailwind/CSS usage, example component reference design code, layout rules, states, and accessibility rules.
- For a UI-bearing product, `design-system.md` identifies the human Builder UX Direction owner, maps every selected/provisional/assumed direction to a concrete system expression, and names the evidence or validation need.
- Builder direction conformance is not presented as usability validation; unsupported preferences remain explicit hypotheses.
- The visual thesis includes three to five concrete brand or context cues, at least two recurring signature decisions, and avoided defaults tied to product evidence or explicit assumptions.
- The taste statement names a concrete visual character and the compositional choices that create it; it does not stop at generic adjectives.
- The container and border table defaults ordinary regions to open layouts, chooses one primary grouping cue per nesting level, and gives every visible frame or elevation a named purpose.
- The iconography section records a current official-source market scan, evidence-based primary choice, actual required-icon coverage, token rules, semantic inventory, package or asset source, checked date, license, accessibility behavior, and documented exceptions.
- The iconography section includes stack-appropriate reference code for labeled and icon-only actions using the exact approved import, tokens, accessible-name ownership, decorative hiding, and tooltip behavior.
- The motion system defines purpose, stack choice, tokens, pattern inventory, triggers, interruption/repeat rules, responsive variants, reduced-motion behavior, performance limits, a stated motion-personality archetype justified against the taste statement, and hero choreography when a hero exists.
- Every non-hero motion surface identified during discovery (modal/sheet, list reorder/add/remove, toast, skeleton, form validation, drag-and-drop, scroll reveal, empty state, chart/data-viz) has a Motion Pattern Inventory row with trigger, properties, token, and reduced-motion fallback, or is explicitly marked `n/a`.
- Requested runnable motion showcases exist, work without production dependencies unless justified, expose preview controls, and keep essential content usable when animation is unavailable.
- Every important page/route/screen has a real `mockups/*.html` file, styled to the resolved platform's own conventions, that renders exact content, shows each required state as a visible labeled section, expresses responsive/size-class behavior with CSS media queries, links to related pages, and carries its trace/DS IDs in a top-of-file comment; the `ui-mockups.md` index maps every page to its HTML file, trace IDs, DS IDs, represented states, and acceptance TEST IDs.
- Every mockup preserves product-source exact wording or a bounded display contract for every visible region; generic mockup placeholders do not pass validation.
- Every mockup resolves each required style label, states the container and border treatment, and does not default regions to framed panels, nested cards, or colored accent rails without a named purpose.
- When a landing page is in scope, `design-system.md` and `ui-mockups.md` define the first-viewport message and action, one job per section, content to defer, and per-region image/media/motion status.
- `visual-acceptance.md` defines implementation-verifiable visual gates, including taste, unsupported AI-UI pattern clusters, and container and border purpose.
- Missing brand assets, mockups, states, or breakpoints are explicit assumptions or open questions.
- When Dynamic Workflow was used, every required design role has an explicit result, failed agents remain blocked roles, and taste/trace verifier findings are resolved or recorded before finalization. Workflow output is a candidate and does not itself prove rendered visual conformance.
- The package does not create product scope, backend architecture, harness mission maps, or E2E evidence registers.
- The package is validated in `docs/product/.design-staging/<run-id>/`; exact overwrites and archive moves are authorized before publication, or the staged package remains unchanged awaiting approval.

## Taste & Anti-Slop Review Checklist

Before finalizing, verify:

- The interface remains understandable when decorative effects are removed.
- The one-sentence taste statement is visible in the hierarchy and at least two recurring decisions, not only in the logo or adjectives.
- At least two signature decisions recur across the system and important pages without becoming repetitive decoration.
- Ordinary content regions default to open layouts, and each nesting level uses one primary grouping cue unless a documented reason requires more.
- Every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose; the removal test eliminates treatments that add no information.
- Repeated bordered cards, nested frames, colored side rails, accent stripes, dashed outlines, and double frames are absent unless every use has a named semantic or approved brand role.
- No uniform default border is applied to every button, input, image, and avatar regardless of role; each bordered element has its own documented purpose.
- Radii, pills, shadows, gradients, glass effects, icons, and motion each have a product, hierarchy, or interaction rationale.
- Page composition follows task priority and content shape instead of defaulting to centered heroes, uniform card grids, or equal visual weight.
- Landing pages do not summarize the entire PRD. The first viewport has one message and primary action, and every later section earns its place with one clear job.
- Images, media, and animation are tied to a named user or product purpose; decorative assets are not added merely to fill space.
- Labels, sample data, imagery, and content lengths reflect the domain; unsupported claims, metrics, testimonials, logos, and stat-counter badges (for example "10K+ users," "99.9% uptime") are not fabricated.
- The font pairing and icon library are named as deliberate choices with a brand or coverage reason, not an unexamined default such as Inter/Poppins/Manrope/Geist or Lucide/Heroicons/Font Awesome kept only because it shipped with the starting template.
- Familiar patterns retained for usability, platform convention, or brand fit have a documented reason rather than being removed mechanically.
- When visual artifacts or an implementation exist, required breakpoint renders were critiqued, the highest-impact failure was repaired, and the package was rechecked against these gates. For a spec-only package, a text-only conformance review covers taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and the package makes no visual-verification claim.
