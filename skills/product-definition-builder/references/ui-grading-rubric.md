# UI Grading Rubric

This rubric defines the PRD-bound diagnostic and grading stage that runs after the first `wireframes.html` or high-fidelity HTML draft and before its human UI gate. It supplements the browser matrix check and static checker; it never replaces either one or the human approval decision. Correctness comes from explicit hard-gate evidence. Numeric scores summarize comparative visual quality and never create another repair round by themselves.

## Frozen Grading Basis

Before dispatch, the parent records the exact PRD path plus revision or SHA-256 and the candidate HTML path plus SHA-256. Every grader receives the same frozen inputs: the `UI-*` surfaces, `UX-*` traces, actions, flows, states, responsive targets, Builder UX Direction, approved copy or display contracts, and the candidate HTML. Graders score only conformance to those inputs. They do not add screens, flows, visual preferences, media, or motion.

A missing or contradictory PRD obligation returns to the PRD flow. Graders never resolve it by inventing a preferred behavior. A direct contradiction between the artifact and a clear PRD obligation is a `block` regardless of numeric score.

## Capability And Authorization

- First observe whether the host can dispatch fresh read-only agents that can open the local HTML in a real browser. Capability does not grant permission.
- When that capability is unavailable, skip only the multi-agent stage and record `UI grading: skipped — multi-agent capability unavailable` with the frozen PRD and artifact identities. Continue the static checker, browser matrix check, and human gate. Do not label a parent-only review as multi-agent grading.
- When the capability is available, require explicit delegation authorization for this grading stage or the matching current RUN `spawn_subagents` grant before dispatch. If authorization is missing, do not spawn; pause the grading stage for the owner rather than treating capability as permission.
- Run one complete diagnostic wave before any repair. Default to one fresh lead grader that walks the complete in-scope `UI-* × responsive target × non-n/a state` matrix and must return every finding it can establish, not stop at the first block.
- Add at most two fresh specialist sibling graders only when the owner requests independent review or a recorded high-impact risk justifies separate accessibility, localization/state, or visual lenses. Give specialists non-overlapping lenses over the same frozen inputs. All dispatched graders finish the same diagnostic wave before the parent begins repair; they do not share notes or open later waves to look for more examples.
- Graders are read-only and advisory: they never edit files, mint trace IDs, contact the owner, or approve the artifact.

## Scores

Each dimension receives one integer score from `0` to `100` and a status:

- `80–100 — pass`: meets the grading threshold and matches the frozen PRD without a blocking issue;
- `60–79 — advisory`: records a qualitative weakness for the human decision owner but does not trigger repair unless the evidence also proves a PRD contradiction, Technical Hard Gate failure, critical-dimension failure, or other explicit block; or
- `0–59 — block`: a required screen, action, state, responsive behavior, readable layout, or other PRD obligation is missing or broken.

The wireframe overall score is the arithmetic mean of `W1` through `W5`; it is ready for its human structural gate only when the overall score is at least `80`, every dimension is at least `60`, and it has no `block`. The high-fidelity overall score is the arithmetic mean of `H1` through `H9`, rounded to the nearest integer; it is ready for its human visual gate only when the overall score is at least `90`, every dimension is at least `60`, `H2 Layout safety`, `H4 Responsive and edge states`, and `H8 Accessibility` each score at least `90`, and it has no `block`. Scores never average away a `block` or a critical high-fidelity threshold. Once those conditions pass, do not repair or regrade merely to raise a score toward 100; carry any advisory to the human gate.

## Technical Hard Gate

Apply this before numeric grading. The HTML must open as one self-contained local file, render meaningful content, make no unexpected network, backend, authentication, or generation request, and produce no uncaught console error or broken runtime overlay. Every in-scope page, state, action, overlay, and responsive target must remain reachable after a clean reload, without duplicate event effects or stale state leaking between screens. At every matrix entry, run a DOM geometry scan over visible peer elements and their container and viewport bounds; ignore ancestor-descendant containment and only the overlays explicitly allowed by the PRD. Record the selectors or stable element IDs for every collision, clipping, off-container boundary, and horizontal overflow result. A failure is a `block`; intentional deferred media or motion placeholders are not broken assets.

