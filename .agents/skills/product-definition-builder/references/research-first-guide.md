# Research-First Guide

Use this reference for the research-first assessment: a bounded, read-only pass that runs **before** the closed-set decisions and PRD drafting, and decides whether this product should be drafted at all. The post-draft market-research pass (`references/market-research-guide.md`) stays; it reconciles this assessment against the drafted package instead of researching from a blank slate.

## When It Runs

Default: on, for every non-trivial new package, after the interview's free-text segments complete and before the first `AskUserQuestion` closed-set batch.

Skip it when any of these is true, and record which one applies in `PRD.md`'s `### Research Gate`:

- The user asked to skip the assessment.
- No web search or fetch tool is available in the current session. Do not substitute model recall for research.
- The package is a trivial single-screen stub.

Enhancement mode never runs this pass: the delta is assessed by the post-draft market-research pass, scoped to only what the new request adds or changes.

## What To Assess

Work through these in order and stop at the ones that genuinely apply to this product:

1. **Segment and problem evidence.** Who has this problem, and is there outside evidence it is real and current — beyond the requester's own account?
2. **Jobs to be done.** What concrete jobs would the intended users hire this product for, in their words where possible?
3. **Existing alternatives.** What do these users do today — named products, in-house builds, manual process, a spreadsheet, or nothing? An honest "the current alternative is a spreadsheet" is a finding.
4. **Integration baseline.** Which integrations, platforms, or data sources are table stakes for this product's category?
5. **Adoption signals.** What evidence exists that the intended users would adopt or switch — pricing expectations, switching costs, distribution channels?
6. **Market-side risks.** Incumbent response, platform dependency, regulatory or compliance constraints, and licensing limits on the named alternatives.

## Source Rules

Apply `references/market-research-guide.md`'s Source Rules and confidence vocabulary unchanged: every claim carries a source URL, publisher, and retrieval date; prefer primary sources; record what could not be confirmed as `UNVALIDATED` with what was searched; never invent a competitor, price, user count, or market figure.

## Delegation

The same authorization discipline as the market-research pass applies: a single read-only subagent only when the parent holds a separate explicit delegation authorization for it, otherwise the parent runs the role inline. There is no workflow lane for this phase — the Dynamic Workflow runs after the closed-set decisions — and the single-subagent grant is never inferred from tool availability or package size.

## The Artifact

Write `research-assessment.md`:

```text
# Research Assessment: [Product Name]

## Scope of This Assessment
Researched on: [YYYY-MM-DD]

## Segment And Jobs Evidence
| Finding | Evidence | Confidence | Sources |

## Existing Alternatives
| Alternative | What it is | Who uses it | Where it falls short | Confidence | Sources |

## Integration And Adoption Baseline
[prose or table]

## Market Risks
[prose or table]

## Findings
| RA ID | Finding | Confidence | Sources |

## Unresolved
| Question | What was searched | What would settle it |

## Sources
| Source ID | Publisher | Title | URL | Retrieved | Type |
```

`RA-*` IDs follow the `MR-*` discipline: mint a stable ID only for a finding that could change a product decision, preserve IDs across revisions, and never reuse a retired ID. `PRD.md` cites `RA-*` IDs the same way it cites `MR-*`; it never restates the evidence.

## The Gate

The researcher recommends; the human owner decides. Record the decision in `PRD.md`'s `### Research Gate`:

```text
Research Gate: [go | clarify | stop] — assessed [YYYY-MM-DD], findings in research-assessment.md
```

- `go` — the evidence supports drafting. Proceed to the closed-set decisions with the assessment's findings as input.
- `clarify` — specific unresolved items would change the product's shape. Ask exactly those questions in one bounded `AskUserQuestion` round, record the answers as resolutions in `research-assessment.md`'s `## Unresolved`, then re-assess only the affected findings and record the final gate value.
- `stop` — the evidence says do not draft this product: no real problem, an existing alternative the segment will not switch from, or a blocking risk. Draft nothing. Report the findings, leave `research-assessment.md` in the staging directory for the user, and end the run.

A researcher-recommended `stop` without owner confirmation is recorded as `clarify` with the decisive question stated, never as a silent refusal to draft.
