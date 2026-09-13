# SEO Source Catalog

Use the smallest set of sources that can answer the question. A source name or available UI does not prove access to the intended property. Record the exact non-secret scope, date range, retrieval time, route, and relevant limitations for every source used.

Before using a provider field, report, quota, API, or console path, fetch its current official documentation. The links below are starting authorities, not remembered execution instructions.

## Source Roles

| Source | Answers | Does not prove |
| --- | --- | --- |
| Google Search Console | How the site appeared and received clicks in Google Search | On-site engagement, revenue, or a complete list of every query |
| GA4 | What measured visitors did after arriving and which key events occurred | Search impressions, exact query demand, or why Google ranked a page |
| Google Trends | Relative interest, seasonality, geography, related topics and rising queries | Absolute search volume or organic ranking difficulty |
| Keyword Planner / Google Ads API | Keyword ideas and historical advertising-oriented search estimates | Organic ranking difficulty, content quality, or guaranteed traffic |
| Production pages and crawl evidence | Current HTTP, rendered content, metadata, directives, links and structured data | Search demand or business value by themselves |
| Public SERP and competitor pages | Current result intent, formats, language and content gaps | Private competitor performance or permission to scrape at scale |
| First-party product language | How customers describe needs in site search, support, sales or research | Public market size unless corroborated by search evidence |

## Search Console

Use Search Console first when the property already has meaningful data. Its Performance report and Search Analytics API expose clicks, impressions, CTR and average position across query, page, country, device, date and search appearance dimensions.

Useful opportunity slices include:

- high-impression queries or pages with weaker-than-peer CTR;
- relevant queries where a page appears but receives little traffic;
- non-brand query growth or decline;
- page/query pairs that indicate intent mismatch or several pages competing for one topic;
- country, language, device or search-appearance differences; and
- changed pages or queries between equal comparison periods.

Limits matter:

- privacy-protected anonymized queries are omitted from query tables;
- UI exports and the Search Analytics API return bounded or top rows rather than every query;
- bulk export to BigQuery is optional for larger or long-running analysis and still excludes anonymized queries;
- page and property aggregation produce different totals and position calculations; and
- the newest data may be preliminary or incomplete. Record the cutoff and use complete periods.

Access routes: an existing connector or MCP tool, the official Search Console API, the read-only console UI, or a user-provided export. Do not add/remove a property, submit/delete a sitemap, or change associations in this review.

## GA4

Use GA4 to judge post-click value. Relevant evidence includes organic sessions, engaged sessions or engagement rate, landing pages, key events, ecommerce outcomes when applicable, content groups, site-search events, country and device.

Do not assign Google Search queries to GA4 conversions when the data does not support that join. Search Console and GA4 use different collection, canonicalization, attribution, bot and session rules. Compare their trends and use landing-page analysis where compatible; do not force clicks and sessions to reconcile to one number.

Access routes: an existing connector or MCP tool, the GA4 Data API, the read-only Analytics UI, or a user-provided export. Property or stream creation, tag installation, account linking, key-event changes, data-sharing choices, retention changes, and filter activation belong to `product-activation` or implementation work.

## Google Trends

Use Trends to test whether a change is seasonal, regional or market-wide and to compare the relative interest of closely related terms or topics. Trends is sampled, anonymized, aggregated and normalized to a 0–100 scale. It is not an absolute volume source.

Use the Explore UI or a user-provided export for arbitrary terms. The public BigQuery dataset can support top and rising-query research in its covered regions, but it is not a replacement for arbitrary Explore queries. Do not automate unsupported scraping of Google results or Trends pages.

## Keyword Planner And Google Ads API

Use Keyword Planner to expand relevant seed terms, page URLs or a site into keyword ideas and to retrieve historical estimates such as average monthly searches. Always bind requests to the intended language, location and network.

Treat `competition` as advertiser competition, not organic SEO difficulty. Search-volume and bid data are estimates and must not outrank product fit, first-party demand, user value or the site's ability to add original value.

The Google Ads API requires an appropriate Ads account, OAuth and developer-token setup. That authentication and provider client belong in an external connector or MCP server, not this skill. Browser or exported-data review remains valid when no API route exists.

## Public Site And Search Evidence

Inspect representative production routes, including the home page, primary public landing pages, important content templates, conversion pages and known weak or declining URLs. Review:

- response codes, redirect chains and canonical host;
- `robots.txt`, robots directives and accidental production `noindex`;
- canonical links, sitemap reachability and localized `hreflang` when applicable;
- rendered title, description, headings, main content, alt text and crawlable internal links;
- structured data against current eligibility and visible-page content;
- real 404/410 behavior and redirect quality;
- mobile rendering and material Core Web Vitals or page-experience evidence; and
- originality, authorship, evidence, update history and other trust signals appropriate to the topic.

A generic Lighthouse SEO score is a clue, not a complete technical review. URL Inspection is stronger evidence for Google's indexed view of a specific URL when exact property access is available.

## First-Party Language And Third-Party Tools

Site-search logs, support conversations, sales questions and user research can reveal valuable language and unmet needs. Use only data the user authorized, aggregate it, remove personal or sensitive terms, and distinguish it from public market demand.

Third-party SEO suites may add competitor estimates, backlink indexes, keyword-difficulty models or site crawls. Record the provider and retrieval date. Their authority and difficulty scores are provider-specific diagnostics, not Google metrics and not success targets. Do not require a paid provider when official and first-party sources answer the question.

## Connector And MCP Boundary

The skill defines source preference, query intent, reconciliation and output. A connector or MCP server owns API authentication, authorization, pagination, quotas, retries, provider clients, structured tool schemas and service observability.

An eventual read-only SEO data MCP may expose tools such as:

- `search_console.query_performance`;
- `search_console.inspect_url`;
- `search_console.list_sitemaps`;
- `ga4.run_report`;
- `ga4.run_realtime_report`;
- `keyword_planner.generate_ideas`; and
- `keyword_planner.get_historical_metrics`.

This list is an interface direction, not evidence that the tools exist. When unavailable, record `connector_gap` and continue with public evidence, Browser read-only access, or user-provided exports as the selected mode permits.

## Starting Authorities

- [Google Search Essentials](https://developers.google.com/search/docs/essentials)
- [SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Spam policies for Google Search](https://developers.google.com/search/docs/essentials/spam-policies)
- [Search Console Performance report](https://support.google.com/webmasters/answer/7576553)
- [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Search Console API reference](https://developers.google.com/webmaster-tools/v1/api_reference_index)
- [Search Console bulk data export](https://support.google.com/webmasters/answer/12918484)
- [Get started with Google Trends](https://developers.google.com/search/docs/monitor-debug/trends-start)
- [Google Trends data FAQ](https://support.google.com/trends/answer/4365533)
- [Keyword ideas in the Google Ads API](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas)
- [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Connect Search Console to Google Analytics](https://support.google.com/analytics/answer/10737381)
- [Use Search Console and Google Analytics for SEO](https://developers.google.com/search/docs/monitor-debug/google-analytics-search-console)
- [PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started)
