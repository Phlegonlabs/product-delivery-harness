# Artifact Checks And Delivery

## Inspect Actual Payloads

Retain the native build/pack commands, tool versions, exit codes and final artifact inventory. Inspect archives without executing their contents first. Extract only into a new isolated destination with traversal/link protections appropriate to the format; do not unpack over an existing checkout or install directory.

Verify each declared entry point, runtime asset, license and applicable README/metadata file inside the artifact. Check names/version against the component's authoritative source, accounting for native normalization such as Python distribution names. A publishable child and a private monorepo root have different identities. Match lockfile/dependency/runtime constraints to the actual build.

Keep secrets and unrelated data out of the payload. Inspect names/metadata first; a suspected credential file is a packaging failure, not permission to read or reproduce its value. Check the runtime's actual inclusion rules: a file allowlist or ignore file alone does not prove the archive contents.

## Exercise The Consumer Path

Use the actual tarball, wheel, source distribution, extracted binary, image or app package in an authorized disposable environment. Test the README's primary install/import/CLI/startup path with a finite deadline. Avoid source-directory imports, workspace links or previously installed versions that can hide missing files. Record when hooks/network access/dependencies were excluded or unavailable.

Check one useful behavior beyond an artifact listing or version label. For a library this may be a minimal API call; for a CLI a tiny input fixture; for an app/container the existing startup/health path. Check all selected mandatory targets on matching runners. An unavailable platform or signing tool cannot receive a functional/signature PASS from another host.

When a check fails, keep the artifact, command and bounded failure log, state the affected component/target, and fix only the accepted packaging scope. A missing output asset, runtime dependency, wrong entry point or version is a real gap. Finish independent targets and preserve unresolved ones. Do not publish a diagnostic build as a successful release.

## Reconcile Documentation And Publication

Confirm README examples, compatibility, download links and release notes against each final artifact and channel. Use the source project's language and existing version/changelog conventions. Independently versioned desktop/CLI/SDK packages need separate rows; one channel's version cannot stand in for all channels.

Repository-relative images/links may not work in a registry or extracted package. Check the distributed README and intended renderer, or reuse the project's derived registry copy. A local build or publication dry-run does not prove that a public download URL exists. npm package-page README updates follow package publication; a repository edit alone cannot update it. Source: [npm README behavior](https://docs.npmjs.com/about-package-readme-files).

### npm README Check

For every npm tarball, run this local helper before recording README/artifact verification as passed:

```text
python <release-packager-root>/scripts/check_npm_readme.py --tarball <actual.tgz> --consumer <isolated-installed-consumer> --review <review.json> --timeout 10
```

First install the exact tarball into a fresh consumer using the reviewed native command, offline and with lifecycle scripts disabled. Prepare its tiny input fixture. The helper checks packaged files against installed bytes and rejects linked installations. It never installs dependencies or executes hooks.

For packages declaring `bin`, review the first useful direct CLI example in the packaged README. Review its code, dependencies and arguments for offline execution. Write a task-local JSON approval that binds those reviewed bytes:

```json
{
  "artifact_sha256": "<SHA-256 of actual.tgz>",
  "argv": ["example-cli", "hello", "input.txt"],
  "stdout": "Hello, fixture!\n",
  "offline_code_reviewed": true
}
```

The helper compares that argv with the documented command before execution. It resolves the installed manifest's bin directly and checks exact stdout. It never evaluates README chunks, shell syntax, npm scripts, `npx` or global commands. Examples containing shell syntax need separate reviewed verification; they cannot receive this helper's PASS.

Supported CLI bins are Node `.js`, `.cjs` and `.mjs` files with read-only consumer inputs. Node must support `--permission` (Node 22.13+). Child processes, workers, native addons, WASI and writes receive no permission. A preload blocks ordinary Node network APIs; it is defense in depth, not containment for hostile code. Review code before execution. The helper makes no external requests and does not verify external images or registry rendering.

Supported image syntax includes Markdown inline/reference images, HTML `img` and `picture/source` `src`/`srcset`, including dark SVGs. Local paths must exist with exact case in the tarball. Unsupported or unparseable applicable syntax fails. The helper checks file presence, not image rendering or SVG safety.

Packages without `bin` receive `cli: not_applicable`; their required import behavior check remains separate. Missing README, review, runtime, installed bytes or useful CLI example prevents PASS. Other artifact formats keep their native verification routes; this helper makes no claim about them.

If publication is authorized, use the selected native release path and verify the remote name/version and immutable artifact identity afterward. Rebuilding between verification and upload changes the artifact: verify the uploaded bytes or bind them to the checked package. Preserve previous releases and registry immutability. GitHub's automatic source archives do not prove that an installable binary/package was produced; see [GitHub releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Delivery Record

Use the existing release/task record. A compact per-artifact table is enough:

| Component / version | Source identity | Runtime / platform | Artifact location | SHA-256 or image identity | Verification | Publication |
| --- | --- | --- | --- | --- | --- | --- |

Populate rows from actual evidence, including every requested component/target. For files, hash the final bytes after signing, stapling or repacking. For containers, distinguish local image ID, exported-file SHA-256 and remote manifest/per-platform digest. List source SHA plus scoped uncommitted input evidence when applicable. Record precise states such as built, install-tested, signature-verified, unverified target and published/read-back.

Link the actual package files, checksums, command results and required visual evidence. Name remaining capabilities, signing material or authority needed. Stop temporary task-owned processes by verified identity and retain task artifacts/logs; shared services are not task-owned cleanup targets.
