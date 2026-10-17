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
