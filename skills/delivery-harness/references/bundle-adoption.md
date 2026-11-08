# Bundle Adoption

Use this procedure when a consumer repository adopts a newly installed Harness bundle. A Harness bundle adoption is one Change Log row with the adopted digest in the current Epic, never a new Epic. It changes no product decision and grants no commit, push or install.

1. Read `delivery-harness/VERSION` and compute the digest: `python "<delivery-harness-skill-root>/scripts/harness_contract.py"`.
2. Update the two `## Harness Version` bullets in `AGENTS.md`: the install line (version, tag commit SHA, date, skills root) and the five-skill contract SHA-256.
3. Run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md AGENTS.md --previous-skill-dir <installer backup dir>`. Re-pin only a binding it labels `previous_release`, after reviewing that skill's semantic diff; an `owner_pin` change is an owner decision.
4. Run `python "<delivery-harness-skill-root>/scripts/configure_project_context.py" --root . --check --merge-agents` and fix stale shared rules in place, as [Handoff Documentation Audit](governance/task-and-handoff.md#handoff-documentation-audit) says.
5. Search live documents outside `docs/epics/` and `docs/goal/` for the old version, tag or digest. Fix current-state lines only; history stays as written.
6. Append exactly one row to the current Epic's Change Log, never a dated section: version, tag commit, contract digest, previous digest, binding result, template verdict and remaining work.
7. Save the document-sync snapshot only under [Reconcile Under Existing Authority](document-sync-contract.md#reconcile-under-existing-authority).
8. Rewrite that Epic's one `## Handoff` block.
