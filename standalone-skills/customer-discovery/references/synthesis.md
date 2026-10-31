# Synthesis

Turn redacted session notes into one evidence table, then shape decision-relevant findings into `RA-*` candidates.

## Evidence Table

Build one table for the whole study:

| Participant code | Segment | Observation or quote (redacted) | Hypothesis supported or contradicted | Strength | Date |
| --- | --- | --- | --- | --- | --- |

- `Strength` is `observed` when the row records something the participant actually did, and `hypothesis` when it records an opinion or intent.
- Redact names, employers and contact details before a row is written. A row that cannot be redacted is dropped.

## Counting Rules

- Count participants, not quotes. One participant repeating a point is still one participant.
- A pattern needs at least three independent participants before it is called `observed`.
- List disconfirming evidence first. A finding that contradicts a hypothesis is kept and stated plainly.
- Label every finding `observed` or `hypothesis`. An unlabeled finding is not a result.
- State the segment a pattern came from. Do not merge segments silently.
- State the count and stop. A small sample proves no market size.

## RA-* Candidate Rows

Use the research assessment columns of `product-definition-builder` (`RA ID`, `Finding`, `Confidence`, `Sources`) plus `Decision it informs` for the handoff. One row per finding that could change a product decision:

| RA ID | Finding | Confidence | Sources | Decision it informs |
| --- | --- | --- | --- | --- |

- `RA ID`: a stable `RA-*` identifier. Mint it once, preserve it across revisions, and never reuse a retired ID.
- `Finding`: one sentence, stated as a result, with the count of independent participants.
- `Confidence`: `observed` or `hypothesis`, matching the evidence table.
- `Sources`: interview codes and dates, in the form `P03 2026-03-02; P05 2026-03-04`. Never a name.
- `Decision it informs`: the open question or decision named in the study brief.

A finding that could change no decision stays in the evidence table and gets no `RA-*` ID.

## Handoff Note

Pass the candidates to `product-definition-builder` with this note:

```text
Study: <study name and date range>
Hypotheses tested: <count>, with each result: supported / contradicted / unresolved
RA candidates: <count>, listed above with sources
Scope notes: <segments covered, segments missed, known biases>
```

The note hands over candidates. It never marks a research gate `go` and never claims a product decision.
