---
name: release-packager
description: Prepare and verify release artifacts for a project's actual runtime and supported platforms, including Node/Bun packages, Python distributions, Go/Rust binaries, containers and native apps. Use during release preparation or when downloadable/installable packages are missing.
---

# Release Packager

Every release task includes preparation and verification of its applicable distribution artifacts. Follow the project's existing build and release contract. npm is one channel, not the default for every project.

## Resolve The Release Unit

Read effective repository instructions, the existing release record, public manifests, lockfiles, build scripts, CI configuration, supported platform matrix and signing requirements. Inspect names before contents; never open credentials to discover packaging settings. Existing action grants apply; ask only for a concrete missing target/channel or action needed to finish the requested scope.

Identify each independently released component in a monorepo. Select its actual runtime, artifact format, version source, supported targets and native packaging command. A private root manifest may contain publishable children; do not make the root public or invent an npm wrapper for another runtime.

Freeze source SHA and relevant scoped working-tree differences before building. Record uncommitted inputs as such; HEAD alone cannot identify those bytes. Reuse the existing release/task record rather than create another specification. A Harness installation is not required.

## Prepare Applicable Artifacts

Read only the applicable sections of [runtime packaging](references/runtime-packaging.md). Build with the native toolchain and existing lockfile/configuration. Review the commands and their lifecycle hooks before running them: a dry-run can still execute scripts, fetch dependencies or contact services.

Use a fresh task-specific output location or an already authorized project location. Preserve old releases, user files and unrelated work. Include required runtime code, assets, metadata, license and installation information; inspect the actual payload rather than trust an allowlist. Keep secrets (see artifact checks), dependency caches and unrelated source outputs out of the distributable.

Support the channels the project has selected. Do not add a registry, installer, platform or CI workflow just because another runtime uses one. Signing, notarization and platform store uploads follow the project's existing route and applicable authorization. Missing tools, runners or signing material are explicit gaps.

## Verify The Built Artifact

Use [artifact checks and delivery](references/artifact-checks.md). Install/extract the final package in an authorized isolated environment and exercise its actual import, CLI or application startup. Do not let the source checkout or a global installation mask missing packaged files. Native dependencies and target architecture need a matching runner.

Verify name/version, entry points, runtime constraints, required payload, platform identity and applicable signatures. Hash final bytes after signing, stapling or repacking. For a container, keep local image ID, exported archive checksum and remote registry digest distinct.

List every selected component/target/channel and its result. A successful build is not an installation, signature or startup PASS. Retain failures and finish independent applicable targets; unavailable required platforms remain unverified.

## Reconcile And Deliver

Reconcile README and release-note facts as described in Reconcile Documentation And Publication in [artifact checks](references/artifact-checks.md). Use `readme-studio` only for presentation work. Do not describe a prepared asset as already available at a public URL.

Return the Delivery Record table with remaining gaps. Publishing uses the existing project's exact authorization and channel, followed by readback of the uploaded artifact/version; it is never inferred from building a package or selecting this skill.

This skill applies when an agent handles a release task. It creates no background monitor, tag hook or automatic CI pipeline by itself.
