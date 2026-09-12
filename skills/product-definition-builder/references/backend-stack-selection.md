# Backend Stack Selection

Use this guide for every PRD package with a backend, persistent data, or auth requirement. The wider architecture may remain technology-neutral. This guide separates the backend layers, produces coherent choices from product evidence, and requires owner acceptance before a recommendation becomes executable.

Label the decision status accurately:

- `Required`: mandated by the user, organization, or hard external constraint.
- `Selected`: already adopted by the current product or repository.
- `Approved`: accepted by the human owner for this package, directly or through an explicit recorded delegation.
- `Recommended`: the PRD's evidence-backed proposal; not yet owner-approved and not executable.
- `Provisional`: the leading choice pending named evidence or a spike.

Assign status per layer; one section may mix statuses. Every layer row also cites its authority/evidence: a dated user statement, organization policy, repository/config path, product requirement IDs, official documentation with check date, or named spike. Authority is the cited source, not a status label, and `PRD recommendation` alone is not evidence.

## First Separate the Layers

| Layer | Question | Examples |
| --- | --- | --- |
| Service topology | How many independently deployable backend services does the product need, and how is code organized across them? | Single service (monolith), workspace monorepo with named services, polyrepo |
| Backend runtime / framework | What executes business logic and serves API or backend requests? | Cloudflare Workers, Node.js (Express/Hono/Fastify), Next.js API routes or server actions, FastAPI, Django, Rails, Go |
| Database category | What shape of persistence does the data need? | Relational, document, key-value or cache only, none |
| Database engine | Which specific engine implements that category? | Postgres, MySQL, SQLite, Cloudflare D1, PlanetScale, MongoDB Atlas, DynamoDB, Cloudflare KV, Upstash Redis |
| Auth strategy | Who builds and owns identity/session verification? | Build custom, managed third-party provider, platform-native provider, no auth needed |
| Auth provider | Which specific vendor or mechanism implements that strategy? | Clerk, Auth0, WorkOS, Cloudflare Access, AWS Cognito, custom JWT/session store |
| Supporting choices | How are secondary backend concerns implemented? | API style (REST/GraphQL/RPC), background jobs/queue, file/object storage, caching, rate limiting |

Database category and auth strategy are separate from database engine and auth provider. Resolve or explicitly delegate the category/strategy first; then compare coherent engine/provider bundles inside those constraints. A recommendation remains non-executable until the Stack Decision Checkpoint accepts it.

## Service Topology Decision

Decide this before naming a specific backend runtime, since the topology choice frames it.

1. Monolith vs microservices — default to a single service (monolith) unless the product already has two or more confirmed independent deployment boundaries (separate release cadence, separate scaling profile, separate team ownership, or a hard platform constraint requiring separate deployables). Do not choose microservices for a hypothetical future need; splitting a well-organized monolith later is cheaper than un-splitting a premature microservice split, and the added operational complexity (service discovery, cross-service contracts, distributed tracing, more deployment surfaces) is real cost that KISS/YAGNI weighs against speculative scaling headroom.
2. When multiple services are justified, decide monorepo versus polyrepo from release cadence, team ownership, contract-change atomicity, access boundaries, and existing repository policy. A monorepo is often simpler for tightly coupled internal services, but do not silently select its workspace manager or runtime.
3. Choose Bun, Node.js, another JavaScript runtime, or another language/runtime only after checking the resolved deployment platform, required dependencies, team ownership, support window, and measured performance needs. Verify current compatibility from official documentation; no runtime is a standing default.

Record the decision status (`Required`/`Selected`/`Approved`/`Recommended`/`Provisional`) for topology and runtime the same way as every other layer in this guide.

## Collect Decision Evidence

Score or describe these inputs before selecting a stack:

1. Data shape and relationships: structured/relational records with joins and transactions, flexible/nested document shape, or simple key-value access.
2. Consistency and transaction needs: strict ACID/multi-row transactions versus eventual-consistency tolerance.
3. Query complexity: ad hoc reporting, joins, and aggregation versus simple lookups by key.
4. Scale and throughput: expected read/write volume, hot partitions, and growth trajectory.
5. Identity requirements: role count and complexity, SSO or enterprise mandates, social login, MFA, and compliance drivers (SOC2, HIPAA, GDPR).
6. Team and codebase: existing backend language/runtime, ORM or data-access experience, existing auth vendor relationships, migration cost.
7. Platform and runtime constraints: managed services available on the already-resolved deployment platform (for example Cloudflare D1, KV, or Durable Objects; AWS RDS or DynamoDB).
8. Integration and API consumers: internal-only versus public API, third-party integrations, webhook or event needs.
9. Delivery: migration and versioning strategy, environment isolation, observability, cost, and vendor lock-in tolerance.
10. Ownership: the Stack Decision Mode, human decision owner, build-versus-buy constraints, data-processing restrictions, support obligations, and who operates each managed service.

