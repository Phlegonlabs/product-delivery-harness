# Managed Delivery

Apply this file only after the entry routes work as `large`.
Literal `references/...`, `assets/...`, and `scripts/...` paths resolve from the delivery-harness skill root.

## Managed Route

Recover existing RUNs before replacement; see `references/execution-state-model.md`.

New managed work uses PLAN schema v6 and RUN schema v11. New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only files remain readable for recovery, but cannot authorize new execution.

Author PLAN from `assets/templates/HARNESS_PLAN.template.md`. Generate RUN with `scripts/new_run.py`; it derives initial state and grants nothing. RUN owns checkpoints, tasks, attempts, evidence, and closeout. With `--repo-root`, `new_run.py --out` and guarded checkpoint transitions automatically render `docs/tasks.md` from its declared coordination path; this non-canonical view preserves its Update Log. A refresh failure leaves successful RUN state intact; use `scripts/render_tasks_view.py` to repair or `--check` it. Read `references/execution-state-model.md` for the checkpoint set, source guards, and formal revision procedure.

### Reference Routing

Read only what the current decision needs:

- `references/contract-and-traceability.md`: frozen sources, traces, permissions, and file placement.
- `references/execution-state-model.md`: PLAN/RUN creation, resume reconciliation, authorization, state transitions, and host handoff.
- `references/graph-orchestration.md`: typed graph, provider policy, bounded experiments, retries and correction loops.
- `references/execution-task-decomposition.md`: mission/task split rules.
- `references/parallel-mission-selection.md`: parallel write-wave selection.
- `references/runtime-adapters.md`: the general capability and dispatch contract, applied only when managed execution needs it.
- `references/deployment-contract.md` and `references/branch-promotion-contract.md`: candidate-environment verification and post-RUN exact-SHA promotion to `main`.
- `references/worktree-thread-orchestration.md`: only after the selected adapter needs workers, threads, or worktrees.
- `references/verification-gates.md`: task, integration, UI, and evidence gates.
- `references/runtime-performance.md`: bounded context, event waits, streaming review, verifier batches, and machine telemetry.
- `references/runtime-upgrades.md`: host/Harness version observation, old-runtime wave boundaries, updater/restart handling, and fresh-session recovery.
- Runtime trust/publication: see `references/runtime-trust.md` and `trusted-host-publication.md`.
- `references/ui-implementation-contract.md`: every UI implementation or UI review.
- `references/gitignore-contract.md`: task-specific ignore classification and checks.
- `references/commit-convention.md`: before a Harness-managed commit.
- `references/design-input-updates.md` and `references/platform-archetypes.md`: only when those shapes apply.
- `references/orchestration-research-notes.md`: capability/version evidence, not routine execution.
- `references/worker-result-contract.md`: only while rendering or validating a delegated worker payload.

## Adapter Routing

Direct delegation uses `references/delegation-contract.md`; managed execution also uses `references/runtime-adapters.md`. Record observed capabilities and host identity (`generic` when unknown). Bridges need explicit bindings and authorization.

The adapter layer owns no shared state, authorization, review, integration, handoff or cleanup. Adding a host needs no provider section, fixed model defaults, launch script or schema change.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work:

1. Proactively inspect the current-session native tool surface, permission boundary, completion channel, worker slots, isolation, Git state, shared resources, host version, and loaded Harness version before the first launch.
2. Record observed capability independently from authorization. Missing authorization must never make an available driver disappear. Every advertised delegated driver needs observed `capability_probe` facts; unrelated surfaces need no inventory. For a web review that must inspect the live page, add `review.required_tools: ["chrome_devtools"]` in PLAN and record the selected driver's fresh reviewer-session probe under `runtime_capabilities.reviewer_tools.chrome_devtools`. Parent-session access, an installed package, or a CLI flag alone is not enough. A capability-probe child is read-only discovery, never review evidence, and still needs matching launch authorization; its result cannot update review state.
3. Do not cap `max_parallel_workers` at a small fixed number. The effective budget is the minimum of configured maximum, observed slots, isolation capacity, and the dependency-ready conflict-free frontier.
4. Before selection, record `observed.captured_at`, live Git facts, and `integration.batch_base_sha`. A green validator with empty `dispatchable_nodes` and `deferred_nodes` reasons `parent_state_unreconciled` or `batch_base_missing` means the live snapshot is incomplete; these are dispatch-time reasons, not an empty graph.
5. Enable scheduler fan-out only when at least two dependency-ready, nonconflicting write missions have isolated workspaces and exact authorization. Never run parallel writers in `shared_checkout`.
6. If no delegated driver is usable, only nodes without a mandatory delegate may use `sequential_parent` under `references/execution-state-model.md`. Required frontend and independent review nodes stay blocked until an eligible bound executor is available.

