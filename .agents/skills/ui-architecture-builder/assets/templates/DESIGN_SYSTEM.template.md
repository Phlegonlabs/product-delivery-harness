# Design System: <product name>

## Overview

<Product archetype, audience, visual intent, density, tone, constraints, and source priority.>

<Resolved platform (web, native iOS, native Android, Flutter, React Native, macOS, Windows, or cross-platform desktop). The platform sets the vocabulary for the sections below: icon family, component-code language, breakpoint vs. size-class model, and the styling-pattern section. Do not default to web/Tailwind for a native or desktop target — see references/output-contract.md "Platform-Conditional Vocabulary".>

## Source Inputs

| Source | Path / URL | Role | Notes |
|---|---|---|---|
| PRD | <path> | product source | <notes> |
| Wireframes | <path> | structure source | <notes> |
| Brand / reference | <path or URL> | visual source | <notes> |

## Rendered HTML Projection

Artifact: `docs/product/design/design-system.html`

This Markdown file is the semantic authority for token values and visual decisions. `ui-registry.json` is the authority for registered closed sets. `design-system.html` is a dependency-free rendered projection generated from both; its token block copies their resolved values for rendering and must not introduce tokens, primitives, variants, states, or parameters.

| Projection coverage | IDs | Parameters | Status |
|---|---|---|---|
| Typography hierarchy and paragraph styles; links; buttons and all variants/states; form controls; labels/help/error text; cards/surfaces; navigation; alerts/status; icons; spacing/layout; colors/tokens; applicable motion; responsive behavior | <token + primitive/component + variant IDs as applicable> | <implementation-relevant values or named parameters beside each rendered specimen> | <complete / gaps> |

Every rendered specimen's reproduction block uses the exact fields `IDs`, `Parameters`, `States`, `Responsive`, `Accessibility`, `Use`, and `Do not use`.

## Builder UX Direction Handoff

Decision owner: <human product/design owner or commissioning team>

| Dimension | Upstream direction | Status | Design-system expression | Evidence or validation need |
|---|---|---|---|---|
| Experience priority | <direction> | <selected / provisional / assumed> | <hierarchy, component, content, or interaction consequence> | <user evidence, prototype test, or none> |
| Guidance and control | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Information density | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Interaction and layout | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Confirmation and recovery | <direction> | <selected / provisional / assumed> | <system expression> | <need> |

Builder approval proves direction conformance only, not usability. Keep unsupported preferences provisional or assumed until separate user evidence exists.

## Frontend Design Preference & HTML Exploration

Status: <not used / preference discovery / candidates awaiting comparison / selected HTML awaiting approval / approved / rejected>

### Visual Preference Brief

Decision owner: <human product/design owner>
Ask User evidence: <question/answer record or n/a>
Purpose: <what the interface must help people do>
Tone: <product-specific direction, not a fixed style label>
Constraints: <brand, platform, content, accessibility, and performance limits>
Differentiation: <what should make this product recognizable>

### Candidate Direction Comparison

| Direction ID | Same representative screens / UI IDs | HTML paths | Material differentiators | Human decision |
|---|---|---|---|---|
| <direction ID or n/a> | <the same one or two screen names and exact authorized UI-* IDs> | <complete dependency-free HTML paths> | <material visual axes plus a structural fingerprint; changing only color does not count> | <selected / rejected / cues requested for mix> |

Hallmark status: <loaded / unavailable / not requested>
Hallmark candidate audits: <exact `hallmark-audit.md` paths and dispositions, or n/a; reports are read-only review evidence>

### Approved Selected HTML

Selected path: <exact `visual-directions/selected/` path or n/a>
Selection method: <direct selection / mixed and consolidated / n/a>
Approval owner: <human product/design owner; never an agent or delegated selector>
Approval evidence: <explicit approval record or n/a>
Selected HTML manifest: <ordered `{ ui_id, html_path, sha256 }` entries, one per representative screen, or n/a>
Approval manifest SHA-256: <lowercase 64-character digest shown in the approval evidence, or n/a>
Parent byte verification: <`selected_files_verification` status, verified file count, matching manifest SHA-256, and evidence that the parent read and hashed every selected file immediately before launch, or n/a>
Selected Hallmark audit: <exact `visual-directions/selected/hallmark-audit.md` path and disposition, or unavailable / n/a>

