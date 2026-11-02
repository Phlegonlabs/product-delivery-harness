# AI Feature Contract

The AI and Automation Gate says what to decide. This reference says how to run an AI feature once those decisions exist. Use it when the gate is `required`. It adds no gate, no table row and no schema field. Write each item in the row its trace token names, in the architecture's AI and Automation section, or in the stack decision's AI table.

## Prompts And Models Are Versioned Artifacts

- Keep every prompt, system message, tool description and output schema at a repository path. A copy in a console or database is not the source.
- The `AI-CAPABILITY` row cites each path with its SHA-256. Every eval result cites the same path and hash.
- A changed prompt or model is a new candidate. It needs a fresh eval, like any changed input under [Evaluation Policy](eval-policy-contract.md).
- Record the pinned model snapshot as the eval `subject` identity and the prompt hashes in its `configuration`. A rolling alias or provider-side default is a mutable dependency: list it in `freshness.dependencies` and read its identity back during the run.

## Model Matrix

Record one entry per capability in the `AI-CAPABILITY` row or the stack decision's model row.

| Field | Record |
| --- | --- |
| Primary model | Exact snapshot ID or alias, and why it fits |
| Fallback model | The `AI-FALLBACK` target and the trigger that selects it |
| Routing rule | What sends a request to each model: input size, tier, error or budget state |
| Max context | The input and output token ceilings the feature uses |
| Provider setting | Temperature, tool list, structured-output schema path and reasoning effort |

Provider retirement dates are an Open Question until the owner pins them. Name the owner and a deadline. Close the question with the date from the provider's current deprecation page and the retrieval date. Recheck on a stated cadence.

## Cost Budget

The `AI-OPERATIONS` row holds the budget for each feature:

- **Per request:** maximum tokens in and out, and maximum money.
- **Per month:** a money ceiling and an alert threshold below it. Name who receives the alert.
- **At the ceiling:** one named behavior: degrade to the fallback model, queue requests, or disable the feature. Test it as an `AI-FALLBACK` case.
- **Measurement:** record the usage read-back as an `MS-*` row like any metric. Product metering is `first_party`. Name the provider's usage dashboard or usage API in `Retrieval` as the cross-check. A budget without a read-back is a hypothesis.

Eval runs spend under the policy's `limits`, not under this budget.

## Eval Set Lifecycle

- **Build:** the owner labels a golden set that represents the PRD journeys, including refusals, malformed input and tool failure. The set holds no personal data. Redact or synthesize it.
- **Size floor:** set `minimum_cases` for each slice in the policy. A slice under its floor fails. Do not copy a floor from another product.
- **Location:** the dataset, rubric, grader and subject sit at new immutable paths, such as `evals/inputs/<revision>/`.
- **Regression run:** every prompt or model change reruns the full eval. The report binds to the prompt and model hashes through the `subject` and `freshness.dependencies`. A pass on old hashes proves nothing.
- **Offline before release:** the quality eval passes at the tested candidate before release.
- **Online after release:** record a sampling rate for production traffic, a labelling owner and a review cadence. Redact each sampled case before it enters the set. Accepted cases go into a new revision at a new path through the existing approval flow. Never edit a bound file.
- **Monitoring:** online signals, such as error rate, refusal rate, user correction and cost, read through the `AI-OPERATIONS` source. They raise alerts. They never replace the offline gate.

## Human-In-The-Loop

When a person must approve a side effect or review a low-confidence output, record:

- **Reviewer queue:** where items wait, and what each item holds: input, model output, proposed action, evidence, and prompt and model hashes. Show reviewers no more data than the decision needs.
- **SLA:** time to first review and time to expiry. An expired item is denied. It is never auto-approved.
- **Approval surface:** when a reviewer acts in a product screen, define it as a `UI-*` entry in the PRD UI Surface Contract with pending, approved, rejected and expired states. Point the `AI-SIDE-EFFECTS` row at that entry.

## Retrieval Governance

Apply this section when the feature retrieves context. Record it in the `AI-CONTEXT` row.

- **Source allowlist:** each corpus, its owner and its data class. Index nothing outside the list.
- **Chunking and index:** the chunking rule and embedding model. Version them like a prompt; a change is a new candidate.
- **Refresh cadence:** how often each source reindexes, and how a deleted source record leaves the index.
- **Citation:** each answer cites the sources it used. An answer with no supporting source says so and does not guess.
- **Stale-index detection:** an alert fires when index age exceeds the cadence, or when the source version differs from the indexed version.

## Tool Permission Manifest

For an agent, keep a manifest at a repository path. It mirrors the `AI-SIDE-EFFECTS` row and cites its SHA-256 like a prompt. Each row records:

- the tool name;
- the side-effect class: read-only, reversible write, or irreversible or external;
- the credential name, never its value, and the scope limit;
- the confirmation point: none, user confirmation, or reviewer approval.

A tool absent from the manifest is denied. A change to the manifest is a new candidate. The manifest grants no permission by itself; the owner's approval of the row does.
