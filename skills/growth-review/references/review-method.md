# Growth Review Method

Read the Surface Lenses rows for the surfaces under review and the sections for the chosen mode. Keep the review useful without turning it into a standing project board or a list of generic checks.

## Surface Lenses

One lens per surface class or presence kind. The Surface Catalog in delivery-harness owns the classes; this table owns what the review reads for each.

| Surface | Lens | Discovery checks | Demand and outcome evidence | Typical blockers |
| --- | --- | --- | --- | --- |
| hosted_web (public) | seo, geo | Status codes, redirects, robots and index directives, canonicals, sitemap, rendered metadata, structured data validity, internal-link crawlability, mobile rendering, Core Web Vitals; `llms.txt` and citeable page structure for answer engines | search_console queries and pages, ga4 landing-page outcomes, google_trends and keyword_planner estimates, public_serp observation, answer-engine citation checks | Production `noindex`, blocking robots rule, canonical to another host, persistent errors, mismatched analytics property |
| ios, android | aso | Listing completeness per locale, keyword and title fit, screenshot set per device class, rating and review state, category, pre-registration state, review-reply ownership, policy flags, deep-link and app-link verification | app_store_connect and play_console impressions, product-page views, installs and conversion, crash rate, revenuecat trials and conversions when recorded, first_party onboarding events | Rejected or stuck review, missing privacy answers, broken deep links, listing in the wrong category, crash spike after release |
| browser_extension, marketplace_app, assistant_listing | store-listing | Store or marketplace listing completeness, permissions justification, single-purpose clarity, review state, ratings, pricing clarity, install and uninstall smoke | Store or marketplace stats (registry role), first_party activation events | Policy rejection, excessive permissions, missing test instructions, listing hidden from search |
| mcp_server, library_or_sdk, skill_or_plugin, container_or_self_hosted, cli | directory | Registry entry completeness, README quickstart that runs, version and changelog, license, install smoke from a clean machine, directory or registry listing state | registry downloads or pulls and version adoption, first_party usage signal, GitHub stars and issues as public observation | Broken install, stale version on the registry, missing README, directory entry pointing at the wrong package |
| agent | directory | Directory metadata, `llms.txt` and public docs reachability, tool permission boundary stated publicly, console health when operations exist | registry listing read-back, first_party usage events | Directory entry unverified, docs page unreachable, side effects undisclosed |
| messaging_bot | directory | Platform app-directory entry, command list, onboarding message, opt-in and privacy text, delivery health | bot_platform stats (active chats, commands), first_party events | Bot offline, directory entry missing, commands undocumented, rate limits hit |
| social, video_channel, newsletter, community (presence) | presence | Account ownership and recovery, profile completeness, link destinations with UTM policy, cadence kept against the planned one, reply and moderation workload | platform_insights (followers, views, opens, members, clicks), ga4 or first_party for the destination side | Account not owned by the team, cadence abandoned, links to a stale destination, destination without measurement |
| docs_site | seo | Same checks as hosted_web plus task-page coverage of the product's first-run and integration questions | search_console, production_page | Docs unreachable from the listing or README, duplicate docs hosts |
| hosted_api, worker, job, webhook, realtime, internal_service, other_nonpublic | none | No public discovery path; record the reason | first_party or service_health only when a metric in the north star depends on it | — |

A surface earns a lens only when the PRD or architecture says it exists; the review never adds a surface. A hybrid product gets one row per surface and one cross-surface reconciliation at the end.

## Measurement Integrity

Check only what current evidence supports:

1. Production and preview traffic are distinguishable and the canonical production identity (host, listing, package, account) is stable.
2. Each source's scope covers the intended surface: the Search Console property covers the protocol, host and path scope; the GA4 property and stream cover the production site; the store or registry account owns the exact listing or package; the platform account is the one the team runs.
3. Selected channel, landing-page, key-event, install, download and date definitions match the stated business question.
4. Consent and filters do not silently remove or mix the population under review.
5. Dates use complete data and comparable time zones, or the mismatch is disclosed.
6. Any `MS-*` row used from `docs/DEPLOYMENT.md` is `verified` and matches the release target and identity under review.

