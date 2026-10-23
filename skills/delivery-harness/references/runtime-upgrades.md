# Runtime Upgrade Gate

Use this gate after capability detection and during Resume Reconciliation.
It covers the host runtime and loaded Harness bundle. Version strings support observation; they do not prove capability.

Observe versions once per host session and again after restart, update, handoff or material capability change.
A fresh RUN in that session may reuse the unchanged observation with its origin.
Record host/Harness versions, required versions, session, loaded/installed digests, status and concrete evidence in `runtime_capabilities.runtime_adapter.version_gate`.
Keep an unobservable loaded digest null; disk bytes never prove startup identity.

| Status | Meaning | Scheduling result |
| --- | --- | --- |
| `unobserved` | Session or bundle identity is not established | `runtime_version_unobserved` |
| `current` | Required capabilities are observed and loaded/installed digests agree | Dispatch normally |
| `compatible_old` | An active old runtime remains capable | Finish only the active wave; then `runtime_upgrade_pending` |
| `upgrade_required` | A required capability or minimum version is missing | `runtime_upgrade_required` |
| `restart_required` | Installed bytes differ from the session's loaded bundle | `runtime_restart_required` |

Missing loaded or installed digest also defers with `runtime_contract_unobserved`.
Digest disagreement requires restart; do not fill an unknown loaded digest from installed bytes.
Historical `adopted` is accepted only with an explicit pin below 0.66.
Current dispatch always defers it with `pinned_bundle_or_restart_required`.
A 0.66+ RUN cannot use that status. Finish on the exact old bundle or restart through the pinned-bundle route.

## Run-Scoped Contract Pin

Keep one RUN on one Harness bundle from readiness to close.
Record the installed digest at readiness and after any authorized installation.
A new bundle applies to the next RUN; do not migrate an active RUN by editing retained fields.
Collect blocking source fixes into one reviewed release rather than installing each fix separately.
Owner-directed model changes apply to new assignments only. Preserve existing reservations and record the decision once.

A UI design round keeps the seven-skill digest recorded at intake through Visual Approval.
Only a blocking defect justifies one collected mid-round update, at a quiescent boundary with explicit installation authority.
Record the new digest and restart before loading changed rules. Preserve prior decisions and evidence with their original identities.

## Safe Upgrade Sequence

Never hot-upgrade a live worker or transfer its lease to a replacement process.

1. Stop new dispatch. Let only a capable old active wave reach its safe boundary.
2. Preserve PLAN/RUN, results, leases, worktrees, dirty files, commits, exact heads and session evidence.
3. Confirm actual worker/reviewer termination and owned process cleanup; canonical phases do not prove liveness.
4. Close the active wave before an independently authorized runtime or skill installation.
5. Use the owning installer and [Update Local Skills](governance/source-maintenance.md#update-local-skills); preserve prior copies and backups.
6. Verify installation, recompute the installed digest, and start a fresh host when loaded bytes differ.
7. Re-observe capabilities and version identity before selecting unfinished work.

The 12 RUN ledger actions grant no software installation or settings change.
Never overwrite or delete prior copies or backups.
A failed installer rolls back its own attempt. After a failed post-install check, rerun the installer from the previous release tag.
Do not replace installers with manual overwrites or alter credentials, roles or unrelated packages.

## Re-Orchestrate Remaining Work Onto The New Runtime

A fresh host does not inherit another session's capability claims.
First follow [Finishing A Run On Its Pinned Bundle](legacy-pins.md#finishing-a-run-on-its-pinned-bundle).
An incompatible active pin stays on that bundle; current tools do not silently adopt or migrate it.

For a compatible unchanged RUN, run Resume Reconciliation before selection.
Keep terminal results, attempts and SHAs as history. Unfinished work receives a fresh attempt and lease.
Never revive a lease or re-execute completed missions merely because the host restarted.
A provider outside `allowed_providers` needs an explicitly authorized PLAN revision or remains `runtime_unavailable`.

## Version Decisions

- Do not query an assumed latest public version during every RUN.
- An unavailable host version may remain null with evidence; required capabilities and Harness identity still need observation.
- A missing optional feature does not force an upgrade when the route does not use it.
- A version above the minimum can still fail its capability requirements.
- `compatible_old` applies only while every capability needed by the active wave remains observed.

## Host Update Boundaries

Feature/development pushes do not replace the installed formal release.
Follow [Update Local Skills](governance/source-maintenance.md#update-local-skills) for release installation and host restart authority.

## Design Before Implementation

After a bundle change, use the document-sync inventory and `pre-delivery-self-review.md` to identify affected design obligations.
Recheck first, then repair only affected scope under existing authority.
Preserve valid decisions, historical design bytes and terminal execution evidence.
An explicit full design rebuild follows the UI translation/rebuild contract.

## Scoped Skill-Bundle Migration

For fresh-session work, map changed sources to affected documents, requirements and required rechecks in the existing Epic or RUN evidence.
Never regenerate owner AGENTS instructions, the whole PRD or the design package from new templates.
Unknown loaded identity remains unknown. Preserve document-sync findings until their actual disposition is recorded.
Keep historical snapshots and approvals; create current evidence for changed inputs rather than relabeling old receipts.
