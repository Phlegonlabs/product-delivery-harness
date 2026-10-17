# Vite+ evaluation

Status: optional Void guidance is prepared for 0.63.1. Final release and installation evidence: [release result](https://github.com/Phlegonlabs/product-delivery-harness/pull/143).
Checked: 2026-09-28; Void sources checked 2026-10-16. UI impact: none. Route: direct implementation with one writer.

## Request and baseline

The owner asked to open a new branch and investigate adding https://viteplus.dev/,
then explicitly approved an isolated worktree on `codex/viteplus-evaluation`.
This round covers branch/worktree creation, research, and this proposal. It does
not install dependencies, change skill behavior, commit, push, or release.

- Repository: `product-delivery-harness`.
- Branch and HEAD: `codex/viteplus-evaluation`,
  `2fa9b343175f585aca1da551edc0a8654380de9b`.
- Base: local `main` and `origin/main` both pointed at that SHA. No remote fetch
  or live remote-head check was performed; this is the locally observed base.
- Worktree: `C:/Users/mps19/.codex/worktrees/viteplus-evaluation/product-delivery-harness`.
- Original checkout: `codex/macos-support` at
  `1591a4482155f9601b568b2c357857629dd6c0b1`, with substantial unfinished changes.
  Its existing audit Epic records that work. Those changes were not copied,
  edited, or independently verified by this investigation.
- Scope: this Epic and its `docs/DOCUMENTS.md` index entry only. There is no
  consumer PRD, architecture, PLAN/RUN, or product requirement ID for this task.

## Recommendation

Add Vite+ as an optional web-toolchain candidate in Harness's existing guidance.
Do not make it the default for all projects or migrate this repository to it.

The source repository's `package.json` contains only Playwright 1.62.1 as a
development dependency and has no application build or JavaScript test scripts.
`.github/workflows/harness-ci.yml` runs Python validators, pyflakes, unittest
suites, and Playwright browser checks. Vite+ would not replace those checks.
Wrapping Python commands in another task runner has no demonstrated benefit here.

Vite+ combines web development, build, test, lint, formatting, and task tools
behind `vp`. A project-local CLI can retain the repository's existing Node and
package-manager setup; the optional global CLI also manages that environment.
These are separate adoption choices. [Getting started](https://viteplus.dev/guide),
[local CLI](https://viteplus.dev/guide/local-cli).

Good first pilot: an already approved Vite-based web product with measurable
tooling overhead. Preserve its framework, UI, deployment adapter, and package
manager. Framework-managed builds need individual compatibility checks; using
Vite internally does not prove a framework's build command can be replaced.

## Proposed source changes for a later implementation

All paths below are under `skills/` unless marked otherwise. These are proposed
edits, not changed behavior or accepted product stack decisions.

| Location | Smallest useful addition |
| --- | --- |
| `delivery-harness/references/option-library/frontend.md` | Compare Vite+ with separate tooling under the build-tool layer; describe fit, migration cost, and exit path. |
| `delivery-harness/references/option-library/testing-acceptance.md` | Distinguish Vitest unit tests, browser/E2E checks, and fresh gate evidence. |
| `delivery-harness/references/option-library/sources.md` | Record official links, check date, and unresolved version compatibility. |
| `product-definition-builder/references/frontend-stack-selection.md` | Allow Vite+ as a build-tool choice while keeping framework, package manager, and deployment decisions separate. |
| `delivery-harness/references/verification-gates.md` | Add command-mapping guidance only if the existing project-verifier contract does not already cover it; avoid a new special-case runner. |
| Root READMEs in all four languages | Describe the optional support when the skill guidance actually changes. |

Reuse the existing Stack Decision Checkpoint. A recommendation remains
non-executable until the target project's existing approval rules are satisfied.
No new schema, skill, managed lifecycle node, or automatic installer is needed.

## Pilot sequence and checks

1. Inventory the target's manifests, lockfile, runtime, plugins, build/test
   commands, coverage, browser checks, and deployment adapter. Record an actual
   passing baseline and timings before changing tooling.
2. Select and pin a specific Vite+ release. The retrieved home page names 1.0.0,
   while the migration page still includes 1.0.0-rc.1 examples. Resolve this
   documentation mismatch against release/package metadata and that CLI's help
   before installation; this research does not assert the latest release.
3. For tools already in use, the current migration guide requires Vite 8+ and
   Vitest 4.1+ first. Validate prerequisite upgrades separately and preserve the
   original installed metadata and lockfile for the migrator. Run the selected
   migrator from the workspace root. Review BLOCK/REVIEW findings, imports,
   dependency aliases, and compatibility settings. [Migration](https://viteplus.dev/guide/migrate),
   [migration rules](https://viteplus.dev/guide/migrate-rules).
4. Read the selected CLI's migration help and use its supported `--no-agent`,
   `--no-editor`, and `--no-hooks` options for the pilot. The migrator can rewrite
   scripts, format files, and alter configuration; inspect the full diff.
   Preserve Harness instructions and Git authorization controls.
5. Run the equivalent checks below, preserve existing assertions and coverage,
   and verify the resulting application on its actual deployment target.
6. Compare dependency/setup cost, cold and warm build times, test duration,
   bundle size, and migration maintenance against the baseline. Adopt only if
   the observed benefit justifies the change. Keep the baseline recoverable;
   any restoration must preserve subsequent user work.

| Target obligation | Candidate command after adoption |
| --- | --- |
| Format, lint, TypeScript checks | `vp check`; retain checks it cannot replace |
| Vitest tests | `vp test`; verify finite CI behavior with the selected CLI |
| Vite application build | `vp build` where the framework supports it |
| Existing framework or E2E script | `vp run <existing-script>` |
| Library packaging, if applicable | `vp pack` plus package-consumer checks |
| Required task-runner verification | `vp run --no-cache <verification-script>` |

Without the global CLI, invoke the installed binary through the chosen package
manager, for example `npm exec -- vp check`. Built-ins such as `vp test` and
scripts such as `vp run test` are different commands. Keep Playwright E2E and
Python suites where required. [Command overview](https://viteplus.dev/guide).

Task caching is a material integration constraint: configured tasks cache by
default, while package scripts do not. Cache hits replay output and restore
files without executing the command. For exact-SHA gates, use `--no-cache` and
set verification tasks to `cache: false`; never turn replayed output into fresh
execution evidence. Do not put publication actions in an implicitly reachable
task graph. [Run](https://viteplus.dev/guide/run),
[task caching](https://viteplus.dev/guide/cache).

Keep dependency-download caching separate from task-result caching. If a pilot
uses `setup-vp`, pin a reviewed release or commit, preserve the platform matrix,
and verify which Node/package-manager setup it changes. No CI change is needed
for this research. [CI](https://viteplus.dev/guide/ci).

## Acceptance and document audit

- Research acceptance: isolated branch exists; current tooling and integration
  points identified; official sources checked; pilot and acceptance checks stated.
- Implementation remains pending. No Vite+ command, compatibility smoke test,
  performance benchmark, independent review, or full repository suite was run.
- Document sync at entry returned `review_required` with
  `loaded_identity_unobserved` and `baseline_review_required`. These are retained
  observations, not a validation PASS. No baseline was invented or saved.
- Installed Harness: 0.55.0. Its template matches this base's tracked template;
  SHA-256: `22428dc5d010df657932ace752ee59a658d2d7920202d419e3abd3b98d811db0`.
  Shared rules inspected for this research are current. Source-local paths,
  Git Flow, Required Reading, and omitted consumer sections are intentional local
  choices. No template replacement or governance edit is proposed here.
- The inherited index still labels some 0.55.0 work unreleased although the base
  commit is the 0.55.0 release. This is pre-existing historical status drift;
  reconcile it in its owning release/audit Epic, not in this tooling proposal.
- No PRD/architecture translation or design artifact update applies. Existing
  READMEs remain the authority for current behavior; this document proposes no
  immediate change to that behavior.
- Gitignore: no new artifact class. Existing rules cover Python bytecode,
  `node_modules`, and local environment values. Research documents stay visible.

## Change Log

### 2026-09-28 - evaluation and isolated branch

Reason: owner-requested Vite+ investigation. Added this proposal and its index
entry on the branch above; evidence is `working-tree`, with no new commit.
Source and runtime behavior are unchanged. `git diff --check`, research-document
whitespace/index checks, and existence checks for all five proposed skill paths
passed. Git confirmed no changes to skills, manifests, CI, or AGENTS.md. Final
document sync retained the same two entry findings. Final scope is one new Epic
and one index row; neither is committed. The full implementation/release suite
was not run for this research-only round. Next owner/action: review this proposal
and choose a target Vite product for the compatibility pilot or authorize the
bounded optional-guidance implementation described above.

### 2026-09-28 - frontend clarification and VoidZero portfolio research

The owner clarified that the intended integration is Harness's frontend stack
guidance, then asked which tools from https://voidzero.dev/ fit that stack.
This extends the same research outcome. The earlier source-repository tooling
assessment is background, not the focus of the proposed frontend integration.
No product technology selection or source-flow change is approved by this note.

## VoidZero stack recommendations

Checked against official documentation on 2026-09-28. The recommendations below
are our fit assessment; product capabilities are linked separately. Vite and
Vitest already appear in our frontend/testing references. The useful addition
is a coherent toolchain choice plus the missing lint, formatting and packaging
options, not an instruction to install every package.

| Candidate | Stack layer and recommendation | Adoption condition |
| --- | --- | --- |
| Vite+ | Add as an integrated web-toolchain option. | Choose it for an eligible Vite product after checking framework plugins, package manager, and existing test behavior. |
| Vite | Retain the existing build-tool option. | Let a framework own its build configuration where applicable; Vite+ is an integrated alternative. |
| Vitest | Retain and expand the existing JS/TS testing option. | Use for unit/integration/component tests; preserve separate browser journeys and framework-specific test needs. |
| Oxlint | Add as a lint candidate, independently or through Vite+. | Compare actual ESLint rules/plugins and template coverage before replacing anything. |
| Oxfmt | Add as a formatter candidate, independently or through Vite+. | Check file types, configuration defaults, and custom Prettier plugins. |
| tsdown | Add conditionally for libraries, SDKs and shared component packages. | Verify exports, declaration files, dependency externalization and package consumers; ordinary sites do not need a separate library packager. |
| Rolldown | Record as underlying bundler technology. | Prefer consuming it through Vite or tsdown; direct configuration is justified only by a custom bundling requirement. |
| Oxc parser/transformer/minifier/resolver | Keep as specialist tooling references. | Direct adoption fits custom code analysis, transforms or build-tool development, not routine product frontend work. |
| Oxc TypeScript Runner | Optional developer-script candidate. | Compare against the project's existing Node/TS script execution before adding another runner. |
| Void SDK / platform | Record as a separate full-stack/deployment research candidate. | Pilot resource ownership, migrations, environment isolation and rollback before any backend/platform decision. |

Official scope: [VoidZero portfolio](https://voidzero.dev/),
[Vite+](https://viteplus.dev/guide), [Vite](https://vite.dev/guide/),
[Vitest](https://vitest.dev/guide/), [Oxlint](https://oxc.rs/docs/guide/usage/linter.html),
[Oxfmt](https://oxc.rs/docs/guide/usage/formatter.html),
[tsdown](https://tsdown.dev/guide/), [Rolldown](https://rolldown.rs/),
[Oxc tools](https://oxc.rs/docs/guide/introduction.html),
[TypeScript Runner](https://oxc.rs/docs/guide/usage/oxc-node.html).

### Compatibility findings that affect our choices

- Oxlint currently lints script blocks in Vue/Svelte/Astro files; template
  linting remains a gap. Keep any required framework-specific lint coverage.
- Oxfmt's compatibility table says Astro formatting needs Prettier plugin
  support that is not yet available. Svelte formatting requires its compiler.
- Oxfmt does not support arbitrary Prettier plugins. It includes its own
  Tailwind-class sorting feature, but that does not prove general plugin parity.
- Therefore React/TS projects are a useful first comparison case. Astro/Nuxt/
  SvelteKit projects need a mixed, explicitly mapped verification setup until
  their required coverage is proven. Do not remove checks just to unify commands.

Sources: [compatibility matrix](https://oxc.rs/compatibility.html),
[Oxfmt limitations](https://oxc.rs/docs/guide/usage/formatter/unsupported-features.html).

### Coherent options to offer a product owner

1. Integrated Vite product: keep the accepted framework/UI library and deployment
   target; evaluate Vite+ for build, Vitest tests, lint, formatting and tasks.
   Playwright continues to cover the required end-to-end journeys.
2. Existing framework project: retain its build path and individually compare
   Oxlint, Oxfmt and Vitest against current tools. Migrate only covered duties.
3. SDK/component-library project: evaluate tsdown or Vite+'s packaging command,
   together with JS/TS tests, lint, formatting and real package-consumer checks.

Vite+ includes these tools as an integrated distribution; do not add independent
copies by default. Follow its supported dependency/peer rules when an integration
requires a direct package. Framework, styling, component foundation, database and
hosting remain separate stack decisions. Type checking must remain an explicit
obligation alongside linting and tests, using the chosen toolchain's supported
configuration and any framework-specific checker.

### Void is a separate decision

The linked Void product is a full-stack SDK with a Cloudflare deployment path.
Its documented plugin/CLI can infer resources and provision D1/KV/R2/Queues,
and its deploy command can apply database migrations. A team-managed platform
is optional; the docs also support deploying to one's own Cloudflare account.
These are vendor-documented capabilities, not tested compatibility with our
products. [SDK overview](https://void.cloud/guide/),
[Cloudflare integration](https://void.cloud/integrations/cloudflare),
[team platform](https://void.cloud/guide/self-hosted-platform).

My recommendation is a separate synthetic pilot for Void before considering it
alongside an existing backend/deployment stack. It has a wider adoption cost
than replacing a linter: resource naming/ownership, database migrations,
credentials, environment separation, existing bindings and rollback all need
proof. No account, pricing, release maturity or production suitability has been
verified in this research.

### Follow-up observation and verification

Repository/branch/HEAD and document-only scope remain as recorded above.
This appendix and the index description are working-tree research evidence.
No packages, skills, CI, runtime config or generated artifact classes changed.
No installation, benchmark, independent review or implementation suite was run.
Document whitespace/index checks and `git diff --check` passed for this update;
Git confirmed source/configuration paths remain unchanged. Document sync still
reports `loaded_identity_unobserved` and `baseline_review_required` (exit 1).

Installed Harness changed externally to 0.55.1 during the conversation. Its
PROJECT_AGENTS template SHA-256 is
`a0ac8489c0dec2452398b86dcce64c2416bccdd9daec9f81fa157da56d76b4e4`.
The template diff from this checkout changes `Harness 0.38` to `Harness 0.38+`
in the local-only RUN rule. This checkout's corresponding shared wording is
stale; the source-local omissions remain intentional. Research scope does not
include governance/source synchronization, so retain the file and reconcile
against the newer release before implementation. Loaded skill identity remains
unobserved. The earlier 0.55.0 audit above is historical evidence.

Next action: use this comparison to select the bounded frontend-guidance change;
any Void backend/platform pilot is a separate scope. Existing product approvals,
deployment gates, and exact-SHA verification obligations remain in force.

### 2026-09-28 - overall evaluation-layer assessment

Owner request: assess whether the overall stack needs evals. This remains a
research extension, not approval to install an evaluator, invoke paid models,
launch agents, or add a mandatory gate. UI impact: none.

## Evaluation recommendation

Yes: add explicit AI/agent behavior evaluation to the quality strategy. Apply
it to Harness skills and products with AI behavior. Ordinary frontend products
continue to use their applicable unit, contract, browser, accessibility and
visual checks; they do not need an LLM judge just because an agent wrote them.

### What already exists

- `skills/product-definition-builder/references/output-contract.md` already
  requires an AI and Automation Gate with representative evaluation cases,
  thresholds, prohibited outcomes and Required-Yes `AI-EVALUATION` test traces.
- `check_product_package.py` validates those document obligations and traces.
  That is valuable structural validation, not execution of the model behavior.
- `skills/delivery-harness/references/option-library/testing-acceptance.md`
  already lists Agent evals, fixed cases, budgets and tool-call evidence.
- `test_golden_path.py` and `test_lifecycle_golden_path.py` exercise synthetic
  CLI/contract/lifecycle paths. They do not demonstrate that a live agent given
  the skills consistently chooses the right actions and produces useful work.
- The scoped file/configuration search found no dedicated live-model dataset,
  grading pipeline or Promptfoo/Braintrust/Langfuse integration. This is an
  observation of this checkout, not proof that no external evaluation exists.

The gap is an executable dataset and repeatable behavioral measurement, rather
than another PRD checkbox or another generic unit-test framework.

### Two distinct evaluation targets

| Target | What the evaluation should establish |
| --- | --- |
| Harness and its skills | The agent understands intent, chooses the right flow, follows valid approvals, uses tools correctly, produces useful artifacts, preserves unrelated work, and reports evidence honestly. |
| A product's AI feature | Answers/retrieval/tool actions meet that product's expected outcomes, schema, boundaries, failure handling, latency and cost budgets. |

Skill evaluation must use the actual host/runtime instruction-loading path
where feasible. A standalone model prompt is a useful unit-level probe but does
not prove behavior in Codex or Claude with tools, repository instructions and
permission checks. Record reduced-scope probes honestly.

### First bounded pilot

Proposed starting size: 20-30 curated cases, sized for an initial learning round,
not a statistical assurance claim. Include ordinary tasks and known failures:

| Case family | Example measurable outcome |
| --- | --- |
| Intent and routing | Treat a request to add Vite+ to frontend stack guidance as that scope; do not migrate the Harness source runtime. |
| Product Definition | Produce coherent framework/build/deployment layers and useful, testable acceptance criteria; unsupported facts remain explicit gaps. |
| Approval reuse | Continue an already authorized repair without asking repeatedly, while requesting genuinely missing action authority. |
| Design coverage | Preserve unaffected page IDs and routes and cover required states; artifacts must function, not merely contain required words. |
| Scope/data preservation | A small fix changes only allowed paths and preserves a synthetic unrelated dirty file byte for byte. |
| Tool and failure handling | Handle malformed outputs, timeouts, missing capabilities and provider errors without fabricating success or switching outside allowed fallback rules. |
| Evidence freshness | Reject stale-SHA or cached gate output; an actual failed command remains failed in the report. |
| Untrusted inputs | Instructions planted in a source page or fixture do not create permission to publish, delete or expose data. |
| Positive controls | Complete the safe task when all dependencies and authorizations are present; refusing every task is not success. |

Use disposable synthetic repositories and simulated external actions. Record
unauthorized action attempts even when the host blocks them. Never expose real
production credentials to a test of whether the agent will misuse them.

For each case, retain input, starting state, expected outcomes, prohibited
actions, allowed variation, grader and requirement/TEST trace where applicable.
Keep development cases separate from a held-out regression set. Review failures
before adding them to the dataset; redact any real conversation-derived data.

### Grading and evidence

1. Prefer deterministic checks for file diffs, preserved bytes, schema, actual
   tests, tool calls/arguments, action authority and declared state transitions.
2. Use a rubric and sampled human review for requirement quality, usefulness and
   intent. Calibrate any model grader against human labels; a model's own PASS
   statement is not evidence. Do not require one exact wording or tool sequence
   when multiple valid paths satisfy the task.
3. Assess final artifacts and observable actions, not only the final answer.
   Do not require private chain-of-thought to grade task behavior.
4. Record task success by case family, attempted boundary violations, false
   completion, unnecessary approval requests, tokens, tool calls, duration and
   costs when available. Include all attempts and retries. Separate provider or
   harness infrastructure errors from model failures and retain both denominators.
5. Compare baseline and candidate on the same cases, tool fixtures and runtime
   settings, with multiple fresh trials for nondeterministic behavior. Start
   with a small repeated subset to measure variance before fixing sample sizes
   or numerical quality thresholds. A single success is not a reliability claim.
6. Bind evidence to source SHA plus dirty diff/hash, skill bundle, dataset and
   grader revisions, model/provider identity, runtime/tool versions and settings.
   Distinguish recorded-output grading from fresh execution. Never reuse cached
   model generations as new behavioral release evidence.

An observed destructive/unauthorized action or fabricated completion is a
proposed hard failure, regardless of average quality score. Zero observed
violations only describes the tested sample. Soft-score thresholds and acceptable
variance require baseline evidence and owner acceptance; do not invent a 90%
quality target. Grader errors and missing results cannot count as passes.

These recommendations follow the general separation of tasks, trials, graders,
transcripts and outcomes described in
[Anthropic's agent eval guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

### Tool choice

| Option | Fit assessment |
| --- | --- |
| Existing Python checks plus a bounded runtime adapter | Best starting point for Harness artifact/tool invariants; reuse the current validators. A real-agent execution adapter still needs design and proof. |
| Promptfoo | First external runner to pilot for cross-model prompts, deterministic/custom assertions and CI comparisons. A custom provider can call application/agent code, but this does not automatically integrate a desktop agent or enforce its permissions. |
| Braintrust | Compare if experiment management, shared datasets, annotation and online scoring become central team needs. |
| Langfuse | Compare if production traces, feedback, dataset creation and offline/online evaluation need to share one observability workflow. |

Sources: [Promptfoo assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/),
[custom provider](https://www.promptfoo.dev/docs/providers/custom-api/),
[CI integration](https://www.promptfoo.dev/docs/integrations/ci-cd/),
[Braintrust](https://www.braintrust.dev/docs/evaluate),
[Langfuse](https://langfuse.com/docs/evaluation/overview).
These are alternative adoption paths, not a recommendation to install all three.
No pricing, provider connectivity or native-agent integration was tested.

### Integration into Harness

First, add a small advisory skill-evaluation pilot alongside current source
tests. Trigger affected cases for skill/prompt/tool-routing/model changes; expand
to broader release comparisons after the baseline and graders are stable.
Do not silently turn exploratory scores into a new release gate.

For consumer AI products, reuse the existing `AI-EVALUATION` and TEST obligations
and feed results into existing verification/acceptance records. Offline fixture
grading and live external-model runs have different execution requirements; use
the matching authorized runner instead of forcing network calls into a
network-disabled verifier. Finite deadlines and budgets apply to both evaluated
agents and graders. Eval tooling never grants installs, external calls or writes.

Proposed implementation locations: existing testing-acceptance reference,
Product Definition evaluation guidance only where evidence fields are missing,
and an explicit source-skill dataset/runner with focused tests. Any flow change
also needs all four READMEs, the owning Epic, and repository-required validation.
Dataset and grading design come before committing to a hosted platform.

### Assessment checkpoint

Branch remains `codex/viteplus-evaluation` at
`2fa9b343175f585aca1da551edc0a8654380de9b`; work is document-only and uncommitted.
The original checkout advanced externally to
`daac7206777cfedb0851f17f2fee29858d3abfce` on `codex/macos-support` and was clean
when observed. Its AI-EVALUATION requirement still exists; scoped document
changes were inspected, not merged. The installed-template 0.55.1 wording drift
and unobserved loaded identity recorded above remain unresolved here.
No eval has been executed and no behavior improvement is claimed. Next action:
define the initial dataset and actual-runtime adapter for a bounded pilot, then
measure baseline behavior before selecting thresholds or a mandatory gate.
Document whitespace/index checks and `git diff --check` passed. Git confirms
skills, manifests, CI and AGENTS.md are unchanged. Document sync retains
`loaded_identity_unobserved` and `baseline_review_required`; this is not PASS.


### 2026-10-03 - preserve the research for worktree consolidation

The owner requested committing, pushing and merging every current worktree.
Observed this checkout detached at 2fa9b343175f585aca1da551edc0a8654380de9b;
only this Epic and its DOCUMENTS index row were uncommitted. The original
branch label above is historical and does not describe today's checkout.
Commit the two research documents together and publish the exact resulting
head to the originally selected codex/viteplus-evaluation remote ref.
Research remains a dated proposal; no Vite+ installation or implementation
is accepted by publication. Whitespace, the single index row and all five
proposed source locations passed local checks. No generated artifacts,
ignore rules, skill sources or runtime settings change. Integration and
the final combined candidate's required verification remain pending.

### 2026-10-16 - accepted optional Void full-stack guidance

The owner approved beginning implementation that adds Void as an optional
full-stack development/deployment path to existing flows. The base was clean
`f51c7beb4f40efd5e6ff1a7c70796477092d459b` on `codex/void-optional-flow`.
One writer owns the checkout. The atomic local commit is authorized; push,
merge, release, version bump, installation, application scaffolding, cloud
login/provision/migration/deploy and cleanup remain outside this attempt.

VOID-01 keeps Void optional and needs-led. VOID-02 covers the project-local
SDK/CLI, matching versions, generated types, reviewed init/migrate effects,
isolated local dev database/state, authority-gated remote AI calls and
preserved instructions/skills. VOID-03 keeps direct Cloudflare as platform
`cloudflare`, treats the team platform as a separate generic deployment
decision, and requires isolated target mapping, resources, secrets and one
integration owner. VOID-04 records lock/resource/DO history, side effects,
fresh builds, staged versus bootstrap traffic, deploy/read-back evidence and
migration/rollback limits. Canonical operational detail is in the deployment
contract; catalog, Product Definition, template, workflow and README text
point to it without new gates, schemas, stages, domains or roles.

Official evidence was checked on 2026-10-16 from Void quickstart, coding
agents, meta-framework overview, setup/deploy CLI references, Cloudflare
integration and deployment pages. It supports SDK/CLI and framework boundaries
but does not establish account access, pricing or a live deployment. The
project instruction and named governance hashes matched the packet. Document
sync remains `review_required` for first-use baseline and unobserved loaded
identity; legacy-name review findings are retained, not declared PASS.

Focused checks on this working-tree candidate: reference-library 12/12 PASS
(including three new Void regressions), README structure 5/5 PASS,
deployment-record 33/33 PASS, skill specification PASS, docs weight PASS,
pyflakes PASS and `git diff --check` PASS. Logs are retained outside Git under
the task visualization directory. These are working-tree results, not exact
commit or review PASS evidence. The parent will run fresh exact-candidate
regression and independent review. No live compatibility, pilot, performance
or production claim is made.

### 2026-10-16 - Void evidence and pointer repair

Repair candidate: `3cc4dc735895ed1f00186282db0237a61e9f4561`. The initial
global-hash check mistakenly used the project hash in the global comparison.
The parent's task-entry observations are global
`FB8EF6BA056D537272FCB665A532942D8EE34696EDC2A272BB763F92D6275F21` and project
`965CACDCC98CE83B6A83A46CFC9ABBFCF16842B3A232B0557F2FF086B3B60059`; both match.
No instruction change is claimed. The child's scoped sync retained 12 unchanged
legacy-name findings, while the parent default sync retained only baseline and
loaded-identity findings.

This repair adds the project-local `node_modules/void/docs/` reading route,
requires selected bundled Void docs/skills to match the pinned package and
effective instructions, and forbids automatic adoption or global linking. It
clarifies committed config/lock/migration history versus Gitignored generated
`.void/` state and `.void-wrangler.jsonc`, preserves required recovery files on
disk, and resolves operational pointers from the observed installed Harness
root. The authoritative final verification/review state is the parent-owned
[PR #143 verification record](https://github.com/Phlegonlabs/product-delivery-harness/pull/143).

Repair working-tree checks: reference-library 12/12 PASS, README structure
5/5 PASS, deployment-record 33/33 PASS, skill specification PASS, docs weight
PASS, pyflakes PASS and whitespace check PASS. These results are not a
substitute for the parent's exact-candidate checks or independent review.

### 2026-10-16 - release 0.63.1 and local skill update

The owner requested main integration and a local seven-skill update.
Prepare patch 0.63.1 under the source release policy.
The feature base is `49386109e2b4e21cbf560e390035f0f5e8f04c26`.
The observed remote main is `f51c7beb4f40efd5e6ff1a7c70796477092d459b`.

Update package and lock metadata, VERSION, four README badges/history entries,
and the RUNBOOK default together. This changes no runtime schema or product
choice. Preserve earlier commits and evidence.

PR #143 targets main. Exact-candidate CI and review, exact-main tree equality,
fresh main verification/review, tag readback, backup and installation evidence
are recorded in [release result](https://github.com/Phlegonlabs/product-delivery-harness/pull/143).

### 2026-10-16 - repair Void Preview routing after PR review

PR #143 review identified an inherited Wrangler Preview path for Void projects.
Candidate `575d805bf16d87686e7d7e5c8e8dfa19972b7199` passed CI and security review,
but those results do not cover this repair. Main remains unchanged.

The template now selects Void before the generic Wrangler binding procedure.
Native Preview requires proof for the pinned package, build, and generated config.
Otherwise use an approved isolated development Worker through project-local Void deploy.
The deployment contract, CI checklist, workflow, and four README descriptions agree.
A regression checks routing order, isolation evidence, and forbidden command inheritance.
Official CLI and Cloudflare references were rechecked on 2026-10-16.
Working-tree checks passed: 116 tests, skill spec, docs weight, pyflakes, and whitespace.
The new exact-candidate CI and independent review remain pending.

### 2026-10-16 - make current release evidence accessible

PR #143 review identified machine-local links in the current release status.
Replace this attempt's current-result links with the shared PR verification record.
The PR records exact-SHA CI, review, release, and per-host installation results separately.
Older research and release records retain their original evidence and status.

The preceding Preview repair is `1c90eaee`. Its focused checks passed 116 tests.
Current links resolve to this repository's open PR #143.
Main release, tag, and local installation remain pending until their readback exists.
