# Activation Profile Catalog

Select `core` plus only the profiles supported by the product contract and delivered implementation. A profile supplies candidate actions; it never makes every row mandatory and never selects a provider for the owner.

Before executing a fast-moving provider setup, fetch its current official documentation. Record the provider, retrieval date, applicable account or plan constraint, and any unresolved difference from this catalog. A remembered dashboard path is not execution evidence.

## Core

Apply to every activation run:

- Release identity: exact release target IDs, full Git SHA, artifact or build identity, channel, environment, availability signal, and rollback or forward-fix owner.
- Account ownership: organization, billing owner, technical owner, privacy approver, support owner, least privilege, MFA, recovery, and break-glass path.
- Configuration: exact non-secret variable and secret names, placement surfaces, environment separation, rotation owner, and expiry where applicable.
- Privacy and data: data inventory, purpose, identity rule, consent, PII prohibition, retention, access/export/delete path, processors, and regional decision owner.
- Measurement: one canonical definition for every PRD metric and required `TEST-*` signal; environment/test-traffic policy; data-quality and duplicate-event checks.
- Reliability: logs, errors or crashes, health signals, alerts, escalation, support/status communication, backup/restore where state exists, and cost/usage alerts.
- Evidence: exact target, route, timestamp, read-back, behavior check, and remaining caveats. Never record a secret value or raw customer export.

## Web

Apply when a release target is a public website, web app, hosted API, or browser frontend.

### Public Web Baseline

- Domain and DNS: registrar and zone ownership, renewal, recovery, apex/subdomain inventory, DNS records, proxy status, DNSSEC/CAA decision, and domain verification.
- TLS and routing: origin encryption, certificate renewal, minimum TLS, canonical scheme/host, HTTP-to-HTTPS and old-URL redirects, HSTS only after every covered host passes HTTPS.
- Environment isolation: separate preview and production data, auth, secrets, analytics, and payment modes; preview/admin access; crawler-visible preview `noindex`; production must not retain it.
- Edge security: DDoS/WAF rules, rate limits on login and expensive writes, bot policy, origin protection, and Turnstile or another abuse control when public forms exist. A challenge widget requires server-side verification.
- Browser security: CSP report-only before enforcement, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, cookie flags, CORS, CSRF, upload boundaries, and `/.well-known/security.txt` when a disclosure channel exists.
- Delivery performance: cache rules, authenticated-response bypass, versioned immutable assets, purge policy, compression, image/font handling, HTTP protocol decision, and Core Web Vitals evidence on representative mobile and desktop routes.
- Discoverability: Search Console or equivalent owner, sitemap when useful, robots crawl policy, canonical URLs, structured data when eligible, per-route title/description, favicon/social previews, redirect map, real 404/410 responses, and `hreflang` for localized URLs.
- Accessibility: the product's WCAG target, keyboard/focus, labels, contrast, screen reader, zoom, reduced motion, touch targets, and human review of critical flows. Automated scores alone are not conformance.
- Operations: health/readiness endpoints, synthetic journeys, error tracking and source maps, log redaction, alerts/on-call receipt, support and abuse contacts, status/maintenance communication, restore test, and budget ownership.

