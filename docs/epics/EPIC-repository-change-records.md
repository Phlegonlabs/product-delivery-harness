# Repository Changes Recorded Without A Full Harness Run

Status: implemented and verified locally. UI impact: none.

The owner requested `AGENTS.md` rules that keep Epic records current even when a project does not run the full Product Delivery Harness. The owner selected checks at task start, significant change boundaries and task completion, rather than a timed background job.

Baseline: branch `enhancement-readable-wireframes-token-coverage`, HEAD `6beb5e41f0007b35718f6dfe53f3eb23d147d40a`; existing runtime changes, bilingual-review work and unrelated untracked `scripts/` are preserved. This repository's governance and Epic contract are the requirement sources; there is no product PRD.

Scope: root and seeded `AGENTS.md`, shared Epic/document-sync guidance, Epic template, documentation and contract tests. Inspect committed and uncommitted changes, retain exact observed evidence, append logical changes to the matching Epic and update `docs/DOCUMENTS.md`. Unknown external changes remain observed/unverified; detection grants no approval or implementation authority. Read-only tasks report the proposed record without writing it.

Acceptance: the rules work without PLAN/RUN or installed Harness tooling, use bounded local Git observations and an explicit prior baseline, preserve historical records and unrelated work, avoid duplicate/no-change logs, and detect branch changes or unavailable history without fabricating a delta. No background service, commit, push, installation or cleanup is authorized.

Gitignore: no generated cache, service or new local state file. Epic and document index remain tracked; verification logs stay outside the checkout.

## Change Log

| Observation / request | Scope and evidence | Verification / remaining work |
| --- | --- | --- |
| 2026-09-22 05:44 UTC; owner chose task-start, significant-change and task-end checks | Working-tree changes on the baseline branch/HEAD above. Root/seeded AGENTS, Epic template, bounded/document-sync rules and entry tests scoped diff SHA-256: `0c9860e88385283549f9fc9a607cf5890f9788e413be41e7df199af4b2719d04` | Six enhancement-entry tests, 60 skill-contract tests and all four README structure checks passed. Full repository checks pending. |

The fingerprint is a cumulative scoped diff against HEAD, including preserved runtime work; it does not attribute unrelated changes to this task. Checkpoint details remain in `%TEMP%/bilingual-epic-evidence-c0v1n8gp/checkpoint.json`. The prior untracked `scripts/` remains observed and untouched. No background schedule was created.

Result: complete for the authorized local source scope. Root and seeded AGENTS contain matching standalone task checkpoints. The rules cover external commits and uncommitted changes, preserve baseline gaps and actual verification, update the matching Epic/index, avoid duplicate entries and respect read-only tasks. No scheduler, background watcher, extra state database or new action grant was introduced.

Final verification: Delivery Harness 1,150 tests (16 skipped), Product Definition 224, UI Design 212, Design System 99 (3 skipped), Activation 56, SEO 16, and opt-in golden path 1; all suites passed. Dependencies, spec, pyflakes, document weight and both diff checks passed. Skips follow suite conditions on this Windows host. Logs: `%TEMP%/bilingual-epic-full-ffkmqtii/`. Both scoped fingerprints remained unchanged at the final checkpoint, retained in `%TEMP%/bilingual-epic-evidence-c0v1n8gp/final-checkpoint.json`. No commit, push, installation into the user's skills directory or release was performed.
