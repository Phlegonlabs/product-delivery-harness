# Source Maintenance

These rules own skill-source reading, Git, release verification, installation, and review. They authorize only actions explicitly granted by the owner or a matching RUN ledger.

## Required Reading

- Before editing `skills/` or any documented flow, read the canonical SKILL.md and the references the change touches; the four READMEs are the documentation of record.
- Before running a Product Delivery Harness flow in a target repository, that repository's seeded `AGENTS.md` Required Reading rules govern the session — they are mandatory, not advisory.
- Work that skipped this reading is a blocking review finding.

## Mission Task Split

- When decomposing a PRD into full-delivery missions, keep each mission a feature batch and split it into finer tasks: one task per small, independently verifiable step, so each step is done and checked carefully. Fine tasks, not more missions, carry the small steps.
- Each task keeps its own atomic commit. Finer tasks stay sequential checkpoints inside their mission. A section may contain several independent frontend, backend or integration missions after shared interfaces are frozen; each writer uses an isolated checkout and a nonconflicting scope.

## Git Flow

- Before every authorized commit, read [Atomic Commit Convention](../commit-convention.md). Direct tasks use `<type>(<scope>): <imperative summary>`; managed task and mission trailers apply only inside managed runs.
- This skills source repository is maintained for the owner's own use. Protect `main` permanently. Use temporary work branches and reviewed PRs directly to `main`; no `development` branch or development integration is required. The consumer branch-promotion contract governs consuming repositories, not this source-maintenance route. Preserve exact-candidate verification, atomic history and separate publication authority.
- Before any action represented in the RUN authorization ledger, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create the exact non-default work branch named by governance or the user from observed released `main`. Preserve the original base. If the branch name is unresolved, ask; never add a fixed prefix. Never recreate `development` for source maintenance.
- With matching `create_local_commits` authorization, commit only the verified task scope. Commit atomically: one commit per minimal logical change (matching the minimal task split), never bundling unrelated changes.
- Worker branches and worktrees stay local. With matching `integrate_locally` authorization, the parent integrates verified worker commits into that one run branch.
- Harness 0.38+ RUNs close `local_only` at candidate C. Their `push` authorization remains false, `pushed_head_sha` remains null, and PLAN contains no push lifecycle node.
- After RUN close, archive on the same work branch and create archive-only direct child A, following [Managed RUN Archive Before Promotion](../branch-promotion-contract.md#managed-run-archive-before-promotion). The frozen PLAN also preserves its version-pinned original base. The parent publishes A only after the owner's exact instruction naming its SHA and branch, then reads back the remote ref. This grants no protected-branch landing. Never force-push.
- Land a reviewed fixed candidate directly into `main` only under separate exact target/SHA authorization and the required PR mechanism. Preserve atomic task history. A provider-created main SHA S inherits candidate evidence only after verified tree equality, with the original result origin retained; a different tree is a new candidate. This source route creates no product deployment or consumer hotfix forward-integration obligation.
- Branch deletion and worktree removal are separate actions. Do not infer approval for them from implementation or from a successful push.

## Update Local Skills

- After a verified formal release, compare its five-skill bundle digest with the observed installed digest. When different, complete one local update at a quiescent boundary in the release handoff; a feature or development push does not replace the installed release. An explicitly requested development installation is a separate channel and never becomes the official release by implication. Quiesce only relevant active skill-using sessions, then run `./install.sh` (in Git Bash on Windows) against `~/.agents/skills/`. It installs `delivery-harness`, `product-definition-builder`, `ui-design-builder`, `design-system-compiler`, and `growth-review`; retires `full-harness`, `prd-builder`, `product-design-builder`, `code-security-review`, `product-activation`, and `seo-growth-review`; and writes prior copies under `~/.agents/skill-backups/product-delivery-harness/`. Never replace the installer with manual move/copy commands; never overwrite or delete prior copies or backups. A failed install rolls itself back. If post-install verification fails, rerun the installer from the previous release tag so it backs up the bad copy first. Restart the relevant host only after successful verification and when needed to load changed skills. If installation cannot finish, report it pending; do not claim the release handoff fully complete.
- Per-runtime copies (Codex plugin, Claude plugin, Pi extension) stay retired. Do not install, update, or reinstall them.

## Required Verification

Edit the canonical skill sources in `skills/`. For each atomic task, run focused checks selected from changed files and their negative cases. The candidate's one full run is the required matrix below, from the repository root. CI on the candidate SHA is that run; a local full run happens only when CI is unavailable. Source maintenance does not create a consumer Product Definition, UI approval, Activation pass or managed archive merely to edit a skill. Preserve all suites.

For required UI browser checks, prepare dependencies with `npm ci` and `npx playwright install chromium` when missing or changed, then set `PDH_REQUIRE_BROWSER_TESTS=1` and `PLAYWRIGHT_MODULE` to this checkout's `node_modules/playwright`. Reuse only an observed installation matching the current lockfile and Playwright browser revision; do not reinstall it for every task. Linux CI installs Chromium with `--with-deps`. Missing prerequisites must fail required browser verification. Python test dependencies follow the current requirements file.

```text
python -m pip install -r skills/delivery-harness/requirements-test.txt
python skills/delivery-harness/scripts/check_skill_spec.py
python -m pyflakes skills/delivery-harness/scripts skills/product-definition-builder/scripts skills/ui-design-builder/scripts skills/design-system-compiler/scripts
python skills/delivery-harness/scripts/docs_weight.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -v
# or, in parallel with per-module logs: python skills/delivery-harness/scripts/ci_test_shards.py run --suite harness --workers 8
# POSIX shells
HARNESS_GOLDEN_PATH=1 python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v
# PowerShell
$env:HARNESS_GOLDEN_PATH='1'; python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v; Remove-Item Env:HARNESS_GOLDEN_PATH
python -m unittest discover -s skills/product-definition-builder/scripts/tests -v
python -m unittest discover -s skills/ui-design-builder/scripts/tests -v
python -m unittest discover -s skills/design-system-compiler/scripts/tests -v
git diff --check
```

CI retains the same required coverage with exact-candidate jobs and a required aggregate. A successful deterministic suite may be cited from that same exact SHA and unchanged configuration, dependencies and toolchain; retain its origin, do not relabel it as a fresh execution. Changed code, configuration or other relevant inputs require fresh applicable evidence. Only receipt-verified archive A and provider-created tree-equal main S inherit results under `branch-promotion-contract.md`; retain their original SHA and origin, never claim fresh security or CI execution at A/S. Do not repeat the full suite or security review solely for those proved identity transformations. Security freshness, browser/live state and migration checks retain their own contracts. Never cache PASS or waive a missing platform result.

Every flow that promotes to `main` bumps the release version in the same change: `package.json`, `skills/delivery-harness/VERSION`, the README badges and version-history entries in all four languages, and the RUNBOOK `required_harness_version` default. `test_skill_contract.py` reads `VERSION` and fails when any of these surfaces differ from it. A breaking skill-bundle change bumps the minor version. After the release promotion reaches `main`, tag that commit with the matching `v<version>` tag — the READMEs' Releasing section is the full checklist.

Any change that adds or alters a skill, rule, or documented flow also updates the READMEs' descriptive sections in the same change, in all four languages — the README is documentation-of-record, not a release-time artifact.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for one of the 12 keys in the [Authorization Action Ledger](../execution-state-model.md#authorization-action-ledger).
- Any Harness 0.38+ RUN with `integration_push`, non-null `pushed_head_sha`, enabled push grant, or a push lifecycle node; any legacy RUN push that reaches `main` or `development`; or any run whose integration branch resolves to either name.
- Any archive-candidate publication that lacks the owner's exact SHA/branch instruction, fails receipt-bound C-to-A relocation/allowlist verification, uses force, accepts remote drift, or fails to read back exact A. Neither it nor a legacy RUN grant authorizes development or main landing.
- Any source main promotion lacking separate exact branch/SHA authorization, required candidate verification or the repository PR mechanism is blocking. Never force-push, lose task ancestry or delete main. A server-created main SHA requires verified tree equality before tagging or release completion; a different tree is a new candidate. Consumer promotions retain [branch-promotion-contract](../branch-promotion-contract.md).
- Any gate PASS that is not bound to the exact integration head SHA.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.
