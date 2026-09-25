# Mobile Stack Selection

Use this guide for every PRD package whose product surface includes a mobile app. First resolve the target operating systems, then compare native and cross-platform implementation strategies, and finally obtain owner acceptance for one coherent client stack. A mobile app's release path is an app store or signed build, not the web deployment-platform question; its backend resolves hosting separately.

Label the decision status accurately:

- `Required`: mandated by the user, organization, or hard external constraint.
- `Selected`: already adopted by the current product or repository.
- `Approved`: accepted by the human owner for this package, directly or through an explicit recorded delegation.
- `Recommended`: the PRD's evidence-backed proposal; not yet owner-approved and not executable.
- `Provisional`: the leading choice pending named evidence or a spike.

Assign status per layer; one section may mix statuses. Every layer row also cites its authority/evidence: a dated user statement, organization policy, repository/config path, product requirement IDs, official documentation with check date, or named spike. Authority is the cited source, not a status label, and `PRD recommendation` alone is not evidence.

## App And Companion Web Contract

**React Native + Expo is a reference option, not a required or default stack for App + Web products.** Compare suitable native and cross-platform approaches from the product's needs using the selection procedure below. Mentioning a framework as an example does not make it `Required` or `Approved`. Preserve an existing `Selected` or `Approved` stack and reuse an explicit owner mandate only when one actually exists. Keep target platforms, framework, toolchain and Web implementation decisions separate.

A product may ship its apps and public showcase website together. Keep one PRD, architecture and stack-decision package. During discovery, resolve whether the web scope is a public showcase, an authenticated web application, both, or neither. Do not add a website merely because an app exists. Record included, deferred and excluded surfaces in the existing Product Archetype/scope sections, and bind included surfaces to architecture Release Targets:

| Surface | Role | Surface class / capture mode | Review obligations |
| --- | --- | --- | --- |
| iOS app | Native product journeys | `ios` / `native` | Named smaller/larger supported phone targets; iPad only when scoped |
| Android app | Native product journeys | `android` / `native` | Named smaller/larger supported phone targets; tablets/foldables only when scoped |
| Public showcase web | Explain the product and support discovery or acquisition | `hosted_web` / `hosted-browser` | 390, 768, 1024 and 1440 px by default |
| Authenticated web app or admin | Browser product/operator journeys, only when required | `hosted_web` / `hosted-browser` | Its own approved routes, states and responsive contract |

Each included platform gets distinct release-surface IDs and its own `UI-*` bindings, even when the apps share source code. Native entries use at least two ordered named `sizeClasses` with supported device/orientation obligations; UI authoring binds each name to an explicit review-canvas width. Web entries use numeric `viewports`. Existing approved responsive sets remain authoritative. Do not apply the four web widths to native screens or imply that a second phone size includes tablet support.

The PRD records platform-specific requirements for safe areas, keyboard avoidance, system text scaling (including iOS Dynamic Type and Android font scaling), screen readers, back/navigation behavior, permissions, deep links and offline/recovery states. State non-applicability where appropriate. Showcase scope names the actual required pages, content sources, SEO/indexing, accessibility and acquisition destinations; store links must have defined pre-release and platform-unavailable behavior. A showcase does not acquire login, checkout or app feature parity by implication.

In architecture and stack decisions, state what is shared: API contracts, validation, domain logic, data ownership and approved design principles. Also state what differs: native versus browser navigation/components, secure storage/session handling, permissions and platform integrations. Explicitly choose shared cross-platform Web code or a separate Web frontend from the Web requirements. Expo Web is one reference when Expo is selected for mobile; no mobile choice settles the website framework, hosting, rendering or SEO strategy. Record shared-backend compatibility, auth callback/deep-link boundaries and failure recovery when a journey crosses surfaces. Monetization and entitlement rules still follow the existing commercial gates when applicable.

Define separate iOS, Android and web build/release targets, identifiers, environments, distribution, availability signals and rollback paths. Choose build/distribution tools for the selected stack. For the Expo reference option, EAS Build/Submit/Update and local/other CI remain explicit choices; Expo does not require a paid EAS service. Native-library/config changes require compatible native builds. OTA use records runtime compatibility and applicable store-policy constraints rather than promising every change can ship without review. Expo Go or an HTML preview is not production-native acceptance evidence: require platform builds and per-platform test obligations, plus browser checks for web. These fields belong in existing PRD `TEST-*` rows and architecture testing/release sections, not a second specification.

