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

## Greenfield / Empty Repository

Detect this before applying any archetype profile below: no toolchain manifest, no app source tree, or no locally runnable dev/build command exists yet. Every archetype's "Common missions" list below assumes the workspace and chosen stack already exist — on a greenfield repository, insert one workspace-foundation mission before them and shift the archetype's own list down by one (its `M1` becomes `M2`, and so on).

Detect which toolchain is (or should be) in play before scaffolding, and branch — do not assume a JS package manager. Match the frozen `architecture.md` Frontend/Platform Technology Decision (see `prd-builder`'s `references/frontend-stack-selection.md`) to one of these, checking the repository for an existing manifest of each shape first:

```text
JS/TS web:        package.json + a lockfile (Bun/npm/pnpm/Yarn)
iOS/macOS Swift:  *.xcodeproj / *.xcworkspace, or Package.swift (Swift Package Manager)
Android:          build.gradle / build.gradle.kts + settings.gradle(.kts)
Flutter:          pubspec.yaml (targets iOS + Android, and optionally web/desktop, from one codebase)
Windows .NET:     *.csproj / *.sln
```

The scaffold mission installs every layer the frozen decision names for the detected toolchain, not the framework alone. Scaffold the toolchain's own equivalent of "workspace init + framework/UI-library/build-tool install", never a Bun/npm workspace by default:

```text
JS/TS web:
  Workspace manager: init the chosen manager (Bun/npm/pnpm/Yarn) and its workspace layout, lockfile, and root script contract
  Deployment/runtime: install and configure the resolved platform adapter (e.g. Cloudflare adapter, Vercel adapter)
  Web framework: install and wire the decided framework (e.g. Astro, a React framework)
  UI library: install the decided UI library when one is named (e.g. React, Preact, Vue), including the framework's integration for it
  Build tool: install/configure the build tool the framework doesn't already own
  Styling/components: install the decided styling and component approach (e.g. Tailwind, a component library) and wire its build-time configuration
  Routing/data, testing: scaffold the minimal contract needed for later missions to extend, per the decision record

iOS/macOS Swift:
  Project: create the Xcode project/workspace (*.xcodeproj / *.xcworkspace) or a Package.swift target, with app, unit-test, and UI-test targets
  Dependencies: wire Swift Package Manager (or the decided manager) for the named libraries
  App shell: minimal navigation/entry point the later feature missions extend
  Signing/config: record the bundle identifier and target OS version from the decision record (leave signing certificates to the release lifecycle, not the scaffold)

Android:
  Project: create the Gradle project (build.gradle(.kts) + settings.gradle(.kts)) with app module, unit-test, and instrumented-test source sets
  Dependencies: declare the named libraries and the Kotlin/AGP versions from the decision record
  App shell: minimal activity/navigation the later feature missions extend
  Config: record applicationId, minSdk/targetSdk from the decision record

Flutter:
  Project: run the Flutter create equivalent to produce pubspec.yaml plus the iOS and Android runner sub-projects
  Dependencies: add the decided packages to pubspec.yaml
  App shell: minimal widget tree/navigation the later feature missions extend
  Config: confirm both native distribution targets (iOS + Android, plus any others named) build from this one codebase

Windows .NET:
  Project: create the .NET solution/project (*.sln / *.csproj) for the decided UI toolkit (WPF/WinUI/MAUI or a cross-platform toolkit)
  Dependencies: restore the named NuGet packages from the decision record
  App shell: minimal window/navigation the later feature missions extend
  Config: record the target framework and packaging shape (MSIX vs installer) for the release lifecycle
```

Exit criterion: a locally runnable dev/build for the detected toolchain and its passing build/compile plus test discovery — a running dev server and passing build/typecheck for JS/TS web, a successful `xcodebuild build`/`swift build` for Swift, a successful `./gradlew assembleDebug` for Android, `flutter build` (or `flutter run` device check) for Flutter, `dotnet build` for .NET — proving every installed layer actually works together rather than merely appearing in a manifest. Treat an unselected layer (still `Provisional` in `architecture.md`) as a stop condition, not a default guess — request the missing decision instead of picking a stack yourself.

Common missions: `M1 workspace-foundation` (above), then the archetype's own list below renumbered to start at `M2`.

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

## Mobile / Desktop Archetype

Use this profile when the target is a native mobile or desktop app instead of a web surface: native iOS, native Android, Flutter (one codebase targeting iOS + Android and optionally more), or a macOS/Windows desktop app. These do not have a URL model, SEO metadata, or a Worker redeploy — their distribution runs through app stores or signed installers. Read `references/mobile-desktop-deployment-lifecycle.md` for the release/promotion model; freeze the surfaces below before implementation.

Freeze these surfaces:

```text
Toolchain and project shape: iOS (*.xcodeproj/*.xcworkspace, Package.swift), Android (build.gradle(.kts), settings.gradle(.kts)), Flutter (pubspec.yaml + native runners), macOS (*.xcodeproj/Swift or cross-platform toolkit), Windows (*.csproj/*.sln, WPF/WinUI/MAUI or cross-platform toolkit)
Targets and minimums: OS/SDK floor (minSdk/targetSdk, deployment target, target framework), device classes (phone/tablet/desktop), orientation, per-target parity for Flutter
App shell and navigation: entry point, navigation model, deep links / universal links / app links, state restoration
Local persistence and sync: on-device storage (Core Data/SwiftData, Room, SQLite, Hive/Isar), offline behavior, background sync, migration of on-device schema across app versions
Platform capabilities: push notifications (APNs/FCM), permissions (camera, location, contacts), background tasks, in-app purchase/entitlements when present
Identity and data: auth flow (native, OAuth, platform sign-in), secure credential storage (Keychain/Keystore/DPAPI), account recovery
Signing and distribution identity: bundle/application identifier, signing certificates and provisioning profiles / keystore / code-signing cert (configured, never stored in PLAN/RUN), distribution channel (TestFlight + App Store, Play tracks + production, Developer ID/notarized, Microsoft Store/MSIX/installer)
Release isolation: development/staging build config (sandbox APIs, test push, non-production backend, debug entitlements) kept separate from production build config (live APIs, production push, production backend, release entitlements)
```

Common missions:

```text
M1 project/app-shell and navigation foundation for the chosen toolchain
M2 core feature and platform-capability integration (persistence, permissions, native APIs)
M3 identity, secure storage, and backend/data contract
M4 push notifications, background tasks, in-app purchase/entitlements when present
M5 beta distribution (TestFlight / Play internal or closed track) and store metadata/assets
M6 store submission/review readiness and E2E across device/OS states
```

Required E2E scenarios:

- App launches to first screen on the minimum supported OS/SDK and a current one.
- Primary feature flow passes on at least one phone and one larger form factor (tablet/desktop) the target list names.
- Permission grant and denial paths both behave (denied path does not crash or dead-end).
- Offline / no-network behavior for anything that persists or syncs locally.
- On-device data survives an app-version upgrade (persistence migration verified, not just a fresh install).
- Push notification receipt and tap-through, when notifications are in scope.
- Auth login, logout, and credential-storage behavior across app relaunch.
- Deep link / universal link / app link opens the correct in-app destination, when in scope.

Required verification per toolchain (run before any distribution gate):

```text
iOS/macOS Swift: xcodebuild test (unit + UI tests via XCTest/XCUITest); xcodebuild build for the release config
Android:         ./gradlew test (unit) and ./gradlew connectedAndroidTest (instrumented, on an emulator/device); ./gradlew assembleRelease
Flutter:         flutter test (widget/unit) and flutter test integration_test/ (integration); flutter build for each native target in scope
Windows .NET:    dotnet test (unit/integration); dotnet build/publish for the release config
Desktop macOS:   xcodebuild test for a Swift app, or the cross-platform toolkit's own test runner
```

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
APPSHELL-* native app shell/navigation
CAP-* platform capabilities (push, permissions, background tasks)
STORE-* store submission/review/distribution
SIGN-* signing/provisioning/notarization
```

## Profile Selection Rule

If a task spans profiles, freeze the shared contract first, then split missions by ownership. For example, a SaaS marketing site plus authenticated dashboard should keep public-site SEO/content missions separate from app-shell tenant/auth/billing missions and integrate through a final release/E2E gate.
