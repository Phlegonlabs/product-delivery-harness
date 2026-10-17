# Verification Tiers

Status: in_progress

## Problem And Baseline

At `d8bc9e20`, the 0.64.0 candidate, every push to a PR ran the full Linux, macOS and Windows matrix in about 10 to 12 minutes. The source rules also asked for the complete matrix locally before a release, so one candidate was verified several times. Each review fix restarted both. Evidence was spread across local logs, worker runs, review runs, commits and Epics.

## Accepted Outcome

Verify source changes in three tiers: focused local checks per task, Linux-only CI for draft PRs, and the full matrix once the PR is ready for review. Review the final candidate once, then only the new commits after a fix. Require a security review only for executable code. Keep one verification summary in the PR. Consumer projects keep their current rules; a separate change covers them.

## Requirements

| ID | Outcome |
| --- | --- |
| VT-01 | Draft PR runs execute only the Linux jobs and report `validate-draft`, which requires exactly those jobs. |
| VT-02 | Ready PR, `main`, merge queue and manual release runs execute every job and report the required `validate` check. |
| VT-03 | Source rules and the four READMEs describe the three tiers and drop the local full-matrix step. |
| VT-04 | Review runs once per final candidate; security review covers only executable code; a tree-equal main SHA keeps the candidate review. |
| VT-05 | The PR template holds one verification table. |
| VT-06 | CI verifies the platforms where the skills run. Linux and Windows run every suite, and macOS is no longer verified. |

## Document Impact

| Source | Affected artifact |
| --- | --- |
| `.github/workflows/harness-ci.yml` | Source CI job selection and `validate` aggregate |
| `skills/delivery-harness/references/governance/source-maintenance.md` | Required Verification |
| Four READMEs | Releasing section |
| `.github/pull_request_template.md` | Verification section |
| `skills/delivery-harness/scripts/ci_test_shards.py` | Windows plans every Harness file |
| `skills/delivery-harness/scripts/tests/test_install_script*.py` | Installer tests split into three files |

## Change Log

| Change | Commit | Verification |
| --- | --- | --- |
| Draft PRs run only the Linux jobs and report `validate-draft`; every other run reports `validate` | `7cab027f` | CI gate 14, workflow YAML 2, shard 13 and skill contract 65 tests pass on Windows. The POSIX-only gate test is skipped there; its five scenarios passed through local Git Bash. |
| Three-tier rules in Required Verification, the four READMEs and the PR template | `1282b104` | README structure 5, skill contract 65 and document sync 27 tests pass. |
| Version 0.64.1 | `62592778` | Skill contract 65 and README structure 5 tests pass. |
| Review of `387cc49a..1282b104` | — | GPT-6.1 Sol: PASS, covering correctness and security, with 12 focused tests and 17 gate CLI cases. This PR's own CI is the first live draft-to-ready run. |
| First live draft run on PR #145 | — | The Linux jobs finished in about 2 minutes, macOS and Windows were skipped, and `validate-draft` passed. |
| Linux and Windows CI instead of macOS | `61c47ef4` | CI 42, skill contract 65 and installer CI 2 tests pass. The Windows planner prints eight shards that cover every Harness file. |
| CI platform description in Required Verification and the four READMEs | `2cc20ba3` | README structure 5 and skill contract 65 tests pass. |
| Installer tests split into three files | `c8f27e34` | An AST comparison shows every test unchanged. The 21 installer tests pass on Windows in 437 s. |
| Version 0.64.2 | `0d45da7a` | Skill contract 65 and README structure 5 tests pass. |
