# Growth Source Catalog

Use the smallest set of sources that can answer the question. A source name or an available UI does not prove access to the intended property, listing, package or account. Record the exact non-secret scope, date range, retrieval time, route and relevant limitations for every source used.

A source is verified evidence only when `docs/DEPLOYMENT.md` Measurement Sources marks the matching `MS-*` row `verified` for the same release target and identity. Roles stay separate; do not let one property, listing or account imply the others.

Resolve the provider behind each role from the project's own records: the `MS-*` row, then `docs/product/stack-decisions.md`, then the platform default for the surface class. Before using a provider field, report, quota, API or console path, fetch its current official documentation. Access routes, in order: an existing connector or MCP tool, the official API, the read-only console UI, or a user-provided export. Setup and configuration changes are outside this review.

## Source Roles

| Role | Answers | Does not prove |
| --- | --- | --- |
| `search_console` | How the site appeared and received clicks in Google Search | On-site engagement, revenue, or a complete list of every query |
| `ga4` | What measured visitors did after arriving and which key events occurred | Search impressions, exact query demand, or why Google ranked a page |
| `production_page` | Current HTTP, rendered content, metadata, directives, links and structured data | Search demand or business value by themselves |
| `google_trends` | Relative interest, seasonality, geography, related topics and rising queries | Absolute search volume or organic ranking difficulty |
| `keyword_planner` | Keyword ideas and advertising-oriented search estimates | Organic difficulty, content quality or guaranteed traffic |
| `public_serp` | Current result intent, formats, language, store or registry search results, competitor pages and answer-engine citations | Private competitor performance or permission to scrape at scale |
| `first_party` | The product's own events: sign-ups, activations, usage, site search, support language | Public market size unless corroborated by platform evidence |
| `app_store_connect` | iOS impressions, product-page views, downloads, conversion, retention, crashes, ratings and pre-orders | In-app behavior beyond what the product's own events record |
| `play_console` | Android store listing visitors, installs, uninstalls, ratings, crashes and ANRs, pre-registration | In-app behavior; Play statistics and in-app analytics are separate |
| `revenuecat` | Trials, conversions, renewals, churn and revenue per subscription product across stores, when the stack records RevenueCat | Store-side listing performance; the store remains the commerce owner |
| `auth_provider` | Sign-ups, active users and login methods from whatever identity provider the stack names | Discovery or demand; it measures the gate, not the path to it |
| `crash` | Crash-free rate and top crashes per build from the recorded crash reporter | Growth; it explains retention drops and release regressions |
| `registry` | Package or image downloads, pulls, version adoption, dependents, and marketplace or store stats for extensions, plugins and assistants | Actual usage; a download is not an activation |
| `bot_platform` | Bot active chats, commands used, delivery errors and directory listing state from the messaging platform | Why users arrived; attribution needs the destination side |
| `platform_insights` | Followers, reach, views, opens, members, clicks and demographics from the social, video, newsletter or community platform the team runs | Product outcome; pair with ga4 or first_party at the destination |
| `service_health` | Uptime, health-check results and error rates of an internal or backend service | Any discovery or growth signal |

## Search Console

Use Search Console first for a web or docs surface when the property already has meaningful data. The Performance report and Search Analytics API expose clicks, impressions, CTR and average position across query, page, country, device, date and search appearance.

Useful slices: high-impression queries or pages with weaker-than-peer CTR; relevant queries where a page appears but receives little traffic; non-brand query growth or decline; page/query pairs that show intent mismatch or several pages competing; country, language, device or appearance differences; changed pages or queries between equal periods.

Limits: anonymized queries are omitted; UI exports and the API return bounded rows; bulk export to BigQuery is optional and still excludes anonymized queries; page and property aggregation differ; the newest data may be preliminary. Record the cutoff and use complete periods.

## GA4

Use GA4 to judge post-click value for web and docs surfaces: organic sessions, engaged sessions, landing pages, key events, ecommerce outcomes, content groups, site-search events, country and device.

Do not assign Google Search queries to GA4 conversions when the data does not support that join. Search Console and GA4 use different collection, canonicalization, attribution, bot and session rules. Compare trends and use landing-page analysis where compatible; never force clicks and sessions to one number.

## App Store Connect And Play Console

Use the store consoles for app surfaces. App Store Connect reports impressions, product-page views, downloads, conversion rate, retention, crashes and ratings per territory and source type; Play Console reports store listing visitors, installs, uninstalls, ratings, crashes and ANRs, with pre-registration and testing-track breakdowns.

