# Frontend Stack Selection

Use this guide for every PRD package that includes a browser frontend. The wider architecture may remain technology-neutral. This guide turns product evidence into coherent stack choices and one recommendation, then records the owner's accepted stack instead of handing an unapproved tool list to implementation.

Label the decision status accurately:

- `Required`: mandated by the user, organization, or hard external constraint.
- `Selected`: already adopted by the current product or repository.
- `Approved`: accepted by the human owner for this package, either directly or through an explicit recorded delegation.
- `Recommended`: the PRD's evidence-backed proposal; not yet owner-approved and not executable.
- `Provisional`: the leading choice pending named evidence or a spike.

Assign status per layer; one section may mix statuses. Every layer row also cites its authority/evidence: a dated user statement, organization policy, repository/config path, product requirement IDs, official documentation with check date, or named spike. Authority is the cited source, not a status label, and `PRD recommendation` alone is not evidence.

## First Separate the Layers

Never compare `Cloudflare vs Astro vs Vite vs React` as though they solve the same problem.

| Layer | Question | Examples |
| --- | --- | --- |
| Deployment / runtime | Where are assets and server code deployed and executed? | Cloudflare Workers with Static Assets, Cloudflare Pages, Vercel, AWS (Amplify/ECS/Lambda), self-hosted (Docker/VM/Kubernetes) |
| Rendering model | When and where does HTML render? | Static, SSG, SSR, on-demand, SPA/CSR, islands, hybrid by route |
| Language | What language contract does application code use? | TypeScript, JavaScript, another framework-native language |
| Package manager | What owns dependency resolution, scripts, workspaces, and the lockfile? | npm, pnpm, Yarn, Bun |
| Web framework | What owns routes, rendering conventions, and app structure? | Astro, React Router, TanStack Start |
| UI library | What expresses interactive component behavior? | React, Preact, Vue, none |
| Component foundation | Where do accessible primitives and reusable controls come from? | shadcn/ui-style owned source, headless primitives (Base UI, Radix Primitives) plus custom components, packaged component suite, fully custom |
| Styling approach | How are styles authored and scoped? | Tailwind CSS utilities, CSS Modules, vanilla modern CSS (cascade layers, container queries), component-library-managed styles |
| Build tool | What provides development, transforms, and production builds? | Vite, framework-managed Vite |
| Supporting choices | How are product concerns implemented? | Routing/data loading, state, forms, styling, components, tests |

Astro is a framework and uses Vite as part of its toolchain. React is a UI library and can be used inside Astro islands, with Vite in a custom SPA, or through a React framework. Cloudflare is the hosting/runtime target for any of those valid combinations.

Record component foundation and styling as separate layer rows. React and shadcn/ui are not peers: React is a UI runtime, while shadcn/ui is an owned-source component and code-distribution approach. Tailwind utilities, CSS Modules, and vanilla modern CSS each change how the codebase scales. When the chosen component foundation constrains styling — current shadcn/ui components use Tailwind, for example — the styling row cites that verified constraint instead of pretending it remains a free choice. Verify the current official documentation and record the check date for both rows.

Base UI and Radix Primitives are unstyled React primitives. They supply WAI-ARIA roles, focus management and keyboard behavior for controls such as dialogs, popovers, menus and comboboxes; the project still owns tokens, visual styling and its own accessibility tests. Pick one primitive layer per product rather than mixing both for the same control, and record it as the component foundation (for example `Base UI primitives + custom components`). Both are React-only, so they do not fit a non-React UI library row. Radix Themes is a separate styled library and belongs in the packaged-suite option, not the headless one.

## Collect Decision Evidence

Score or describe these inputs before selecting a stack:

1. Content versus interaction: mostly readable/indexable pages, mostly application state, or a mixture.
2. Rendering by route: static at build time, on-demand/SSR, client-side SPA, or hybrid.
3. SEO and discovery: public indexable routes, social previews, localization, and content freshness.
4. Personalization and auth: whether the server must authenticate before rendering or serving protected assets.
5. Edge data and compute: Cloudflare bindings or APIs required by page requests, jobs, or real-time workflows.
6. Performance: LCP/INP/CLS targets, JavaScript budget, low-end devices, network conditions, and cache strategy.
7. Product complexity: routing, forms, optimistic updates, real-time state, offline needs, and long-lived sessions.
8. Team and codebase: existing stack, reusable components, expertise, maintenance ownership, migration cost, and test tooling.
9. Delivery: preview environments, rollback, observability, runtime parity, release frequency, and cost constraints.
10. Ownership: the interview's Stack Decision Mode, decision owner, build-versus-buy preference, license limits, acceptable vendor lock-in, and who maintains copied or customized component source.

