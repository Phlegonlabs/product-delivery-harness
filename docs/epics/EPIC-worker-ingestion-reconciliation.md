# Worker ingestion reconciliation

Status: retry-head prevention verified locally; recovery remains incomplete.

## Problem and scope

AgentKiosk's second M01 author returned a passing candidate, but the mission still held the first attempt's head. Normal ingestion rejected the new head and durably recorded a retryable failure. The owner accepted the exact candidate for independent review and asked to finish the project. That does not erase the rejected ingestion or grant another writer attempt.

Source baseline: `codex/agentkiosk-motion-compiler` at `78fb89c90fc729d81f519ad9c33000dea4f905f7`. This direct support repair changes no consumer product or design source. Source work stays local. A new isolated runtime needs its own reviewed fixed candidate and concrete adoption authority; shared installation, publication and deployment are outside this change.

## Required behavior

A new lease clears the mission's current-head projection while preserving previous workers and attempts. Recovery of the existing rejection must separately prove the unchanged original result, exact receipt and lease, sole stale-head blocker, real current Git and verifier evidence, and preserved failed history/counts. It must support the closed original wave and the original S3 child contract check after a later authorized runtime adoption. Normal failed-phase and current-contract checks remain strict.

## Change log

- 2026-10-22 UTC: native implementer configured as GLM Flash/max produced a recovery draft. Its first5-case fixture runs failed before proving acceptance. The parent identified missing sole-cause, receipt, role and Markdown guards. The author added some checks but did not complete recovery. Drafts and original failed logs remain under `agentkiosk-implementation-20261021-01/ingestion-repair-004/recovery-draft-20261022-0230/` in the system temporary directory. No consumer state or bundle was changed by that author.
- `1472f65b846698ff7d927076813378ffcfeeb3f1` commits only new-lease head clearing and its focused regression. The author reports focused regression, pyflakes, skill specification and diff checks passed. The source remains a development candidate, without independent review or installation.
- Parent discovery found that the new test inherited every existing transition test and imported its test class. Discovery therefore repeated the old suite; the finite180second parent run timed out and its owned tree exited. This was not a PASS. The follow-up uses the existing fixture's setup/teardown through a module import without inheriting its test methods. Discovery now runs exactly one regression: exit0, 4.085seconds. It also removes an unrelated formatting change from the preceding commit. Evidence: `checks/retry-head-discovery-fix-004-1792636275385383000.json` under the same external task root.
- The initial author edited `validate_worker_result.py` before requesting that path. The parent later restricted its use to guarded reconciliation; those draft edits were preserved and removed from the live checkout. The new regression path is included in the parent's current follow-up scope. No scope exception establishes code acceptance.

## Remaining work

Freeze the historical-adoption and closed-wave recovery design, complete actual CLI/receipt/verifier and negative-case fixtures, document the new command in the four READMEs and touched contracts, and run the related suites. A fresh GPT-6.1 Sol/xhigh code/security review must bind the complete fixed source candidate before any new bundle is proposed. M01 is not accepted, reviewed or integrated by these source changes.
