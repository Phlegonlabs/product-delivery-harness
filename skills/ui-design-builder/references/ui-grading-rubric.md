# UI Grading Rubric

This rubric defines the Product-Definition-bound diagnostic and grading stage for current HiFi. A `ui-design/2` package runs the HiFi completeness preflight, then the first HiFi review, and finally the full HiFi human gate; it does not run W1–W5 or a wireframe grading wave. The W material below is retained for inspecting and validating legacy wireframes only. This rubric supplements the browser matrix check, static checker, and required Impeccable HiFi review; it never replaces them or the human approval decision. Correctness comes from explicit hard-gate evidence. Numeric scores summarize comparative quality and never create another repair round by themselves.

## Frozen Grading Basis

Before dispatch, the parent records the exact PRD and `ui-design.md` paths plus revisions or SHA-256 values and the candidate HTML path plus SHA-256. A legacy wireframe grader receives the current filled structure and PRD-join result under its old schema; no human copy gate is required in schema 5. Every current grader receives the same frozen inputs: the `UI-*` surfaces, `UX-*` traces, actions, flows, states, responsive targets, UI Design Intake, complete sourced copy, Motion and Media Intent, selected direction when applicable, and the candidate HTML. Graders score only conformance to those inputs. They do not add screens, flows, visual preferences, copy, media, or motion.

A missing or contradictory product obligation returns to `product-definition-builder`; a missing UI direction returns to `ui-design-builder`. Graders never resolve either by inventing a preferred behavior. A direct contradiction with a frozen requirement or approved UI decision is a `block` regardless of numeric score.

## Capability And Authorization

- First observe whether the host can dispatch the required grading agents that can open the local HTML in a real browser. Capability does not grant permission.
- If the required grading capability or explicit authorization is unavailable, the grading gate is blocked. Record the frozen PRD and artifact identities plus the missing capability; do not convert the result into a PASS or continue to human approval.
- When the capability is available, require explicit delegation authorization for this grading stage or the matching current RUN `spawn_subagents` grant before dispatch. If authorization is missing, do not spawn; pause the grading stage for the owner rather than treating capability as permission.
- Run one complete diagnostic wave before any repair. Default to one fresh lead grader that walks the complete in-scope `UI-* × responsive target × non-n/a state` matrix and must return every finding it can establish, not stop at the first block.
- Add at most two fresh specialist sibling graders only when the owner requests independent review or a recorded high-impact risk justifies separate accessibility, localization/state, or visual lenses. Give specialists non-overlapping lenses over the same frozen inputs. All dispatched graders finish the same diagnostic wave before the parent begins repair; they do not share notes or open later waves to look for more examples.
- Graders return evidence only: they do not publish, mint trace IDs, contact the owner, or approve the artifact.

## Scores

Each dimension receives one integer score from `0` to `100` and a status:

- `80–100 — pass`: meets the grading threshold and matches the frozen PRD without a blocking issue;
- `60–79 — advisory`: retained for legacy Wireframe only. For HiFi, any dimension below 80 blocks readiness; or
- `0–59 — block`: a required screen, action, state, responsive behavior, readable layout, or other PRD obligation is missing or broken.

Legacy Wireframe thresholds stay unchanged: overall at least `80`, `W5` at least `80`, every dimension at least `60`, and no `block`.
HiFi readiness requires an overall score of at least `85` and every `H1`–`H9` dimension at least `80`.
Any `block` or disputed dimension still prevents readiness.
Record the rounded arithmetic mean of `H1` through `H9` as the overall score.
The overall score and every dimension threshold must pass before Visual Approval.
Keep the recorded values consistent with the actual assessment.
Scores never average away a blocking finding or a failed dimension threshold.
After required checks pass, carry remaining advisories to the human gate without another scoring round.

## Technical Hard Gate

