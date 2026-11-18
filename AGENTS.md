# Project Rules

## Skill Activation

Use this suite only when the user explicitly requests a named skill or continues its already requested workflow.
A `$skill-name` invocation or a natural-language request naming the skill qualifies; discussing a skill does not.
Required checks and dependencies stay within that requested outcome. A new top-level stage needs an explicit request.
Installed skills, seeded instructions, product documents and existing PLAN/RUN files do not activate a workflow.
For ordinary tasks, follow effective host and repository instructions plus the user's request.
Do not run Harness routing, document sync, Epic/index updates, template audits or PLAN/RUN solely because these instructions exist.
Existing data protection and action authorization still apply.

## Runtime Boundary

- This file is the entry. It contains authority boundaries and routes, not complete procedures. Preserve the current host's effective instruction discovery and precedence.
- Within an explicitly requested skill workflow, apply [Parent-Owned Delegation](skills/delivery-harness/references/delegation-contract.md) before direct or managed routing. Resolve executors and delegation from effective agent configuration, AGENTS instructions and observed tools. The actual frontend author reads the complete pinned `frontend-design` SKILL.md and applicable project design skills in its own context; verify the full-tree pin independently. Fresh independent review binds the exact candidate. One writer owns each checkout, including the parent; preserve required independent review and actual execution evidence.
- For explicitly requested managed execution, use [General Runtime Adapter](skills/delivery-harness/references/runtime-adapters.md) for observed native capabilities, authorization, isolation and result contracts. Capability does not grant an action.
- Within an explicitly requested `delivery-harness` workflow, direct work uses one writer, or a [Direct Fan-Out](skills/delivery-harness/references/direct-fan-out.md) of sibling writers, and one coherent verification sequence. Managed rules apply only after work routes into PLAN/RUN.
- Preserve unrelated local work. Important local data needs explicit owner approval before deletion, overwrite, or move.
- This source repository intentionally omits the template's Skill Bindings (it has no consumer stage slots), Behavior Specs (it has no feature files), Harness Version (it is the source, not an installed consumer), Deployment section and its Deployment and External Setup routes (it deploys and sets up no product), and the delivery-acceptance bullet (it has no product accounts or data). Its Git Flow replaces the template's Git Safety, and its Required Reading replaces the template's. Treat these as local choices, not drift, in the handoff audit.

## Worker Policy

Effective agent definitions and AGENTS instructions own worker selection, models, effort, fallback and delegation topology. Shared skills own methods, inputs, authorization, evidence and acceptance; they do not supply competing worker policy. Persisted RUN labels describe responsibilities, not native agent identities; preserve the pinned execution protocol.

## Delivery Autonomy

Landing policy: `.harness/landing-policy.json`. While it says `"landing": "owner_each_time"`, every push, merge and cleanup stays under the owner's instruction at the time. The owner sets `"landing": "epic_grant"` once this repository meets [Epic Landing Grant](skills/delivery-harness/references/branch-promotion-contract.md#epic-landing-grant); one grant per Epic then covers the actions that grant names. The parent reads the file from the frozen `main` base. This repository deploys no product, so `production_deploy` does not apply.

## Engineering Principles

These 24 principles say how to do authorized work well. They grant no action. Where one conflicts with a rule in this file or with a delivery-harness contract, the rule wins. Name a principle when it changed a decision, and say which decision.

Adapted from the PStack plugin by Lauren Tan, MIT License: [PSTACK-LICENSE](skills/delivery-harness/assets/third-party/PSTACK-LICENSE). Each entry keeps the original text; a sentence that pointed at a PStack-only skill is replaced.

### Core

#### Laziness Protocol

Apply when refactoring, evaluating diff size, or tempted to add abstractions, layers, or signal threading. Bias toward deletion and the smallest change that solves the problem.

- **Consolidate decisions.** Do not repeat the same choice in several places. Put it behind one source of truth and pass the result as a simple flag.
- **Minimize the diff.** Make the smallest change that solves the problem. Fewer lines beat "elegant" boilerplate.

#### Foundational Thinking

Apply before writing logic: choosing core types and data structures, sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the data structures right so downstream code becomes obvious.

Get the data shape right before writing logic. Define core types early, trace every access pattern, and choose structures that match the dominant paths. DRY the structure, not every line.