Read the listing's live state (metadata, screenshots, category, review state) in the same pass. Store search popularity indicators are estimates, not demand. Keep store statistics separate from in-app analytics; an install is not an activation.

## RevenueCat, Auth Provider And Crash

Use `revenuecat` only when `docs/product/stack-decisions.md` records it; it then owns trial, conversion, renewal and churn truth across stores, read-only. Use `auth_provider` for sign-ups and active users from the identity provider the stack names; never assume Firebase or any other vendor. Use `crash` from the recorded reporter to explain retention drops and release regressions, keyed to build identity.

## Registries, Marketplaces And Bot Platforms

Use `registry` for npm, PyPI, Go, Docker Hub, GHCR, the MCP registry, browser and marketplace stores and assistant stores: downloads or pulls, version adoption, dependents, listing views and ratings where the registry exposes them. Read the live entry (name, version, README, license, install command) in the same pass and run the install smoke from a clean environment when the review can.

Use `bot_platform` for the messaging platform's own stats and the app-directory entry. Public GitHub signals (stars, issues, forks) are `public_serp`-class observation, not adoption.

## Platform Insights

Use `platform_insights` for the social, video, newsletter and community accounts the team runs: followers or subscribers, reach and views, opens and clicks, members and active members, and demographics the platform exposes. Export or screenshot with the date and scope recorded. Pair every presence metric with its destination's `ga4` or `first_party` evidence; reach without a destination outcome is a hypothesis.

## Google Trends And Keyword Planner

Use Trends to test whether a change is seasonal, regional or market-wide and to compare related terms. It is sampled, normalized to 0–100 and not an absolute volume source. Use Keyword Planner to expand seed terms into ideas with historical estimates bound to language, location and network; `competition` is advertiser competition, not organic difficulty. The Google Ads API needs an Ads account, OAuth and a developer token that an external connector owns.

## Public Surfaces And Search Evidence

Inspect representative production routes, listings, registry entries and account pages: the home page and primary landing pages, important templates, conversion pages, known weak or declining URLs, the live store listing per locale, the registry page and README, the bot's directory entry, and the account profile with its links. Review response codes, redirects, canonical host, robots directives, `noindex`, canonicals, sitemap, `hreflang`, rendered metadata and main content, structured data against visible content, 404/410 behavior, mobile rendering and Core Web Vitals for web; listing completeness, media, ratings and policy flags for stores; metadata, install command and version hygiene for registries; profile completeness and link destinations for accounts.

A generic Lighthouse score is a clue, not a complete review. URL Inspection is stronger evidence for Google's indexed view of a specific URL when exact property access is available.

## First-Party Language And Third-Party Tools

Site-search logs, support conversations, sales questions, store reviews, community threads and user research reveal language and unmet needs. Use only data the user authorized, aggregate it, remove personal or sensitive terms, and distinguish it from public market demand.

Third-party SEO, ASO or social suites may add competitor estimates, keyword-difficulty models, listing trackers or crawls. Record the provider and retrieval date. Their scores are provider-specific diagnostics, not platform metrics and not success targets. Do not require a paid provider when official and first-party sources answer the question.

## Starting Authorities

- [Google Search Essentials](https://developers.google.com/search/docs/essentials)
- [SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Spam policies for Google Search](https://developers.google.com/search/docs/essentials/spam-policies)
- [Search Console Performance report](https://support.google.com/webmasters/answer/7576553)
- [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Get started with Google Trends](https://developers.google.com/search/docs/monitor-debug/trends-start)
- [Keyword ideas in the Google Ads API](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas)
- [App Store Connect analytics](https://developer.apple.com/help/app-store-connect/view-app-analytics/overview-of-reports)
- [App Store product page optimization](https://developer.apple.com/app-store/product-page-optimization/)
- [Play Console statistics](https://support.google.com/googleplay/android-developer/answer/139628)
- [Play store listing experiments](https://support.google.com/googleplay/android-developer/answer/12155571)
- [RevenueCat charts and metrics](https://www.revenuecat.com/docs/dashboard-and-metrics/charts)
- [npm registry API](https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md)
- [PyPI stats](https://pypistats.org/)
- [MCP registry](https://github.com/modelcontextprotocol/registry)
- [Chrome Web Store stats](https://developer.chrome.com/docs/webstore/analytics)
- [YouTube Analytics API](https://developers.google.com/youtube/analytics)
- [Instagram Insights](https://developers.facebook.com/docs/instagram-platform/insights)
- [PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started)
