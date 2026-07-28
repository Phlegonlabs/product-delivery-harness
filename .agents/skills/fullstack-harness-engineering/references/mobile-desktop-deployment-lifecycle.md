# Mobile / Desktop Deployment Lifecycle

Use this reference when a deployable app targets native iOS, native Android, Flutter (which still distributes through both native paths), macOS, or Windows. It is the mobile/desktop parallel to `cloudflare-deployment-lifecycle.md`. Read that file for the web/Worker model; this file exists because the store/signed-installer model is genuinely different.

The one difference to internalize first: **there is no instant redeploy or instant rollback here.** A Cloudflare Worker promotes a new version in seconds and can roll back to a prior version id just as fast. Every platform below ships a signed artifact through a store or an update channel, most involve review or notarization latency, and "rollback" means shipping another build or halting/adjusting a staged rollout — not flipping to a previous version instantly. State this to the user plainly whenever they expect web-style rollback.

Every native release plan declares a `production` target for the public channel. Add a `development` promotion target only when the repository actually uses a separate beta, testing, or preview channel:

```text
verified build -> optional development target (beta/testing) -> tester/QA verification
approved build -> required production target (public channel) -> availability + smoke
```

`development` and `production` here are promotion stages. Current PLAN-v5 uses the same provider-neutral target shape for every platform; it has no provider discriminator or provider-specific fallback object. Put platform identity in prerequisites and retained evidence, and keep target fields limited to the exact PLAN-v5 contract.

## Prerequisite and Signing Bootstrap

These are one-time (or account-level) prerequisites, not part of every release attempt — the analog of Cloudflare's "Wrangler Config and Account Bootstrap". Confirm the relevant gate below **before attempting any submission or distribution**, and stop and tell the user exactly what is missing if it is not in place. Never store certificate files, private keys, App Store Connect API keys, keystore passwords, or provisioning profiles in PLAN, RUN, or any committed file; direct the user to configure them in the platform's own store/keychain/secret manager or CI secret store.

- **iOS / macOS.** Verify an active Apple Developer Program membership and that signing is configured: a valid signing certificate plus, for iOS, a provisioning profile matching the bundle identifier and distribution method; for macOS direct distribution, a Developer ID Application certificate. Verify the notarization credential for macOS (an App Store Connect API key or app-specific password usable by `notarytool`). Do not attempt a TestFlight/App Store/notarized build without these.
- **Android.** Verify a Google Play Console developer account and that app signing is set up. Play App Signing holds the app signing key; you sign uploads with an upload key. Confirm the upload keystore (or the CI signing config) is available before attempting any track upload.
- **Windows.** Verify a code signing certificate for the distribution path in use: Microsoft Store submission re-signs MSIX/AppX packages with a Microsoft certificate so you do not need a CA-trusted cert for that path, but an MSI/EXE installer submitted to the Store, or any MSIX distributed outside the Store via an `.appinstaller` auto-update feed, must be Authenticode-signed with your own CA-trusted certificate. Confirm which path applies and that its cert is in place.

If the gate cannot be confirmed, stop — do not attempt the build/submission — and tell the user exactly what to configure (enroll in the program, install the certificate, set up Play App Signing, configure the CI signing secret). Never ask the user to paste a key or password into chat.

## Required Verification Before Distribution

A successful build or a successful store upload is not the PASS signal. Before any distribution, run the toolchain's tests and a release-config build (see `references/platform-archetypes.md`, "Required verification per toolchain"): `xcodebuild test` for iOS/macOS, `./gradlew test` plus `./gradlew connectedAndroidTest` for Android, `flutter test` plus `flutter test integration_test/` for Flutter, `dotnet test` for Windows. Retain the build identifier (build number / versionCode / package version), the signed artifact reference, and the source SHA. When the repository declares the optional development target, also retain its tester/QA evidence and require that signoff before production promotion.

## iOS (and Flutter's iOS path)

- **Development target — TestFlight.** Upload a signed build to App Store Connect and distribute via TestFlight. Internal testers (up to 100 App Store Connect users) can install builds without App Review; each build is available to internal testers for 90 days. External testers (up to 10,000) require TestFlight App Review, but only the first build of an app sent to a group triggers a full review; subsequent builds usually do not. Up to six builds can be submitted for TestFlight App Review per 24 hours.
- **Production target — App Store.** Submit the build for App Review. On approval it becomes available on the App Store. Use phased release to roll a new version out to a percentage of users automatically over several days.
- **Automation options.** App Store Connect API, Xcode Cloud, or fastlane can automate build upload, TestFlight distribution, and submission. Use whichever the project already has; do not invent credentials.
- **Rollback reality.** There is no instant rollback like a Worker redeploy. You cannot un-ship an approved App Store version to existing installs. The real mechanisms are: pause an in-progress phased release, remove the version from sale, or submit a fixed build (optionally requesting expedited review). Note this explicitly to the user — a broken iOS production release is not a one-command revert.

