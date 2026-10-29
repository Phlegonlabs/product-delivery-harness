# Eval Acceptance

Use the PRD's approved `eval-policy/1` from
`../../product-definition-builder/references/eval-policy-contract.md`. No fixed
global pass rate. Ordinary products retain deterministic TEST acceptance.

`eval-contract/1` has exactly `schema`, `prd_sha256`, `policy_sha256`, `quality`,
`handoff`, `delivery`. The last three fields equal PRD policy field-for-field;
`policy_sha256` hashes UTF-8 JSON with sorted keys, no extra separators and
`ensure_ascii=False`. It introduces no alternative thresholds. Start from
`EVAL_CONTRACT.template.json`; placeholders intentionally fail.

Two independent full runs at candidate H1 produce self-contained
`eval-report/1` files: `quality` and `handoff`. The latter comes from another
clean checkout following the delivered runbook. Register each file directly
under its required TEST/scenario in `delivery-results/1`; nested trace references
never widen H1/H2's allowed paths. Preserve failed reports separately under
existing authority. Do not silently replace trials or report only best-of-N.

## Report

`EVAL_REPORT.template.json` is a failing scaffold. Exact fields are `schema`,
`purpose`, `run_id`, `candidate_sha`, `contract_sha256`, `prd_sha256`,
`policy_sha256`, `started_at`, `finished_at`, `execution`, `artifacts`,
`provenance`, `trials`, `usage`. IDs differ between runs. Execution equals its
frozen delivery scenario. Artifacts maps every approved input and delivered
runner/grader/lockfile/runbook path to its exact SHA-256 at H1.

Provenance contains exactly `executor`, `job_id`, `checkout_sha`, `git_status`,
`setup`, `full`, `dependency_readbacks`. Both command receipts have `argv`,
`exit_code`, `observation`; record approved commands, actual exit 0 and captured
redacted output. Status is empty at exact H1. Readbacks map every declared
mutable dependency to `{identity, checked_at, observation}` during execution.
Freshness uses the checker clock and approved age; report writers cannot set it.

Each trial has exactly `case_id`, `trial_index` (1-based), `status`, `scores`,
`assertion_results`, `observed_subject`, `observed_grader`, `duration_ms`,
`usage`, `redacted_output`, `grading_observation`, `tool_observations`, `failure`.
Only `completed` counts as valid execution. Scores cover every rubric dimension
with in-range integers. Assertions cover every prohibited check with `pass` or
`fail`; any fail rejects acceptance. Critical trials all meet rubric minima.
Retain output, judge rationale, tool/end-state readbacks and quality failure
observations inline. Tool-free cases state what was permitted and observed.
Never include credentials, raw private records or heldout answers in subject logs.

Usage has `calls`, `cost_microunits`, `currency`, both per trial and per report;
totals recompute and obey policy limits. Runner enforces deadlines and budgets;
checker validates recorded duration, dates and spending. Review verifies truth.

## Arithmetic And Assertions

For `case_all_trials`, a case passes only when every planned trial meets rubric
minima. For `trial_pass_rate`, count each planned trial. Compare integers:
`passing * denominator >= population * numerator`. Failed quality samples stay
in the population. No rounding or excluded failures. Slices use frozen membership
and their own minima; overlaps never inflate the overall denominator. Missing,
duplicate, extra, skipped, timeout, error or malformed trials invalidate the run.

The quality scenario requires `eval-inputs-match`, `eval-complete`, `eval-rate`,
`eval-slices`, `eval-critical`; handoff requires `eval-handoff`. All assertions
and required functional scenarios still PASS. Both full reports independently
recompute quality. A self-written summary, `handoff_ok` flag, or consistent hash
cannot prove execution. Independent review inspects executor receipts, sample
coverage, judge calibration, tool outcomes and actual clean-checkout provenance.

## Exact Evidence Gate

```text
python "<delivery-harness-skill-root>/scripts/check_eval_acceptance.py" --repo-root . --prd docs/product/PRD.md --prd-sha256 <frozen-prd-hash> --contract docs/verification/eval-contract.json --contract-sha256 <frozen-eval-hash> --delivery-contract docs/verification/delivery-acceptance.json --delivery-contract-sha256 <frozen-acceptance-hash> --results docs/verification/delivery-results.json --candidate-from-head
```

