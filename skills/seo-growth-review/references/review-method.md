# SEO Review Method

Use this method after reading `source-catalog.md`. Keep the review useful without turning it into a standing project board or a list of generic SEO checks.

## Establish The Review

Record:

- mode: `baseline`, `growth_review`, or `traffic_drop`;
- production domain and included route or content scope;
- target country or region, language and audience;
- business outcome and relevant PRD metric or key event when available;
- current and comparison periods, complete-data cutoff and timezone;
- target market, language, business outcome, and (for `growth_review` or
  `traffic_drop`) equal comparison windows;
- each source's `verified at` time separately from its coverage-through cutoff;
- release target, deployed SHA or artifact identity when verifiable; and
- source inventory with exact property/account scope, freshness, route and limitation.

If Search Console, GA4, the production host and the recorded release describe different scopes, report the mismatch before interpreting performance.

## Measurement Integrity

Check only what current evidence supports:

1. Production and preview traffic are distinguishable and the canonical production host is stable.
2. The Search Console property covers the intended protocol, host, subdomains and path scope.
3. The GA4 property and web stream cover the intended production site without obvious duplicate page views or a mixed preview stream.
4. The selected organic channel, landing-page, key-event and date definitions match the stated business question.
5. Consent and filters do not silently remove or mix the population under review.
6. Search Console and GA4 dates use complete data and comparable time zones or disclose the mismatch.
7. Any `MS-*` source used from `docs/ACTIVATION.md` is verified and matches the release target and identity under review.

Never treat installation alone as measurement verification. If a read-only check cannot prove the exact configuration, record an activation gap instead of guessing.

## Technical Review

Inspect representative live routes and classify findings:

- `blocker`: the intended public content is materially undiscoverable or measurement scope is wrong, such as an accidental production `noindex`, a blocking robots rule, an incorrect canonical to another page or host, persistent error responses, or a mismatched analytics property used for the conclusion;
- `high`: a widespread template or architecture issue is likely to waste crawl or prevent important pages from being understood, reached or measured;
- `medium`: a bounded page or content issue has clear evidence and a measurable improvement path; or
- `low`: a limited cleanup or experiment whose expected effect is small or uncertain.

Review these groups:

1. Crawl and index: status codes, redirects, robots controls, canonicals, sitemap when useful, URL Inspection when available, duplicate URL families, JavaScript rendering and localized alternatives.
2. Search appearance: unique titles and descriptions, heading clarity, structured data eligibility and validity, image/video handling, snippets and social metadata where the product contract requires them.
3. Information architecture: crawlable navigation, internal-link depth, descriptive anchors, orphan risk, pagination/facets and topic relationships.
4. Content and trust: intent match, completeness, originality, first-hand evidence, authorship, sourcing, update need, product expertise and topic fit.
5. Experience: mobile usability, material Core Web Vitals, intrusive interstitials, accessibility blockers and conversion friction that reduces the value of organic visits.

An observed defect names the URL, expected state, observed state, retrieval time and evidence. A best-practice idea without a defect is a recommendation, not a blocker.

## Opportunity Types

Classify each keyword or page opportunity as one primary type:

- `existing_page`: a relevant page already receives visibility and can better satisfy the observed intent;
- `ctr`: impressions exist but the search presentation appears weaker than comparable pages or periods;
- `content_gap`: relevant demand exists and no current page has a credible matching responsibility;
- `decay`: a previously useful query or page shows a material decline after controlling for period and demand changes;
- `intent_mismatch`: the visible page, snippet or conversion path does not match the query's likely task;
- `cannibalization`: several pages repeatedly appear for the same topic without a clear intentional distinction;
- `internal_link`: useful content exists but navigation and anchors do not expose its relationship or priority; or
- `trust_value`: the site can add original evidence, expertise, tools, comparisons, examples or other value that current content lacks.

Do not create one page per keyword variant. Cluster terms only when they share intent and can be answered well by one page. Split them when the user task, content responsibility or conversion path differs materially.

## Evidence And Priority

Label evidence strength:

- `observed`: direct live-site, Search Console, GA4, URL Inspection or verified measurement evidence;
- `estimated`: current provider estimate such as Keyword Planner or Trends; or
- `hypothesis`: public-result, competitor, support-language or expert inference that still needs first-party validation.

Prioritize qualitatively with:

- business and audience fit;
- observed first-party demand;
- engagement, key-event or revenue relevance;
- intent and current-page fit;
- ability to add original, helpful value;
- confidence and data quality;
- implementation and maintenance effort; and
- policy, trust, legal and reputation risk.

