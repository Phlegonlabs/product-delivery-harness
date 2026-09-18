# UI Grading Rubric

This rubric defines the Product-Definition-bound diagnostic and grading stage that runs after a schema-4 wireframe passes its Copy Freeze Gate, or after the first HiFi design-reference HTML draft, and before the matching human UI gate. It supplements the browser matrix check, static checker, and required Impeccable HiFi review; it never replaces them or the human approval decision. Correctness comes from explicit hard-gate evidence. Numeric scores summarize comparative quality and never create another repair round by themselves.

## Frozen Grading Basis

Before dispatch, the parent records the exact PRD and `ui-design.md` paths plus revisions or SHA-256 values and the candidate HTML path plus SHA-256. A wireframe grader also receives the passing `--require-copy-approved` result; without it, grading has not started. Every grader receives the same frozen inputs: the `UI-*` surfaces, `UX-*` traces, actions, flows, states, responsive targets, UI Design Intake, approved Copy Freeze, Motion and Media Intent, selected direction when applicable, and the candidate HTML. Graders score only conformance to those inputs. They do not add screens, flows, visual preferences, copy, media, or motion.

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
- `60–79 — advisory`: records a qualitative weakness for the human decision owner but does not trigger repair unless the evidence also proves a PRD contradiction, Technical Hard Gate failure, critical-dimension failure, or other explicit block; or
- `0–59 — block`: a required screen, action, state, responsive behavior, readable layout, or other PRD obligation is missing or broken.

The wireframe overall score is the arithmetic mean of `W1` through `W5`; it is ready for its human structural gate only when the overall score is at least `80`, `W5` is at least `80`, every dimension is at least `60`, and it has no `block`. The design-reference overall score is the arithmetic mean of `H1` through `H9`, rounded to the nearest integer; it is ready for its human visual gate only when the overall score is at least `90`, every dimension is at least `60`, `H2 Layout safety`, `H4 Responsive and edge states`, and `H8 Accessibility` each score at least `90`, `H5 Visual slop`, `H7 Creative distinction`, and `H9 Design consistency` each score at least `80`, and it has no `block`. Scores never average away a `block` or a critical design-reference threshold. Once those conditions pass, do not repair or regrade merely to raise a score toward 100; carry any advisory to the human gate.

## Technical Hard Gate

Apply this before numeric grading. The HiFi must open as a connected local HTML package (the wireframe remains one self-contained file), render meaningful content, make no unexpected network, backend, authentication, or generation request, and produce no uncaught console error or broken runtime overlay. Every HiFi page has exactly one canonical restrictive CSP meta; the required closed policy is recorded in the output contract. Schema-2 HiFi follows the local-page allowlist and click/keyboard ui-output/2 contract in output-contract.md; every product control must reach its declared visible destination with correct focus. Schema-1 remains inspection-only and cannot pass current Visual Approval. Its historical surface checks run with method `sandboxed-offline-browser` inside a sandbox with network disabled and top navigation, popups, and forms blocked. The retained `ui-output/1` artifact contains the console, network, and navigation transcript; any error or attempt is a block. This receipt boundary complements the static CSP and does not claim regex can prove arbitrary JavaScript safe. Every in-scope page, state, action, overlay, responsive target, reviewer-inspector view, and copy-inventory record must remain reachable after a clean reload, without duplicate event effects or stale state leaking between screens. For `wireframes/4`, static product copy, action labels, feedback and alternate-state messages, and dynamic display contracts must already have passed the Copy Freeze Gate; reviewer notes must not appear as product copy. At every matrix entry, run a DOM geometry scan over visible peer elements and their container and viewport bounds; ignore ancestor-descendant containment and only the overlays explicitly allowed by the PRD. Record the selectors or stable element IDs for every collision, clipping, off-container boundary, and horizontal overflow result. A failure is a `block`; intentional deferred media or motion placeholders are not broken assets.

## Wireframe Scope

- `W1 PRD conformance`: every `UI-*` screen, route, required content/control responsibility, action, flow, state, responsive target, and trace agrees with the frozen PRD; the wireframe's region grouping and order introduce no new product obligation.
- `W2 Layout safety`: no reviewer-shell or canvas element is unintentionally overlapped, clipped, occluded, or forcing horizontal page scrolling. An intended overlay passes only when its PRD interaction rule names stacking, focus, and dismissal.
- `W3 Interaction`: every visible region action works from the local file. It navigates to the PRD-recorded screen, opens the recorded overlay, or shows the recorded local feedback; the page switcher, all-pages overview, responsive-target control, state control, and runtime layout QA also work.
- `W4 Responsive and state integrity`: every never-drop region stays visible with the declared order and spans, and every non-`n/a` state is selectable at every target.
- `W5 Structural clarity and evidence`: the canvas makes product hierarchy, content density, and responsive composition legible without pretending to be final visual design; product copy is clearly separated from reviewer notes; the `WREF-*` decisions support rather than decorate the chosen structure; apply the structural items below against the PRD rather than grader taste.

