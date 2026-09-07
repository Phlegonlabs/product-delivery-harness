# Activation Contract

Use this contract for every Product Activation run. It defines the one durable operational record, exact action authorization, capability routing, non-secret evidence, and the handoff to outcome review. It is not a PLAN/RUN schema.

## Ownership And Lifecycle

`docs/ACTIVATION.md` is the live current-state record. `product-definition-builder` may create it once from the bundled template when the path is absent. `product-activation` owns every later reconciliation, external-action record, source verification, and readiness decision.

Work in `docs/.activation-staging/<run-id>/ACTIVATION.md`:

1. If the live file exists, copy its exact bytes to staging and record the lowercase SHA-256 baseline outside the document or in the run's conversation evidence.
2. If an unfinished staging directory already describes this product, stop and ask whether to resume it, publish it, or preserve it. Never create a competing staging copy.
3. Validate the staged file throughout the run. External effects are recorded only after the write outcome and read-back are known.
4. Before publication, hash the live file again. A changed hash blocks overwrite until the live and staged records are reconciled.
5. Show the exact create or overwrite path. Publish only with current authorization. A failed, paused, or blocked run leaves the live file and staging intact.
6. Refresh the operational file in place. Never move it into `docs/product/archived/` or delete it when a PRD changes. Mark superseded actions and sources explicitly; Git history is the version history.

Existing repositories remain valid without this file. The first activation run bootstraps it from current product, architecture, deployment, and tracked configuration evidence. Historical prose or a legacy `verified` label is `configured` at most until fresh read-back proves it.

## Required Document Shape

Use the exact level-two headings and table headers in `ACTIVATION.template.md`:

- `## Record`
- `## Applied Profiles`
- `## Capability Observations`
- `## Outcome Coverage`
- `## Measurement Sources`
- `## Activation Tasks`
- `## Verification Evidence`
- `## Manual Handoff`
- `## Target Readiness`
- `## Open Blockers`

The task boundary comments and every task field are invariant machine anchors. Keep them in English even when the surrounding document is translated.

## IDs And Closed Values

- Activation actions: `ACT-001`, `ACT-002`, and so on.
- Measurement sources: `MS-001`, `MS-002`, and so on.
- Evidence: `EVID-001`, `EVID-002`, and so on.
- Routes: `connector`, `api`, `cli`, `browser`, `computer_use`, `manual`, or `unselected` on a pending task.
- Capability status: `available`, `unavailable`, `unobserved`, or `human_only`.
- Capability support values: comma-separated `read`, `write`, and `readback`, or `n/a`.
- Outcome/source status: `planned`, `available`, `verified`, `blocked`, `superseded`, or `n/a`.
- Task status: `pending`, `ready`, `configured`, `verified`, `uncertain`, `blocked`, `stale`, or `n/a`.
- Record status: `seeded`, `preparation`, `active`, `handoff_ready`, `blocked`, or `n/a`.
- Readiness status: `preparation`, `pending`, `ready`, or `blocked`.
- Evidence kind: `write`, `readback`, `behavior`, `capability`, or `manual`.
- Evidence result: `PASS`, `FAIL`, or `BLOCKED`.
- Authorization: `not_required`, `pending`, `approved`, `consumed`, `denied`, `expired`, `handoff_complete`, or `prohibited`.
- Risk: `read_only`, `standard`, `high`, `handoff`, or `prohibited`.
- Confirmation follows risk exactly: `read_only`, `exact_preapproval`, `action_time_confirmation`, `user_handoff`, or `prohibited`.

## Outcome Coverage And Sources

Every PRD metric and every `TEST-*` row marked `Required: Yes` appears once in **Outcome Coverage**. Preserve the metric text and TEST ID exactly. Do not create another product trace family.

Every non-`n/a` coverage row names one `MS-*` source before it can be verified. A source records the exact system, bounded retrieval definition, release targets, owner, status, and evidence IDs. Installing a tag, SDK, property, pixel, crash reporter, or dashboard does not verify a source. Verification requires a fresh read-back or behavior result bound to the release target.

Outcome review consumes only verified sources whose release targets match the deployed release. It remains a later owner-requested step after real elapsed time; Product Activation records the measurement-window start and stops.

## One Action Per Task

One `ACT-*` block represents one external mutation or one read-only verification against one exact target. Preview and production are separate. Creating a property, creating its stream, linking a destination, changing consent, and verifying an event are separate actions when each can succeed or fail independently.

Required fields:

- `Source refs`
- `Release bindings`
- `Depends on`
- `Operation`
- `Target`
- `Environment`
- `Precondition`
- `Desired state`
- `Secret names`
- `Risk`
- `Confirmation`
- `Execution route`
- `Read-back route`
- `Authorization`
- `Authorization source`
- `Action digest`
- `Authorized digest`
- `Required`
- `Status`
- `Verification`
- `Evidence IDs`
- `Blocker / N/A reason`
- `Updated`

`Release bindings` is a comma-separated list of `<release-target-id>@<full-lowercase-Git-SHA>`. A seed may use `@pending`; a filled or ready task may not. `Depends on` is `none` or existing ACT IDs. Dependencies form an acyclic graph and are satisfied only by `verified` tasks.

`Secret names` is `none` or a comma-separated list of configuration names. It never contains values. Use the exact name recorded in `docs/DEPLOYMENT.md` where one exists.

