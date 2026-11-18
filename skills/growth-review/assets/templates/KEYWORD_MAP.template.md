# Keyword Map

<!-- Publish at docs/product/keyword-map.md. Written by growth-review in demand_research mode. Rows marked "example" show the format. Delete them. -->

## Scope

<!-- One line per field. Retrieval date is YYYY-MM-DD. Never invent a volume, a rank or a competitor fact. -->

- Market: <country or region>
- Language: <language>
- Lenses: <seo, geo, aso>
- Sources used: <source role: scope, retrieval date>
- Sources not available: <source role: reason, for example "keyword_planner: no recorded account access">

## Clusters

<!--
One row per cluster. IDs are stable: KW-001, KW-002, and so on. Never reuse or renumber.
Intent: learn, compare, buy or navigate. Cluster only queries that share one intent.
Queries: two to five, public-safe. Demand: label (observed, estimated or hypothesis), source, date, finding.
Ranks now: observed on the retrieval date: who ranks and with what kind of page.
Mapped page: a new route or an existing one, and what that page must answer. Priority: high, medium or low.
-->

| ID | Cluster | Intent | Queries | Demand evidence | Ranks now | Mapped page | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KW-001 (example) | invoice reminders for freelancers | compare | "invoice reminder app"; "automatic payment reminders" | estimated: google_trends, 2026-01-15, steady interest in the market | observed 2026-01-15: three comparison lists and two vendor landing pages | new route `/invoice-reminders`: must answer which reminders it sends and when | high |

## Not pursued

<!-- One row per cluster set aside, with the reason. Keep the row when the decision changes; add a new KW-* row instead. -->

| Cluster | Reason |
| --- | --- |
| (example) free invoice templates | Result pages are template downloads; the product does not offer one. |

## Content fields

<!-- One row per mapped page. Current values only. The PRD keeps the launch values. Limits are working limits unless the PRD names others. -->

| Page | Current title | Title limit | Current meta description | Description limit | Serves |
| --- | --- | --- | --- | --- | --- |
| (example) `/invoice-reminders` | Invoice reminders that send themselves | 60 | Set up payment reminders once. See when each one goes out. | 155 | KW-001 |

## Change log

<!-- Add one row for each content-field change. Never edit an old row. Readback date is when the change was checked against first-party data. -->

| Date | KW | Field | Before | After | Evidence | Readback |
| --- | --- | --- | --- | --- | --- | --- |
| (example) 2026-02-20 | KW-001 | title | Invoice reminders that send themselves | Automatic invoice reminders | observed: Search Console, 2026-02-14 to 2026-02-20, impressions without clicks | 2026-03-20 |
