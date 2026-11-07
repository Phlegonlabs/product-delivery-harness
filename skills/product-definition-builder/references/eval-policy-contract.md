# Evaluation Policy

New packages run the package checker as [Workflow step 15](stages/product-definition.md#workflow)
states. Its `--repo-root` enables approved-input byte checks; a call without it
inspects shape only and cannot complete the new-package approval/publication flow.
Legacy calls may omit `--eval-policy` and the marker; a present marker always validates.
Never migrate historical approvals automatically.

Record one `<!-- eval-policy:start -->` / `<!-- eval-policy:end -->` pair in
PRD's `## AI and Automation`, outside the approval block. Its body is a JSON
object inside a `json` fence, keeping every field visible in rendered review.
Before the body, use LF/CRLF/CR line endings and ASCII space/tab blank lines;
Unicode separators and padding cannot masquerade as Markdown boundaries.
Unicode inside JSON strings stays unchanged.
The existing product approval digest
covers these bytes. Derived delivery contracts cannot replace this authority.
Overlapping or malformed approval boundaries fail validation; approval-excluded
bytes cannot carry policy authority.
The parser checks the actual raw digest exclusion, including hidden markers;
active Markdown placement alone cannot prove approval coverage.

An ordinary product without eval needs records exactly `schema: eval-policy/1`,
`applicability: not_required`, concrete `reason` and human `owner`. Required AI
cannot waive eval. Non-AI products may opt in. No universal threshold is supplied.

## Required Policy

| Exact field | Contract |
| --- | --- |
| `schema`, `applicability`, `reason`, `owner` | `eval-policy/1`, `required`, concrete reason and human owner |
| `quality`, `handoff` | Each `{test_id, scenario_id, report}`; `scenario_id` is the `<TEST-ID>/<slug>` of a feature-file scenario tagged with that TEST, and the package checker verifies it when feature coverage runs; distinct Required-Yes TESTs and reports; AI packages trace both to `AI-EVALUATION` |
| `dataset`, `rubric`, `grader`, `subject` | Each `{path, sha256}` for approved files; relative POSIX paths and lowercase hashes; no secrets or links |
| `metric`, `trials_per_case`, `minimum_rate` | `case_all_trials` or `trial_pass_rate`; integer repeats; rate `{numerator, denominator}` with positive denominator and numerator within it |
| `slices` | List of `{id, minimum_cases, minimum_rate}`; membership from dataset only; overlap allowed, empty/undersized slices fail |
| `critical_rule`, `retry_policy` | Exactly `all_trials_pass` and `none` |
| `freshness` | `{max_age_seconds, dependencies}`; positive age and map of mutable dependency IDs to expected identities |
| `limits` | `{trial_timeout_ms, run_timeout_ms, max_calls, max_cost_microunits, currency}`; integer limits, positive timeouts, explicit three-letter currency |
| `delivery` | `{runner, grader, lockfile, runbook, setup_argv, full_argv}`; paths and nonempty argument arrays; full command names the runner |

Freeze dataset/rubric/judge/subject before approval. Runner, grader code,
lockfile and runbook bytes bind later to tested candidate H1; they need not
exist at Product Definition time. No digest cycle is introduced.

Approved inputs use new immutable repository-relative paths outside
`.prd-staging`, for example `evals/inputs/<revision>/`. Record exact paths and
their creation authority in the existing task/Epic before writing; reuse an
existing grant and resolve only a concrete missing grant. Never overwrite a
file bound by a live or historical policy. A changed input uses a new path.
These paths stay the same through validation and Markdown publication. Include
the prepared paths, hashes and creation authority in the step-20 publication
mutation list; content approval never grants a missing filesystem action.
Retain superseded inputs at their approved paths. Moving or deleting them needs
separate authority; do not put them in the core-document archive move set.

## Approved Input Files

Dataset is UTF-8 JSONL. Each row has exactly `case_id`, `split`, `slices`,
`critical`, `input`, `expected`. IDs are unique; split is `development` or
`heldout`; critical is boolean; slices contain unique declared IDs; input and
expected are concrete redacted text. Every row counts in acceptance. v1 limits
the population to 100,000 planned trials. Keep non-acceptance development data
in a separate file. Review data rights and representativeness; heldout answers
never enter the evaluated subject's context.
Approved content and command arguments may contain JSON, markup and long prompts;
placeholder checks apply to decision prose, not the data being evaluated.

Rubric has exactly `schema: eval-rubric/1`, `dimensions`, `prohibited_assertions`.
Each dimension is `{id, minimum, maximum, passing_score, anchors}`: integer
scores 0..100 with a concrete text anchor for every score. Assertions map stable
IDs to observable prohibited-outcome checks. Any prohibited outcome fails the
gate even when aggregate quality meets its threshold.

Grader definition has exactly `schema: eval-grader/1`, `kind` (`deterministic`,
`human` or `model`), `identity`, `instructions`, `calibration`. Freeze judge
identity/version, prompt/configuration and calibration rationale. Subject has
exactly `schema: eval-subject/1`, `identity`, `configuration`. Keep subject and
judge separate; these files contain no credentials. Human/model judgments and
calibration still need semantic review.

Quality failures stay in the denominator. Missing, duplicate, extra, skipped,
timeout or grader-error trials invalidate execution. No best-of-N replacement:
retry means a fresh full run and new run ID; preserve failed reports. Policy or
approved-input changes use the existing approval flow. Checkers prove structure,
hashes and TEST joins; reviewers verify anchors, protected data and provenance.
