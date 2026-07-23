# Mobile Stack Selection

Use this guide for every PRD package whose product surface includes a mobile app. The wider architecture may remain technology-neutral. This guide ensures the mobile client itself records a required/selected choice or turns product evidence into one implementation-ready recommendation, rather than producing a fashionable list of frameworks. A mobile app's release path is an app store or a signed build, not the web deployment-platform question — its backend, if any, resolves its own hosting separately.

Label the decision status accurately:

- `Required`: mandated by the user, organization, or hard external constraint.
- `Selected`: already adopted by the current product or repository.
- `Recommended`: the PRD's evidence-backed advice; not yet user-approved.
- `Provisional`: the leading choice pending named evidence or a spike.

## First Separate the Layers

Never compare `native iOS vs Flutter vs React Native vs Expo` as though they sit at the same level. The choice is a small stack of nested decisions, not one flat menu.

| Layer | Question | Examples |
| --- | --- | --- |
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

1. Classify the product by target platforms at launch, native-capability needs, performance profile, existing-codebase reuse potential, and team skills.
2. Resolve cross-platform vs native, then the framework, then (for React Native) Expo vs bare, eliminating any option that cannot satisfy a hard constraint or whose current support is unverified.
3. Choose the simplest coherent stack that covers the product's platforms and capabilities without unnecessary native-tooling burden or an unused extra language.
4. Name the required/selected stack, or one recommendation when no choice exists. Do not hand the implementer an unranked shortlist, and do not present advice as an approved requirement.
5. Explain at least two serious alternatives, where each would fit better, why it loses here, and what would trigger reconsideration.
6. Verify current Expo/React Native/Flutter and Apple/Google documentation and capture direct sources plus the check date.
7. When evidence is missing, define a time-boxed spike that measures the uncertainty with pass/fail criteria. Until then, label the layer `Provisional`, not `Selected`.

## Required Architecture Record

The `Mobile/Desktop Technology Decision` section in `architecture.md` must include (a sibling section template for it lives in `references/output-contract.md`):

- Product evidence and hard constraints, including existing-codebase reuse potential and target platforms at launch.
- Decision status and authority (`Required`, `Selected`, `Recommended`, or `Provisional`) per layer.
- One recorded stack separated by cross-platform-vs-native, framework (Flutter or React Native), React Native workflow (Expo or bare) when applicable, navigation, local persistence, state, offline/sync, secure storage, push, native-module boundaries, and testing.
- The extra target surfaces (React Native for Web, Windows/macOS, Flutter web/desktop) that are in scope, if any.
- Alternatives and revisit triggers.
- Official documentation links and verification date.
- Store distribution obligations per platform: developer-program requirement, code signing, testing track, target-API rules, and push service (APNs / FCM), cross-referenced to the matching `architecture-playbook.md` pattern; and EAS Build/Submit/Update usage when Expo is selected.
- The release and rollback path per store (a new build or staged rollout, not a silent un-ship of an installed version).
- Owners, deadlines, spikes, and pass/fail criteria for any provisional decision.

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
- Treating Expo and React Native as separate competing frameworks instead of Expo being the current recommended way to build React Native apps.
- Assuming bare React Native when Expo would remove unnecessary native-tooling burden, without a stated native-module or build reason not to use Expo.
- Recommending Flutter or React Native for a team with a large existing React web codebase without weighing code/logic reuse against a fresh Dart codebase.
- Recommending native for a JS/TS team without a dominant platform-capability, performance, or single-platform reason that justifies zero code reuse and doubled client cost.
- Assuming a cross-platform framework covers a deep native capability for free instead of confirming a maintained native module exists or budgeting to write one.
- Claiming current Expo SDK, EAS tier, or Flutter support without a date and official source, or copying a version/limit from memory.
- Forgetting that a cross-platform choice still owes both stores' developer-program, signing, testing, and target-API obligations.
- Writing `TBD` without an owner, deadline, experiment, and decision threshold.