### Token Extraction Trace

| Selected HTML evidence | Extracted tokens | Extracted primitives / components | Recipes / registry / final mockups |
|---|---|---|---|
| <element, selector, screenshot, or measured repeated value> | <token IDs and actual values> | <DS IDs and closed variants> | <recipe IDs, registry entries, and canonical mockups> |

Exploration evidence: <Archive / Retain / n/a> — <exact final archive or retained `visual-directions/` path; `pending publication approval` is allowed only in staging>

Candidate and selected HTML, selected-file manifests, and Hallmark reports are non-canonical exploration evidence. Record `n/a — exploration not requested or not authorized` when unused. When used, include exactly two or three materially and structurally different directions for the same one or two screens. Tokens are extracted only after the human explicitly approves the selected HTML's exact manifest digest, the parent re-reads and hashes every selected file, and the Dynamic Workflow recomputes the canonical manifest digest. Any byte, canonical path, order, or UI-ID mapping change invalidates approval. When exploration is `not used` or `rejected`, derive from recorded product inputs and explicit visual assumptions and do not claim approved-HTML extraction. The published package records the final exploration evidence path, and implementation consumes only the extracted package.

## Product-Specific Visual Thesis

| DS ID | Cue / signature decision | Product or source basis | Upstream trace IDs | System expression | Avoid |
|---|---|---|---|---|---|
| DS-001 | <concrete cue or recurring decision> | <evidence or explicit assumption> | PRD-001, UI-001, UX-001 | <tokens, components, layouts, imagery, or motion> | <unsupported generic default> |

## Taste & Anti-Slop Guardrails

Taste statement: <one sentence naming the intended visual character and the concrete typography, composition, color, imagery, or interaction choices that create it>

| Risk | Default rule | Allowed exception | Review test |
|---|---|---|---|
| <generic or AI-UI pattern risk> | <product-specific rule> | <evidence-based exception> | <how to verify> |
| Repeated bordered panels with a colored side rail or accent stripe | Do not use as a generic section treatment | Named state, selection, priority, category, or approved brand motif | Every use has a documented semantic or brand role |
| Uniform default border on every button, input, image, and avatar | Border only where rule 4 of Container & Border Decision Rules applies | Control boundary, data structure, focus, selection, validation, or status | Removal test leaves hierarchy and comprehension intact |
| Unexamined default font pairing (Inter/Poppins/Manrope/Geist) or default icon library (Lucide/Heroicons/Font Awesome) | Name the choice as deliberate with a brand or coverage reason | Evidence-based selection matching the product's audience and content | Taste statement cites the concrete typography/icon choice and why |

### Container & Border Rules

| Surface / region | Default treatment | Primary grouping cue | Border / elevation allowed for | Must avoid |
|---|---|---|---|---|
| Ordinary content section | open | spacing | n/a | decorative frame, nested card, accent rail |
| <surface> | <open / background band / real container> | <spacing / alignment / background / divider / border / elevation> | <named interaction, hierarchy, state, data, or accessibility purpose> | <unsupported framing or stacked effects> |

## Content & Data Realism

<Domain vocabulary, representative data shapes and lengths, asset constraints, placeholder rules, and claims that must not be fabricated.>

## Landing Page Simplicity & Media Plan

<Use when a public website, marketing page, or landing page is in scope. Keep one clear value proposition and one primary action in the first viewport. Give each section one job.>

| Section / region | Single job | Exact wording / display contract | Style direction | Image / media | Motion | Defer / exclude |
|---|---|---|---|---|---|---|
| <region> | <what the user must understand or do> | <verbatim wording, or what to show + intended takeaway/action + source + constraints> | <visual job; open/container/background/layout treatment; purpose> | <required / optional / none; purpose; source or creation need; responsive and static fallback> | <required / optional / none; purpose; trigger; reduced-motion fallback> | <content that belongs elsewhere> |

## Color Palette

Harmony method: <complementary / analogous / monochromatic / triadic / brand-anchored, and why it fits the product-specific visual thesis>

