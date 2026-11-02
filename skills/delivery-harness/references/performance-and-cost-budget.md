# Performance And Cost Budget

How a product states, verifies and reads back its run-time performance, scalability and cost. This covers the product, not the Harness's own agent runtime ([Runtime Performance](runtime-performance.md)).

There is no budget gate. A budget is a measurable `PRD-*` row under Non-Functional Requirements with a required `TEST-*`; existing acceptance, review and Measurement Sources rules carry it. Product Definition writes the rows; Delivery verifies them.

## Capacity Assumptions

Record these inputs first, in the architecture's Scaling and Reliability section. Every budget row names the input it derives from.

- Users: registered, monthly active, peak concurrent.
- Transactions: per day for each critical workflow, and the peak-to-average ratio.
- Data growth: rows or bytes added per month, and the largest single payload.
- Retention: how long each data class is kept before delete or archive.

Mark each input `measured` or `assumed`. An assumed input has an owner and a review date. A changed input reopens the rows derived from it.

## Budget Rows By Surface Class

Bracketed values show the form; replace them with numbers derived from the capacity inputs. The Core Web Vitals "good" thresholds are published at [web.dev](https://web.dev/articles/vitals).

| ID | Quality attribute | Scope | Measure | Target | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-010 | Performance | hosted_web: each named route, mobile and desktop | LCP, INP, CLS at p75, 28-day field window; compressed JavaScript per route | LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1; ≤ [N] KB | TEST-010 |
| PRD-011 | Performance | hosted_api, backends: each critical endpoint at [N] req/s | p95 latency; 5xx rate; cold start p95 | ≤ [N] ms; ≤ [N]%; ≤ [N] ms | TEST-011 |
| PRD-012 | Performance | ios, android, macos, windows, linux: named device and OS | Cold launch p50 and p95; dropped frames; peak memory | ≤ [N] ms; ≤ [N]%; ≤ [N] MB | TEST-012 |
| PRD-013 | Scalability | worker, job: at [N] jobs/min | Throughput; p95 queue age; dead-letter depth | ≥ [N]/min; ≤ [N] s; 0 sustained | TEST-013 |
| PRD-014 | Cost | Each paid platform | Projected monthly cost at the capacity inputs | ≤ [N] per month | TEST-014 |

## Caching Tiers

State the staleness each cached item tolerates, in seconds. Tenant and user identity belong in the cache key.

- Edge: may cache versioned immutable assets, public pages and public GET responses with a TTL. Never authenticated, per-user or cookie-setting responses. Invalidate by content-hashed URLs and purge on deploy.
- Application: may cache computed reads, third-party lookups and rate counters. Never secrets, or authorization decisions beyond a short TTL. Invalidate by TTL and delete on write.
- Database: may cache materialized views, read replicas and query results. Never a read that must see the latest write. Invalidate by refresh schedule and a replica-lag bound.

## Queue Backpressure And Retries

- Bound each queue by depth and by age. At the bound, shed or reject with an explicit error; never grow without limit.
- Cap consumer concurrency at what the slowest downstream accepts.
- Retry only transient failures: a maximum attempt count, exponential backoff with jitter, and an idempotency key on every retried write.
- Send exhausted messages to a dead-letter queue with an owner and an alert. A validation failure goes there at once, not through retries.

## Cost Model

Monthly cost = requests per month (from the capacity inputs) × cost per request + fixed platform fees. Cost per request covers compute time, egress, storage operations and every metered downstream call. Take unit prices from the platform's current pricing page and record the date.

| Platform kind | What drives cost | Alert | Action at the ceiling |
| --- | --- | --- | --- |
| Serverless functions and workers | Requests, CPU or memory time, egress, retries | At [N]% of the monthly ceiling, or when the forecast crosses it | Throttle non-critical jobs, then shed free-tier traffic |
| Managed database and storage | Provisioned size, reads and writes, growth, backups, egress | Same, or data growth above the assumed rate | Archive per the retention input, then resize with owner approval |

Add a row for any metered third-party API, driven by calls per user action. Record whether the platform enforces a hard cap or only alerts, and who approves a raise. An alert with no named action is not a budget.

## Verify Before Release

- hosted_web: Lighthouse CI against the candidate Preview, assertions at `error` level. Lab runs cover LCP, CLS and total blocking time; INP needs field data, and blocking time is its lab proxy.
- hosted_api, worker, job: a load tool such as k6 with thresholds on p95 latency and error rate, failing the run on breach. Use an isolated environment with data at the assumed scale.
- Native: the platform's own profiler and test metrics, such as XCTest launch metrics with Instruments, or Macrobenchmark, on the named device and OS. A browser or emulator result does not stand in.

Retain the tool and version, environment, data scale, run count, the deployed SHA read back from that environment, and the result with the `TEST-*` record. A result for another SHA or environment does not transfer. A miss fails the TEST: repair it, or change the NFR through the PRD with owner approval. Candidate tools: the optional [Testing / Acceptance reference](option-library/testing-acceptance.md).

## Production Read-Back

Add each budget signal to `docs/DEPLOYMENT.md` Measurement Sources: `service_health` for latency, error rate, queue age and platform usage or cost; `first_party` for field vitals, launch time and other client events. A row is `verified` only when a read-back returns data for the exact release target, SHA and artifact ([External Setup](external-setup.md)). Compare it with the NFR target at the same percentile and window. Outcome reviews read only verified rows.
