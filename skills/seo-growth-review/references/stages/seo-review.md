# SEO Review Stage

## Path Interpretation

Outside a real Markdown link, `references/...`, `assets/...`, `scripts/...`, and sibling skill paths such as `../delivery-harness/...` are logical installed-skill paths from `<seo-growth-review-skill-root>`. `docs/...` remains repository-relative.

## Required Inputs

Start with the production URL or domain, target country or region, language, intended audience, and the business outcome organic traffic should support. Use the owner's measurement window when one exists.

When a repository is available, read the applicable current files before drawing conclusions:

- `docs/product/PRD.md` for approved public surfaces, SEO obligations, metrics, and `TEST-*` signals;
- `docs/product/architecture.md` and `docs/product/stack-decisions.md` for release targets, rendering, analytics, and provider decisions;
- `docs/DEPLOYMENT.md` for the deployed environment and exact release identity;
- `docs/ACTIVATION.md` for verified `MS-*` measurement sources and remaining setup gaps; and
- the public production pages and their rendered metadata, status, crawl controls, structured data, and internal links.

An absent repository does not block a public baseline review. Missing target market, language, or business outcome does: ask one short question rather than ranking generic keywords.

## Modes

Choose one mode from the available evidence:

- `pre_launch`: the product has an approved launch window and no production search evidence yet. Build query clusters, page responsibilities and the internal-link skeleton as hypotheses; mark every claim `estimated` or `hypothesis` until launch. Route new routes and metadata contracts to `product-definition-builder`, and implementation to `delivery-harness`. A `pre_launch` review is inline only; the saved lifecycle format binds a deployed release.
- `baseline`: the site is new or useful first-party search data is unavailable. Review production crawlability, indexability, information architecture, content coverage, trust signals, and measurement readiness. Mark keyword ideas as estimates or hypotheses.
- `growth_review`: enough complete Search Console and GA4 data exists to compare queries, landing pages, engagement, and business outcomes. Rank current-page improvements before proposing new pages. Run it as a cadence at the PRD Growth Contract's Day 7 and Day 30 readbacks; return next-round PRD delta candidates with the evidence.
- `traffic_drop`: the user reports a material decline. Compare equal periods and segment by query, page, country, device, and search appearance before attributing a cause. Check demand and seasonality separately from site-specific changes.

## Workflow

1. Record the mode, production scope, target market and language, business outcome, comparison windows, data cutoff, release identity when verifiable, and every source's scope, freshness and access route.
2. Read the `references/source-catalog.md` sections for the sources you use. Fetch current official provider documentation before relying on a fast-moving API, report, field, quota, or console path.

    Consult `../delivery-harness/references/reference-selection.md` only for a public, discoverable surface and only when its adopted stack, security, deployment, or operations context is material to an SEO finding. Relevant catalog domains stay subordinate to the existing public-surface scope; this pointer creates no SEO work, gate, or change authority.
3. Read the `references/review-method.md` sections for the chosen mode. Inventory available evidence before calling a source unavailable. Never infer authenticated access from a tool name, installed package, or signed-in page without proving the exact property or account scope.
4. Validate measurement integrity first. Confirm the production site, Search Console property, GA4 property and stream, canonical host, environment, and date coverage refer to the same scope. If `docs/ACTIVATION.md` exists, use its verified matching `MS-*` sources; a configured tag or dashboard alone is not verified data.
5. Inspect the production site for technical discovery blockers: HTTP and redirect behavior, crawl and index directives, canonicals, sitemap reachability when applicable, rendered metadata, structured data eligibility, internal-link crawlability, mobile rendering, and material performance or page-experience failures. Distinguish a current observed failure from a recommendation.
6. Gather keyword and page evidence from the highest-value available sources. Prefer actual Search Console queries and landing pages, then GA4 post-click value, then Trends and Keyword Planner estimates, then public SERP or competitor observations and first-party language supplied by the user.
7. Reconcile rather than merge unlike metrics. Search Console is the source for Google Search visibility and clicks; GA4 is the source for on-site sessions, engagement, and key events. Compare trends and landing-page outcomes without forcing clicks and sessions to equal one another.
8. Build a query-to-page opportunity map. Separate improvements to an existing page, missing content, intent mismatch, declining content, possible cannibalization, internal-link gaps, and trust or originality gaps. Mark each claim `observed`, `estimated`, or `hypothesis`.
9. Prioritize with business fit, first-party demand, conversion or key-event evidence, page and intent fit, confidence, effort, and policy risk. Do not use a third-party authority score or one fixed keyword-volume threshold as the decision rule.
10. Return the review in the shape defined by `references/review-method.md`. Give each proposed change one owner route and one measurable follow-up. A finding never authorizes the change.
11. If the user asks to save the review, show the exact path first and preserve earlier reports. Default to an inline report; do not create a kanban board, standing dashboard, or canonical repository artifact without an explicit request.
12. For a saved lifecycle public-release review, use `assets/templates/SEO_REVIEW.template.md`, save once under `docs/seo/reviews/YYYY-MM-DD-<slug>.md`, and run `scripts/check_seo_review.py --require-lifecycle` with the arguments that `references/review-method.md` lists in its Saved Lifecycle section. The checker includes the Product Definition and Deployment validation.

## Reference Routing

- `references/source-catalog.md` owns source roles, limitations and provider-access routes. `references/review-method.md` owns technical checks, opportunity classification, prioritization, output, traffic-drop analysis and gap routing.
- Use `assets/templates/SEO_REVIEW.template.md` and `scripts/check_seo_review.py` only for a saved lifecycle public-release review; an inline standalone audit does not create or validate that artifact.
- Use `product-activation` only when external configuration or verified measurement setup is requested.
- Use `product-definition-builder` and `delivery-harness` only after the review identifies work in their owned scopes and the user requests that work.

## Output

Report:

- scope, mode, target market and language, data windows, cutoff, and source freshness;
- measurement integrity and any exact property or release mismatch;
- observed technical blockers and non-blocking findings;
- prioritized keyword, page, content, and internal-link opportunities with evidence strength;
- which opportunities improve an existing page and which require a new or changed product contract;
- the owner route for every follow-up, from Gap Routing in `references/review-method.md`; and
- the metric and next complete comparison window that can show whether an approved change worked.
