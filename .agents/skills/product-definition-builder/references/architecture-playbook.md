# Architecture Playbook

Use this playbook to make architecture sections implementation-ready. The overall architecture may remain stack-neutral where requirements do not justify a named choice. For products with a browser surface, record the required/selected frontend or make an evidence-backed recommendation as described in `frontend-stack-selection.md`. For products with a backend, persistent data, or auth requirement, apply the same per-layer status and cited-authority discipline to service topology first, then backend runtime, database, and auth layers as described in `references/backend-stack-selection.md`.

## Baseline Architecture Coverage

Every architecture should cover:

- Product archetype and target surfaces.
- Actors and external systems.
- Frontend or client responsibilities.
- For products with a browser frontend, frontend technology layers: deployment/runtime, rendering model, framework, UI library, build tool, routing/data approach, styling/component approach, and testing.
- For products with a backend, persistent data, or auth requirement, backend technology layers in this order: service topology (monolith versus named services and monorepo versus polyrepo), runtime/framework, database category, database engine, auth strategy, auth provider, API style, background jobs/queue, and file/object storage.
- Backend, service, or workflow orchestration responsibilities.
- Data model and persistence.
- API, event, file, or trigger contracts.
- Authentication, authorization, and role boundaries.
- Monetization model; product/price, purchase/subscription, entitlement, payment, tax, refund, and chargeback ownership; and the separately resolved affiliate, referral, or reseller operating model when applicable. Apply `monetization-and-partner-channel-guide.md` instead of assuming RevenueCat or treating every partner as an affiliate.
- Security, privacy, secrets, and audit concerns.
- Integrations and failure handling.
- Deployment, environment configuration, migrations, and rollback.
- For every deployable surface, provider-neutral release targets with stable IDs, development/production stage, source, artifact/signing, exact channel, release gate path, availability proof, rollout, and rollback or forward-fix.
- Observability, metrics, alerting, and audit logs.
- Scaling, reliability, idempotency, retries, and rate limits.

## Provider-Neutral Release Target Pattern

Use this for every deployable web, API, mobile, desktop, or browser-extension surface. Close an explicit inventory of expected deployable surfaces during discovery instead of leaving destinations for implementation. Give each surface a stable identity, then give each exact destination a stable target ID and a `development` or `production` stage. Each expected surface needs at least one target in each stage; reject a package that omits one. Keep `surface` separate from `provider`: the same stable surface may use different providers in development and production.

For every target, record:

- the stable surface identity and the stage-specific provider as separate fields;
- the explicit lowercase kebab-case surface suffix and provider-neutral release name, using the convention below;
- the source policy: the exact candidate run branch/ref for the internally tested development release and remote `main` for production after same-SHA fast-forward, or another exact branch or ref rule, including a required signed tag, recorded explicitly;
- artifact kind and exact signing/notarization requirement;
- exact environment, channel, store track, tester group, update feed, or direct-download destination;
- the ordered submission, promotion, review, or manual-approval path and its decision owner;
- the availability signal proving the intended audience can actually reach, install, or download the release and pass its smoke/acceptance check;
- rollout controls; and
- rollback to a prior deployed version when the platform supports it, or rollout halt/removal plus a signed forward-fix through the same distribution path when it does not.

A build, upload, submission, deployment command, notarization result, or store approval is an intermediate event, not availability. Hosted web/API availability requires the named route or API to serve the exact release and pass deployed smoke checks. Mobile and desktop availability requires the named audience to be able to install or download the approved artifact through the exact channel and pass the release smoke check.

Keep native mobile and desktop targets in this provider-neutral record. Do not force TestFlight, Play tracks, App Store, notarized downloads, Microsoft Store, or signed update feeds into the two-row hosted environment table below. Preserve stable target IDs across revisions and retire rather than reuse an ID whose destination changes meaning.

### Surface Naming Convention

Name an independently released unit from what it is, not from where it runs. Use lowercase kebab case. The production name is the canonical `<product-slug>-<surface-suffix>` name and never carries `-prod`; the development name is that exact canonical name plus `-dev`. Long-lived `-staging` or `-qa` names are valid only when those environments actually exist. Ephemeral branch/SHA previews keep platform-generated identities instead of inventing permanent names.