## Android (and Flutter's Android path)

- **Development target — testing tracks.** Play Console has internal, closed, and open testing tracks. Internal testing distributes a new App Bundle to testers within minutes and is the fastest beta path; closed testing uses email/tester lists (up to 200 lists, up to 2,000 testers each); open testing exposes the test version broadly on Google Play. You can run multiple closed tests and one open test at a time.
- **Production target.** The production track releases to all users. Releases to production and to test tracks can use a **staged rollout**: the update reaches only a percentage of users, which you increase over time.
- **App signing.** Play App Signing manages the app signing key; you upload builds signed with your upload key and Google re-signs with the app signing key.
- **Rollback reality.** Closest thing to rollback: **halt a staged rollout** to stop it reaching more users, then either resume after a fix or release a new (higher versionCode) build. You cannot lower the versionCode or restore a previous APK to users who already updated; recovery is a new build through the same track. State this rather than implying instant revert.

## macOS

- **Notarization is required for direct distribution.** Gatekeeper checks Developer ID-signed apps distributed outside the Mac App Store. Sign with a Developer ID Application certificate, then notarize with `xcrun notarytool` and staple the ticket with `xcrun stapler`. Notarization is an automated malware/code-signing scan, not App Review, and returns quickly. `altool` is no longer accepted for notary uploads — use `notarytool` (Xcode 14+).
- **Two distribution paths.** Developer ID + notarization for direct (website/DMG/PKG) distribution, or the Mac App Store for store discovery and managed updates. Choose one per build; they use different certificates.
- **Rollback reality.** No instant rollback. For direct distribution, ship a new signed+notarized build through your update channel. For the Mac App Store, submit a fixed build (expedited review if warranted). Note the absence of a web-style revert.

## Windows

- **Code signing.** See the bootstrap gate: Store submissions of MSIX/AppX are re-signed by Microsoft (no CA cert needed for that path); MSI/EXE installers submitted to the Store, and any MSIX distributed outside the Store, must be Authenticode-signed by you.
- **Distribution paths.** (1) Microsoft Store — MSIX/AppX packaging, Store handles signing and update delivery. (2) Direct distribution — an MSIX with an `.appinstaller` file for auto-update (requires a CA-trusted code signing cert), or a traditional installer (MSI/EXE) with its own auto-update mechanism (for example Squirrel or a custom updater).
- **Rollback reality.** Rollback means publishing a previous version through whichever channel is in use — a prior package version to the Store, or a prior version to the `.appinstaller` / installer update feed. There is no instant server-side revert of installed clients; clients recover on their next update check. State this explicitly.

## Release Isolation

When the repository declares both stages, keep development and production builds isolated the same way the Cloudflare model keeps environments isolated. Development/beta builds should use non-production backends, sandbox in-app purchase, test push credentials, and debug entitlements; production builds use live backends, production purchase, production push, and release entitlements. Do not let a TestFlight/internal-track build point at production data or live payments by default. Bundle/application identifiers, push certificates, and backend endpoints stay per-stage.

## Verification and Failure Rules

- Retain the build identifier, signed-artifact reference, source SHA, test evidence, and tester/QA or store-review status. A successful upload alone is not a development or production PASS.
- Stop promotion to production when the release-config build fails, or when a declared development target's tests or tester/QA verification fail.
- Do not mark production PASS on upload success alone — production PASS requires the build actually available through the store/channel and its smoke/acceptance check passing.
- Because there is no instant rollback, treat a broken production release as forward-fix work: halt the rollout/phased release where possible and prepare a corrected signed build. Do not claim a rollback the platform cannot perform.

Recheck current official documentation before using fast-moving submission requirements, review-timing, packaging, or signing details (verified 2026-07-22):

- https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/
- https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers/
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/developer-id/
- https://support.google.com/googleplay/android-developer/answer/9845334
- https://support.google.com/googleplay/android-developer/answer/6346149
- https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview
- https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements
- https://learn.microsoft.com/en-us/windows/msix/app-installer/auto-update-and-repair--overview
