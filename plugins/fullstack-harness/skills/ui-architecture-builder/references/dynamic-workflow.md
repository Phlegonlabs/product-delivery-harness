# Claude Code Dynamic Workflow

Use this reference only after design discovery, Builder UX Direction intake, and source identification are complete. A workflow cannot obtain design approval, choose between unresolved human directions, or authorize publication.

`references/ui-architecture-guide.md` holds the layer model, the source-of-truth precedence, and the derivation method. The roles below split that work between agents; they do not restate it. Every role reads that guide for its own layer's rules and stays inside that layer.

## Graph Model

The stable org graph defines these roles:

| Role | Responsibility | Output |
| --- | --- | --- |
| visual-thesis-content | Product-specific thesis, taste statement, content realism, landing-page restraint | Visual direction and content rules |
| content-contracts | Product rules turned into content contracts: required fields, limits, formats, CTA counts, empty and long-content handling, never-drop fields; route and state contracts; the state matrix | Content contracts, route/state contracts, and the state matrix |
| system-components | Tokens, typography, the layered component architecture (layout, surface, and control primitives through product components), states, accessibility | Design-system sections, the component inventory, and DS IDs |
| primitive-contracts | A closed variant set per primitive, each variant's purpose and forbidden use, the product-component bindings, and the guardrail checks that must fail when a page leaves the set | Primitive contracts and the registry input |
| iconography | Current source scan, semantic coverage, token and accessibility rules | Icon system decision |
| motion | Purpose, the three-mechanism split, tokens, registered variants, choreography, performance and one global reduced-motion policy | Motion architecture, registered variants, and demo contract |
| page-recipes | Per-route section order, container, density, allowed surfaces, required components and their content contracts, forbidden patterns, required states, and the no-JavaScript floor | Page recipes |
| page-coverage | Route/screen, breakpoint or size class, state, mockup, data, and evidence mapping | Page coverage and visual gates: a per-page HTML mockup plan (styled to the resolved platform), the component catalog plan, and the route → mockup → trace → DS → TEST index |
| synthesis | Reconcile all role outputs | The UI architecture artifact bodies, including the registry and the per-page mockup HTML |
| taste-verifier | Check product specificity, hierarchy, and anti-slop rules | Findings and decision |
| trace-verifier | Check upstream/DS/test trace coverage and internal consistency | Findings and decision |
| registry-verifier | Check that the registry, the primitive contracts, the page recipes, the state matrix, and the catalog describe the same system | Findings and decision |

A role that sets a value another layer owns is a verifier finding, not a shortcut.

The temporary work graph is one bounded workflow run. It fans out independent design analysis, joins for synthesis, then fans out independent verification. It does not replace the parent-owned staging lifecycle or the Harness PLAN/RUN graph.

## Preconditions

A package is "non-trivial" when more than one role in the Graph Model above would produce substantive, non-boilerplate content for it — for example a UI-bearing product spanning more than one screen or archetype, not a single-page trivial stub. "Multi-agent analysis is authorized" means the current session is not restricted to single-agent or sequential-only execution by explicit user instruction, host policy, or permission mode. Both conditions must hold before launching this workflow; when either is false, perform the roles sequentially instead.

Before launch, the parent must have:

