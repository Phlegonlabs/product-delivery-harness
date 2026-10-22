# Task And Handoff Governance

These procedures are the rule owners for task entry, repository checkpoints, handoff review, and completion. They do not grant Git, deployment, installation, publication, or other external actions.

## Project Entry And Current Work

This is the entry checklist. Run it at the first work in a session. A later invocation reuses it while HEAD and the instruction bytes match; rerun it when either changed or at handoff. Read each linked contract in full only when its trigger fires.

1. Read the effective repository instructions, `docs/DOCUMENTS.md` when present, current product/design sources and relevant unfinished work. Resolve every `delivery-harness/` reference against the observed installed delivery-harness skill root, not a presumed target-local `skills/` directory. In this skill-source repository, it resolves as `skills/delivery-harness/references/`.
2. Run the document-sync inventory with the Repository Change Checkpoint below. Pass `--loaded-digest` when the host exposes it, otherwise this session's `--session-marker`; unknown means unknown, not the current disk version. The parent runs the full global inventory at first entry and after a source, instruction, scope, skill identity, cross-stage dependency or handoff change.

   ```text
   python "<delivery-harness-skill-root>/scripts/check_document_sync.py" --repo-root <project-root> --baseline docs/document-sync.json
   ```

   Read [document-sync-contract](../document-sync-contract.md) when the report needs review or input is invalid, when no baseline exists, and before a child inventory. Design consumers then apply [design-freshness](../../../ui-design-builder/references/design-freshness.md).
