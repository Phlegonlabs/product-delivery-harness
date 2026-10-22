# Runtime Upgrade Gate

Use this gate after runtime capability detection and during Resume Reconciliation. It covers the active host runtime and the loaded Product Delivery Harness release. A version string is supporting evidence; observable capability remains authoritative.

Observe the versions once per host session, not once per run. Neither the host binary nor the loaded Harness release can change under a live session without a restart, and `restart_required` already covers the case where an updater changed installed files. A later run in the same session copies the recorded observation forward; a fresh session, a restart, or a changed provider re-observes.

Record RUN-v11 `runtime_capabilities.runtime_adapter.version_gate` with normalized host and Harness versions, any minimum host or required Harness version, the host `session_id`, `loaded_contract_digest`, `installed_contract_digest`, one status, and concrete evidence. A semantic version alone is never enough to prove the loaded contract.

```text
unobserved | current | adopted | compatible_old | upgrade_required | restart_required
```

Use the statuses as follows:

| Status | Meaning | Scheduling result |
|---|---|---|
| `unobserved` | The parent has not checked both the current session and loaded Harness release | Defer runtime-worker nodes with `runtime_version_unobserved` |
| `current` | The current session and loaded Harness release satisfy the selected driver, and loaded/installed contract digests match | Dispatch normally |
| `adopted` | The host cannot expose a startup digest, but the owner authorized the parent to re-read one fixed installed seven-skill contract at a quiescent boundary | Recompute the installed digest once for a selection; dispatch only while it matches the session-bound adoption, then require a fresh worker/reviewer digest check and reading evidence |
| `compatible_old` | The active host or Harness release is old but still exposes every required capability | Let an already-active wave reach its safe boundary; defer the next wave with `runtime_upgrade_pending` |
| `upgrade_required` | A required capability or minimum version is missing | Defer runtime-worker nodes with `runtime_upgrade_required` |
| `restart_required` | An updater changed installed files, but this session still has the old runtime or skill loaded | Defer runtime-worker nodes with `runtime_restart_required` |

## Safe Upgrade Sequence

Never hot-upgrade a live worker or transfer its lease to a replacement process.

When a host exposes skills as lazy filesystem references and cannot report what was loaded at session start, keep `loaded_contract_digest` null. A quiescent boundary has no proposed/active wave, leased/running worker or reviewer, reserved node attempt, or running node outside the exception below. The owner-authorized parent may take the RUN lock and run `adopt-runtime-contract --owner-source <explicit owner instruction> --reading-evidence <what the parent actually read> --expected-contract-digest <digest of the bytes reviewed>`. The transition verifies the executing Harness `VERSION` against the RUN pin, recomputes the installed seven-skill digest, and refuses a mismatch before changing RUN. A valid draft, ready, running, or blocked RUN may record this metadata observation; complete and cancelled runs cannot. The transition records an `adopted` receipt bound to the lock-owner session, preserves any prior receipt in immutable history, and changes no other gate. It does not convert the disk digest into loaded-at-start evidence, quiet `loaded_identity_unobserved`, bypass `restart_required`, or prove capability. Each later selection recomputes the live digest once when runtime-worker work is possible; drift defers dispatch. A replacement adoption needs the same quiet boundary and explicit owner source; the same digest may be adopted again only by a fresh session.

A running mission node may await integration after its exact current worker has terminal `worker_passed` state. Adoption exempts it only when mission, worker, lease, attempt and full head agree. Every required preintegration review must retain current-bound exact-head PASS evidence, including applicable nested-review evidence. Adoption uses integration's same pure review proof and complete manifest validation. Receipts, launch identity, verifier coverage and any ingestion-reconciliation receipt must remain valid. The adoption attempt records the exempted mission, node and head. No candidate, phase, prior receipt, attempt, counter, lease or grant changes. `update-role-bindings` retains its stricter boundary and still rejects running mission nodes.