Useful current authorities include [Cloudflare Full (strict)](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/), [Cloudflare HSTS](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/), [Cloudflare WAF](https://developers.cloudflare.com/waf/get-started/), [Cloudflare Turnstile validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/), [Google Search crawling and indexing](https://developers.google.com/search/docs/crawling-indexing), [Core Web Vitals](https://web.dev/articles/vitals), and [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

### Web Analytics And Acquisition

- Choose one primary tag orchestrator: direct provider tag, GTM, or Cloudflare Zaraz. Do not let several routes own the same page view or conversion.
- Create separate development and production properties, streams, containers, datasets, or pixels where the provider supports them.
- Map canonical events, parameters, identity, consent, retention, internal traffic, cross-domain/referral behavior, UTM policy, and key conversions.
- Verify accept, reject, and revoke consent paths. Google Consent Mode does not provide a consent banner by itself.
- Cloudflare Web Analytics is a privacy-first traffic/RUM source, not a replacement for the product-event and campaign contract.
- Meta Pixel may run through the selected web tag route. Conversions API tokens stay server-side; browser/server copies of one conversion need a common event name and event ID for deduplication.
- Link Search Console, ad platforms, cost imports, domain verification, or campaign sources only when the growth plan requires them.

Use current [GA4 recommended events](https://support.google.com/analytics/answer/9267735), [Google Consent Mode](https://support.google.com/analytics/answer/10000067), [Cloudflare Zaraz supported tools](https://developers.cloudflare.com/zaraz/reference/supported-tools/), and [Cloudflare Web Analytics](https://developers.cloudflare.com/web-analytics/about/) at execution time.

### Web Feature Overlays

- `web-auth`: provider tenant, exact origins/callback/logout URLs, authorization code with PKCE, scopes, sessions, MFA, verification/reset/recovery, account deletion, and abuse rate limits.
- `forms-leads`: server validation, spam controls, CRM mapping, notification route, webhook retry/idempotency, and form success/failure measurement.
- `transactional-email`: sending domain/subdomain, SPF, DKIM, DMARC, TLS/PTR where applicable, templates/locales, Reply-To/Return-Path, bounce/complaint/suppression, delivery alerts, and unsubscribe/preferences for marketing traffic.
- `payments`: test/live isolation, products/prices/currencies, checkout domain, tax, receipts/invoices, subscriptions/cancel/dunning, fraud/3DS, refunds/disputes, PCI scope, webhooks, reconciliation, and finance owner.
- `cms-content`: roles, draft/preview/publish, cache revalidation/purge, media, alt text, localization, redirects, and broken-link checks.
- `localization`: locale URLs, language fallback, currency/time zone, `hreflang`, translated legal/consent content, and RTL when applicable.
- `uploads-media`: object storage, signed access, size/type limits, malware scanning, transforms, retention/lifecycle, deletion, and independent backups.
- `pwa`: manifest, icons, installability, service-worker scope/update, offline fallback, push permission, and reinstall/upgrade behavior. Do not add a service worker to an ordinary site without a product need.
- `search`: provider/index, freshness, authorization filters, faceting/canonical policy, zero results, reindex, and cost/latency alerts.
- `background-jobs`: UTC/time-zone rule, heartbeat, last success, timeout, concurrency lock, retry/backoff, queue depth/age, dead-letter queue, replay, and idempotency.
- `feature-flags`: separate environments, safe default, staged rollout, kill switch, audit owner, expiry, and stale-flag cleanup.
- `paid-acquisition`: conversion destinations, consent, domain verification, attribution gaps, event deduplication, campaign taxonomy, and spend alerts.
- `app-extension-linking`: universal/app links, association files, OAuth redirect/allowed origin, browser-extension ID, and externally connectable boundaries.
- `regulated-or-ha`: SSO/RBAC, audit export, retention/region, incident and breach path, health checks, load balancing, and tested failover.

Use current [Gmail sender requirements](https://support.google.com/mail/answer/81126), [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/rfc9700), [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), and the selected payment provider's current go-live and webhook documentation.

## iOS

Apply when a release target is a native or cross-platform iOS app.

### Required Baseline

- Apple Developer and App Store Connect account, current agreements, roles, explicit App ID, bundle ID, SKU/app ID, signing/provisioning, build/version, archive, and dSYM ownership.
- App Store record, localized metadata, screenshots, category, age rating, content rights, privacy/support URLs, review contact and notes, demo account or mode, export-compliance decision, release method, and install/upgrade smoke.
- `PrivacyInfo.xcprivacy`, required-reason API declarations, third-party SDK privacy manifests/signatures, Xcode privacy report, App Privacy answers, retention, and in-app privacy/account-deletion access.
- ATT applicability decision. Request tracking permission only when the app performs Apple's defined cross-company tracking; never bypass refusal with another identifier.
- App Store Analytics plus the selected product-event and crash source. Preserve matching archives/dSYMs and verify symbolication.
- TestFlight/internal or external distribution, processing/review status, supported OS/device matrix, permission denial, offline/network failure, and server compatibility with older app versions.

### Conditional iOS Overlays

- APNs: capability/entitlement, environment, provider key or certificate name, topic, device-token lifecycle, opt-in/preferences, provider response, and sandbox/TestFlight production tests.
- Universal Links: Associated Domains entitlement, every hostname's `apple-app-site-association`, TLS/no redirect, path routing, and fresh-install link test.
- Sign in with Apple: App ID/Services ID grouping, domains/return URLs, server key names, relay-email and revoke behavior.
- IAP/subscriptions: paid agreement, product IDs/metadata/pricing/tax, StoreKit, sandbox/TestFlight purchase/restore/refund/grace, entitlement source, and App Store Server Notifications V2 with signed-event verification and idempotency.
- Advertising attribution: AdAttributionKit or still-required partner path, campaign taxonomy, conversion/postback rules, ATT/label consistency, and privacy-threshold caveats.
- Regional or regulated capabilities: Apple Pay, HealthKit, iCloud/CloudKit, app groups, background modes, medical declarations, trader status, regional licenses, tax, or banking only when the product and distribution require them.

Use current [App Store Connect workflow](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-workflow/), [privacy manifest files](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files), [App Privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy), [User Privacy and Data Use](https://developer.apple.com/app-store/user-privacy-and-data-use/), and [TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview) before acting.

## Browser Extension

Apply when a release target is a Chrome, Chromium, Firefox, or Safari extension. Use the target store's current rules; Chrome Manifest V3 is not a universal browser-extension contract.

### Chrome Baseline

- Chrome Web Store developer/publisher account, verified contact, two-step verification, least-privilege roles, item ID, ownership/recovery, and available item slots.
- Manifest V3 package, incremented version, service worker, locally bundled executable code, CSP, no remote hosted code, smallest required permissions/host patterns, and optional permission timing.
- One clear single purpose; store listing, icons/screenshots, support/homepage, privacy/data-use disclosure, permission justifications, test instructions and credentials, distribution visibility, regions, and paid-feature disclosure.
- Stable extension ID across local, store, allowlists, external messaging, and OAuth. Google OAuth uses a Chrome Extension client bound to the item ID; other providers use the exact `chromiumapp.org` redirect.
- Install, first run, popup/options/content script, service-worker termination/restart, stored settings, permission denial, update warning, upgrade, rollback/forward-fix, review, and actual audience availability.
- Runtime telemetry must comply with store policy and Manifest V3. Do not load remote analytics JavaScript. Use a first-party endpoint or GA4 Measurement Protocol only when collection is disclosed and necessary. Keep Chrome Web Store listing analytics separate from runtime telemetry.
- Do not send extension browsing or user data to Meta or another advertising platform for personalized or retargeted advertising. Measure paid acquisition on the public website instead.

Use current [Chrome Web Store publishing](https://developer.chrome.com/docs/webstore), [program policies](https://developer.chrome.com/docs/webstore/program-policies/policies), [Manifest V3](https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3), and [GA4 for extensions](https://developer.chrome.com/docs/extensions/how-to/integrate/google-analytics-4) before acting. Firefox or Safari targets require their own official profile review and must not inherit Chrome-specific store claims.
