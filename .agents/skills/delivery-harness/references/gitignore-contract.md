# Gitignore Contract

Use this contract whenever a direct task or managed mission introduces or retires a file class that may be local-only. The goal is a small, toolchain-specific `.gitignore`, not a generic list copied into every repository.

## Scope Scan

During System Review And Route, inspect the existing `.gitignore`, tracked file names, package and build manifests, framework configuration, CI workflows, and documented output paths. Do not open value-bearing environment files, credential files, key stores, or exported secrets. Record one result:

- `none`: the task adds no new local-only file class and retires none;
- `update`: observed files or toolchain behavior justify exact rule changes; or
- `needs owner decision`: a file may be either canonical input or reproducible output, and repository evidence does not resolve its ownership.

An uncertain file stays visible to Git until ownership is resolved. Never add an ignore rule only to make a dirty worktree look clean.

## Classification

Ignore a path only when repository evidence shows it is local or reproducible:

- value-bearing local environment files, credential exports, private keys, and provider-local secret files;
- installed dependency directories that the tracked manifest and lockfile can restore;
- generated build, packaging, coverage, cache, log, temporary, local database, and runtime-state outputs;
- editor, operating-system, emulator, simulator, and platform-local state that the project does not intentionally share.

Keep these tracked unless repository governance explicitly says otherwise:

- source code, source assets, tests, fixtures, schemas, migrations, and seed definitions;
- dependency manifests and lockfiles;
- `.env.example`, `.env.*.example`, typed environment schemas, and platform-native configuration examples containing names or placeholders only;
- CI, deployment, infrastructure, product, architecture, wireframe, design-system, and operational documents;
- generated artifacts that are canonical inputs, release artifacts, vendored dependencies, snapshots, or fixtures the repository intentionally versions.

If a generated-looking file is consumed as a required source or compared in CI, treat it as tracked until the owner or repository contract says otherwise.

## Environment Files

Select patterns for the framework and platform actually present. The normal dotenv shape ignores value-bearing variants while explicitly keeping examples visible:

```gitignore
.env
.env.*
!.env.example
!.env.*.example
```

Add `.dev.vars`, `local.properties`, `.xcconfig`, or another platform form only when that toolchain uses it, with a tracked example or schema where the platform supports one. Do not create an empty example file when the application reads no environment variable. When code introduces a new environment-variable read, add the placeholder to the tracked example or typed schema and the value-bearing-file ignore rule in that same task.

Never read a secret value to build the example. Derive names from code, typed schemas, tracked examples, platform configuration, CI declarations, and `docs/DEPLOYMENT.md`. If a required value is unavailable, stop and request it through the repository's secret handoff instead of inventing it.

## Editing Rules

Preserve existing entries and comments. Add the narrowest practical pattern, near related rules, in the same scoped task that introduces the file class. Remove an obsolete pattern only when the task proves the class no longer exists and the removal will not expose user data.

Do not use `.gitignore` to hide a file that should be reviewed, to silence unrelated dirty state, or to work around a verifier. Do not untrack, move, delete, rotate, or rewrite history for an already tracked file without explicit authorization. If a likely secret file is tracked, report its repository-relative path without opening it and stop before commit or push.

For a managed mission, include `.gitignore` and every affected example or schema path in the owning task's `write_scope`. Keep the edit and its verification inside that task's atomic commit.

## Verification

Run the checks that fit the changed rules from the repository root:

1. Use `git check-ignore -v --no-index <representative-local-path>` to show the exact positive rule for every newly ignored class.
2. Use `git check-ignore -v --no-index <representative-example-path>` to inspect any matching negation, and use `git status --short --untracked-files=all` or `git ls-files --error-unmatch <path>` to prove a real example remains visible or tracked.
3. Use `git status --short --ignored` to check that the rule does not hide source, tests, lockfiles, migrations, examples, or required artifacts.
4. Use `git ls-files` with name-only filtering to confirm no value-bearing local environment or credential file is tracked. Never print file contents.
5. Review the complete `.gitignore` diff and run `git diff --check`.

Record the representative paths and results in the task evidence. A passing build does not replace these checks.