Use `web`, `api`, and `extension` as the normal suffixes. Use `admin`, `worker`, `jobs`, `agent`, `webhook`, `realtime`, or `cli` only for a separately released artifact. Native release artifacts may use `ios`, `android`, `macos`, or `windows`; a hosted backend shared by native clients is still `api`, not `ios-api` or `android-api`. A unit serving one combined web application and its API remains `web`; independently deployed web and API units get separate names. Keep Chrome, Firefox, an app store, and a hosting vendor in `provider` or channel fields. Add a browser name to the suffix only when browser-specific artifacts actually diverge, such as `chrome-extension` and `firefox-extension`. A public listing title may differ from this internal release name.

## Candidate-to-Production Release Pattern

For a deployable hosted web, API, or backend product, resolve the platform explicitly before writing this section; never default to one silently. Keep one repository and one codebase with `main` as the only persistent protected branch. Initial delivery and later enhancements both cut their run branch from observed remote `main`. After the run produces a fixed candidate, deploy and test that exact candidate branch/SHA in the isolated development environment when applicable, then separately fast-forward the same SHA to `main`. Development and production may use different providers; document both. The table uses Cloudflare's two-Worker model as an example, but keeps the same branch, isolation, authorization, and evidence guarantees elsewhere:

| Target | Release source | Runtime and data boundary | Required proof |
| --- | --- | --- | --- |
| Development | Exact candidate run branch/ref and verified SHA | Development environment (Worker for Cloudflare); isolated non-production bindings, secrets, data, auth, and sandbox payment credentials | Full internal suite on this SHA, migration result, deployed URL/version, and development smoke |
| Production | Exact remote `main` head after separately authorized fast-forward of the same verified candidate SHA | Production environment (Worker for Cloudflare); production bindings, secrets, data, auth, and live payment credentials | Main ref read-back, deployed SHA, production smoke, monitoring signal, and recovery version |

Do not model development as a second codebase or persistent branch. It is an isolated environment deployed from the exact candidate run branch/SHA. Do not let a development environment access production customer data, production sessions, or live payment mutations. Specify promotion prerequisites, migration order, backward compatibility, secret ownership, recovery, and evidence invalidation.

Isolation does not mean development stays empty. When the product has content-shaped data (for example articles, images, or other catalog-style entities), seed the development environment with representative mock/sample data as part of the development migration or setup step, so development testing sees realistic content without ever reading real production records. Record the mock-data seed in the development row's Migration Order cell of the environment-contract table (see `references/output-contract.md`'s architecture.md template) or an equivalent setup step, and never source it from a live production copy unless the user explicitly authorizes and scopes that as a separate, deliberate sync/anonymization process. Each Migration Order entry is written for the human or CI release process that runs after the engineering harness pushes its branch; the harness does not consume it.

## Web App Pattern

Use for browser-based SaaS, marketplaces, dashboards, portals, and public web products.

- Frontend: routes, layout model, server/client rendering assumptions, form validation, state management, responsive behavior.
- Frontend decision: status (`Required`, `Selected`, `Recommended`, or `Provisional`), product-fit rationale, alternatives rejected, official-source verification date, runtime compatibility, and any spike needed to close uncertainty.
- Backend: API layer, business services, validation, background jobs, file handling, notifications.
- Data: relational entities by default for transactional products; include indexes, tenancy, soft delete, audit history, and retention when relevant.
- APIs: list core REST, GraphQL, RPC, or server action contracts; include pagination, filtering, validation errors, auth errors, and rate limits.
- Security: session management, CSRF when applicable, RBAC, tenant isolation, input validation, secure file upload, secrets handling.
- Operations: environments, database migrations, feature flags, scheduled jobs, queues, monitoring, rollback.
- Commercial systems when applicable: separately selected store/billing, entitlement, paywall/checkout, merchant-of-record/tax, and affiliate/referral/reseller providers; stable identity joins; verified idempotent webhooks; refund/chargeback effects; reconciliation; and partner attribution, commission, payout, provisioning, and termination flows.

## Mobile and Desktop Distribution Discipline

The mobile and desktop patterns below name concrete toolchains, store fees, code-signing steps, testing tracks, and OS-version deadlines. These change on the vendors' schedule, not yours. Do not copy any specific fee, tester count, testing-window rule, target-API deadline, minimum OS version, or signing/notarization step from memory into a PRD. Verify each against the official source cited in the pattern on the date the PRD is written, and record that check date and the direct link in `architecture.md`'s deployment/operations section, the same way `frontend-stack-selection.md` records a verification date in `stack-decisions.md` for web platform claims. When you cannot verify a specific number live, write the requirement without the number and mark it as needing live verification rather than asserting a stale figure.

