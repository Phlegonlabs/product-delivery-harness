# EPIC-epic-landing-grant: one owner approval covers an Epic's push, merge, deployment and cleanup

Status: candidate prepared as 0.92.0; review and PR pending
Design workflow: enhancement
UI impact: none

## Problem And Baseline

The owner wants an agent to finish an Epic without stopping to ask at each Git step, so that code can land overnight. The promotion contract made that impossible by wording, not by any gate: condition 5 of Promote To Main and the archive publication rule both require an instruction that names the exact SHA, and a SHA exists only after the work is done. Push, merge, branch deletion and worktree removal each waited for a new instruction.

Two independent reviews (Claude Fable 5.2 and GPT-6.2 Astra, 2026-11-18) agreed on the cut. Autonomy belongs to an Epic and an action, not to a project's age. The owner approves how the candidate will be identified; the parent binds that approval to the real SHA when it acts. A candidate must not be able to edit its own grant or its own required checks.

Baseline: `main` `a3b547dd` (v0.91.0). This is round two of three approved on 2026-11-18; round one is [EPIC-entry-route-split](EPIC-entry-route-split.md).

## Accepted Scope

Owner decisions, 2026-11-18:

- A grant covers commit, push, pull request, merge to `main`, production deployment with its smoke, and deletion of the merged work branch and its worktrees.
- A grant also covers bot review threads. The owner first left this out and added it later the same day: fix a confirmed finding or post a concrete disproof, reply, resolve, read the state back.
- Rounds are published one at a time.

Included:

- LG-1: the rule. `branch-promotion-contract.md` gains `## Epic Landing Grant`; condition 5 and the publication rule accept a passing grant check in place of the SHA-naming instruction. No gate changes.
- LG-2: repository eligibility. A repository states its landing policy in `.harness/landing-policy.json`, strict JSON, default `"landing": "owner_each_time"`; the parent reads it from the frozen `main` base. `PROJECT_AGENTS.template.md` and this repository's `AGENTS.md` gain a `## Delivery Autonomy` section that points at the file. The policy began as lines in that section and moved to JSON during review; see Review And Repairs.
- LG-3: `scripts/landing_gate.py` with `record`, `revoke`, `check` and `cleanup-plan`. It is offline, performs no action and never writes inside the checkout.
- LG-4: the standing cleanup exception, limited to the commands `cleanup-plan` prints.

Kept unchanged: every review, security, acceptance, Preview and read-back gate; the 12 ledger keys; a managed RUN closing `local_only` at C with `push` false; the C-to-A archive receipt; legacy pins; no force-push.

Always the owner's: product scope and PRD changes, a changed visual direction, spending and paid resources, external console setup, destructive data operations and migrations, protection or ruleset exceptions, and owner-only paths (`AGENTS.md`, `CLAUDE.md`, CI workflow files, plus what the repository lists).

Not in this round: choosing a pilot repository and setting it to `epic_grant`. That needs the repository's CI coverage and protection rules read first, and it is the owner's decision. This source repository is seeded at `owner_each_time`.

Ambition rung: 2 — an eligible repository lands an Epic end to end on one owner approval.
Outside judge: `test_landing_gate.py` refusing each attack the reviews named (wrong repository, stale head, expiry, revocation, a policy edited on the candidate), and one independent review of the candidate.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| LG-1 | The section states the two conditions, the six actions, the order, what stays the owner's and the managed-RUN limits; every pointer resolves | `test_skill_contract.py::test_epic_landing_grant_replaces_the_sha_instruction_and_no_gate`, `test_governance_entry_routes.py` | none |
| LG-2 | A repository without the file, or with the seeded template, is not eligible; this repository states its own policy; the reader accepts one spelling of the file and refuses every other | `test_skill_contract.py`, `test_project_template_rules.py`, `test_landing_gate.py::test_policy_reader_acceptance_matrix` | none |
| LG-3 | `check` passes a valid grant and refuses: hash mismatch, revoked, expired, action not granted, wrong repository, stale head, base not an ancestor, policy not `epic_grant`, policy changed only on the candidate, an owner-only path, a missing or failed required check, checks for another SHA, a review that is not PASS or binds an older code state, failed acceptance, a deployment without a passing read-back | `test_landing_gate.py` | worker commit |
| LG-4 | `cleanup-plan` plans a merged branch and its clean linked worktree; refuses a dirty worktree, a branch that moved, the primary checkout and a protected branch; no planned command holds a force flag | `test_landing_gate.py` | worker commit |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Rule text, templates and pointers | LG-1, LG-2, LG-4. `branch-promotion-contract.md`, `SKILL.md`, `stages/direct-cards.md`, `stages/stage-cards.md`, `trusted-host-publication.md`, `direct-fan-out.md`, the three governance files, `EPIC.template.md`, `PROJECT_AGENTS.template.md`, `AGENTS.md`, the four READMEs | `4c403761` | Doc-asserting modules pass (241 tests). Direct route must-read 3,828 to 3,878 words; the grant section is read only when an Epic records a grant. |

