# Remove The Wireframe Stage

Status: complete
Committed as `511a7a5b`, integrated with review follow-ups and macOS support, then landed on `main` in the 0.56 release line.
Design workflow: enhancement
UI impact: none (skill contracts and validators; no product UI authored).

## Accepted Outcome

The owner approved removing grayscale Wireframe authoring and W1-W5 from new design packages and authorized multi-agent implementation on `codex/remove-wireframe-stage`. PRD remains the only per-page product contract. Direction prompts read its UI Surface Contract directly; Design Brief page-purpose mapping records design constraints and freedom without duplicating requirements. New visual scope defaults to three comparable directions, explicit owner direction may use one, and unchanged enhancements retain their selected direction.

Retain legacy Wireframe tools and historical approvals for their original versions. New contracts explicitly select the wireframe-free path. Missing files never select a weaker validation path. Preserve sourced copy, operations, routes, states, responsive coverage, motion, bilingual review, recipes and native projection requirements through direct PRD-to-HiFi checks. Full approved HiFi packages replace Wireframe as frozen design input to Harness and the compiler.

This follows [Wireframe Handoff Refinement](EPIC-wireframe-handoff-refinement.md), [Design Authoring Flow](EPIC-design-authoring-flow.md), and [Motion And Media Quality](EPIC-motion-media-quality.md); their results remain historical.

## Baseline And Authority

- Observed 2026-09-28: fetched remote `main` at `2fa9b343175f585aca1da551edc0a8654380de9b`, source version 0.55.0. Created the exact owner-authorized branch `codex/remove-wireframe-stage` from that head.
- Prior branch `codex/macos-support` remains at `daac7206777cfedb0851f17f2fee29858d3abfce`; its unrelated, unmerged work is not imported. Entry working tree was clean.
- Installed bundle is 0.55.1; actually loaded digest is unobserved. This task edits canonical source and does not upgrade installed skills.
- Authority: local implementation, named branch creation/switch, multi-agent work and the proposed read-only Claude Bridge review. No commit, push, promotion, release, install, archive or deletion is authorized.
- Direct source maintenance, parent-owned integration and one final verification sequence. No consumer product PRD, design approvals or managed PLAN/RUN is created. Agents have explicit non-overlapping ownership; the parent owns this Epic/index and final acceptance.

## Requirements And Checks

| ID | Acceptance |
| --- | --- |
| RW-1 | Explicit new contract removes Wireframe artifacts, headings and usage rows; legacy contracts retain their original checks. |
| RW-2 | Product package preflight checks PRD copy, operations, states and responsive inputs before HiFi. Prompt references PRD directly. |
| RW-3 | Cheap HiFi coverage/copy/control checks precede Impeccable; missing pages, text, states, targets and wrong destinations fail. |
| RW-4 | Harness freezes complete approved HiFi input and validates PRD/PLAN/HiFi joins and byte identity; missing or stale siblings fail. |
| RW-5 | Compiler binds approved HiFi instead of Wireframe for new pairs, preserving historical schemas. |
| RW-6 | Design freedom, three-direction default, motion, bilingual copy, useful recipes and platform projections survive in direction/HiFi guidance. |
| RW-7 | All affected canonical skills, templates, four README descriptions, tests and release surfaces agree on 0.56.0. |

Verification: focused positive/negative regressions and legacy cases, skill specification, pyflakes, documentation weight, all repository-required suites, explicit golden path, required Chromium tests, diff/ignore checks, parent diff inspection and independent read-only review. Working-tree results are not exact-commit release evidence. Repair budget: at most two rounds per root-cause family; retain failures and unresolved gaps.

Write scope: affected seven-skill canonical sources and tests, root AGENTS shared design rules, package/version surfaces, four READMEs, this Epic and DOCUMENTS index. No new artifact class is expected; task logs and review packets remain outside the checkout. Existing dependency/cache ignore rules remain applicable.

## Change Log

