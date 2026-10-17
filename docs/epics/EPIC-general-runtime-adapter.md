# General Runtime Adapter

Status: complete
Route: direct, one writer and one coherent verification sequence. UI impact: none.

Problem: one nominal adapter still routes by host name, pins model defaults and carries native launch templates and compatibility state.

Baseline: current branch enhancement-readable-wireframes-token-coverage at 6beb5e4; no tracked local changes before this task. The unrelated untracked scripts/ directory is preserved. This repository has no product PRD; canonical skills and the four READMEs own the contract.

Accepted outcome: one capability-based contract for every host. The agent maps observed native tools automatically. Preserve explicit provider eligibility, authorization, fresh context, isolated writes, exact-head review and parent-owned PLAN/RUN. Remove provider-specific defaults, native workflow templates and their compatibility path, as explicitly requested by the owner. Historical user RUN files remain untouched and require replanning before using removed runtime bindings.

Write scope: affected canonical skill code, references, templates and tests; four README descriptive sections; this Epic and DOCUMENTS; the obsolete root CLAUDE adapter pointer. No commit, branch/worktree creation, push, installation, release or cleanup authorization is inferred.

Dependencies: loaded installed-skill identity is unobserved; disk bytes are not a loaded identity. Document-sync first observation requires semantic review. Existing unfinished UI Epics are unrelated and retained.

Gitignore: no new generated artifact class. Pure packet-builder source and tests stay tracked; temporary verification logs stay outside the checkout. Existing Python cache rules apply.

Acceptance: unknown and named hosts use the same routing/options/probe rules; removed driver/state/templates are rejected or absent; missing evidence or authorization cannot dispatch; PRD product-input gates remain covered without a native runner. Run the full repository-required spec, lint, document-weight, unit and golden-path checks from the root. No live multi-host capability or exact-commit security PASS is claimed.

Result: provider-specific routing, model defaults and browser-surface catalogs are removed. The agent selects observed native capabilities through one contract. The three native workflow templates and workflow-run compatibility validator are removed; the PRD input gates and role packets now live in the pure `product_agent_graph.cjs` module. The four READMEs, skill entrypoints, context pointers and references describe the same behavior. Authorization, isolation, exact-SHA evidence and parent ownership remain enforced.

Verification on 2026-09-21, from the repository root:

| Check | Result |
| --- | --- |
| Dependency install, skill spec, pyflakes, document weight | PASS |
| Delivery Harness | 1,149 tests; OK, 16 skipped |
| Product Definition Builder | 217 tests; OK |
| UI Design Builder | 212 tests; OK |
| Design System Compiler | 99 tests; OK, 3 skipped |
| Product Activation | 56 tests; OK |
| SEO Growth Review | 16 tests; OK |
| Opt-in golden path | 1 test; OK |
| Working-tree and staged diff checks | PASS |
| Ignore rules and source inventory | PASS; no new ignore rule needed |

The skipped tests follow their environment or opt-in conditions on this Windows host; the golden path was run separately with its required flag. Capability fixtures cover generic, Codex, Claude, Pi, ZCode and an unknown host identity. This is contract coverage, not a live test of each host.

Final logs are outside the checkout under `%TEMP%/general-runtime-verified-vkaur62d/`, with the final Product Definition rerun under `%TEMP%/general-runtime-product-final-40xkiw8i/` and final static checks under `%TEMP%/general-runtime-final-static-p03z8se8/`. Earlier failures were corrected and the complete Harness suite was rerun successfully with stable source files. Document-sync loaded identity remains unobserved; no baseline or installed identity was fabricated. No commit, push, installation into the user's skills directory, or release was performed.

## 2026-09-23 reliability follow-up

Local main and local tag `v0.52.0` were observed at `baf7e22b05a7f2776ee8b205395204ff21cbdcb5`. This is a current local repository observation, not a rerun of the historical release checks above. The 0.53.0 browser, cross-skill, runtime and translation follow-up is tracked in [EPIC-runtime-and-verification-reliability.md](EPIC-runtime-and-verification-reliability.md); preserve the earlier results and remaining coverage distinctions.

## 2026-09-27 runtime-contract adoption repair

Working-tree record on branch `codex/runtime-contract-adoption` from `f8d52d987c1437ecbb8704fc2a20adbe5e24873a`. The owner authorized filling the Codex lazy-skill identity gap without falsely labeling installed bytes as loaded at session start.

The change adds RUN-v11-only `version_gate.status = "adopted"` with a session-bound `contract_adoption` receipt and immutable replacement history. `loaded_contract_digest` remains null; `installed_contract_digest` and the receipt must match. The guarded `adopt-runtime-contract` transition requires the RUN lock, a quiescent graph, an owner source, reading evidence, the expected digest of the reviewed bytes, a fresh installed-digest match, and an executing Harness `VERSION` at or above the RUN pin. Draft runs may record this metadata observation; complete and cancelled runs cannot. Later selections recompute the live seven-skill digest once when runtime-worker dispatch is possible and defer on drift. Worker directives and review packets carry the receipt so a fresh child independently recomputes, reads, and reports the fixed contract. Existing `current`, mismatch/restart, capability, authorization, source, action and review gates retain their prior meaning.

Owner source and reading evidence are recorded attestations, not cryptographic proof of model ingestion. The digest checks prove only the bytes observed at their measurement points.