Apply this before numeric grading after the current package passes its cheap completeness preflight. The HiFi must open as a connected local HTML package, render meaningful content, make no unexpected network, backend, authentication, or generation request, and produce no uncaught console error or broken runtime overlay. Every HiFi page has exactly one canonical restrictive CSP meta; the required closed policy is recorded in the output contract. Schema-2 HiFi follows the local-page allowlist and click/keyboard ui-output/3 contract in output-contract.md; every product control must reach its declared visible destination with correct focus. Schema-1 remains inspection-only and cannot pass current Visual Approval. Its historical surface checks run with method `sandboxed-offline-browser` inside a sandbox with network disabled and top navigation, popups, and forms blocked. The retained `ui-output/1` artifact contains the console, network, and navigation transcript; any error or attempt is a block. This receipt boundary complements the static CSP and does not claim regex can prove arbitrary JavaScript safe. Every in-scope page, state, action, overlay, responsive target, reviewer-inspector view, `ui-hifi-copy/1` item and paired-language product copy binding must remain reachable after a clean reload, without duplicate event effects or stale state leaking between screens. For a legacy wireframe, static copy, labels, feedback, alternate states and dynamic display contracts must be complete and sourced; reviewer notes must not appear as product copy. At every matrix entry, run a DOM geometry scan over visible peer elements and their container and viewport bounds; ignore ancestor-descendant containment and only the overlays explicitly allowed by the PRD. Record the selectors or stable element IDs for every collision, clipping, off-container boundary, and horizontal overflow result. A failure is a `block`; intentional deferred media or motion placeholders are not broken assets.

## Legacy Wireframe Scope

- `W1 PRD conformance`: every `UI-*` screen, route, required content/control responsibility, action, flow, state, responsive target, and trace agrees with the frozen PRD; the wireframe's region grouping and order introduce no new product obligation.
- `W2 Layout safety`: no reviewer-shell or canvas element is unintentionally overlapped, clipped, occluded, or forcing horizontal page scrolling. An intended overlay passes only when its PRD interaction rule names stacking, focus, and dismissal.
- `W3 Interaction`: every visible region action works from the local file. It navigates to the PRD-recorded screen, opens the recorded overlay, or shows the recorded local feedback; the page switcher, all-pages overview, responsive-target control, state control, and runtime layout QA also work.
- `W4 Responsive and state integrity`: every never-drop region stays visible with the declared order and spans, and every non-`n/a` state is selectable at every target.
- `W5 Structural clarity and evidence`: the canvas makes product hierarchy, content density, and responsive composition legible without pretending to be final visual design; product copy is clearly separated from reviewer notes; the `WREF-*` decisions support rather than decorate the chosen structure; apply the structural items below against the PRD rather than grader taste.

### W5 Composition Criteria

Wireframe has no Tokens or Design System Draft view. W3 verifies actual product menus, tabs, navigation, input, validation and recovery. Reviewer controls cannot prove a product journey. Verify required Home, back and cancel actions against the PRD, then compare Wireframe and HiFi destinations. Unsupported required interactions block readiness.

Before expanding the complete screen set, compose one frequent task and one dense or alternate-state case from the approved scope. A single-screen product may use two states of that screen; do not invent a second task. Inspect both at the applicable wide and compact targets. This authoring checkpoint adds no approval gate and never replaces the full final matrix.

Evaluate all seven criteria against the approved task, content, and platform:

| Criterion | Passing evidence |
| --- | --- |
| Task hierarchy | The primary task and action are easy to locate; supporting content does not compete for equal emphasis. |
| Type hierarchy | Page title, section title, body, and supporting text have distinct, readable roles without labeling every paragraph. |
| Spacing and grouping | Related items sit together; larger gaps separate groups; alignment and line length support reading. |
| Content form | Navigation, forms, lists, and tables look and behave like their intended structures rather than identical cards. |
| Composition and density | Region proportions reflect task importance; no arbitrary equal boxes or empty height spacers. |
| Platform and reflow | Compact layouts reprioritize and reflow content; platform conventions remain distinct. |
| Review separation and neutrality | The formal view opens with readable annotations, named destinations and measured spacing. Notes are distinct from product copy. The optional clean view preserves the product layout rules and working flows. |