Before sharing state between actors, ask what happens if another actor modifies it concurrently. If the answer is not "nothing", isolate.

Scaffold first. Whatever helps every later phase (CI, tests, shared types) goes first, after removing dead code. Keep commits small and single-purpose.

#### Redesign From First Principles

Apply when integrating a new requirement into an existing design.

When integrating a change, don't bolt it onto the existing design. Redesign as if the requirement had been a foundational assumption from the start.

- Read all affected files and understand the current design
- Ask: "if we were writing this from scratch with this new requirement, what would we build?"
- Propagate the change through every reference: types, docs, examples, rationale sections
- Think about the whole redesign, then deliver it incrementally

This is the method for preserving option value when integrating changes into an existing design.

#### Attack the Premise

Apply when two or more fixes that share one premise have failed the same gate. Write the premise down and test it directly before you write another fix that assumes it.

When two or more fixes that share one premise have failed the same gate, suspect the premise, not the fixes.

- Write the premise down: the one sentence every failed fix assumed.
- Test it before the next fix. Find an observation that would come out differently if the premise were false, and make it. Look at how the failures are distributed, not only at how large they are.
- If the evidence contradicts the premise, look for what the failures share that it did not predict. If one part always lands on the losing side, change what puts it there instead of adding a mechanism that cleans up after it.

Do not start the next fix before the premise is written down and tested.

#### Subtract Before You Add

Apply when sequencing an addition, refactor, or rewrite. Remove dead code, redundant validators, and stub references first, then build on the simpler base.

When evolving a system, remove complexity first, then build. Default to subtraction.

Make simplification a continual investment. Leave the design slightly simpler and more capable behind the same or smaller surface than you found it.

- Sequence removal before construction
- Cut before you polish (get to the minimum before investing in quality)
- Design for observed usage, not speculative edge cases
- No speculative validators, parsers, or guards beyond what the spec demands
- Simplify prompts (remove redundant instructions, excessive templates)
- When a reference has no novel content, delete it rather than leaving a stub

#### Minimize Reader Load

Apply when reviewing or shaping code that's hard to trace. Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope.

Reader load is the work a reader must do to understand code. It has two independent axes: layers to trace between the question and the answer, and hidden or mutable state to hold in their head. Guard both.

- Collapse layers that only forward: wrappers with one caller, adapters with no second implementation, pass-through methods. Inline them.
- Shrink state scope: returns over mutations, locals over fields, fields over module state, module state over globals. Derive instead of sync.
- Name an invariant once at the boundary, not in every consumer.

The test: can a new reader answer "where does X come from?" and "what can change X?" in under 30 seconds? If not, cut layers or cut state.

#### Outcome-Oriented Execution

Apply during planned rewrites and migrations with explicit phase boundaries. Converge on the target architecture; don't preserve smooth intermediate states with throwaway compatibility code.

Optimize for the intended, verifiable end state rather than preserving smooth intermediate states.

**Why:** Keeping every intermediate step fully stable often creates temporary compatibility code that becomes long-lived debt. Converge on the target architecture and prove correctness at explicit verification boundaries.

**Core rule:**
- Prioritize end-state integrity over transitional stability
- Intermediate breakage is acceptable when it is planned, scoped, and reversible

**Guardrails:**
- Use this for planned rewrites and migrations with explicit phase boundaries
- Declare where temporary breakage is acceptable
- Keep high-signal checks for actively touched areas while migrating
- Require full static and runtime verification at plan completion

#### Experience First

Apply when product, UX, or feature-scope tradeoffs come up. Choose user delight over implementation convenience; ship fewer polished features over more rough ones.

When implementation convenience conflicts with user delight, choose delight.

- Every feature, control, and option must be justified
- Ship less, ship better (polished experience with three features beats rough one with ten)
- Prototype before committing (design decisions are cheaper in throwaway HTML than production code)
- Get the details right (transitions, alignment, spacing, feedback, error states)
- Tighten the core loop (every feature should serve the central workflow or get out of the way)

The user is whoever consumes the work. For a UI that is the end user. For a library or an internal API it is the colleague who imports it. The engineer who maintains the code next is a user too. Weigh their experience the same way, and explain impact from their perspective.

Foundations should serve the experience. Foundational thinking governs the *sequence* of work. This principle governs the *target*.

#### Exhaust the Design Space

