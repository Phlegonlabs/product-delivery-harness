# Test Fixture Lifecycle

Use with `delivery-acceptance-contract.md` for each real Web, native, agent, or cross-surface journey. This is a project-specific execution contract, not a universal account-creation client. Never select an auth vendor or install a test runner implicitly.

## Before Execution

Derive personas from approved requirements: anonymous, ordinary user, administrator, different tenants, new/empty/existing data, unverified, disabled, expired session, or paid/unpaid only when applicable. Keep stable fixture definitions in source; keep credential values, cookies, browser storage state and simulator local data out of Git and logs. Apply `gitignore-contract.md` in the same change that introduces those outputs. Use names or secret-manager references only in documents.

Record the exact nonproduction environment identity, endpoint, project/tenant, database, auth provider mode, delivery run ID, unique namespace, seed version, and permissions. Separately name the setup, test and cleanup commands, their expected results, approved mutation scope and reset strategy. Check the target identity before each mutation; an environment named staging does not prove it is isolated. If identity, permission, secrets or native capability is missing, mark the affected tests blocked and continue independent checks.

Freeze required scenarios before implementation results are known. Each scenario names its TEST IDs, platform/device/OS, role and tenant, auth mode, initial data, actions, observable assertions, external service mode and expected side effects. Negative tests assert both rejection and unchanged protected state. Register two users/tenants when isolation is required; one all-powerful test account cannot prove isolation.

## Setup, Exercise, Observe, Teardown

1. Under existing exact test-environment authority, create or reset only synthetic resources owned by this run. Stamp resources with the run namespace and retain their non-secret identifiers in an ownership manifest. Setup is idempotent; after an ambiguous timeout, read back before retrying. Concurrent runs have different namespaces and no shared mutable accounts.
2. Verify initial state independently: account role, tenant, entitlement/state and seeded records. A seed command's exit code alone does not prove the requested persona exists. Preserve failed setup as failure, not a skipped passing journey.
3. Run mock-state cases and real-sandbox cases separately. Mock auth can exercise UI states deterministically. At least the required authentication lifecycle cases use the real test auth boundary; injected cookies/tokens or bypassed login cannot prove login. Production builds must reject test bypasses, verified by a negative test of the production configuration/build.
4. Exercise the real browser or installed native binary for UI journeys. Retain device/OS and build identity for native tests; a browser screenshot of a native design projection does not count. Verify state persistence after reload/relaunch and authorization at the backend, not only visible controls.
5. For agents, first test deterministic tool adapters and denial paths with fixtures, then test the required real sandbox tool integrations. Observe actual side effects, idempotency, retries, cancellation, permission denial and recovery. For live-model evaluation, predeclare model/configuration, dataset, number of trials and success threshold; retain every trial, not only successful examples. Mock-model results cannot satisfy a live-model obligation.
6. For cross-platform requirements, verify the same synthetic identity/data across the named clients and agent tools. Independent happy paths do not prove sync or shared entitlements.
7. Retain redacted assertions, runner output, traces and applicable native/browser screenshots with exact candidate/build/configuration and requirement bindings. Include the original failure and retry history; a flaky retry is not silently a clean PASS. Test success, visual quality, representative-user usability and production availability remain separate claims.
8. Before teardown, retain diagnostic evidence. Delete/reset only exact identifiers whose current namespace and ownership still match this run and whose cleanup was authorized. Never use a broad database reset or delete a shared tenant. Interrupted runs leave an explicit cleanup-pending handoff; recovery rechecks identity/ownership before acting. Verify cleanup and record leftovers. Do not claim complete environment hygiene while teardown failed.

## External And Production Boundaries

Default outbound email/SMS to an approved sink, payments to test mode, and external tools to explicit sandbox destinations. This default is a requirement to configure a safe route, not authority to create external resources. If no safe route exists, block the affected case; do not send real messages or money to make a test pass.

Production verification is a separately authorized bounded smoke against the actual release. It never inherits synthetic-account creation, destructive cleanup or login-bypass permission. Test content is access-controlled/non-indexable where applicable and test events are excluded from production outcome metrics. `product-activation` verifies production availability; `seo-growth-review` reports any indexing or measurement contamination read-only.