Record each criterion's observation, page-target-state, and inspected screenshot path/hash in the existing grading detail. Review representative cases with annotations on and also verify the clean view. Check that action descriptions match real page, dialog and local-result behavior, and, for HiFi, that token specimens apply the displayed values. Cite the relevant PRD/intake/reference decision for each weakness. W5 below 80 blocks readiness even when the overall score passes; merely removing color or passing geometry checks does not establish composition quality. Do not grade a preferred brand style or freeze final fonts, colors, or tokens here.

## Reading And Cross-Screen Cases

Within W3-W5 and H4/H8/H9, inspect long real copy, bilingual pairs and language-specific wrapping where required. Check text enlargement, dates/numbers, RTL only when in scope, and repeated component appearance/meaning across pages. Verify motion boundaries and fallback separately from produced motion. iPhone review targets are smaller/larger phone cases, not an automatic iPad obligation. Preserve complete PRD-required matrices; representative language stress checks do not waive them. Screenshots identify exact spacing/type/reading failures; an unchanged score cannot hide one.

## Design-Reference HTML Scope

- `H1 Product, copy, and direction conformance`: every included surface follows the frozen PRD UI Surface Contract, `ui-design.md`, its accepted Design Brief/page-purpose/profile decisions, and the selected `VD-*` direction. Login, registration, recovery, and authentication-error previews are excluded only when the UI design contract records them as `n/a` for this visual pass. Any design-stage wording change is a block until its copy delta is approved through Product Definition and the full HiFi copy review.
- `H2 Layout safety`: inspect all visible peer elements, controls, text blocks, media placeholders, and overlays in the retained all-screens HTML. No required element may unintentionally overlap another, clip, become occluded, collide through broken spacing or wrapping, leave its container, or force horizontal page overflow. Intended overlays pass only with their recorded stacking, focus, safe-area, and dismissal behavior. Any such failure on required content is a `block`.
- `H3 Interaction wiring`: every visible product control responds by navigating, switching a declared state, opening a documented overlay, or showing recorded inline feedback. Dead controls and isolated stills are blocks.
- `H4 Responsive and edge states`: repeat the element-level `H2` inspection at every PRD-declared viewport or size class and every non-`n/a` state. Long labels, localized copy, validation errors, empty data, and dense data stay readable and usable; layout reflows in the recorded order, spacing remains intentional, and resizing never strands focus, hides a required action, creates clipping, or introduces horizontal overflow. Any failure on required content is a `block`.
- `H5 Visual slop`: apply the visual items below against the selected `VD-*` direction.
- `H6 Media and motion fit`: apply `ui-design.md`'s Motion and Media Intent. Required functional UI motion is represented locally with its trigger, purpose, timing intent, and reduced-motion fallback; its absence or a fallback that loses meaning is a `block`. A `not_required` surface adds no decorative motion beyond platform-standard functional feedback. Each image, motion, or combined treatment matches its recorded MM intent and approved generation route. A Higgsfield or other provider asset is accepted only with recorded authorization, output identity, placement, usage constraints, and fallback; otherwise it remains a static deferred placeholder. The HTML never invokes an unapproved provider or pretends generated output exists. Also judge motion craft on every played effect: durations and easing follow the motion tokens, related movements share one rhythm, the effect can be interrupted or replayed as specified, it causes no layout shift or jank, and the reduced-motion path keeps the same meaning. Record each craft failure as an H6 finding with its capture so the consolidated repair batch fixes it, and lower the H6 score to match.
- `H7 Creative distinction`: composition, hierarchy, interaction concepts, and content presentation feel intentional and specific to the product rather than interchangeable with a generic template. The approved direction has one coherent thesis and a complementary reference-role map; it does not splice unrelated source aesthetics into a collage. Creativity must support the frozen PRD, accepted Design Brief/profile decisions, and selected `VD-*` direction; it earns no credit by adding unapproved scope, rewriting copy, obscuring content, weakening accessibility, breaking familiar controls, or pretending deferred media exists.
- `H8 Accessibility`: keyboard-only use reaches every in-scope action and state with a visible logical focus order; dialogs and drawers move, contain, dismiss, and restore focus correctly; controls have meaningful names, roles, states, and usable target sizes; headings, landmarks, status announcements, contrast, zoom, and reduced-motion behavior meet the frozen PRD accessibility requirements. Any required flow that is unavailable without a pointer, loses focus, or exposes an unnamed control is a `block`.
- `H9 Design consistency`: repeated components, spacing, typography, color roles, icon meaning, control hierarchy, and ready/hover/focus/disabled/error states remain coherent across screens and responsive targets. A deliberate exception passes only when the selected direction or PRD explains it; accidental component drift or inconsistent interaction meaning is an advisory or block according to user impact.