Apply when facing a novel UI interaction or architectural decision with no precedent in the codebase. Build 2-3 competing prototypes and compare side by side before committing.

It also applies to product design decisions where user experience depends on feel, not logic.

#### Build the Lever

Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun.

When the work isn't trivial, build the tool that does it (a codemod, script, generator, or rerunnable check) instead of doing it by hand. The bar is triviality, not repetition. Skip the tool only for a couple of obvious edits.

- Do the first unit by hand, then build the tool and prove it by rerunning it on that unit. Make it safe to rerun.
- A deterministic tool beats fan-out. When you do fan out, write the recipe, the verification contract, and the fences as one skill the delegates read and cannot edit.
- Applying this produces a file. No script, codemod, generator, or delegate skill in the diff means you didn't apply it. Commit it when the work outlives the session.
- Build the smallest script that does or proves the job, never a framework.

### Architecture

#### Model the Domain

Apply when writing stateful logic, or when code branches a lot or repeats a shape assumption across files.

Encode the domain in a data structure instead of scattering it across conditionals. The right structure makes invalid states unrepresentable and deletes branches.

Reach for a state machine instead of scattered booleans or phase checks, a typed model instead of loose parameters, a map, registry, or discriminated union instead of branching spread across files, a reducer instead of ad hoc mutations, and an index, queue, or normalized collection where the access pattern calls for it.

Do not force it. Keep boring code when the shape is clear, local, and unlikely to grow, and distrust an abstraction that adds indirection without removing branches or invalid states.

The sign that you skipped this: a feature that grows an if/else chain by one more branch, or a second boolean that must stay in sync with the first.

#### Boundary Discipline

Apply when wiring validation, error handling, or framework adapters. Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions.

Validate, narrow types, and handle errors where data crosses a system boundary (CLI args, config files, external APIs, network). Inside, trust the types: no re-validation and no redundant nil checks. Parse raw data into domain types at the boundary, and keep transport and framework types out of the public surface. Business logic lives in pure functions with no framework dependencies. The shell that calls them is thin.

Two tests. Is this data crossing a boundary right now? If not, the validation is redundant. Can this be a pure function the shell just calls? If yes, extract it.

#### Type System Discipline

Apply when designing types, reviewing a function signature, or writing code in any statically-typed language. Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, exhaust variants, derive from authoritative schemas.

Make the compiler reject impossible states, mismatched primitives, and unhandled variants.

- **Brand semantic primitives.** If two arguments share a primitive type but mean different things, give each its own type. Validate once at creation.
- **External data is untyped until parsed.** JSON, RPC payloads, CLI args, config, environment variables, and database rows go through a parse function at the boundary that returns the typed model.
- **Derive types from authoritative schemas.** When a schema file owns a shape, derive the type from it instead of hand-rolling a parallel one.

#### Make Operations Idempotent

Apply when designing commands, lifecycle steps, or processing loops that run amid crashes, restarts, and retries. Converge to the same end state regardless of partial prior runs.

Design every state-changing operation to converge to the correct state however many times it runs and wherever the previous run stopped.

Derive each step from the state that exists, not from what the previous run meant to do. Read the current state, compare it to the goal, and apply only the difference.

Anything a run leaves behind (a lock, a temporary file, a half-written record, a claimed job) must be recognizable as stale by the next run, by evidence that holds wherever the previous run could have stopped. Write to a temporary path and rename it into place.

The test: what happens if this runs twice? What if the previous run crashed at every possible point? If the answer depends on what was left behind, add a reconciliation step.

#### Migrate Callers Then Delete Legacy APIs

Apply when introducing a new internal API while old callers still exist. Migrate callers and delete the old API in the same wave instead of preserving compatibility layers.

- Update tests to assert the new contract, and delete tests that only protect pre-refactor implementation details

**When this applies:**
- No external users depend on backward compatibility
- The project can absorb coordinated breaking changes
- The new API is part of a simplification or refactor initiative

#### Separate Before Serializing Shared State

Apply when concurrent actors might write to the same file, branch, key, or state object. Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant.

When concurrent actors might write the same file, branch, key, or object, first ask whether they need one shared object or are publishing independent facts. Default to giving each actor its own file, key, branch, or state directory, and merge only where the state is read. Two workers writing their own field into one `state.json` is still shared mutation.

