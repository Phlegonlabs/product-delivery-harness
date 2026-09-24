# Shared Invocation Document Check

At the first work in a new session and at every skill invocation, use this entry check. It is read-only by default and does not launch another skill, probe another host, install software, fetch a public latest version, or grant permission. A public-only SEO review with no repository records the repository portion as not applicable.

## Inventory And Observe

1. Resolve the effective instruction chain for the host and selected scope. Include existing AGENTS.md, AGENTS.override.md, CLAUDE.md where applicable, docs/DOCUMENTS.md, current PRD/architecture/stack, applicable design and operational sources, and the prior active PLAN/RUN when present. Inspect names first; never open credential files. Missing expected documents are gaps; absent non-applicable documents do not require placeholder creation.
2. Use the existing `harness_contract.py` digest for the seven-skill bundle. Compare the digest actually loaded at session start with the currently installed bytes; never fill an unknown loaded digest with the current disk hash. Unknown loaded identity needs observation, and a mismatch follows `runtime-upgrades.md`'s restart boundary. Capability still needs the existing stage-specific probe; identical hashes are not a capability check.
3. Run `check_document_sync.py` on the explicitly scoped Markdown paths. The defaults cover root instructions, common live flow documents and direct Markdown children of `docs/epics/` (no recursive history scan); removed inventoried Epics remain visible as missing. Inspect the relevant unfinished Epic and its referenced work. add applicable nested instructions and manifest-listed Markdown with repeated `--path`. Supplying paths replaces the defaults, so pass the whole applicable inventory. Add `--required-path` for every document required by the selected stage. Binary wireframes/compiled registries use their existing owners' validators and frozen hashes, not this Markdown inventory.
4. Read unchanged required sources under their skill's normal reading rules. For changed documents, changed skill contracts, retired pointers, inventory changes or a first observation, review the semantic delta and affected stages. Prior task records and runtime observations are recovery context, never fresh approval or proof of process liveness. Historical snapshots remain readable reference outside the live inventory.

### Same-session source reading reuse

When another skill invocation needs a source already read in this session, reuse that reading only when the current file bytes still match the recorded SHA-256, the full prior content remains available in this session, and the prior read covered the same applicable rule and stage. Read changed, missing, newly referenced or newly applicable sources, and any sections not covered by the earlier read. Re-run this document inventory for each invocation; reusing unchanged source text does not reuse a drift result, complete semantic review, or grant approval. Do not persist a separate reading cache or approval record. If a session restart or compaction leaves only a summary instead of the source content, read the source again.

```text
python "<delivery-harness-skill-root>/scripts/check_document_sync.py" --repo-root <project-root> --loaded-digest <observed-session-contract-sha256> --baseline docs/document-sync.json
```

Omit `--baseline` on first use. `--skills-root` names the observed installed sibling directory when not using this bundle's location. The CLI recomputes the installed digest; optional `--installed-digest` is an expected-value assertion, not an override. Run from the target root. Exit 0 means the inventoried bytes are unchanged; exit 1 means review is needed; exit 2 means invalid input. None means an approval or delivery PASS. Output is JSON with findings and a `snapshot` object; it never writes files, executes document commands or follows links.

## Reconcile Under Existing Authority

When the host cannot observe the loaded digest, omit `--loaded-digest`; the report remains `review_required` with `loaded_identity_unobserved`. Do not invent one from disk. Snapshot paths and hashes are checkout-relative, so the tracked snapshot works in another clone or worktree of the same project. The parent verifies that the baseline belongs to this project's history; a snapshot is not a repository identity credential. Explicitly scoped root or component Markdown, such as `SECURITY.md`, is allowed; credential and historical exclusions still apply.

Retired-name findings have a narrow quiet exception. Bare names in an explicit retirement prose catalog are quiet, such as a note saying a release retires `full-harness`, `prd-builder`, and `product-design-builder`. Actual paths, commands, links, and uses inside fenced code still surface. Other standalone legacy names also surface. Unknown loaded identity is a separate finding and is never quieted by the catalog.

