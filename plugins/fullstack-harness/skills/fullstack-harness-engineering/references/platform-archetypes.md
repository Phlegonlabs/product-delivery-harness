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
```

## Greenfield / Empty Repository

Detect this before applying any archetype profile below: no toolchain manifest, no app source tree, or no locally runnable dev/build command exists yet. Greenfield detection is per-toolchain, not whole-repo — a repository can be simultaneously non-greenfield for an already-established platform (e.g. a working web app) and greenfield for a newly-added one (e.g. no iOS project yet); apply the toolchain-detection table below per target platform, and scope the new workspace-foundation mission only to the platform that is actually greenfield. Every archetype's "Common missions" list below assumes the workspace and chosen stack already exist — on a greenfield repository, insert one workspace-foundation mission before them and shift the archetype's own list down by one (its `M1` becomes `M2`, and so on). This renumbering applies only when drafting a fresh single-archetype plan from scratch; when a later plan revision adds a new platform to an already-integrated project, mint the new workspace-foundation mission with the next available mission ID in that revision instead — mission IDs are opaque and do not encode order (see `contract-and-traceability.md`'s Mission And Task Identity section), so do not renumber or disturb any already-integrated mission's ID.

Detect which toolchain is (or should be) in play before scaffolding, and branch — do not assume a JS package manager. Match the frozen `stack-decisions.md` Frontend/Platform Technology Decision (see `../prd-builder/references/frontend-stack-selection.md`) to one of these, checking the repository for an existing manifest of each shape first:

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
  Web framework: install and wire the decided framework (e.g. Astro, a React framework)
  UI library: install the decided UI library when one is named (e.g. React, Preact, Vue), including the framework's integration for it
  Build tool: install/configure the build tool the framework doesn't already own
  Styling/components: install the decided styling and component approach (e.g. Tailwind, a component library) and wire its build-time configuration
  Routing/data, testing: scaffold the minimal contract needed for later missions to extend, per the decision record

iOS/macOS Swift:
  Project: create the Xcode project/workspace (*.xcodeproj / *.xcworkspace) or a Package.swift target, with app, unit-test, and UI-test targets
  Dependencies: wire Swift Package Manager (or the decided manager) for the named libraries
  App shell: minimal navigation/entry point the later feature missions extend
  Signing/config: record the bundle identifier and target OS version from the decision record

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
  Config: record the target framework and packaging shape (MSIX vs installer)
```

