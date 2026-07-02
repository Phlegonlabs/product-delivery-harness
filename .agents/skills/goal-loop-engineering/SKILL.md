---
name: goal-loop-engineering
description: Build and run Codex Goal loops with verification harnesses. Use when shaping or drafting /goal prompts, fitting PRDs or UI designs into long-running Codex goals, creating one-take UI coding prompts, planning epic/milestone/task flows with atomic commits, simplifying large-project context docs, converting vague work into measurable done criteria, designing loop engineering workflows, selecting thread automations/subagents/worktrees, or improving an agent harness for long-running Codex tasks.
---

# Goal Loop Engineering

## Purpose

Use this skill to turn an objective into a Goal prompt, context pack, epic/milestone/task loop plan, and verification harness. Keep the Goal prompt short; put durable context and loop state in files only when the work is large enough to need them.

## References

- Read `references/foundation-notes.md` when Codex Goal, skill, loop, harness, verification, or automation facts matter.
- Read `references/large-project-context-pack.md` when the goal depends on a PRD, UI design, Figma file, screenshots, architecture notes, or other large artifacts.
- Read `references/ui-one-take-prompts.md` when the goal involves frontend, UI refinement, design implementation, screenshots, responsive behavior, visual QA, or accessibility verification.

## Principles

- Treat the goal text as both instruction and completion criteria.
- If the environment exposes an active Goal, inspect it first. If no Goal is active, draft or normalize one from the user prompt.
- Do not paste full PRDs, design specs, or long acceptance lists into `/goal`; reference canonical files instead.
- Use the smallest durable doc set that preserves context after compaction or resume.
- Prefer deterministic verification as the hard gate. Use LLM review as critique, not final proof.
- For UI work, do not accept subjective criteria like "modern" or "polished" unless they are tied to design sources, screenshots, states, breakpoints, and visual evidence.
- Use epics only for large work with multiple product areas, workflows, or workstreams. Skip epics for small or single-feature work.
- An epic groups a product capability or workflow; a milestone is a verifiable phase inside an epic; a task is the atomic execution and commit unit.
- For long-running work, break milestones into verified tasks. A task is the smallest independently verifiable work slice.
- When commits are allowed, create one atomic commit after each task passes its verifier. Do not commit failed or unverified work.
- Treat repeated agent failure as a harness problem: improve tests, fixtures, docs, tooling, or observability before retrying.
- Do not run open-ended loops without stop/ask conditions, budget or cadence, and evidence requirements.

## Workflow

### 1. Intake And Classify

Classify the task before writing the Goal prompt:

```text
Mode: plan | create-goal | execute-active-goal | audit-loop | design-harness
Objective:
Scope:
Constraints:
Scale: small | context-heavy | long-running
Epic strategy: none | required
Canonical inputs:
Acceptance:
Verification:
Allowed actions: answer-only | draft-docs | create-files | run-verifiers | create-commits | create-automation | spawn-subagents
Task commit policy: verified-slice tasks; verify then commit; Conventional Commits unless repo conventions override
Stop or ask when:
Budget or cadence:
```

Use the small path when the request, acceptance criteria, and verification fit in one concise Goal prompt. Use the context-pack path when the work references a PRD, UI design, Figma, screenshots, architecture docs, multiple milestones, external artifacts, or recurring/long-running follow-up. Use epics when the project spans multiple product areas or has enough milestones that a flat list becomes hard to scan.

If an active Goal exists, inspect objective, status, budget, blockers, evidence so far, and next action before drafting or changing anything.

### 2. Prepare Context Pack Only If Needed

For context-heavy or long-running work, default to two docs:

- `docs/goal-context.md`: sources, PRD summary, UI/design summary, architecture notes, acceptance criteria, verification plan, open questions.
- `docs/loop-state.md`: epics, milestones, task queue, current progress, decisions, blockers, changed files, verification evidence, commits, next action.

Split into more files only when a source already exists, a section becomes too large to scan, or the team needs separate ownership. Point to source PRDs, Figma URLs/node IDs, screenshots, exports, issues, and architecture docs; do not duplicate long source bodies.

For planning-only requests, describe or draft the context pack. Create files only when the user asks for setup or execution. The context pack is done when canonical sources are linked, open questions are named, acceptance criteria map to verification, loop state is initialized, and long source bodies are not duplicated.

### 3. Draft The Goal Prompt

When the mode is `plan` or `create-goal`, output a ready-to-use Goal prompt under `Goal prompt:`. Do not force a `/goal` prompt for execution-only, audit-only, or active-goal debugging requests.

For small work:

```text
/goal [Objective]. Scope: [scope]. Done when [acceptance criteria]. Verify with [commands/checks/artifacts]. Keep evidence of verification. Stop and ask if [stop/ask conditions]. Stay within [budget/cadence].
```

For large work, use the template in `references/large-project-context-pack.md`.

For UI one-take work, use the template in `references/ui-one-take-prompts.md`.

### 4. Plan Epics, Tasks, And Harness

Design the loop as a small table or checklist:

```text
Epic:
Milestone:
Task:
Scope:
Done when:
Verifier:
Commit message:
Evidence:
Harness gaps:
```

For context-heavy or long-running work, decompose into epics only when useful, then milestones, then verified tasks. Do not start the next task until the current task is verified and committed, unless the current task is explicitly blocked. Use Conventional Commits by default, unless repo context or `AGENTS.md` defines another commit style.

Use this default cycle:

```text
observe -> choose active epic/milestone -> choose smallest task -> implement or investigate -> run task verifier -> commit verified task -> record evidence and commit hash -> update next task
```

Include these harness fields when relevant:

- Context: canonical files, links, issues, screenshots, logs.
- Tooling: commands, browser checks, MCP/connectors, fixtures, scripts.
- Oracle: the pass/fail rule for each milestone.
- Isolation: branch, worktree, sandbox, seed/reset plan.
- State: where progress and evidence are recorded.
- Review: human gates for irreversible, production, security, spend, or ambiguous quality decisions.

### 5. Execute, Verify, And Close

During execution, record meaningful state transitions, verifier results, decisions, blockers, evidence, and next action. Before declaring completion:

- Ensure epic, milestone, and task acceptance criteria are satisfied or the remaining gap is explicitly accepted.
- Run and record verification commands/checks.
- For every completed task, record verifier evidence and commit hash.
- Name skipped checks and residual risks.
- Update `docs/loop-state.md` or equivalent durable state for long work.
- Mention automation only when the user requested recurring work or the loop requires scheduled wake-ups.

## Output Shape

For a planning response:

```text
Goal:
Goal prompt:
Context pack: required | not needed
Epics, milestones, and tasks:
Commit policy:
Verification:
Harness gaps:
Next action:
Stop/ask conditions:
```

For an execution response:

```text
Outcome:
Evidence:
Changed files:
Commits:
Residual risk:
Next loop:
```
