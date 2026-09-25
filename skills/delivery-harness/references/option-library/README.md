# Optional Reference Library

Reference only. Source check date: 2026-09-25.

This is a maintained catalog for comparing technology and design choices. It does not select a stack, install anything, create a gate, or change approvals. Start with [reference selection](../reference-selection.md), read only the relevant domain, compare coherent options or retain the existing stack, and record any adopted choice in the existing project document.

Domain content stays in Traditional Chinese because that is the researched authoring copy. The English index below is the routing surface. Keep the layer boundaries: product and stack decisions belong to `product-definition-builder`; visual direction belongs to `ui-design-builder`; the compiler only consumes adopted choices; delivery, security, activation, and SEO act only on their own scopes.

CSS frameworks, component foundations and icon packages are technology choices owned by Product Definition when unresolved. UI intake uses their approved constraints to select visual treatments; a new dependency or stack change returns upstream. A domain row below lists typical consumers, not exclusive ownership or permission to skip an existing gate.

## Domain index

| Domain | Main comparison | Relevant skills / stages |
| --- | --- | --- |
| [AI / Agentic](ai-agentic.md) | Model call, fixed workflow, agent loop, durable execution, and multi-agent tradeoffs | `product-definition-builder`: AI/automation decisions; `delivery-harness`: testing/ops for adopted behavior |
| [API](api.md) | REST/OpenAPI, GraphQL, gRPC, tRPC, webhooks/events, SSE, WebSocket | `product-definition-builder`: API contract and integration decisions |
| [Architecture](architecture.md) | Modular monolith, BFF, web-queue-worker, event-driven, microservices, serverless topology | `product-definition-builder`: service topology; `delivery-harness`: implementation and operations |
| [Authentication](authentication-and-identity.md) | Managed, ecosystem-coupled, application-session, and self-hosted identity paths | `product-definition-builder`: auth strategy; `code-security-review`: exact-scope session/token review |
| [Backend](backend.md) | FastAPI, Django, NestJS, Hono, ASP.NET Core, and Go/runtime paths | `product-definition-builder`: backend stack; `delivery-harness`: testing/runtime constraints |
| [Cloudflare platform](cloudflare-platform.md) | Compute, data, queues/workflows, AI, abuse controls; mixed-provider alternatives | `product-definition-builder`: deployment/runtime decisions; `product-activation`: adopted provider setup |
| [Components / Icons](components-icons.md) | Native/existing controls, headless primitives, component libraries, registries | `ui-design-builder`: intake, direction, wireframes, HiFi with approved stack |
| [CSS / Styling](css-styling.md) | Native CSS through utility/atomic/typed/framework styling | `ui-design-builder`: intake and direction with approved stack; `design-system-compiler`: consumed choices only |
| [Data / Storage](data-storage.md) | Relational, embedded, document, cache, and object storage | `product-definition-builder`: data architecture; `delivery-harness`: tests and migrations |
| [Deployment](deployment.md) | Serverless platforms, managed workers, containers, and VM lifecycle candidates | `product-definition-builder`: release targets; `product-activation`: adopted deployment/operations |
| [Design](design.md) | Page/style profiles, fonts, grids, motion intent, overlap and compression checks | `ui-design-builder`: intake, direction, wireframes, HiFi |
| [Frontend](frontend.md) | React/Vue/Svelte application paths, content sites, SPA, existing/native alternatives | `product-definition-builder`: frontend stack; `ui-design-builder`: consumes approved stack |
| [Icon systems](icon-systems.md) | Existing assets, SVG packages, platform symbols, brand assets | `ui-design-builder`: direction and HiFi with approved stack |
| [Integrations](integrations.md) | Sync APIs, webhooks, polling, queues, workflow tools, provider adapters | `product-definition-builder`: integration topology; `product-activation`: adopted setup |
| [Motion](motion.md) | CSS, WAAPI, Motion, GSAP, Lottie, Rive, native animation, and video | `ui-design-builder`: existing motion routing; simple CSS/WAAPI remains possible |
| [Operations](operations.md) | Instrumentation versus backend, metrics, errors, SLOs, backup, release, and cost controls | `product-definition-builder`: reliability needs; `product-activation`: adopted operations |
| [Runtime selection](runtime-selection.md) | Product runtime, product agent runtime, and current development runtime separately | `product-definition-builder`: product/runtime decisions; `delivery-harness`: current development capability |
| [Security](security.md) | ASVS, API risk, authorization/OAuth/mobile topics, threat methods, controls | `product-definition-builder`: security requirements; `code-security-review`: exact-scope review |
| [Testing / Acceptance](testing-acceptance.md) | Unit, contract, browser, mobile, load, and agent evaluation evidence | `delivery-harness`: verification design for adopted obligations |

## Cross-domain and maintenance

- [Scenario guide](scenario-guide.md) gives conditional combinations, not starter stacks.
- [Reference maintenance](reference-maintenance.md) explains source review and replacement discipline.
- [Sources](sources.md) lists official sources, known retrieval limits, and unresolved checks.

The check date records when capabilities were reviewed, not an approval date. Prices, quotas, licenses, SDK support, and account features still need an official check before an actual recommendation or adoption. Known gaps in the source list remain gaps.
