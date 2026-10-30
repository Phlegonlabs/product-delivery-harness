# Growth Review Stage

## Path Interpretation

Outside a real Markdown link, `references/...` and sibling skill paths such as `../delivery-harness/...` are logical installed-skill paths from `<growth-review-skill-root>`. `docs/...` remains repository-relative.

## Required Inputs

Start with the surfaces under review and, for each, its public identity: production URL or domain, store listing, package or registry name, bot or account handle. Add the target country or region, language, intended audience, the business outcome growth should support, and the owner's measurement window when one exists.

When a repository is available, read the applicable current files before drawing conclusions:

- `docs/product/PRD.md`: the Shape row, `## Growth Contract` (north star, re-engagement, discovery surfaces, launch window), public-surface obligations, metrics and `TEST-*` signals;
- `docs/product/architecture.md` Release Targets: every build surface and its class;
- `docs/product/stack-decisions.md`: the analytics, auth, subscription, crash and registry providers the product actually uses;
- `docs/DEPLOYMENT.md`: the deployed release identity per target, External Console Setup status, and the Measurement Sources table with each `MS-*` row's role and status;
- the public pages, listings, registry entries and account pages themselves, as rendered today.

An absent repository does not block a public baseline review. Missing target market, language or business outcome does: ask one short question rather than ranking generic keywords or listings.

## Modes

Choose one mode from the available evidence:

- `pre_launch`: an approved launch window exists and no production evidence yet. Plan query clusters, page responsibilities and the internal-link skeleton for web surfaces; listing keywords, metadata and screenshot responsibilities for store surfaces; registry metadata and the README quickstart for registry surfaces; the first posts and cadence for presence surfaces. Mark every claim `estimated` or `hypothesis`. Route new routes, listing contracts and metadata to `product-definition-builder`, implementation to `delivery-harness`, content to `go-to-market`.
- `baseline`: the product is new or useful first-party data is unavailable. Review each surface's discoverability, listing or page quality, trust signals and measurement readiness. Mark keyword and listing ideas as estimates or hypotheses.
- `growth_review`: enough complete data exists to compare demand, visibility, installs or visits, engagement and the business outcome across surfaces. Rank improvements to existing pages and listings before proposing new ones. Run it at the Growth Contract's Day 7 and Day 30 readbacks; return next-round PRD delta candidates with evidence.
- `traffic_drop`: the user reports a material decline on any surface. Compare equal periods and segment by query, page, listing, country, device or source before attributing a cause. Separate demand and seasonality from surface-specific changes.

## Workflow

1. Record the mode, the surfaces in scope with their classes and public identities, target market and language, business outcome, comparison windows, data cutoff, release identity per surface when verifiable, and every source's scope, freshness and access route.
2. For each surface, select its lens from [Surface Lenses](../review-method.md#surface-lenses). A surface whose class has no lens is recorded with the reason and skipped.
3. Resolve sources per surface in this order: the `MS-*` rows in `docs/DEPLOYMENT.md` Measurement Sources, then the providers in `docs/product/stack-decisions.md`, then the platform default for the class. Read the matching [Source Catalog](../source-catalog.md) sections. Fetch current official provider documentation before relying on a fast-moving API, report, field, quota or console path.
4. Validate measurement integrity first. Confirm the production surface, its property, listing, registry entry or account, the environment and the date coverage refer to the same scope. Use only `MS-*` rows marked `verified` for the exact release target and identity under review; a configured tag, SDK or dashboard alone is not verified data.
5. Inspect each surface for discovery blockers with its lens: crawl and index state for web; listing completeness, review state and policy flags for stores; package metadata, install smoke and README for registries; command list, directory entry and delivery health for bots; account ownership, cadence and link destinations for presence surfaces. Distinguish a current observed failure from a recommendation.
6. Gather demand and outcome evidence from the highest-value available sources per lens: first-party platform data (Search Console, App Store Connect, Play Console, registry downloads, platform insights), then the product's own events (`first_party`, GA4, RevenueCat when recorded), then estimates (Trends, Keyword Planner), then public observation (SERP, store search, registry search, competitor listings).
7. Reconcile rather than merge unlike metrics. Impressions, clicks, listing views, installs, downloads, follows and sessions come from different systems with different rules; compare trends and conversion steps without forcing them to equal one another.
8. Build the opportunity map per surface, typed with [Opportunity Types](../review-method.md#opportunity-types). Then reconcile across surfaces: which surface the north star depends on, where the launch window's channel classes actually delivered, and which re-engagement mechanism shows retention.
9. Prioritize with business fit, observed first-party demand, conversion or key-event evidence, surface and intent fit, confidence, effort and policy risk. No third-party authority score, volume floor or install threshold is a hard gate.
10. Return the review in the [Default Output](../review-method.md#default-output) shape. Each proposed change names one owner route and one measurable follow-up. A finding never authorizes a change.
11. If the user asks to save the review, show the exact path first, use a dated file under `docs/growth/reviews/`, and preserve earlier reports. Default to inline; create no kanban board, standing dashboard or canonical repository artifact without an explicit request.

## Reference Routing

- `references/review-method.md` owns surface lenses, technical checks, opportunity types, prioritization, growth cadence, decline analysis, output and gap routing.
- `references/source-catalog.md` owns source roles, provider access routes and limitations per role.
- `../delivery-harness/references/surface-catalog.md` owns which surface classes and kinds exist and their default source roles.
- `../delivery-harness/references/external-setup.md` owns the setup rows a finding may route to; this skill never performs them.

## Output

Report:

- scope, mode, the surfaces reviewed with class and lens, target market and language, data windows, cutoff and source freshness;
- measurement integrity per surface and any property, listing, registry or release mismatch;
- observed blockers and non-blocking findings per surface;
- prioritized opportunities per surface with evidence strength, then the cross-surface reconciliation against the north star;
- which opportunities improve an existing page, listing or account and which need a new or changed product contract;
- the owner route for every follow-up, from Gap Routing in `references/review-method.md`; and
- the metric and next complete comparison window that can show whether an approved change worked.
