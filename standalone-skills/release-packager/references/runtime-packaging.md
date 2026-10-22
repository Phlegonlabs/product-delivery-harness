# Runtime Packaging

Use the component's existing tools and supported targets. The commands below illustrate native routes; resolve actual component paths, tool versions and output names before execution. References checked on 2026-10-04. Consult the installed tool's help and current official documentation when behavior or flags differ.

## Node And Bun

Inspect the exact package's `package.json`: name/version, license, `files`, `exports` or `main`, `types`, `bin`, runtime engines, dependencies and existing `publishConfig`. Use the component's lockfile and build command. A `private: true` package may still produce a local archive but cannot be reported as publishable to npm; preserve that setting. A private workspace root is not the public package.

Review `prepare`, `prepack`, `postpack` and install/publish hooks before packaging. `npm pack --dry-run --ignore-scripts --json` can inspect the selected file list without hooks, but it does not run a required build or prove that an actual package works. Execute the reviewed build first, then create a real archive with `npm pack --json --pack-destination <fresh-output-directory>`; retain hook evidence or use `--ignore-scripts` only when the required built payload is already present.

Inspect the tarball for all exports, declarations, bin files, dynamic assets, README and license. Install that exact tarball into an isolated consumer, then import/use the package or run its installed CLI. A test that resolves a workspace symlink does not validate the archive. If install hooks are suppressed for safety, record that limitation and run required hooks only within the task's authorized environment. Match the project's ESM/CJS and runtime requirements.

Bun-managed packages may use their existing npm-compatible archive route or `bun pm pack` after checking installed-version support. `bun publish --dry-run` is an optional publication preview, not a substitute for packing/installing real bytes; review its hooks and flags first. Do not execute bare publish to create an archive.

For an existing Bun executable route, `bun build --compile` creates a different artifact from a registry package. Use the project's selected target and bundled-asset behavior. Run the final binary on a matching OS/architecture; cross-compilation alone is not runtime verification.