If the sources describe different scopes, report the mismatch before interpreting performance. Never treat installation alone as measurement verification. If a read-only check cannot prove the exact configuration, record a setup gap instead of guessing.

## Technical Review

Inspect representative live surfaces and classify findings:

- `blocker`: the intended public content or listing is materially undiscoverable or measurement scope is wrong, such as an accidental production `noindex`, a blocking robots rule, a canonical to another page or host, persistent error responses, a rejected or hidden store listing, a broken install from the registry, or a mismatched property used for the conclusion;
- `high`: a widespread template, listing or architecture issue is likely to prevent important pages or listings from being understood, reached or measured;
- `medium`: a bounded page, listing or content issue has clear evidence and a measurable improvement path; or
- `low`: a limited cleanup or experiment whose expected effect is small or uncertain.

For web and docs surfaces review crawl and index, search appearance, information architecture, content and trust, and experience. For store surfaces review listing completeness, media, ratings and reviews, policy state and the post-install first run. For registry surfaces review metadata, install and import smoke, README and version hygiene. For presence surfaces review ownership, profile, cadence, link destinations and reply workload.

An observed defect names the URL, listing, package or account, expected state, observed state, retrieval time and evidence. A best-practice idea without a defect is a recommendation, not a blocker.

## Opportunity Types

Classify each opportunity as one primary type:

- `existing_page`: a page or listing already receives visibility and can better satisfy the observed intent;
- `ctr`: impressions or listing views exist but conversion to click or install appears weaker than comparable pages, listings or periods;
- `content_gap`: relevant demand exists and no current page, listing, registry entry or post has a credible matching responsibility;
- `decay`: a previously useful query, page or listing shows a material decline after controlling for period and demand changes;
- `intent_mismatch`: the visible page, snippet, listing or first-run path does not match the likely task;
- `cannibalization`: several pages, listings or packages repeatedly appear for the same topic without a clear intentional distinction;
- `internal_link`: useful content exists but navigation, anchors, README links or cross-surface links do not expose its relationship or priority;
- `trust_value`: the surface can add original evidence, expertise, examples, demos, reviews or other value that current content lacks; or
- `cadence`: a presence surface is under-posted, over-posted or unanswered relative to the plan and the audience's response.

Do not create one page, listing or post per keyword variant. Cluster terms only when they share intent and one surface can answer them well.

## Evidence And Priority

Label evidence strength:

- `observed`: direct live-surface, platform-console or verified measurement evidence;
- `estimated`: a current provider estimate such as Keyword Planner, Trends or a store's search-popularity index; or
- `hypothesis`: public-result, competitor, support-language or expert inference that still needs first-party validation.

Prioritize qualitatively with business and audience fit, observed first-party demand, engagement, install, key-event or revenue relevance, intent and current-surface fit, ability to add original value, confidence and data quality, implementation and maintenance effort, and policy, trust, legal and reputation risk.

Rank blockers before growth experiments. Among non-blockers, prefer a strong existing-page or existing-listing opportunity over a speculative new program. Do not use a universal position band, volume floor, difficulty score, authority target or install threshold as a hard gate.

## Pre-Launch Planning Sequence

For `pre_launch`, production data does not exist yet. Build the plan per surface in this order:

1. Cluster the questions and tasks the product answers, from audience language, support material and public demand evidence.
2. Assign each cluster one responsibility: a planned public page for web, listing text or screenshot for stores, README section or registry description for registries, a first post series for presence surfaces.
3. Draft the internal-link and cross-surface skeleton: which pages, listings, README and posts point at which destination, and what each anchor tells the reader.
4. Route new or changed routes, listing contracts and metadata to `product-definition-builder`, implementation to `delivery-harness`, and content to `go-to-market`.
5. Label every claim `estimated` or `hypothesis` until the surfaces exist and data arrives.

The plan feeds the PRD's routes, listing contract and Launch Window destinations. It creates nothing and promises no ranking, install or citation.

## Traffic-Drop Sequence