Rank technical blockers before growth experiments. Among non-blockers, prefer a strong existing-page opportunity over a speculative new content program. Do not use a universal position band, volume floor, keyword-difficulty score or domain-authority target as a hard gate.

## Traffic-Drop Sequence

For `traffic_drop`, test explanations in this order:

1. Confirm the decline is real in complete data and not a property, tag, filter, canonical or reporting change.
2. Localize it by search type, query, page, country, device, search appearance and date.
3. Compare Search Console clicks and impressions with GA4 organic sessions and landing-page engagement. A change isolated to one system may be measurement or attribution drift.
4. Check Trends or other market evidence for seasonality and demand change.
5. Check release history, redirects, robots, canonicals, rendering, status codes, internal links and content changes for the affected pages.
6. Check whether competitors or the result format changed, while keeping that evidence as public observation rather than private-performance fact.
7. Report the smallest supported cause set and the evidence that would falsify it. Do not name an algorithm update or penalty without direct current evidence.

## Gap Routing

Every follow-up has exactly one primary route:

| Route | Use when |
| --- | --- |
| `product_activation` | GA4, Search Console, tag, consent, account link, sitemap submission, filter, key-event or measurement-source configuration is missing or unverified |
| `product_definition` | A new or changed public route, content responsibility, SEO metadata contract, success metric, trust decision or other product obligation is needed |
| `delivery` | An approved crawl, rendering, metadata, structured-data, performance, internal-link or content implementation change is needed |
| `connector` | Authenticated data cannot be read repeatably because the required connector, MCP tool or API integration does not exist |
| `observe_later` | Indexing or the defined measurement window has not produced enough complete data |
| `owner` | Market, audience, editorial, legal, brand, access or commercial judgment is unresolved |

A finding may mention dependent routes, but one route owns the next action. The review never performs the routed mutation.

## Default Output

Return the result inline unless the user asks to save it.

```markdown
# SEO Growth Review

## Scope And Evidence
[Mode, site, market, language, business outcome, periods, cutoff, source coverage and limitations.]

## Measurement Integrity
[Verified scopes, mismatches, and activation or connector gaps.]

## Technical Findings
| Priority | Finding | Scope | Evidence | Impact | Route |
| --- | --- | --- | --- | --- | --- |

## Growth Opportunities
| Priority | Query or topic | Intent / type | Evidence | Current page | Action / route | Follow-up metric |
| --- | --- | --- | --- | --- | --- | --- |

## What To Do First
[The smallest ordered set of actions; technical blockers before growth experiments.]

## Limits And Next Window
[What is not observable yet, what data would settle it, and the next complete comparison window.]
```

Keep the executive result short. Put supporting rows below the decision, not before it. If the user asks for a saved report, use a dated path, preserve prior reports, follow repository document-governance rules, and show the exact write path before creating it.

## Saved Lifecycle Public-Release Review

An inline standalone audit is still the default and writes no file. When the owner explicitly asks for a lifecycle public-release review that survives later product changes, save it once at `docs/seo/reviews/YYYY-MM-DD-<slug>.md`; never overwrite an earlier issue.

The saved lifecycle artifact is strict evidence, not a convenience copy:

- use `assets/templates/SEO_REVIEW.template.md`;
- record the mode (`baseline`, `growth_review`, or `traffic_drop`) and `Review type: lifecycle_public_release`;
- bind one architecture production target, full source SHA, exact artifact/build identity, deployment identity and checked time, production domain, data cutoff, and human review owner;
- bind the lowercase SHA-256 of the exact current `docs/ACTIVATION.md`;
- list every verified `MS-*` source whose exact target, SHA, and artifact match, and no other source as verified evidence;
- keep Search Console, GA4, production-page, demand, and first-party evidence roles separate; and
- run `scripts/check_seo_review.py --review <path> --prd <PRD> --architecture <architecture> --stack-decisions <stack-decisions> --deployment <DEPLOYMENT> --activation <ACTIVATION> --repo-root <repository-root> --require-lifecycle`.

A URL, ranking, or analytics property alone does not identify the release. A stale Activation hash, mismatched deployment SHA/artifact, wrong domain, or non-matching source is a blocker before interpretation.

## Review Completion

A complete review:

- distinguishes observed facts, estimates and hypotheses;
- records source scope, freshness and limitations;
- does not force unlike metrics to match;
- assigns every follow-up one owner route and metric;
- avoids ranking promises and search-policy violations; and
- ends without waiting for delayed provider or indexing data.