Do not let one factor decide by itself. A marketing route inside a large authenticated product may still justify a hybrid or separate frontend boundary.

Use the proactive default for an owner with no technology preference: one coherent product-fit bundle plus one or two serious alternatives, stated in plain outcome language. The owner may approve the recommendation, change consequences or priorities, or choose another option; this is not a technical multiple-choice exam or an implicit delegation. Keep existing hard constraints as `Required`.

## Product-Fit Patterns

Use these as starting hypotheses, then validate them against the decision evidence.

Platform is a separate, already-resolved input (see the interview's platform `AskUserQuestion` step) — these rows recommend the framework/rendering layer only. The Watch-outs column names the deployment detail for each resolved platform; on Cloudflare that means Workers Static Assets or a Worker API, on Vercel its native framework adapter, on AWS a static/hosting target (e.g. S3+CloudFront, Amplify), and on self-hosted a static file server or container.

| Product shape | Starting recommendation | Why | Watch-outs |
| --- | --- | --- | --- |
| Marketing, docs, editorial, portfolio, content-led commerce | Astro with static output | Content-first routing and little client JavaScript by default | Confirm CMS previews, search, localization, and rebuild latency. Deploy target: Cloudflare Workers Static Assets, Vercel's static output, an AWS static host, or a self-hosted static file server |
| Content-led site with a few rich tools, calculators, or account widgets | Astro + React islands | Static/server-rendered pages with React only where interaction needs it | Define island boundaries; avoid turning every section into a hydrated component. Deploy target: the platform's Astro adapter (Cloudflare, Vercel, or self-hosted) |
| Authenticated dashboard, operations console, or interaction-heavy SPA | React + Vite, plus a backend API when needed | Coherent client application model | Specify routing, data fetching, code splitting, auth, error handling, and SPA fallback. Deploy target: Cloudflare Workers Static Assets plus a Worker API, Vercel static hosting plus serverless functions, or an AWS/self-hosted static host plus service |
| Full-stack React app with route data, SSR, or server actions | A currently supported React framework | Framework-owned routing/data/rendering avoids rebuilding production conventions by hand | Verify the framework's current support, maturity, runtime limits, and migration path on the resolved platform |
| Existing app with a healthy supported stack | Preserve the existing stack unless measured constraints justify migration | Reduces rewrite risk and preserves team velocity | Document the actual limitation and measurable exit criteria before migrating |

React's official guidance recommends starting new React apps with a framework and treating a from-scratch Vite setup as a deliberate choice. Therefore, do not default every production web app to bare React + Vite: use it when a SPA or custom architecture is itself the product-fit decision.

For an unresolved React framework or routing/data choice, compare TanStack Start, React Router framework mode, Next.js, or a deliberate Vite SPA using the optional [frontend catalog](../../delivery-harness/references/option-library/frontend.md). TanStack Start owns the server/build layer around Router; Query, Table, Virtual, Form and the other TanStack modules remain separate need-based choices. Start's RC label is a dated observation, not a blanket production recommendation. Recheck current official maturity, security advisories, hosting adapter and actual peer dependencies before recommending it. Use the [architecture catalog](../../delivery-harness/references/option-library/architecture.md) for complete stack compositions; keep deployment, backend/data/auth, component foundation and styling as separate approved layers.

## Browser Extension Stacks

When the product surface is a browser extension, the same layer separation and approval discipline apply to browser targets, extension bundler, UI framework, component/styling approach, and testing. Use the v1 browser set resolved in the interview; do not silently default the target.

- Browser target: the approved v1 set (for example Chrome/Chromium with Manifest V3, Chrome plus Firefox, or an explicit Safari target). Each added browser multiplies store review and API-compatibility work; record it as a product target, not a bundler flag.
- Bundler: TypeScript plus an extension-aware bundler — Vite with CRXJS or WXT — so the manifest, content scripts, service worker, and extension pages build from one tool.
- UI framework: optional, sized to the popup/options UI complexity. A small popup or options page needs none; a complex side-panel or options UI justifies React or another library, with the same product-fit reasoning as the patterns above.
- Record the extension layers in `stack-decisions.md`'s `Frontend Technology Decision` table with per-row status and cited authority, and the store distribution in `architecture.md` per `architecture-playbook.md`'s Browser Extension Pattern.
- Verify current Manifest V3 requirements, API surface, and store policy against official documentation on the PRD date and record the check date — MV3 rules and store policy move. Start with [Chrome Extensions docs](https://developer.chrome.com/docs/extensions/) and [Chrome Web Store](https://developer.chrome.com/docs/webstore/); cite the equivalent official docs for any other named browser.

## Platform Decision Rules

Verify these rules against current official documentation on the date the PRD is written.

### Any Platform

- Use one codebase and isolated non-production/production targets. [Release Targets](output-contract.md#release-targets) owns the source policy, release names and promotion. Isolate bindings, data, auth and sandbox payments.
- Record remote migration order, deployed-environment smoke checks, retained URL/version evidence, and rollback version separately for each environment. A successful upload alone is not release proof.
- Platform and framework support changes quickly. Do not copy version numbers or support claims from memory. Record the verification date and direct official sources in `stack-decisions.md`.

### Cloudflare

1. Prefer Cloudflare Workers with Static Assets for new Cloudflare-hosted static sites, SPAs, and full-stack apps. Cloudflare Pages is not a default option: it enters a stack decision only when the owner explicitly chooses it for that project, and the choice is recorded in `stack-decisions.md`.
2. Use Astro static output when every relevant route can be pre-rendered. Add the Cloudflare adapter only for on-demand rendering or server features, and verify build/runtime requirements.
3. Use React + Vite for an interaction-heavy SPA when client rendering is intentional. Define SPA asset fallback and the Worker API/auth boundary.
4. Use Astro + React islands when most pages are content-led and only named regions need hydration.
5. If SSR or full-stack React conventions are needed, select a framework that current Cloudflare docs support rather than assuming a build tool supplies routing, data loading, caching, or server behavior.
6. For Worker-backed apps, document the `compatibility_date`, flags, bindings, secrets, asset routing, local preview and build requirements. Explicitly create separate D1/KV/R2 resources and record both ID sets in Resource Isolation. Native Previews provision isolated Durable Objects and Containers; record their observed IDs. An approved named-environment fallback declares all bindings explicitly.
7. If authentication or middleware must run before protected assets, explicitly verify asset routing/order; never assume frontend route guards provide authorization.
8. Use one codebase with native Workers Previews and production, or an approved isolated alternative, following the Any Platform promotion rule above.

If the owner approves Void, record it as one coherent full-stack choice, not an automatic build-tool or auth decision. Native Void mode owns routing and rendering. Framework mode retains the selected framework's router and renderer while adding Void data, bindings, jobs and deployment. Auth remains a separate layer; official framework-mode docs currently describe Better Auth rather than Void-managed auth, so preserve an existing approved provider unless the owner accepts a new decision.

### Vercel, AWS, and Self-Hosted

Platform-specific rule sets for these targets are not yet authored in this guide. When one of these is the resolved platform, look up its current official deployment/framework documentation live and apply the same Any Platform rules above and the same verification-date discipline — do not invent platform-specific rules speculatively.

## Selection Procedure

1. Classify every route group by audience, content, interactivity, rendering, auth, freshness, and caching.
2. Eliminate options that cannot satisfy a hard constraint or whose current deployment support is unverified.
3. Choose the simplest coherent stack that covers the dominant route groups without unnecessary client JavaScript or custom infrastructure.
4. Assemble two or three coherent stack bundles from the surviving layers. Each bundle names every applicable layer, fit, tradeoffs, ownership/maintenance cost, constraints, and revisit trigger. Do not offer disconnected framework, CSS, and component menus that could produce an incoherent combination.
5. Recommend one bundle and explain why the serious alternatives lose here. Present the recommendation and alternatives to the owner under the recorded Stack Decision Mode: approve the recommendation, select or modify layers, or apply an explicit prior delegation.
6. For each bundle, state operating-cost assumptions, license/build-vs-buy and maintenance ownership, compatibility evidence or the time-boxed spike needed, and what would make the decision change. Do not treat a build tool or package manager as a production runtime; keep production language/runtime separate from build and dependency tooling.
7. Mark accepted new choices `Approved`; preserve existing choices as `Selected` and hard constraints as `Required`. Keep an unaccepted proposal `Recommended`. Do not present advice as approved or hand `Recommended` rows to implementation.
8. Verify current platform/framework/component/styling documentation and capture direct sources plus the check date.
9. When evidence is missing, define a time-boxed spike that measures the uncertainty with pass/fail criteria. Until then, label the layer `Provisional` and keep the Stack Decision Checkpoint blocked.

For an enhancement, inspect the current UI and stack baseline before proposing anything. Classify the UI impact `none`, `style`, `structure`, or `both`, preserve unaffected pages and layers, and recommend technology changes only where the delta needs them. Hand affected UI IDs and constraints to `ui-design-builder` for same-content before/after studies; do not author visual directions in Product Definition. A tiny bug fix does not justify a redesign or reopen a healthy stack.

## Required Architecture Record

The `Frontend Technology Decision` section in `stack-decisions.md` must include:

- Product evidence and hard constraints.
- The Stack Decision Mode, human decision owner, coherent bundles presented, selected bundle or layer overrides, delegation source when used, and the `approved`, `revision_requested`, or `blocked` Stack Decision Checkpoint result.
- Selection, status, cited authority/evidence, product-fit reason, and constraint/follow-up on every layer row. Sections may mix `Required`, `Selected`, and `Approved`; `Recommended` and `Provisional` remain draft-only.
- One recorded stack separated by deployment/runtime, rendering, language, package manager, framework, UI library, component foundation, styling, build tool, routing/data, and testing.
- A route-level rendering table.
- Alternatives and revisit triggers, as rows in the file's shared `Alternatives Considered` table with `[Area]` naming this decision — not a table inside this section.
- Official documentation links and verification date.
- Platform adapter/plugin, build runtime, compatibility date, asset routing, binding, auth, and local-preview constraints when applicable (Cloudflare `compatibility_date` and bindings when that is the resolved platform).
- For a deployable product, the deployment-unit names, release sources, isolation, migration order, deployed-environment verification, and rollback path required by Any Platform.
- Any provisional layer, as a row in the file's shared `Unresolved Decision Protocol` table with owner, deadline, time-boxed spike, and pass/fail criteria.

## Official Sources to Recheck

These links cover Cloudflare specifically. When the resolved platform is Vercel, AWS, or self-hosted, find and cite that platform's own official documentation live, using the same verification-date discipline — do not fabricate URLs for platforms not covered here.

Use primary documentation, not marketplace roundups:

- [Cloudflare Workers web application guides](https://developers.cloudflare.com/workers/framework-guides/web-apps/)
- [Cloudflare Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/)
- [Cloudflare Vite plugin](https://developers.cloudflare.com/workers/vite-plugin/)
- [Cloudflare React + Vite guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/react/)
- [Cloudflare Astro guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/astro/)
- [Astro: Why Astro](https://docs.astro.build/en/concepts/why-astro/)
- [Astro Cloudflare adapter](https://docs.astro.build/en/guides/integrations-guide/cloudflare/)
- [React: Creating a React App](https://react.dev/learn/creating-a-react-app)
- [Vite guide](https://vite.dev/guide/)
- [Void quickstart](https://void.cloud/guide/quickstart), [meta-framework overview](https://void.cloud/integrations/frameworks/overview), and [Cloudflare integration](https://void.cloud/integrations/cloudflare) (checked 2026-10-16)
- [shadcn/ui introduction and code-ownership model](https://ui.shadcn.com/docs)
- [shadcn/ui manual installation and current styling requirements](https://ui.shadcn.com/docs/installation/manual)
- [Base UI: about](https://base-ui.com/react/overview/about) and [accessibility](https://base-ui.com/react/overview/accessibility)
- [Radix Primitives: introduction](https://www.radix-ui.com/primitives/docs/overview/introduction)
- [Tailwind CSS documentation](https://tailwindcss.com/docs)

## Failure Modes

- A flat `Astro / Vite / React` options list with no layer model or recommendation.
- Choosing Astro solely for performance without proving the product is content-led.
- Choosing React + Vite solely because React is familiar while leaving routing, data, SEO, and SSR unresolved.
- Calling Vite a UI framework or treating it as a substitute for React.
- Adding React to Astro when native Astro or plain browser behavior is enough.
- Treating React, shadcn/ui, Tailwind, and Vite as peer alternatives instead of separate runtime, component, styling, and build layers.
- Sending a `Recommended` component or CSS choice to scaffolding without owner approval or an explicit recorded delegation.
- Assuming client-side route protection secures a Worker API or protected asset.
- Claiming current Cloudflare support without a date and official source.
- Writing `TBD` without an owner, deadline, experiment, and decision threshold.
