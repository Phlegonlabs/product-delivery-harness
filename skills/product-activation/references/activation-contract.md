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
- Capability observations: `CAP-001`, `CAP-002`, and so on.
- Open blockers: `BLOCK-001`, `BLOCK-002`, and so on.
- Routes: `connector`, `api`, `cli`, `browser`, `computer_use`, `manual`, or `unselected` on a pending task.
- Capability status: `available`, `unavailable`, `unobserved`, or `human_only`.
- Capability support values: comma-separated `read`, `write`, and `readback`, or `n/a`.
- Outcome/source status: `planned`, `available`, `verified`, `blocked`, `superseded`, or `n/a`.
- Task status: `pending`, `ready`, `configured`, `verified`, `uncertain`, `blocked`, `stale`, or `n/a`.
- Record status: `seeded`, `preparation`, `active`, `handoff_ready`, `blocked`, or `n/a`.
- Readiness status: `preparation`, `pending`, `ready`, or `blocked`.
- Evidence kind: `write`, `readback`, `behavior`, `capability`, or `manual`.
- Evidence result: `PASS`, `FAIL`, `BLOCKED`, or `UNCERTAIN` when a mutation attempt has no definite outcome.
- Authorization: `not_required`, `pending`, `approved`, `consumed`, `denied`, `expired`, `handoff_complete`, or `prohibited`.
- Risk: `read_only`, `standard`, `high`, `handoff`, or `prohibited`.
- Confirmation follows risk exactly: `read_only`, `exact_preapproval`, `action_time_confirmation`, `user_handoff`, or `prohibited`.

## Outcome Coverage And Sources

Every PRD metric and every `TEST-*` row marked `Required: Yes` appears once in **Outcome Coverage**. Preserve the metric text and TEST ID exactly. Do not create another product trace family.

Every non-`n/a` coverage row names one `MS-*` source before it can be verified. A source records the exact provider target, environment, bounded retrieval definition, route plus target-scoped capability observation, typed release bindings, owner, status, and evidence IDs. Installing a tag, SDK, property, pixel, crash reporter, or dashboard does not verify a source. Verification requires fresh `readback` or `behavior` evidence bound to the exact release SHA and artifact identity; a manual statement cannot verify a measurement source.

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
- `Risk tags`
- `Risk`
- `Confirmation`
- `Execution route`
- `Execution capability`
- `Read-back route`
- `Read-back capability`
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

`Release bindings` is a comma-separated list of `<release-target-id>@<full-lowercase-Git-SHA>#<artifact-or-build-id>`. Use `n/a` as the artifact identity only for a release with no separate signed or store artifact. A seed may use `@pending#pending`; a filled or ready task may not. `Depends on` is `none` or existing ACT IDs. Dependencies form an acyclic graph and are satisfied only by `verified` tasks.

`Secret names` is `none` or a comma-separated list of configuration names. It never contains values. Use the exact name recorded in `docs/DEPLOYMENT.md` where one exists.

`Risk tags` is `none` or a comma-separated list of `dns`, `permissions`, `persistent_access`, `billing`, `production_traffic`, `public_submission`, `data_sharing`, `advertising_tracking`, `upload`, and `destructive`. Every listed tag on a non-read action requires `high` risk unless execution is a manual handoff. A read-only check keeps `read_only` risk even when it names a sensitive resource. The checker also requires the evident `dns`, `permissions`, `billing`, `production_traffic`, or `advertising_tracking` tag when a non-read target or desired state names that concern.

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
- sorted risk tags;
- risk;
- confirmation;
- execution route; and
- execution capability observation ID.

Normalize every string to Unicode NFC and trim surrounding whitespace. Exclude capability observations, authorization state, evidence, timestamps, blockers, and task status. Secret values never enter the action or digest.

`scripts/check_activation.py --show-action-digests` prints the current digest without editing the file. A mutation may run only when `Authorized digest` equals the recomputed `Action digest`. Any target, release SHA or artifact, precondition, desired state, dependency, secret name, risk, confirmation, route, or capability-observation change expires the approval.

## Capability And Route Selection

Probe the current session, exact target, and environment. Give each observation a stable `CAP-*` ID and record its route, status, supported operations, exact service/account/project/resource scope, environment, checked time, and non-secret evidence. Record it `available` only after a non-mutating check proves that exact scope. A plugin directory, installed binary, tool name, parent browser, or remembered login is supporting context only.

Route each action independently:

1. purpose-built connector;
2. official API;
3. official CLI;
4. Browser for a web console;
5. Computer Use for a native graphical interface or an otherwise inaccessible UI;
6. manual handoff.

An explicit user choice of Browser, Chrome, Edge, or Computer Use is a hard constraint for that action. If unavailable, report the gap instead of silently switching. One route performs the write. A different route may perform safer read-back.