## Wireframe Scope

- `W1 PRD conformance`: every `UI-*` screen, route, region responsibility, action, flow, state, responsive target, and trace agrees with the frozen PRD.
- `W2 Layout safety`: no reviewer-shell or canvas element is unintentionally overlapped, clipped, occluded, or forcing horizontal page scrolling. An intended overlay passes only when its PRD interaction rule names stacking, focus, and dismissal.
- `W3 Interaction`: every visible region action works from the local file. It navigates to the PRD-recorded screen, opens the recorded overlay, or shows the recorded local feedback; the page switcher, all-pages overview, responsive-target control, state control, and runtime layout QA also work.
- `W4 Responsive and state integrity`: every never-drop region stays visible with the declared order and spans, and every non-`n/a` state is selectable at every target.
- `W5 Structural slop`: apply the structural items below against the PRD rather than grader taste.

## High-Fidelity HTML Scope

- `H1 PRD and direction conformance`: every included surface follows the frozen PRD and selected `VD-*` direction. Login, registration, recovery, and authentication-error previews are excluded only when the PRD records them as `n/a` for this visual pass.
- `H2 Layout safety`: inspect all visible peer elements, controls, text blocks, media placeholders, and overlays in the retained all-screens HTML. No required element may unintentionally overlap another, clip, become occluded, collide through broken spacing or wrapping, leave its container, or force horizontal page overflow. Intended overlays pass only with their recorded stacking, focus, safe-area, and dismissal behavior. Any such failure on required content is a `block`.
- `H3 Interaction wiring`: every visible product control responds by navigating, switching a declared state, opening a documented overlay, or showing recorded inline feedback. Dead controls and isolated stills are blocks.
- `H4 Responsive and edge states`: repeat the element-level `H2` inspection at every PRD-declared viewport or size class and every non-`n/a` state. Long labels, localized copy, validation errors, empty data, and dense data stay readable and usable; layout reflows in the recorded order, spacing remains intentional, and resizing never strands focus, hides a required action, creates clipping, or introduces horizontal overflow. Any failure on required content is a `block`.
- `H5 Visual slop`: apply the visual items below against the selected `VD-*` direction.
- `H6 Media and motion fit`: apply the PRD Motion Need Gate. Required functional UI motion is represented locally in the high-fidelity HTML with its trigger, purpose, timing intent, and reduced-motion fallback; its absence or a fallback that loses meaning is a `block`. Recommended motion supports hierarchy or brand without hiding content or becoming required for comprehension. A `not_required` surface adds no decorative motion beyond platform-standard functional feedback. Generated video, illustration animation, cinematic treatment, or other provider-created motion remains a static placeholder with a dedicated prompt, source decision, placement, reduced-motion expectation, and `generationStatus: deferred`; the HTML never invokes a generation provider or pretends generated output exists.
- `H7 Creative distinction`: composition, hierarchy, interaction concepts, and content presentation feel intentional and specific to the product rather than interchangeable with a generic template. Creativity must support the frozen PRD and selected `VD-*` direction; it earns no credit by adding unapproved scope, obscuring content, weakening accessibility, breaking familiar controls, or pretending deferred media exists.
- `H8 Accessibility`: keyboard-only use reaches every in-scope action and state with a visible logical focus order; dialogs and drawers move, contain, dismiss, and restore focus correctly; controls have meaningful names, roles, states, and usable target sizes; headings, landmarks, status announcements, contrast, zoom, and reduced-motion behavior meet the frozen PRD accessibility requirements. Any required flow that is unavailable without a pointer, loses focus, or exposes an unnamed control is a `block`.
- `H9 Design consistency`: repeated components, spacing, typography, color roles, icon meaning, control hierarchy, and ready/hover/focus/disabled/error states remain coherent across screens and responsive targets. A deliberate exception passes only when the selected direction or PRD explains it; accidental component drift or inconsistent interaction meaning is an advisory or block according to user impact.