Expected hashes come from the parent-frozen source rows or direct task record,
never reports. The checker resolves reports from the registered policy scenarios;
callers cannot substitute a passing report. It checks the existing acceptance
contract/register, assertion IDs, safe bounded input reads and exact Git blobs.
It never executes project commands, writes reports or supplies credentials.
Exit 0 means both eval obligations pass structurally; exit 1 means failed/invalid
evidence; argument errors exit 2. It is not a release or provenance certification.

Before H1, set `-text -filter` for actual frozen inputs, contracts, delivered
artifacts, register and evidence paths. Confirm effective attributes and exact
bytes in HEAD. Primary and independent clean-checkout full runs execute at H1;
only the parent adds directly listed reports and register as evidence child H2.
Run this checker before the unchanged delivery-acceptance gate at clean H2.
It resolves HEAD once, verifies source/report bytes, H1 ancestry and the existing
evidence-only change allowlist, then rechecks HEAD and clean status. Frozen
PRD/contracts, approved inputs and delivered artifacts must match regular blobs
and Git modes at H1, even if directly registered as evidence. A literal-path
tree diff rejects mode, type, content or existence changes in those paths.
Changes or additions after H1
require a new candidate and full runs. No transitive trace exemption is added.

Deliver `docs/verification/EVAL_RUNBOOK.md` filled with setup/full/quick commands, versions,
credential variable names, limits, readbacks, heldout protection, failure replay,
cleanup authority/exact owned IDs, and candidate/policy change rules. A quick
subset is diagnostic only. Independent handoff captures setup and full command
receipts, not a `handoff_ok` flag. Review verifies the receipts' actual origin.
After H2, managed repairs use the existing formal revision protocol; old reports
and approvals remain historical evidence.

## Readiness And Compatibility

RUN pins >=0.60.0 require an explicit PRD applicability declaration, including
reasoned ordinary-product `not_required`. A present marker opts in under older
pins and plan-only validation too. Absent markers in older pinned plans keep
their historical checks. This is a new contract boundary, not an auto-migration.
Extra reference rows or legacy PRD kind aliases cannot suppress marker adoption;
multiple declared policies fail as ambiguous authority.
Policy absence must be observed from a safe, bounded authority read. Unreadable,
oversized, secret-like or linked PRD authority returns a gap even on old pins;
it never means `not_required`. Non-frozen reference-only archive rows are not
authority. No permissive fallback reads credentials or follows links.
Before parsing either presence or absence, those bytes must match the row's
frozen `content_sha256` and any full `source_revision` regular Git blob.
The same bounded bytes are hashed against Git metadata; no divergent revision
or working copy can decide applicability. A missing hash is an authority gap.

Applicable PLANs freeze one canonical `eval contract` source at
`docs/verification/eval-contract.json` and one `delivery acceptance` source at
`docs/verification/delivery-acceptance.json`, with hashes and optional full
source revision. Required final gates are `eval-acceptance`, `delivery-acceptance`
and `final-closeout`. The first two directly invoke absolute installed checker paths
with the absolute Python executable observed by readiness (same resolved path),
with exactly the frozen paths/hashes, default register and `--candidate-from-head`,
`cwd: .`, `pass_signal: exit 0`, explicit `execution.isolation: host`, and
omitted/always selection. The host Git checkout and installed skill paths must
share one filesystem namespace; an archive-only container snapshot cannot supply
this proof. No shell wrapper
or caller-selected passing checker substitutes for them. Bare `python`/`python3`
cannot select a project executable or another interpreter through PATH.

Each final gate has one `local_command` verifier node. Pass-only unbounded
dependency paths run every broad final check -> eval-acceptance ->
delivery-acceptance -> final-closeout. Readiness rejects missing/disconnected
nodes, wrong argv/hash/source kind, selected-away gates and changed approved
inputs. The common source join applies before Product/UI early returns, including
transitions and closeout. RUN continues to store normal exact-SHA verifier
execution evidence; no eval rows or scheduler are added.
