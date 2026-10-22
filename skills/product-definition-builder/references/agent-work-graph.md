# Read-Only Analysis Helpers

Helpers are optional. They only read, search and report. A helper never asks the owner, approves a choice, writes a file, or publishes.

- Use a helper when delegation is authorized for this task and the host exposes read-only tools. Capability alone grants nothing. Without a helper, the parent does the work itself or records the skip with its reason.
- Launch one `market_researcher` per research phase (pre-draft, post-draft). It covers the whole question inventory, unless the owner asks for more. Do not add verifier agents. The checker and the one self-review cover trace and consistency.
- Give the helper frozen sources, the public-safe query summary and the rules in `research-first-guide.md` or `market-research-guide.md`. Do not send confidential inputs.
- The parent records in the Epic what each helper read (paths and SHA-256) and what it returned. A search that found nothing is recorded as `no_sources`. A skipped pass is recorded with its reason.
- A helper's proposal stays `pending` until the owner decides. A proposed new stack row stays `Recommended`.
- Every factual claim carries publisher, URL and retrieval date, or is `UNVALIDATED`.
- If a helper fails, repeat it once or record the gap. A material gap becomes a blocking Open Question.