## AI-Slop Checklist

Structural items, wireframe scope:

- Unrelated screens share an identical skeleton with no PRD reason.
- Filler content ignores the bounded display contracts or approved copy.
- Section-purpose labels are missing, duplicated meaninglessly, or name no responsibility.
- A region exists that no `UI-*` entry or flow accounts for.

Visual items, high-fidelity scope:

- The rendering ignores the selected `VD-*` direction and reads as a generic default.
- Identical section rhythms repeat across unrelated screens with no directional reason.
- Decorative gradients, glows, labels, emoji, status dots, or fake-precise numbers appear without support from the approved direction or copy source.
- Controls exist purely as decoration and do nothing when used.
- A media or motion placeholder uses a generic prompt that does not name its page, position, purpose, and constraints.

## Reporting And Reconciliation

- Each grader returns one row per dimension: integer score from 0 to 100, `pass` / `advisory` / `block`, page-target-state, element or region, PRD trace, and observed evidence. It also returns all blocking findings and advisories found within its assigned lens in the same report. For `H2` and `H4`, identify the exact element pair or boundary involved in every overlap, clipping, wrapping, spacing, or overflow finding.
- With one grader, use its score directly. With multiple graders, the reconciled numeric value for each dimension is their median score. Any `block` remains a block regardless of the median. When the highest and lowest scores for one dimension differ by more than 20 points, mark it `disputed`, preserve the evidence rows, and reconcile that evidence inside the same diagnostic wave before repair; do not start another full grading wave merely to sample a different opinion.
- The parent preserves every `block` and any grader disagreement. A high-fidelity candidate is below threshold when its overall score is below 90, `H2`, `H4`, or `H8` is below 90, any dimension is below 60, any `block` remains, or any dimension is `disputed`.
- Before any edit, the parent reconciles the complete diagnostic wave into one consolidated defect ledger grouped by semantic root cause. Each family names all known variants, affected surfaces and states, the structural repair objective, and the acceptance-matrix cases that prove closure. Do not send separate grader reports to separate writers for the same HTML.
- A below-threshold candidate gets one repair batch by the artifact's single owning writer and one re-review on the new SHA-256. The re-review repeats the Technical Hard Gate and browser matrix, verifies every ledger family and its acceptance cases, and rescans the full rubric once; it does not start a new open-ended diagnostic cycle. A partial re-score cannot clear the gate. Do not present a below-threshold candidate for human visual approval.
- If the re-review finds another variant of a family claimed closed, another block, or a disputed dimension, stop at `blocked`. Return a missing or contradictory obligation to the PRD flow. Otherwise propose one structural repair with a complete acceptance matrix. One exceptional successor re-review may be granted only once by an explicit owner decision that approves the changed strategy and acceptance matrix; a generic instruction to continue does not grant it.
- A grader initialization, browser-access, interruption, or report-completion failure is an execution failure inside the current diagnostic wave, not a new grading or repair round. Replace the failed slot at most once when its lens is still required; otherwise record the capability gap. Never dispatch another same-scope review on an unchanged SHA.
- Record the initial diagnostic wave and, when needed, the one repair batch and one re-review with their input and output HTML SHA-256 values, scores, consolidated root-cause families, acceptance cases, and outcome. An owner-requested product or design change after a pass starts a named new revision cycle; it does not extend the completed grading lineage.
- The owning flow records one `UI grading:` line in the matching PRD record: grader count and lenses, rubric scope, frozen PRD identity, current candidate HTML SHA-256, Technical Hard Gate and DOM geometry results, per-dimension grader scores, medians and statuses when applicable, overall score, advisories, disputed dimensions, the `H2`, `H4`, and `H8` critical-threshold results, consolidated defect ledger, repair/re-review outcome or blocked owner decision, and the location of the inline detail rows.