## Default Mission Topology

1. Map one independently testable goal to one mission: specifically, one product or contract outcome. A mission is not a phase label, subsystem backlog, or catch-all for everything touching one router. Blog, Settings, and user administration are separate missions when each can be reviewed and verified independently, even when they share auth, schema, navigation, or migration work.
2. Pass the Mission Cohesion Gate in `references/execution-task-decomposition.md` before readiness. Split a mission when its objective joins independently valuable outcomes, spans separate product surfaces or domain capabilities, needs unrelated verifier families, or hides more than one commit-sized outcome inside a task. Shared files, likely merge conflicts, or serialized resources are not reasons to bundle independent outcomes: freeze a shared foundation first, then represent ordering and conflicts with dependency and resource edges. Combine work only when separating it would create an unverifiable or nonfunctional half-state.
3. Plan tasks as ordered atomic commit boundaries. Complete one task's implementation and focused verifier, create its authorized task commit, and only then begin the next task. One commit cannot satisfy multiple tasks. A review repair is a separate atomic follow-up commit attributed to exactly one task; it does not make the original task broader.
4. Size each mission so its fixed worktree, handoff, validation, exact-head review, serial integration, and rerun overhead stays small against useful work; overslicing slows delivery. Treat 10-20 minutes of implementation plus focused verification as a normal bounded slice's upper shape, not a target; prefer the smaller cohesive mission when candidate splits both preserve independent verification. If frozen scope cannot fit one bounded worker slice, split independently testable outcomes before readiness rather than rely on a long-running child or timeout-driven repair.
5. For bounded read-only exploration, split independent substantive questions into distinct authorized sibling assignments under `references/delegation-contract.md`. Explorers report to the parent, never delegate; capacity limits waves, not assignment identity.
6. Give every writer one explicit `write_scope` and one isolated exact-base worktree. No active writers share a branch, file ownership, or exclusive runtime resource.
7. Freeze shared APIs, schemas, and types before dependent missions launch.
8. Verify repository, branch, base HEAD, and empty `git status --porcelain` before dispatch.
9. Render `WORKER_GOAL.template.md`; attach only the host contract and result fields that mission needs.
10. Validate returned identity, changed files, scope, verifier evidence, atomic task-commit attribution, commit order, and ancestry against live Git.
11. Require one exact-head pre-integration reviewer per applicable surface for every mission. Render its bounded packet with `scripts/render_review_packet.py`; do not attach the full PLAN/RUN when that slice is sufficient. Each review returns all blocking findings in one pass and allows at most one repair-and-re-review cycle. Group related findings into one root-cause failure family before repair. After repair, another variant of that family requires a structural repair with a complete acceptance matrix or return `REFINEMENT_REQUEST` / `contract_gap`. Add same-surface reviewer fan-out only when the user requests it or a recorded high-impact risk justifies it. A web `visual` review declares `required_tools: ["chrome_devtools"]`. A `frontend_code` review declares it when DOM state, console, network, runtime JavaScript, accessibility, or rendered behavior is part of its evidence. Backend-only and source-only reviews do not acquire a browser requirement. The selector defers a required tool as `reviewer_tool_unobserved:<tool>` or `reviewer_tool_unavailable:<tool>`; never replace the missing reviewer tool with the parent's browser session.
12. Dispatch one planned parent-owned read-only reviewer per integration surface on the unified SHA. Every new code-delivery PLAN adds a fresh sibling `security` review over all missions with the `code_security_verification` binding; it never uses the tree-identity skip. For other review, do not dispatch another same-scope review on an unchanged SHA; a byte-identical skip records both tree SHAs.
13. After those reviews pass, run one planned broad final validation suite. A security repair changes the SHA and invalidates its review and downstream gates.

Managed runs carry no wall-time percentage target. The objective is to stop paying for the same work twice. Follow `references/runtime-performance.md`; removing repetition never weakens authorization, exact-head review, evidence, or final validation.

## Workflow

### 2. Plan Large Work

