# Development Rules

These are the rule owners for local data, implementation discipline, documentation style, and module size. They do not authorize a mutation.

## Protect Local Data

- Never delete, overwrite, or move important local data without explicit user approval.
- Preserve unrelated dirty files, branches, and worktrees.
- Avoid destructive Git and filesystem commands unless the user asked for that exact action.

## Keep Changes Simple

- Make the smallest change that satisfies the request.
- Do not add speculative abstractions or unrelated cleanup.
- Write short, direct documentation, comments, commit messages, and reports.

## Document Writing

Use the core writing rules of [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) for new or changed project documentation. This is a STE-informed guideline, not a claim of full conformity.

- Give each sentence one main idea. Use active voice and name the actor when ownership matters.
- Give each procedure step one instruction, using the imperative form. Put necessary conditions before the instruction and state the expected result when needed.
- In English prose, use at most 20 words per procedural sentence and 25 per descriptive sentence. Split long sentences without removing necessary information.
- Use the same term for the same concept. Define new technical terms and reuse established project terminology.
- Preserve literal code, commands, paths, identifiers, error messages and quoted source text. Code blocks, structured examples and literal strings are outside this guideline's prose counts.
- Preserve requirement strength, technical meaning, approvals and history. PRDs and specifications still include all required details and edge cases.
- Apply clarity and consistent terminology to other languages, using natural local phrasing. English word-count and dictionary rules do not apply to them.
- Use the existing document review to check clarity and meaning. Style preferences alone do not block delivery or replace behavior checks.

## Source Core Development Principles

For work consuming a Product Definition package, apply [pre-delivery-self-review](../pre-delivery-self-review.md) before execution. A backend-only binding check is not permission to defer required UI/self-review for a UI-bearing initial delivery. Keep scoped enhancement/maintenance routes and the reference's historical-approval catch-up rules.

- Follow [bounded-enhancement](../bounded-enhancement.md): reuse the accepted scope and valid action grants for repairs, document synchronization, module replacement and retesting. Do not repeat approvals for unchanged decisions. Never infer external, destructive, publication or installation authority.
- A module that fails accepted requirements may be replaced inside its write scope; preserve required interfaces, unaffected requirements, data and recoverable history. Bound repair attempts and keep unresolved gaps for the next round; ending a round is not a PASS.
- Reason from the problem's actual constraints, not from habit, inherited patterns, or how another project solved it.
- At 500 lines, review whether a module has more than one responsibility. Split when it improves ownership and verification; otherwise record why it stays together. This is a checkpoint, not a hard limit. The consumer template's hard cap does not apply to this skill-source repository.
- Don't add hacks, shims, or dual-path logic unless a frozen contract requires compatibility. Don't break an existing interface as unrelated cleanup; when an authorized change removes one, update its consumers and tests in the same change. Remove code only when verification proves it is dead.
- For multi-step, high-risk, or ambiguous work, state a brief approach, acceptance criteria, and test plan before editing. Small bounded work may proceed directly.
- Every change must be verifiable. For bug fixes, add or update a regression test when practical; otherwise explain the verification used.

## Consumer Core Development Principles

For work consuming a Product Definition package, apply `delivery-harness/references/pre-delivery-self-review.md` before execution. A backend-only binding check is not permission to defer required UI/self-review for a UI-bearing initial delivery. Keep scoped enhancement/maintenance routes and the reference's historical-approval catch-up rules.

### Bounded Enhancement And Test Evidence

- At every skill invocation, run the entry checklist in `delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work`.
- Follow `delivery-harness/references/bounded-enhancement.md`: reuse the accepted scope and valid action grants for repairs, technical document synchronization, module replacement and retesting. Do not repeat approvals for unchanged decisions. Never infer external, destructive, publication or installation authority.
- A module that fails accepted requirements may be replaced inside its write scope; preserve required interfaces, unaffected requirements, data and recoverable history. Reverify dependent behavior rather than preserving bad code through patches.
- Use `delivery-harness/references/delivery-acceptance-contract.md` for isolated synthetic accounts, separate mock/real-auth tests and per-platform evidence. Never use production data or a test login bypass in production.
- Bound repair attempts; retain unresolved PRD/TEST gaps for the next round. Ending a round is not a delivery PASS, a descoped requirement, or authorization to launch another task.

### Keep It Simple (KISS / YAGNI)

- Only do what's asked. No unrequested features, fallbacks, or "future-proof" abstractions.
- Prefer the simplest thing that works. Don't over-engineer.
- Don't "improve" code you weren't asked to touch.

### First Principles

- Reason from the problem's actual constraints, not from habit, inherited patterns, or how another project solved it.
- When a decision is non-obvious, derive it from what the product must do, then choose the simplest structure that satisfies it.

### Module Size Limit

- This rule governs the consuming project where this template is applied, not the Harness skill-source repository.
- New code modules, including tests, are limited to 500 physical lines.
- Split a module before it exceeds the limit. Give each module one clear responsibility and a small, explicit interface; do not compress lines or create arbitrary fragments to evade the cap.
- Record existing oversized modules for scoped follow-up. Applying this template does not authorize a whole-project refactor.
- Choose a bounded repair or replacement from the failing requirement and regression evidence. Preserve required compatibility, data and unrelated work; never delete and rewrite a module merely because it is problematic.

### Compatibility Changes

- Do not write speculative compatibility code or retain duplicate old/new implementations. Use one implementation for the accepted contract.
- Don't add hacks, shims, or dual-path logic unless a frozen product or repository contract requires compatibility.
- Don't remove or break an existing interface as unrelated cleanup. When an authorized contract change intentionally removes one, update its consumers and tests in the same scoped change.
- Remove code only when the requested change makes it dead and verification proves it is no longer used.

### Surgical Changes

- Make the smallest change possible. One goal per change.
- Only remove imports and variables your own edit orphaned.
- Avoid wide refactors unless you can prove they're safe.
- Keep diffs reviewable and easy to roll back.

### Think Before Coding

- For multi-step, high-risk, or ambiguous work, state a brief approach, acceptance criteria, and test plan before editing.
- Small bounded work may proceed directly after inspecting the relevant code and instructions.

### Verify First

- Every change must be verifiable (tests, scripts, output). If you can't verify it, don't ship it.
- For bug fixes, add or update a regression test when practical. If no reliable automated test fits, explain the verification used instead.