Official references checked 2026-09-24: [Expo development workflow](https://docs.expo.dev/workflow/overview/), [Expo web](https://docs.expo.dev/workflow/web/), and [React Native setup](https://reactnative.dev/docs/environment-setup). Recheck current SDK support and service/store constraints when drafting a product.

## First Separate the Layers

Never compare `native iOS vs Flutter vs React Native vs Expo` as though they sit at the same level. Target operating systems, code-sharing strategy, framework, and toolchain are nested decisions, not one flat menu.

| Layer | Question | Examples |
| --- | --- | --- |
| Target operating systems | Which destinations ship in v1? | iOS, Android, both; later targets explicitly deferred |
| Cross-platform vs native | One shared codebase across platforms, or a separate native codebase per platform? | Cross-platform (Flutter, React Native) or native (Swift/SwiftUI for iOS, Kotlin/Jetpack Compose for Android) |
| Cross-platform framework | If cross-platform, which framework owns the UI and app model? | Flutter (Dart codebase, its own rendering engine) or React Native (JavaScript/TypeScript, native platform components) |
| React Native workflow / toolchain | If React Native, how is the app built, signed, and shipped? | Expo (managed workflow, `create-expo-app`, EAS Build/Submit/Update) or bare React Native (full native iOS/Android projects, ejection/prebuild for native modules) |
| Supporting choices | How are client concerns implemented? | Navigation, local persistence, state, offline/sync, secure storage, push, native-module boundaries, tests |

Expo is a workflow and toolchain *within* React Native, not a separate framework competing with it — the same way Astro-vs-bare-Vite is a choice within the web frontend layer model, not a rival to it. React Native's own documentation calls Expo "a production-grade React Native Framework" and recommends starting a new React Native app with it. Treat "React Native" and "Expo" as two layers of one decision, never as two peers on a shortlist.

## Collect Decision Evidence

Score or describe these inputs before selecting a stack:

1. Existing web/product stack and its language: an existing React/TypeScript web app is a first-class input, because a React Native client can share business logic, hooks, validation, and API clients with that codebase in a way Flutter's separate Dart codebase cannot. Record what already exists and how much is reusable.
2. Team skills and appetite: current JavaScript/TypeScript strength versus willingness to learn Dart, or Swift and Kotlin for a native path.
3. Native-capability and performance needs: heavy custom animation, AR/camera, audio/video processing, Bluetooth/peripheral access, background processing, or exact day-one access to a specific platform API.
4. Build-infrastructure ownership: EAS Build compiles and signs iOS and Android in the cloud and removes the local-Mac-for-iOS-builds requirement; bare React Native and native both still need Xcode/Android Studio locally or a CI Mac runner for iOS.
5. Over-the-air / instant-update needs: EAS Update ships JavaScript and asset changes over-the-air without an app-store review cycle; native code changes and bare-native releases always go through a store review.
6. Target surface beyond phones: React Native can additionally target the web (React Native for Web) and Windows/macOS; Flutter has its own web, desktop (Windows/macOS/Linux), and embedded targets. Record which extra surfaces are actually in scope for v1 versus later.
7. Store and distribution obligations: both stores' developer-program requirements apply regardless of framework (see `architecture-playbook.md`'s native patterns). A cross-platform framework does not bypass either store.
8. Timeline and delivery: launch date, number of platforms at launch, review-cycle tolerance, and whether one team ships both platforms.
9. Ownership: Stack Decision Mode, decision owner, store-account/signing ownership, build-service cost, license limits, vendor lock-in, and who maintains native modules.

Do not let one factor decide by itself. A team with deep React skills may still choose native when a single hard platform-capability or performance requirement dominates the product.

## Product-Fit Patterns

Use these as starting hypotheses, then validate them against the decision evidence. These rows recommend the framework/workflow layer only; the store-distribution obligations in `architecture-playbook.md`'s native, Flutter, and React Native/Expo patterns still apply to whichever choice wins.

