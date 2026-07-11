# Multi-Thread Orchestration Research Notes

Research date: 2026-07-04. This file records the facts and sources behind the skill's orchestration decision. Re-verify against the sources before changing orchestration guidance in `SKILL.md`, templates, or `worktree-thread-orchestration.md`.

Prior research: `codex-goal-prompt/references/research-notes.md` (2026-06-08, spot checks 2026-06-17 and 2026-06-22). This note extends it with Claude Code coverage and re-verifies Codex as of codex-cli 0.142.5.

## Decision

The canonical orchestration mode enum, used verbatim everywhere in this skill:

```text
single-checkout subagents | sequential single thread | mission worktrees | Codex-managed app worktrees
```

- **Default: `single-checkout subagents`.** One checkout, one branch, parent-owned state. Write missions run one at a time through subagents; read-only work (audits, reviews, verification lenses) fans out to parallel subagents. Confirmed still correct for both runtimes.
- **Fallback: `sequential single thread`.** The parent runs missions itself with identical gates when the runtime has no subagent primitive.
- **Opt-in: `mission worktrees`.** Parent-orchestrated parallel write workers, one worktree/branch per mission. Justified only by parallel-write wall-clock need, resource isolation, high-risk refactors needing a stable parent checkout, or long-running background work.
- **Opt-in: `Codex-managed app worktrees`.** The Codex app/automation creates and owns the worktree; record it instead of hand-creating paths.

The two-layer hierarchy (parent/orchestrator -> mission workers, tasks sequential inside each worker) is the portable shape: it is the *maximum* Codex allows (`max_depth = 1`) and a deliberate simplification on Claude Code (which allows deeper nesting).

## Re-Verification Checklist

Before editing orchestration guidance, re-check:

- Codex `[agents]` keys and defaults: `max_threads` (6), `max_depth` (1), `job_max_runtime_seconds`; built-in `default` / `worker` / `explorer`; spawn-on-explicit-request default.
- Codex feature flags: `goals` and `multi_agent` stable; watch `multi_agent_v2` and `enable_fanout` (both under development as of 0.142.5).
- Codex subagent result semantics: barrier-style ("waits until all requested results are available, then returns a consolidated response"); parent receives terminal subagent errors (added 0.142.0).
- Codex app worktrees: detached HEAD start, one thread per worktree, `.worktreeinclude` for ignored files, keeps most recent 15, automations run on dedicated background worktrees.
- Claude Code subagents: background-by-default (v2.1.198+), completion notifies the parent conversation, `isolation: worktree` frontmatter with auto-create and auto-cleanup-if-unchanged, nesting depth limit 5.
- Claude Code higher-level surfaces: agent view (research preview), agent teams (experimental, disabled by default, no worktree isolation), dynamic workflows, `/batch`.

## Runtime Capabilities (verified 2026-07-04)

### Codex (codex-cli 0.142.5; `goals` stable/true, `multi_agent` stable/true)

- Manager-worker model: the main agent orchestrates "spawning new subagents, routing follow-up instructions, waiting for results, and closing agent threads".
- Spawn is explicit-request-only by default: "Codex only spawns a new agent when you explicitly ask it to do so." Fan-out must be written into the goal/prompt. (New in 0.142.0: app-server clients can configure delegation as disabled, explicit-request-only, or proactive per thread/turn; CLI default remains explicit.)
- `max_depth = 1`: exactly two layers, orchestrator -> workers; workers cannot spawn further.
- `max_threads = 6` default concurrent thread cap.
- Result delivery is a barrier: "Codex waits until all requested results are available, then returns a consolidated response." No incremental completion notification to the parent.
- Reliability improvements in 0.142.0: parent agents receive terminal subagent errors instead of seeing failed work as success; token budgets track usage across agent threads, remind on remaining budget, and abort turns when exhausted.
- Manual parallel mission threads: the parent is not notified when a separately launched thread finishes; the user relays completion. This is the main coordination cost of `mission worktrees` on Codex.
- App-managed worktrees: created automatically per thread, start detached HEAD, one thread per worktree, `.worktreeinclude` copies needed ignored files, most recent 15 kept, automations run on dedicated background worktrees.
- Best practices: one thread per coherent unit of work; fork only when work truly branches; subagents for bounded exploration/tests/triage; "Running live threads on the same files without using git worktrees" is a listed common mistake.

### Claude Code (docs as of July 2026)