Freeze only approved inputs needed by the graph: Product Definition revision, Stack Decision Checkpoint, source paths and digests, scope, architecture and design boundaries, acceptance criteria, trace IDs, write/deny scopes, dependencies, resources, stop conditions, and exact verifiers. Harness 0.38+ requires one canonical frozen PRD, architecture, and stack source for every plan and always runs the full sibling Product package checker with `--repo-root`. Harness 0.59+ new full-UI plans freeze `ui-design/3`, complete HiFi, `design-system/4` and one frozen derived HTML source, without wireframes. A retained `ui-design/2` package freezes its original conditional `design-system/3` contract; pins 0.56–0.58 use `ui-design/2`; older pins retain historical joins. Use the bounded review-repair graph and owner-attempt rules. A generic instruction to continue grants no new attempt.

Map active `platform-delivery/1` stages in architecture order. Use pass-only dependencies to completions and next stages. Shared foundations start first. Completion verifiers carry upstream platform TESTs. Marked contracts, including `not_required`, require fresh gates for planned features.

### 3. Pass Plan Readiness

Apply the direct route's self-review handoff before managed readiness.

Require frozen or explicitly `UNVALIDATED` inputs, concrete scope, a passed Mission Cohesion Gate, one bounded worker slice per mission with small fixed overhead, one atomic commit boundary per executable task, a verifier for every mission, known conflicts, exact action authorization, and an executable provider for every runtime-worker node. Reject readiness when independent outcomes are bundled only because they share files/resources or one task needs a catch-all commit. Executability covers the whole graph, not just the next node; each node's `allowed_providers` must include a host this delivery actually uses. An unavailable provider is a blocking readiness gap unless the user explicitly accepts deferral to another host. See `references/graph-orchestration.md`.

Apply `references/gitignore-contract.md`'s task ownership and `write_scope` gate when applicable.

### 4. Execute And Integrate

Acceptance/eval gates: `references/delivery-acceptance-contract.md`, `references/eval-acceptance-contract.md`.

After the version gate, run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation`. Global flags precede the subcommand. It binds the host, PLAN revision, and digest, plus runtime and RepoDigest for explicitly selected containers; `--probe-sandboxes` is diagnostic only. `lease-worker` copies selector bindings and materializes exact targets only from active wildcard grants. Record through guarded transitions, review exact heads, integrate serially, and close the wave.

### 5. Verify Local-First

New PLANs explicitly select `execution.isolation: "host"` for local build/lint/test. Host commands use current user permissions, not sandbox confinement. Containers remain optional with no fallback. See `references/verification-gates.md` for mode, source/Git guards, and evidence requirements.

Use the verification ladder:

1. focused task and worker checks selected from parent-observed changed files using `selection.mode: "changed_files"`;
2. exact-head mission review;
3. mission integration and interaction checks;
4. retained platform handoff at the completion mission's integrated SHA;
5. fresh exact-SHA unified review; only non-security review may reuse byte-identical-tree evidence;
6. `code-security-review`, repair when required, and fresh review of the new SHA;
7. final broad regression, browser E2E, platform TEST gates, breakpoint-by-state UI evidence, element overlap/clipping/overflow checks, visual, and migration checks; UI-surface runs also close the Final Visual Parity Loop from `references/verification-gates.md`;
8. applicable `references/gitignore-contract.md` checks, then `git diff --check` and complete final-diff review.

Host verifiers run fresh and serially per runner. Container `session_exact` reuse requires `exit 0`, clean matching inputs, read-only task/worker declarations, and `cache.deterministic_local: true` within one runner batch. Every consumer rechecks guards and runtime/image identity and retains its reservation, evidence, and origin. Keep request/result artifacts repository-external; no disk cache is used. Integration, cross-mission, final, browser, migration, mutable-environment, and network checks execute fresh. UI artifacts under `docs/goal/evidence/` use lowercase SHA-256 and bind to the integration head.

### 6. Complete

Harness 0.38+ RUNs close `local_only` at C after all gates and security pass. `archive_run.py --anchor-out <external path>` moves coordination, writes `ARCHIVE_RECEIPT.json` plus its immutable external anchor, and rolls back failure; commit only bookkeeping as A and reverify it. A current RUN never pushes. Under a new instruction, `push_archived_candidate.py --archive-anchor <path>` keeps request, attempt, receipt, and trusted-host evidence external; binds the canonical URL, machine-policy ID/hash/principal, and OS-managed verifier digest; and returns a URL-only no-force argv without invoking `git push`. A trusted host reloads the sanitized request, revalidates and signs evidence, publishes, and recovery-verifies readback before closing. Candidate Preview gates and separately authorized exact-SHA `main` promotion follow.

`product-activation` preparation requires a fixed SHA and separate authorization. Readiness, measurement handoff, outcome review, and SEO require promotion and production verification; no RUN grant authorizes them.
