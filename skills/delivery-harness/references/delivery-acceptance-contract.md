# Requirement-To-Evidence Acceptance

Use this contract on new delivery work, both direct and managed. It supplements the existing PRD checker, PLAN/RUN joins and security/UI gates; it does not replace their authority or alter legacy RUN schemas. `test-fixture-lifecycle.md` defines setup, execution, observation and teardown. `bounded-enhancement.md` defines repair budgets and honest next-round handoff.

## Freeze Expectations Before Results

Product Definition owns PRD requirements and required TEST IDs. First run its full approved-package checker to prove Must/NFR and gate coverage. The Harness then freezes the concrete scenario matrix derived from those obligations: TEST ID, scenario identity, platform/device/OS, authentication mode, environment, build/configuration identity, initial persona/data, observable assertions and external dependency mode. A primary journey needs complete user-to-data proof in addition to unit/integration checks; not every requirement needs an expensive UI test.

When the PRD Browser Targets table names a non-Chromium engine, freeze one web scenario per browser combination. Each combination pairs one release target, one smoke TEST ID and one engine. Chrome and Edge map to `chromium`, Firefox maps to `firefox`, and Safari on macOS or iOS maps to `webkit`. Record that identity in the scenario's `execution.browser` field. A Chromium-only or undeclared PRD adds no browser scenarios.

Retain the executable contract separately from the result register. Bind its SHA-256 in the accepted plan or direct-task scope record before execution. The acceptance CLI's expected contract hash comes from that parent-observed authority, never from the result file itself; its candidate is a parent-observed SHA or is proven against the checked-out head in Git. A result writer cannot remove a required platform, relabel real auth as mock, weaken an assertion or edit both expectation and result to obtain PASS. A changed expectation needs the original scope decision checked again, not a silent hash refresh.

For managed work, freeze the contract as an additional PLAN source and declare `check_delivery_acceptance.py` as an always-run final gate with a matching verifier graph node between the final check and closeout. The existing verifier runtime records its execution key in RUN; link the register rather than copying its result rows into a competing RUN schema. Direct work runs the same CLI without PLAN/RUN. Gate-authoring review must reject a missing acceptance verifier; this is not automatic retroactive migration of old plans.

## Execute And Retain

### Check At The Right Boundary

| Boundary | Required work |
| --- | --- |
| Atomic task | Focused positive, negative and security checks for the changed behavior. |
| Mission integration | Exact-head diff review and affected cross-layer checks. |
| Fixed release candidate | Complete declared acceptance matrix, fresh independent security review and required regression/UI checks. |
| Deployment | Actual build/configuration/account/environment read-back and authorized production-safe smoke. |

Freeze coverage before execution. Share fixture setup only where ownership, isolation and cleanup remain explicit; retain a separate result for every required scenario. Collect result fields from actual runner output and review the underlying assertions. A generated register or a shared setup never replaces execution evidence.

Reuse only evidence allowed by the existing exact-candidate contract and `runtime-performance.md`; retain the original execution identity. Do not rerun a passing deterministic check merely because a second document links it. Do not relabel an old result with a new SHA. The H1-to-H2 evidence-only proof below remains the narrow acceptance rule, not a general exemption from fresh security, browser, live-state or migration checks. A new candidate, changed expectations, dependencies, configuration or toolchain requires the applicable checks again.

Independent security review may run alongside resource-safe deterministic regression after the candidate is frozen. Keep that checkout unchanged until both finish. A repair invalidates the review and affected gates; finish or stop owned jobs before starting the next candidate. No new reviewer is needed just to repeat the same complete exact-SHA verdict, but missing coverage or changed inputs require a new review.

For an applicable PRD `eval-policy/1`, also use `eval-acceptance-contract.md`. A quality TEST owns the rate/slice/critical assertions; a distinct handoff TEST owns the independent clean-checkout full report. Every required scenario still passes. Both reports are directly listed evidence, with the existing H1/H2 allowlist and parent write boundary unchanged. Deliver the runner, grader, lockfile and filled eval runbook.

