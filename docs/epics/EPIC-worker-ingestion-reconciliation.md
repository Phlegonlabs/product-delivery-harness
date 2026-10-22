# Worker ingestion reconciliation

Status: recovery and local verification complete; fixed-candidate independent review and isolated adoption pending.

## Problem and scope

AgentKiosk's second M01 author returned a passing candidate, but the mission still held the first attempt's head. Normal ingestion rejected the new head and durably recorded a retryable failure. The owner accepted the exact candidate for independent review and asked to finish the project. That does not erase the rejected ingestion or grant another writer attempt.

Source baseline: `codex/agentkiosk-motion-compiler` at `78fb89c90fc729d81f519ad9c33000dea4f905f7`. This direct support repair changes no consumer product or design source. Source work stays local. A new isolated runtime needs its own reviewed fixed candidate and concrete adoption authority; shared installation, publication and deployment are outside this change.

## Required behavior

A new lease clears the mission's current-head projection while preserving previous workers and attempts. Recovery of the existing rejection must separately prove the unchanged original result, exact receipt and lease, sole stale-head blocker, real current Git and verifier evidence, and preserved failed history/counts. It must support the closed original wave and the original S3 child contract check after a later authorized runtime adoption. Normal failed-phase and current-contract checks remain strict.

## Change log

- Final recovery check passed in 95.847 seconds (`checks/ingestion-recovery-final-006-1792643448451322900.json`). The 230-case existing regression run had one expected-command-list failure and three platform skips; the unchanged list omitted the new tasks projection checkpoint. That assertion was updated and its complete module passed on rerun (`checks/ingestion-tasks-view-regression-006-1792643554060275000.json`). The skips cover one POSIX-only assertion and two unavailable Windows symlink operations. Full six-skill pyflakes, skill specification, documentation weight and diff checks passed. These are local development checks, not a formal release matrix or installation claim. Source review remains required.

- Parent implemented the frozen Sol design in two focused modules. Ordinary worker/adoption acceptance stays unchanged; a shared success projection preserves the original rejected dispatch. Recovery records a strict receipt, rechecks source bytes and the worker branch at commit, and keeps the mission node running until integration. Two focused tests passed in 134.779 seconds, including closed-wave S3-to-S4 recovery, fifteen isolated negative cases, four transaction races, replay refusal, historical receipt retention and a fresh S4 review directive. The first two development runs reached recovery but exposed incorrect test API/node-name assumptions; those failures remain retained. A final focused rerun covers the last receipt-projection and bounded-input checks. Evidence: `checks/ingestion-recovery-core-006-003-1792643255631580400.json` under the external task root. The four READMEs and five affected references describe the command. No consumer state, new bundle or shared installation changed.

- Parent completed the real CLI regression fixture after taking exclusive checkout ownership. Two real leases, task commits, host verifier executions and a retained result receipt reproduce only the inherited-head rejection. Discovery runs one test: PASS in 34.797 seconds. Evidence: `checks/ingestion-parent-real-fixture-005-002-1792642539718139600.json` under the external task root. Recovery remains unimplemented and the consumer remains unchanged. Architecture and independent review use native GPT-6.1 Sol/xhigh; the earlier Astra diagnostic was stopped and replaced.

- 2026-10-22 UTC: native implementer configured as GLM Flash/max produced a recovery draft. Its first5-case fixture runs failed before proving acceptance. The parent identified missing sole-cause, receipt, role and Markdown guards. The author added some checks but did not complete recovery. Drafts and original failed logs remain under `agentkiosk-implementation-20261021-01/ingestion-repair-004/recovery-draft-20261022-0230/` in the system temporary directory. No consumer state or bundle was changed by that author.
- `1472f65b846698ff7d927076813378ffcfeeb3f1` commits only new-lease head clearing and its focused regression. The author reports focused regression, pyflakes, skill specification and diff checks passed. The source remains a development candidate, without independent review or installation.
- Parent discovery found that the new test inherited every existing transition test and imported its test class. Discovery therefore repeated the old suite; the finite180second parent run timed out and its owned tree exited. This was not a PASS. The follow-up uses the existing fixture's setup/teardown through a module import without inheriting its test methods. Discovery now runs exactly one regression: exit0, 4.085seconds. It also removes an unrelated formatting change from the preceding commit. Evidence: `checks/retry-head-discovery-fix-004-1792636275385383000.json` under the same external task root.
- The initial author edited `validate_worker_result.py` before requesting that path. The parent later restricted its use to guarded reconciliation; those draft edits were preserved and removed from the live checkout. The new regression path is included in the parent's current follow-up scope. No scope exception establishes code acceptance.

## Remaining work

Bind a fresh GPT-6.1 Sol/xhigh code/security review to the complete fixed source candidate. A new isolated bundle still needs concrete adoption authority. M01 is not accepted, reviewed or integrated by these source changes.
