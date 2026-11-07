# Design Review Lifecycle

Use the existing Epic, direct-task record or PLAN/RUN as the work record. These rules do not create a second specification or approval database.

| Work | Baseline and required design |
| --- | --- |
| Initial design | Approved product/stack, PRD completeness preflight, direction choice and full HiFi review |
| Enhancement | Current accepted product; added/changed pages and necessary connecting flows; retained direction when unchanged |
| Maintenance | Current product, effective requirements and accepted changes; direct product fixes and verification |
| Explicit full redesign | Complete `ui-design/3` sequence for the named scope |

The approved HiFi is this round's implementation baseline. After delivery, accepted product changes become the maintenance baseline. Do not rewrite historic HiFi, tokens or approvals merely to match routine work. A new product or technology decision returns to the corresponding owner flow.

For a managed Harness maintenance route, freeze the matching `docs/epics/EPIC-*.md` as a PLAN source with `kind: task record` and its full Git `source_revision`. The Epic must carry exact top-level `Design workflow: maintenance`, `UI impact: none` or `UI impact: style`, `Plan ID: <exact plan_id>`, `Plan objective: <exact objective>`, `Requirement refs: REQ-...[, ...]`, and `UI scope: UI-...[, ...]`. Requirement refs match current UI mission traces, and each trace includes this task-record source ID; UI scope matches affected PLAN surfaces. Keep retained UI design, wireframe, HiFi and design-system-pair bytes stable. The current Product Definition and PLAN route/state/target joins still apply. `structure` or `both` follows normal affected design gates; a loose task note or unrelated Epic cannot waive them.

## One Author And Consolidated Approval