- Run actual project-specific setup and test commands under exact existing authority. These checkers inspect records; they never provision accounts, run a browser/simulator, invoke tools, deploy, or supply credentials themselves.
- Keep mock, real-sandbox, and production-smoke claims separate. Real-login obligations exercise the actual test authentication boundary. Native obligations require the actual native artifact and device/OS evidence; unavailable runners are blocked, never substituted with browser projections.
- For agent obligations, record actual tool outcomes and side effects, not merely the final answer. Use deterministic adapters for boundary tests and predeclared repeated live-model trials for reliability claims. Preserve failures/retries and do not cherry-pick a passing trial.
- For cross-platform obligations, verify shared synthetic identity, persistence, sync and entitlements across the named clients. Individual platform happy paths do not prove their interaction.
- Retain redacted logs/assertions, applicable screenshots and native build/configuration evidence with content hashes and exact candidate identity. A nonempty hashed file proves retained bytes, not the truth of its contents; reviewer inspection of assertions and provenance remains required.
- Build and configuration identity must match the artifact actually exercised. A deployed environment is read back; a local commit SHA alone cannot prove the server or native binary matches it. Candidate checks and separately authorized production smoke are distinct.

A web release target counts as delivery-verified only when every required browser combination has a frozen scenario and a passing result. Report WebKit results as a Safari approximation. WebKit does not prove real Safari, iOS or device coverage.

## Full-Stack Slices And Reproducible E2E

Implement complete accepted user flows in small slices: screen/client → API/service → permissions → saved data → visible result. For each applicable slice, prove validation, real test login, tenant/role denial, persistence after reload or a separate read, safe retry, cancellation and external side effects. A working mock screen does not prove its backend. Use existing project test tools before proposing another dependency.

Use `agent-browser` for exploratory Web operation and acceptance, in an isolated named session. Preserve important paths as tests runnable locally and in CI with documented setup, fixture ownership, assertions and teardown. Browser commands are execution, not evidence by themselves: retain the observed state and data assertions, exact build and command results. Native flows use their platform runner, not a browser projection. The local HiFi smoke example in the UI skill proves its controlled Web interactions only.

Use the existing acceptance contract and results register. Screenshots can support visual findings but cannot replace required auth/data/permission assertions; Agent self-reports cannot prove tool side effects. Mechanical checks validate IDs, hashes, matrix coverage and recorded assertions. Independent review must reject a structurally valid record when its logs lack the claimed execution or contain only screenshots/prose. Never describe that semantic check as something a file hash proves.

After interruption, reconcile the current candidate, existing records, owned fixtures and external readbacks before resuming. Reuse verified unchanged steps; repeat only stale/missing checks. Before retrying a state-changing operation, inspect its idempotency key or actual outcome. Unknown outcome blocks that operation until reconciled; never replay a payment, message, migration or account creation just because the last response was lost.

## Acceptance And Handoff

### Record Format

Start from `assets/templates/DELIVERY_ACCEPTANCE.template.json` and `DELIVERY_RESULTS.template.json`. Their placeholders and unvalidated results intentionally fail. Default project paths are `docs/verification/delivery-acceptance.json` and `docs/verification/delivery-results.json`; record actual paths in DOCUMENTS. No credentials, cookies or browser storage belong in either file.

Concrete identity and execution fields reject embedded placeholder tokens such as `release-<build-id>` or `Chrome <version>`; comparison text such as `latency < 200 ms` remains valid. Evidence paths must be checkout-relative even when an absolute path would point inside the current checkout. CLI input paths may be absolute.

