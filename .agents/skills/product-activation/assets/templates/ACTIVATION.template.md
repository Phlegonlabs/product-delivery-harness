# Product Activation

The live post-delivery activation record. Keep it at `docs/ACTIVATION.md`. Record exact non-secret targets, actions, read-back, and behavior evidence; never record secret values.

## Record

- Schema: product-activation/1
- Product: <fill>
- Activation owner: <fill>
- Release reference: <fill>
- Status: seeded
- Updated: pending
- Measurement window starts: pending

## Applied Profiles

| Profile | Applies | Reason | Owner |
| --- | --- | --- | --- |
| core | yes | Shared release, ownership, privacy, measurement, operations, and evidence baseline | <fill> |
| <surface-or-feature-profile> | <yes / no> | <why it applies or n/a> | <fill> |

## Capability Observations

`available` requires a live, non-mutating probe of the exact target. Installed tools alone remain `unobserved`.

| Route | Status | Supports | Surface | Target context | Checked | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| connector | unobserved | n/a | n/a | n/a | pending | pending |
| api | unobserved | n/a | n/a | n/a | pending | pending |
| cli | unobserved | n/a | n/a | n/a | pending | pending |
| browser | unobserved | n/a | n/a | n/a | pending | pending |
| computer_use | unobserved | n/a | n/a | n/a | pending | pending |
| manual | unobserved | n/a | user handoff | n/a | pending | pending |

## Outcome Coverage

Add one row for every PRD metric and every required `TEST-*` expected signal. Preserve each metric name and TEST ID exactly.

| Signal | Definition / target | Window | Release targets | Source ID | Status |
| --- | --- | --- | --- | --- | --- |
| <exact PRD metric name or TEST-ID> | <definition and target> | <measurement window> | <release-target-id> | pending | planned |

## Measurement Sources

| MS ID | System / retrieval | Route | Release targets | Owner | Status | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- |
| MS-001 | <provider and bounded query or read-back definition> | unselected | <release-target-id> | <fill> | planned | none |

## Activation Tasks

Keep one task per exact target mutation or read-only verification. Copy the block for additional actions.

<!-- activation-task-contract:start -->
### ACT-001 — <short action name>

- Source refs: <PRD-*, TEST-*, ARCH-*, deployment row, or owner decision>
- Release bindings: <release-target-id>@pending
- Depends on: none
- Operation: update
- Target: <exact provider/account/project/resource/setting without a secret value>
- Environment: <preview / production / store channel>
- Precondition: <exact non-secret state expected before action>
- Desired state: <exact non-secret state after action>
- Secret names: none
- Risk: standard
- Confirmation: exact_preapproval
- Execution route: unselected
- Read-back route: unselected
- Authorization: pending
- Authorization source: none
- Action digest: pending
- Authorized digest: pending
- Required: yes
- Status: pending
- Verification: <behavior-level expected signal or n/a with reason>
- Evidence IDs: none
- Blocker / N/A reason: none
- Updated: pending
<!-- activation-task-contract:end -->

## Verification Evidence

Mutation output and read-back must be separate evidence rows. Keep references non-secret.

| Evidence ID | Item ID | Kind | Checked | Result | Route | Reference |
| --- | --- | --- | --- | --- | --- | --- |

## Manual Handoff

| Item ID | Owner | Exact step | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| ACT-001 | <fill> | <only when the action requires user handoff> | <non-secret read-back proof> | n/a |

## Target Readiness

| Release target | Release identity | Status | Checked | Blockers |
| --- | --- | --- | --- | --- |
| <release-target-id> | pending | preparation | pending | ACT-001 |

## Open Blockers

- none