Focused verification on 2026-09-27 passed eight tests: RUN-v11 schema separation, RUN-v10 rejection, one live hash per selection, drift deferral, documented deferral codes, guarded adoption/history/fresh-session behavior, expected-digest and active-work no-mutation, and reviewer-packet propagation. Evidence: `%TEMP%/pdh-identity-focus2-6aaeebeb28c84cbc9e6c9964efe3a2cc.log` and `C:/Users/mps19/Documents/Codex/2026-09-27/overbet-harness-takeover/work/identity-v10-rejection-20260927T140007Z.log`. Bounded static checks passed for skill specification, delivery-script pyflakes and docs weight under `identity-skill-spec-20260927T140019Z.log`, `identity-pyflakes-20260927T140019Z.log`, and `identity-docs-weight-20260927T140019Z.log` in the same work directory. Full repository regression, independent review, exact-commit handling, installation and release remain pending; none is claimed here.

## 2026-09-27 coordination checkpoint repair

Working-tree follow-up on `codex/runtime-contract-adoption` from committed `7f06ab385c505c7eb175729b7b52e1a42d7080c5`. The first adoption repair had passed focused/static checks, five sibling suites, the golden path, and independent GLM security review; the parent then cancelled the remaining full Harness regression when this separate integration checkpoint gap was confirmed. That cancellation is not a test result and is not reused as coverage for this change.

The documented commit convention requires a separate bookkeeping commit after integration or wave close, but `accept-wave` refused the resulting live head and `record-integration`/`reconcile-candidate-head` did not describe this healthy checkpoint path. The bounded fix adds `reconcile-coordination-head`: a lock-holding, source-named, Git-read-only transition that binds one ordinary direct child `B` of recorded integration head `I` after a fresh observation. It proves repository/branch/live-plus-observed head, live PLAN revision/digest, forward and batch ancestry, clean product tree, regular unchanged Git entry modes, and an exact supported coordination path set. Supported exact paths cover `PLAN.md`, `RUN.md`, `DECISIONS.md`, and `REFINEMENT_BACKLOG.md` directly under `docs/goal/` or in one bounded run namespace, historical and matching generated `tasks.md`, `docs/DOCUMENTS.md`, and one exact Epic checkpoint; arbitrary application/package paths, frozen product/design sources, globs, deletions, product edits, hidden intermediate commits, drift, stale PLAN state, replay, and foreign/missing locks are rejected. Old integration head and evidence history remain immutable; current integration-review/final-gate projections re-arm under their existing budgets and authorizations are unchanged. Isolated in-flight mission workers and preintegration reviewers may continue, while live integration reviewers and parent-owned running checks must be quiescent.

Focused real-Git verification passed the preexisting close/next-wave regression and a close/integration checkpoint → committed all-nested `docs/goal/pdr12/PLAN.md`, `RUN.md`, `DECISIONS.md`, and generated `tasks.md` plus historical `docs/tasks.md` → fresh observation → coordination reconciliation → next-wave sequence, including missing-lock, stale-head, dirty-product, and replay no-mutation guards. Nine focused guard cases passed: isolated writer allowed, isolated preintegration reviewer allowed, old PASS projection invalidated while history remains, product edit rejected, hidden intermediate commit rejected, frozen source rejected, arbitrary application source rejected, non-regular Git entry rejected, observed-head drift rejected, and live integration reviewer/parent node rejected. Evidence is under `C:/Users/mps19/Documents/Codex/2026-09-27/overbet-harness-takeover/work/` in `coordination-existing-nextwave-20260927T145002Z.log`, `coordination-nested-final-20260927T145313Z.log`, and `coordination-guards-nested-final2-20260927T145413Z.log`. Skill specification, delivery-script pyflakes and docs-weight checks passed under `nested-checkpoint-skill-spec-20260927T145459Z.log`, `nested-checkpoint-pyflakes-20260927T145459Z.log`, and `nested-checkpoint-docs-weight-20260927T145459Z.log` in the same directory. Full repository regression, independent review, commit, installation, publication and release remain pending.

## 2026-09-27 review repair: checkpoint expectation

Independent unified review of committed candidate `319d713773609dbef8eca0823240e68fa9bc3fe1` found one issue: `test_projection_uses_exact_checkpoints_and_declared_path` omitted the intentional `reconcile-coordination-head` member of `TASK_VIEW_CHECKPOINTS`, so the focused expectation and the 15-test transition file failed. The repair adds that command to the expected set and changes no implementation. Review evidence belongs to the parent-run unified review. Bounded repair verification passed the focused expectation under `C:/Users/mps19/Documents/Codex/2026-09-27/overbet-harness-takeover/work/review-repair-focused-20260927T151117Z.log` and the complete transition module under `review-repair-transition-module-20260927T151145Z.log`: 15 tests, OK, one pre-existing Windows symlink-privilege skip.

## 2026-09-27 source instruction handoff sync

Parent observation at `codex/runtime-contract-adoption` / `c56a7295f7352f7b97d0eff3a56155133bf1b78e`: the review identified absent Runtime Boundary and managed-run entry guidance in source AGENTS.md. This working-tree documentation patch adds those shared meanings using this repository's canonical `skills/` paths and preserves its stricter verification, installation and Git rules. The observed template is version 0.54.5, SHA-256 `1677220abf249a21b7b3967aada7b8a7339f0d614a85958132ea938b908c78e7`. These audited shared rules are now current by meaning. Consumer Skill Bindings are not applicable to this direct source-maintenance task: no consumer PRD or managed PLAN/RUN exists here. The added entry rule requires resolving them at the applicable stage if managed work begins, without inventing pins or importing a product template wholesale. Manual comparison and `git diff --check` passed; no runtime behavior or action grant changed. Existing README routing and adapter descriptions remain accurate. Candidate review, full regression and installation remain separate pending steps.