Do not let one factor decide by itself. A product that is mostly read-heavy content may still need a small relational store for accounts and orders.

## Product-Fit Patterns

Use these as starting hypotheses, then validate them against the decision evidence. Platform is a separate, already-resolved input (see the interview's platform `AskUserQuestion` step) — these rows recommend the database category/auth strategy layer only. Where the Why or Watch-outs column names a platform-specific implementation detail (for example Durable Objects), treat it as one example of a platform-appropriate equivalent, not a requirement to use that vendor on a different resolved platform.

| Product shape | Starting recommendation | Why | Watch-outs |
| --- | --- | --- | --- |
| Transactional SaaS or web app (accounts, billing, records with relationships) | Relational database with an ORM/query builder; managed third-party auth provider | Joins, transactions, and referential integrity matter; auth with billing/roles is rarely worth building from scratch | Confirm multi-tenancy model, migration strategy, and provider pricing at expected scale |
| Internal tool with an existing IdP | Relational database; platform-native or existing-IdP auth (SSO) | Operational data is usually structured; reusing the org's IdP avoids duplicate identity systems | Confirm SSO protocol (SAML/OIDC) support and role/claim mapping |
| Content-led site with minimal dynamic data | Key-value or document store for light dynamic data (comments, contact forms); no auth | Most content is static; a full relational database is unnecessary overhead | Confirm whether any workflow later needs relational integrity (for example paid content) |
| Automation or agent workflow | Key-value or document store for run records/state; no auth or platform-native service auth | Workloads are usually append-heavy run/step logs, not relational entities | Confirm idempotency keys and replay/dedup needs before picking a store |
| Real-time or collaborative app | Document or key-value store with a real-time layer; managed third-party auth | Flexible, fast-changing state fits document/key-value better than rigid relational schemas, backed by a real-time/pub-sub primitive appropriate to the resolved platform (e.g., Cloudflare Durable Objects, a managed WebSocket/pub-sub service on AWS, or a self-hosted equivalent) | Confirm conflict resolution and consistency guarantees under concurrent writes |
| Existing app with a healthy backend/data stack | Preserve the existing stack unless measured constraints justify migration | Reduces rewrite risk and preserves team velocity | Document the actual limitation and measurable exit criteria before migrating |

## Data and Auth Decision Rules

Verify these rules against current official documentation on the date the PRD is written.

### Any Category or Strategy

- Use isolated development and production credentials, connection strings, and data for every store and auth provider. Never let development access production customer data or live sessions.
- Isolation does not mean development stays empty: for content-shaped entities (articles, images, catalog items), seed development with representative mock/sample data as part of its setup or migration step, so development has realistic-looking data without ever reading real production records. Only source seed data from a real production copy when the user explicitly authorizes and scopes that as a separate, deliberate sync/anonymization process.
- Record migration order, rollback path, and deployed-environment verification for every schema or data change.
- Vendor and managed-service support changes quickly. Do not copy limits, pricing, or capability claims from memory; record the verification date and direct official sources in `stack-decisions.md`.

### Relational

- Default to a relational database when data has multiple related entities, needs transactions, or requires ad hoc reporting/joins.
- Name the specific engine, migration tool, and connection/pooling approach for the resolved deployment platform.

### Document

- Use a document store when the dominant shape is flexible or nested records with few cross-entity joins.
- Document how referential integrity (if any) is enforced at the application layer, since the store will not enforce it.

### Key-Value or Cache Only

- Use a key-value store or cache when access is by key, TTL-based, or purely operational (sessions, rate limits, feature flags).
- Do not use a key-value store as the system of record for data that needs relational queries or joins later.

### No Database Needed

- Confirm this in writing: no accounts, no persisted product data beyond ephemeral request state, and no compliance requirement to retain records.
- Revisit this decision the moment any workflow needs to remember something between requests.

### Auth: Build Custom

- Only choose this when a managed or platform-native provider cannot meet a hard constraint (data residency, an unusual identity model, or cost at extreme scale).
- Specify password/session storage, hashing, token rotation, and account-recovery flows explicitly; do not leave any of these as `TBD`.

### Auth: Managed Third-Party Provider

- Default to this when the product needs standard sign-up/sign-in, social login, MFA, or SSO without a hard constraint against a third party.
- Record the provider, session/token model, and how roles/claims map into the product's authorization model.

### Auth: Platform-Native

- Use this when the resolved deployment platform or the org's existing IdP already provides adequate identity (for example Cloudflare Access, an internal SSO gateway).
- Confirm the platform-native provider covers the product's external users, not only internal/employee access, before relying on it for a customer-facing product.

### Auth: No Auth Needed

- Confirm this in writing: the product is fully public with no per-user data, permissions, or restricted actions.
- Revisit this decision the moment any workflow needs to know who the user is.

## Selection Procedure

1. Classify data entities, access patterns, and identity/authorization needs.
2. Eliminate options that cannot satisfy a hard constraint or whose current support is unverified.
3. Choose service topology first, then the simplest coherent combination of runtime, database, and auth that covers the dominant access patterns and identity needs without unnecessary infrastructure.
4. Build two or three coherent backend bundles from the surviving choices. Each bundle covers topology, runtime, database category and engine, auth strategy and provider, API style, jobs/queue, storage, operational ownership, cost, and data constraints.
5. Recommend one bundle and explain where the serious alternatives fit better, why they lose here, and what would trigger reconsideration. Present them under the recorded Stack Decision Mode instead of silently choosing vendors.
6. Mark accepted new choices `Approved`; preserve adopted choices as `Selected` and hard constraints as `Required`. An unaccepted proposal remains `Recommended` and cannot enter implementation.
7. Verify current platform/vendor documentation and capture direct sources plus the check date.
8. When evidence is missing, define a time-boxed spike with pass/fail criteria. Until then, label the layer `Provisional` and keep the Stack Decision Checkpoint blocked.

## Required Architecture Record

The `Backend and Data Technology Decision` section in `stack-decisions.md` must include:

- Product evidence and hard constraints.
- The Stack Decision Mode, human owner, coherent bundles presented, accepted bundle or layer overrides, delegation source when used, and checkpoint decision.
- Selection, status, cited authority/evidence, product-fit reason, and constraint/follow-up on every layer row. `Recommended` and `Provisional` rows remain draft-only; an approved package uses `Required`, `Selected`, or `Approved` for every executable layer.
- One recorded stack separated in this order: service topology (monolith versus named services, and monorepo/polyrepo structure), backend runtime/framework, database category, database engine, auth strategy, auth provider, API style, background jobs/queue, and file/object storage.
- A data-entity-to-store mapping when more than one store is used.
- Alternatives and revisit triggers, as rows in the file's shared `Alternatives Considered` table with `[Area]` naming this decision — not a table inside this section.
- Official documentation links and verification date.
- Platform-managed-service bindings or configuration where applicable.
- For a deployable product, migration order, development/production isolation, and rollback path for schema or data changes.
- Any provisional layer, as a row in the file's shared `Unresolved Decision Protocol` table with owner, deadline, time-boxed spike, and pass/fail criteria.

## Official Sources to Recheck

Use primary documentation, not marketplace roundups. These links cover Cloudflare's managed data/auth services as the worked example; for another vendor, find and cite its own official documentation live, using the same verification-date discipline.

- [Cloudflare D1](https://developers.cloudflare.com/d1/)
- [Cloudflare KV](https://developers.cloudflare.com/kv/)
- [Cloudflare Durable Objects](https://developers.cloudflare.com/durable-objects/)
- [Cloudflare Queues](https://developers.cloudflare.com/queues/)
- [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/)

## Failure Modes

- Picking a database engine before establishing category from data-shape evidence.
- Choosing microservices without two or more confirmed independent deployment boundaries, adding distributed-systems complexity (service discovery, cross-service contracts, more deployment surfaces) for a product that does not need it yet.
- Silently defaulting to "just use Postgres" or "just use Firebase" without recording the decision or alternatives.
- Treating auth as a late bolt-on with unresolved session or authorization boundaries.
- Building custom auth when SSO or compliance effectively mandates a managed or platform-native provider.
- Conflating database category with database engine, or auth strategy with auth provider, as one decision.
- Skipping the `AskUserQuestion` step and silently assuming a database category or auth strategy.
- Treating a recommended runtime, engine, auth vendor, queue, or storage provider as executable before the owner accepts the coherent backend bundle.
- Claiming current vendor support or limits without a date and official source.
- Writing `TBD` without an owner, deadline, experiment, and decision threshold.