## AI-Slop Checklist

For `H5`, `H7`, and `H9`, attach inspected candidate screenshots with path/hash, page-target-state, and the exact region behind each finding. Explain typography, alignment, density, spacing, hierarchy, or component treatment against the selected direction and its confirmed references. A score without this visual basis is incomplete review evidence. Check a frequent working screen and a dense or alternate state, not only an attractive entry screen; use only cases that exist in the approved scope.

Calibrate with owner-confirmed reference principles: `60–79` means usable but visibly generic or inconsistent, `80–89` means intentional and coherent with named remaining weaknesses, and `90–100` means refined execution demonstrated across the inspected cases. Familiar native controls can be excellent design; novelty, decoration, custom fonts, and motion earn no points by themselves. A sub-80 visual-quality dimension blocks readiness even when the overall average passes. Validators check recorded thresholds and evidence consistency, not beauty or whether a screenshot was honestly inspected.

Structural items, HiFi and legacy-wireframe scope:

- Unrelated screens share an identical skeleton with no PRD reason.
- Product copy remains generic, draft, ambiguous, or mixed with reviewer-only purpose and trace notes.
- Dynamic examples omit source, order, format, count, length, or fallback, so implementation must guess.
- Section-purpose labels are missing, duplicated meaninglessly, or name no responsibility.
- A region exists that no `UI-*` entry or flow accounts for.
- A cited reference, `WREF-*` or `REF-*`, names an attractive category peer without matching the exact screen, flow, viewport, or state it supposedly supports.

Visual items, design-reference scope:

- The rendering ignores the selected `VD-*` direction: for example, default sans typography, neutral-gray rounded cards, or a centered hero with equal-width feature tiles appear without a task or direction reason. These treatments are not defects when the approved direction or platform calls for them.
- The rendering changes approved wording or converts a dynamic example into fixed product copy.
- Identical section rhythms repeat across unrelated screens with no directional reason.
- Decorative gradients, glows, labels, emoji, status dots, or fake-precise numbers appear without support from the approved direction or copy source.
- Controls exist purely as decoration and do nothing when used.
- A media or motion placeholder uses a generic prompt that does not name its page, position, purpose, and constraints.
- Several reference aesthetics appear side by side with no single direction thesis or Adopt / Adapt / Avoid rationale.

## Layout Integrity And Anti-Slop Review

Apply these internal rules during authoring and the existing Technical Hard Gate and H2/H4/H5/H7/H9 review. They add no skill dependency, schema or approval gate. Hallmark is not required. Keep the selected direction and product scope; simplicity, cards, gradients or symmetry are not defects by themselves.

### Controls, Containers And Layers

