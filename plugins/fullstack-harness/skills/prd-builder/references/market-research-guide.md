# Market Research Guide

Use this reference for the `market-research` role: a bounded, read-only research pass that runs **after** the candidate package is drafted and reports what the PRD is missing.

This role does not draft the product. Requirements, architecture, UX, and stack decisions are already written when it starts. Its job is to check those drafts against what actually exists in the market and hand back two things: the `market-research.md` artifact and a list of gap findings the parent patches into the package.

## When It Runs

Default: on, for every non-trivial package.

Skip it when any of these is true, and record which one applies:

- The user asked to skip market research.
- No web search or fetch tool is available in the current session. Do not substitute model recall for research — see Source Rules.
- The package is a trivial single-screen stub.

In enhancement mode, run it only against what the new request adds or changes. Carry forward existing `MR-*` findings and their sources unchanged; do not re-research settled market context.

## Inputs

The role receives the frozen discovery context and the candidate package bodies. It needs:

- product name, archetypes, and the interview summary;
- the drafted `PRD.md` body, which is what it checks;
- whether the product is public-facing or internal, because that changes what "the market" means — an internal tool competes with spreadsheets, existing internal systems, and doing nothing, not with commercial products.

## What To Research

Work through these in order and stop at the ones that genuinely apply to this product:

1. **Problem validation.** Is there outside evidence this pain is real and current, beyond the requester's own account?
2. **Existing alternatives.** What do these users do today — named products, in-house builds, manual process, or nothing? An honest "the current alternative is a spreadsheet" is a finding.
3. **Feature baseline.** Which capabilities are table stakes in this category, and which are genuine differentiators? Table-stakes capabilities missing from the drafted requirements are the highest-value gap this role finds.
4. **Differentiation.** What is this product's wedge against the named alternatives, and does the drafted PRD actually deliver it?
5. **Pricing and business model** reference points, when the product has a commercial surface.
6. **Market context and segment** — size, growth, or segment shape only when a drafted goal or metric depends on it. Do not produce market sizing nobody asked for.
7. **Category benchmarks.** What do comparable products treat as acceptable for the metrics `PRD.md` sets targets for? A target with no reference point is worth flagging.
8. **Market-side risks.** Incumbent response, switching costs, platform dependency, regulatory or compliance constraints, and licensing limits on the named alternatives.

## Source Rules

This is the part that makes the artifact worth reading. Follow it exactly.

- Every factual claim carries a source: URL, publisher, and the date it was retrieved.
- Prefer primary sources — the vendor's own pricing or docs page, a filing, a standards body, an official changelog — over roundups, listicles, and SEO content farms.
- Record the retrieval date on every source. Pricing, feature lists, and market figures go stale, and a reader needs to know how old the claim is.
- **Never state an unsourced claim as fact.** If research could not confirm something, record it as `UNVALIDATED` with what was searched and what would settle it. An honest gap is more useful than a confident invention.
- Do not invent competitor names, pricing, funding, user counts, market sizes, or feature comparisons. A plausible-sounding number with no source is the main failure mode of this role.
- Do not present a competitor's marketing copy as verified capability. "The vendor's site claims X" is a different statement from "X works."
- When sources disagree, record both and say they disagree. Do not average them or pick the convenient one.

Assign each finding a confidence value:

| Confidence | Meaning |
| --- | --- |
| `sourced` | Primary or official source, cited with URL and retrieval date |
| `reported` | Secondary source only — press, analyst, or community report |
| `UNVALIDATED` | No source found; recorded as a hypothesis with the search that failed |

## MR Trace IDs

Mint stable `MR-*` IDs for each finding, in `market-research.md`. Preserve them across revisions and never reuse a retired ID for a different meaning, exactly like every other trace family in this package.

A finding earns an `MR-*` ID when it could change a product decision. Background colour does not need an ID.

`PRD.md` cites `MR-*` IDs where a research finding backs a statement; it does not restate the evidence. The full competitor table, the sources, and the retrieval dates stay in `market-research.md`.

## Gap Findings

The role returns gap findings against the drafted package. Each finding names the artifact and section it lands in, the `MR-*` ID that supports it, and what should change.

Typical landing sites:

| Finding type | Lands in |
| --- | --- |
| Pain is broader, narrower, or different than drafted | `PRD.md` `## Problem Statement` |
| Table-stakes capability absent from requirements | `PRD.md` `## Functional Requirements` |
| Something the market treats as out of scope | `PRD.md` `## Non-Goals` |
| A user segment or job the personas miss | `PRD.md` `## Users and Personas` |
| A metric target with no category reference point | `PRD.md` `## Metrics` |
| Incumbent, switching-cost, or platform-dependency risk | `PRD.md` `## Risks` |
| Pricing or business-model reference points | `PRD.md` `## Metrics` or `## Business Rules` |
| A question research could not settle | `PRD.md` `## Open Questions` |
| An integration the category expects | `architecture.md` `## Integrations` |
| Evidence that strengthens or contradicts a named technology choice | `stack-decisions.md` `Frontend Technology Decision`, `Mobile/Desktop Technology Decision`, or `Backend and Data Technology Decision` table (Why It Fits), citing the `MR-*` ID |
| An alternative the market evidence speaks to | `stack-decisions.md` shared `Alternatives Considered` table, citing the `MR-*` ID |

The role reports findings. It does not edit any file — the parent applies them, then reruns the quality checklist.

A finding that would change product scope is a recommendation, not a decision. Scope changes belong to the user; record the finding and let the parent raise it.

## Blocked Path

Return `blocked` — do not publish a half-researched artifact — when:

- no web tool is available;
- every search failed and the artifact would consist entirely of `UNVALIDATED` rows;
- the product is confidential enough that searching it would leak it. Say so and stop; do not search around the edges.

A blocked role is recorded explicitly, never silently omitted. The package can still publish without `market-research.md`; record in `PRD.md` `## Assumptions` that the market context is unvalidated.

## Failure Modes

- **Inventing competitors.** The single worst outcome. An `UNVALIDATED` row beats a fabricated one every time.
- **Stale pricing stated as current.** Always carry the retrieval date.
- **Researching a product that has no market.** An internal tool for one team competes with the current spreadsheet, not with commercial SaaS. Scope the research to real alternatives.
- **Market sizing theatre.** A TAM figure nobody will use is padding. Produce it only when a drafted goal or metric depends on it.
- **Rewriting the PRD.** This role reports gaps; the parent decides and edits.
- **Reopening settled interview decisions.** If research contradicts a decision the user already made, record it as an open question. Do not overturn it.
