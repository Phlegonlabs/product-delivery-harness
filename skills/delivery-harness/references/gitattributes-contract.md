# Gitattributes Contract

Use this contract when a task adds a hash-bound file class or root. The suite hashes raw file bytes: the PRD and feature files, HiFi pages, the design-system pair and preview, PLAN source rows, the acceptance register and its evidence. Git must store those bytes unchanged.

## Rule

Before Product Definition publish commits the first hash-bound file, the root `.gitattributes` carries `<root>/** -text -filter` for `docs/product`, `docs/design`, `docs/verification`, `docs/goal` and any other hash-bound root that `docs/DOCUMENTS.md` records. `text eol=lf` and `text=auto` do not qualify: they rewrite CRLF bytes on `git add`, so a hash taken before the commit no longer matches HEAD. A content filter such as LFS replaces the bytes in HEAD.

Start from `assets/templates/PROJECT_GITATTRIBUTES.template`. Keep its block, and add a line only for a hash-bound path outside those roots. Only the committed file counts: confirm it with `git show HEAD:.gitattributes`. `git check-attr` also reads `.git/info/attributes` and `core.attributesFile`, which never reach clones, CI or the `review_input.py` clone.

## Check

Run `python "<delivery-harness-skill-root>/scripts/configure_project_context.py" --root <project-root> --check --require-resolved`. It runs `git check-attr` read-only on each root and fails unless `text` is unset, `filter` and `ident` are unset or unspecified, and `working-tree-encoding` is unspecified. It prints the lines to add. Never run Git filters during the check.

## Converted Files

A `bytes differ from HEAD` result can mean line-ending or filter conversion even when `git status` is clean. A hash that matches only after turning CRLF into LF, or LF into CRLF, means Git converted the bytes: fix the attributes, and never regenerate the artifact or re-pin its hash. Files checked out with conversion before the rule landed then show as modified. Checking them out again overwrites the working copy, so it needs owner approval.
