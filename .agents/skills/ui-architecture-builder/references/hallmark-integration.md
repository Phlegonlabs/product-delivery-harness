# Hallmark Integration

Use this reference only when the separate `hallmark` skill is loaded. Hallmark is a read-only auditor and structural-variety gate inside this workflow; `frontend-design` remains the candidate generator for Frontend Design Preference & HTML Exploration.

Do not copy Hallmark's theme catalog into the product interview. Do not let Hallmark choose a direction for the human. Do not let it create canonical tokens before selected-HTML approval.

## Responsibilities

| Stage | `frontend-design` | `hallmark` | Parent |
| --- | --- | --- | --- |
| Preference discovery | Analyze Purpose, Tone, Constraints, and Differentiation | Supply anti-slop and structural-risk criteria | Ask one product-specific Ask User round and freeze the non-binding brief |
| Candidate generation | Produce exactly two or three complete HTML directions for the same screens | No writes | Freeze equal hard limits and candidate scope |
| Candidate review | Repair the named findings without changing product scope | Run `hallmark audit` on each direction | Save reports, enforce structural distance, and make every candidate reviewable |
| Selection / mix | Consolidate the human's chosen cues | Audit the consolidated selected HTML | Compute the immutable selected-HTML manifest and ask for explicit approval |
| Extraction | No independent redesign | Audit final mockups for drift when available | Extract tokens, primitives, components, recipes, registry, and mockups from the approved source |

Hallmark does not replace the existing taste verifier, accessibility review, platform review, or human approval gate. Its report is evidence for those gates.

## Candidate Rules

- Every direction receives the same frozen routes, flow, regions, wording or display contracts, required states, accessibility constraints, platform rules, representative `UI-*` IDs, and Visual Preference Brief.
- For page scope, candidate directions must differ structurally, not only visually. Record a short structural fingerprint for each direction: macrostructure or page rhythm, heading placement, section sequence, nav archetype when navigation exists, footer/closing treatment when a footer exists, density, and primary interaction rhythm.
- No two directions may share the same generic hero â†’ equal feature grid â†’ CTA â†’ footer skeleton. A palette, radius, font, or light/dark swap on the same skeleton is one direction, not two.
- For component scope, apply Hallmark's component-scope rules instead: skip page macrostructure, navigation, and footer comparison; require the applicable eight states (default, hover, focus, active, disabled, loading, error, success).
- A candidate may use a direction-local token block inside its dependency-free HTML. Those variables are internal consistency tools, not canonical design tokens. Do not create project-root `tokens.css`, `design.md`, or `.hallmark/log.json` during exploration.
- Hallmark may not add claims, metrics, testimonials, logos, routes, regions, features, content requirements, or interaction steps. It audits only the visual and interaction layer inside the frozen product limits.

## Audit Loop

Run `hallmark audit` separately against every candidate direction and save the exact report beside that direction as `hallmark-audit.md`.

Each report records:

- the direction ID and audited HTML paths;
- the structural fingerprint;
- each finding's Hallmark tell, file and line range, severity, and concrete fix;
- the count of critical, major, and minor findings;
- which Hallmark responsive and state checks were rendered, inspected, unavailable, or not applicable;
- the final decision: `pass`, `fix_required`, or `unavailable`.

Critical and major findings block presentation as a viable candidate. Send them back to that direction's `frontend-design` execution, rerun the audit, and retain the superseded report as history. Minor findings may remain visible during comparison only when they are clearly disclosed; they must be resolved before selected-HTML approval unless the human explicitly waives the exact finding.

Run the same audit on `visual-directions/selected/` after a direct selection or mixed-direction consolidation. Selected HTML passes only when:

- the structural fingerprint matches what the human selected;
- all applicable Hallmark slop-test gates pass;
- no critical or major finding remains;
- any waived minor finding has a named human owner and explicit evidence;
- the required responsive/state evidence is present or honestly marked unavailable.

If Hallmark is unavailable, record `Hallmark status: unavailable` and use this skill's existing taste and anti-slop review. Never fabricate a Hallmark report and never claim a Hallmark pass.

## Immutable Approval Binding

Approval binds to bytes, not only to a path.

1. Keep selected files under the canonical run path `visual-directions/selected/`.
2. For each representative `UI-*` ID, record its exact HTML path and lowercase SHA-256 digest.
3. Canonically serialize the ordered `{ ui_id, html_path, sha256 }` list and record its SHA-256 as `approval_manifest_sha256`.
4. Show that manifest digest with the selected HTML when asking the human for approval.
5. Store the human approval evidence beside the same digest.
6. Immediately before Dynamic Workflow launch, the parent reads every selected file, recomputes its SHA-256, rebuilds the ordered manifest from those verified values, and records `selected_files_verification` with `status: "passed"`, `verified_by: "parent"`, the manifest digest, verified file count, and concrete evidence.

Any selected-file content change, path change, file addition/removal, or manifest reordering invalidates the approval. Recompute the manifest, rerun the selected Hallmark audit, and ask for fresh approval before extraction.

The Dynamic Workflow receives the canonical selected directory, the per-screen file manifest, `approval_manifest_sha256`, and the parent byte-verification record. It canonically serializes the ordered `{ ui_id, html_path, sha256 }` entries, recomputes their SHA-256, requires it to equal both the approved digest and the parent verification record, and rejects a stale or shape-only digest before launching. The parent owns real file existence and byte hashing; the workflow owns independent manifest recomputation.

## Final Projection Review

After extraction, audit the canonical `mockups/*.html` and `design-system.html` when Hallmark is available. Treat the approved selected HTML as the visual source and the extracted package as the binding implementation contract:

- repair extraction drift in the package;
- return to selected HTML and obtain fresh approval when a repair materially changes the approved direction;
- do not pull rejected candidate values back into the package to satisfy a Hallmark preference;
- record unavailable render evidence honestly instead of claiming a pass.