Canonical terminal state does not prove host processes stopped. The parent must reconcile actual worker/reviewer termination and owned command cleanup before adoption. Retain concrete terminal/stop references in `--reading-evidence`; unknown liveness remains blocking. Already accepted S3/S4 receipts and child checks remain unchanged history. Fresh result recording still requires the current adopted digest.

The owner source and reading evidence are recorded attestations. They bind responsibility and make the review auditable, but no schema can cryptographically prove what text an LLM ingested; the digest checks prove only the bytes observed at their measurement points.

1. Stop new runtime dispatch. If the old version is `compatible_old`, allow only the current active wave and its dependency-ready streaming reviews to finish.
2. Preserve PLAN/RUN, terminal results, leases, worktrees, dirty files, commits, exact heads, and session evidence. If an incompatible worker is still active, request a checkpoint after its current tool call and quiesce it at that boundary.
3. Close or supersede the active wave before replacing the host runtime or the installed Harness skills. Updating installed software is a separate machine mutation and requires an explicit user instruction; the 12 RUN ledger actions do not silently authorize it.
4. Update the host through the installer that owns that binary. Updating installed Harness skills needs a separate explicit instruction. Quiesce active skill-using sessions, then run `install.sh` or `install.ps1` against `~/.agents/skills/`. It installs `delivery-harness`, `product-definition-builder`, `ui-design-builder`, `design-system-compiler`, `code-security-review`, `product-activation`, and `seo-growth-review`; retires `full-harness`, `prd-builder`, and `product-design-builder`; and writes the prior copies under `~/.agents/skill-backups/product-delivery-harness/`. Never overwrite or delete prior copies, and never replace the installer with manual move/copy commands. Do not alter installed roles, model selection, fallback order, provider credentials, or unrelated packages.
5. Require installer success and verify the current IDs load and legacy IDs are absent. A failed install rolls itself back. If the installed skills fail verification after the installer succeeded, restore by re-running the installer from a checkout of the previous release tag; it backs up the bad copy first. Then recompute the installed contract digest, mark `restart_required` when it differs from the loaded digest, and start a fresh host session. Installed files changing on disk does not update an existing host task or session.
6. Re-run capability and version probes. Replace the old capability snapshot; do not merge it into the new one. Set `current` only when the new session exposes every selected-driver capability.
7. Validate preserved heads and evidence. Accept already-terminal exact-bound results normally. Create a new graph attempt and lease for unfinished work; never revive the old lease.

## Re-Orchestrate Remaining Work Onto The New Runtime

