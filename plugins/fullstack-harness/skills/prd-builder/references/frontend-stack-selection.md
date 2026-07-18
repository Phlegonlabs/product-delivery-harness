# Frontend Stack Selection

Use this guide for every PRD package that includes a browser frontend. The wider architecture may remain technology-neutral. This guide ensures the frontend itself records a required/selected choice or turns product evidence into one implementation-ready recommendation, rather than producing a fashionable list of tools.

Label the decision status accurately:

- `Required`: mandated by the user, organization, or hard external constraint.
- `Selected`: already adopted by the current product or repository.
- `Recommended`: the PRD's evidence-backed advice; not yet user-approved.
- `Provisional`: the leading choice pending named evidence or a spike.

## First Separate the Layers

Never compare `Cloudflare vs Astro vs Vite vs React` as though they solve the same problem.

| Layer | Question | Examples |
| --- | --- | --- |
| Deployment / runtime | Where are assets and server code deployed and executed? | Cloudflare Workers with Static Assets, Cloudflare Pages |
| Rendering model | When and where does HTML render? | Static, SSG, SSR, on-demand, SPA/CSR, islands, hybrid by route |
| Web framework | What owns routes, rendering conventions, and app structure? | Astro, React Router, TanStack Start |
| UI library | What expresses interactive component behavior? | React, Preact, Vue, none |
| Build tool | What provides development, transforms, and production builds? | Vite, framework-managed Vite |
| Supporting choices | How are product concerns implemented? | Routing/data loading, state, forms, styling, components, tests |

Astro is a framework and uses Vite as part of its toolchain. React is a UI library and can be used inside Astro islands, with Vite in a custom SPA, or through a React framework. Cloudflare is the hosting/runtime target for any of those valid combinations.

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

Do not let one factor decide by itself. A marketing route inside a large authenticated product may still justify a hybrid or separate frontend boundary.

## Product-Fit Patterns

Use these as starting hypotheses, then validate them against the decision evidence.

| Product shape | Starting recommendation | Why | Watch-outs |
| --- | --- | --- | --- |
| Marketing, docs, editorial, portfolio, content-led commerce | Astro with static output on Cloudflare Workers Static Assets | Content-first routing and little client JavaScript by default | Confirm CMS previews, search, localization, and rebuild latency |
| Content-led site with a few rich tools, calculators, or account widgets | Astro + React islands on Cloudflare Workers | Static/server-rendered pages with React only where interaction needs it | Define island boundaries; avoid turning every section into a hydrated component |
| Authenticated dashboard, operations console, or interaction-heavy SPA | React + Vite on Cloudflare Workers Static Assets, plus a Worker API when needed | Coherent client application model and direct Cloudflare Vite integration | Specify routing, data fetching, code splitting, auth, error handling, and SPA fallback |
| Full-stack React app with route data, SSR, or server actions | A currently supported React framework on Cloudflare Workers | Framework-owned routing/data/rendering avoids rebuilding production conventions by hand | Verify the framework's current Cloudflare support, maturity, runtime limits, and migration path |
| Existing app with a healthy supported stack | Preserve the existing stack unless measured constraints justify migration | Reduces rewrite risk and preserves team velocity | Document the actual limitation and measurable exit criteria before migrating |

React's official guidance recommends starting new React apps with a framework and treating a from-scratch Vite setup as a deliberate choice. Therefore, do not default every production web app to bare React + Vite: use it when a SPA or custom architecture is itself the product-fit decision.

## Cloudflare Decision Rules

Verify these rules against current official documentation on the date the PRD is written:

1. Prefer Cloudflare Workers with Static Assets for new Cloudflare-hosted static sites, SPAs, and full-stack apps unless an existing Pages workflow or a specific Pages capability materially changes the decision.
2. Use Astro static output when every relevant route can be pre-rendered. Add the Cloudflare adapter only for on-demand rendering or server features, and verify build/runtime requirements.
3. Use React + Vite for an interaction-heavy SPA when client rendering is intentional. Define SPA asset fallback and the Worker API/auth boundary.
4. Use Astro + React islands when most pages are content-led and only named regions need hydration.
5. If SSR or full-stack React conventions are needed, select a framework that current Cloudflare docs support rather than assuming a build tool supplies routing, data loading, caching, or server behavior.
6. For Worker-backed apps, document the `compatibility_date`, runtime compatibility flags, bindings, secrets, asset routing, local preview path, and build environment requirements.
7. If authentication or middleware must run before protected assets, explicitly verify asset routing/order; never assume frontend route guards provide authorization.
8. Use one codebase with separately named development and production Workers. Development deploys the current PR head only after current-head CI and uses isolated non-production bindings, data, auth, and sandbox payment credentials. Production deploys the exact merged base-branch SHA only after development passes and uses production bindings, auth, and live payment credentials.
9. Record remote migration order, deployed-environment smoke checks, retained URL/version evidence, and rollback version separately for each Worker. A successful upload alone is not release proof.

Cloudflare and framework support changes quickly. Do not copy version numbers or support claims from memory. Record the verification date and direct official sources in `architecture.md`.

## Selection Procedure

1. Classify every route group by audience, content, interactivity, rendering, auth, freshness, and caching.
2. Eliminate options that cannot satisfy a hard constraint or whose current deployment support is unverified.
3. Choose the simplest coherent stack that covers the dominant route groups without unnecessary client JavaScript or custom infrastructure.
4. Name the required/selected stack, or one recommendation when no choice exists. Do not hand the implementer an unranked shortlist, and do not present advice as an approved requirement.
5. Explain at least two serious alternatives, where each would fit better, why it loses here, and what would trigger reconsideration.
6. Verify current platform/framework documentation and capture direct sources plus the check date.
7. When evidence is missing, define a time-boxed spike that measures the uncertainty with pass/fail criteria. Until then, label the layer `Provisional`, not `Selected`.

## Required Architecture Record

The `Frontend Technology Decision` section in `architecture.md` must include:

- Product evidence and hard constraints.
- Decision status and authority (`Required`, `Selected`, `Recommended`, or `Provisional`).
- One selected stack separated by deployment/runtime, rendering, framework, UI library, build tool, routing/data, styling/components, and testing.
- A route-level rendering table.
- Alternatives and revisit triggers.
- Official documentation links and verification date.
- Cloudflare adapter/plugin, build runtime, compatibility date, asset routing, binding, auth, and local-preview constraints when applicable.
- For deployable Cloudflare products, the distinct development and production Worker names, exact release sources, resource/auth/payment isolation, migration order, deployed-environment verification, and rollback path.
- Owners, deadlines, spikes, and pass/fail criteria for any provisional decision.

## Official Sources to Recheck

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

## Failure Modes

- A flat `Astro / Vite / React` options list with no layer model or recommendation.
- Choosing Astro solely for performance without proving the product is content-led.
- Choosing React + Vite solely because React is familiar while leaving routing, data, SEO, and SSR unresolved.
- Calling Vite a UI framework or treating it as a substitute for React.
- Adding React to Astro when native Astro or plain browser behavior is enough.
- Assuming client-side route protection secures a Worker API or protected asset.
- Claiming current Cloudflare support without a date and official source.
- Writing `TBD` without an owner, deadline, experiment, and decision threshold.
