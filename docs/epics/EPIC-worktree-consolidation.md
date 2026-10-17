# Consolidate the current worktrees

Status: complete
All 16 worktree heads published; current source integrated locally.
Fixed-candidate contract/correctness review, complete CI and exact main promotion remain pending.

## Request And Scope

On 2026-10-03 the owner requested committing, pushing and merging every current
worktree. The owner then questioned the development target. Fresh remote
observation confirms no development ref and main at
`bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61` (0.58.0).
The new dual-branch consumer contract remains intact. Creating or protecting
development is not part of this request. Direct main landing needs the owner's
exact-candidate decision and an explicit source-release exception to that route.

This is one parent-owned direct consolidation sequence. It creates no consumer
Product Definition, PLAN/RUN, worktree, local branch or UI design decision.
UI impact of conflict repair is none: the newer UI3/DS4 fixtures are retained,
and their synthetic PRD declares eval exemption before approval hashing.
Existing Epics retain accepted scope and historical verification.

Write scope includes the 15 Eval conflict paths, the Vite proposal/index, this Epic,
the workflow guide, four-language candidate descriptions and the bounded
correctness repairs recorded below. The 13 older
detached checkouts have no uncommitted changes; their exact commits are retained
as remote snapshot branches rather than reapplying old versions over current
sources. Snapshot publication is preservation, not fresh verification or release.

## Repository Observations

- Entry: clean `codex/harness-flow-modernization` at
  `2f4ed10ec7a3571f1252f017544b77d9617bee82`.
- Eval: clean `codex/eval-contract-research` at
  `72560a1b7cb5d1d8e7b0163babd0a9ed9ecc9483`, initially unpublished.
- Vite: detached `2fa9b343175f585aca1da551edc0a8654380de9b`, with only two
  research documents uncommitted. Their checkpoint is `23d56690`.
- All heads below were pushed without force in one atomic operation, with
  exact remote read-back. Main was unchanged and development remained absent.
- Live ruleset 18970503 requires a PR and validate, and allows only squash.
  The proposed sole change is allowed_merge_methods: squash -> merge,squash.
  PR/check/deletion/non-fast-forward controls stay intact. No ruleset write,
  protected-branch update, tag, installation, deletion or cleanup has occurred.

| Worktree | Published full SHA | Remote branch | Disposition |
| --- | --- | --- | --- |
| primary | `2f4ed10ec7a3571f1252f017544b77d9617bee82` | `codex/harness-flow-modernization` | current source |
| eval | `72560a1b7cb5d1d8e7b0163babd0a9ed9ecc9483` | `codex/eval-contract-research` | current source |
| viteplus | `23d5669089fb19b13b932361adf392346ea5d9ae` | `codex/viteplus-evaluation` | current source |
| harness-installer-repair | `70ab12bd8770ec4d9ae394b66e640c8c597c7cbb` | `codex/worktree-snapshot-harness-installer-repair` | historical snapshot; no uncommitted edits |
| pdh-review-followups | `fd54a797559c7994eca6af838a581d7fad0e30ac` | `codex/worktree-snapshot-pdh-review-followups` | historical snapshot; no uncommitted edits |
| wf_81434796-014-1 | `d9b037b96f7797629394f9dc5592d572d0c2f772` | `codex/worktree-snapshot-wf_81434796-014-1` | historical snapshot; no uncommitted edits |
| wf_81434796-014-2 | `206a92ed4057367f0eb255387e5f831723de2a67` | `codex/worktree-snapshot-wf_81434796-014-2` | historical snapshot; no uncommitted edits |
| wf_81434796-014-3 | `4b76728d3c6b7956aa2ecf44977c0cb2925f9902` | `codex/worktree-snapshot-wf_81434796-014-3` | historical snapshot; no uncommitted edits |
| wf_81434796-014-4 | `6ccd5a22d516e6619b9c96e2639f7bb088a054ce` | `codex/worktree-snapshot-wf_81434796-014-4` | historical snapshot; no uncommitted edits |
| wf_81434796-014-5 | `72538ec21eab61ef1ed7ea9f5dc9d382c7d7d74f` | `codex/worktree-snapshot-wf_81434796-014-5` | historical snapshot; no uncommitted edits |
| wf_cf68e735-fca-1 | `66bfd01203aa11170efe375ddb4d5dfcdfdd1b00` | `codex/worktree-snapshot-wf_cf68e735-fca-1` | historical snapshot; no uncommitted edits |
| wf_cf68e735-fca-2 | `a1065919dec551fcc930961ee3eb6f1630c65098` | `codex/worktree-snapshot-wf_cf68e735-fca-2` | historical snapshot; no uncommitted edits |
| wf_cf68e735-fca-3 | `bb8d9a11a70bd3153afb4cf837ab1bded96360af` | `codex/worktree-snapshot-wf_cf68e735-fca-3` | historical snapshot; no uncommitted edits |
| wf_f2da7312-78e-1 | `14e1bb633ea26aac96a79b6b93e112e7092c461c` | `codex/worktree-snapshot-wf_f2da7312-78e-1` | historical snapshot; no uncommitted edits |
| wf_f2da7312-78e-2 | `3ab107af56baefd8791e2104c4bff7adeaaf9cda` | `codex/worktree-snapshot-wf_f2da7312-78e-2` | historical snapshot; no uncommitted edits |
| wf_f2da7312-78e-3 | `84ec6261b466a1dce97fb4b038ec8ea502f22c07` | `codex/worktree-snapshot-wf_f2da7312-78e-3` | historical snapshot; no uncommitted edits |