- 2026-09-28: first baseline recorded and new branch created. Read-only architecture and UI/downstream dependency exploration dispatched. Implementation and verification pending.
- 2026-09-28 working-tree: implemented explicit `ui-design/2`, direct Product/HiFi operations and typed-copy joins, pre-Impeccable completeness flag, versioned Harness source inventory and `design-system/3`. Updated design prompt, affected references/templates, four README descriptions and 0.56.0 release fields. Legacy validators and approvals remain version-bound. Four implementation agents stopped after provider 429 retry exhaustion; parent integrated their partial files and completed the remaining edits. No alternate provider was used to bypass quota.
- 2026-09-28 verification in progress: new direct-join, publication-without-wireframe, Harness and compiler integration regressions pass. UI suite passed 303 tests with required browser configuration; Activation passed 56 and SEO passed 21. Static checks and documentation-weight checks passed. Earlier runs exposed an exception in a replacement-contract diagnostic, an incorrect version comparison, stale wireframe evidence resolution and obsolete documentation assertions; repairs are included. Full Harness, final Product/compiler checks and independent review remain pending. Synthetic fixture receipts are consistency tests, never product approval or browser observations.
- Module responsibility checkpoint: existing large validators remain integration entrypoints to preserve their public APIs and legacy tests. The new PRD operation parser and HiFi copy/product join live in separate focused modules; no general compatibility framework was added. Logs, dependency-install results and review packet are outside the checkout under `C:/Users/mps19/AppData/Local/Temp/pdh-remove-wireframe-ok1w22ng/`. No new ignore class was introduced.
- 2026-09-28 10:05 UTC working-tree: independent read-only Claude Opus 5.5 review and bounded re-review completed. The five findings were repaired: schema-3 compiler comparison dispatch, PLAN-only current-contract dispatch, Product enhancement refresh vocabulary, legacy Approved-target hash validation, and document-sync impact hints. Re-review confirmed those repairs; its claimed sibling-revision gap was retracted because pre-existing validation and tests cover it. Remaining Product reference wording was updated to HiFi and its documentation tests passed. Review logs: `C:/Users/mps19/.codex/bridges/claude-code/runs/20260928-023205-5b6a4b5d/result.json` and `C:/Users/mps19/.codex/bridges/claude-code/runs/20260928-024910-e74e4fc1/result.json`.
- 2026-09-28 10:05 UTC verification checkpoint: Product 240, UI 304 with required Chromium, compiler 117 (4 skipped), Activation 56 and SEO 21 passed. Current frozen-source joins 4, strict authority 19, PLAN/RUN plus PLAN-only golden path 1, current full lifecycle 1, cross-skill smoke 15, Harness documentation contract 60, and document-sync 26 (1 skipped) passed. Full Harness and installer regression are still running. The first Harness run found stale documentation and lifecycle fixtures and installers rejecting untracked source; focused reruns repair these without weakening checks. New source paths have intent-to-add entries so installer tests can inspect the complete candidate; no file content is staged and no commit was created.
- Handoff audit in progress: repository/branch/HEAD remain the recorded baseline; changes are local. The source repository has no consumer PRD/architecture or managed PLAN/RUN, so no translation backfill or generated task view applies. Four README descriptions and release fields agree on the unreleased 0.56.0 candidate. Installed template remains 0.55.1, SHA-256 `a0ac8489c0dec2452398b86dcce64c2416bccdd9daec9f81fa157da56d76b4e4`; shared rules are current by meaning with the authorized candidate design-flow replacement and preserved source-repository exceptions. Installed Wireframe wording is older than this candidate, not a reason to revert the accepted change. Loaded skill identity remains unknown. Existing ignore rules cover dependencies and Python caches; source, lockfile and templates remain tracked.
- 2026-09-28 10:35 UTC final working-tree checkpoint: all four frozen-source Harness shards exited 0. Their inventories contain exactly the same 1,325 discovered test IDs, assigned once across 332/331/331/331 cases with no omission or overlap. `HARNESS_GOLDEN_PATH=1` was enabled and the real CLI golden path plus current Product-to-Harness-to-Activation-to-SEO lifecycle passed. Fifteen Harness cases skipped for POSIX-only behavior or unavailable file-symlink privileges. The complete first sequential run remains recorded as failed (1,324 cases, 14 failures and 3 errors); stale fixtures and untracked/moving source caused the repaired failures. Its runtime single-flight failure was `started.wait(5)` timing out; the unchanged runtime group passed 45 cases (2 platform skips), and the final full sharded rerun also passed. No assertion or safety gate was weakened to hide that failure.
- Final candidate identity: `C:/Users/mps19/AppData/Local/Temp/pdh-remove-wireframe-ok1w22ng/candidate-20260928T100532Z.json` records SHA-256 for all 69 changed source/test/README/version/governance files, excluding this Epic and its index. Inventory SHA-256 is `a7784ba052a11bad256ed82aba702f1b45192acdd5109e774911169ef992fcab`. Every file still matched after the full rerun. Final logs are `harness-frozen-shard-{0,1,2,3}-20260928T1016*.log` with matching result files and four `harness-shard-*-inventory.json` files in that external evidence directory. All tracked verification wrappers completed, the review processes exited, and no task-owned test process remains.

## Final Verification And Handoff

| Check | Result |
| --- | --- |
| Harness full discovery, four disjoint shards | 1,325 cases; success, 15 platform/privilege skips; golden path enabled |
| Product Definition full suite | 240 cases; success |
| UI Design full suite | 304 cases; success with required Chromium configuration |
| Design System Compiler full suite | 117 cases; success, 4 POSIX/file-symlink skips |
| Activation / SEO full suites | 56 / 21 cases; success |
| Skill specification, pyflakes, documentation weight | Success |
| Diff whitespace and ignore hygiene | Success; existing dependency/cache rules suffice |
| Independent review | Five findings repaired and confirmed by Claude Opus 5.5 read-only re-review; remaining wording fixed and tested |

RW-1 through RW-7 are implemented and covered by the checks above. The reusable design prompt is in `skills/ui-design-builder/references/ui-design-pass.md#direction-authoring-prompt`. Historical Wireframe checks remain available; new packages explicitly use the PRD-to-HiFi path.

Final repository: `C:/Users/mps19/Documents/GitHub/product-delivery-harness`, branch `codex/remove-wireframe-stage`, HEAD `2fa9b343175f585aca1da551edc0a8654380de9b`. The changes remain in the working tree, with intent-to-add for new source files and no staged file content. The source/index/task audit agrees with this result. Installed template identity and its authorized source-flow difference are recorded above; installed skills remain 0.55.1.

This is a local implementation handoff, not release completion. Commits, publication, CI on other platforms, exact-SHA main promotion, tagging and installation have not occurred. Those release actions require their existing separate authorizations; platform-limited tests still need an appropriate CI host.

## Integration

- 2026-09-28: the owner asked to commit, push and merge this branch with #129 and #130. Committed as `511a7a5b`, pushed, and merged into `codex/release-0.56.0` (merge `32bb7de1`). Conflicts in 24 files were resolved keeping both sides: `ui-design/2` contracts use this Epic's direct PRD-to-HiFi path; legacy contracts keep the review-fix current-HiFi cutover and its 0.55.1 join gate. One 0.56.0 release carries all three branches.