- Use shared spacing, type, control-height and alignment rules from the selected direction. Compare repeated buttons, field labels, icons and card edges across screens; measure the intended baseline or edge, not only the outer box. Record optical exceptions by component and reason. Arbitrary one-off offsets do not establish consistency.
- Keep content in normal flow unless its interaction requires positioning. Flex/grid children must wrap, stack or scroll in the intended container before required labels or actions collapse. Preserve usable control dimensions and label/icon gaps with long sourced labels, loading indicators and validation text. A wrapped label must not collide with another control or leave its button.
- Test each declared menu, popover, sheet and modal open as well as closed. Check nested scroll containers, sticky headers/footers and stacking contexts: the panel and its controls must remain visible, reachable and dismissible, with correct focus and background interaction. A higher z-index alone does not repair clipping by an ancestor.
- Do not conceal a failure with page-wide overflow hiding, arbitrary fixed heights, shrinking text or hit areas, negative margins, or removal of required content. Intentional truncation, scrolling and decorative overlap need the existing content/interaction contract and must preserve access to required information and actions. Keep approved exceptions narrow; never exempt an entire page from geometry review.

### Browser Inspection Procedure

1. Render every required page, target and state at its actual canvas width, with fonts settled and intended transitions complete. Exercise open layers, focus and validation states through real product controls. Sweep between Web review targets and record any intermediate failure with its actual width; this supplements rather than changes the approved responsive set. Native size classes retain their own platform evidence requirements.
2. For visible controls, text and panels, inspect bounding rectangles, text line rectangles, scroll versus client dimensions, clipping ancestors and containing bounds. Compare peer pairs for unintended intersection; inspect child content for clipping even though parent-child containment is not a collision. Use hit testing at visible actionable points plus actual click/keyboard activation to detect occlusion. An icon inside its own button is not a competing target. Rectangles alone cannot prove that text is readable or a layer is usable.
3. Inspect full-canvas screenshots and close views of dense controls and open layers. Stress the approved longest content, required languages, text scaling, narrow layouts and fallback fonts. Check consistent baselines, spacing and control dimensions across sibling screens. A clean default screenshot or a scan with zero findings is insufficient without these observations.
4. Retain findings in the existing ui-output/3 assessment and consolidated defect ledger. Each names candidate identity, surface/state/actual target, exact element pair or clipping ancestor, expected rule, observed geometry or hit-test result, inspected capture path/hash, root cause, repair and acceptance cases. Keep extra measurements inside referenced captures rather than adding fields to the fixed receipt schema. Missing browser access or uninspected cases remain MISSING/BLOCKED, never PASS.

Required content that overlaps, collapses, clips or becomes unreachable blocks readiness under H2/H4 regardless of the overall score. Repair the shared cause, inspect all consumers, and rerun the affected cases plus the required final matrix on the changed candidate within the existing repair budget. Do not reuse earlier screenshots to clear a repaired layout.

### Product-Specific Visual Judgment

For H5/H7/H9, compare the primary task and dense case against the selected direction. Flag interchangeable hero/card/CTA sequences on unrelated tasks, equal emphasis for unequal actions, decorative panels around every fragment, unsupported badges or metrics, competing accents, and inconsistent control/type/spacing roles. State how each example harms hierarchy, reading or the approved direction and cite its surface and capture. Reuse is appropriate for the same task/component; novelty, extra decoration and arbitrary asymmetry are not acceptance criteria. Separate a measured layout failure from a taste advisory. An unsupported generic aesthetic cannot be cleared solely by raising a score, while a justified restrained design must not be penalized for being simple.

## Reporting And Reconciliation

