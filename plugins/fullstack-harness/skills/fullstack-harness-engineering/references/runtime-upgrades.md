# Runtime Upgrade Gate

Use this gate after runtime capability detection and during Resume Reconciliation. It covers the active host runtime and the loaded Full Stack Harness release. A version string is supporting evidence; observable capability remains authoritative.

Observe the versions once per host session, not once per run. Neither the host binary nor the loaded Harness release can change under a live session without a restart, and `restart_required` already covers the case where an updater changed installed files. A later run in the same session copies the recorded observation forward; a fresh session, a restart, or a changed provider re-observes.

Record RUN-v10 `runtime_capabilities.runtime_adapter.version_gate` with normalized host and Harness versions, any minimum host or required Harness version, one status, and concrete evidence:

```text
unobserved | current | compatible_old | upgrade_required | restart_required
```

Use the statuses as follows:

| Status | Meaning | Scheduling result |
|---|---|---|
| `unobserved` | The parent has not checked both the current session and loaded Harness release | Defer runtime-worker nodes with `runtime_version_unobserved` |
| `current` | The current session and loaded Harness release satisfy the selected driver | Dispatch normally |
| `compatible_old` | The active host or Harness release is old but still exposes every required capability | Let an already-active wave reach its safe boundary; defer the next wave with `runtime_upgrade_pending` |
| `upgrade_required` | A required capability or minimum version is missing | Defer runtime-worker nodes with `runtime_upgrade_required` |
| `restart_required` | An updater changed installed files, but this session still has the old runtime or skill loaded | Defer runtime-worker nodes with `runtime_restart_required` |

## Safe Upgrade Sequence

Never hot-upgrade a live worker or transfer its lease to a replacement process.

1. Stop new runtime dispatch. If the old version is `compatible_old`, allow only the current active wave and its dependency-ready streaming reviews to finish.
2. Preserve PLAN/RUN, terminal results, leases, worktrees, dirty files, commits, exact heads, and session evidence. If an incompatible worker is still active, request a checkpoint after its current tool call and quiesce it at that boundary.
3. Close or supersede the active wave before replacing the host runtime or Harness package. Updating installed software is a separate machine mutation and requires an explicit user instruction; the 12 RUN ledger actions do not silently authorize it.
4. Use the host-owned updater. Update the Full Stack Harness package with the repository updater. Do not alter Pi roles, model selection, fallback order, provider credentials, or unrelated packages.
5. Mark `restart_required`, then start a fresh host session. Installed files changing on disk does not update an existing Codex task, Claude Code Workflow/session, or Pi session.
6. Re-run capability and version probes. Replace the old capability snapshot; do not merge it into the new one. Set `current` only when the new session exposes every selected-driver capability.
7. Validate preserved heads and evidence. Accept already-terminal exact-bound results normally. Create a new graph attempt and lease for unfinished work; never revive the old lease.

## Version Decisions

- Do not compare against an assumed latest public version during every run. Use the installed package metadata, the selected driver's documented minimum when one exists, and fresh capability probes.
- A missing optional feature does not force an upgrade when the selected route does not use it.
- A version at or above a documented minimum can still be `upgrade_required` when its observable capability or completion behavior is broken.
- A lower version can be `compatible_old` only when every capability needed by the active wave is observed and the active result channel remains usable.
- Record version checks once per host session and again only after an updater, restart, host handoff, or material capability change.

## Host Update Boundaries

- Codex: update the Full Stack Harness marketplace/plugin, then open a new top-level task. Update the Codex host itself only through the installation method that owns that binary.
- Claude Code: update the marketplace/plugin, then run `/reload-plugins` or restart. Dynamic Workflow also requires the currently documented minimum Claude Code version.
- Pi: update Pi with its native updater and update a packaged Harness source with Pi's package updater. Start a fresh Pi session afterward. Standalone skill copies are separate user data and must not be overwritten or removed silently.
