# Large Project Context Pack

Use this when a Goal depends on a PRD, UI design, Figma file, screenshots, architecture notes, or other large artifacts.

## Core Rule

Do not fit a large project into `/goal` by pasting everything. Fit it by pointing a short Goal prompt at durable context and state files that survive compaction, resume, handoff, and automation wake-up.

## Default File Set

Default to two files:

```text
docs/goal-context.md  # sources, requirements, design, architecture, acceptance, verification
docs/loop-state.md    # epics, milestones, task queue, commits, progress, decisions, evidence, next action
```

Split into `docs/prd.md`, `docs/ui-spec.md`, `docs/implementation-plan.md`, or `docs/verification.md` only when the section is too large to scan, a source already exists, or separate ownership matters.

## Minimal Schemas

```text
# Goal Context

Sources: PRD, UI/design, architecture, issues, screenshots, exports
Product: outcome, users, must-have requirements, out-of-scope, open questions
Design: screens/flows, source URLs/node IDs, responsive rules, states, accessibility
Architecture: areas/modules, APIs/data, constraints
Acceptance: epic/milestone/task criteria, non-functional criteria
Verification: commands, browser/visual checks, regression coverage

# Loop State

Current objective:
Epic queue:
Active epic:
Current epic verifier:
Active milestone:
Current milestone verifier:
Active task:
Task queue:
Current task verifier:
Commit policy:
Completed:
In progress:
Blocked:
Open questions:
Decisions:
Verification evidence:
Files changed:
Commits:
Next action:
Stop/ask triggers:
```

## Intake Rules

Extract only decision-driving information:

- PRD: outcome, target users, must-have requirements, non-goals, workflows, business rules, edge cases, data/permission/integration needs, non-functional requirements, blocking questions.
- UI: Figma URL/node IDs, screenshots or exports, screen inventory, flows, layout rules, responsive breakpoints, tokens, interaction states, data states, accessibility expectations.
- Architecture: touched modules, APIs, data model, migration constraints, dependencies, existing conventions.

If a UI source is external and unavailable through tools, ask for screenshots, exports, or a written spec before treating the design as verified.

## Epic And Milestone Template

```text
Epic:
Outcome:
Done when:
Verification:
Milestones:
- Milestone:
  Scope:
  Done when:
  Verification:
  Risks:
  Open questions:
  Tasks:
  - Task:
    Scope:
    Done when:
    Verification:
    Commit message:
    Commit hash:
```

For smaller projects that do not need epics, use the milestone subset:

```text
Milestone:
Scope:
Done when:
Verification:
Risks:
Open questions:
Tasks:
- Task:
  Scope:
  Done when:
  Verification:
  Commit message:
  Commit hash:
```

Prefer thin vertical slices that connect UI, data, and verification over large horizontal rewrites. Use epics only when a flat milestone list becomes hard to scan. Each task should be the smallest independently verifiable work slice. If the project must start with architecture or harness work, make that a milestone with its own visible output.

## Goal Prompt Template

```text
/goal Deliver [project/outcome] using docs/goal-context.md as the source of truth and docs/loop-state.md as the run log. First read docs/goal-context.md; read linked PRD, UI/design sources, architecture notes, and verification sources only when needed to resolve ambiguity or verify design-sensitive work. Organize work by epic when the project spans multiple product areas, otherwise use milestones directly. Work epic by epic, milestone by milestone. Break each milestone into independently verifiable tasks. After each task passes verification, create one atomic commit and record commit hash plus evidence in docs/loop-state.md. An epic or milestone is done only when its acceptance criteria pass the listed checks and evidence is recorded. Stop and ask before changing scope, skipping a must-have requirement, diverging from design, taking destructive actions, or proceeding when requirements conflict.
```

## Atomic Commit Rules

- Commit only after task-specific verification passes.
- Commit must contain only that task's scoped changes.
- Use Conventional Commits by default, such as `feat: add checkout summary`, unless repo context or `AGENTS.md` defines another style.
- If verification fails, do not commit. Record the blocker, failed verifier, and next action.
- If a task produces harness or test work needed for later tasks, commit it as its own `test:` or `chore:` task.
- Record each completed task's commit hash and verification evidence in `docs/loop-state.md`.

## Harness Checks

Include checks that match the project:

- product behavior: unit, integration, e2e
- static health: typecheck, lint, format, build
- UI: browser flow, screenshot evidence, accessibility
- data: migration, seed, reset, fixture checks
- sensitive flows: permission or security tests

If no reliable verifier exists, create the verifier before implementing high-risk scope. If verifier creation is disproportionate, use structured review, record residual risk, and ask before proceeding.