- Contract: exactly `schema: delivery-acceptance/1`, `prd_sha256`, `tests`. Each test has `test_id` and `scenarios`; each scenario has `id`, `platform`, `auth_mode`, `environment`, `build`, `execution`, `fixtures`.
- Result: exactly `schema: delivery-results/1`, `candidate_sha`, `results`. Each row has `test_id`, `scenario_id`, `platform`, `auth_mode`, `environment`, `build`, `execution`, `status`, `assertion_results`, `fixture_cleanup`, `evidence`.
- `execution` freezes `target`, `device`, `os`, `persona` (exactly `role`, `tenant`, `account_state`), `initial_data`, ordered `actions`, `assertions` (stable ID to expected signal), `expected_side_effects`, and `dependency_mode`. Use concrete non-secret text; explain genuine non-applicability. Results repeat the exact observed context. For native tests name the actual device/simulator and OS; for agent trials name the tool/model setup and predeclared trial counts. Reviewer inspection must confirm this matches reality.
- Version 2 pairs `schema: delivery-acceptance/2` with `delivery-results/2`. It adds exactly `browser` to the `execution` of every `web` scenario. Other platforms and version 1 reject the field. `browser` holds exactly `release_target` (lowercase kebab-case) and `engine` (`chromium`, `firefox`, or `webkit`). Results repeat the frozen `browser` identity exactly. When the frozen PRD maps a release target to Firefox or WebKit, the contract must be version 2. Every required combination then needs a `web` scenario with that identity and a passing result. Version 1 stays valid only when the PRD names no non-Chromium target.

  ```json
  {
    "id": "web-firefox-smoke",
    "platform": "web",
    "execution": {
      "browser": {"release_target": "web-production", "engine": "firefox"}
    }
  }
  ```
- `build` uses exactly `build_id` and lowercase SHA-256 `config_digest`. Only non-native local checks may instead use `not_applicable_reason` with a real explanation. A mocked UI cannot use this escape to claim native completion.
- `platform` is `web`, `browser-extension`, `ios`, `android`, `macos`, `windows`, `desktop`, `agent`, `api`, or `cli`. `auth_mode` is `mock`, `real`, or `none`. `environment` is `local`, `test`, `preview`, `staging`, or `production`; mock auth and synthetic fixtures cannot target production.
- Each fixture has exactly `namespace` (unique `synthetic-*` run namespace), `setup_authority`, `cleanup_authority`, `owned_resources` (unique `owned:` resource handles), `production: false`, `auth_bypass: false`. Authority text references an already verified grant, never creates one. An empty fixture list is allowed only when the scenario genuinely needs no seeded resource; the parent checks applicability.
- Required results have `status: pass` and `assertion_results` covering exactly every frozen assertion with `pass`. Other recorded statuses are `fail`, `blocked`, `skipped`, and `unvalidated`; none satisfies required acceptance. `fixture_cleanup` must be `cleaned` if fixtures exist, otherwise `not_required`. Keep setup/cleanup readbacks, exact owned IDs and assertion observations in the linked evidence; a flag alone is not execution proof.
- `evidence` has exactly repository-contained `path` and lowercase `sha256`. The path sits under `evidence/` next to the register (`docs/verification/evidence/` by default). It names a nonempty, bounded, redacted regular file, not a link, secret file or out-of-repository path. Unknown fields and duplicate JSON keys fail.

```text
python "<delivery-harness-skill-root>/scripts/check_delivery_acceptance.py" --repo-root . --prd docs/product/PRD.md --contract docs/verification/delivery-acceptance.json --contract-sha256 <parent-frozen-hash> --results docs/verification/delivery-results.json --candidate-from-head
```

Exit 0 reports structural `PASS`; exit 1 reports failed evidence coverage, and invalid CLI arguments exit 2. This is one gate, not product completion. Legacy PLANs without eval-policy adoption do not automatically require it; applicable eval adoption enforces its source, declaration and graph under `eval-acceptance-contract.md`. New-work authoring review still checks actual execution. Semantic coverage, native provenance and fixture safety need review even when the register passes.

`check_delivery_acceptance.py` takes the authoritative PRD, frozen contract and expected contract SHA-256, result register, repository root and either `--candidate-sha <sha>` or `--candidate-from-head`. Run from the project root using the installed absolute script path. It checks coverage and retained artifacts read-only. When `--repo-root` is the Git checkout root, it reads the register and evidence from the working tree and requires those exact bytes to match regular files committed at HEAD. A register cannot name the commit that holds it, so use this order: run the scenarios at candidate H1 and write `candidate_sha: H1`; commit only the register and the evidence files it lists on top of H1, giving H2; run the exact-head reviews and every final gate, including this check, at H2 from a clean checkout (`git status --porcelain --untracked-files=all` is empty). Managed host verifiers already require that clean tree at the exact head, and direct work checks it by hand.

