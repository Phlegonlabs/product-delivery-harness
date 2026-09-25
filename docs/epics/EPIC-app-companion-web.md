# App And Companion Web Product Definition

Status: implemented locally; product/UI validation passed. Broader Harness verification is not green.

## Problem And Baseline

The owner cited React Native + Expo as a reference and wants PRD work to cover an app and a public showcase website together. Existing hybrid schemas support separate platforms, but discovery and authoring guidance did not make this common combination explicit.

Repository `product-delivery-harness`, branch `codex/wireframe-four-widths`, HEAD `077cd3471d267d2c2f093c8d06f3f76a293ed1e1`. The four-width template work and earlier documentation/untracked scripts remain in the working tree. This is a new accepted documentation outcome; no new branch, commit, push, installation or product artifact is requested.

## Accepted Scope And Acceptance

- One PRD covers explicitly included iOS, Android and showcase Web surfaces; authenticated Web/admin scope remains explicit.
- React Native + Expo is only a reference option, not a required or default stack. Select technology from product requirements, preserve existing accepted stacks, and keep unresolved layers at their existing approval checkpoint.
- Use existing surface bindings, responsive sets, TEST rows and release targets. Native review sizes and per-platform behavior remain distinct from four-width Web review.
- Document shared-code/API boundaries, cross-surface journeys, native/browser verification and separate release paths. No new schema, gate or product approval is introduced.
- UI impact: none to the reviewer runtime in this follow-up; authoring guidance covers future multi-platform structure. Earlier template edits remain separately recorded.

## Document Impact

Canonical Product Definition entry, interview, mobile-stack, output and architecture references; UI wireframe guide; four README descriptions; this Epic and Documents index. Tests reuse existing hybrid/product/UI contract coverage. There is no product PRD/architecture pair in this source repository to translate. No new generated/secret artifact class or gitignore change is needed; logs stay outside the checkout.

## Change Log

- 2026-09-24: owner requested Expo mobile specifications and combined App/Web PRD coverage. Working-tree changes add the common contract and route discovery, architecture and wireframes to it. Existing schema/validator behavior is retained. Official Expo and React Native documentation was checked for development builds, optional EAS and Web support. Verification pending; no executable product or deployment is created.
- Owner clarification: React Native and Expo are references, not mandatory or default choices. Removed the initial default-stack wording from the new contract, entry guidance and all four READMEs before verification. App/Web coverage remains technology-neutral.
- Focused review: Product Definition contract tests initially reported one failure (12 inventoried decisions versus 13 marked questions). Repaired the same-scope guidance by using the existing product/channel discovery and archetype decision instead of introducing another closed question. The test and decision inventory remain unchanged; recheck pending.
- The recheck caught an overlong discovery prompt (228 characters; maximum 160). Shortened the same prompt without removing companion-Web coverage; retained the full scope explanation in the routing reference. No test threshold changed.
- Final log review also found `test_responsive_set_stays_equal_across_product_design_and_harness` still asserting the old three-width documentation example. Updated that existing assertion to require the four-width default, retain the three-viewport minimum and explicitly preserve approved hybrid target sets. The source validator and cross-stage equality checks remain unchanged; focused cross-skill recheck follows.

## Verification And Handoff — 2026-09-24

- Final Product Definition contract recheck: all 95 tests pass. Full Product Definition: 235 pass; UI Design: 281 pass; Design System Compiler: 99 with 3 skips; Product Activation: 56 pass; SEO: 17 pass; golden path: 1 pass. The 66 wireframe contract tests and 5 real-browser checks also pass. Dependency setup, specification, pyflakes, final document-weight and whitespace checks pass. The new native size-class and four-width Web examples parse successfully without changing a validator.
- Full Harness rerun reported the old responsive-example assertion plus the unchanged dirty-checkout assertion and installer-lock failure/teardown error already recorded in [the wireframe Epic](EPIC-wireframe-handoff-refinement.md). Stopped this rerun at about 704 seconds; remaining Harness tests were not rerun in this follow-up. The responsive assertion is repaired and rechecked separately; this is not a full-suite PASS. Inspected the process identity and child commands before termination and confirmed the recorded processes were absent afterward; no failed check remains running. The earlier complete split-run evidence stays historical and is not relabeled as a fresh PASS.
- Logs and exit codes: [results.json](C:/Users/mps19/AppData/Local/Temp/pdh-app-web-wz5wyzyx/results.json). Earlier focused failures and final success remain in `product-contract-early.log`, `product-contract-recheck.log` and `product-contract-final.log` in that directory. The [final scoped source inventory](C:/Users/mps19/AppData/Local/Temp/pdh-app-web-wz5wyzyx/source-hashes-final.json) has SHA-256 `38d5f5ac9bcdc8bf142ed1cf6f340346fc8ce8433f1a1d15fcff20b3d103d304`; its ten file hashes stayed unchanged through final verification. Record-only Epic/index edits are excluded. Specification and document-weight checks were repeated after the final wording repair.
- Repository checkpoint: `product-delivery-harness` / `codex/wireframe-four-widths` / HEAD `077cd3471d267d2c2f093c8d06f3f76a293ed1e1`. Changes remain local and uncommitted. Earlier four-width work, pre-existing audit edits and untracked `scripts/design/hifi_model.py` are preserved. No release, shared skill install, branch/worktree cleanup or product approval occurred.
- Documentation audit: Product Definition routing, interview, output contract, architecture, mobile-stack guidance, UI handoff and all four READMEs agree that React Native + Expo is only a reference option. The same PRD owns included platforms; Web scope and technology remain explicit. The Documents index links this Epic. There is no product PRD/architecture pair or managed PLAN/RUN to update. Gitignore needs no new pattern; source Markdown is not ignored and generated caches remain covered.
- Installed Harness remains 0.54.1; loaded identity remains unknown. Observed shared AGENTS template SHA-256: `86cc1595619c097f79ef8e4234367e9ba8b056a9635bc24d372bcf417b024aa6`. Applicable shared entry/change/handoff rules remain current by meaning; source-repository paths and stricter local authorization/release rules are retained. Document sync reports first observation and unknown loaded identity, not an approval.
- Next: owner reviews this local specification update. Repair the separate Harness test issues before claiming a fully green release candidate. Commit, publication and installation are outside this request.

Final assertion repair: all 15 cross-skill pipeline tests pass, including responsive-set equality; pyflakes passes for the changed test. The [verified source inventory](C:/Users/mps19/AppData/Local/Temp/pdh-app-web-wz5wyzyx/verified-source-hashes.json) adds that test's hash to the ten unchanged final document hashes. No source drift was observed. Only the two previously reproduced broader Harness issues remain unresolved; the stopped full run is still partial, not green.

## Branch publication authorization — 2026-09-25

The owner now requests scoped commits, push of `codex/wireframe-four-widths`, and renewal of all seven Harness skills with the official installer. This supersedes the earlier local-only next action; it does not request main promotion or a release. Verified source hashes are unchanged. Preserve unrelated audit documentation and `scripts/design/hifi_model.py`. The two recorded broader Harness test failures remain open; branch publication is not a full-suite or release PASS. Exact commit, remote readback and installation/backup evidence will be reported after execution. The observed Codex task list has no other active skill-using task; finish skill consumption before installation and start a fresh session afterward.