The capability observation does not authorize a write. Each task names separate execution and read-back capability IDs; both target scopes and environments must equal the task's exact target and environment, and their routes must equal the declared routes. Each measurement source similarly records `route;CAP-ID`, exact target, and environment before it can be available or verified. Login, account ambiguity, missing privilege, or a changed session blocks the task without changing another observation.

`human_only` observations use the `manual` route. They can support user handoff for execution, but cannot independently prove a task `verified`; verified read-back requires an `available` observation.

## Risk And Authorization

- `read_only` / `read_only`: no write; authorization is `not_required`.
- `standard` / `exact_preapproval`: a reversible, clearly scoped setting may use one approval covering an exact displayed batch of ACT IDs and digests.
- `high` / `action_time_confirmation`: DNS, permissions, persistent access, billing, production traffic, public submission, data sharing, advertising tracking, uploads, deletes, revocations, rotations, or another high-impact change requires confirmation immediately before that action.
- `handoff` / `user_handoff`: the user performs password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, secret-value entry, or a step with no safe agent route. An owner statement proves `configured` at most.
- `prohibited` / `prohibited`: the action is not executed. Record a blocker or `n/a` reason.

Approval is bound to the exact ACT ID and action digest. Record a concise user-authored source, never page text. Mark the grant `consumed` on the first mutation attempt, including timeout or unknown completion. Delete, revoke, rotate, disable, transfer, rollback, or retry after drift is a new action and needs new approval.

A non-read action may use `standard` only when its normalized environment value exactly equals `preview`, `development`, `dev`, `test`, `testing`, `sandbox`, `staging`, `stage`, or `local` and the operation is otherwise reversible. Compound or unknown labels, `prod`, `live`, public/store channels, and every upload, publish, transmit, delete, rotate, or revoke default to `high`. Manual or `human_only` execution uses `handoff` instead.

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

For every non-read operation in `configured` or `verified`, record a PASS `write` or `manual` evidence row. For `verified`, also record a separate PASS `readback` row and a PASS `behavior` row unless `Verification` uses `n/a: <specific reason>` or `n/a - <specific reason>`. Bare `n/a` is invalid. The mutation response cannot also be the read-back evidence.

Every evidence row carries `route;action-digest-or-n/a;target@sha#artifact`. Task evidence must use the task's current action digest and one of its exact release bindings. Measurement-source evidence uses `n/a` for the action digest and one of the source's exact release bindings. Write evidence uses the execution route; read-back and behavior evidence use the declared read-back route. Evidence from another digest, target, SHA, artifact, or route is stale and cannot satisfy the item. For the same item, binding, route, and evidence kind, only the chronologically latest result supports status; a newer `FAIL`, `BLOCKED`, or `UNCERTAIN` invalidates an older PASS.

Every `Checked` and `Updated` time is timezone-bearing RFC3339. Capability probes precede the evidence that relies on them. For a mutation, read-back and behavior evidence must be later than its latest matching PASS write/manual evidence. A ready target's check must be at or after all matching task and source evidence.

An ambiguous mutation result stays `uncertain` and records matching `UNCERTAIN` write or manual evidence. A failed read-back becomes `blocked` or `stale`; it never triggers automatic rollback or remediation.

## Target Readiness

Readiness is per release target. A target is `ready` only when:

- its source identity is a full lowercase Git SHA and its artifact/build identity is exact or explicitly `n/a`;
- every required ACT task bound to it is `verified`;
- every non-`n/a` Outcome Coverage row for it is `verified` through a verified `MS-*` source;
- no blocker names that target;
- the row has a checked timestamp and no blockers.

`handoff_ready` means every target claimed in the current activation scope is ready. It does not mean the outcome window has closed or the product met its adoption target.

The complete target set is the union of non-placeholder targets in ACT release bindings, measurement-source release bindings, and Outcome Coverage. Every active target needs exactly one Target Readiness row. **Open Blockers** uses structured `BLOCK-*` rows; an `open` global blocker or blocker naming a target prevents that target and the overall record from becoming ready.

## Gap Routing

- `code_gap` -> `delivery-harness`; name source IDs, target/SHA, missing behavior, and acceptance signal.
- `contract_gap` -> `product-definition-builder`; name the missing or contradictory requirement, TEST ID, metric, release target, or provider decision.
- `access_gap` -> owner; name the exact account, role, or login requirement without guessing credentials.
- `external_drift` -> mark stale, read back, recompute the action and digest, and request new authorization if a mutation remains necessary.
- delayed external state -> preserve `configured` or `pending`, record the next read-only check, and end the run.

## Checker Contract

Run:

```text
python skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md
python skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --prd docs/product/PRD.md
python skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --require-filled
python skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --prd docs/product/PRD.md --require-verified-sources --require-ready <release-target-id>
python skills/product-activation/scripts/check_activation.py --activation docs/ACTIVATION.md --show-action-digests
```

The checker is read-only. Exit `0` means the requested contract checks pass, `1` means findings were printed, and `2` means the input could not be read or the CLI was invalid. It never calls a provider, executes a recorded command, reads a secret, or edits a document.