### W5 Composition Criteria

The Design System Draft view participates in existing checks: W2 covers its readable layout, W3 its navigation and working specimen controls, and W5 its agreement with actual canvas values and classes. Verify type, spacing and control specimens from rendered values, not a manually copied table. Reviewer samples add no PRD copy or product surface. W3 primary-journey evidence must use product controls; read-only fields and review-shell state switches cannot prove required input, validation or recovery behavior. An unsupported required interaction blocks readiness until the canonical renderer supports it. Keep formal brand-token approval in the later visual/compiler stages.

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
| Review separation and neutrality | The default product canvas has no IDs, priority badges, review buttons, or inherited green tint. Annotations remain reachable separately. |

Record each criterion's observation, page-target-state, and inspected screenshot path/hash in the existing grading detail. Show the representative cases with annotations off and check annotation access separately. Cite the relevant PRD/intake/reference decision for each weakness. W5 below 80 blocks readiness even when the overall score passes; merely removing color or passing geometry checks does not establish composition quality. Do not grade a preferred brand style or freeze final fonts, colors, or tokens here.

## Design-Reference HTML Scope

- `H1 Product, copy, and direction conformance`: every included surface follows the frozen PRD, `ui-design.md`, approved copy-frozen wireframe, and selected `VD-*` direction. Login, registration, recovery, and authentication-error previews are excluded only when the UI design contract records them as `n/a` for this visual pass. Any design-stage wording change is a block until its copy delta is approved through Product Definition and renewed Copy Freeze.
- `H2 Layout safety`: inspect all visible peer elements, controls, text blocks, media placeholders, and overlays in the retained all-screens HTML. No required element may unintentionally overlap another, clip, become occluded, collide through broken spacing or wrapping, leave its container, or force horizontal page overflow. Intended overlays pass only with their recorded stacking, focus, safe-area, and dismissal behavior. Any such failure on required content is a `block`.
- `H3 Interaction wiring`: every visible product control responds by navigating, switching a declared state, opening a documented overlay, or showing recorded inline feedback. Dead controls and isolated stills are blocks.
- `H4 Responsive and edge states`: repeat the element-level `H2` inspection at every PRD-declared viewport or size class and every non-`n/a` state. Long labels, localized copy, validation errors, empty data, and dense data stay readable and usable; layout reflows in the recorded order, spacing remains intentional, and resizing never strands focus, hides a required action, creates clipping, or introduces horizontal overflow. Any failure on required content is a `block`.
- `H5 Visual slop`: apply the visual items below against the selected `VD-*` direction.
- `H6 Media and motion fit`: apply `ui-design.md`'s Motion and Media Intent. Required functional UI motion is represented locally with its trigger, purpose, timing intent, and reduced-motion fallback; its absence or a fallback that loses meaning is a `block`. A `not_required` surface adds no decorative motion beyond platform-standard functional feedback. Each image, motion, or combined treatment matches its typed wireframe placeholder and approved generation route. A Higgsfield or other provider asset is accepted only with recorded authorization, output identity, placement, usage constraints, and fallback; otherwise it remains a static deferred placeholder. The HTML never invokes an unapproved provider or pretends generated output exists.
- `H7 Creative distinction`: composition, hierarchy, interaction concepts, and content presentation feel intentional and specific to the product rather than interchangeable with a generic template. The approved direction has one coherent thesis and a complementary reference-role map; it does not splice unrelated source aesthetics into a collage. Creativity must support the frozen PRD and selected `VD-*` direction; it earns no credit by adding unapproved scope, rewriting copy, obscuring content, weakening accessibility, breaking familiar controls, or pretending deferred media exists.
- `H8 Accessibility`: keyboard-only use reaches every in-scope action and state with a visible logical focus order; dialogs and drawers move, contain, dismiss, and restore focus correctly; controls have meaningful names, roles, states, and usable target sizes; headings, landmarks, status announcements, contrast, zoom, and reduced-motion behavior meet the frozen PRD accessibility requirements. Any required flow that is unavailable without a pointer, loses focus, or exposes an unnamed control is a `block`.
- `H9 Design consistency`: repeated components, spacing, typography, color roles, icon meaning, control hierarchy, and ready/hover/focus/disabled/error states remain coherent across screens and responsive targets. A deliberate exception passes only when the selected direction or PRD explains it; accidental component drift or inconsistent interaction meaning is an advisory or block according to user impact.

## AI-Slop Checklist

For `H5`, `H7`, and `H9`, attach inspected candidate screenshots with path/hash, page-target-state, and the exact region behind each finding. Explain typography, alignment, density, spacing, hierarchy, or component treatment against the selected direction and its confirmed references. A score without this visual basis is incomplete review evidence. Check a frequent working screen and a dense or alternate state, not only an attractive entry screen; use only cases that exist in the approved scope.