- a stable run ID and product name;
- product archetype, audience, and source paths or source summary;
- Builder UX Direction and its selected/provisional/assumed status for UI-bearing products;
- the exact approved selected HTML plus its human approval record, or an explicit `visual_direction_pass.status: "not used"` or `"rejected"` record; an `approved` payload includes one or two unique non-empty `representative_ui_ids`, two or three `candidate_directions` with a unique `direction_id` and one unique canonical `html_path` per representative screen, a canonical `selected_html_path` equal to one approved manifest path, an ordered `selected_html_files` entry per representative UI ID with canonical path and lowercase SHA-256, the lowercase `approval_manifest_sha256`, `approval_owner`, `approval_evidence`, and `selected_files_verification` proving that the parent read every selected file and recomputed its byte digest immediately before launch; the workflow independently recomputes the canonical manifest SHA-256 and rejects any mismatch; the workflow never launches while preference discovery, candidate comparison, selected-HTML consolidation, byte verification, digest binding, or approval is still pending;
- `hallmark_review.availability` set explicitly to `loaded` or `unavailable`; unavailable runs include a reason and never claim a Hallmark pass; loaded approved runs include one ordered parent-verified candidate report at the exact `hallmark-audit.md` path beside that direction's canonical HTML plus the exact selected-root `hallmark-audit.md`, whose manifest SHA-256 equals the approved selected manifest; every report retains a `passed` or `repaired` disposition and concrete evidence; loaded runs without approved selected HTML explain that state in `hallmark_review.evidence`;
- explicit decisions on whether iconography and motion are in scope;
- the closed-set architecture answers from `references/design-interview-guide.md`: styling engine, animation runtime split, registry enforcement mode, and greenfield-or-phased adoption;
- the required viewport set (390 / 768 / 1200 / 1440 px unless the user names different ones);
- resolved conflicts that require a human choice;
- a machine-enforced `builder_readonly` launch profile that exposes only Workflow and the required read/search/web tools, with no `Edit`, `Write`, `NotebookEdit`, `Bash`, or other mutating MCP tools.

If the host cannot enforce that read-only tool boundary, use the sequential parent fallback.

## Execution

Use `assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js` with structured arguments. The workflow is read-only:

1. Visual thesis/content, content contracts, system/components, primitive contracts, page recipes, page coverage, and conditional icon/motion roles run independently. Every role treats the human-approved selected HTML and its verified manifest digest as frozen visual input and extracts its own layer from that source, but no role may generate a different direction, revive rejected candidate values, reinterpret the approved composition, or treat Hallmark review evidence as product authority. When exploration is `not used` or `rejected`, roles use the recorded product inputs and explicit visual assumptions and do not claim approved-HTML extraction.
2. Failed or skipped agents remain explicit blocked role results.
3. Synthesis waits for the complete role barrier and returns candidate artifact bodies. It derives `ui-registry.json` from the primitive contracts, product components, registered motion variants, and page recipes it returns in the same result, so the registry and the architecture body cannot describe different systems.
4. Taste, trace, and registry verifiers independently inspect the synthesis. When Hallmark reports exist, the taste verifier checks that their critical and major findings were repaired or explicitly blocked; it does not rerun Hallmark or claim a new pass.
5. The parent repairs findings, renders or reviews evidence when available, and, when Hallmark is loaded, performs a final read-only Hallmark audit of the design-system projection and representative final mockups for extraction drift. It then stages the artifacts and applies the existing publish gate.

The workflow does not create production images or claim rendered visual verification. A returned motion showcase, and the per-page mockup and catalog markup, are candidate source text only until the parent writes them to real `mockups/*.html` files and reviews them. The workflow's synthesis returns candidate artifact bodies for every platform; the parent produces the final `ui-architecture.md`, `ui-registry.json`, `page-recipes.md`, `design-system.md`, `mockups/*.html`, `mockups/catalog.html`, and `visual-acceptance.md`.

## Failure And Resume

- A failed required role blocks finalization until rerun or completed sequentially.
- A material verifier finding must be repaired or recorded as an unresolved constraint.
- A registry that disagrees with the primitive contracts, the page recipes, the state matrix, or the catalog is a blocked result, not a note. The contract check would then run against a stale allowlist, so the parent rebuilds the registry from the architecture body or reruns the role before staging.
- Native workflow resume works within the same Claude Code session. Across sessions, start a new run from the frozen source inputs and retained staging package.
- Record the workflow run ID and review findings in the task report when available.

## Fallback

When Dynamic Workflow is unavailable, perform the same roles sequentially. Do not claim multi-agent review, runtime parallelism, or workflow resume in the fallback path.
