# Design Translation And Rebuild

Apply after the existing UI and motion intake, before full wireframe authoring. Keep the result in `ui-design.md`; this is an authoring checkpoint, not another document or approval gate. Reuse answers already supplied by the owner.

## Choose The Scope

- **Incremental** is the default: follow `enhancement-recommendations.md` and preserve unnamed scope.
- **Full design rebuild with retained PRD** requires the owner's explicit instruction. It overrides incremental design preservation for the named full scope. Keep the approved PRD, architecture, stack, product copy, trace IDs and known usability failures as acceptance inputs. Do not reuse the old composition, component appearance, direction or design tokens as a starting point. Retain only brand assets or design constraints explicitly carried forward by the owner. Inspect old artifacts for inventory and recovery, not creative authority.
- Start the rebuild from translation under the actually loaded skill contract. A current disk version does not prove a live session loaded it. Preserve old files and receipts until separately authorized replacement/archive. Create fresh wireframe and visual decisions; never relabel old approvals. Unchanged approved product wording can be reused, but confirm the new complete Copy Freeze inventory through its existing gate.
- A retained PRD is not editable by implication. If a new rule conflicts with its behavior, languages, devices or stack, report the exact conflict to Product Definition. Continue independent work; never remove a requirement to fit a template.

## Translation Record

Record a short table with `UI/UX trace | primary task | content and reading order | composition and density | responsive transformation | interactions and motion | fixed / provisional | acceptance case`. Include:

1. The visual entry point, primary action and subordinate content. Use real frozen copy and bounded examples, not filler that hides layout problems.
2. Region proportions, content measure, min/max width, content-driven height, padding, grouping and image ratio/crop intent. Use the existing per-target `composition` data for geometry. Do not force equal cards, empty height spacers or a marketing hero onto every screen.
3. Reflow rules for each approved target: reorder, wrap, collapse, sticky positioning, table handling and never-drop actions. Check intermediate widths and either side of a layout transition; a screenshot at three widths cannot prove continuous reflow. Review-only intermediate widths do not become new PRD targets or approval receipts.
4. Navigation opening/closing, current location, back/cancel, focus restoration, keyboard/gesture alternatives and state retention. Functional controls work locally. A hamburger drawer uses the existing declared overlay flow; the disclosure pattern below is an inline menu, not proof of a modal drawer.
5. Applicable control hierarchy, sizing, icon purpose and placement, full-width compact treatment, focus/pressed/disabled/loading/error states. A disabled required journey still needs a reachable enabled state. Use exact labels; any icon-only control needs an approved accessible name. Do not infer an action from decoration.
6. Motion regions with scope, trigger, behavior/end state, interruption/replay, space/scroll requirements, compact fallback, reduced-motion fallback and cost/dependency constraints. Annotate the whole affected region or a named element within it. Keep annotations switchable and deferred assets visibly deferred.

Compose a primary task and a dense, long-content or alternate-state case at compact and wide targets first. Inspect reading order, spacing and operations before expanding all screens. Use the existing W1-W5 review and gates.

## Reading And Language

Derive supported languages from the PRD. Single-language products need real-copy and long-content checks, not a multilingual matrix. Multi-language products author the full primary-language set and inspect representative other-language screens and high-risk controls. These representative checks supplement, never shrink, any full language matrix explicitly required by the PRD.

Distinguish locale switching from simultaneous bilingual display. Pair corresponding paragraphs closely and separate different groups with more space. For stacked bilingual copy, put each language on its own line/block and allow each to wrap; never force exactly two physical lines or shrink text to fit. Record equal versus primary/secondary emphasis. Long articles may use paragraph pairs or a product-approved locale switch. Do not add language controls without PRD scope.

Check Chinese punctuation and line breaking, mixed CJK/Latin baselines, long titles/buttons, dates, money, numbers, font fallback and zoom. For RTL languages also inspect ordering, directional icons, mixed numbers and reading order; whole-page mirroring is insufficient. Identify stress text separately from approved shipping copy. Mark each language for assistive reading. Do not duplicate every button/tab label in two languages by default.

## iPhone Scope

For newly scoped iOS products, propose iPhone first; add iPad only when explicitly required. Existing iPad requirements remain binding until Product Definition changes them. Use two named iPhone review targets (for example `iphone-small`, `iphone-large`) with recorded point-size intent and HTML canvas widths. These are review targets, not claims about UIKit size classes; do not force an iPad `regular` layout to meet the two-target rule. Keep the PRD's exact target names. Test Dynamic Type separately from device width; landscape is required when the PRD supports it.

Choose browse/detail, top-level tabs or input/confirmation from the task. Do not carry desktop sidebars or hamburger navigation into iPhone by default. Record safe areas, reachable actions, back versus close/cancel, sheets, keyboard avoidance, scroll retention, system text styles, SF Symbols and supported OS range. Shared brand does not imply shared Web controls. Assess dark appearance, VoiceOver, reduced motion and haptics according to product requirements. Brand character may come from content, imagery and typography while system navigation stays familiar.

HTML is a review projection only. Native font metrics, keyboard, gestures, VoiceOver and haptics require platform evidence in the first implementation slice, not a fake native PASS from a browser. Official resource links and reusable composition choices are in `composition-patterns.md`.

## Handoff To HiFi

Fixed: product behavior/copy, information priority, region relationships, navigation destinations and responsive obligations. Provisional: prototype font choice, optical spacing, fine proportions, palette, radius, material and animation timing. HiFi can refine provisional values while preserving the fixed contract; behavior or structural changes return to their owner. Preserve the approved wireframe bytes.

Use the existing direction studies to compare actual typography, composition, imagery and control treatment over identical content. Explain one product-specific visual thesis and focal point. Compare repeated components across pages and states, including bilingual and compact examples. Record source-bound screenshots and concrete before/after findings, not score-only claims. Do not add another direction approval gate.