Calibrate with owner-confirmed reference principles: `60–79` means usable but visibly generic or inconsistent, `80–89` means intentional and coherent with named remaining weaknesses, and `90–100` means refined execution demonstrated across the inspected cases. Familiar native controls can be excellent design; novelty, decoration, custom fonts, and motion earn no points by themselves. A sub-80 visual-quality dimension blocks readiness even when the overall average passes. Validators check recorded thresholds and evidence consistency, not beauty or whether a screenshot was honestly inspected.

Structural items, wireframe scope:

- Unrelated screens share an identical skeleton with no PRD reason.
- Product copy remains generic, draft, ambiguous, or mixed with reviewer-only purpose and trace notes.
- Dynamic examples omit source, order, format, count, length, or fallback, so implementation must guess.
- Section-purpose labels are missing, duplicated meaninglessly, or name no responsibility.
- A region exists that no `UI-*` entry or flow accounts for.
- `WREF-*` entries cite an attractive category peer without matching the exact screen, flow, viewport, or state they supposedly support.

Visual items, design-reference scope:

- The rendering ignores the selected `VD-*` direction and reads as a generic default.
- The rendering changes approved wording or converts a dynamic example into fixed product copy.
- Identical section rhythms repeat across unrelated screens with no directional reason.
- Decorative gradients, glows, labels, emoji, status dots, or fake-precise numbers appear without support from the approved direction or copy source.
- Controls exist purely as decoration and do nothing when used.
- A media or motion placeholder uses a generic prompt that does not name its page, position, purpose, and constraints.
- Several reference aesthetics appear side by side with no single direction thesis or Adopt / Adapt / Avoid rationale.

## Reporting And Reconciliation

- Each grader returns one row per dimension: integer score from 0 to 100, `pass` / `advisory` / `block`, page-target-state, element or region, PRD trace, and observed evidence. It also returns all blocking findings and advisories found within its assigned lens in the same report. For `H2` and `H4`, identify the exact element pair or boundary involved in every overlap, clipping, wrapping, spacing, or overflow finding.
- With one grader, use its score directly. With multiple graders, the reconciled numeric value for each dimension is their median score. Any `block` remains a block regardless of the median. When the highest and lowest scores for one dimension differ by more than 20 points, mark it `disputed`, preserve the evidence rows, and reconcile that evidence inside the same diagnostic wave before repair; do not start another full grading wave merely to sample a different opinion.
- The parent preserves every Impeccable finding, rubric `block`, and grader disagreement. A design-reference candidate is below threshold when its overall score is below 90, `H2`, `H4`, or `H8` is below 90, `H5`, `H7`, or `H9` is below 80, any dimension is below 60, any `block` remains, or any dimension is `disputed`.
- Before any edit, the parent reconciles the complete Impeccable critique/audit and grading wave into one consolidated defect ledger grouped by semantic root cause. Each family names all known variants, affected surfaces and states, the repair objective, and the acceptance-matrix cases that prove closure. Do not send separate reports to separate writers for the same HTML.
- A below-threshold candidate gets one repair batch by `frontend-design`, the artifact's single owning writer, and one re-review on the new SHA-256. The HiFi re-review repeats Impeccable critique/audit, the Technical Hard Gate, browser matrix, every ledger acceptance case, and the full rubric once. It does not start a new open-ended diagnostic cycle. A partial re-score cannot clear the gate. Do not present a below-threshold candidate for human visual approval.
- If the re-review finds another variant of a family claimed closed, another block, or a disputed dimension, stop at `blocked`. Return a missing or contradictory obligation to the PRD flow. Otherwise propose one structural repair with a complete acceptance matrix. One exceptional successor re-review may be granted only once by an explicit owner decision that approves the changed strategy and acceptance matrix; a generic instruction to continue does not grant it.
- A grader initialization, browser-access, interruption, or report-completion failure is an execution failure inside the current diagnostic wave, not a new grading or repair round. Replace the failed slot at most once when its lens is still required; otherwise record the capability gap. Never dispatch another same-scope review on an unchanged SHA.
- Record the initial diagnostic wave and, when needed, the one repair batch and one re-review with their input and output HTML SHA-256 values, scores, consolidated root-cause families, acceptance cases, and outcome. An owner-requested product or design change after a pass starts a named new revision cycle; it does not extend the completed grading lineage.
- The owning flow records one `UI grading:` line in the matching `ui-design.md` gate: grader count and lenses, rubric scope, frozen PRD and UI-design identities, current candidate HTML SHA-256, Impeccable evidence when HiFi applies, Technical Hard Gate and DOM geometry results, per-dimension grader scores, medians and statuses when applicable, overall score, advisories, disputed dimensions, the `H2`, `H4`, and `H8` safety-threshold results and `H5`, `H7`, and `H9` visual-quality-threshold results, consolidated defect ledger, repair/re-review outcome or blocked owner decision, and the location of the inline detail rows.