| Product shape | Starting recommendation | Why | Watch-outs |
| --- | --- | --- | --- |
| Team already has a full-stack web app in React/TypeScript, now adding a mobile client | React Native via Expo (managed workflow, EAS Build/Submit/Update) | Shares business logic, hooks, and API clients with the existing React codebase; team already knows JS/TS; EAS Build/Submit removes most native-tooling burden and the local-Mac-for-iOS requirement | Confirm which native modules (if any) force bare React Native / a config plugin; verify current Expo SDK, EAS tiers, and OTA-update policy live |
| Same team, weighing Flutter instead | Flutter, only if pixel-consistent cross-platform rendering outweighs code reuse | Flutter's own rendering engine gives more consistent cross-platform visuals, but it is a fresh Dart codebase with no reuse of the existing React logic | Budget for the team learning Dart and maintaining a second language; no shared code with the web app |
| Same team, weighing native instead | Native iOS (Swift/SwiftUI) and native Android (Kotlin/Jetpack Compose), only if platform fidelity/performance or day-one API access dominates | Best performance and platform fidelity and full access to every platform API on day one | Two fully separate codebases with zero code reuse; needs a Mac for iOS regardless; roughly double the client build/maintenance cost |
| No existing web app / mobile-only greenfield team | Decide on team skill and platform-fidelity needs alone: React Native/Expo if the team leans JS/TS, Flutter if it prefers Dart and wants consistent rendering, native if the product is single-platform or capability-heavy | With no web codebase to reuse, the reuse argument is absent, so team skill and fidelity/performance needs lead | Confirm whether both platforms ship at launch; a single-platform launch weakens the cross-platform argument |
| Product needs deep platform-specific capability from day one (heavy AR, low-level audio/video, background processing, exact native API access) | Native, or a cross-platform framework (React Native/Expo or Flutter) with native modules — name the tradeoff explicitly | Native gives unmediated access; cross-platform can reach the same APIs through native modules but adds a bridge layer and per-platform module work | Do not assume a cross-platform framework covers the capability for free; verify a maintained native module exists or budget for writing one, and record which platforms it supports |
| Existing mobile app with a healthy supported stack | Preserve the existing stack unless measured constraints justify migration | Reduces rewrite risk and preserves team velocity | Document the actual limitation and measurable exit criteria before migrating |

React Native's official guidance recommends starting a new React Native app with a Framework (Expo) and treats building without one as a deliberate choice for apps with unusual constraints. Therefore, do not default to bare React Native: choose Expo unless a stated constraint (a native module or build requirement Expo cannot serve) makes the bare workflow the deliberate decision.

## Platform Decision Rules

Verify these rules against current official documentation on the date the PRD is written. Tooling here moves on the vendors' schedule — do not copy an Expo SDK version, EAS pricing/tier, supported-OS range, or Flutter stable-channel number from memory. When you cannot verify a specific number live, write the requirement without the number and mark it as needing live verification rather than asserting a stale figure.

### Any Mobile Target

- Resolve cross-platform vs native first, then the framework, then (for React Native) the Expo-vs-bare workflow. Record each layer's decision status separately.
- Both app stores' developer-program, code-signing, testing-track, and target-API rules apply regardless of framework. A cross-platform codebase does not remove either store's release and rollback discipline — see `architecture-playbook.md`'s Native iOS, Native Android, Flutter, and React Native / Expo patterns.
- A mobile product with a server backend resolves that backend's hosting with `backend-stack-selection.md`; the mobile framework choice does not decide it.

### React Native / Expo

1. Prefer Expo (managed workflow) for a new React Native app unless a specific native module or build requirement Expo cannot serve makes the bare workflow the deliberate choice. Record that reason when choosing bare React Native.
2. Use EAS Build to compile and sign iOS and Android in the cloud when the team wants to avoid owning local iOS build infrastructure; confirm current EAS build tiers and limits live.
3. Use EAS Submit to upload builds to the App Store and Play Store from the cloud, the automation role fastlane plays for native iOS/Android. Manual App Store Connect / Play Console upload remains the alternative.
4. Use EAS Update for over-the-air JavaScript/asset fixes that do not touch native code; native changes still require a new store-reviewed build. Record which change types are OTA-eligible and which are not.
5. When a native module needs full native-project access, use a config plugin or, if necessary, bare React Native / prebuild — and state which native modules forced it.
6. If React Native for Web or Windows/macOS targets are in scope, verify their current support and per-target limitations live rather than assuming parity with iOS/Android.

### Flutter

1. Use Flutter when one Dart codebase should target iOS and Android (and optionally web, desktop, and embedded) and consistent cross-platform rendering outweighs reuse of an existing JS/TS codebase.
2. Reach native-only capabilities through platform channels or a typed generator; record which platforms each plugin actually supports.
3. Confirm the current stable channel, supported per-target OS ranges, and per-store deployment steps live.

### Native iOS and Native Android

Follow `architecture-playbook.md`'s Native iOS Pattern and Native Android Pattern for toolchain, distribution, signing, testing tracks, and target-API rules. Choose native when platform fidelity, performance, or day-one API access dominates, or when the product is effectively single-platform.

## Selection Procedure

1. Resolve target operating systems at launch before discussing implementation frameworks.
2. Classify native-capability needs, performance profile, existing-codebase reuse potential, team skills, signing/build ownership, and distribution constraints.
3. Resolve native versus cross-platform, then the framework, then (for React Native) Expo versus bare, eliminating any option that cannot satisfy a hard constraint or whose current support is unverified.
4. Build two or three coherent client bundles. Each covers target OSs, code strategy, framework/toolchain, navigation, state, local persistence, secure storage, sync, push, native modules, testing, signing/build, cost, and ownership.
5. Recommend one bundle and present its tradeoffs plus serious alternatives under the recorded Stack Decision Mode. Do not hand the implementer an unranked shortlist.
6. For each bundle, state store/developer-program and build-service cost assumptions, license/build-vs-buy and maintenance ownership, compatibility evidence or a time-boxed spike, and the revisit trigger. Keep native typography, navigation, safe areas, keyboard, gestures, accessibility, reduced motion, and haptics decisions distinct from an HTML projection.
7. Mark accepted new choices `Approved`; retain adopted choices as `Selected` and hard constraints as `Required`. Keep unaccepted proposals `Recommended` and non-executable.
8. Verify current Expo/React Native/Flutter and Apple/Google documentation and capture direct sources plus the check date.
9. When evidence is missing, define a time-boxed spike with pass/fail criteria. Until then, label the layer `Provisional` and keep the Stack Decision Checkpoint blocked.

