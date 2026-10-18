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

## Document Impact

| Source | Affected artifact |
| --- | --- |
| `.github/workflows/harness-ci.yml` | Source CI job selection and `validate` aggregate |
| `skills/delivery-harness/references/governance/source-maintenance.md` | Required Verification |
| Four READMEs | Releasing section |
| `.github/pull_request_template.md` | Verification section |

## Change Log

| Change | Commit | Verification |
| --- | --- | --- |
| Draft PRs run only the Linux jobs and report `validate-draft`; every other run reports `validate` | `7cab027f` | CI gate 14, workflow YAML 2, shard 13 and skill contract 65 tests pass on Windows. The POSIX-only gate test is skipped there; its five scenarios passed through local Git Bash. |
| Three-tier rules in Required Verification, the four READMEs and the PR template | `1282b104` | README structure 5, skill contract 65 and document sync 27 tests pass. |
| Version 0.64.1 | `62592778` | Skill contract 65 and README structure 5 tests pass. |
| Review of `387cc49a..1282b104` | — | GPT-6.1 Sol: PASS, covering correctness and security, with 12 focused tests and 17 gate CLI cases. This PR's own CI is the first live draft-to-ready run. |
| Separate concurrency groups for draft and ready runs | `db3ab897` | On PR #145, a push and the ready mark landed one second apart. The push's draft-mode run cancelled the complete run, and `validate` correctly failed. The two run kinds now use separate groups. CI 42 and skill contract 65 tests pass. |
| Review of `d9481820..2fd5719f` and its fix | `8f5cad74` | GPT-6.1 Sol: FIX_REQUIRED with one P2. The concurrency test only matched text, so a flipped `pull_request` guard still passed. The test now evaluates the group and `cancel-in-progress` expressions for every trigger and checks that the flipped guard merges the draft and ready groups. CI 43 tests pass, and three hand-made workflow mutations each fail the test. |
