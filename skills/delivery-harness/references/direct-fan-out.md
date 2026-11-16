# Direct Fan-Out

Use this on the [Direct Route](../SKILL.md#direct-route) when small work holds two or more parts that can be written at the same time. It creates no PLAN/RUN. Work whose parts depend on each other, or that must survive this session, is large and uses the managed route.

## When It Applies

All of these hold:

- Each part is small on its own: one writer, one bounded outcome, one focused verifier.
- No part needs another part's output. A shared token, type, schema or helper that several parts need comes first as ordinary direct work by one writer, and the fan-out starts from the commit that holds it. For UI implementation the tokens and primitives are that foundation ([UI Build Order](execution-task-decomposition.md#ui-build-order)). A shared contract that needs its own review before the dependents start makes the work large.
- The parts' write scopes do not overlap, and no two parts need the same exclusive runtime resource such as a fixed port, a database or an external sandbox.
- The whole fan-out finishes in this session.
- The host gives each writer an isolated checkout.

When one fails, keep one writer or route the work large. When one stops holding part-way, let the running parts finish, merge what passes, and continue the rest with one writer or a PLAN.

## Authorization

Ask once per round for the bundle: sibling writers, one worktree and local branch per writer, local commits, and local integration into the work branch. An owner instruction to run the work in parallel or with several agents is that grant. It covers every part and every merge of the round. It never covers push, worktree removal or branch deletion.

The work branch follows the ordinary branch rule and exists before launch. A writer branch is a runtime allocation, as in a managed wave: name it from the work branch and the part ID, check that the name is unused, and keep it local.

## Launch

1. List the parts in the existing Epic or task record: ID, outcome, write scope, focused verifier. Create no other record.
2. Check the scopes with `python "<delivery-harness-skill-root>/scripts/worktree_fanout.py" scopes --part <id>=<claim>[,<claim>...] --part <id>=<claim>[,<claim>...]`. A test file is a write path: give each part its own test file, because two parts that add a test to one shared file overlap. Remove an overlap by moving the shared path into the foundation work, never by narrowing a scope a part really needs.
3. Start from a committed work branch and record its head as the base SHA.
4. Launch every part at once, each in its own worktree cut from the base SHA. Each writer receives an [assignment packet](delegation-contract.md#assignment-and-result-evidence) from [ASSIGNMENT.template.md](../assets/templates/ASSIGNMENT.template.md) carrying its write paths, the paths it must not touch and its verifier. A writer commits each step and never merges, rebases, pulls or pushes. A frontend part carries the [frontend dispatch brief](delegation-contract.md#resolve-roles-before-direct-or-managed-work).

Observed capacity bounds the number of parts. There is no fixed number.

## Merge On Finish

When a writer returns, the parent acts at once. It does not wait for the other parts or for the owner.

1. Run `python "<delivery-harness-skill-root>/scripts/worktree_fanout.py" merge-check --repo-root <root> --base <sha> --head <branch> --worktree <worktree> --scope <claim>` from the work branch. Repeat `--scope` for each claim; add `--deny <claim>` for a path the writer must not touch. The check compares against `HEAD` of `<root>` and writes nothing there.
2. `mergeable: true` and a PASS in the writer's verifier output: run the printed merge command on the work branch, then rerun that part's focused verifier on the new head.
3. `mergeable: false`: merge nothing, leave the worktree as it is, and keep the other parts running. Send the same writer back for `worktree_dirty`, `out_of_scope`, `denied_path`, `whitespace_error` or a failed verifier. `integration_checkout_dirty` and `untracked_collision` are the parent's own checkout: commit the tracked change, and ask the owner before moving or deleting an untracked or ignored file. `merge_conflict` means two scopes met in one file. The parent resolves it on the work branch when both sides only add, such as two new tests in one file; otherwise that writer redoes the part on the new head after the other parts have merged.
4. A verifier that fails after the merge is repaired forward on the work branch by the same writer. Never reset the branch.

This merge puts the part on the work branch. It is not a review PASS and not a landing on a protected branch.

## After The Last Merge

Continue the [Direct Route](../SKILL.md#direct-route) on the unified head: one focused check sequence, one independent reviewer carrying every lens the diff needs, one consolidated repair, one targeted re-check. A fan-out adds no review per part.

Worktrees and branches stay until the owner authorizes their removal.
