# Design Brief And Reference Intake

Status: committed candidate included in the authorized 0.54.1 release; final verification, publication and installation pending.
Design workflow: enhancement
UI impact: none

## Scope And Accepted Outcome

The owner requested a Design Brief in the existing design flow and an explicit Ask User question about reference images, websites and products. The existing Visual Preference Brief and REF/RP records already own these decisions, but the reference question and a concise brief need clearer authoring guidance.

Extend UI Design Intake inside `docs/design/ui-design.md`; do not add a standalone brief, schema, approval gate or design author. Reuse the existing reference-principle confirmation, direction selection and Visual Approval. This changes skill guidance, not product UI or historical design approvals. This source repository has no product PRD or architecture package; canonical skill documents and the four READMEs are the implementation sources.

| Requirement | Acceptance |
| --- | --- |
| DB-1 | Ask once for unresolved references and desired/avoided aspects. Support images, screenshots, websites, Figma views and named products. Text-only questions collect text; attachments use normal conversation. |
| DB-2 | Accept no references and offer research/proposals. Preserve supplied answers and unchanged enhancement decisions. Missing or inaccessible material remains uninspected; silence is not approval. |
| DB-3 | Keep the concise brief in existing UI Design Intake. Link PRD purpose/audience/tasks, REF/RP evidence, visual constraints, avoid rules, Style Integration and MM records without duplicating their authority. |
| DB-4 | Preserve product/stack boundaries, reference confirmation and human design approvals. No new gate, mandatory historical backfill, validator or runtime. Update all four README descriptions. |

Sources: current `ui-design-builder` SKILL and intake/reference/output/pass guides; the owner's conversation instruction. External inspiration: [repo-harness design brief](https://github.com/Ancienttwo/repo-harness/blob/main/assets/templates/design-brief.template.md), inspected in the preceding research. The implementation adapts the idea to our existing records rather than copying a separate template.

## Baseline And Authority

Observed 2026-09-24 UTC: repository `C:/Users/mps19/Documents/GitHub/product-delivery-harness`, local main and locally observed origin/main at `b4ffe691b97265d5a76817c2e0ccf457e084fa54` (0.53.1). No remote freshness claim or fetch. The owner explicitly confirmed branch `codex/design-brief-references` and GLM workers. That branch was created from the observed origin/main SHA. No local commits, push, promotion, installation, worktree creation or cleanup is authorized by this task.

Original untracked `scripts/design/hifi_model.py` is observed/unverified, unrelated to this task and preserved. There were no staged or tracked working-tree changes at entry. The prior research observed the same baseline; this task does not re-verify historical release results.

Use one GLM Flash worker through the authorized `glm-workers` dispatcher in read-only mode to return a patch. The dispatcher requires a clean checkout for writable workers; the parent applies reviewed changes without moving the original untracked file. The parent owns README/Epic/index edits and final verification. Workers do not delegate or mutate Git. No PLAN/RUN is needed for this bounded direct change.

Write scope: `skills/ui-design-builder/SKILL.md`, its `ui-design-intake.md`, `design-reference-guide.md`, `output-contract.md` and `ui-design-pass.md` references; four READMEs; this Epic and the document index. No new artifact class or `.gitignore` rule is needed. Logs and worker outputs remain outside the checkout; existing ignores cover dependency and Python cache output.

## Verification And Change Log