## Change Log And Verification

- `23d56690`: preserve the dated Vite/AI tooling research and index. Whitespace,
  index uniqueness, five referenced source locations and staged diff passed.
- `14eb8674`: merge the 42-commit Eval line into the modernization branch.
  Resolve 15 paths by preserving both contracts, choosing version 0.60.0,
  combining README histories and keeping the newer UI3/DS4 plus dual-branch
  fixtures. Current golden-path PRDs receive the reasoned Eval declaration
  before their approvals; production validators are unchanged by that repair.
- `bd45e8f2`: integrate the Vite documentation. Resolve only DOCUMENTS by
  preserving current rows and adding the proposal. Scoped whitespace/index
  and staged diff checks passed.
- Working-tree candidate preparation: index this consolidation, reconcile the
  workflow's Eval steps and distinguish the unreleased 0.59 source milestone
  from the unified 0.60 candidate in all four README histories.
- 2026-10-03 owner clarification: "這套是 skills，skills 不用去 review security".
  Skip security review for this source consolidation. Continue the independent
  contract/correctness review and complete source CI. This is this task's owner
  exception; it does not edit consumer product security gates. PR #135 was
  opened at `27b634c3`; this documentation checkpoint creates its next exact
  candidate, without repinning earlier checks or review results.

- Complete hosted CI passed all 20 jobs at exact `108ec8014b808ff40432ed0adf49dcefe76104ce`, run [37147080642](https://github.com/Phlegonlabs/product-delivery-harness/actions/runs/37147080642). It covered Linux/macOS/Windows, golden path, required Chromium suites, native installer checks, quality checks and the required aggregate. This is the prior candidate's actual result, not verification of the repair commits below.
- Two native read-only correctness reviewers inspected the unified candidate and requested five repairs. Security review remains waived by the owner. The reviewer role was configured GPT-6.1-Sol/xhigh; actual serving identity was not exposed. One reviewed Harness/root changes; the other inspected all 58 other-skill paths. Review findings and detailed coverage remain in the parent task evidence.

| Repair | Atomic commit | Actual focused verification |
| --- | --- | --- |
| Validate PLAN-only branch policies without treating them as historical RUN pins | `4b62c2ab15f958633ac9e61e79ab03551d7b3200` | Branch policy 9 passed; explicit golden path passed |
| Accept concrete translated Activation blocker and owner-deferral reasons | `92bf0f7648af20453f4ec855a869642acac7afb0` | Activation checker 60 passed; vague/placeholder reasons still rejected |
| Rebind the current animation node after Replay clones it | `b90dd378f4c721fd3bb1e5817a8ee70da700d9b6` | Showcase 14 passed with browser required; before/after video confirms repeated Replay and Stop/Replay |
| Enforce a real total test-profile deadline with owned descendant cleanup | `04c2cec043880dae11106fd10146a4d92c119b79` | Shard helper 13 passed; host runtime 20 passed with two POSIX-only skips on Windows |
| Give native-only UI3 targets a closed intermediate-web-width exception | `fdd2a207b49dc7f38d3d6862ce5b9daba2b908e1` | UI3 12 passed; full UI 323 passed with browser required; README structure 5 passed |

- The owner explicitly authorized the Replay repair through Claude Code Bridge. Observed serving model was `claude-opus-5-5`; launch effort was `high`, serving effort was unobserved. Two bounded attempts preserved the same write scope. The parent corrected its external regeneration script after the first attempt exposed a tuple-return mistake. The second attempt passed verification; an exact staging-order permission mismatch left the four files unstaged. After the worker exited, the parent verified the scoped patch and created the authorized atomic local commit. No provider fallback, permission broadening or concurrent writer was used.
- Final local checkpoint before this bookkeeping child: clean `codex/harness-flow-modernization` at `fdd2a207b49dc7f38d3d6862ce5b9daba2b908e1`; remote work branch still at `108ec801`, main still at `bdae1d82`, development absent. Each repair is in its matching Epic. Required source/static checks and whitespace checks passed; fixtures and lockfiles remain tracked, while dependencies and Python caches use existing ignore rules. The new fixed SHA still requires fresh complete CI and review before the separate exact main decision. PR [135](https://github.com/Phlegonlabs/product-delivery-harness/pull/135) retains the external candidate, check, review and later promotion results.

Focused integration checks passed on the resolved working source before the
Eval merge commit: skill specification, full six-skill Pyflakes, docs weight,
new RUN, tasks view, both golden paths, all three Eval suites, current source
binding and version contract. These are working-tree results, not repinned
final-SHA evidence. Logs and immutable publication inventory are outside Git:
`pdh-worktree-merge-20261003-eb6k85jg`.

The complete fixed-candidate Linux/macOS/Windows CI, required browser suites,
golden path and independent contract/correctness review must cover the unified SHA.
The bound reviewer is native GPT-6.1-Sol/xhigh with read-only assignments;
review coverage and actual returned identity will be retained externally.

## Document And Local-Data Audit

- Expanded PR #135 review at exact `c382375b7b305d30f9b196814125d8a0199b8f4f` found four more correctness gaps in its unresolved automated threads. Both independent reviewers reproduced their assigned cases, superseding the earlier narrower PASS. Complete hosted CI at c382 passed all 20 jobs in run [37150717350](https://github.com/Phlegonlabs/product-delivery-harness/actions/runs/37150717350); it remains that candidate's result and does not certify the repairs below. The task-ancestry comment was inapplicable: Eval merge `14eb8674` and head `72560a1b` are ancestors, with all 42 Eval commits retained. The 13 older worktree snapshots remain preserved. No history rewrite is needed.

| Additional repair | Atomic commit | Actual working-tree verification |
| --- | --- | --- |
| Require substantive no-op target reason suffixes | `6027662666f6a807f0d505f1decf06938b22b935` | Activation checker 61 passed, including English/CJK positives and trivial/placeholder negatives |
| Reject concurrent AGENTS merge drift without removing any bytes | `de553f06fff3478ba6b9999f1adb80e20a1bed61` | Configure tests 16 passed, including pre-open append, same-size edit and late-write preservation |
| Require explicit state-treatment rows even when specimens exist | `77420a901dc2b6fc0c188b19b93091e33384b80c` | Showcase 16 passed with Chromium required; defaults displayed and counted once; fixtures regenerated |
| Bind animation provenance to the actual specimen and named keyframes | `a1052aef0d333c644c5748055242971c02237686` | Full Design System suite 137 passed with four POSIX-only skips on Windows; later expanded Showcase 17 passed with Chromium required |

- Additional-repair checkpoint: clean `codex/harness-flow-modernization` at `a1052aef0d333c644c5748055242971c02237686`; only the current source checkout was authored. Each concern has a scoped Epic entry, regression evidence and an atomic receipt. Full source Pyflakes, skill specification, docs weight, README structure (5) and base-to-candidate whitespace passed. The source and observed installed governance template hashes still match. Existing ignore rules cover dependencies and caches; lockfiles and required fixtures remain tracked. This bookkeeping child freezes the replacement candidate for new complete CI and independent re-review. The previous source-only security waiver remains in force. Main promotion, development bootstrap, ruleset changes, tagging, installation and cleanup remain unperformed.

- The expanded document-sync inventory also reports retired-name review in all four READMEs. The Harness reviewer checked that these are intentional migration mappings or dated version history, with no live route to a retired skill. Unobserved loaded identity and first-observation baselines remain observations, never an approval. No consumer product package or managed state is created.

Observed installed Harness is 0.59.0 from a development installation. Its
PROJECT_AGENTS template and the source template both hash to
`0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`.
Shared governance is current by meaning, with the source-repository omissions
and stricter local Git rules retained. Loaded-at-start skill identity is unknown.
Document sync reports only loaded_identity_unobserved and baseline_review_required;
neither is a PASS. No live consumer PRD/architecture or generated tasks view applies.

No new local artifact class is added: logs, process records and proposal JSON
stay outside the checkout. Existing ignores cover dependencies, bytecode and
local values. All source fixtures, templates, locks, research and Epics stay
tracked. No local worktree, data, branch, backup or old installed skill is removed.

Next action: finish the fixed-candidate checks and independent review, retain
the PR and results, then request the exact main landing and merge-method change.
Do not infer either from a branch push. Formal tag and local installation
remain separate from this source consolidation.


- 2026-10-03 final animation countercheck, baseline `e779b2535738c9bc7180f102fb10bc1c40509dbd`: complete CI run [37153219564](https://github.com/Phlegonlabs/product-delivery-harness/actions/runs/37153219564) passed all 20 jobs. The native Harness reviewer passed its context/rules/document scope with 16 configure tests and six independent race probes. The other-skill reviewer required changes after actual Chromium exposed unresolved easing variables and incorrect animation cascade. Preserve that verdict and CI as e779 evidence. Atomic repair `2b107dc80400864c68857cd85add54faa15b7a1a` implements a closed provenance parser with importance/specificity/order, shorthand/name resets and computed custom properties. Its matching Design Showcase Epic records the red regressions, full 139-test Design System result with required Chromium and four POSIX-only Windows skips, five README tests and static checks. Source skill specification, six-skill Pyflakes, docs weight and baseline whitespace passed after the repair. This bookkeeping child is the new fixed candidate for complete CI and independent re-review; its results remain external through PR #135. Runtime/product CSS and existing approved Replay repair are unchanged. The work branch is clean, all earlier task ancestry remains present, main remains `bdae1d82`, and development is absent. No protected promotion, ruleset write, tag, formal installation or deletion has occurred. Source-only security review remains waived by the owner.


- 2026-10-03 closed-subset follow-up, baseline `faeb9af64b52a347467fe09e6f51f77863365989`: native other-skill review passed 18 of20 actual Chromium counterchecks and reproduced two remaining animation parser cases. Preserve its changes-required verdict. Atomic repair `de2fd2138b185743032a4760362ec0029af39953` rejects escaped CSS before classification and competing none/fill-mode shorthand tokens; helper and full-source regressions plus the valid none treatment pass. Full Design System139 with required Chromium and four Windows POSIX-only skips, README5, scoped Pyflakes and whitespace passed at their recorded working-tree origin. The matching Epic names the reviewer and parent logs. This bookkeeping child freezes the replacement SHA for fresh complete CI and bounded independent confirmation. Before/after state-table images and Replay videos are preserved outside Git. The optional development-bootstrap proposal mirrors main's review/status/no-force/no-deletion protections and names an exact candidate; it is prepared only, not applied. Main's proposal changes only its permitted merge methods to retain atomic ancestry. Both protected-branch actions, formal tag, installer and shutdown-after-completion retain their authorization boundaries. All checkout data and earlier publication refs remain preserved.
