# Platform Archetypes

Use this reference after intake chooses the product archetype. Apply only the relevant profile sections; hybrids may combine sections, but do not add unused gates.

`App` is the umbrella term for every product surface this skill supports, including websites, content experiences, ecommerce/catalog flows, landing pages, SaaS platforms, dashboards, internal tools, and hybrids. Always resolve the concrete archetype before selecting contracts and gates.

## Intake Fields

Add these to the harness route when applicable:

```text
Product archetype:
Audience:
Traffic or workflow objective:
Primary user journey:
Content/source of truth:
Identity provider:
Tenant / organization model:
Role / permission model:
Billing / entitlement model:
Admin / operator surfaces:
External integrations:
Regulated or sensitive data:
Release target:
Development Worker and non-production resource boundary:
Production Worker and production resource boundary:
```

## Authenticated App, Dashboard, Internal Tool, SaaS

Freeze these surfaces before implementation:

```text
Identity lifecycle: signup, invite, login, logout, session expiry, password or SSO, account recovery
Tenant model: personal, team, organization, workspace, enterprise hierarchy
Tenant isolation: query scoping, storage boundaries, cross-tenant deny cases, seed data
Role / permission matrix: roles, actions, resources, allow/deny cases, admin override
Billing / entitlements: plans, limits, feature flags, subscription states, trial, payment failure, cancellation
Admin / operator surfaces: impersonation policy, moderation, support actions, destructive actions
Audit / observability: audit events, logs, metrics, alerts, data export/delete/retention
Integrations: webhooks, background jobs, email, queues, object storage, third-party APIs
Cloudflare release isolation: development uses non-production data, development auth, sandbox payments, and separate stateful bindings; production uses production data, production auth, live payments, and production bindings
```

Common missions:

```text
M1 tenant/account/auth foundation
M2 role/permission and API contract
M3 billing/entitlement or feature-flag gate
M4 app shell, dashboard, settings, admin/operator UI
M5 jobs/webhooks/integrations and audit events
M6 E2E with allowed/denied/tenant/billing/admin scenarios
```

Required E2E scenarios:

- Anonymous denied or redirected.
- Authenticated allowed path.
- Logout/session expiry behavior.
- Wrong-role denied path.
- Cross-tenant denied path.
- Admin/operator workflow, if present.
- Billing entitlement allowed and blocked states, if present.
- Audit/event/log created for sensitive actions.
- Seed/reset and migration compatibility verified.

## Public Website, Marketing Site, Landing Page

Freeze these surfaces:

```text
Page inventory: homepage, landing pages, pricing, about, contact, legal, 404, thank-you
URL model: slugs, canonical URLs, redirects, locale strategy, static/SSR behavior
Content source: repo markdown, CMS, API, spreadsheet, manual copy, media library
SEO metadata: title, description, Open Graph, Twitter cards, schema, sitemap, robots
Conversion: CTA, forms, analytics events, pixels, consent, UTM preservation, CRM/webhook target
Performance budget: LCP, CLS, INP or Lighthouse threshold, image/media policy
Release target: deployed URL, cache/CDN/revalidation, rollback notes
```

Common missions:

```text
M1 content/source and routing foundation
M2 page templates and responsive layout
M3 SEO/metadata/structured data
M4 conversion forms, analytics, consent, integrations
M5 accessibility, visual QA, performance
M6 deployed URL smoke, sitemap/robots/redirect checks
```

Required E2E scenarios:

- Primary CTA or form submission reaches the expected destination.
- Metadata/canonical/OG render for key pages.
- Sitemap, robots policy, redirects, and 404 behavior are checked when relevant.
- Analytics/conversion events fire or are stub-verified.
- Responsive and visual checks cover page templates, not just one page.
- Public deployed URL smoke test passes before final PASS when deployment is in scope.

## Docs Or Content Site

Freeze these surfaces:

```text
Content model: collections, article/doc fields, authors, tags, categories, locales
Publishing workflow: draft, preview, publish, scheduled, revalidation, rollback
Navigation/search: IA, sidebars, breadcrumbs, related content, search/facets
Media policy: images, captions, alt text, embeds, downloads
Accessibility semantics: headings, landmarks, link purpose, code blocks, tables
```

Required E2E scenarios:

- Draft/preview/publish or repo-build readback works.
- Slugs, taxonomy, navigation, and search/facet behavior match the contract.
- Article/doc templates pass semantic accessibility checks.
- Content-heavy responsive states and long text are captured.

## Ecommerce Or Catalog

Freeze these surfaces:

```text
Catalog model: product, SKU, variant, price, availability, inventory, media
Listing behavior: PLP, filters, sort, search, pagination, empty states
Detail behavior: PDP, variant selection, price/availability, media, schema markup
Commerce boundary: cart, checkout, payment, fulfillment, or explicit out-of-scope note
Tracking: product impression, view item, add to cart, checkout, purchase or lead events
```

Required E2E scenarios:

- Product listing and detail page render from the source of truth.
- Search/filter/sort/pagination pass for representative data.
- Product structured data and metadata are present when public.
- Price/availability/variant states are verified.
- Cart/checkout/payment are verified or explicitly out of scope.

## Trace ID Families

Use archetype-specific IDs as needed:

```text
AUTH-* identity/session
TENANT-* tenant and isolation
ROLE-* permission matrix
BILL-* billing and entitlements
ADMIN-* admin/operator actions
AUDIT-* logs/events/observability
CONTENT-* content model and publishing
CMS-* CMS/readback/revalidation
SEO-* metadata/crawl/indexing
ANALYTICS-* events/pixels/consent
CONV-* conversion forms/CTA/CRM
CATALOG-* product/catalog/search
CHECKOUT-* cart/payment/checkout
A11Y-* accessibility
PERF-* performance budgets
RELEASE-* deployment/smoke/rollback
```

## Profile Selection Rule

If a task spans profiles, freeze the shared contract first, then split missions by ownership. For example, a SaaS marketing site plus authenticated dashboard should keep public-site SEO/content missions separate from app-shell tenant/auth/billing missions and integrate through a final release/E2E gate.