**Environment configuration (every toolchain).** Reserve a place for environment secrets from the first scaffold commit, before any task needs one: create a tracked `.env.example` (or the toolchain's native equivalent — e.g. `local.properties.example` for Android, an `.xcconfig` template for Swift) listing every environment variable the app currently needs by name, with a placeholder or one-line description and no real value. Ensure the real `.env` (or equivalent local secret file) is git-ignored from this same commit, never committed. Treat `.env.example` as living documentation: a later task that reads a new environment variable adds its entry to `.env.example` in the same commit that introduces the read (see `commit-convention.md`), not as a separate cleanup pass. Never invent a placeholder's real value — when a required variable's actual value is unavailable, stop and ask per `contract-and-traceability.md`'s Stop And Ask Conditions rather than guessing.

Exit criterion: a locally runnable dev/build for the detected toolchain and its passing build/compile plus test discovery — a running dev server and passing build/typecheck for JS/TS web, a successful `xcodebuild build`/`swift build` for Swift, a successful `./gradlew assembleDebug` for Android, `flutter build` (or `flutter run` device check) for Flutter, `dotnet build` for .NET — proving every installed layer actually works together rather than merely appearing in a manifest. Treat an unselected layer (still `Provisional` in `stack-decisions.md`) as a stop condition, not a default guess — request the missing decision instead of picking a stack yourself.

Common missions: `M1 workspace-foundation` (above), then the archetype's own list below renumbered to start at `M2` — but this renumbering is only for a fresh from-scratch single-archetype plan; a later revision that adds a new platform to an already-integrated project mints the workspace-foundation mission with the next available mission ID instead (see the per-toolchain and mission-ID note above).

### Worked `M1 workspace-foundation` Mission Object

This is a complete, copy-paste-ready PLAN-v6 mission object for the scaffold mission above. Every field keeps the meaning and default that `assets/templates/HARNESS_PLAN.template.md` already explains for its main worked mission — only `objective`, `write_scope`, `stop_conditions`, the verifier commands, and `tasks` actually differ for a scaffold mission.

```json
{
  "id": "M1",
  "alias": "workspace-foundation",
  "objective": "Create the workspace manager root and a locally runnable application foundation with every decided frontend layer installed.",
  "priority": 100,
  "merge_rank": 10,
  "trace_ids": ["PRD-<architecture-decision-trace>"],
  "write_scope": ["package.json", "<lockfile>", "apps/web/**", ".env.example", ".gitignore"],
  "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
  "resource_inventory_complete": true,
  "serialized_resources": [],
  "runtime_resources": [],
  "worktree_eligible": true,
  "required_skills": [],
  "stop_conditions": [
    "Stop if any Frontend Technology Decision layer is still Provisional; request the missing decision instead of guessing a stack."
  ],
  "worker_verifiers": [
    {
      "id": "m1-typecheck",
      "cwd": ".",
      "argv": ["<package-manager>", "run", "typecheck"],
      "pass_signal": "Typecheck exits 0"
    }
  ],
  "integration_verifiers": [
    {
      "id": "m1-build",
      "cwd": ".",
      "argv": ["<package-manager>", "run", "build"],
      "pass_signal": "Build exits 0 with every installed layer (framework, UI library, build tool, styling/components) wired and locally runnable"
    }
  ],
  "tasks": [
    {
      "id": "M1/T01",
      "alias": "workspace-init",
      "objective": "Initialize the workspace manager, lockfile, and root script contract.",
      "depends_on": [],
      "write_scope": ["package.json", "<lockfile>"],
      "verifiers": [{"id": "m1-t01", "cwd": ".", "argv": ["<package-manager>", "ci"], "pass_signal": "Frozen install exits 0"}]
    },
    {
      "id": "M1/T02",
      "alias": "framework-and-ui-stack",
      "objective": "Install and wire the decided framework, UI library, build tool, and styling/components together.",
      "depends_on": ["M1/T01"],
      "write_scope": ["apps/web/**"],
      "verifiers": [{"id": "m1-t02", "cwd": ".", "argv": ["<package-manager>", "run", "build"], "pass_signal": "Build exits 0 and the dev server serves a page locally"}]
    },
    {
      "id": "M1/T03",
      "alias": "environment-configuration",
      "objective": "Reserve every known environment variable in a tracked .env.example with placeholder values, and git-ignore the real local secret file.",
      "depends_on": ["M1/T02"],
      "write_scope": [".env.example", ".gitignore"],
      "verifiers": [{"id": "m1-t03", "cwd": ".", "argv": ["<package-manager>", "run", "typecheck"], "pass_signal": "Typecheck exits 0 with no committed .env, and .env.example lists every variable read by the scaffolded app with a placeholder, not a real value"}]
    }
  ]
}
```

`M1/T03` is a worked example, not a fixed template: list only the environment variables the scaffolded layers actually read at this point (for example a database connection string or an auth provider client ID), one placeholder line each, and add more entries in later tasks/missions exactly when they introduce a new read — see `commit-convention.md`'s atomic-boundary rule and the Environment configuration paragraph above.

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

M4 is an illustrative single line, not a mandate to build every authenticated screen in one mission. Per `contract-and-traceability.md`'s mission-granularity corollary, split it into one mission per page (or a small tightly-coupled group) and pair each with its own scoped `visual` review as soon as that mission integrates. When the product has a design system, those page missions come after its tokens and primitives are implemented — see `execution-task-decomposition.md`'s UI Build Order.

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
```

Common missions:

```text
M1 content/source and routing foundation
M2 page templates and responsive layout
M3 SEO/metadata/structured data
M4 conversion forms, analytics, consent, integrations
M5 accessibility, visual QA, performance
M6 sitemap/robots/redirect checks
```

M2 and M5 above are illustrative single lines, not a mandate to lump every page into one mission or defer all visual QA to the end. Per `contract-and-traceability.md`'s mission-granularity corollary, split M2 into one mission per page (or a small tightly-coupled group, for example the legal/about/contact pages sharing one trivial template) and pair each with its own scoped `visual` review as soon as that mission integrates, rather than one M2 covering the whole page inventory reviewed once by a later M5.

When the product has a design system, M2's page templates come after its tokens and primitives are implemented — see `execution-task-decomposition.md`'s UI Build Order. Each page mission then implements its route from `design-system.json` and that route's `UI-*` entry in `PRD.md`.

Required E2E scenarios:

- Primary CTA or form submission reaches the expected destination.
- Metadata/canonical/OG render for key pages.
- Sitemap, robots policy, redirects, and 404 behavior are checked when relevant.
- Analytics/conversion events fire or are stub-verified.
- Responsive and visual checks cover page templates, not just one page.

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

Use this profile when the target is a native mobile or desktop app instead of a web surface: native iOS, native Android, Flutter (one codebase targeting iOS + Android and optionally more), or a macOS/Windows desktop app. These do not have a URL model or SEO metadata. Freeze the surfaces below before implementation.

The design-source input for this profile is the active visual route recorded in the PRD UI Design Handoff, written for the resolved platform's HIG, Material, or desktop window conventions. When the Design System Need Gate is `required`, `design-system.md` and `design-system.json` bind and their primitive layers take the platform's vocabulary. When it is `not_required`, the approved native or desktop target plus platform conventions bind and no placeholder pair is created. UI evidence uses the native row and per-platform capture mechanism in `references/verification-gates.md`'s UI Evidence Gate (Simulator/Emulator/device screenshots), not browser screenshots.

Freeze these surfaces:

```text
Toolchain and project shape: iOS (*.xcodeproj/*.xcworkspace, Package.swift), Android (build.gradle(.kts), settings.gradle(.kts)), Flutter (pubspec.yaml + native runners), macOS (*.xcodeproj/Swift or cross-platform toolkit), Windows (*.csproj/*.sln, WPF/WinUI/MAUI or cross-platform toolkit)
Targets and minimums: OS/SDK floor (minSdk/targetSdk, minimum OS version, target framework), device classes (phone/tablet/desktop), orientation, per-target parity for Flutter
App shell and navigation: entry point, navigation model, deep links / universal links / app links, state restoration
Local persistence and sync: on-device storage (Core Data/SwiftData, Room, SQLite, Hive/Isar), offline behavior, background sync, migration of on-device schema across app versions
Platform capabilities: push notifications (APNs/FCM), permissions (camera, location, contacts), background tasks, in-app purchase/entitlements when present
Identity and data: auth flow (native, OAuth, platform sign-in), secure credential storage (Keychain/Keystore/DPAPI), account recovery
Analytics / crash reporting / feature flags: crash-reporting tool and its symbol-upload step, analytics events for key user actions, feature-flag mechanism when used — or explicitly out of scope for this product
Application identity: bundle/application identifier and the local build configuration that carries it
```

Common missions:

```text
M1 project/app-shell and navigation foundation for the chosen toolchain
M2 crash-reporting/analytics SDK wired into the app shell (symbol-upload step, key-event capture), feature flags when used
M3 core feature and platform-capability integration (persistence, permissions, native APIs)
M4 identity, secure storage, and backend/data contract
M5 push notifications, background tasks, in-app purchase/entitlements when present
M6 E2E across device/OS states
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
- A representative crash or logged error reaches the crash-reporting tool, and a key user action reaches the analytics pipeline (or both are explicitly marked out of scope with a stated reason).

Required verification per toolchain:

```text
iOS/macOS Swift: xcodebuild test (unit + UI tests via XCTest/XCUITest); xcodebuild build
Android:         ./gradlew test (unit) and ./gradlew connectedAndroidTest (instrumented, on an emulator/device); ./gradlew assembleDebug
Flutter:         flutter test (widget/unit) and flutter test integration_test/ (integration); flutter build for each native target in scope
Windows .NET:    dotnet test (unit/integration); dotnet build
Desktop macOS:   xcodebuild test for a Swift app, or the cross-platform toolkit's own test runner
```

## Trace ID Families

These are lenses on requirements that already carry a core trace ID, not a separate upstream ID space. Tag an existing `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `DS-*`, or `TEST-*` requirement with the archetype family that describes it — a tenant-isolation rule frozen as `ARCH-004` is also `TENANT-001`. A harness planner may apply a tag, because applying one mints nothing; the underlying requirement still comes from an upstream contract file, per `contract-and-traceability.md`'s Trace IDs rules. A tag inherits its requirement's coverage obligation, and the same downstream task and verification row prove both.

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
APPSHELL-* native app shell/navigation
CAP-* platform capabilities (push, permissions, background tasks)
```

## Profile Selection Rule

If a task spans profiles, freeze the shared contract first, then split missions by ownership. For example, a SaaS marketing site plus authenticated dashboard should keep public-site SEO/content missions separate from app-shell tenant/auth/billing missions and integrate through a final E2E gate.