The native iOS, native Android, Flutter, React Native, and desktop targets do not use the web deployment-platform question (Cloudflare/Vercel/AWS/self-hosted). Their release path is an app store, testing track, notarized download, or signed installer/update feed. Record those exact development and production destinations as separate stable release targets; do not fit them into the hosted web environment table. A successful upload, submission, review approval, or notarization is not production availability until the intended audience can install or download the artifact and the release smoke check passes. When the channel cannot restore an already-installed version, recovery is a staged/phased-rollout halt where possible plus a corrected signed forward-fix through the same review or distribution path. A mobile or desktop product that also has a server backend still resolves that backend's own hosting separately.

## Native iOS Pattern

Use for a native Apple-platform app built directly against Apple's SDKs (not a cross-platform runtime).

- Toolchain: Xcode as the IDE, Swift with SwiftUI or UIKit for the UI, Swift Package Manager for dependencies. CocoaPods is an older dependency manager now in maintenance mode — prefer Swift Package Manager for new work and only carry CocoaPods forward for existing pods, verifying its current support status before relying on it.
- Client architecture: navigation and screen structure (commonly MVVM with a coordinator or navigation-stack pattern), local persistence (Core Data, SwiftData, or SQLite), local state, offline behavior, permissions, deep links, and device capabilities.
- Distribution: a paid Apple Developer Program membership is required to ship to the App Store and TestFlight — confirm the current annual fee live. Builds must be code-signed with a distribution certificate and a provisioning profile. TestFlight is the beta channel before public release; confirm the current internal and external tester limits live. Push notifications go through APNs (Apple Push Notification service).
- Backend: sync API, auth sessions, notification sending to APNs, media upload, and entitlement or subscription checks when the app sells content.
- Purchases: apply `monetization-and-partner-channel-guide.md` when the app charges for digital access. StoreKit may be sufficient for one Apple-only surface; select RevenueCat or another layer only from cross-platform, entitlement, paywall, analytics, or operations requirements verified on the PRD date.
- Data: local cache versus remote canonical records, conflict resolution, sync timestamps, and deletion behavior.
- Security: Keychain for secrets, biometric or device auth when needed, PII minimization, and jailbroken-device assumptions only when the product requires them.
- Operations and required verification: app-review turnaround, server compatibility windows across app versions in the wild, analytics, crash reporting, and the limited rollback after an App Store release (you ship a new build or use phased release / expedited review, you do not silently roll back an installed version). Verify current signing, TestFlight, and submission requirements at [Apple Developer Program](https://developer.apple.com/programs/), [TestFlight](https://developer.apple.com/testflight/), and [code signing and provisioning profiles (TN3125)](https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles) on the PRD date.

## Native Android Pattern

Use for a native Android app built directly against the Android SDK (not a cross-platform runtime).

- Toolchain: Android Studio as the IDE, Kotlin as the language, Gradle as the build system, and Jetpack Compose (or the older Views system) for the UI.
- Client architecture: navigation and screen structure (commonly MVVM with Jetpack components), local persistence (Room over SQLite or DataStore), local state, offline behavior, permissions, deep links, and device capabilities.
- Distribution: a Google Play Console developer account requires a one-time registration fee — confirm the current amount live. Play offers internal, closed, and open testing tracks before production. Play App Signing has Google hold and manage the app signing key while you sign uploads with an upload key. New personal developer accounts are subject to a pre-production testing requirement (a minimum number of testers opted in for a minimum number of days before you can apply for production access) — verify the current tester count and duration live, since these have changed. New apps and updates must target a minimum Android API level by a Play deadline that moves each year — verify the current required target API level and its deadline live. Push notifications go through FCM (Firebase Cloud Messaging).
- Backend: sync API, auth sessions, notification sending to FCM, media upload, and entitlement or subscription checks when relevant.
- Purchases: apply `monetization-and-partner-channel-guide.md`; Google Play Billing, cross-platform subscription management, web checkout, and partner distribution remain separate decisions.
- Data: local cache versus remote canonical records, conflict resolution, sync timestamps, and deletion behavior.
- Security: EncryptedSharedPreferences or the Keystore for secrets, biometric or device auth when needed, PII minimization, and rooted-device assumptions only when required.
- Operations and required verification: staged rollout percentages, server compatibility windows across app versions, analytics, crash reporting (for example via Play Console vitals), and rollback constraints after release (halt or reduce a staged rollout rather than un-shipping an installed version). Verify current fees, testing tracks, signing, testing gates, and target-API rules at [Play Console registration](https://support.google.com/googleplay/android-developer/answer/6112435), [Play App Signing](https://developer.android.com/studio/publish/app-signing), [test your app](https://developer.android.com/guide/app-bundle/test), and [target API level requirements](https://developer.android.com/google/play/requirements/target-sdk) on the PRD date.

## Flutter Pattern

Use for a single cross-platform codebase targeting iOS and Android from one source (and optionally web, macOS, Windows, and Linux).

- Toolchain: one Dart codebase, dependencies declared in `pubspec.yaml` and resolved from pub.dev. Native-only capabilities are reached through platform channels (MethodChannel, or a typed generator such as Pigeon) that call into Kotlin/Java on Android and Swift/Objective-C on iOS.
- Targets: Flutter compiles to native binaries per platform. Confirm the current supported OS-version ranges for each target you intend to ship live, since they move with releases.
- Distribution: because it compiles to native, Flutter does not bypass either store. An iOS+Android product still needs BOTH an Apple path (Apple Developer Program, code signing, TestFlight, App Store review) exactly as in the Native iOS Pattern AND a Google path (Play Console, testing tracks, Play App Signing, target-API rules) exactly as in the Native Android Pattern. Budget for both memberships, both signing setups, and both review processes. If you also ship Flutter desktop, add the matching desktop distribution path below.
- Client architecture, backend, data, and security: follow the same concerns as the native patterns (navigation and state, local persistence, sync API, secure storage, push via APNs on iOS and FCM on Android). A plugin that wraps a native capability may differ per platform — record which platforms each plugin actually supports.
- Operations and required verification: one build pipeline produces multiple platform artifacts, but each still goes through its own store's release and rollback rules. Verify the current supported platforms and per-store deployment steps at [Flutter supported platforms](https://docs.flutter.dev/reference/supported-platforms), [Flutter iOS deployment](https://docs.flutter.dev/deployment/ios), and [Flutter Android deployment](https://docs.flutter.dev/deployment/android), plus the Apple and Google sources named in the native patterns, on the PRD date.

## React Native / Expo Pattern

Use for a single cross-platform codebase targeting iOS and Android from JavaScript/TypeScript, especially when sharing logic with an existing React web codebase. React Native's own documentation recommends building a new app with a Framework, and Expo is the recommended one — see `mobile-stack-selection.md` for choosing this over Flutter or native, and for the Expo-vs-bare workflow decision.

- Toolchain: one JavaScript/TypeScript codebase, npm/yarn/pnpm dependencies, and React Native's native platform components. Expo (the managed workflow, scaffolded with `create-expo-app`) is the default toolchain: it provides file-based routing, a standard library of native modules, and the EAS cloud services below. Choose bare React Native (full native iOS/Android projects, reached via prebuild or ejection) only when a native module needs native-project access Expo's managed workflow and config plugins cannot provide, and record which module forced it.
- Targets: React Native compiles to native iOS and Android apps. The same codebase can optionally target the web (React Native for Web) and Windows/macOS — confirm current support and per-target limitations live before promising a target beyond iOS/Android.
- Client architecture: navigation (commonly React Navigation or Expo Router), local persistence (SQLite, or a wrapper such as AsyncStorage/MMKV for key-value), local and shared state, offline behavior, permissions, deep links, and device capabilities reached through native modules.
- Distribution: because it produces native apps, React Native does not bypass either store. An iOS+Android product still needs BOTH an Apple path (Apple Developer Program, code signing, TestFlight, App Store review) exactly as in the Native iOS Pattern AND a Google path (Play Console, testing tracks, Play App Signing, target-API rules) exactly as in the Native Android Pattern. Budget for both memberships and both review processes. EAS Build compiles and signs both platforms in the cloud (removing the local-Mac-for-iOS-builds requirement); EAS Submit uploads builds to the App Store and Play Store from the cloud, the automation role fastlane plays in the native patterns; manual App Store Connect / Play Console upload remains the alternative to EAS Submit.
- Over-the-air updates: EAS Update ships JavaScript and asset changes over-the-air without an app-store review cycle. Native code changes (new native modules, native config) always require a new store-reviewed build. Record which change types are OTA-eligible and which are not.
- Backend, data, and security: follow the same concerns as the native patterns (sync API, auth sessions, push via APNs on iOS and FCM on Android, secure storage via the platform Keychain/Keystore through a native module, local cache versus remote canonical records, conflict resolution). A native module may differ per platform — record which platforms each supports.
- Operations and required verification: one build pipeline (EAS or self-hosted CI) produces both platform artifacts, but each still goes through its own store's release and rollback rules (a new build or staged rollout, not a silent un-ship). Do not copy an Expo SDK version, EAS build tier/pricing, or supported-OS range from memory. Verify current tooling at [React Native: Get Started](https://reactnative.dev/docs/environment-setup), [Expo docs](https://docs.expo.dev/), [EAS Build](https://docs.expo.dev/build/introduction/), [EAS Submit](https://docs.expo.dev/submit/introduction/), and [EAS Update](https://docs.expo.dev/eas-update/introduction/), plus the Apple and Google sources named in the native patterns, on the PRD date.

## Desktop App Pattern

Use for an installable desktop application on macOS, Windows, or both.

- macOS toolchain and distribution: build with SwiftUI or AppKit (or a cross-platform toolkit, see below). Apps are code-signed with a Developer ID certificate; apps distributed outside the Mac App Store must also be notarized by Apple (submitted with `notarytool`) so Gatekeeper runs them without an "unidentified developer" warning. Distribution is either direct download (Developer ID, signed and notarized) or the Mac App Store (sandboxing required). Verify current signing and notarization requirements at [notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) and [macOS distribution](https://developer.apple.com/macos/distribution/) on the PRD date.
- Windows toolchain and distribution: build with WinUI or .NET (WPF or WinForms), or a cross-platform toolkit. Package as MSIX (the modern Windows package format; MSIX packages must be signed) or a traditional installer. Distribute by direct download or the Microsoft Store; the Store re-signs MSIX submissions, while direct download needs a certificate that chains to a trusted root. Verify current packaging, signing, and distribution options at [MSIX overview](https://learn.microsoft.com/en-us/windows/msix/overview), [signing an MSIX package](https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview), and [choose a distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path) on the PRD date.
- Cross-platform desktop alternative: when one codebase should target both macOS and Windows (and often Linux), consider Tauri (a web frontend over the OS-native webview with a Rust backend, small binaries) or Electron (bundles Chromium and Node.js, larger binaries but a full browser runtime). A cross-platform build still has to satisfy each OS's own signing and distribution rules above — the framework does not remove macOS notarization or Windows signing. Verify current platform support at [Tauri](https://tauri.app/) and [Electron](https://www.electronjs.org/) on the PRD date.
- Client architecture: window and view structure, local persistence and file handling, offline-first behavior (desktop apps typically run without a network), auto-update mechanism, OS integration (menu bar, tray, notifications, file associations), and permissions.
- Backend and data: many desktop apps are local-first with optional sync; when a backend exists, resolve its hosting separately, and specify sync, conflict resolution, and auth-session handling.
- Security: OS keychain/credential store for secrets, code-signing integrity, update-channel integrity (signed updates), and PII minimization.
- Operations and required verification: signed auto-update delivery, per-OS minimum-version support, crash reporting, and staged rollout where the update framework supports it. Rollback means shipping a prior signed version through the same update channel. Record the verification date and the official sources above on `stack-decisions.md`'s `Compatibility checked on:` line; signing, distribution, and rollout stay in `architecture.md`.

## Browser Extension Pattern

Use for a browser extension. Chrome with Manifest V3 is the default target today; Firefox and Safari are explicit alternatives, each with its own store and API differences.

- Toolchain: TypeScript plus an extension-aware bundler such as Vite with CRXJS or WXT, so the manifest, content scripts, service worker, and extension pages build from one tool (see `frontend-stack-selection.md`).
- Client architecture: a `manifest.json` (V3) declares the entry points. A service worker is the event-driven background context — there is no persistent background page. Content scripts run inside web pages with only partial extension-API access; extension pages (popup, options, side panel) are ordinary HTML/TypeScript documents with full API access. Assign each workflow to the context that owns it and define how contexts communicate (`chrome.runtime` messaging, long-lived ports, or storage events).
- Permissions model: declare the narrowest host and API permissions that work. `host_permissions` drive install-time warnings and store review; use optional permissions with runtime requests where the UX allows.
- Backend and data: `chrome.storage` for settings and local state. When sync, accounts, or shared data need a companion backend, resolve its hosting separately like any other server surface, and define the requests the extension may make and how its auth tokens are stored.
- Distribution: the release path is the Chrome Web Store developer dashboard (one-time registration fee — confirm the current amount live), store review before publication, versioned uploads, and staged rollouts; the browser itself delivers updates. Firefox (addons.mozilla.org) and Safari (App Store as a Safari Web Extension) each need their own listing and review when targeted. Record each store destination in `architecture.md`'s provider-neutral `## Release Targets`, like a native store target; the hosted two-row environment table does not apply.
- Operations and required verification: extension version pinning by the store, review turnaround for each update, and a forward-fix through the same store review rather than instant rollback. Verify current manifest requirements, permission policy, fees, and store rules at [Chrome Extensions docs](https://developer.chrome.com/docs/extensions/) and [Chrome Web Store](https://developer.chrome.com/docs/webstore/) on the PRD date; do not copy limits, review timing, or fees from memory.

## Internal Tool Pattern

Use for admin panels, operations consoles, review queues, workflow tools, and back-office systems.

- Frontend: dense table views, filters, search, bulk actions, detail panels, audit trails, keyboard efficiency where useful.
- Backend: permissioned admin endpoints, approval workflows, import/export, background processing, audit logging.
- Data: operational records, user actions, review status, assignment, SLA timestamps, immutable audit entries.
- APIs: guarded mutations, bulk operation contracts, validation summaries, idempotency keys for destructive or repeat actions.
- Security: least-privilege roles, approval gates, PII masking, access review, comprehensive audit logs.
- Operations: queue visibility, retry tools, manual override policies, incident playbooks.

## Automation and Agent Workflow Pattern

Use for scheduled automations, event-triggered workflows, AI agents, data pipelines, and integration tools.

- Triggers: schedule, webhook, email, file drop, database change, manual run, or user command.
- Orchestration: workflow steps, state machine, queue, retry policy, timeout, cancellation, and human approval points.
- Tools and integrations: source system, destination system, auth method, scopes, rate limits, quotas, and sandbox behavior.
- Data: run records, step logs, input snapshots, generated outputs, idempotency keys, deduplication, and replay support.
- Safety: permission boundaries, dry-run mode, confirmation gates, prompt injection defenses for AI workflows, output validation.
- Failure handling: partial success, retryable and non-retryable errors, dead-letter queue, alerting, resume, rollback or compensating actions.
- Observability: run history, step-level logs, latency, success rate, cost, token or API usage, integration error rates.

## API or Backend Service Pattern

Use when the product is mainly a service consumed by other systems.

- Interfaces: endpoints, events, SDK boundaries, authentication, versioning, rate limits, and error taxonomy.
- Domain services: validation, authorization, business rules, consistency boundaries, transaction design.
- Data: canonical entities, migrations, indexing, archival, retention, encryption, and backup.
- Operations: SLOs, capacity, autoscaling, deploy strategy, backward compatibility, observability, and incident response.

## Decision Guidance

- Prefer the simplest architecture that satisfies the stated workflows and constraints.
- Call out tradeoffs when choosing between synchronous requests, background jobs, event-driven design, or scheduled processing.
- Specify idempotency for payment, notification, import, workflow, and external mutation flows.
- Keep monetization infrastructure separate from partner distribution. Pricing makes both gates applicable but does not automatically select RevenueCat; affiliate, referral, and reseller motions keep distinct attribution, customer-ownership, commission/discount, payout, provisioning, and support contracts.
- Specify authorization at both UI and backend layers.
- For a browser frontend, backend, persistent data, or auth requirement, name the required/selected stack or a recommended stack when requirements support a decision; do not leave the implementer to reinterpret a flat list of tools or present a recommendation as user-approved.
- Treat platform, rendering, framework, UI library, and build tooling as separate decisions. For example, `Cloudflare Workers + React + Vite` is a coherent stack; `Cloudflare vs Astro vs Vite vs React` is not a coherent comparison.
- For Cloudflare delivery, name separate development and production Workers even though both use the same codebase. Define isolated bindings, secrets, data, auth, and payment modes plus the exact candidate-run-branch-to-`main` promotion path.
- Keep stable provider-neutral release target IDs above provider-specific commands. A successful publish command, upload, submission, or review is not availability without audience access and smoke evidence.
- For native mobile and desktop channels, distinguish rollout halt/removal from rollback and require a signed forward-fix when installed clients cannot be reverted.
- Avoid naming other vendors unless the user specified one, the current environment requires it, or a documented tradeoff makes the recommendation materially more useful.
