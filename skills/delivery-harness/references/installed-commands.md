# Installed commands and stage bindings

Resolve each `<name-skill-root>`, such as `<delivery-harness-skill-root>`, to the absolute directory containing that skill's installed SKILL.md. Resolve sibling skill roots from the same installation, normally `~/.agents/skills/`. Quote script paths. Keep the working directory and `--repo-root` at the target project; do not assume it contains `skills/`.

In references, `skills/<name>/scripts/`, `<name>/scripts/`, and bare `scripts/` are logical installed paths. Expand them to the observed absolute skill root before execution. Repository maintenance and CI commands still run from the source repository.

For a receipt-proven inherited-head rejection, `harness_transition.py ... reconcile-worker-ingestion` uses the [strict recovery flags](execution-state-model.md#scripted-transition-flag-surfaces). It preserves the failed dispatch and creates no author attempt. Ordinary failed results remain ineligible.

For an owner-authorized host policy change, use `harness_transition.py [global flags] update-role-bindings --policy <absolute-local-json> --expected-role-bindings-sha256 <digest> --update-id <id> --owner-source <reference>`. Global flags include `--plan`, `--run`, `--repo-root` and the held parent `--session-id`. The JSON maps existing logical roles to complete replacement bindings. See the [quiet-boundary and history contract](runtime-adapters.md#host-role-policy-updates).

Before each stage, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage <stage>`. The stage names are:

- `product-definition`: future slots may be absent or `pending`/`pending`; no installed-stage PASS is claimed.
- `ui-design`: UI authoring, style integration, and UI quality bindings.
- `design-compilation`: compilation and style integration bindings.
- `backend`: code security, only for an approved headless product or a backend-only scope with no UI work.
- `all` (default): all six slots, required for full UI delivery or unknown applicability.

`--stage backend` narrows binding validation only; it never waives the applicable design and self-review handoff in `pre-delivery-self-review.md`.

Every row must remain well-formed, unique, and known. A deferred row either uses `pending` in both cells or a syntactically valid skill name and full-tree hash. Only required-stage installed trees are verified. Recheck on every stage transition: an earlier result never authorizes a later stage. Product context resolution uses the matching `--stage`, but it checks document shape only; `check_skill_bindings.py` proves installed bytes.