| Landing gate script | LG-3, LG-4. `landing_gate.py` (record, revoke, check, cleanup-plan) and 51 tests, written by a GLM-5.3 worker in its own worktree | `8e7b9ff7` | 51 tests pass; pyflakes clean on the four script trees. |
| Parent inspection before review | Four gaps the parent found by reading the script. It refused every ssh remote of the form `git@host:owner/repo.git` as a credential, although the shared push-URL helper already accepts a passwordless ssh identity and rejects a password. A renamed owner-only file showed only its new name and passed the owner-only check. A failed diff read as "nothing changed". A merge check with no `--evidence` raised instead of refusing. The review carry-forward also accepted any `.md` path, which in this repository includes rule text; it now accepts only `docs/` and top-level `README*.md` and `CHANGELOG.md` | `8c93cd64` | 55 tests pass, four of them new. |

## Review And Repairs

One review point on `70c87857`, two read-only calls launched together (GPT-6.1 Sol, effort high): the rule text (318 s) and the script with the security lens (455 s). Both returned FIX_REQUIRED. Fifteen blocking findings, each with the line and the input that showed it. Most trace to the parent's rule text and brief, not to the worker's implementation of that brief.

Rule text, five findings, repaired in `ad7994d3` (and in the script where the rule needed enforcement, `6abee2a4`):

| Finding | Repair |
| --- | --- |
| The order put push before the review, which moved the review boundary | Review comes before push again. `push` and `pull_request` now need a review PASS that binds the candidate |
| A review PASS carried across any later change under `docs/`, wider than the existing carry-forward rule | It carries only across a commit that changes the Epic record alone (`docs/epics/*.md`, `docs/DOCUMENTS.md`) |
| "CI workflow files" covered only `.github/workflows/` | Owner-only now covers `.github/`, the standard CI paths of five other systems, and instruction files at any depth; a repository lists any other check definition itself |
| The repair budget was recorded and never enforced | The parent reports repair rounds in the evidence; the check refuses a count above the budget |
| `cleanup-plan` did not check the repository, so a grant could print deletions for a fork | It applies the same grant, repository and policy checks as `check` |

Script, ten findings, repaired in `6abee2a4` by rewriting the gate fail-closed:

| Finding | Repair |
| --- | --- |
| `refs/heads/Main` passed the protected-branch test although Windows resolves it to `main` | Protected names compare case-insensitively in `record`, in grant validation and in the worktree match |
| Cleanup was not bound to the repository or to a grant outside the checkout | One shared binding check serves `check` and `cleanup-plan` |
| Three owner-only bypasses: a quoted non-ASCII path, a case variant, a directory replaced by a submodule | Paths are read with `-z`, matched case-insensitively, and a directory pattern also matches the directory entry |
| A fenced example, a second section or a repeated key could make a repository eligible; `Landing` alone was enough | Fences are skipped; exactly one section, no repeated key and all six lines filled are required |
| Code under `docs/` inherited an older review | See the carry-forward repair above |
| A symlink alias of the grant hid its revocation marker | The marker is looked up beside the canonical grant path |
| `--now` revived an expired grant | The flag is gone; tests replace the clock function |
| A missing `observed_main` or a git error led to `git branch -D` | A read-back needs every field; a git error is an error; `-D` is planned only for `tree_equal_S` |
| A grant with no `repository` and an unreadable remote compared equal | The grant's fields are validated after the hash; an unreadable remote is a refusal |
| A missing `--action` and a git timeout escaped as tracebacks | Both now return the structured error or refusal |

`cleanup-plan` is also all or nothing now: one refused target leaves no command to run.

