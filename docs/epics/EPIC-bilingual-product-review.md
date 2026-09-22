# English Product Sources And Chinese Review

Status: implemented and verified locally. UI impact: none; this changes skill authoring contracts, not a product UI.

The owner requested Chinese PRD and architecture content for review while software delivery references English. The accepted outcome is canonical English `PRD.md` and `architecture.md`, with complete synchronized `*.zh-TW.md` review copies, no separate approval authority, and stale-source checks before review and publication.

Baseline: branch `enhancement-readable-wireframes-token-coverage`, HEAD `6beb5e41f0007b35718f6dfe53f3eb23d147d40a`. The prior general-runtime-adapter work and unrelated untracked `scripts/` remain intact. No product PRD exists in this source repository; the output, lifecycle and approval contracts are the requirement references.

Scope: Product Definition skill, output/lifecycle/architecture/agent handoff references, read-only translation checker and tests, document manifest template, all four READMEs and this record. No commit, push, installation or release is authorized. Loaded skill identity remains unobserved; document-sync first observation and the intentional retired-skill cleanup pointers were semantically reviewed without inventing a loaded digest.

Acceptance: English remains the downstream reference; Chinese covers the same sections and IDs; owner feedback reaches both views; stale/missing/wrong-source translations fail; publication and archive retain pairs. Tests cover source changes with unchanged IDs, wrong/missing/duplicate bindings, ID drift, read-only behavior and both required CLI companions. Run repository-required checks from the root.

Gitignore: sources, review artifacts and Epic records stay tracked. Test artifacts and logs stay outside the checkout; existing Python cache rules suffice.

## Change Log

| Observation / request | Scope and evidence | Verification / remaining work |
| --- | --- | --- |
| 2026-09-22 05:44 UTC; owner requested Chinese review with English implementation references | Working-tree changes on the baseline branch/HEAD above. Product Definition tree plus document-manifest template scoped diff SHA-256: `a40f59139278c41a730c4e02f0cd38151ce89a25e428ed45284597d02b127e38` | 224 Product Definition tests passed, including stale-source, trace and CLI cases. Full repository checks pending. |

The fingerprint is a cumulative scoped diff against HEAD, including preserved runtime work; it is not an authorship claim or commit identity. Checkpoint details remain in `%TEMP%/bilingual-epic-evidence-c0v1n8gp/checkpoint.json`. The packet module remains one input-validation and handoff responsibility at its 500-line checkpoint; a new module split would not improve this change's ownership.

Result: complete for the authorized local source scope. English remains canonical; the paired Chinese review, feedback, approval and publication rules are wired through the skill and references. The checker is read-only and does not claim semantic translation accuracy. No existing product package or archived approval was rewritten.

Final verification: Delivery Harness 1,150 tests (16 skipped), Product Definition 224, UI Design 212, Design System 99 (3 skipped), Activation 56, SEO 16, and opt-in golden path 1; all suites passed. Dependencies, spec, pyflakes, document weight and both diff checks passed. Skips follow suite conditions on this Windows host. Logs: `%TEMP%/bilingual-epic-full-ffkmqtii/`. Both scoped fingerprints remained unchanged at the final checkpoint, retained in `%TEMP%/bilingual-epic-evidence-c0v1n8gp/final-checkpoint.json`. No commit, push, installation into the user's skills directory or release was performed.

## English-only Backfill And Release Follow-up

The owner also requested automatic same-directory Chinese translations for existing English-only PRDs and explicitly authorized commit, push and merge of this task. This supersedes the earlier local-only authorization above. The same backfill applies to existing architecture sources; English bytes and approvals remain unchanged. PRD-only validation is supported; existing translations and archives are preserved. No current product PRD exists in this source repository.

Release target: 0.51.0. Observed remote main: `63d9f071001eef1375a9e7d80d21bf0ffd896929`. Its tree equals the current branch baseline; the earlier wireframe work is already released by PR #117. Preserve unrelated untracked `scripts/`. Final candidate and exact-main verification are pending and will be recorded in release evidence outside the candidate. No cleanup of branches or worktrees is authorized.
