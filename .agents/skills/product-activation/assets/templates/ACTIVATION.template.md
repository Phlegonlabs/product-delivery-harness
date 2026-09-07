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

| Observation ID | Route | Status | Supports | Target scope | Environment | Checked | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAP-001 | connector | unobserved | n/a | <exact service/account/project/resource> | <preview / production / store channel> | pending | pending |
| CAP-002 | api | unobserved | n/a | <exact service/account/project/resource> | <preview / production / store channel> | pending | pending |
| CAP-003 | cli | unobserved | n/a | <exact service/account/project/resource> | <preview / production / store channel> | pending | pending |
| CAP-004 | browser | unobserved | n/a | <exact service/account/project/resource> | <preview / production / store channel> | pending | pending |
| CAP-005 | computer_use | unobserved | n/a | <exact app/account/project/resource> | <preview / production / store channel> | pending | pending |
| CAP-006 | manual | unobserved | n/a | <exact service/account/project/resource> | <preview / production / store channel> | pending | pending |

## Outcome Coverage

Add one row for every PRD metric and every required `TEST-*` expected signal. Preserve each metric name and TEST ID exactly.

| Signal | Definition / target | Window | Release targets | Source ID | Status |
| --- | --- | --- | --- | --- | --- |
| <exact PRD metric name or TEST-ID> | <definition and target> | <measurement window> | <release-target-id> | pending | planned |

## Measurement Sources

| MS ID | Target | Environment | Retrieval | Route / capability | Release bindings | Owner | Status | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-001 | <exact provider target> | <preview / production / store channel> | <bounded query or read-back definition> | unselected;pending | <release-target-id>@pending#pending | <fill> | planned | none |

## Activation Tasks

Keep one task per exact target mutation or read-only verification. Copy the block for additional actions.

<!-- activation-task-contract:start -->
### ACT-001 — <short action name>

- Source refs: <PRD-*, TEST-*, ARCH-*, deployment row, or owner decision>
- Release bindings: <release-target-id>@pending#pending
- Depends on: none
- Operation: update
- Target: <exact provider/account/project/resource/setting without a secret value>
- Environment: <preview / production / store channel>
- Precondition: <exact non-secret state expected before action>
- Desired state: <exact non-secret state after action>
- Secret names: none
- Risk tags: none
- Risk: standard
- Confirmation: exact_preapproval
- Execution route: unselected
- Execution capability: pending
- Read-back route: unselected
- Read-back capability: pending
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

| Evidence ID | Item ID | Kind | Route / action / release binding | Checked | Result | Reference |
| --- | --- | --- | --- | --- | --- | --- |

## Manual Handoff

| Item ID | Owner | Exact step | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| ACT-001 | <fill> | <only when the action requires user handoff> | <non-secret read-back proof> | n/a |

## Target Readiness

| Release target | Source SHA | Artifact / build identity | Status | Checked | Blockers |
| --- | --- | --- | --- | --- | --- |
| <release-target-id> | pending | pending | preparation | pending | none |

## Open Blockers

| Blocker ID | Release targets | Kind | Owner | Next step | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