| Token | Value / Direction | Tailwind / CSS reference | Usage | Contrast ratio (if text/UI pairing) |
|---|---|---|---|---|
| Background | <value> | <class or CSS var> | <usage> | <n/a> |
| Surface | <value> | <class or CSS var> | <usage> | <n/a> |
| Text | <value> | <class or CSS var> | <usage> | <e.g. 7.2:1 on Background> |
| Accent | <value> | <class or CSS var> | <usage> | <e.g. 4.8:1 on Background> |
| Border | <value> | <class or CSS var> | <usage> | <n/a> |
| Success / warning / danger | <value> | <class or CSS var> | <usage> | <ratio on their usual background, plus the non-color cue used to keep them colorblind-safe> |

## Typography

Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

Pairing rationale: <why these families/roles work together, and the type-scale ratio or logic tying the sizes below into one system>

| Role | Font / family | Size | Weight | Line height | Line-height ratio | Usage |
|---|---|---|---|---|---|---|
| Display / page title | <font> | <size> | <weight> | <line height> | <e.g. 1.15 (heading floor 1.1)> | <usage> |
| Section heading | <font> | <size> | <weight> | <line height> | <e.g. 1.2 (heading floor 1.1)> | <usage> |
| Body | <font> | <size> | <weight> | <line height> | <e.g. 1.5 (WCAG 1.4.12 minimum)> | <usage> |
| Caption / metadata | <font> | <size> | <weight> | <line height> | <e.g. 1.5 (WCAG 1.4.12 minimum)> | <usage> |

## Iconography System

### Market Scan & Decision

| Candidate | Official source | Visual fit | Required-icon coverage | Integration | License / checked date | Decision |
|---|---|---|---|---|---|---|
| <icon set> | <official URL> | <fit> | <pass / gaps> | <package, SVG, font, or platform API> | <license / YYYY-MM-DD> | <primary, exception, or rejected> |

### Icon Tokens

| Token | Optical size | Stroke / weight / fill | Color behavior | Usage |
|---|---|---|---|---|
| <token> | <size> | <setting> | <currentColor or semantic token> | <usage> |

### Semantic Icon Inventory

| Intent / object | Visible label | Icon name | Source | Token / variant | State behavior | Accessibility behavior |
|---|---|---|---|---|---|---|
| <action, status, navigation, or domain object> | <label or none> | <exact name> | <library or custom source> | <token / variant> | <selected, disabled, RTL, etc.> | <hidden, named control, tooltip, etc.> |

### Source & Exception Rules

<Primary package/import path or asset source, version policy, tree-shaking or subsetting, RTL handling, brand-icon source, custom-icon construction rules, and approved secondary-library exceptions.>

### Example Icon Usage Code

```tsx
// Example structure only. Replace with the selected library and project primitives.
import { ExampleIcon } from "<approved-icon-package>";

export function IconActions() {
  return (
    <>
      <button>
        <ExampleIcon aria-hidden="true" className="<icon-token>" />
        Visible action
      </button>
      <button aria-label="Descriptive action">
        <ExampleIcon aria-hidden="true" className="<icon-token>" />
      </button>
    </>
  );
}
```

<Define tooltip behavior for the icon-only control and adapt accessibility details to the target stack.>

## Spacing System

| Token | Value | Usage |
|---|---|---|
| Base spacing | <value> | <usage> |
| Component padding | <value> | <usage> |
| Section gap | <value> | <usage> |
| Grid gap | <value> | <usage> |

## Component Architecture

This document owns the token layer. The layers built on it — layout, surface, typography, and control primitives, product components, and their closed variant sets — live in `ui-architecture.md`, and their machine-readable allowlist lives in `ui-registry.json`.

Two rules bind this document to those:

- Every raw color, dimension, and motion value in the product appears in the token sections here and nowhere else.
- Nothing outside this document may invent a value. A page or component that needs one gets a new token here plus a new variant in `ui-architecture.md` and `ui-registry.json`.

## Shadows & Elevation

| Token | Value / Direction | Usage |
|---|---|---|
| None / flat | <value> | <usage> |
| Raised | <value> | <usage> |
| Overlay | <value> | <usage> |

## Motion System

### Motion Principles & Stack

| Mechanism | Technology | Owns | Dependency / version | Performance constraints | Fallback |
|---|---|---|---|---|---|
| <style-layer transition / animation runtime / route-level transition> | <CSS, WAAPI, Motion, GSAP, Rive, native, or none> | <the work this mechanism owns> | <dependency / version or built-in> | <constraints> | <fallback> |