Each repair has a test: 72 tests in `test_landing_gate.py`, 21 of them new. One, the revocation alias, needs a symbolic link and is skipped on a Windows host without that privilege; CI runs it on Linux and macOS.

Targeted re-check on `4254dc57`, the same two lenses (194 s and 398 s): eleven of the fifteen findings resolved. Four remained or were sharpened, and the repair had introduced two more. All six went into one isolated repair (`6d96c7d6`, `e60ed588`):

| Finding | Repair |
| --- | --- |
| The narrowed carry-forward still let a review stand after a change to an Epic record that was itself in the reviewed scope | No later commit inherits a review. `review.sha` must be the candidate |
| That narrowing contradicted the existing rule that archive child A inherits C's review | The one inheritance is stated and enforced: A's only parent is C and the parent reports the receipt-bound C-to-A verification as passed |
| `review_threads` could authorize fixes without the repair budget | It needs the repair-round count like the other actions |
| The policy reader still accepted an indented example, a nested fence and a second heading with closing hashes | It no longer interprets Markdown. It accepts one plain shape: the heading written exactly, once in the file under any spelling or level, above every code fence, with unindented lines; anything else is not eligible |
| New in the repair: matching worktrees case-insensitively could select the worktree of another branch | The worktree match is exact again; case-insensitive comparison stays only on the protected names |
| A read-back was believed by its label: `exact` with main still at the base, or `tree_equal_S` with another tree | The gate recomputes the classification from the two commits and refuses a label that disagrees |
| Evidence and read-back files inside the checkout were accepted | Both must resolve outside the checkout |

Scoped review of that repair on `1788442c`: the rule-text lens PASS (204 s). The script lens FIX_REQUIRED (391 s): the worktree, read-back and placement repairs held, but the policy reader failed again in two more ways. It skipped an indented second `- Landing:` line before counting repeats, which the previous version had refused, and it did not see `## Delivery  Autonomy ###`, with two inner spaces, as a second heading.

That was the third review to find a hole in the same reader, so the next repair changed the approach, not the patch (`2c540e82`). The reader no longer walks the file as Markdown. It checks one invariant over the whole file: the heading and each of the six policy lines occur exactly once under any spelling, indentation or list marker; that one occurrence is in the plain form; the lines sit inside the section; and nothing above them is a code fence or an HTML comment. Whatever it cannot place is a refusal.

Acceptance matrix for the family, `policy_matrix()` in `test_landing_gate.py`: 469 cases over five classes (heading spelling, policy-line spelling, a second occurrence anywhere in the file, a wrapper above the policy, an incomplete policy). Old reader loaded from `1788442c` against the new one, on the same texts:

| Transition | Cases |
| --- | --- |
| old accept, new accept (retained) | 8 |
| old accept, new reject (closed) | 265 |
| old reject, new reject | 196 |
| old reject, new accept | 0 |

This repository's own `AGENTS.md` and the project template both read as one complete section under the new reader.

Scoped review of the reader repair on `b5188c91` (375 s): FIX_REQUIRED again. The reviewer reproduced the 469 cases and the transition counts, confirmed both earlier findings resolved, and then found three more texts the reader accepted: a linked heading `## [Delivery Autonomy](#delivery-autonomy)` with an escaped `- Landing\\:` line, a whole policy inside `<pre>`, and a value wrapped onto a second line, which silently dropped a required check and an owner-only path.

Four reviews had now each found another spelling. The premise shared by every repair was that a policy written in Markdown can be read safely by something that is not a Markdown parser. It cannot: Markdown has many texts that render alike. So the policy left Markdown (`bb6f7eb8`). It is now `.harness/landing-policy.json`, read from the frozen base with the standard JSON parser plus four checks: UTF-8, no repeated key, exactly the seven fields, and each value of its one allowed type. `AGENTS.md` keeps a `## Delivery Autonomy` section, but it is prose that points at the file and is never parsed. `.harness/` is an owner-only path. The 469-case Markdown matrix is gone with the reader it tested; `policy_matrix()` now lists 137 ways to write the JSON file, 7 accepted and 130 refused, including each field missing, repeated, mistyped or respelled, comments, trailing text, a byte order mark, NaN and a Markdown section in place of JSON.

`test_landing_gate.py` holds 78 tests.

