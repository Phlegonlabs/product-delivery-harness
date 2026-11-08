# Architecture Playbook

Use this playbook to make architecture sections implementation-ready. The overall architecture may remain stack-neutral where requirements do not justify a named choice. Browser products use `references/frontend-stack-selection.md`; backend, persistent-data, or auth products use `references/backend-stack-selection.md`; mobile products use `references/mobile-stack-selection.md`. Technology proposals remain non-executable until the Stack Decision Checkpoint and Product Definition Approval are both approved.

## Caller And State Method

Apply [Architecture Method](../../delivery-harness/references/architecture-method.md) to the accepted journeys. Keep implementation signatures and types in the downstream implementation-design assignment. Compare structural alternatives only when coupling, durability, trust or migration remains unresolved. Reuse valid enhancement decisions and small-repair designs. These methods add no approval gate or mandatory package field.

## Baseline Architecture Coverage

Write the canonical `architecture.md` in English and draft its complete `architecture.zh-TW.md` review copy alongside it under `bilingual-review.md`.

Every architecture should cover:

- Product archetype, target surfaces, actors, and external systems.
- Frontend or client responsibilities.
- For products with a browser frontend, frontend technology layers: deployment/runtime, rendering model, language, package manager, framework, UI library, component foundation, styling approach, build tool, routing/data approach, and testing.
- For products with a backend, persistent data, or auth requirement, backend technology layers in this order: service topology (monolith versus named services and monorepo versus polyrepo), runtime/framework, database category, database engine, auth strategy, auth provider, API style, background jobs/queue, and file/object storage.
- Backend, service, or workflow orchestration responsibilities.
- Data model and persistence.
- API, event, file, or trigger contracts.
- Authentication, authorization, and role boundaries.
- Monetization model and ownership, plus the separately resolved affiliate, referral, or reseller operating model when applicable. Apply `monetization-and-partner-channel-guide.md`.
- Security, privacy, secrets, and audit concerns.
- Required PRD Security Requirements rows: name each asset/boundary, enforcement point, safe failure, PRD ID, and TEST ID in Auth, Permissions, and Security.
- The Data and Trust Gate and, when applicable, the AI and Automation Gate, with their applicable tests, using the fields in `output-contract.md`'s architecture template.
- Integrations and failure handling.
- Deployment, environment configuration, migrations, and rollback.
- Provider-neutral release targets for every deployable surface (see Provider-Neutral Release Target Pattern).
- Observability, metrics, alerting, and audit logs.
- Scaling, reliability, idempotency, retries, and rate limits.

## Full-Stack Journey Handoff

For each accepted journey, connect the PRD role/data/action and success/failure/recovery outcomes to the actual screen or client, API/service contract, authorization enforcement, data model and persistence, external dependencies and operational owner. Name validation errors, denied access, retry/idempotency, partial failure and recovery where applicable. Link the same requirement and TEST IDs; do not duplicate the PRD or invent a new handoff specification. Headless and local-only products record their actual client and explain inapplicable layers.

Recommend a complete compatible stack when the owner has no preference, including runtime, client, backend, auth/data, agent tools and tests as applicable. Reuse the current approved stack for enhancements unless the accepted scope changes it.

## Provider-Neutral Release Target Pattern