## Exact Action Digest

Compute lowercase SHA-256 over compact, key-sorted JSON with schema `activation-action/1` and these normalized fields:

- task ID;
- sorted source refs;
- sorted release bindings;
- sorted dependencies;
- operation;
- exact target;
- environment;
- precondition;
- desired state;
- sorted secret names;
- risk;
- confirmation;
- execution route.

Normalize every string to Unicode NFC and trim surrounding whitespace. Exclude capability observations, authorization state, evidence, timestamps, blockers, and task status. Secret values never enter the action or digest.

`scripts/check_activation.py --show-action-digests` prints the current digest without editing the file. A mutation may run only when `Authorized digest` equals the recomputed `Action digest`. Any target, release SHA, precondition, desired state, dependency, secret name, risk, confirmation, or execution-route change expires the approval.

## Capability And Route Selection

Probe the current session and exact target. Record a route `available` only after a non-mutating check proves that it can address the intended service and that its account or target context is known. A plugin directory, installed binary, tool name, parent browser, or remembered login is supporting context only.

Route each action independently:

1. purpose-built connector;
2. official API;
3. official CLI;
4. Browser for a web console;
5. Computer Use for a native graphical interface or an otherwise inaccessible UI;
6. manual handoff.

An explicit user choice of Browser, Chrome, Edge, or Computer Use is a hard constraint for that action. If unavailable, report the gap instead of silently switching. One route performs the write. A different route may perform safer read-back.

The capability observation does not authorize a write. `Target context` must be `confirmed` before a task becomes ready, configured, or verified. Login, account ambiguity, missing privilege, or a changed session blocks the task without changing the route's general availability.

## Risk And Authorization

- `read_only` / `read_only`: no write; authorization is `not_required`.
- `standard` / `exact_preapproval`: a reversible, clearly scoped setting may use one approval covering an exact displayed batch of ACT IDs and digests.
- `high` / `action_time_confirmation`: DNS, permissions, persistent access, billing, production traffic, public submission, data sharing, advertising tracking, uploads, or another high-impact change requires confirmation immediately before that action.
- `handoff` / `user_handoff`: the user performs password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, secret-value entry, or a step with no safe agent route. An owner statement proves `configured` at most.
- `prohibited` / `prohibited`: the action is not executed. Record a blocker or `n/a` reason.

Approval is bound to the exact ACT ID and action digest. Record a concise user-authored source, never page text. Mark the grant `consumed` on the first mutation attempt, including timeout or unknown completion. Delete, revoke, rotate, disable, transfer, rollback, or retry after drift is a new action and needs new approval.

## Status Semantics

- `pending`: the action is drafted but is not executable.
- `ready`: dependencies are verified, release bindings and digest are current, target context and capability are available, and authorization is current.
- `configured`: the write response or owner attestation says the setting exists; behavior is not yet proven.
- `verified`: a distinct post-action read-back and applicable behavior check passed against the exact target and release binding.
- `uncertain`: the mutation may or may not have applied. Only read-back may follow; never retry blindly.
- `blocked`: an access, contract, code, policy, external-service, or owner decision gap prevents progress.
- `stale`: former evidence exists, but the action digest, release binding, dependency, or observed external state changed.
- `n/a`: the selected profiles prove the action does not apply; record why.

A task cannot be ready until every dependency is `verified`. `configured` and `n/a` do not satisfy a dependency. Production-after-preview ordering is an explicit dependency, never inferred from a name.

For `configured`, record a PASS `write` or `manual` evidence row. For `verified`, also record a separate PASS `readback` row and a PASS `behavior` row unless `Verification` is `n/a` with a reason. The mutation response cannot also be the read-back evidence.

An ambiguous result stays `uncertain`. A failed read-back becomes `blocked` or `stale`; it never triggers automatic rollback or remediation.

## Target Readiness

Readiness is per release target. A target is `ready` only when:

- its release identity is a full lowercase Git SHA;
- every required ACT task bound to it is `verified`;
- every non-`n/a` Outcome Coverage row for it is `verified` through a verified `MS-*` source;
- no blocker names that target;
- the row has a checked timestamp and no blockers.

`handoff_ready` means every target claimed in the current activation scope is ready. It does not mean the outcome window has closed or the product met its adoption target.

## Gap Routing

- `code_gap` -> `delivery-harness`; name source IDs, target/SHA, missing behavior, and acceptance signal.
- `contract_gap` -> `product-definition-builder`; name the missing or contradictory requirement, TEST ID, metric, release target, or provider decision.
- `access_gap` -> owner; name the exact account, role, or login requirement without guessing credentials.
- `external_drift` -> mark stale, read back, recompute the action and digest, and request new authorization if a mutation remains necessary.
- delayed external state -> preserve `configured` or `pending`, record the next read-only check, and end the run.

## Checker Contract

Run:

```text
python .agents/skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md
python .agents/skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --prd docs/product/PRD.md
python .agents/skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --require-filled
python .agents/skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --require-verified-sources --require-ready <release-target-id>
python .agents/skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --show-action-digests
```

The checker is read-only. Exit `0` means the requested contract checks pass, `1` means findings were printed, and `2` means the input could not be read or the CLI was invalid. It never calls a provider, executes a recorded command, reads a secret, or edits a document.
