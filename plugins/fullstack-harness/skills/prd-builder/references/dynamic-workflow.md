# Claude Code Dynamic Workflow

Use this reference only after product discovery, the Builder UX Direction gate, and source identification are complete. A running workflow cannot ask the user for decisions, approve publication, or replace the parent-owned artifact lifecycle.

## Graph Model

The stable org graph defines these roles:

| Role | Responsibility | Output |
| --- | --- | --- |
| requirements | Product scope, requirements, trace IDs, metrics, risks | PRD sections and trace coverage |
| architecture | Components, data, APIs, security, deployment, failure handling | Architecture sections and contracts |
| ux-wireframe | Journeys, UX obligations, routes, states, wireframe structure | UX/UI sections and wireframe requirements |
| frontend-platform | Browser stack and platform evidence when applicable | Frontend decision and source evidence |
| synthesis | Reconcile all lanes into one package | Draft artifact bodies |
| trace-verifier | Check requirement and ID coverage | Findings and decision |
| consistency-verifier | Check cross-document conflicts and unsupported claims | Findings and decision |
| seo-copy-verifier | Check public/marketing screen copy for SEO effectiveness when the product has public-facing content | Findings and decision |

The temporary work graph is one bounded workflow run. It may fan out analysis lanes, join them for synthesis, and fan out verification. It does not persist as a second PLAN/RUN system.

## Preconditions

A package is "non-trivial" when more than one role in the Graph Model above would produce substantive, non-boilerplate content for it — for example a UI-bearing product spanning more than one screen or archetype, not a single-page trivial stub. "Multi-agent analysis is authorized" means the current session is not restricted to single-agent or sequential-only execution by explicit user instruction, host policy, or permission mode. Both conditions must hold before launching this workflow; when either is false, perform the roles sequentially instead.

Before launch, the parent must have:

- a stable run ID;
- the product name and archetype;
- an interview summary or explicit assumption authorization;
- the Builder UX Direction record for UI-bearing products;
- source paths or a complete source summary;
- a decision on whether a browser frontend and optional implementation plan are in scope;
- for a deployable product, the deployment platform resolved (via the interview's platform `AskUserQuestion` step, the user, or the current repository) before a lane launches — a running read-only lane cannot ask the user for this;
- a decision on whether the product has any public-facing marketing, landing, or SEO-relevant page, which gates whether `seo-copy-verifier` runs;
- a machine-enforced `builder_readonly` launch profile that exposes only Workflow and the required read/search/web tools, with no `Edit`, `Write`, `NotebookEdit`, `Bash`, or other mutating MCP tools.

If the host cannot enforce that read-only tool boundary, use the sequential parent fallback. If a human decision, missing secret, publish approval, destructive action, or scope change is needed, do not launch or continue the workflow. Resolve it in the parent session first.

### Optional Platform Research Lanes

Only when the platform choice is genuinely ambiguous under the technology-neutral, time-boxed-spike escape hatch (`SKILL.md`'s Output Standards), the parent may optionally run one or two short read-only research lookups before presenting the platform `AskUserQuestion` menu, each returning 2-3 named platform options with tradeoffs so the menu is evidence-backed rather than silently decided by the agent. This is an ad hoc parent-side lookup under the existing `builder_readonly` boundary, not a new stable Graph Model role — do not add a row to the table above or change `assets/templates/CLAUDE_PRD_WORKFLOW.template.js` for it. Most PRDs skip this entirely: a single `AskUserQuestion` call offering Cloudflare, Vercel, AWS, and Self-hosted (plus Other) is sufficient absent real ambiguity.

## Execution

Use `assets/templates/CLAUDE_PRD_WORKFLOW.template.js` with structured arguments. The workflow is read-only:

1. Requirements, architecture, UX/wireframe, and conditional frontend/platform roles run independently.
2. All successful and failed lane results are retained explicitly.
3. Synthesis starts only after the analysis barrier.
4. Trace, consistency, and (when public-facing content is in scope) SEO copy verifiers review the same synthesis independently.
5. The parent receives candidate Markdown bodies and review findings.

A workflow result does not authorize file creation, overwrite, archive, or publication. The parent applies the normal staging lifecycle, repairs unresolved findings, runs the output checklist, and presents exact mutations for approval.

## Failure And Resume

- A skipped or failed agent becomes an explicit failed lane result; it is never silently omitted.
- A failed required lane blocks package finalization until the parent reruns it or completes that role sequentially.
- Native workflow resume is useful only within the same Claude Code session. Across sessions, use the retained staging package and frozen source inputs to start a new workflow run.
- Record the workflow run ID and relevant findings in the task report when the runtime exposes them.

## Fallback

When Dynamic Workflow is unavailable, the parent performs the same roles sequentially. Do not claim multi-agent verification or workflow resume when that fallback is used.