Mechanism and purpose are separate decisions. Every pattern below uses exactly one purpose: feedback, continuity, processing, or storytelling. There is no decorative or ambient exception.

### Global Reduced-Motion Configuration

| Configuration point | Location | Normal behavior | Reduced-motion behavior | Opt-out / exception rule |
|---|---|---|---|---|
| Application boundary | <single style-layer media query, runtime provider/configuration, and route-transition setting> | <global default inherited by every registered variant> | <final state immediately, or opacity-only; no spatial transform, parallax, autoplay, continuous ambience, or scale> | <route-level opt-out or justified per-variant exception; name the owner and reason> |

Call sites do not query reduced-motion preferences. They reference registered variants that inherit this global configuration. Any exception is recorded once in the pattern inventory with its reason.

### Motion Tokens

| Token | Duration | Easing / spring | Distance / scale | Usage | Reduced-motion value |
|---|---|---|---|---|---|
| <token> | <duration> | <curve or spring> | <distance or scale> | <usage> | <none, instant, or opacity-only> |

### Motion Pattern Inventory

| Motion ID | Surface / component | Mechanism | Purpose | Trigger | Properties | Token / sequence | Repeat / interruption | Responsive and reduced-motion behavior |
|---|---|---|---|---|---|---|---|---|
| MOTION-001 | <surface> | <style-layer transition / animation runtime / route-level transition> | <feedback / continuity / processing / storytelling> | <load, viewport, interaction, state, or scroll> | <opacity/transform/etc.> | <tokens> | <rules> | <behavior> |

### Hero Choreography

| Step | Element | Start / relation | From → to | Purpose | Mobile behavior | Reduced-motion behavior |
|---|---|---|---|---|---|---|
| 1 | <eyebrow, headline, copy, CTA, media, or brand accent> | <time or relation> | <values> | storytelling — <rationale> | <variant> | <fallback> |

### Motion Demo Index

| Demo ID | Pattern / page | Artifact path | Stack | Controls | Status |
|---|---|---|---|---|---|
| DEMO-001 | <hero or pattern> | <motion-showcase.html or path> | <stack> | play / pause / restart / reduced motion | <draft or approved> |

### Example Motion Implementation Code

<Provide static-first, stack-appropriate implementation code with reduced-motion handling and cleanup/cancellation where required.>

## Border Radius

| Token | Value | Usage |
|---|---|---|
| Small | <value> | <usage> |
| Medium | <value> | <usage> |
| Large | <value> | <usage> |

## Opacity & Transparency

| Token / Pattern | Value | Usage |
|---|---|---|
| Disabled | <value> | <usage> |
| Overlay | <value> | <usage> |
| Subtle surface | <value> | <usage> |

## Layout Rules

<Grid, max widths, navigation layout, responsive breakpoints, and region rules.>

## Common Tailwind CSS Usage In Project

<Web target. For a native or desktop target, rename this to the platform's styling model (SwiftUI view modifiers, Compose Modifier chains and MaterialTheme tokens, Flutter ThemeData/widget styles, or WinUI resources) and list the reusable style patterns implementers apply.>

| Pattern | Classes / tokens | Usage | Notes |
|---|---|---|---|
| Page shell | <classes> | <usage> | <notes> |
| Card / panel | <classes> | <usage> | <notes> |
| Button | <classes> | <usage> | <notes> |
| Form control | <classes> | <usage> | <notes> |
| Responsive grid | <classes> | <usage> | <notes> |

## Example Component Reference Design Code

```tsx
// Example only. Adapt to the target project stack.
export function ExampleContentSection() {
  return (
    <section className="<open layout classes>">
      <div className="<header classes>">
        <h2 className="<title classes>">Example title</h2>
        <p className="<body classes>">Example supporting copy.</p>
      </div>
      <button className="<button classes>">Primary action</button>
    </section>
  );
}
```

## Interaction Rules

<Focus, hover, active, loading, disabled, selected, expanded, and validation feedback.>

## Accessibility Rules

<Contrast intent, focus visibility, keyboard path, text sizing, labels, and motion.>

## Assumptions

- <assumption>

## Open Questions

- <question>