The register and evidence must be stored byte-for-byte in Git. Before adding them, set `.gitattributes` for their actual paths, for example `docs/verification/delivery-results.json -text -filter` and `docs/verification/evidence/** -text -filter`. Check the effective attributes with `git check-attr text filter -- <register> <evidence-path>`; both must be unset. This prevents Git for Windows CRLF conversion and content filters such as LFS from replacing the bytes in HEAD. Add the attributes before candidate H1, not in the register-only commit. A `bytes differ from HEAD` result can mean line-ending or filter conversion even when `git status` is clean. Do not run Git filters during this read-only check or treat a converted working copy as exact evidence.

For one check, resolve HEAD once to an immutable commit SHA. Compare the register, every evidence blob, candidate ancestry and changed paths against that SHA, then fail unless HEAD still names the same SHA when the check finishes. Include submodule pointer changes regardless of Git's diff ignore settings. A moving branch must never combine evidence from different commits into one PASS.

When `--repo-root` is a Git checkout root, the check fails unless `candidate_sha` is HEAD or an ancestor of it and every later commit changes only the register, the evidence files it lists under that evidence root and run coordination files such as RUN. Naming a product or test file as evidence never exempts it. Any other change after H1 makes a new candidate; run the scenarios again. `--candidate-sha` also requires the register to name that SHA. `--candidate-from-head` takes H1 from the register, so a PLAN gate never has to name it: Git, not the register writer, proves that H1 has HEAD's product tree. It needs a Git checkout.

In a managed run, H1 is the last mission's merged head before `record-integration`; commit the register there, then run `record-integration --integrated-sha H2`, so H2 is the recorded integration head before the unified reviews start. That mission's `write_scope` must list the register and evidence paths (the PLAN template shows them). Before H1, the readiness review checks effective byte-preserving attributes on the base; if missing, an authorized pre-H1 task must add `.gitattributes` to its `write_scope` and security review scope, then commit it before H1. `record-integration` checks only that scope, so the acceptance gate is what refuses a product file committed with the register. Only the parent writes these paths, and every evidence file the register lists comes from its own run at H1. When the PLAN declares the acceptance gate, worker-result validation refuses a worker change to the register the gate names with `--results` or anything under its `evidence/` directory, whatever the task `write_scope` says. It also refuses any change no task `write_scope` covers, even when the register path cannot be read from the gate argv. Both checks run in every workspace mode, shared checkout included. They are not coordination paths: a register commit after the recorded head leaves RUN stale. Any candidate repair after H2 changes files outside the register, so the gate fails at the repaired head. `reconcile-candidate-head` accepts only paths in the repair task's `write_scope`, which never lists the register, so rerunning acceptance after H2 needs a formal PLAN revision with fresh owner authorization; the new digest stops the old execution grants from covering anything. The revision adds a repair task whose `write_scope` lists only the register and evidence paths; that is safe then because the mission is already integrated. The parent commits that repair and records it with `reconcile-candidate-head`; a worker result cannot carry it.

Ignored, untracked or edited register and evidence bytes fail the Git checkout check, even when their content hashes match the result rows. Review still confirms the evidence came from runs against `candidate_sha`; the checker cannot prove that. The contract/reference and tests document the precise JSON fields; do not invent result fields or treat a hand-written PASS summary as execution evidence.

Every required obligation and scenario must have matching passing evidence. Missing, failed, blocked, unvalidated, stale or duplicate results fail acceptance. Mock evidence cannot satisfy real-auth obligations, a different platform cannot satisfy native coverage, and fixture authority cannot cover production mutation. Reject malformed records and unsafe evidence paths rather than trying to repair them during verification.

A required failure moved to the backlog is still a failure. Report verified scope, incomplete scope and exact next-round acceptance conditions without claiming global PASS. A formally accepted later scope is a new scope, not a rewrite of this round's failed history. No checker result grants publication, live security probing, installation, cleanup or other external actions.