Use this for every deployable web, API, mobile, desktop, or browser-extension surface. Close the inventory of deployable surfaces during discovery, and record each target with the fields, source policy and availability rules in [Release Targets](output-contract.md#architecturemd). A build, upload, submission, deployment command, notarization result, or store approval is an intermediate event, not availability.

Keep native mobile and desktop targets in this record. Do not force TestFlight, Play tracks, App Store, notarized downloads, Microsoft Store, or signed update feeds into the two-row hosted environment table.

### Surface Naming Convention

Name an independently released unit from what it is, not from where it runs. Use lowercase kebab case: the production name is `<product-slug>-<surface-suffix>` and never carries `-prod`; the development name adds `-dev`. Long-lived `-staging` or `-qa` names are valid only when those environments exist. Ephemeral branch/SHA previews keep platform-generated identities.

Use `web`, `api`, and `extension` as the normal suffixes. Use `admin`, `worker`, `jobs`, `agent`, `webhook`, `realtime`, or `cli` only for a separately released artifact. Native release artifacts may use `ios`, `android`, `macos`, `windows`, or `linux`; a hosted backend shared by native clients is still `api`, not `ios-api` or `android-api`. One unit serving a combined web application and its API remains `web`; independently deployed web and API units get separate names. Keep Chrome, Firefox, an app store, and a hosting vendor in `provider` or channel fields. Add a browser name to the suffix only when browser-specific artifacts actually diverge, such as `chrome-extension` and `firefox-extension`. A public listing title may differ from this internal release name.

## Platform Delivery Sequence

Record this sequence only when the human owner selects a whole-platform order. A shared API is a normal shared surface; user-facing platform classes cannot be renamed into a shared label. Reuse `output-contract.md`'s exact fields and table.

## Candidate-to-Production Release Pattern

For a deployable hosted web, API, or backend product, resolve the platform before drafting and keep one repository and one codebase. The release source policy is owned by [Release Targets](output-contract.md#architecturemd); the environment contract is in the output contract's Deployment and Operations template. Cloudflare uses native Workers Previews when supported, Pages only by owner choice, or an approved isolated fallback.

Do not model development as a second codebase or persistent branch. It is an isolated environment deployed from the exact candidate run branch/SHA. Do not let a development environment access production customer data, production sessions, or live payment mutations. Specify promotion prerequisites, migration order, backward compatibility, secret ownership, recovery, and evidence invalidation.

Isolation does not mean development stays empty. When the product has content-shaped data (articles, images, other catalog-style entities), seed the development environment with representative mock/sample data in the development migration or setup step. Record the seed in the development row's Migration Order cell of the environment-contract table (see `references/output-contract.md`'s architecture.md template) or an equivalent setup step, and never source it from a live production copy unless the user explicitly authorizes and scopes a separate sync/anonymization process. Write each Migration Order entry for the human or CI release process that runs after the harness produces the candidate; the harness does not consume it.

## Web App Pattern

Use for browser-based SaaS, marketplaces, dashboards, portals, and public web products.

- Frontend: routes, layout model, server/client rendering assumptions, form validation, state management, responsive behavior.
- Frontend decision: status (`Required`, `Selected`, `Approved`, `Recommended`, or `Provisional`), product-fit rationale, alternatives, official-source verification date, and uncertainty. Only the first three are executable.
- Backend: API layer, business services, validation, background jobs, file handling, notifications.
- Data: relational entities by default for transactional products; include indexes, tenancy, soft delete, audit history, and retention when relevant.
- APIs: list core REST, GraphQL, RPC, or server action contracts; include pagination, filtering, validation errors, and auth errors.
- Security: session management, CSRF when applicable, RBAC, tenant isolation, input validation, secure file upload.
- Operations: feature flags, scheduled jobs, queues.
- Commercial systems when applicable: apply `monetization-and-partner-channel-guide.md`.

## Mobile and Desktop Distribution Discipline

The mobile and desktop patterns below name toolchains, store fees, code-signing steps, testing tracks, and OS-version deadlines that change on the vendors' schedule. Do not copy any specific fee, tester count, testing-window rule, target-API deadline, minimum OS version, or signing/notarization step from memory into a PRD. Verify each against the official source cited in the pattern on the date the PRD is written, and record that check date and the direct link in `architecture.md`'s deployment/operations section. When you cannot verify a number live, write the requirement without it and mark it as needing live verification.

Native iOS, native Android, Flutter, React Native, and desktop release through an app store, testing track, notarized download, or signed installer/update feed. When the channel cannot restore an installed version, halt a staged rollout where possible and ship a signed forward-fix through the same distribution path. A mobile or desktop product with a server backend still resolves that backend's hosting separately.

## Native iOS Pattern

Use for a native Apple-platform app built directly against Apple's SDKs.

- Toolchain: Xcode, Swift with SwiftUI or UIKit, Swift Package Manager. Evaluate CocoaPods only when existing pods or a required dependency need it, after verifying its current support status and compatibility from official sources.
- Client architecture: navigation and screen structure (commonly MVVM with a coordinator or navigation stack), local persistence (Core Data, SwiftData, or SQLite), local state, offline behavior, permissions, deep links, and device capabilities.
- Distribution: a paid Apple Developer Program membership (annual fee) is required for the App Store and TestFlight. Builds are code-signed with a distribution certificate and a provisioning profile. TestFlight is the beta channel before public release (internal and external tester limits). Push goes through APNs.
- Backend: sync API, auth sessions, APNs sending, media upload, and entitlement or subscription checks when the app sells content.
- Purchases: apply `monetization-and-partner-channel-guide.md` when the app charges for digital access. StoreKit may be sufficient for one Apple-only surface.
- Data: local cache versus remote canonical records, conflict resolution, sync timestamps, and deletion behavior.
- Security: Keychain for secrets, biometric or device auth when needed, PII minimization, and jailbroken-device assumptions only when the product requires them.
- Operations and required verification: app-review turnaround, server compatibility windows across app versions in the wild, analytics, crash reporting, and limited rollback after an App Store release (ship a new build or use phased release / expedited review). Official sources: [Apple Developer Program](https://developer.apple.com/programs/), [TestFlight](https://developer.apple.com/testflight/), and [TN3125](https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles).

## Native Android Pattern

Use for a native Android app built directly against the Android SDK.

- Toolchain: Android Studio, Kotlin, Gradle, and Jetpack Compose (or the older Views system).
- Client architecture: as the Native iOS Pattern, commonly MVVM with Jetpack components and Room over SQLite or DataStore for local persistence.
- Distribution: a Google Play Console developer account requires a one-time registration fee. Play offers internal, closed, and open testing tracks before production. Under Play App Signing, Google holds the app signing key and you sign uploads with an upload key. New personal developer accounts must meet a pre-production testing requirement (minimum testers for a minimum number of days before production access). New apps and updates must target a minimum Android API level by a Play deadline that moves each year. Push goes through FCM.
- Backend and data: as the Native iOS Pattern, with FCM for notifications.
- Purchases: as the Native iOS Pattern; Google Play Billing, cross-platform subscription management, web checkout, and partner distribution remain separate decisions.
- Security: EncryptedSharedPreferences or the Keystore for secrets, biometric or device auth when needed, PII minimization, and rooted-device assumptions only when required.
- Operations and required verification: staged rollout percentages (halt or reduce rather than un-ship), server compatibility windows across app versions, analytics, and crash reporting. Official sources: [Play Console registration](https://support.google.com/googleplay/android-developer/answer/6112435), [Play App Signing](https://developer.android.com/studio/publish/app-signing), [test your app](https://developer.android.com/guide/app-bundle/test), and [target API level requirements](https://developer.android.com/google/play/requirements/target-sdk).

## Flutter Pattern

Use for a single cross-platform codebase targeting iOS and Android from one source (and optionally web, macOS, Windows, and Linux).

- Toolchain: one Dart codebase, dependencies declared in `pubspec.yaml` and resolved from pub.dev. Native-only capabilities are reached through platform channels (MethodChannel, or a typed generator such as Pigeon) that call into Kotlin/Java on Android and Swift/Objective-C on iOS.
- Distribution: Flutter compiles to native binaries, so it bypasses neither store. An iOS+Android product needs BOTH an Apple path exactly as in the Native iOS Pattern AND a Google path exactly as in the Native Android Pattern. Budget for both memberships, both signing setups, and both review processes. If you also ship Flutter desktop, add the matching desktop distribution path below.
- Client architecture, backend, data, and security: follow the native patterns (push via APNs on iOS and FCM on Android). Record which platforms each plugin actually supports.
- Operations and required verification: verify supported platforms and OS-version ranges for each shipped target. Official sources: [Flutter supported platforms](https://docs.flutter.dev/reference/supported-platforms), [Flutter iOS deployment](https://docs.flutter.dev/deployment/ios), and [Flutter Android deployment](https://docs.flutter.dev/deployment/android), plus the Apple and Google sources in the native patterns.

## React Native / Expo Pattern

For App + companion Web delivery, apply `mobile-stack-selection.md#app-and-companion-web-contract`: one product architecture with separate iOS, Android and showcase/browser release surfaces, explicit shared-code boundaries and per-platform acceptance. A mobile Expo choice does not decide the Web frontend stack or merge store releases with website deployment.

Use for a single cross-platform codebase targeting iOS and Android from JavaScript/TypeScript, especially when sharing logic with an existing React web codebase. React Native's documentation recommends a Framework for new apps, and Expo is the recommended one; see `mobile-stack-selection.md` for choosing this over Flutter or native and for the Expo-vs-bare workflow decision.

- Toolchain: one JavaScript/TypeScript codebase (npm/yarn/pnpm) with Expo (managed workflow, `create-expo-app`) as the default. Choose bare React Native (via prebuild or ejection) only when a native module needs native-project access Expo's managed workflow and config plugins cannot provide, and record which module forced it.
- Targets: iOS and Android; confirm current support and per-target limitations before promising web (React Native for Web) or Windows/macOS.
- Client architecture: navigation (commonly React Navigation or Expo Router), local persistence (SQLite, or AsyncStorage/MMKV for key-value), local and shared state, offline behavior, permissions, deep links, and device capabilities reached through native modules.
- Distribution: as in the Flutter Pattern, BOTH the Apple and Google paths are required. EAS Build compiles and signs both platforms in the cloud; EAS Submit uploads builds to both stores; manual App Store Connect / Play Console upload remains the alternative.
- Over-the-air updates: EAS Update ships JavaScript and asset changes without an app-store review cycle; native code changes (new native modules, native config) always require a new store-reviewed build. Record which change types are OTA-eligible.
- Backend, data, and security: as the native patterns, with secure storage via the platform Keychain/Keystore through a native module. Record which platforms each native module supports.
- Operations and required verification: do not copy an Expo SDK version, EAS build tier/pricing, or supported-OS range from memory. Official sources: [React Native: Get Started](https://reactnative.dev/docs/environment-setup), [Expo docs](https://docs.expo.dev/), [EAS Build](https://docs.expo.dev/build/introduction/), [EAS Submit](https://docs.expo.dev/submit/introduction/), and [EAS Update](https://docs.expo.dev/eas-update/introduction/), plus the Apple and Google sources in the native patterns.

## Desktop App Pattern

Use for an installable desktop application on macOS, Windows, Linux, or a set of them.

- macOS toolchain and distribution: build with SwiftUI or AppKit (or a cross-platform toolkit, see below). Sign with a Developer ID certificate; apps distributed outside the Mac App Store must also be notarized by Apple (submitted with `notarytool`). Distribute by direct download or the Mac App Store (sandboxing required). Official sources: [notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) and [macOS distribution](https://developer.apple.com/macos/distribution/).
- Windows toolchain and distribution: build with WinUI or .NET (WPF or WinForms), or a cross-platform toolkit. Package as MSIX (must be signed) or a traditional installer. Distribute by direct download, which needs a certificate that chains to a trusted root, or the Microsoft Store, which re-signs MSIX submissions. Official sources: [MSIX overview](https://learn.microsoft.com/en-us/windows/msix/overview), [signing an MSIX package](https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview), and [choose a distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path).
- Linux toolchain and distribution: build with GTK or Qt, or a cross-platform toolkit. Ship as a Flatpak on Flathub, a Snap on the Snap Store, deb/rpm packages from a signed repository, or an AppImage. Name the supported distributions and the oldest glibc you build against. Official sources: [Flathub](https://docs.flathub.org/docs/for-app-authors/submission) and [Snapcraft](https://snapcraft.io/docs).
- Cross-platform desktop alternative: when one codebase should target both macOS and Windows (and often Linux), consider Tauri (OS-native webview with a Rust backend, small binaries) or Electron (bundled Chromium and Node.js, larger binaries). Either still has to satisfy each OS's signing and distribution rules above, including macOS notarization and Windows signing. Official sources: [Tauri](https://tauri.app/) and [Electron](https://www.electronjs.org/).
- Client architecture: window and view structure, local persistence and file handling, offline-first behavior, auto-update mechanism, OS integration (menu bar, tray, notifications, file associations), and permissions.
- Backend and data: many desktop apps are local-first with optional sync; when a backend exists, resolve its hosting separately, and specify sync, conflict resolution, and auth-session handling.
- Security: OS keychain/credential store for secrets, code-signing integrity, update-channel integrity (signed updates), and PII minimization.
- Operations and required verification: signed auto-update delivery, per-OS minimum-version support, crash reporting, and staged rollout where the update framework supports it. Rollback means shipping a prior signed version through the same update channel. Record the verification date and the official sources above on `stack-decisions.md`'s `Compatibility checked on:` line; signing, distribution, and rollout stay in `architecture.md`.

## Browser Extension Pattern

Use for a browser extension. The interview resolves the complete v1 browser target set before architecture; Chrome with Manifest V3 is a common single-target choice, but Firefox and Safari have separate stores and API differences. Never turn the common case into a silent target decision.

- Toolchain: TypeScript plus an extension-aware bundler such as Vite with CRXJS or WXT (see `frontend-stack-selection.md`).
- Client architecture: a `manifest.json` (V3) declares the entry points. A service worker is the event-driven background context; there is no persistent background page. Content scripts run inside web pages with only partial extension-API access; extension pages (popup, options, side panel) are ordinary HTML/TypeScript documents with full API access. Assign each workflow to the context that owns it and define how contexts communicate (`chrome.runtime` messaging, long-lived ports, or storage events).
- Permissions model: declare the narrowest host and API permissions that work. `host_permissions` drive install-time warnings and store review; use optional permissions with runtime requests where the UX allows.
- Backend and data: `chrome.storage` for settings and local state. When sync, accounts, or shared data need a companion backend, resolve its hosting separately and define the requests the extension may make and how its auth tokens are stored.
- Distribution: the release path is the Chrome Web Store developer dashboard (one-time registration fee), store review before publication, versioned uploads, and staged rollouts; the browser itself delivers updates. Firefox (addons.mozilla.org) and Safari (App Store as a Safari Web Extension) each need their own listing and review when targeted. Record each store destination as a release target in `architecture.md`'s `## Release Targets`.
- Operations and required verification: extension version pinning by the store, review turnaround for each update, and a forward-fix through the same store review rather than instant rollback. Official sources: [Chrome Extensions docs](https://developer.chrome.com/docs/extensions/) and [Chrome Web Store](https://developer.chrome.com/docs/webstore/); do not copy limits, review timing, or fees from memory.

## Internal Tool Pattern

Use for admin panels, operations consoles, review queues, workflow tools, and back-office systems.

- Frontend: dense table views, filters, search, bulk actions, detail panels, audit trails, keyboard efficiency where useful.
- Backend: permissioned admin endpoints, approval workflows, import/export, background processing.
- Data: operational records, user actions, review status, assignment, SLA timestamps, immutable audit entries.
- APIs: guarded mutations, bulk operation contracts, validation summaries, idempotency keys for destructive or repeat actions.
- Security: least-privilege roles, approval gates, PII masking, access review.
- Operations: queue visibility, retry tools, manual override policies, incident playbooks.

## Automation and Agent Workflow Pattern

Use for scheduled automations, event-triggered workflows, AI agents, data pipelines, and integration tools.

- Triggers: schedule, webhook, email, file drop, database change, manual run, or user command.
- Orchestration: workflow steps, state machine, queue, retry policy, and timeout.
- Tools and integrations: source system, destination system, auth method, scopes, rate limits, quotas, and sandbox behavior.
- Data: run records, step logs, input snapshots, generated outputs, idempotency keys, deduplication, and replay support.
- Safety: permission boundaries, dry-run mode, confirmation gates, prompt injection defenses for AI workflows, output validation.
- Model and data boundary: provider/runtime, version-change policy, inputs and context sent to the model, retention/training terms, retrieval sources, and confidential-data exclusions.
- Evaluation: representative task set, required quality and safety thresholds, prohibited outcomes, deterministic checks around model output, and regression cadence.
- Human control: exact tools and side effects the automation may invoke, approval points, cancellation, emergency disable, fallback behavior, and who accepts residual risk.
- Execution selection: use `agentic-runtime-selection.md` to choose a fixed workflow, single agent, or bounded multi-agent topology before naming SDKs or models.
- Failure handling: partial success, retryable and non-retryable errors, dead-letter queue, alerting, resume, rollback or compensating actions.
- Observability: run history, step-level logs, latency, success rate, cost, token or API usage, integration error rates.

## Agentic Operations Console Pattern

Use for an agent or automation product whose Shape row records `console: operations`. Build this deliberately designed backend control surface from six modules:

- Configuration: agent definitions, model and provider routing, tool permissions, and prompt and skill versions.
- Execution: run history, traces and logs, rerun, and a kill switch.
- Human-in-the-loop: approval queue, escalation, and who approves what.
- Cost and usage: tokens, calls, spend, and budget alerts.
- Quality: eval sets, pass rates, and regression comparison; reuse `eval-policy/1` from `eval-policy-contract.md`.
- Security: tenant isolation, secret management, and audit export; reuse the PRD's Data and Trust and Security Requirements and their TEST traces.

A `console: operations` shape requires User Journeys for configuration, run inspection, and approval, plus at least one TEST per module the product selects. Reflect the selected modules in `architecture.md`'s component, observability, and security sections.

## API or Backend Service Pattern

Use when the product is mainly a service consumed by other systems.

- Interfaces: endpoints, events, SDK boundaries, authentication, versioning, error taxonomy.
- Domain services: validation, authorization, business rules, consistency boundaries, transaction design.
- Data: canonical entities, migrations, indexing, archival, retention, encryption, and backup.
- Operations: SLOs, capacity, autoscaling, deploy strategy, backward compatibility, and incident response.

## Modular Monolith Pattern

Use for an application with many business modules (ERP, back-office suites, multi-module SaaS) that should ship as one deployable with hard module boundaries. It organizes the backend and data; each module's screens still follow the Web App or Internal Tool Pattern. Durable workflow, multi-tenant isolation, and a typed API for several clients are compared in the optional [architecture catalog](../../delivery-harness/references/option-library/architecture.md).

- Modules: one bounded context per module, each with a named owner, a purpose, and the business data it owns. List them, their owners, and their allowed dependencies in `architecture.md`'s component section.
- Shared kernel: the few concepts every module needs, such as party, product, unit of measure, currency, organisation unit, and document numbering. Only the kernel owner changes it. Modules depend on the kernel, never the reverse. A concept only two modules use belongs to one of them, not the kernel.
- Data: keep master data (parties, products, price lists: few writers, many readers) apart from transactional data (documents and postings, written by one module). Use one database with a schema or table prefix per module. A module reads and writes only its own tables.
- Cross-module access: only through the owning module's API or its published events, never another module's tables or internal types.
- Events: write each event to an outbox in the same transaction as the state change it reports. Consumers are idempotent (deduplicate by event ID), tolerate redelivery and reordering, and have a dead-letter and replay path. Call another module synchronously only when the caller cannot proceed without the answer.
- API: each module exposes a typed, versioned internal API for commands, queries, and event schemas, and callers use it as if it were remote. A module can then be extracted as a service without changing its callers.
- Auth and audit: declare permissions per module as module, resource, and action, and enforce them in the module's API as well as the UI. Each module writes its own audit entries for sensitive actions.
- Operations: one deployable and one release target. Run per-module migrations in dependency order, kernel first, and tag logs, metrics, and alerts with the module and its owner.
- Tests: each module has its own test suite that runs against fakes of other modules' published APIs. Add a small set of cross-module business process tests (for example quote to order to invoice to payment) that run through real modules, each with its own `TEST-*` ID. A CI check fails on an import across a module boundary.

## Decision Guidance

- Prefer the simplest architecture that satisfies the stated workflows and constraints.
- Choose the Modular Monolith Pattern over the Web App Pattern or API or Backend Service Pattern when the product has several business modules with separate owners or rules that share master data, run business processes across modules, and release together. Keep the Web App Pattern for one domain owned by one team, and the API or Backend Service Pattern for a service consumed by other systems. Split a module into its own deployable only for a recorded scaling, release, or ownership reason.
- Call out tradeoffs when choosing between synchronous requests, background jobs, event-driven design, or scheduled processing.
- Specify idempotency for payment, notification, import, workflow, and external mutation flows.
- Specify authorization at both UI and backend layers.
- Implement required security controls and denial/no-side-effect tests with the task that touches their boundary. A scaffolded protected route stays fail-closed until those controls and tests exist.
- For each applicable frontend, backend/data, mobile/desktop, commercial, or AI/automation area, present coherent stack bundles and record the owner-approved result. `Recommended` and `Provisional` rows are draft inputs, never implementation authority.
- Treat platform, rendering, framework, UI library, and build tooling as separate decisions.
- Avoid naming other vendors unless the user specified one, the current environment requires it, or a documented tradeoff makes the recommendation materially more useful.