Bindings, the `frontend-design` read, research, required surfaces and author self-review follow [Required Skills And Inputs](stages/ui-design.md#required-skills-and-inputs), [Workflow](stages/ui-design.md#workflow) and [Author Self-Review Before Handoff](stages/ui-design.md#author-self-review-before-handoff). The round runs:

(optional, owner-requested [R0 exploration round](#optional-r0-exploration-round) before Product Definition Approval) → Product/stack and PRD preflight with `--ui-contract ui-design/3` → unresolved preferences → three rendered direction studies, each self-checked by the same author → owner select/mix/modify → complete HiFi at every approved and intermediate width, cheap completeness preflight and HiFi author self-review → independent browser, Impeccable critique/audit and H1–H9 wave → diagnostic completeness gate before consolidated repair ([review-evidence.md](review-evidence.md#diagnostic-wave-completeness)) → one repair batch when eligible and its re-review → one human Visual Approval → design-system package compile/update/reuse → Harness handoff check → implementation. A retained `ui-design/2` package keeps its original sequence and conditional compiler. `Delivery profile: mvp` changes this sequence as the mvp paragraph in [Workflow](stages/ui-design.md#workflow) states.

Browser, critique, audit and grading are checks within one wave; repair and re-review follow [Repair Re-review Scope](ui-grading-rubric.md#repair-re-review-scope). Managed mission, integration and security reviews follow their separate Harness contracts.

A `ui-design/2` package has no wireframe, W1–W5, Copy Freeze or human Wireframe Approval stage. It reads the PRD's complete sourced wording and contract directly. The final HiFi review includes wording, structure, product menus, tabs, other interactions, visuals and all product tokens. Formal design-system compilation runs only when the Need Gate requires it.

## Owner Acceptance Closes The Round

Visual Approval closes the round once every required check has its PASS: completeness preflight, browser receipts, Impeccable critique and audit, H1–H9 thresholds and required motion evidence. Acceptance with follow-ups is `approved` when the open ledger rows are non-blocking; each becomes a listed follow-up in the Epic. A block, a failed threshold or missing required evidence cannot be waived by acceptance: the checker admits no waiver, so the candidate stays `blocked` until repaired. After approval the round produces no further gate, receipt, reconciliation or playback record.

Design-system compilation and the Harness handoff consume the accepted candidate and do not reopen its closed round.

Acceptance proves direction conformance, not usability ([UX Direction And Usability Evidence](../../delivery-harness/references/verification-gates.md#ux-direction-and-usability-evidence)).

## Optional R0 Exploration Round

Only when the owner asks, direction studies may run before Product Definition Approval, after the Product Thesis readback and the At a Glance `Shape` row. The default sequence is unchanged without that request. Round ID `R0` (`VD-R0-<n>`): three materially different directions over 2-3 representative screens of the thesis's first useful journey, authored by the same resolved `frontend-design` author under the same [Frontend Visual Inputs](../../delivery-harness/references/frontend-visual-inputs.md) rule. Preflight runs `check_product_package.py` with `--require-filled` and without `--require-approved`; the PRD must already carry the `Shape` row and a drafted UI Surface Contract for the screens shown.

R0 is exploration, not selection. Record the owner's reaction as `REF-*` references and avoid rules in the Visual Preference Brief. No direction is selected, R0 has no approval authority, and no HiFi is built. After Product Definition Approval, round `R1` may reuse, modify or replace the R0 studies; selection happens only in `R1`. R0 never changes product scope, routes, states, copy responsibilities or stack. A wish found in R0 goes back into the PRD draft through Product Definition.

## Incremental Scope And Derived Status

Before an enhancement, record baseline revision and added/changed/preserved paths in the existing task record. Include all consumers of changed shared components and styles. Use this small section in that record:

Design workflow: enhancement

### UI Change Scope

| Disposition | Path | Reason / consumers |
| --- | --- | --- |
| changed | docs/design/ui-references/round/account.html | Accepted account change and return flow |
| preserved | docs/design/ui-references/round/home.html | No product change |
| shared | src/components/navigation.tsx | Account and home regression consumers |

Run from the repository root:

    python "<ui-design-builder-skill-root>/scripts/design_workflow.py" --repo-root . --task-record docs/epics/EPIC-current.md --baseline <observed-commit>

The read-only summary derives HEAD, current changes, record identity, task-file presence, unresolved checkboxes and next work. It checks canonical `docs/goal/PLAN.md` and `docs/goal/RUN.md` plus legacy paths; its `activeTaskFiles` field records paths present on disk only and does not establish an active RUN or live process. A maintenance record is valid only with UI impact `none` or `style`; missing or invalid impact and `structure` or `both` are findings and conservatively set `designRequired`. Structural impacts follow affected design gates. Valid maintenance does not require full design regeneration. Preserved page changes are findings. Inspect product DOM/style and rendered before/after evidence too: file hashes cannot distinguish an intentional shell migration from an unintended product redesign. A new hash never proves semantic equivalence.

At start, significant changes and handoff, reconcile checkout, candidate, uncommitted work, other active tasks and prior results. PLAN revisions preserve completed work and apply at explicit task boundaries. Small work stays direct; durable multi-writer coordination uses the existing managed flow. Reuse timing records for generation, validation, waiting and repair costs.

## Validation Cost And Evidence

The skills suite tests the full common shell. Each product package still verifies every page's integration, isolation, platform/size/state, menu/tab destinations, error recovery, required operations and final full product matrix. Avoid all-pairs shell navigation repetition when the current reviewer contract uses per-page integration cases. Compute changed pages and shared consumers before editing, run focused checks after repair, then retain required final full validation. Never reuse expired browser results. App implementation still requires native proof.

New evidence uses ui-output/3 and ui-evidence/3; see review-evidence.md. Separate machine observations, qualitative findings and human decisions. Repair by root cause under the existing attempt limits; do not reset counters by changing authors or candidates.

## Versions And Migration

Record source, installed and actually loaded skill identities separately; unknown loaded identity remains unknown. Pin each round at intake and finish it on that pin. A bundle change during the round is observed drift ([Run-Scoped Contract Pin](../../delivery-harness/references/runtime-upgrades.md#run-scoped-contract-pin)). A new round re-pins. After a bundle change between rounds, rerun the UI checker on the unchanged artifacts, classify the changed rule as shell, format, validation or design, and renew only affected gates.

wireframes/2–5 and `ui-design` packages without `UI contract: ui-design/2` remain readable under their original meanings. A legacy approved artifact still uses its historical Copy Freeze, Wireframe Approval or Validation, W1–W5 and compiler inputs. Do not relabel it or fabricate a new human decision. The legacy heading does not keep old HiFi evidence rules. A legacy Visual Approval decided on or after 2026-09-27 (the 0.55.0 release), or with any HiFi Review or motion-effect receipt executed at or after 2026-09-27T00:00:00Z, always needs ui-evidence/3, reviewer shell version 3 and `direction`/`hifi` Frontend Design Usage rows, and its Decided on must not predate that evidence; committing or backdating it does not make it historical. An earlier approval keeps its ui-evidence/2 HiFi receipts only while its Approved target equals the one committed at HEAD; a new or changed target needs current evidence. The UI checker, the compiler preflight and Harness 0.55.1+ UI and pair joins enforce the dated rule. New initial and full-redesign packages use `ui-design/3`; `ui-design/2` packages keep their original meaning, including `not_required` gates. Existing products migrate gradually under authorized scope. Migrate through a fresh owner-selected direction and complete HiFi, rerun affected product checks, and preserve historical bytes/receipts. A shell-only update never authorizes product redesign.

Publication, installation, commits, branches/worktrees, provider calls and cleanup retain their own exact authorization boundaries.

## Required Product Operations

Before designing, read necessary Home, back, cancel, recovery, navigation and tab actions from each PRD task. The PRD UI Surface Contract's invariant operations anchor keeps their meaning product-owned. This explicit list prevents directions and HiFi from both omitting the same operation.

Example:

- `operations`: [{"id":"OP-account-home","trigger":"Home","control":"home","sourceState":"ready","destination":{"surface":"UI-001","state":"ready"},"presentation":"page"}]

Each operation uses exactly id, trigger, control (HiFi product control ID), sourceState, destination (surface/state) and presentation (page, overlay, feedback, state or tab). IDs are unique. An informational surface with no action records none — followed by a concrete reason. Include open/close, selection, recovery and state changes when the PRD requires them. Compare actual browser destinations and visible content; updating an active class alone is insufficient.

The PRD-side checker joins these operations to the UI Surface Contract, and the HiFi completeness preflight joins them to manifest interactions before formal review. The browser checker rejects missing required controls, invented states/destinations and HiFi actions without a product operation. For legacy schema-5 approval gates, `check_ui_design_contract.py` uses `operation_coverage.py` to join each operations anchor to Wireframe flows and, for Visual Approval, to HiFi interactions. Neither check can infer an omitted requirement from prose: the Product Definition review must reconcile this list with user tasks, including Home/back/cancel. Retain browser evidence of destinations and visible results in the existing review evidence. A structural check without the required approval flags does not establish operation coverage.
