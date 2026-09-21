# Composition Patterns

Use `assets/templates/composition-patterns.json` as a small recipe library beside the single canonical HTML shell. Select, adapt or reject a recipe after reading the PRD and real content. Recipes contain no product copy, routes or approval. They never create UI surfaces, select a stack, install assets or replace product-specific judgment.

The four Web recipes cover reading/editorial, product storytelling, search/browse and task/workspace. Three iPhone recipes cover browse/detail, top-level tabs and input/confirmation. A recipe declares region roles, compact/wide proportions, reading and interaction checks, motion slots and unsuitable cases. Map roles only to existing approved regions; record that mapping and any deviation in the translation record. Shared bilingual, motion and navigation patterns avoid copying the whole shell. Motion slots are optional positions, never a requirement to add animation. Omit roles the PRD does not need; do not invent content to fill a recipe. New recipes need a use case, both target treatments and a failing-case check before entering the library.

For each selected recipe, record its ID/version, product-fit reason, rejected assumptions and the actual loaded skill identity. Build one representative primary/stress pair, then use the canonical renderer and checker. A JSON recipe alone is not a working UI or visual-quality evidence. No default recipe is mandatory, and a full rebuild must not mechanically reproduce the prior recipe.

## Reference Cards

These are starting research pointers, inspected as documentation on 2026-09-20, not observations of every live interaction. Reinspect the exact page/viewport/state for project-specific claims and record source/date/limitations in existing WREF/REF rows. Adopt principles, not another brand's identity. Check licensing before copying assets; link official UI kits rather than bundling them here.

| Card | Useful principle | Boundary | Source |
| --- | --- | --- | --- |
| Composition rhythm | Hierarchy, whitespace, repetition with variation, deliberate asymmetry | Do not force asymmetry or IBM typography on unrelated content | [IBM layout](https://www.ibm.com/design/language/layout/tips-and-techniques/) |
| Product storytelling | Explain a product through a purposeful demonstration | Historical 2017 case, not a current technology recommendation | [Stripe Connect](https://stripe.com/blog/connect-front-end-experience) |
| Working navigation | Stable global navigation and content space | Enterprise shell is not a universal landing page or iPhone pattern | [Carbon header](https://carbondesignsystem.com/patterns/global-header/) |
| Readable content | Type hierarchy and text measure at paragraph and page level | English measures do not automatically fit Chinese | [USWDS typography](https://designsystem.digital.gov/components/typography/) |
| Chinese reading | Punctuation, line breaks and mixed-script composition | Test actual product copy and fonts | [W3C Chinese layout](https://www.w3.org/TR/clreq/) |
| iPhone behavior | Reachability, focused tasks and platform adaptation | Match supported OS and device scope | [Apple iOS](https://developer.apple.com/design/human-interface-guidelines/designing-for-ios/) |
| Native type and icons | System text roles, Dynamic Type and SF Symbols | HTML cannot prove native metrics or accessibility | [Typography](https://developer.apple.com/design/human-interface-guidelines/typography), [SF Symbols](https://developer.apple.com/sf-symbols/) |
| Native controls | Official design resources and navigation/material conventions | Choose the target OS kit; Liquid Glass is not a blanket content-card style | [Resources](https://developer.apple.com/design/resources/), [Tabs](https://developer.apple.com/design/human-interface-guidelines/tab-bars), [Materials](https://developer.apple.com/design/human-interface-guidelines/materials) |

A project-specific visual reference card states audience/task, type roles, spacing rhythm, imagery, controls, motion, Adopt/Adapt/Avoid and limitations. Keep it in the existing direction record. These cards support direction studies; they are not a fixed catalog of themes to apply during wireframing.
