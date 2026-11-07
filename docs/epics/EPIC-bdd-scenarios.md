# EPIC-bdd-scenarios: executable scenarios under every Test Obligation

Status: complete locally; candidate `d36c7216` (0.77.0) passed the full matrix; publication, tag and install are owner actions

## Problem And Baseline

The PRD package already carries the spine of behavior-driven delivery: `PRD-*` requirements, `TEST-*` obligations with an Expected signal, journeys written as action and visible result, and a delivery-acceptance register whose scenarios freeze persona, initial data, ordered actions and assertions. What is missing is one layer a person can read and a runner can execute: the scenario text itself. Today it is written twice, once as journey prose in the PRD and once as JSON in `docs/verification/delivery-acceptance.json`, and neither is run by a BDD tool.

Owner direction (2026-11-07): add that layer across the suite, simplify the wording of every section the work touches, write with Claude Opus 5.5 at effort xhigh, review with Claude Fable 5.1. Blank projects and enhancement rounds use the same layer; a blank project approves the whole set once, a round approves its delta.

Baseline: `origin/main` `12eecf90` (0.76.1 merged through PR #179).

## Accepted Scope

Frozen conventions. Every writer and reviewer applies these without re-deciding them.

- Feature files live at `docs/product/features/<scope>.feature`. `standard` and `mvp` packages use `product.feature`; a `program` package uses one file per module scope token in lowercase (`inv.feature`) plus `program.feature` for the program PRD's own TESTs (`TEST-PRG-*`, `TEST-E2E-*`, `TEST-MIG-*`). With `--module`, only the program's and that module's rows need a scenario; any module's TEST may be named.
- A feature file is part of the PRD package: staged, approved, hashed and archived with `PRD.md`. Its text is owner-approved product content. Step definitions are implementation code owned by the writer.
- Every scenario carries exactly one `@TEST-...` tag. Its id is `<TEST-ID>/<slug of the scenario name>` and is the `scenarios[].id` of the delivery-acceptance register.
- Every `Required: Yes` Test Obligation needs at least one scenario, because the delivery-acceptance register already freezes one scenario per Required TEST; `Required: No` rows may have scenarios.
- Given maps to persona and initial data, When to ordered actions, Then to assertions `ASSERT-001..` in order. Background steps are Given steps of every scenario in the file. And/But continue the previous keyword.
- `@platform:<value>`, `@auth:<value>` and `@env:<value>` tags override the run profile for one scenario. Build identity, execution target, device, OS, tenant, account state and fixtures come from a run profile JSON the parent authors; `render_delivery_acceptance.py` joins the two into the register.
- Not supported in this round: Scenario Outline, Examples, Rule, doc strings, data tables, non-English keywords. The reader rejects them with a line number.
- A scenario text change is a product decision and goes through a PRD delta; a change that touches only step definitions or implementation is a small fix on the existing Epic.
- `check_product_package.py --features <dir>` is required for new packages, as `--eval-policy` is; legacy packages are unaffected. `check_prd_delta_scope.py` requires every `new` or `revised` delta ID carrying a Required TEST to appear as a changed scenario in the bound feature diff.
- The shared reader is `product-definition-builder/scripts/feature_file.py`; the delivery-harness scripts load it the way `harness_contract_join.py` loads the package checker.
- Wording: in every touched section, shorter sentences, no repeated rule, no new word beyond what the rule needs. Rules stay intact; tests that pin sentences are updated with the sentence, never deleted.

Writers and ownership:

- W1 (Opus 5.5, xhigh): product-definition-builder side. `references/output-contract.md`, `references/stages/product-definition.md`, `references/artifact-lifecycle.md`, `assets/templates/PRD_DELTA.template.md`, the two PRD templates' Test Obligations note, `assets/templates/FEATURE.template.feature`, `scripts/check_feature_coverage.py`, the `--features` flag in `scripts/check_product_package.py`, tests, `SKILL.md`.
- W2 (Opus 5.5, xhigh): delivery-harness side. `references/delivery-acceptance-contract.md`, `references/contract-and-traceability.md`, `references/verification-gates.md`, `references/bounded-enhancement.md`, `references/platform-archetypes.md`, `references/stages/stage-cards.md`, `assets/templates/PROJECT_AGENTS.template.md`, `assets/templates/DOCUMENTS.template.md`, `assets/templates/PROJECT_CI.template.yml`, `scripts/render_delivery_acceptance.py`, the scenario rule in `scripts/check_prd_delta_scope.py`, tests, `SKILL.md`.
- W3 (Opus 5.5, xhigh), after integration: the four READMEs' descriptive sections and version-history entries.
- Parent: this Epic, `docs/DOCUMENTS.md`, the shared reader, integration, version bump, review, full matrix.

Out of scope: converting this repository's own test suite to BDD; back-filling scenarios into existing consumer packages; any runner installation.

Ambition rung: 2 — a consumer package approved after this release can run its Test Obligations as scenarios without a second hand-written register.
Outside judge: a blank consumer project whose `check_product_package.py --features` and `check_delivery_acceptance.py` both pass on a register rendered from its feature files.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| BDD-1 | `feature_file.py` parses the supported subset, resolves And/But and Background, rejects the unsupported subset with `path:line` | `test_feature_file.py` | none |
| BDD-2 | `check_feature_coverage.py` and `check_product_package.py --features` prove both directions: every Required TEST has a scenario, every scenario tag names an existing TEST | pdb tests | BDD-1 |
| BDD-3 | `render_delivery_acceptance.py` writes a register that `check_delivery_acceptance.py` accepts unchanged; profile tags override the run profile | harness tests | BDD-1 |
| BDD-4 | `check_prd_delta_scope.py` rejects a delta whose new or revised Required TEST has no changed scenario | `test_prd_delta_scope.py` | BDD-1 |
| BDD-5 | Templates and references state the conventions above once each; the Greenfield scaffold and `PROJECT_AGENTS` carry the Behavior Specs rule | `test_skill_contract.py`, docs weight | none |
| BDD-6 | Four READMEs describe the layer and the 0.77.0 entry | `test_skill_contract.py` | BDD-2..5 |

## Document Impact

| Changed source / requirement | Affected live artifact | Required recheck |
| --- | --- | --- |
| Feature files join the package | `output-contract.md`, `artifact-lifecycle.md`, `product-definition.md`, PRD and delta templates | pdb suite, `check_skill_spec.py` |
| Register rendered from features | `delivery-acceptance-contract.md`, `stage-cards.md`, `contract-and-traceability.md` | harness suite |
| Scaffold and project rules | `platform-archetypes.md`, `PROJECT_AGENTS.template.md`, `DOCUMENTS.template.md`, `PROJECT_CI.template.yml` | `test_skill_contract.py` |
| Release surfaces | four READMEs, `CHANGELOG.md`, `VERSION`, `package.json`, RUNBOOK default | `test_skill_contract.py` |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Shared feature-file reader | One parser for both skills, frozen before the writers start | `7be60715` | `test_feature_file.py` 8 tests, exit 0 |
| Epic opened | Conventions frozen before launch | `ce08d8f7` | `git diff --check` exit 0 |
| W1: product-definition-builder side | Feature template, `check_feature_coverage.py`, `--features` on the package checker, output contract, stage steps 12 and 19, lifecycle, delta `## Changed Scenarios`, entry points | `2935bae7`..`9d348b4c`, fast-forwarded onto `feat/bdd-scenarios` at `9d348b4c` | On the integrated head: pdb suite 430 tests exit 0; `test_skill_contract.py`, `test_docs_reading_budget.py`, `check_skill_spec.py`, pyflakes, `git diff --check` exit 0; docs weight +287 words. `test_cli_utf8_output.py` inventory entry is a parent edit after W2 |
| W2: delivery-harness side | `render_delivery_acceptance.py` and the profile template, the delta scenario rule, acceptance contract, traceability, gates, enhancement, scaffold, stage card, project templates, SKILL wording | `bf021846`..`51cb05ee`, merged at `73d4a802` | W2's final run: harness suite 112 modules exit 0, golden path exit 0, skill spec, pyflakes, docs weight, `git diff --check` exit 0; docs weight +255 words |
| Parent: inventory and AGENTS omission | W1's checker in the UTF-8 CLI inventory; this repository omits the template's Behavior Specs | `bec44f2a`, `10b733de` | `test_cli_utf8_output.py` exit 0 |
| Repair: one scenario per Required TEST | `check_delivery_acceptance.py` rejects a register that omits any Required TEST, so the narrow E2E/integration/contract rule could pass coverage and fail the render; the checker, its tests, the output contract and this Epic now require a scenario for every Required TEST | `20b9e624` | pdb suite 430 tests exit 0; eight harness modules exit 0; pyflakes, skill spec, docs weight, `git diff --check` exit 0 |
| W3: READMEs and release surfaces | Four READMEs describe the feature files and the rendered register; version 0.77.0 on every surface with the 0.75.2 entry rotated into CHANGELOG | `58a3e82e`, `5d27a648`, fast-forwarded | `test_skill_contract.py`, `test_documented_commands.py`, `test_readme_structure.py`, skill spec, docs weight, `git diff --check` exit 0 |
| Matrix at `5d27a648` | Full Required Verification run | `task/release-0770/matrix-5d27a648/summary.txt` | harness suite 110 of 112 modules; `test_enhancement_entry_contract.py` (W3 dropped a pinned Chinese sentence) and `test_install_script.py` (digest hashed a `.pytest_cache` the installer skips) failed; every other step exit 0 |
| Fix: pinned README sentence | Restore `不能手動編輯產生區段` / `不能手动编辑生成区段` beside the new clause | `d512ad11` | `test_enhancement_entry_contract.py`, `test_skill_contract.py` exit 0 |
| Fix: digest ignores `.pytest_cache` | `contract_digest` now skips what `install.sh` never stages; a clean tree's digest is unchanged | `8ee9054d` | `test_harness_contract.py`, `test_install_script.py` exit 0 |
| Matrix at `8ee9054d` | Full Required Verification run after the two fixes | `task/release-0770/matrix-8ee9054d/summary.txt` | every step exit 0; harness suite 112 of 112 modules |
| W4: READMEs end to end | Start here and What is included rows for delivery-harness, the flow diagram's Product and Tests nodes, a Delivery acceptance bullet in Operating rules, and a proofread of the 0.77.0 entry in zh-TW, zh-CN and es | `d36c7216`, fast-forwarded | `test_skill_contract.py`, `test_enhancement_entry_contract.py`, `test_readme_structure.py`, `test_documented_commands.py`, `test_pre_delivery_self_review.py`, skill spec, `git diff --check` exit 0 |
| Matrix at `d36c7216` | Full Required Verification run at the candidate | `task/release-0770/matrix-d36c7216/summary.txt` | every step exit 0: skill spec, pyflakes, docs weight, harness suite 112 of 112 modules (788 s, 8 workers), golden path, pdb, udb and dsc suites, git diff --check |

## Results And Remaining Work

- W1 integrated at `9d348b4c`; parent read of the diff found no blocking finding.
- The approval package digest still covers only PRD, architecture and stack decisions. This round lists each feature file with its SHA-256 in the approval request, as eval inputs are listed; folding feature files into `canonical_product_bytes` and the approval check is a later round. Closed by the suite review (M24): the approval block now carries a separate `Feature files` digest field that `check_product_package.py --features --require-approved` verifies.
- `TEST-PRG-*` scenarios live in `program.feature`; W1 also split lifecycle steps 3 and 4 and corrected the interview turn count in `openai.yaml` from three to four.
- W2 integrated at `73d4a802`. The parent read of its diff found one blocking mismatch with W1's rule, repaired in `20b9e624`.
- Open, cosmetic: `check_delivery_acceptance.py` prints a matched scenario as `<test_id>/<scenario id>`, which now doubles the TEST ID because scenario ids start with it.
- The delta scenario rule compares `--features` with `--features-base`, a directory holding the baseline's feature files; a checkout of the baseline supplies it.
- Candidate `d36c7216`, version 0.77.0, branch `feat/bdd-scenarios` from `origin/main` `12eecf90`. Full matrix: every step exit 0: skill spec, pyflakes, docs weight, harness suite 112 of 112 modules (788 s, 8 workers), golden path, pdb, udb and dsc suites, git diff --check.
- Review at `d36c7216` by the parent (Claude Fable 5.1, owner direction 2026-11-07; the hook refuses Fable children, so the parent read the whole diff itself). Code lens: PASS after one repair (`20b9e624`) and two matrix-driven fixes. Security lens, scope `check_feature_coverage.py`, `check_product_package.py --features`, `render_delivery_acceptance.py`, `check_prd_delta_scope.py`, `harness_contract.py`, `feature_file.py`: repository files and CLI arguments are the only untrusted input; no network, secret or privileged operation; denial behavior is tested (malformed feature file and unknown TEST are `path:line` findings, placeholder profile is a finding, missing directory or unpaired flags exit 2, duplicate scenario ids are findings); PASS for that scope. Visual lens: not applicable, no UI change.
- Open for a later round: the doubled TEST ID in the acceptance checker's output; a reading-budget ratchet per entry point.
- Not done here, owner actions: push the branch and open the PR to `main`, tag `v0.77.0` after the merge, install at a quiescent boundary with `./install.sh`, then consumer adoption. The three record-fix commits and the two harness fixes on `fix/compact-tracked-files-retention` are a separate PR.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / feat/bdd-scenarios / d36c7216 plus this record / task/ untracked
Stage and skill: source maintenance, managed topology by hand (delivery-harness governance)
Inputs consumed (path + hash or revision): origin/main 12eecf90; source-maintenance.md, delegation-contract.md, commit-convention.md at that revision
Approvals in force (gate, owner, date, candidate): owner direction 2026-11-07 for the scope, writers and reviewer above; local branches, worktrees and commits; no push, tag, install or release
Done and verified (command, exit code): full matrix at d36c7216 (task/release-0770/matrix-d36c7216): every step exit 0: skill spec, pyflakes, docs weight, harness suite 112 of 112 modules (788 s, 8 workers), golden path, pdb, udb and dsc suites, git diff --check. Earlier: repair 20b9e624: pdb suite 430 tests exit 0; test_skill_contract, test_cli_utf8_output, test_render_delivery_acceptance, test_prd_delta_scope, test_project_template_rules, test_enhancement_entry_contract, test_docs_reading_budget, test_documented_commands exit 0; pyflakes, check_skill_spec, docs_weight, git diff --check exit 0. W1 integration at 9d348b4c: python -B -m unittest discover -s skills/product-definition-builder/scripts/tests (430 tests, exit 0); test_skill_contract.py and test_docs_reading_budget.py (exit 0); check_skill_spec.py, pyflakes, docs_weight.py, git diff --check (exit 0)
Remaining: owner publication only (push, PR to main, tag v0.77.0, install, consumer adoption); worker worktrees under C:/Users/mps19/.t3/worktrees/product-delivery-harness/ await a separate removal decision
Blocked / waiting (gate name or owner decision): owner decision to publish the branch
Next action (one command or one owner decision): owner pushes feat/bdd-scenarios at d36c7216 and opens the PR to main
Next owner (skill or human): human
```