For a frontend or mobile enhancement, inspect the current platform baseline first. Classify its UI impact and preserve unaffected screens and stack. Hand affected UI IDs and constraints to `ui-design-builder` for same-content before/after studies. Do not author visual directions in Product Definition or use HTML screenshots as native verification; retain the representative native first-slice and final full-matrix gates.

## Required Architecture Record

The `Mobile/Desktop Technology Decision` section in `stack-decisions.md` must include (a sibling section template for it lives in `references/output-contract.md`):

- Product evidence and hard constraints, including existing-codebase reuse potential and target operating systems at launch.
- The Stack Decision Mode, human owner, coherent bundles presented, accepted bundle or layer overrides, delegation source when used, and checkpoint decision.
- Selection, status, cited authority/evidence, product-fit reason, and constraint/follow-up on every layer row. Approved packages use `Required`, `Selected`, or `Approved`; `Recommended` and `Provisional` remain draft-only.
- One recorded stack separated by target operating systems, cross-platform-vs-native, framework, React Native workflow when applicable, navigation, local persistence, state, offline/sync, secure storage, push, native-module boundaries, and testing.
- The extra target surfaces (React Native for Web, Windows/macOS, Flutter web/desktop) that are in scope, if any.
- Alternatives and revisit triggers, as rows in the file's shared `Alternatives Considered` table with `[Area]` naming this decision — not a table inside this section.
- Official documentation links and verification date.
- Store distribution obligations per platform: developer-program requirement, code signing, testing track, target-API rules, and push service (APNs / FCM), cross-referenced to the matching `architecture-playbook.md` pattern; and EAS Build/Submit/Update usage when Expo is selected.
- The release and rollback path per store (a new build or staged rollout, not a silent un-ship of an installed version).
- Any provisional layer, as a row in the file's shared `Unresolved Decision Protocol` table with owner, deadline, time-boxed spike, and pass/fail criteria.

## Official Sources to Recheck

Use primary documentation, not marketplace roundups:

- [React Native: Get Started (Frameworks recommendation)](https://reactnative.dev/docs/environment-setup)
- [React Native docs](https://reactnative.dev/)
- [Expo documentation](https://docs.expo.dev/)
- [Expo Application Services (EAS)](https://docs.expo.dev/eas/)
- [EAS Build](https://docs.expo.dev/build/introduction/)
- [EAS Submit](https://docs.expo.dev/submit/introduction/)
- [EAS Update](https://docs.expo.dev/eas-update/introduction/)
- [Flutter documentation](https://docs.flutter.dev/)
- [Flutter supported platforms](https://docs.flutter.dev/reference/supported-platforms)

For native iOS and Android store, signing, testing-track, and target-API sources, use the Apple and Google links cited in `architecture-playbook.md`'s Native iOS Pattern and Native Android Pattern.

## Failure Modes

- A flat `native iOS / Android / Flutter / React Native / Expo` options list with no layer model or recommendation.
- Asking the owner to choose Flutter or React Native before the v1 target operating systems and native-capability constraints are known.
- Treating Expo and React Native as separate competing frameworks instead of Expo being the current recommended way to build React Native apps.
- Assuming bare React Native when Expo would remove unnecessary native-tooling burden, without a stated native-module or build reason not to use Expo.
- Recommending Flutter or React Native for a team with a large existing React web codebase without weighing code/logic reuse against a fresh Dart codebase.
- Recommending native for a JS/TS team without a dominant platform-capability, performance, or single-platform reason that justifies zero code reuse and doubled client cost.
- Assuming a cross-platform framework covers a deep native capability for free instead of confirming a maintained native module exists or budgeting to write one.
- Claiming current Expo SDK, EAS tier, or Flutter support without a date and official source, or copying a version/limit from memory.
- Forgetting that a cross-platform choice still owes both stores' developer-program, signing, testing, and target-API obligations.
- Sending a `Recommended` framework, build service, navigation, persistence, or push choice to implementation without owner acceptance.
- Writing `TBD` without an owner, deadline, experiment, and decision threshold.