- Subagents run in the background by default (v2.1.198+) and the parent is notified when one completes: "When it finishes, its result arrives as a message in your main conversation." This enables event-driven integration instead of barrier-only waits.
- `isolation: worktree` on a subagent gives it an isolated checkout automatically; "The worktree is automatically cleaned up if the subagent makes no changes." This makes worktree-isolated parallel writes much cheaper to opt into than Codex manual threads.
- Nesting depth limit is 5 (subagents can spawn subagents as of v2.1.172); this skill still uses two layers for portability with Codex.
- Failed background subagents surface the error and last output to the parent; partial work is not lost.
- Higher-level surfaces exist but are not this skill's default: agent view (background sessions, auto-moved into own worktrees; research preview), agent teams (shared task list, no worktree isolation, experimental/disabled by default), dynamic workflows (script-driven fan-out), `/batch` (packaged worktree-isolated subagent fan-out).

## Scheme Comparison

| Dimension | single-checkout subagents (default) | sequential single thread | mission worktrees | Codex-managed app worktrees |
|---|---|---|---|---|
| Write conflict surface | none (writes serialized) | none | isolated files; still shares ports/DB/services | isolated files; detached HEAD |
| Coordination cost | low: one branch, no merges | lowest | high: preflight, merge order, integration reruns, cleanup | medium: app owns lifecycle |
| Completion signal | Claude Code: parent notified; Codex: consolidated barrier return | n/a | Codex: user relays; Claude Code: parent notified (worktree subagents) | app UI; no parent-thread signal |
| Wall-clock gain | read-only fan-out only | none | full parallel writes | full parallel (app-driven) |
| Resource isolation | single env, no contention | single env | must be planned per mission (port/DB/seed) | files only; env still shared |
| Integration cost | none beyond final E2E | none | merge in dependency order + verifier reruns | pull from worktree/branch |
| Evidence flow | parent records in `RUN.md`; optional temporary report | parent records in `RUN.md` | `docs/goal/evidence/M<n>/REPORT.md` -> parent folds into `RUN.md` | thread output + optional report |
| Runtime support | both runtimes, stable | any runtime | both, but notification differs by runtime | Codex app only |

## Rationale

1. Parallel writes in one checkout remain unsafe on both runtimes: lockfiles, build caches, generated files, dev servers, and local databases collide even with disjoint write scopes. Codex's own best practices list same-files parallel threads without worktrees as a common mistake.
2. Worktrees isolate files, not ports, databases, secrets, queues, caches, or running services; full-stack missions still need explicit resource isolation, so worktree parallelism carries planning cost regardless of runtime.
3. Serialized write missions with read-only fan-out capture most subagent value (context isolation, parallel verification lenses) at near-zero coordination cost, and the two-layer shape fits Codex's hard `max_depth = 1`.
4. The runtimes now differ mainly in worker-completion signaling and worktree ergonomics. Claude Code's notification and auto-managed worktrees lower the cost of `mission worktrees`, so the opt-in threshold can be lower there, but the default does not change: the trigger for worktrees is parallel-write need or isolation need, not runtime convenience.
5. Codex 0.142.0 removed the biggest default-mode risk (silent subagent failure) by surfacing terminal errors to the parent, further supporting single-checkout subagents as default.

## Runtime Differences That Affect Execution

| Concern | Codex | Claude Code |
|---|---|---|
| Worker completion | Barrier: consolidated response when all requested workers finish; manual threads need user relay | Parent notified per background subagent completion |
| Worktree creation for workers | Manual `git worktree add`, or Codex app-managed | `isolation: worktree` auto-create/auto-cleanup |
| Depth | 2 layers max (`max_depth = 1`) | up to 5; keep 2 for portability |
| Concurrency cap | `max_threads` (default 6) | runtime-managed; workflows cap ~10-16 |
| Budget control | Token budgets across agent threads (0.142.0), abort on exhaustion | Session/turn budget directives |
| Subagent failure | Terminal errors surfaced to parent (0.142.0+) | Error + last output surfaced; partial work kept |

## Sources

- Codex subagents (manager-worker, `[agents]` keys, spawn-on-request, barrier semantics): https://developers.openai.com/codex/subagents
- Codex app worktrees (detached HEAD, `.worktreeinclude`, retention, automations): https://developers.openai.com/codex/app/worktrees
- Codex best practices (thread-per-unit, fork/subagent/worktree guidance, common mistakes): https://developers.openai.com/codex/learn/best-practices
- Codex changelog (0.142.0 token budgets, delegation modes, terminal subagent errors): https://developers.openai.com/codex/changelog
- Local verification: `codex features list` on codex-cli 0.142.5 (2026-07-04): `goals` stable/true, `multi_agent` stable/true, `multi_agent_v2` under development/false, `enable_fanout` under development/false.
- Claude Code parallel-agents overview (subagents / agent view / agent teams / workflows / worktrees / `/batch`): https://code.claude.com/docs/en/agents
- Claude Code subagents (background default, completion notification, `isolation: worktree`, depth limit): https://code.claude.com/docs/en/sub-agents
- Prior research: `~/.claude/skills/codex-goal-prompt/references/research-notes.md` (2026-06-08)
