# Review Contract

Read this reference for a Delivery Harness security node or any result consumed by another agent.

## Harness Placement

The security review is an integration-stage runtime review. It covers every mission in the candidate and runs after serial integration fixes one integration_head_sha. Under `review_policy: final_candidate` it is the `security` lens of the one final review; otherwise, or on a recorded risk reason or owner request, it is a dedicated node. It must complete before closeout. Resource-safe final regression may run alongside the read-only review on that unchanged candidate only when declared graph dependencies permit it.

The Harness parent owns selection, authorization, dispatch, the durable review receipt, repair routing, and result recording. The reviewer receives a read-only checkout, returns evidence only, and does not edit PLAN or RUN or start nested agents. If the parent runs a Codex Security scan itself, it starts that coordinator directly and uses the Standard repository scan unless the owner asked for a diff or deep scan. A reviewer child never starts a nested scan.

A security integration review is never eligible for the byte-identical-tree skip. Its purpose is a fresh cross-boundary review of the unified candidate.

Targeted re-check: a `final_candidate` PLAN always declares the single repair route, so a validated finding returns `fix_required`. After the one consolidated repair, the same lens runs again in a fresh context on the new SHA. It re-validates the original findings, reviews the diff between the two candidates and its direct consumers, carries forward inspection of unchanged blobs, and returns a complete result object for the new SHA with `coverage.status: complete`. The earlier result never stands for the new SHA.

## Result

Return one object with these fields:

    {
      "review_type": "security",
      "decision": "pass | fix_required | blocked | contract_gap | retryable_failure",
      "reviewed_sha": "<full candidate SHA>",
      "base_sha": "<full base SHA or null>",
      "scope": ["<repository-relative path or subtree>"],
      "exclusions": ["<explicit exclusion and reason>"],
      "trust_boundaries": ["<boundary and protected asset>"],
      "tools": [
        {
          "name": "<tool or manual source review>",
          "status": "passed | findings | skipped | unavailable",
          "evidence": "<command/result or skip reason>"
        }
      ],
      "coverage": {
        "status": "complete | partial",
        "reviewed": ["<surface>"],
        "gaps": ["<gap and consequence>"]
      },
      "findings": [
        {
          "severity": "critical | high | medium | low",
          "confidence": "high | medium | low",
          "cwe": "<CWE id or null>",
          "location": "<path:line>",
          "summary": "<validated issue>",
          "source_to_sink": "<attacker input to impact>",
          "preconditions": "<required attacker position or state>",
          "impact": "<concrete consequence>",
          "counterevidence": "<control or uncertainty checked>",
          "remediation": "<smallest safe fix>",
          "remediation_test": "<observable regression test>"
        }
      ],
      "evidence": ["<exact-SHA and review evidence>"],
      "checks": [
        {
          "id": "<PLAN required check ID>",
          "execution_key": "<64-character lowercase execution key>"
        }
      ]
    }

Copy `checks` exactly from the packet's `required_checks`, or use `[]` when that list is empty. The field may be omitted only when the PLAN declares no required checks. A `null` execution key means the check has no PASS at the reviewed head yet. Do not review from it; the parent renders a new packet.

Use pass only when reviewed_sha is a full SHA, the checkout is clean, required evidence is present, at least one review tool or manual source review has status `passed` or `findings`, `coverage.status` is `complete`, `coverage.reviewed` and `trust_boundaries` are non-empty, `coverage.gaps` is empty, and `evidence` includes the exact reviewed SHA, no validated critical or high finding remains, and `exclusions` is an empty list. An all-skipped or unavailable tool set cannot PASS. Under the current contract, a security PASS cannot carry an exclusion or silently narrow the declared scope. Medium and low findings remain visible and follow the project's declared blocking policy. If no policy exists, do not silently suppress them; report them and state the decision rationale.

Use fix_required for a validated code or configuration vulnerability when the review node declares a bounded repair route. Without that route, return blocked and say so in `coverage.gaps`. The result has no reason-code field; name every blocked cause in `coverage.gaps` or `evidence`. Use blocked when required capability, authorization, source, or evidence is unavailable. Use contract_gap when safe behavior depends on a missing or contradictory product, architecture, or threat-model decision. Use retryable_failure only for a transient review failure that can be retried without changing scope or authority.

## Harness Evidence

Save the returned object as JSON outside the reviewed repository; the parent passes it unchanged with `--security-result`. The parent's validation, live-checkout rechecks, interruption handling and closeout rules are in the security gate of `../delivery-harness/references/verification-gates.md`.
