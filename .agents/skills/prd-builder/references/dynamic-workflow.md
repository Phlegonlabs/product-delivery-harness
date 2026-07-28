# Claude Code Dynamic Workflow

Use this reference only after product discovery, the Builder UX Direction gate, and source identification are complete. A running workflow cannot ask the user for decisions, approve publication, or replace the parent-owned artifact lifecycle.

## Graph Model

The stable org graph defines these roles:

| Role | Responsibility | Output |
| --- | --- | --- |
| requirements | Product scope, functional requirements, measurable non-functional requirements, stable test obligations, metrics, risks | PRD sections with PRD/TEST trace coverage |
| architecture | Components, data, APIs, security, deployment, failure handling | Architecture sections and contracts |
| ux-wireframe | Journeys, UX obligations, routes, states, wireframe structure | UX/UI sections and wireframe requirements |
| frontend-platform | Browser stack and platform evidence when applicable, plus the mobile/desktop platform decision when that target is in scope | Frontend and mobile/desktop decisions with source evidence |
| backend | Service topology first, then backend runtime, database, and auth technology decisions when the product has a backend, persistent data, or auth requirement | Backend and Data Technology Decision rows with per-layer status and cited source evidence |
| synthesis | Reconcile all lanes into one package | Draft artifact bodies |
| market-research | Check the drafted package against what already exists in the market: alternatives, feature baseline, differentiation, pricing, benchmarks, market risks | `market-research.md` body, `MR-*` findings, and gap findings against the draft |
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
- the Builder UX Direction record for UI-bearing products, passed as `args.builder_ux_direction` alongside `args.ui_bearing`. UI-bearing is not the same as having a browser frontend: a native mobile or desktop app is UI-bearing with `browser_frontend: false`, and the template rejects a UI-bearing launch with no direction;
- source paths or a complete source summary;
- a decision on whether a browser frontend and optional implementation plan are in scope;
- a decision on whether the product has a backend, persistent data, or auth requirement, passed as `args.has_backend`, which gates whether the `backend` role runs. Local persistence or local auth can make this true without creating a hosted surface;
- an explicit `args.hosted_deployable` boolean that is true only when the product includes a hosted deployable web, API, or backend surface. Only then must the deployment platform decision be resolved (via the interview's platform `AskUserQuestion` step in workflow step 6, the user, or the current repository) and passed as `args.deployment_platform`; when providers differ by stage, this string records that resolved stage mapping while each target's `provider` remains authoritative. A running read-only lane cannot ask the user for this. A native local-data product may therefore run with `has_backend: true`, `hosted_deployable: false`, and no deployment platform while still receiving the backend analysis lane;
- for a deployable product, a complete `args.deployable_surfaces` inventory of stable surface IDs plus `args.release_targets`. Keep each target's `surface` separate from its `provider`, because development and production may use different providers for the same surface. Every expected surface must have at least one development target and one production target; the template rejects a missing expected surface or a target for an undeclared surface;
- release-target source policies limited to the current PLAN-v5 vocabulary: `pr_head` or `integration_head` for development and `production_head` for production. Signed tags and other source rules are not currently encodable in the engineering handoff and must remain an explicit unresolved handoff gap rather than a frozen release target;
- a decision on whether the product has any public-facing marketing, landing, or SEO-relevant page, which gates whether `seo-copy-verifier` runs;
- an explicit `args.market_research` boolean gating the `market-research` role. Default it to true for a non-trivial package; set it false only when the user declined the pass or the launch profile exposes no web search or fetch tool. The role runs after synthesis, reads the drafted package, and returns findings — it never edits a file, and like every other lane it cannot ask the user anything. Read `market-research-guide.md` before launching it;
- a machine-enforced `builder_readonly` launch profile that exposes only Workflow and the required read/search/web tools, with no `Edit`, `Write`, `NotebookEdit`, `Bash`, or other mutating MCP tools.

If the host cannot enforce that read-only tool boundary, use the sequential parent fallback. If a human decision, missing secret, publish approval, destructive action, or scope change is needed, do not launch or continue the workflow. Resolve it in the parent session first.

### Optional Platform Research Lanes

Only when the platform choice is genuinely ambiguous under the technology-neutral, time-boxed-spike escape hatch (`SKILL.md`'s Output Standards), the parent may optionally run one or two short read-only research lookups before presenting the platform `AskUserQuestion` menu, each returning 2-3 named platform options with tradeoffs so the menu is evidence-backed rather than silently decided by the agent. This is an ad hoc parent-side lookup under the existing `builder_readonly` boundary, not a new stable Graph Model role — do not add a row to the table above or change `assets/templates/CLAUDE_PRD_WORKFLOW.template.js` for it. Most PRDs skip this entirely: a single `AskUserQuestion` call offering Cloudflare, Vercel, AWS, and Self-hosted (plus Other) is sufficient absent real ambiguity.

## Execution

Use `assets/templates/CLAUDE_PRD_WORKFLOW.template.js` with structured arguments. The workflow is read-only:

1. Requirements, architecture, UX/wireframe, and conditional frontend/platform roles run independently.
2. All successful and failed lane results are retained explicitly.
3. Synthesis starts only after the analysis barrier.
4. Trace, consistency, and (when public-facing content is in scope) SEO copy verifiers review the same synthesis independently. Trace verification checks that every Must functional requirement and applicable NFR maps to a required stable `TEST-*` obligation with an observable expected signal.
5. When `args.market_research` is true, the `market-research` role runs in the same stage against the same synthesis. It is not a verifier: it returns a `market-research.md` body and gap findings rather than a pass/fail decision, so it never blocks the package on its own. A role that finds nothing sourceable returns blocked, and the package publishes without the artifact.
6. The parent receives candidate Markdown bodies, review findings, and the research result.

A workflow result does not authorize file creation, overwrite, archive, or publication. The parent applies the normal staging lifecycle, repairs unresolved findings, runs the output checklist, and presents exact mutations for approval. Research findings are applied by the parent, not the role: a finding that would widen product scope goes back to the user as a recommendation.

## Failure And Resume

- A skipped or failed agent becomes an explicit failed lane result; it is never silently omitted.
- A failed required lane blocks package finalization until the parent reruns it or completes that role sequentially.
- Native workflow resume is useful only within the same Claude Code session. Across sessions, use the retained staging package and frozen source inputs to start a new workflow run.
- Record the workflow run ID and relevant findings in the task report when the runtime exposes them.

## Fallback

When Dynamic Workflow is unavailable, the parent performs the same roles sequentially. Do not claim multi-agent verification or workflow resume when that fallback is used.
