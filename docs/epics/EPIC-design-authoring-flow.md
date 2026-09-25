# PRD-Bound Design Authoring Flow

## Goal And Baseline

Owner requests integrating the discussed design/taste/page-profile/motion flow across the existing skills. On 2026-09-25 the owner explicitly selected glm-workers with GLM 5.3 Flash and authorized the `codex/design-flow-glm` isolated worktree plus a baseline commit of current scoped changes. The dispatcher uses `glm-5.3-flash` at max. Push and installation remain paused; no cleanup is authorized.

Base: remote-tracking main observed locally at `077cd3471d267d2c2f093c8d06f3f76a293ed1e1`. Imported only this task's skills, four README changes, matching Epics and scoped index rows from `codex/wireframe-four-widths`. The source checkout's unrelated audit changes, untracked design script and index state remain untouched. Prior working-tree test evidence is historical, not an exact baseline-commit PASS. See the wireframe and App/Web Epics for prior results and unresolved tests.

## Accepted Outcome

Approved PRD/platform scope -> page-purpose profiles and reference-backed Design Brief -> validated grayscale structure -> representative visual directions with playable motion studies where needed -> selected style -> connected all-screens HiFi -> existing technical/qualitative reviews and Visual Approval -> optional design-system compilation -> Harness implementation and native proof.

Maintain one frontend-design author. Taste supplies applicable methods and examples, not another author or product authority. Preserve approved copy, routes, states, targets, stack, reference/direction decisions, review budget and existing schemas. Scope is skill workflow and contracts, not authoring a product UI. UI impact none in this repository. No product PRD/architecture or managed PLAN/RUN applies.

## Implementation And Verification Plan

One GLM writer owns the explicitly dispatched source/doc/test files. Parent owns this Epic/index and integration evidence. Workers do not commit, push, install, delegate or alter the original checkout. Inspect the complete resulting diff and rerun focused checks before acceptance. Use existing motion and direction evidence validators where possible; never claim prose rules automatically prove aesthetics or browser behavior. No forced new schema, linter or approval gate.

Close the bounded study versus full-HiFi sequencing gap; make brief/reference/profile inputs reach direction authoring, final HiFi, compiler and implementation. Add meaningful regressions only for changed executable behavior. Run source specification, lint, documentation weight, relevant suites and the repository-required verification before claiming complete readiness. Retain failures and finite check deadlines. Logs stay outside the checkout; existing dependency/cache ignore rules suffice.

## Change Log

- 2026-09-25: first observation and authorized isolated baseline prepared. Source content copied with an external SHA-256 manifest. GLM read-only audit dispatched separately while the parent prepares this clean checkout. Implementation and new verification pending.
