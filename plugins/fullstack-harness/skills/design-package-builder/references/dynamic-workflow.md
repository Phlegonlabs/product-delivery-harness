# Claude Code Dynamic Workflow

Use this reference only after design discovery, Builder UX Direction intake, and source identification are complete. A workflow cannot obtain design approval, choose between unresolved human directions, or authorize publication.

## Graph Model

The stable org graph defines these roles:

| Role | Responsibility | Output |
| --- | --- | --- |
| visual-thesis-content | Product-specific thesis, taste statement, content realism, landing-page restraint | Visual direction and content rules |
| system-components | Tokens, typography, layout, components, states, accessibility | Design-system sections and DS IDs |
| iconography | Current source scan, semantic coverage, token and accessibility rules | Icon system decision |
| motion | Purpose, stack, tokens, choreography, performance and reduced-motion rules | Motion system and demo contract |
| page-coverage | Route, breakpoint, state, mockup, data, and evidence mapping | Page UI matrix and visual gates |
| synthesizer | Reconcile all role outputs | Four design-package artifact bodies |
| taste-verifier | Check product specificity, hierarchy, and anti-slop rules | Findings and decision |
| trace-verifier | Check upstream/DS/test trace coverage and internal consistency | Findings and decision |

The temporary work graph is one bounded workflow run. It fans out independent design analysis, joins for synthesis, then fans out independent verification. It does not replace the parent-owned staging lifecycle or the Harness PLAN/RUN graph.

## Preconditions

A package is "non-trivial" when more than one role in the Graph Model above would produce substantive, non-boilerplate content for it — for example a UI-bearing product spanning more than one screen or archetype, not a single-page trivial stub. "Multi-agent analysis is authorized" means the current session is not restricted to single-agent or sequential-only execution by explicit user instruction, host policy, or permission mode. Both conditions must hold before launching this workflow; when either is false, perform the roles sequentially instead.

Before launch, the parent must have:

- a stable run ID and product name;
- product archetype, audience, and source paths or source summary;
- Builder UX Direction and its selected/provisional/assumed status for UI-bearing products;
- explicit decisions on whether iconography and motion are in scope;
- resolved conflicts that require a human choice;
- a machine-enforced `builder_readonly` launch profile that exposes only Workflow and the required read/search/web tools, with no `Edit`, `Write`, `NotebookEdit`, `Bash`, or other mutating MCP tools.

If the host cannot enforce that read-only tool boundary, use the sequential parent fallback.

## Execution

Use `assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js` with structured arguments. The workflow is read-only:

1. Visual thesis/content, system/components, page coverage, and conditional icon/motion roles run independently.
2. Failed or skipped agents remain explicit blocked role results.
3. Synthesis waits for the complete role barrier and returns candidate artifact bodies.
4. Taste and trace verifiers independently inspect the synthesis.
5. The parent repairs findings, renders or reviews evidence when available, stages the artifacts, and applies the existing publish gate.

The workflow does not create production images or claim rendered visual verification. A returned motion showcase is candidate source text only until the parent writes and runs it.

## Failure And Resume

- A failed required role blocks finalization until rerun or completed sequentially.
- A material verifier finding must be repaired or recorded as an unresolved constraint.
- Native workflow resume works within the same Claude Code session. Across sessions, start a new run from the frozen source inputs and retained staging package.
- Record the workflow run ID and review findings in the task report when available.

## Fallback

When Dynamic Workflow is unavailable, perform the same roles sequentially. Do not claim multi-agent review, runtime parallelism, or workflow resume in the fallback path.