- Each grader returns one row per dimension: integer score from 0 to 100, `pass` / `advisory` / `block`, page-target-state, element or region, PRD trace, and observed evidence. It also returns all blocking findings and advisories found within its assigned lens in the same report. For `H2` and `H4`, identify the exact element pair or boundary involved in every overlap, clipping, wrapping, spacing, or overflow finding.
- With one grader, use its score directly. With multiple graders, the reconciled numeric value for each dimension is their median score. Any `block` remains a block regardless of the median. When the highest and lowest scores for one dimension differ by more than 20 points, mark it `disputed`, preserve the evidence rows, and reconcile that evidence inside the same diagnostic wave before repair; do not start another full grading wave merely to sample a different opinion.
- Preserve every Impeccable finding, rubric `block`, and grader disagreement. Failed overall or dimension thresholds, blocks and disputes prevent readiness.
- Before any edit, the parent reconciles the complete Impeccable critique/audit and grading wave into one consolidated defect ledger grouped by semantic root cause. Each family names all known variants, affected surfaces and states, the repair objective, and the acceptance-matrix cases that prove closure. Do not send separate reports to separate writers for the same HTML.
- A below-threshold candidate gets one repair batch by `frontend-design` and one re-review on the new SHA-256. Apply Repair Re-review Scope below. Impeccable critique/audit, required coverage and a complete current assessment remain mandatory. Do not present a below-threshold candidate for Visual Approval.
- If the re-review finds another variant of a family claimed closed, another block, or a disputed dimension, stop at `blocked`. Return a missing or contradictory obligation to the PRD flow. Otherwise propose one structural repair with a complete acceptance matrix. One exceptional successor re-review may be granted only once by an explicit owner decision that approves the changed strategy and acceptance matrix; a generic instruction to continue does not grant it.
- A grader initialization, browser-access, interruption, or report-completion failure is an execution failure inside the current diagnostic wave, not a new grading or repair round. Replace the failed slot at most once when its lens is still required; otherwise record the capability gap. Never dispatch another same-scope review on an unchanged SHA.
- Record the initial diagnostic wave and, when needed, the one repair batch and one re-review with their input and output HTML SHA-256 values, scores, consolidated root-cause families, acceptance cases, and outcome. An owner-requested product or design change after a pass starts a named new revision cycle; it does not extend the completed grading lineage.
- The owning flow records one `UI grading:` line in the matching `ui-design.md` gate: grader count and lenses, rubric scope, frozen PRD and UI-design identities, current candidate HTML SHA-256, Impeccable evidence when HiFi applies, Technical Hard Gate and DOM geometry results, per-dimension grader scores, medians and statuses when applicable, overall score, advisories, disputed dimensions, overall and H1-H9 threshold results, consolidated defect ledger, repair/re-review outcome or blocked owner decision, and the location of the inline detail rows.

## Repair Re-review Scope

The initial diagnostic wave covers the complete approved scope.
Its repair re-review follows the same lineage and attempt budget; it does not open another broad qualitative search.

1. Record changed sources, affected dimensions, surfaces, states, targets and shared consumers in the existing defect ledger.
2. Give every requested repair its inspected capture, concrete defect, applicable requirement or dimension threshold, and observable completion criteria.
3. Recheck each original defect and every affected consumer on the current candidate. Include shared styles, navigation and motion dependencies.
4. Run Impeccable critique and audit again under their required workflow and existing authorization. Preserve their actual scope and required checks.
5. Run the Technical Hard Gate and complete required browser matrix on the current candidate.
6. Inspect changed dimensions and confirm unaffected dimensions against current evidence and the reviewed source diff.
7. Return a complete current `H1`–`H9` assessment, including remaining advisories. Do not copy old scores into a new result without inspection.

Retain every current-candidate receipt, capture and input identity required by `review-evidence.md`.
Do not relabel old captures, refresh stale receipt hashes, or treat a partial inspection as complete coverage.
Missing impact evidence requires broader inspection; unresolved coverage remains `blocked`.
A new concrete blocker expands the affected scope within this attempt. It never grants another repair round.
Preference-only suggestions remain advisories unless evidence proves an accepted requirement or dimension threshold fails.
After required checks pass, present the candidate for Visual Approval without another same-scope review wave.