An original passing result rejected solely for an inherited mission head may use [rejected-ingestion recovery](agent-execution-receipts.md#rejected-ingestion-of-a-passing-result). Preserve its original RUN and adoption receipt. Complete any separately authorized quiet-boundary adoption before recovery returns the mission node to `running`. Ordinary fresh results and reviews still require the current adoption.

An upgrade does not resume the old orchestration. Once the fresh session records `current`, it owns every remaining task in the run:

1. Run the Resume Reconciliation Gate from `execution-state-model.md`: reconcile interrupted mission workers and review workers, re-observe canonical state against live Git heads and dirty worktrees, and only then select work. Start with `scripts/inspect_harness_run.py` to see how much of the run is already terminal — only the non-terminal remainder is re-orchestrated.
   The inspector's retained failure counts and latest evidence are recovery input, not permission to rewrite history. Historical worktree drift stays separate from active drift, and phase does not prove process liveness; use the fresh runtime probe and guarded reconciliation/result paths before dispatch.
2. The selector re-derives the frontier from the preserved PLAN/RUN state. Every not-yet-succeeded node gets a new attempt and a new runtime binding on the new runtime; old bindings stay as history. Succeeded and integrated nodes keep their evidence and bound SHAs and are never re-executed — an upgrade re-binds work, it does not redo it.
3. A provider change is a re-orchestration boundary, not a bridge. When the fresh session's provider is not in a remaining node's `allowed_providers`, either replan — revise `allowed_providers` to include the new provider, which bumps the PLAN revision, rebinds the digest, and requires re-granting the affected ledger actions — or leave those nodes deferred with `runtime_unavailable` for a later run on an allowed host. The replan is the only way remaining tasks follow the newest runtime, and it needs the user's explicit instruction; a provider switch is never inferred from an upgrade alone.
4. Record the upgrade and each re-dispatch in `runtime_metrics`, and copy the fresh version-gate observation forward for later runs in the same session.

## Version Decisions

- Do not compare against an assumed latest public version during every run. Use the installed package metadata, the selected driver's documented minimum when one exists, and fresh capability probes.
- A host with no observable own-version is not `unobserved` for that reason: checking the loaded Harness release and the selected driver's live capability probe completes the observation, and the host-version field stays null with its evidence. A missing host-version string alone never defers a node.
- A missing optional feature does not force an upgrade when the selected route does not use it.
- A version at or above a documented minimum can still be `upgrade_required` when its observable capability or completion behavior is broken.
- A lower version can be `compatible_old` only when every capability needed by the active wave is observed and the active result channel remains usable.
- Record version checks once per host session and again only after an updater, restart, host handoff, or material capability change.
- An adopted contract travels with every runtime-worker directive. Before acting, each fresh worker or reviewer independently recomputes the digest, compares it with the adoption receipt, reads the fixed contract, and reports fresh reading evidence as `contract_adoption_check` (`worker-result-contract.md`). A parent receipt never substitutes for that child context. From Harness 0.55.1, the worker-result and review recording transitions reject a missing check, a digest that differs from the adoption receipt, or `matched` other than `true`.

## Host Update Boundaries

For maintenance of the skill-source repository, feature and development pushes do not trigger installation into the user's active release directory. After a verified formal release, compare the released seven-skill digest with the observed installed digest and, under the release's installation authority, run the official installer once when it changed. Retain backup, rollback and byte verification. An explicitly requested development installation is separate from the formal release channel. Record unchanged, updated or pending in the existing release handoff; a pending update is not a completed installation. Quiesce relevant sessions and restart only after successful installation when changed loaded inputs require it. This cadence grants no installation or host-stop authority in a consumer repository.

- Update the current host only through its owning installer, then start a fresh session. Preserve standalone skills, installed roles, model choices and fallback order.
- Every host loads the Harness skills from the user skills directory, so the shared copy there is the only Harness update surface. Use the repository installer transaction above, verify that only the seven current IDs remain discoverable, then start a fresh session.

## Design Before Implementation

Before starting product implementation after a skill update, apply `../../ui-design-builder/references/design-freshness.md`. Inspect changed rules against wireframe, every HiFi sibling and required design-system outputs. Record actual implementation status with evidence; absence of RUN proves nothing. Recheck first, repair affected design before coding when not started, and preserve valid decisions. Do not rerun terminal execution nodes or invent a skill reload. An explicit retained-PRD full design rebuild uses the UI translation/rebuild contract.

## Scoped Skill-Bundle Migration

On fresh-session work after a bundle update, use `document-sync-contract.md` to compare observed identities and current source inventories. Produce changed source → affected document/requirement → required recheck in existing task/RUN evidence. Inspect local rules before any same-scope patch; do not regenerate AGENTS or the whole PRD/design package from new templates. Preserve unaffected HTML pages, stable IDs, accepted decisions, closed RUNs and historical approvals. Unknown loaded identity remains unknown; an `adopted` RUN receipt may be recorded separately as the disposition only after its own quiet-boundary checks and never removes the document-sync finding.

The current contracts retain document-sync/1 snapshots and ui-hifi/2 packages. New or renewed HiFi approval requires reviewer shell v3 and the page-bound reviewer observations described by the UI output contract; reviewer shell v2 is historical. Retain old evidence and create current evidence for the changed candidate; never relabel an old receipt. Epic records link the current PRD and existing execution records, while small direct fixes may use those records alone.