Only when one shared write target is a real invariant, serialize access structurally (a lockfile, a single writer, sequential phases, compare-and-swap). Instructions are not concurrency control, and "we need a lock" is a smell to check first.

### Verification

#### Prove It Works

Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'

Verify every output by checking the real thing directly: run the feature, read the actual value, inspect the diff. Proxies (file mtimes, self-reports, cached output, "it compiles") do not count. When a check fails, suspect the observation method before the system.

Script the check when you can. A deterministic script that reruns the comparison beats a one-time look. Keep its output where the human can see it, and commit it only when the trail must be auditable later.

#### Fix Root Causes

Apply when debugging. Trace each symptom back to the first place the system went wrong and fix it there. A guard is a fix only when the state it handles is legitimate.

Fix the fault, not the place where it surfaced. The root cause is the first place the system did something it should not do, or failed to handle a state it should handle.

- Reproduce first. Ask "why" until the answer is a wrong decision in the code. When stuck, instrument and read the actual state.
- Ask whether the state that triggered the symptom is legitimate. If it is, handle it where the code broke. If it should never exist, a check there hides the bug, so find what produced it. Guards, retries, swallowed errors, clamped values, and discarded state are the usual ways to hide a bug.
- Fix the pattern, not the instance. Find every place with the same fault.
- If the deciding fact took a deep dig, propose the cheap, always-on signal that would have shown it at first look.

#### Sequence work into verifiable units

Apply to multi-step work (sweeps, migrations, runs of similar edits) and to how you stack commits and PRs. Break work into small units that each end in a verifiable state, check each before the next, and order delivery so the sequence proves itself to a reviewer.

Order work as small units that each end in a state you can check, and do not advance until the current one is green.

In a sweep, migration, or run of similar edits, each unit is a bracket: known-good state, one change, run the check, proceed. Run the per-unit check even when a tool does the edits.

Deliver in the order that proves the work: the failing test first, then the fix. The subtraction before the reshape. The baseline before the treatment. Each commit lands on its own.

#### Test Behavior, Not Implementation

Apply when you write, change, or keep a test. Assert what the code's users can observe, so that the test fails when that behavior breaks and keeps passing when only the internals change.

A test is a claim about what users of the code can observe through its interface: return values, errors, state they can read back, and effects on outside systems. Private helpers, internal call order, and intermediate data are implementation.

Judge each test against two imagined edits:

- **Break the behavior** (a wrong value, a skipped or doubled effect). If the test still passes, it proves nothing. The usual causes are a loose assertion, an expected value computed by the code under test, and an assertion on data the test built itself.
- **Change the internals** and keep every observable result. If the test fails, it is pinned to the implementation.

Keep a test that catches the first edit and survives the second. Rewrite or delete the rest. Drive the code through its public interface with a concrete input, and derive the expected value from the requirement. What an external service receives is behavior. A call to an internal helper is not. Pair "this never happens" with a case where it does happen. Assert the error type that callers branch on, not the message.

#### Explain the Number

Apply before you measure, and before you trust, report, or act on a number you measured: a speedup, a regression, a throughput, a latency, or an eval result. Find what limits it, and rule out that it measured something other than the work you think.

- **Write the decision before you run.** Name the result that would change it, and the noise floor. Stop when the run-to-run spread is larger than the effect.
- **Ask "why not double?"** Name the resource or code path that bounds the result, from a profile or counters taken during a run. A guess from reading the code is not a limiter.
- **List what else the number could be measuring** (errors, skipped or cached work, code that never ran, an untuned side, noise, a piece too small to matter) and rule out each one with evidence.
- **Keep the run count, the spread, and the limiter with the number.**

For a performance number, name the limiter, run both sides tuned and alternating, count errors, and confirm the work happened inside the timed region. For an eval result, ask whether every run did the task, whether the gap holds across trials and models, and whether the scenario matters.

### Delegation

#### Guard the Context Window

Apply when context is filling up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread, not raw payloads.

**Why:** Context overflow degrades reasoning quality, creates compression artifacts, and halts progress.

**Pattern:**
- **Size phases and cap scope.** Limit files per phase, set turn budgets, account for mechanism costs.

#### Never Block on the Human

Apply when tempted to ask 'should I do X?' on reversible work.