Use `bounded-enhancement.md`. For authorized same-scope pointer, command or factual document corrections, patch only the affected live text and preserve local rules, owner decisions and unrelated changes. Bootstrap templates create missing files only. A changed external skill pin needs inspection of the new skill tree and side effects before adopting it; never simply replace the hash to silence drift.

When current English PRD/architecture sources lack Chinese review copies, apply `../../product-definition-builder/references/bilingual-review.md` under existing document-write authority. Backfill complete same-directory copies without changing English bytes or approvals; a read-only invocation reports missing copies without writing. This does not require a full Harness run.

Route actual product/UI/stack decision changes to their owner as next-round gaps instead of repeatedly asking mid-delivery or rewriting approved history. Finish independent work. Never silently migrate an active RUN, rewrite a closed RUN, modify an archived PRD/approval, erase old failures or present historical evidence as current.

For new product-relevant findings, use `../../product-definition-builder/references/prd-refinement.md` at the applicable existing stage checkpoint. Reconcile changed evidence into the same PRD through its owning flow; record unresolved proposals in the existing change record, not a competing specification. This is a targeted delta review, not a repeated whole-project interview.

After the semantic review and any authorized correction, the parent may retain only the emitted `snapshot` object at the project-declared path (default `docs/document-sync.json`) under the existing document-write authority. Keep review findings and dispositions in the existing task report/RUN evidence, not a new approval database. Saving a snapshot is not a decision grant. If saving is not authorized, keep the inline report; the next invocation repeats the review rather than pretending it was persisted.

The snapshot is a tracked non-secret inventory, not a cache to hide in .gitignore. Never include values, cookies, tokens or browser storage. Do not include the snapshot itself in its inventory. The CLI excludes historical/credential paths and rejects links, traversal, malformed JSON and oversized files. It cannot prove a document's instructions are correct, that the caller really observed a loaded digest, or that an external action occurred; the parent must verify those facts separately.

## UI Artifact Impact

For design consumers, continue with `../../ui-design-builder/references/design-freshness.md` after the Markdown check. Wireframe/HiFi bytes, upstream identity and applicable skill-rule changes need separate inspection even when Markdown is unchanged. No snapshot update proves freshness or grants a redesign. Record the short affected/retained/recheck list in existing task evidence.

## Impact Review

Markdown byte inventory does not replace the project's **Repository Change Checkpoints**. At task start, significant changes and completion/handoff, also inspect local Git history and working-tree changes, including changes made without Harness. Record relevant code/configuration/product changes in the matching Epic and update `docs/DOCUMENTS.md` under existing write authority. No installed skill or sync snapshot is required for that standalone AGENTS rule. Preserve unverified external changes, missing baselines and read-only restrictions explicitly; never convert an observation into approval or test evidence.

At handoff, apply the project's Handoff Documentation Audit as well. Reconcile applicable live sources, the Epic and index, and the direct task record or PLAN/RUN with any generated `docs/tasks.md` view. Compare the target `AGENTS.md` shared rules to the observed installed `PROJECT_AGENTS.template.md` and version; a document-sync snapshot or matching byte hash alone cannot prove the rules are current. Refresh only stale shared instructions under existing document-write authority, preserving repository-specific text and immutable records. If the template or safe merge cannot be observed, report the gap rather than replacing the target file. This is a handoff checkpoint, not a scheduled scan.

The read-only report includes `impacts`: source path, observation reason, affected artifacts/stages, required checks and `semantic_review_required`. Present first-observation sources and changed or required/missing sources need review; unchanged bytes have no source impact rows. Unknown source types route to parent semantic review. These are conservative routing hints: inspect actual requirement references and the diff before selecting checks. Skill identity changes still require the separate restart/contract findings even when all document bytes match.

Keep this report in existing task or RUN evidence. The `document-sync/1` snapshot stays unchanged; do not store impact hints as a second editable specification or use them as approval.
