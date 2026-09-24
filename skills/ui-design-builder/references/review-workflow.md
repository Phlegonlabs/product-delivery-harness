# Design Review Lifecycle

Use the existing Epic, direct-task record or PLAN/RUN as the work record. These rules do not create a second specification or approval database.

| Work | Baseline and required design |
| --- | --- |
| Initial design | Approved product/stack, complete structure, direction choice and full HiFi review |
| Enhancement | Current accepted product; added/changed pages and necessary connecting flows |
| Maintenance | Current product, effective requirements and accepted changes; direct product fixes and verification |
| Explicit full redesign | Complete design sequence for the named scope |

The approved HiFi is this round's implementation baseline. After delivery, accepted product changes become the maintenance baseline. Do not rewrite historic HiFi, tokens or approvals merely to match routine work. A new product or technology decision returns to the corresponding owner flow.

For a managed Harness maintenance route, freeze the matching `docs/epics/EPIC-*.md` as a PLAN source with `kind: task record` and its full Git `source_revision`. The Epic must carry exact top-level `Design workflow: maintenance`, `UI impact: none` or `UI impact: style`, `Plan ID: <exact plan_id>`, `Plan objective: <exact objective>`, `Requirement refs: REQ-...[, ...]`, and `UI scope: UI-...[, ...]`. Requirement refs match current UI mission traces, and each trace includes this task-record source ID; UI scope matches affected PLAN surfaces. Keep retained UI design, wireframe, HiFi and design-system-pair bytes stable. The current Product Definition and PLAN route/state/target joins still apply. `structure` or `both` follows normal affected design gates; a loose task note or unrelated Epic cannot waive them.

## One Author And Consolidated Approval

Before Wireframe authoring or repair, and again before direction/HiFi authoring or repair, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage ui-design` with installed-command resolution. The actual writer loads the full owner-pinned `frontend-design` skill in its own context. Parent reading, a snapshot, a role name or prior-stage invocation is no substitute; do not backfill evidence or replace the binding. Missing or conflicting dependencies block only that authoring stage and preserve earlier approvals and closed history. This requirement grants no spawn action; a direct parent may author. Preserve one design author. Assemblers build the shell, Impeccable and graders validate, and neither makes product-design decisions. Record source digest, output identity and applied choices in Frontend Design Usage; the record proves traceability, not quality.

Combine missing design, image and motion preferences. Reuse supplied answers. Run:

Product/stack confirmation → unresolved preferences → internal Wireframe Validation → direction selection → complete HiFi, technical checks, Impeccable and grading → one human Visual Approval → implementation.

Wireframe has no human Copy Freeze or Wireframe Approval gate in schema 5. It keeps complete sourced wording and W1–W5. The final HiFi review includes wording, structure, product menus, tabs, other interactions, visuals and all product tokens. Formal design-system compilation runs only when the Need Gate requires it.

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

Record source, installed and actually loaded skill identities separately; unknown loaded identity remains unknown. Pin each round. Before upgrading, classify the effect: reviewer shell, schema/format, validation rule, or product design. Evaluate affected evidence and retain valid product decisions.

wireframes/2–4 and ui-evidence/2 remain readable under their original meanings. A schema-4 approved artifact still uses its historical Copy Freeze and human Wireframe Approval. Do not relabel those as schema 5 or fabricate a new human decision. New or next enhancement packages use schema 5; existing products migrate gradually under authorized scope. Migrate data through reviewable changes, rerun structure and affected product checks, and preserve historical bytes/receipts. A shell-only update never authorizes product redesign.

Publication, installation, commits, branches/worktrees, provider calls and cleanup retain their own exact authorization boundaries.

## Required Product Operations

Before designing, derive necessary Home, back, cancel, recovery, navigation and tab actions from each PRD task. In each UI surface's existing contract, add one invariant operations anchor. Keep its meaning product-owned. This explicit list prevents Wireframe and HiFi from both omitting the same operation.

Example:

- `operations`: [{"id":"OP-account-home","trigger":"Home","control":"home","sourceState":"ready","destination":{"surface":"UI-001","state":"ready"},"presentation":"page"}]

Each operation uses exactly id, trigger (Wireframe action label), control (HiFi product control ID), sourceState, destination (surface/state) and presentation (page, overlay, feedback, state or tab). IDs are unique. An informational surface with no action records none — followed by a concrete reason. Include open/close, selection, recovery and state changes when the PRD requires them. Compare actual browser destinations and visible content; updating an active class alone is insufficient.

The new UI checker joins these PRD operations to Wireframe flows and HiFi interactions. It rejects missing required controls, invented states/destinations and HiFi actions without a product operation. The schema cannot infer an omitted requirement from prose: the Product Definition review must reconcile this list with user tasks, including Home/back/cancel.