The human supervises asynchronously. Agents must stay unblocked. Make reasonable decisions, proceed, and let the human course-correct after the fact. Since code changes are reversible and reviewable, a wrong decision usually costs less than blocking.

- Proceed, then present. Do the work, show the result. Don't ask "should I do X?" Do X, explain why.
- Make the system self-healing. When you notice a problem, log it and fix it in the next round.
- Irreversible actions (force-push, delete production data, send external messages) still require confirmation.
- Reversible actions (write code, edit notes, split tasks) should proceed without blocking.
- Product direction comes from the human. Execution should not block.

In a repository that uses the Product Delivery Harness this principle works inside a recorded Epic landing grant and never replaces an owner decision: product scope, visual direction, spending, destructive data operations and owner-only paths stay with the owner.

### Meta

#### Encode Lessons in Structure

Apply when you catch yourself writing the same instruction a second time, or notice a recurring correction. Encode the rule as a lint, metadata flag, runtime check, or script instead of more text.

If the lesson needs judgment and cannot be encoded, make the instruction more prominent and add an example of the failure mode.

**Corollary:** If the fix is structural, only use the structural fix. The instruction is the symptom.

## Mandatory Governance Routes

Harness-specific routes below apply only within an explicitly requested skill workflow.
Source reading, verification and Git rules still govern maintenance of this repository without starting a consumer delivery workflow.
Read the complete linked section before its applicable action. The links are mandatory, and an owner file's rules cannot be widened by this entry.

| Trigger | Complete rule owner |
| --- | --- |
| Explicit invocation of a skill in this suite | [Project Entry](skills/delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work) |
| Task start; significant edit, commit, merge, branch switch, or observed external change | [Repository Change Checkpoints](skills/delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints) |
| Completion or handoff | [Handoff Documentation Audit](skills/delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit) and [Source Completion](skills/delivery-harness/references/governance/task-and-handoff.md#source-completion) |
| Local deletion, overwrite, or move | [Protect Local Data](skills/delivery-harness/references/governance/development-rules.md#protect-local-data) |
| Implementation or repair | [Keep Changes Simple](skills/delivery-harness/references/governance/development-rules.md#keep-changes-simple) and [Source Core Development Principles](skills/delivery-harness/references/governance/development-rules.md#source-core-development-principles) |
| New or changed documentation | [Document Writing](skills/delivery-harness/references/governance/development-rules.md#document-writing) |
| A task introduces or retires a local-only file class | [Gitignore Contract](skills/delivery-harness/references/gitignore-contract.md) |
| Product requirements, architecture, UI impact, redesign, pricing, or partner channel | [Product Contracts](skills/delivery-harness/references/governance/product-contracts.md#source-keep-product-contracts-current) |
| Pricing, paid access, purchase-gated features, or outside sellers | [Monetization And Partner Channels](skills/delivery-harness/references/governance/product-contracts.md#monetization-and-partner-channels) |
| Editing `skills/`, a documented flow, or running a seeded consumer flow | [Source Required Reading](skills/delivery-harness/references/governance/source-maintenance.md#required-reading) |
| Decomposing PRD work into missions | [Mission Task Split](skills/delivery-harness/references/governance/source-maintenance.md#mission-task-split) |
| Branch, commit, integration, archive, publication, cleanup, or source main landing | [Source Git Flow](skills/delivery-harness/references/governance/source-maintenance.md#git-flow) |
| Every atomic source task before verification | [Required Verification](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) |
| Formal release, version promotion, tag, bundle installation, or host reload | [Update Local Skills](skills/delivery-harness/references/governance/source-maintenance.md#update-local-skills) and [Required Verification](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) |
| Review or acceptance claim | [Source Review Guidelines](skills/delivery-harness/references/governance/source-maintenance.md#review-guidelines) |
| Creating or resuming managed PLAN/RUN | [Managed And Consumer Delivery](skills/delivery-harness/references/governance/managed-delivery.md#managed-product-delivery-harness-runs), [Conditional Project Operating Rules](skills/delivery-harness/references/project-operating-rules.md#managed-product-delivery-harness-runs), and the canonical Harness [SKILL.md](skills/delivery-harness/SKILL.md) |

The Epic and index record observed work; neither record grants product approval, marks a test PASS without evidence, or authorizes a commit, branch, install, push, deployment, cleanup, publication, or external action.
