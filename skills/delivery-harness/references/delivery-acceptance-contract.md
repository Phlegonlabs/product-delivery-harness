# Requirement-To-Evidence Acceptance

Use this contract on new delivery work, both direct and managed. It supplements the existing PRD checker, PLAN/RUN joins and security/UI gates; it does not replace their authority or alter legacy RUN schemas. `test-fixture-lifecycle.md` defines setup, execution, observation and teardown. `bounded-enhancement.md` defines repair budgets and honest next-round handoff.

## Freeze Expectations Before Results

Product Definition owns PRD requirements and required TEST IDs. First run its full approved-package checker to prove Must/NFR and gate coverage. The Harness then freezes the concrete scenario matrix derived from those obligations: TEST ID, scenario identity, platform/device/OS, authentication mode, environment, build/configuration identity, initial persona/data, observable assertions and external dependency mode. A primary journey needs complete user-to-data proof in addition to unit/integration checks; not every requirement needs an expensive UI test.

Retain the executable contract separately from the result register. Bind its SHA-256 in the accepted plan or direct-task scope record before execution. The acceptance CLI's expected contract hash and candidate SHA come from that parent-observed authority, never from the result file itself. A result writer cannot remove a required platform, relabel real auth as mock, weaken an assertion or edit both expectation and result to obtain PASS. A changed expectation needs the original scope decision checked again, not a silent hash refresh.

For managed work, freeze the contract as an additional PLAN source and declare `check_delivery_acceptance.py` as an always-run final gate with a matching verifier graph node before closeout. The existing verifier runtime records its execution key in RUN; link the register rather than copying its result rows into a competing RUN schema. Direct work runs the same CLI without PLAN/RUN. Gate-authoring review must reject a missing acceptance verifier; this is not automatic retroactive migration of old plans.

## Execute And Retain

- Run actual project-specific setup and test commands under exact existing authority. These checkers inspect records; they never provision accounts, run a browser/simulator, invoke tools, deploy, or supply credentials themselves.
- Keep mock, real-sandbox, and production-smoke claims separate. Real-login obligations exercise the actual test authentication boundary. Native obligations require the actual native artifact and device/OS evidence; unavailable runners are blocked, never substituted with browser projections.
- For agent obligations, record actual tool outcomes and side effects, not merely the final answer. Use deterministic adapters for boundary tests and predeclared repeated live-model trials for reliability claims. Preserve failures/retries and do not cherry-pick a passing trial.
- For cross-platform obligations, verify shared synthetic identity, persistence, sync and entitlements across the named clients. Individual platform happy paths do not prove their interaction.
- Retain redacted logs/assertions, applicable screenshots and native build/configuration evidence with content hashes and exact candidate identity. A nonempty hashed file proves retained bytes, not the truth of its contents; reviewer inspection of assertions and provenance remains required.
- Build and configuration identity must match the artifact actually exercised. A deployed environment is read back; a local commit SHA alone cannot prove the server or native binary matches it. Candidate checks and separately authorized production smoke are distinct.

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
- `build` uses exactly `build_id` and lowercase SHA-256 `config_digest`. Only non-native local checks may instead use `not_applicable_reason` with a real explanation. A mocked UI cannot use this escape to claim native completion.
- `platform` is `web`, `browser-extension`, `ios`, `android`, `macos`, `windows`, `desktop`, `agent`, `api`, or `cli`. `auth_mode` is `mock`, `real`, or `none`. `environment` is `local`, `test`, `preview`, `staging`, or `production`; mock auth and synthetic fixtures cannot target production.
- Each fixture has exactly `namespace` (unique `synthetic-*` run namespace), `setup_authority`, `cleanup_authority`, `owned_resources` (unique `owned:` resource handles), `production: false`, `auth_bypass: false`. Authority text references an already verified grant, never creates one. An empty fixture list is allowed only when the scenario genuinely needs no seeded resource; the parent checks applicability.
- Required results have `status: pass` and `assertion_results` covering exactly every frozen assertion with `pass`. Other recorded statuses are `fail`, `blocked`, `skipped`, and `unvalidated`; none satisfies required acceptance. `fixture_cleanup` must be `cleaned` if fixtures exist, otherwise `not_required`. Keep setup/cleanup readbacks, exact owned IDs and assertion observations in the linked evidence; a flag alone is not execution proof.
- `evidence` has exactly repository-contained `path` and lowercase `sha256`. It names a nonempty, bounded, redacted regular file, not a link, secret file or out-of-repository path. Unknown fields and duplicate JSON keys fail.

```text
python "<installed-delivery-harness>/scripts/check_delivery_acceptance.py" --repo-root . --prd docs/product/PRD.md --contract docs/verification/delivery-acceptance.json --contract-sha256 <parent-frozen-hash> --results docs/verification/delivery-results.json --candidate-sha <parent-observed-SHA>
```

Exit 0 reports structural `PASS`; exit 1 reports failed evidence coverage, and invalid CLI arguments exit 2. This is one gate, not product completion. The legacy PLAN validator does not automatically require this new gate: new-work authoring review must verify its frozen source, always-run final declaration, graph placement and execution. Semantic requirement coverage, native provenance and actual fixture safety still need review even when the register passes.

`check_delivery_acceptance.py` takes the authoritative PRD, frozen contract and expected contract SHA-256, result register, repository root and exact candidate SHA. Run from the project root using the installed absolute script path. It checks coverage and retained artifacts read-only. The contract/reference and tests document the precise JSON fields; do not invent result fields or treat a hand-written PASS summary as execution evidence.

Every required obligation and scenario must have matching passing evidence. Missing, failed, blocked, unvalidated, stale or duplicate results fail acceptance. Mock evidence cannot satisfy real-auth obligations, a different platform cannot satisfy native coverage, and fixture authority cannot cover production mutation. Reject malformed records and unsafe evidence paths rather than trying to repair them during verification.

A required failure moved to the backlog is still a failure. Report verified scope, incomplete scope and exact next-round acceptance conditions without claiming global PASS. A formally accepted later scope is a new scope, not a rewrite of this round's failed history. No checker result grants publication, live security probing, installation, cleanup or other external actions.
