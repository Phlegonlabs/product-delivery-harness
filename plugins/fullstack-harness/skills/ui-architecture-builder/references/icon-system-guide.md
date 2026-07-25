# Icon System Guide

Use this guide when a design package includes functional icons, brand marks, platform symbols, or custom icon requirements.

## Selection Workflow

1. Inventory the actual concepts first: primary navigation, common actions, status and feedback, data types, domain objects, external brands, and directional icons.
2. Respect an existing platform or component-library icon system unless the user approves a change.
3. Research current candidates from official sources. Record the checked date, version when relevant, license, pricing tier, package or asset format, supported frameworks, and trademark restrictions. Treat these details as unstable.
4. Test candidates against the inventory. Compare at least the ten most frequent UI concepts and every must-have domain concept; total catalog size is not proof of coverage.
5. Render shortlisted icons at their intended small and default sizes beside the product typography when visual tools are available. Compare optical weight, grid, corner language, legibility, filled/selected states, RTL behavior, and baseline alignment.
6. Score brand fit and required-icon coverage first, then implementation fit, small-size clarity, state support, accessibility and RTL, performance, license, and maintenance.
7. Choose one primary functional set. Allow separate platform symbols, brand marks, or a secondary set only through documented exceptions and normalization rules.

## Current Market Shortlist

Use this as a starting point, not as a substitute for current official verification.

| Set | Best fit and differentiator | Official integration / source | License note |
| --- | --- | --- | --- |
| [Lucide](https://lucide.dev/) | General web products needing a broad, consistent outline family with adjustable size and stroke | Framework packages and SVG; supports per-icon imports and tree-shaking | ISC; preserve required notices |
| [Heroicons](https://heroicons.com/) | Tailwind-oriented products that need a focused family with outline, solid, mini, and micro variants | SVG plus first-party React and Vue packages | MIT |
| [Phosphor](https://phosphoricons.com/) | Expressive consumer or cross-media products needing regular, thin, light, bold, fill, and duotone weights | Framework packages, web assets, and SVG | MIT |
| [Tabler Icons](https://tabler.io/icons) | Data-heavy apps and dashboards needing broad 24px outline coverage plus filled options | SVG, sprite, webfont, React, and design-tool assets | MIT for the open-source set; verify paid asset terms separately |
| [Material Symbols](https://developers.google.com/fonts/docs/material_symbols) | Google/Android-aligned or highly configurable systems needing fill, weight, grade, and optical-size axes | Variable/static fonts, SVG/PNG, repository, and platform formats | Apache 2.0; subset fonts and pin axis choices |
| [Radix Icons](https://www.radix-ui.com/icons) | Compact web interfaces that benefit from crisp 15px symbols | Individual React components, SVG, and Figma | MIT; verify coverage before adopting as the only set |
| [Carbon Icons](https://carbondesignsystem.com/elements/icons/usage/) | Enterprise and technical products aligned with IBM Plex or Carbon's 16/20/24/32px system | Vanilla, React, Angular, and Vue packages | Apache 2.0 |
| [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) | Microsoft/Windows-aligned and cross-platform products needing regular and filled states | React, Android, Apple, Flutter, and SVG assets | MIT |
| [SF Symbols](https://developer.apple.com/sf-symbols/) | Native Apple-platform experiences needing text alignment, weights, scales, localization, and symbol effects | Apple platform APIs and the SF Symbols app | Review Apple's current license and restricted-symbol terms before use; do not treat as a generic web icon pack |
| [Remix Icon](https://www.remixicon.com/) | Neutral 24px UI systems needing paired line and fill variants plus font/SVG delivery | Webfont, SVG sprite, React, Vue, and design tools | Verify the current Remix Icon License and brand-icon restrictions |
| [Font Awesome](https://fontawesome.com/) | Products needing broad familiar coverage or an existing Free/Pro ecosystem | SVG/JS, framework packages, kits, and fonts | Free and Pro assets have different terms; record the exact tier and license |
| [Simple Icons](https://simpleicons.org/) | Third-party brand marks only | SVG and community packages | Project is CC0, but each represented brand can carry trademark rules |
| [Iconify](https://iconify.design/) | Discovery or a unified delivery layer across many open-source sets | Framework components, API, SVG, and icon-set packages | License is per underlying icon set; never record only "Iconify" as the icon license |

## Decision Rules

- Prefer recognizable metaphors and product vocabulary over cleverness. Do not invent a custom glyph when a standard action icon is clearer.
- Keep one geometry per product surface: grid, stroke/fill model, cap and join style, corner language, padding, and optical weight.
- Do not mix an outline icon with a filled icon merely to fill coverage gaps. Use fill consistently for a documented state, emphasis, or semantic family.
- Keep functional icons, illustrations, pictograms, app icons, and brand logos as separate asset classes.
- Use the library's exact icon names in the semantic inventory so design and engineering reference the same asset.
- Make custom icons conform to the primary set's grid, padding, stroke, corner, and optical-size rules. Test them beside native library icons at every supported size.

## Usage Contract

- Define icon-size tokens separately from interactive hit-area tokens. Center the icon optically inside its control; do not enlarge the glyph to satisfy a touch-target requirement.
- Pair unfamiliar, destructive, high-risk, or infrequent actions with visible text. Use icon-only controls only when the metaphor is well understood and space requires it.
- Give every icon-only control an accessible name that describes the action, plus a tooltip on hover and keyboard focus when it aids sighted users. Name the action (for example, "Close"), not the glyph ("X").
- Hide decorative icons and icons that repeat adjacent visible text from assistive technology. Do not hide a focusable control.
- Do not use icon shape or color as the only status signal. Pair critical status with text and appropriate semantic styling.
- Define selected, active, disabled, hover, focus, loading, and destructive behavior without changing the icon metaphor unexpectedly.
- Define RTL mirroring per icon. Mirror directional navigation and flow icons when appropriate; do not mirror logos, text, clocks, media controls, or other direction-independent symbols without platform guidance.
- Import only used SVG components or subset icon fonts where the chosen system supports it. Record the performance strategy in the design system.

## Required Evidence

The design package must include:

- Candidate market-scan table with official URLs and checked date
- Primary library decision and rejected-candidate rationale
- Coverage result for common and domain-specific concepts
- Icon size, weight, fill, color, and hit-area tokens
- Semantic inventory mapping intent to exact icon name and source
- Accessibility, tooltip, label, status, RTL, and state rules
- Package/import or asset-source instructions and performance strategy
- Stack-appropriate labeled and icon-only usage code with accessible-name ownership and tooltip behavior
- Brand-icon policy, custom-icon construction rules, and every approved exception
