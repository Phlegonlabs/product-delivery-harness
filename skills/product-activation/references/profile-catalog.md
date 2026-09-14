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

Apply when a release target is a public website, web app, or browser frontend. A separately released backend uses `API / Backend`; do not treat a browser origin or web analytics property as API scope.

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

## API / Backend

Apply when an `api`, `worker`, `webhook`, `jobs`, or another independently released backend target exists. API targets are not web targets even when the same product also has a browser frontend.

### API Baseline

- Release identity: API release target, environment or namespace, deployment unit, API version, exact route scope, source SHA, artifact/build identity, and rollback owner.
- Access: authentication mode, tenant or service identity, audience and issuer, token lifetime, required scopes, rate and concurrency limits, and least-privilege service accounts.
- Contract: representative request and response evidence, error behavior, deprecation/version policy, OpenAPI or equivalent contract, backward-compatibility rule, and consumer ownership.
- Operations: logs with request and tenant identifiers but no secret or payload oversharing, distributed tracing, latency and error metrics, alerts, quotas, capacity, and cost ownership.
- Security: origin restriction where applicable, input validation, authorization checks, secret placement, audit events, abuse controls, and vulnerability disclosure route.

Keep API measurement separate from browser analytics. API adoption uses server logs, platform metrics, business events, or another bounded query scoped to the API target; a GA4 page-view stream cannot prove API behavior.

## CLI / Toolchain

Apply to independently released CLI targets. Record the supported operating
systems and shell boundary, package/signing or distribution identity, native
runtime/toolchain versions, upgrade and rollback path, telemetry policy, and a
human-readable command smoke test. A shell wrapper or an executable found only
through a repository-controlled `PATH` is not trusted runtime evidence.

## Agent / Automation

Apply to agent release targets in addition to `API / Backend`. Record model and
tool-provider ownership, prompt/context retention, approval gates for every side
effect, evaluation and shutoff controls, cost limits, and a bounded behavior
signal for each target. An agent profile never grants permission to execute a
tool or publish an external change.

## Other Non-Public

Apply to an independently released non-public target that has no narrower
catalog profile. Record its operator, distribution boundary, toolchain,
identity, support and recovery path, and prove why each normal surface overlay
is `n/a`.

### API Overlays

- `api-webhooks`: provider/event contract, signatures, replay windows, idempotency, retries, dead-letter handling, endpoint ownership, and consumer confirmation.
- `api-background-jobs`: trigger and schedule, heartbeat, timeout, concurrency, retry, replay, poison-message handling, and alert ownership.
- `api-data-export`: purpose, requester authorization, scope, format, retention, delivery route, rate limit, and deletion handling.
- `api-partner-access`: partner identity, scopes, quota, key or credential rotation, audit, support route, and termination path.

## Android

Apply when a release target is a native or cross-platform Android app.

### Required Baseline

- Google Play developer account, agreements, roles, explicit package/application ID, signing key or Play App Signing decision, version code, AAB/APK, mapping-file ownership, and recovery owner.
- Play store record, localized metadata, screenshots, category/content rating, data safety, target API level, device categories, review notes, demo access, release mode, and install/upgrade smoke.
- Play tracks: internal, closed, open, and production as selected; staged rollout percentage, halt path, promotion gates, and exact current track.
- Product-event and crash sources keyed to the Android app ID and version; preserve mapping files and verify symbolication. Keep Play Console install statistics separate from in-app behavioral analytics.
- Permission minimization and denial flows, foreground/background constraints, offline/network failure, deep links, app-link verification, and server compatibility with older app versions.

### Conditional Android Overlays

- FCM: project, sender ID, notification channel, token lifecycle, opt-in, priority, background behavior, and test-message read-back.
- Android App Links: `assetlinks.json` for every exact host, SHA-256 verification, intent filters, and fresh-install route test.
- Billing: Play Billing library version, product IDs and offer metadata, sandbox/license-testing purchases, entitlement source, server verification, Real-Time Developer Notifications, refunds, and upgrade/downgrade behavior.
- Attribution: Play Install Referrer or another selected limited-purpose path, consent, campaign taxonomy, and privacy-threshold caveats. Do not replace this with generic web pixel measurement.

Use current [Play Console](https://support.google.com/googleplay/android-developer), [Play App Signing](https://support.google.com/googleplay/android-developer/answer/9842756), [Android App Links](https://developer.android.com/training/app-links), and [Play Billing](https://developer.android.com/google/play/billing) documentation before acting.

## Desktop

Apply separately to `macos` and `windows` targets. Do not collapse them into one desktop profile when their artifact, signing, distribution, or update contracts differ.

### macOS

- Apple Developer team, Developer ID Application certificate, notarization ticket, hardened runtime and entitlement decisions, universal architecture, bundle ID, version, and exact DMG/PKG artifact identity.
- Distribution channel: direct download, update feed, TestFlight, or another named channel; install/upgrade/uninstall smoke, Gatekeeper proof, quarantine behavior, and recovery owner.
- Crash and product-event sources keyed to build identity; symbol retention, consent, privacy declaration, and offline behavior.
- System integration permissions, keychain access, extension boundaries, network entitlements, and cleanup behavior.

### Windows

- Code-signing certificate or trusted-signing policy, MSIX or signed-installer identity, publisher, architecture, version, and exact artifact hash.
- Microsoft Store, winget, direct download, or another exact channel; submission/review state, audience visibility, install/upgrade/uninstall smoke, SmartScreen evidence, and recovery owner.
- Crash and product-event sources keyed to build identity; symbol retention, consent, telemetry policy, and offline behavior.
- System integration permissions, service or scheduled-task boundaries, registry/file cleanup, device guard, and update behavior.

Native desktop availability is installability or downloadable artifact identity plus the release smoke check; a marketing-site URL check cannot substitute. Use current [Developer ID](https://developer.apple.com/developer-id/), [notarizing macOS software](https://developer.apple.com/help/account/reference/notary-service/), [Windows MSIX](https://learn.microsoft.com/windows/msix/), and [code signing](https://learn.microsoft.com/windows/security/threat-protection/code-signing/) documentation before acting.

## Responsibility Separation

Use these responsibilities across profiles; never merge them into one vendor label:

| Responsibility | Activation question |
| --- | --- |
| Billing / store commerce | Who owns products, prices, offers, charges, renewals, and billing support? |
| Entitlement | What source grants, restores, revokes, or expires access? |
| Paywall / checkout | Which exact surface presents the offer and completes purchase? |
| Merchant of record / tax | Who invoices, remits tax, handles fraud/chargebacks, and processes refunds? |
| Attribution | Which bounded signal connects acquisition or partner activity to a product event? |
| Commission / payout | What reversal, settlement, and payment operations exist? |
| Reseller operations | Who owns deal registration, provisioning, delegated administration, support, and termination? |
| Analytics | Which exact property, stream, log query, or event source measures behavior? |
| Security | Which identity, scope, secret, audit, abuse, and disclosure controls apply? |
| Email | Which domain, template, bounce/complaint, preference, and alert path applies? |
| Monitoring | Which logs, traces, metrics, alerts, on-call route, and status communication apply? |
| Store / distribution | Which exact channel, review/promotion path, artifact, audience, and installability check applies? |

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