Sources: [npm pack](https://docs.npmjs.com/cli/commands/npm-pack), [npm scripts](https://docs.npmjs.com/cli/using-npm/scripts), [package.json](https://docs.npmjs.com/cli/configuring-npm/package-json), [Bun package manager](https://bun.com/docs/pm/cli/pm), [Bun publish](https://bun.com/docs/pm/cli/publish), [Bun executables](https://bun.com/docs/bundler/executables).

## Python

Read `pyproject.toml`, the existing build backend, version source, runtime dependencies and package-data rules. Use the existing locked environment; do not switch backend or introduce legacy setup commands as a repair shortcut.

The native route `python -m build` produces an sdist and builds a wheel from it, catching omissions in source-distribution inputs. Inspect both archives, metadata, runtime files, package data and license. Use the project's metadata checker, such as `python -m twine check --strict <artifacts>`, when available. A metadata check does not prove installation or imports.

In an isolated compatible environment, install the actual wheel and exercise imports/CLI without the source directory on the import path. Also build/install from the sdist when it is a selected distribution: a working wheel does not prove consumers can build the source archive. Check Python/platform/ABI tags and declared compatibility. Missing backend, compiler or matching interpreter remains a gap; do not silently skip native-extension verification.

Sources: [packaging flow](https://packaging.python.org/en/latest/flow/), [build](https://build.pypa.io/en/stable/), [packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/), [wheel format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/), [Twine check](https://twine.readthedocs.io/en/stable/).

## Go And Rust

For Go, read `go.mod`, `go.sum`, main packages, native/cgo dependencies and the existing release target/version flags. Run applicable tests and module verification, then use the selected `GOOS`/`GOARCH` with `go build`. Set version metadata through the project's existing mechanism; a local module build does not automatically embed the intended release version. Inspect build settings with `go version -m <binary>` and check the application's own version output on a matching runner.

For Rust, select the intended Cargo workspace package and preserve its lockfile policy. A library's registry artifact is a `.crate`: inspect `cargo package --list`, then `cargo package` and the actual archive. The normal package command also verifies by building the extracted crate. Do not hide failures using `--no-verify` or unrelated dirty work using `--allow-dirty`. Use an isolated consumer for public API/dependency checks when they are part of the release contract. A separately authorized publication preview can use `cargo publish --dry-run`.

A Rust CLI's downloadable artifact comes from the existing `cargo build --release` target route; a `.crate` is not its prebuilt executable. For Go/Rust binaries, package required assets/licenses and applicable platform libraries alongside the executable. Record each OS/architecture or target triple separately. Run the unpacked CLI's version and one useful bounded command on the corresponding runner, not just from the build directory.

Sources: [Go command](https://go.dev/cmd/go/), [Go modules](https://go.dev/ref/mod/), [cargo package](https://doc.rust-lang.org/cargo/commands/cargo-package.html), [cargo build](https://doc.rust-lang.org/cargo/commands/cargo-build.html), [cargo publish](https://doc.rust-lang.org/cargo/commands/cargo-publish.html).

## Containers

Read the selected Dockerfile, context, `.dockerignore`, existing base-image pinning and build/platform settings. Reuse the chosen builder and output format. Review build steps because they execute code and may fetch dependencies. Use the existing BuildKit secret mechanism when required; never embed credentials in build arguments, environment layers or copied files.

For a local image, inspect architecture/OS, labels, entrypoint and image ID. Run the selected startup/health check in an authorized temporary container, with a finite lifetime and task-owned cleanup; do not mount production data or collide with existing ports. Each promised architecture needs its own usable runner or recorded verification gap.

If offline download is a selected channel, export the actual image with `docker image save -o <fresh-archive> <exact-local-image>` or the project's existing OCI exporter, then test loading/running it in an isolated matching environment. Otherwise retain the prepared image/output identity for the selected registry route; do not add an unnecessary archive.

A local image ID is not a published registry digest. After an authorized push, read back the remote manifest digest and, for a multi-platform image, its per-platform digests. Keep those separate from the checksum of any exported file.

Sources: [Docker build](https://docs.docker.com/reference/cli/docker/buildx/build/), [image inspect](https://docs.docker.com/reference/cli/docker/image/inspect/), [image save](https://docs.docker.com/reference/cli/docker/image/save/), [remote manifest inspection](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/), [build secrets](https://docs.docker.com/build/building/secrets/).

## Desktop And Mobile Apps

Use the existing framework/platform project, configuration, package format, version fields and signing route. Identify development, unsigned, signed/exported and store-uploaded states separately. A missing platform environment, certificate or signing authorization blocks only the dependent step; do not weaken the target matrix.

| Target | Existing native route | Artifact verification |
| --- | --- | --- |
| Android | Project-defined Gradle release variant produces APK/AAB | Inspect version, ABI and payload; verify APK with `apksigner verify`. Check an AAB with the selected bundletool/signature route, then test install/start on a compatible device/emulator when authorized. |
| iOS/iPadOS | Existing Xcode archive and export scheme/options | An `.xcarchive` is not an exported IPA. Inspect the exported app's version, provisioning/signature and device support; use the existing installation/test route on an eligible device. |
| macOS | Existing Xcode/framework archive, app/DMG/PKG route | Verify actual signature with `codesign --verify --deep --strict` as applicable and inspect signer metadata separately. Gatekeeper/notarization checks follow the distribution contract. Hash after final signing/stapling. |
| Windows | Existing framework/MSBuild/MSIX/installer route | Inspect package version, payload and architecture; verify applicable signatures with `signtool verify /pa /all`. Test the actual installer/app in an authorized isolated Windows environment. |
| Linux | Selected deb/rpm/AppImage/Flatpak or project format | Use that format's metadata/payload/signature checker, then test installation/start on a matching environment. No single checker establishes readiness for all Linux formats. |

Signing, notarization, timestamping, store submission and deployment can have different local/external authorization requirements. Reuse existing grants; never infer them from a successful build. Reuse framework-owned packaging rather than invent another installer.

Sources: [Android builds](https://developer.android.com/build/building-cmdline), [Android signatures](https://developer.android.com/studio/command-line/apksigner), [Xcode distribution](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-release), [Apple notarization](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution), [SignTool verification](https://learn.microsoft.com/en-us/windows/win32/seccrypto/using-signtool-to-verify-a-file-signature).
