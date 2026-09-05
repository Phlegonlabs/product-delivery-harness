# Runtime Upgrade Gate

Use this gate after runtime capability detection and during Resume Reconciliation. It covers the active host runtime and the loaded Product Delivery Harness release. A version string is supporting evidence; observable capability remains authoritative.

Observe the versions once per host session, not once per run. Neither the host binary nor the loaded Harness release can change under a live session without a restart, and `restart_required` already covers the case where an updater changed installed files. A later run in the same session copies the recorded observation forward; a fresh session, a restart, or a changed provider re-observes.

Record RUN-v11 `runtime_capabilities.runtime_adapter.version_gate` with normalized host and Harness versions, any minimum host or required Harness version, the host `session_id`, `loaded_contract_digest`, `installed_contract_digest`, one status, and concrete evidence. A semantic version alone is never enough to prove the loaded contract.

```text
unobserved | current | compatible_old | upgrade_required | restart_required
```

Use the statuses as follows:

| Status | Meaning | Scheduling result |
|---|---|---|
| `unobserved` | The parent has not checked both the current session and loaded Harness release | Defer runtime-worker nodes with `runtime_version_unobserved` |
| `current` | The current session and loaded Harness release satisfy the selected driver, and loaded/installed contract digests match | Dispatch normally |
| `compatible_old` | The active host or Harness release is old but still exposes every required capability | Let an already-active wave reach its safe boundary; defer the next wave with `runtime_upgrade_pending` |
| `upgrade_required` | A required capability or minimum version is missing | Defer runtime-worker nodes with `runtime_upgrade_required` |
| `restart_required` | An updater changed installed files, but this session still has the old runtime or skill loaded | Defer runtime-worker nodes with `runtime_restart_required` |

## Safe Upgrade Sequence

Never hot-upgrade a live worker or transfer its lease to a replacement process.

1. Stop new runtime dispatch. If the old version is `compatible_old`, allow only the current active wave and its dependency-ready streaming reviews to finish.
2. Preserve PLAN/RUN, terminal results, leases, worktrees, dirty files, commits, exact heads, and session evidence. If an incompatible worker is still active, request a checkpoint after its current tool call and quiesce it at that boundary.
3. Close or supersede the active wave before replacing the host runtime or the installed Harness skills. Updating installed software is a separate machine mutation and requires an explicit user instruction; the 12 RUN ledger actions do not silently authorize it.
4. Update the host through the installer that owns that binary. Updating installed Harness skills needs a separate explicit install/update instruction. Quiesce active skill-using sessions, then move any existing current-name destinations and the legacy `full-harness`, `prd-builder`, and `product-design-builder` directories to one timestamped backup under `~/.agents/skill-backups/product-delivery-harness/`, outside `~/.agents/skills/`. Copy `delivery-harness`, `product-definition-builder`, and `design-system-compiler` from the current repository checkout into `~/.agents/skills/`. Never overwrite or delete the prior copies. Do not alter Pi roles, model selection, fallback order, provider credentials, or unrelated packages.
5. Verify the three installed directories byte-match canonical, the three legacy IDs are absent from `~/.agents/skills/`, and the backup is readable. Restore the backup if verification fails. Recompute the installed contract digest, mark `restart_required` when it differs from the loaded digest, then start a fresh host session. Installed files changing on disk does not update an existing Codex task, Claude Code Workflow/session, or Pi session.
6. Re-run capability and version probes. Replace the old capability snapshot; do not merge it into the new one. Set `current` only when the new session exposes every selected-driver capability.
7. Validate preserved heads and evidence. Accept already-terminal exact-bound results normally. Create a new graph attempt and lease for unfinished work; never revive the old lease.

## Re-Orchestrate Remaining Work Onto The New Runtime

An upgrade does not resume the old orchestration. Once the fresh session records `current`, it owns every remaining task in the run:

1. Run the Resume Reconciliation Gate from `execution-state-model.md`: reconcile interrupted mission workers and review workers, re-observe canonical state against live Git heads and dirty worktrees, and only then select work. Start with `scripts/inspect_harness_run.py` to see how much of the run is already terminal — only the non-terminal remainder is re-orchestrated.
2. The selector re-derives the frontier from the preserved PLAN/RUN state. Every not-yet-succeeded node gets a new attempt and a new runtime binding on the new runtime; old bindings stay as history. Succeeded and integrated nodes keep their evidence and bound SHAs and are never re-executed — an upgrade re-binds work, it does not redo it.
3. A provider change is a re-orchestration boundary, not a bridge. When the fresh session's provider is not in a remaining node's `allowed_providers`, either replan — revise `allowed_providers` to include the new provider, which bumps the PLAN revision, rebinds the digest, and requires re-granting the affected ledger actions — or leave those nodes deferred with `runtime_unavailable` for a later run on an allowed host. The replan is the only way remaining tasks follow the newest runtime, and it needs the user's explicit instruction; a provider switch is never inferred from an upgrade alone.
4. Record the upgrade and each re-dispatch in `runtime_metrics`, and copy the fresh version-gate observation forward for later runs in the same session.

## Version Decisions

- Do not compare against an assumed latest public version during every run. Use the installed package metadata, the selected driver's documented minimum when one exists, and fresh capability probes.
- A generic host with no observable own-version is not `unobserved` for that reason: checking the loaded Harness release and the selected driver's live capability probe completes the observation, and the host-version field stays null with its evidence. A missing host-version string alone never defers a node.
- A missing optional feature does not force an upgrade when the selected route does not use it.
- A version at or above a documented minimum can still be `upgrade_required` when its observable capability or completion behavior is broken.
- A lower version can be `compatible_old` only when every capability needed by the active wave is observed and the active result channel remains usable.
- Record version checks once per host session and again only after an updater, restart, host handoff, or material capability change.

## Host Update Boundaries

- Codex: update the Codex host only through the installation method that owns that binary, then open a new top-level task.
- Claude Code: update Claude Code with its own installer, then restart. Dynamic Workflow also requires the currently documented minimum Claude Code version.
- Pi: update Pi with its native updater and start a fresh Pi session afterward. Standalone skill copies are separate user data and must not be overwritten or removed silently.
- Every host loads the Harness skills from the user skills directory, so the shared copy there is the only Harness update surface. Use the recoverable backup-and-copy sequence above, verify that only the three current IDs remain discoverable, then start a fresh session.