Scoped review of the move to JSON on `cbdeeb98` (372 s): PASS, no blocking finding. The three earlier inputs are refused. The reviewer reran the 137 matrix cases and added 6,941 probes of its own: repeated keys including escaped equivalents and nested ones, escaped key names, every non-string type, NaN and Infinity, every single leading and trailing byte, other encodings, eight-million-character strings and nesting to 100,000 levels. It found 274 accepts, each with exactly the written values, 6,667 refusals, no crash, and no reader left that looks at `AGENTS.md`. It states the limit itself: the probes are finite, not a proof, and it did not run the fixture-based tests.

Review summary for this candidate:

| Pass | Scope | Result |
| --- | --- | --- |
| Parent inspection | script | 4 gaps fixed before review |
| Review, `70c87857` | rule text and script | FIX_REQUIRED, 15 findings |
| Targeted re-check, `4254dc57` | rule text and script | 11 resolved; 6 for an isolated repair |
| Scoped review, `1788442c` | rule text | PASS |
| Scoped review, `1788442c` | script | FIX_REQUIRED, 2 on the policy reader |
| Scoped review, `b5188c91` | policy reader | FIX_REQUIRED, 3 more; premise changed |
| Scoped review, `cbdeeb98` | policy file as JSON | PASS |
| Pull-request review, `a1d8a990` | whole diff (Codex) | 1 finding: ignored files |
| Scoped review, `e1974841` | ignored-file repair | FIX_REQUIRED, 1 in the repair |
| Scoped review, `13ea7b97` | path-name correction | PASS |

Pull-request review (Codex, on `a1d8a990`), one P1: `cleanup-plan` called a worktree clean when `git status --porcelain` printed nothing, but `git worktree remove` deletes ignored files silently, and the reviewer lost an ignored `local.db` that way. None of the seven earlier passes looked at ignored files. Repair `40996cf5`: the plan reads `git status --ignored`, and a worktree holding any ignored file outside five regenerable cache directories (`node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`) is refused with the files named.

Scoped review of that repair on `e1974841` (223 s): the finding resolved, one defect in the repair itself. The listing turned backslashes into slashes, so on POSIX an ignored file named `private\node_modules\local.db` looked as if it sat in a cache directory. Git prints `/` between directories on every platform, so the rewrite was wrong wherever it stood; it is removed from the ignored-file listing and from the changed-path listing (`2c7f38a6`). Scoped review of that correction on `13ea7b97` (127 s): PASS. The reviewer also confirmed, against git's own path handling, that using names as printed does not weaken the owner-only check on Windows or POSIX.

CI on `a1d8a990`: `linux-required-browser` failed in `test_surface_capability.CapabilityBrowserTests.test_missing_or_unestablished_denial_fails_closed_before_product_activation` of design-system-compiler, which read an empty status before the page had written it. This branch changes nothing under `skills/design-system-compiler` or `skills/ui-design-builder`, and the test passed on PR #201 and on `main`. Treated as a timing flake. On `e1974841` the same job passed.

CI on `13ea7b97`: `linux-harness-3` failed in `test_harness_transition_lease_packet.LeasePacketCli.test_unfilled_placeholders_refuse_before_the_run_write`, where `acquire-run-lock` returned 2 in `setUp`; the six other tests of that class passed with the same `setUp`, and this branch does not touch `harness_transition.py`. Also treated as a flake; the next push is the fresh run. Two unrelated flakes in two consecutive runs is worth its own look after this round.

What cost the time: the gate was specified by listing what to refuse. Each review then found the next thing nobody had listed. Two changes ended it, and both replaced a list of bad cases with a rule about what is accepted: the gate recomputes what it can check instead of believing a label, and the policy has one spelling.

## Results And Remaining Work

Remaining: PR, CI matrix. Merge, tag and install wait for the owner, because this repository's own policy is `Landing: owner_each_time`.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / epic-landing-grant / the commit after cbdeeb98 / task/ (untracked, not part of this round)
Stage and skill: source maintenance of delivery-harness; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main a3b547dd (v0.91.0); owner-approved plan of 2026-11-18
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): plan approval, owner, 2026-11-18: work branch, local commits, push and PR. Merge, tag and install for this round are not yet approved.
Done and verified (command, exit code): pytest on the doc-asserting modules, test_landing_gate.py and test_install_script.py, exit 0; pyflakes on the four script trees, exit 0; prepare_release.py --check, exit 0; scoped review PASS on cbdeeb98
Remaining: PR, CI matrix
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): push the branch and open the PR
Next owner (skill or human): parent agent
```