- Entry: semantic review of the existing intake, REF/RP and direction records completed. Loaded skill identity remains unknown; document sync must not label installed bytes as the loaded identity.
- Working-tree implementation: GLM Flash run `20260923-235042-d7c84034c9f74eddb8c7d9a79d9fa5fd` completed read-only and returned a patch. The parent repaired its diff formatting, narrowed missing-input waits to dependent work, and applied the five scoped UI documents. Four README descriptions now match the flow. No schema, executable validator, runtime or historical design artifact changed.
- Before full verification, the nine changed skill/README files have fingerprint `9bc4512e0ea942016cdf5378d538ce7a9a654b7bb25c63fde8db26b39ba6e254`; full per-file hashes are in `C:/Users/mps19/AppData/Local/Temp/pdh-design-brief-a5bf243f3e2d4ac9b7e4e3e749e70b8b/source-before.json`. Epic/index edits are excluded to avoid recursive evidence updates. HEAD remains the baseline; this is working-tree evidence, not a committed candidate.
- Shared document sync reports `loaded_identity_unobserved` and `baseline_review_required`; installed digest is `dd610610baff6e3d607f61a9d5e7c40114a610d7ae17090958b8d813cc0f699f`. The named live scope was reviewed; no installed or loaded identity was relabeled or updated.
- Required dependency commands completed: pip requirements, `npm ci` and `npx playwright install chromium`. A task-local log-tail printer hit Windows console encoding after Chromium had exited 0; the printer was corrected to UTF-8. This was a reporting error, not a dependency-install failure, and no source repair or repeated installation was needed.
- Specification, pyflakes and docs-weight checks passed; normative documentation grows by 555 words against v0.53.1. Required-browser UI suite passed all 279 tests in 64.472 seconds with Chromium and no skips.
- A task-local compatibility check passed the legacy contract and four brief cases: supplied, explicitly none, unanswered and unavailable. Each still rejects a pending direction at Visual Approval. This verifies parser/gate compatibility, not actual user preference capture or visual quality. The parent also reviewed each intake path against DB-1 through DB-4.
- Required checks: skill specification, pyflakes, docs weight, all six unit suites, opt-in golden path, required Chromium browser checks, diff and ignore hygiene. No aesthetics or human approval claim follows from these checks.
- Commit/release version changes, publication and personal-skill installation remain separate from this local task.

## Final Local Result — 2026-09-24 UTC

Release continuation: the Design Brief change was committed on `codex/design-brief-references` as `b257304` (`feat(ui): add design brief reference intake`). The PRD continuation is `dee2d77`. Version 0.54.0 preparation is in progress; the original local verification below remains historical evidence for its tested source, and release-candidate verification, push, installation and promotion are tracked separately.

DB-1 through DB-4 are implemented in the scoped guidance and four README descriptions. The parent reviewed the complete diff. All 11 required verification jobs exited 0 from the repository root:

| Check | Result |
| --- | --- |
| Skill specification, pyflakes, docs weight, diff check | Passed |
| UI Design, required Chromium mode | 279 tests, all passed |
| Harness | 1,165 tests, OK with 16 skips; 1,378.500 seconds |
| Explicit golden path | 1 passed |
| Product Definition | 232 passed |
| Design System Compiler | 99 tests, OK with 3 skips |
| Product Activation | 56 passed |
| SEO Growth Review | 17 passed |

The skips cover Windows/POSIX or symlink-privilege limits and the default opt-in golden-path skip; golden path passed in its separate enabled run. Browser verification did not skip. Negative-test diagnostic lines are expected output, not suite failures. Linux CI, production UI quality and human design approval are not claimed.

Logs, the command manifest and result summaries are under `C:/Users/mps19/AppData/Local/Temp/pdh-design-brief-a5bf243f3e2d4ac9b7e4e3e749e70b8b/`; see `check-jobs.json.results.json`, each named `.log`, `brief_compatibility.py` and `final-identity.json`. The final nine-file source fingerprint matches the pre-verification fingerprint above. Only Epic/index bookkeeping changed after the suites.

Final repository/branch/HEAD remain the named checkout, `codex/design-brief-references` and `b4ffe691b97265d5a76817c2e0ccf457e084fa54`. No staged changes or commits exist. The original untracked `scripts/design/hifi_model.py` is unchanged, SHA-256 `66b61a803153d4da49e10ce3e25b72a51229728a84bc48371620012e21e38b9c`. Ignore checks confirmed `.env`, dependency output and Python caches are covered; source/README/Epic paths remain visible. No new ignore rule or tracked-file removal was needed.

The GLM worker and finite verification commands completed. No push, main promotion, version/tag change, personal-skill installation, branch/worktree removal or other cleanup occurred. This closes the authorized local change; the currently installed skill bundle is unchanged.

## 2026-09-24 Release Continuation

The earlier working-tree results above are historical observations, not current Git status. This change is committed as `b257304` and is included in `codex/runtime-resume-repair`, observed HEAD `6ae201453b518dd289cb0bde0dba7e2292f166aa`. The owner authorized reviewing and publishing the existing 0.54.0 preparation together with the runtime and frontend-authoring repairs as 0.54.1. Final exact-candidate evidence, promotion and installation are tracked in [the runtime reliability Epic](EPIC-runtime-and-verification-reliability.md). No release completion is claimed here.