3. Select the record before implementation. A new accepted outcome gets `docs/epics/EPIC-<id>.md`, indexed in `docs/DOCUMENTS.md`. Small fixes append to the matching Epic. A Harness bundle adoption is one Change Log row with the adopted digest in the current Epic, never a new Epic. Keep one current PRD. [Epic Selection](../bounded-enhancement.md#epic-selection-and-change-history) owns the details.
4. Record the goal, write scope, design source, dependencies and acceptance checks in the existing task record or PLAN/RUN. Preserve valid decisions and authorizations; ask only about a concrete missing dependency.
5. Read these contracts on their trigger:
   - [bounded-enhancement](../bounded-enhancement.md): the owner accepts an enhancement scope, or a repair, module replacement or next-round handoff starts.
   - [delegation-contract](../delegation-contract.md): before you assign work to another executor or launch one. Before a frontend author dispatch, also [frontend-visual-inputs](../frontend-visual-inputs.md).
   - [gen-verify-correct](../gen-verify-correct.md): a checkpoint verifier or review fails or returns findings.
   - [prd-refinement](../../../product-definition-builder/references/prd-refinement.md): a stage checkpoint finds new product evidence.
   - [Product Contracts](product-contracts.md#consumer-keep-product-contracts-current): an English PRD or architecture has no Chinese copy.
   - Other triggers: the project `AGENTS.md` Mandatory Governance Routes.

## Repository Change Checkpoints

These checks apply to every agent task, including work outside Product Delivery Harness and repositories without PLAN/RUN. Run them at task start, after a significant edit/commit/merge/branch switch or newly observed external change, and before completion or handoff. They are task checkpoints, not a background timer, and require only local Git plus the repository documents. At task start, this checkpoint and the document-sync inventory are one entry check with one record; the document-sync contract owns the full global inventory triggers.

- Observe repository root, branch, HEAD, staged/unstaged changes and non-ignored untracked paths. Compare with the last recorded repository/branch/HEAD and scoped change evidence in the relevant Epic. Use bounded local history and scoped diffs; do not fetch, scan all history or open credential files. Include commits made outside Harness as well as current working-tree changes.
- If the baseline is missing, unreachable or belongs to another branch/repository, record a first observation or baseline gap and the current facts. Do not claim an exact delta or that nothing changed. Preserve unrelated dirty work; discovering a change is not permission to edit it.
- Record each meaningful code, product, configuration or documentation change in `docs/epics/EPIC-<id>.md`, even for small direct work. Append to the matching Epic's Change Log; create a narrowly scoped Epic only when no suitable one exists. An unknown-purpose external change is `observed / unverified` with an explicit scope/intent gap, not an accepted feature or completed task. Keep `docs/DOCUMENTS.md` indexed.
- Keep the record factual: observation time, repository/branch, baseline and observed HEAD, affected paths and requirement IDs when known, observed behavior/change, decision source if known, actual verification and unresolved work. Label uncommitted evidence `working-tree` and record its actual verification separately; HEAD alone does not identify those bytes. Retain scoped diff evidence or its fingerprint so an unchanged HEAD cannot hide new edits. Exclude secrets, generated caches and the Epic/index update itself from recursive change logging.
- Group related changes into one logical entry; append again only when the observed change, verification or unresolved state differs. Reuse an existing entry from another agent instead of duplicating it. A no-change check needs no new Epic or log row. Preserve old results and archived records; a follow-up links them rather than rewriting history.
- During a read-only or no-write task, report the proposed Epic update without writing it. Otherwise update the Epic/index under the task's local documentation authority. The record never grants product approval, marks tests passed without evidence, creates PLAN/RUN, or authorizes commits, branches, installs, pushes, deployment or cleanup.

## Handoff Documentation Audit

This audit is the one exit check. Its handoff, described below, is the one record. Before every handoff, repeat the repository change checkpoint and check whether the documents affected by the observed work agree with the current product and task state. Use `docs/DOCUMENTS.md` to find applicable live PRD, architecture, design, deployment and activation sources; check their status, links, requirement IDs and acceptance criteria. Confirm that each meaningful change appears in the matching Epic Change Log and that the current task record names the actual result, verification and remaining work. For a managed run, compare `docs/goal/PLAN.md` and `RUN.md` with any `docs/tasks.md` view using the renderer's `--check`; RUN is authoritative and a direct task does not need a tasks view. Do not hand-edit the generated part of `docs/tasks.md` or rewrite archived records.

At the same handoff, compare this `AGENTS.md` with the **observed installed** `delivery-harness/assets/templates/PROJECT_AGENTS.template.md` and `delivery-harness/VERSION`. Check shared rules by meaning, not whole-file equality: repositories may add stricter local instructions. Mark the shared rules `current`, `stale` or `unknown` with the observed template identity and concrete differences. Under the current task's authorized document-write scope, update only stale shared instructions in place, preserving owner rules, local paths, bindings and historical decisions; never replace the file from the template. If the installed template is unobserved or a safe merge is unclear, leave the file intact and name the gap in the handoff.

The handoff names the repository, branch, HEAD and working-tree status, the template identity and drift decision, document/Epic/task findings, changes actually made, verification and the next owner/action. Reuse a semantic template audit within the same Epic or task after a complete prior audit. Its recorded SHA-256 values must prove that template, VERSION, bundle, effective instructions, owner references, scope and capabilities are unchanged. When they match, the audit survives summary compaction. A newly applicable, missing, or changed input invalidates reuse, as do restart and failed action/source guards. Preserve current, stale, and unknown labels and intentional exceptions; unknown loaded identity stays unknown. Never synthesize unknown loaded identity from installed bytes. A read-only handoff reports proposed updates without writing. A no-change audit needs no new Epic row. This is a task-boundary check, not a timer or permission to publish, approve, commit, push or delete.

## Source Completion

Update the affected skills, references, READMEs and Epic records under existing authority. Preserve untouched rules, IDs, decisions and historical evidence. Report the actual SHA, checks, independent review, release/installation state and unresolved obligations. Required failures, stale evidence or skipped checks prevent a complete delivery claim.

## Consumer Completion

Update affected live PRD, architecture, design and operational sources under existing authority. Preserve untouched pages, IDs, decisions and historical evidence. Report actual SHA/build, checks, independent review, release/installation state and unresolved obligations. Required failures, stale evidence or skipped checks prevent a complete delivery claim.