For `traffic_drop` on any surface, test explanations in this order:

1. Confirm the decline is real in complete data and not a property, tag, filter, canonical, listing or reporting change.
2. Localize it by surface, search type, query, page, listing, country, device, source and date.
3. Compare the discovery-side metric (impressions, listing views, registry page views) with the outcome-side metric (clicks, installs, downloads, sessions). A change isolated to one system may be measurement or attribution drift.
4. Check Trends or other market evidence for seasonality and demand change.
5. Check release history, redirects, robots, canonicals, rendering, status codes, listing edits, review state, version publishes and content changes for the affected surfaces.
6. Check whether competitors, the result format or the store's featuring changed, keeping that evidence as public observation.
7. Report the smallest supported cause set and the evidence that would falsify it. Do not name an algorithm update, penalty or store demotion without direct current evidence.

## Growth Review Cadence

When the PRD has a `## Growth Contract`, run `growth_review` at its Day 7 and Day 30 readbacks:

1. Compare `### North Star` results with the contract's Day 7 and Day 30 targets, per track row.
2. Read back each `### Discovery Surfaces` row with its lens: what it earned in visibility and what arrived through it.
3. Compare each `### Launch Window` row's channel class, destination and readback metric with what was observed.
4. Check each `### Re-engagement` mechanism for a retention signal through its TEST ID or `MS-*` row.
5. Return next-round PRD delta candidates, each with its evidence and one owner route.

The cadence is read-only. It reports evidence; the PRD owner accepts or rejects each candidate. A missed target is a finding, not a mandate to change the product or buy placement.

## Gap Routing

Every follow-up has exactly one primary route:

| Route | Use when |
| --- | --- |
| `external_setup` | A property, tag, consent, account link, listing, registry entry, store metadata, key event or measurement source is missing, unverified or misconfigured; owned by `delivery-harness` through the deployment record |
| `product_definition` | A new or changed public route, listing contract, content responsibility, metadata contract, success metric, trust decision or other product obligation is needed |
| `delivery` | An approved crawl, rendering, metadata, structured-data, performance, internal-link, README, install path or content implementation change is needed |
| `content` | A post, thread, video script, newsletter issue or listing copy is needed; owned by `go-to-market` |
| `connector` | Authenticated data cannot be read repeatably because the required connector, MCP tool or API integration does not exist |
| `observe_later` | Indexing, store review, registry propagation or the defined measurement window has not produced enough complete data |
| `owner` | Market, audience, editorial, legal, brand, access or commercial judgment is unresolved |

A finding may mention dependent routes, but one route owns the next action. The review never performs the routed mutation.

## Default Output

Return the result inline unless the user asks to save it.

```markdown
# Growth Review

## Scope And Evidence
[Mode, surfaces with class and lens, market, language, business outcome, periods, cutoff, source coverage and limitations.]

## Measurement Integrity
[Verified scopes per surface, mismatches, and setup or connector gaps.]

## Findings By Surface
| Surface | Priority | Finding | Evidence | Impact | Route |
| --- | --- | --- | --- | --- | --- |

## Opportunities By Surface
| Surface | Priority | Query, topic or listing | Type | Evidence | Current page or listing | Action / route | Follow-up metric |
| --- | --- | --- | --- | --- | --- | --- | --- |

## North Star Readback
[Per track row: target, observed, which surfaces carried it, which launch-window rows delivered, retention signal.]

## What To Do First
[The smallest ordered set of actions; blockers before growth experiments.]

## Limits And Next Window
[What is not observable yet, what data would settle it, and the next complete comparison window.]
```

Keep the executive result short. Put supporting rows below the decision, not before it. If the user asks for a saved report, use a dated path under `docs/growth/reviews/`, preserve prior reports, follow repository document-governance rules, and show the exact write path before creating it.

## Review Completion

A complete review distinguishes observed facts, estimates and hypotheses; records source scope, freshness and limitations per surface; does not force unlike metrics to match; assigns every follow-up one owner route and metric; and avoids ranking, install or citation promises and platform-policy violations.
