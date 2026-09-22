# English Sources And Chinese Review Copies

Draft `PRD.md` and `architecture.md` in English and produce complete Traditional Chinese review copies alongside them as `PRD.zh-TW.md` and `architecture.zh-TW.md`. Do this during drafting and revision, before presenting a candidate for review; do not postpone translation until publication. These are two views of one package, not separate specifications. Other artifacts remain English unless requested otherwise. Document language does not change the product's supported locales or exact UI copy.

The English files alone are canonical inputs for UI design, implementation, PLAN sources, approval digests and downstream checkers. The Chinese copies explain the same requirements and architecture to the owner. Label each copy visibly in Chinese: it is a review translation, identify and link its English source, and state that implementation uses the English source. Never pass a review copy to `--prd` or `--architecture` or freeze it as an implementation source.

Translate every substantive section, table, requirement, acceptance criterion, risk, assumption, open question and architecture decision in the same order. Keep trace IDs, numeric targets, units, paths, API/schema identifiers, source links and required literal product copy unchanged. Explain technical terms in Chinese while retaining their English names where useful. Do not add, weaken or omit obligations. Translate the human meaning of approval states without creating a second machine approval block or an independent approval history.

Each review copy has exactly one source marker, containing the SHA-256 of the exact English file bytes:

```markdown
<!-- review-source: PRD.md sha256:<64 lowercase hex characters> -->
```

Use `architecture.md` for the architecture marker. Custom filenames explicitly requested by the owner use their real source basenames and explicit review paths. Compute the hash after writing the corresponding English revision. A changed hash means the review needs reconciliation, not permission to update only its marker.

Before every owner review, semantically compare each pair for complete coverage and matching meaning, then run:

```text
python "<product-definition-builder-skill-root>/scripts/check_review_translations.py" --prd <staged PRD.md> --architecture <staged architecture.md>
```

The default companions sit beside the sources; `--prd-review` and `--architecture-review` support explicitly requested custom names. The read-only checker rejects missing copies, stale source hashes and missing or added trace IDs. It does not prove translation quality, completeness or human approval; the parent must inspect those separately. Do not ask for approval with a missing, stale or materially inconsistent review copy.

Present verified links to both Chinese copies first and both English sources alongside them. The owner may comment or approve in Chinese. Accepted review feedback changes the English source first, then its Chinese copy in the same revision; unresolved meaning differences block the existing Product Definition Approval. Confirm that the decision covers the identified English package revision and record it only in the canonical approval block. This does not add a second approval gate. Refresh the copies and hashes after writing approval metadata, without inventing a new owner decision for unchanged substantive content.

Stage, validate, publish and archive each English/review pair together under the existing exact-path publication authority. Recheck hashes immediately before publication and after the move. Index review copies as non-canonical in `docs/DOCUMENTS.md`; retain prior copies with their corresponding archived sources. Never rewrite historical approvals. Downstream work still consumes the approved English sources.

## Existing English-only Documents

At task entry and repository change checkpoints, inspect the current product sources in scope. When an existing English PRD has no Chinese review copy, translate the complete document and create `PRD.zh-TW.md` in the same directory under existing document-write authority. Apply the same rule to an existing English `architecture.md`. Do not wait for a full Harness flow or the next product enhancement. For custom source names, use `<source-stem>.zh-TW.md` beside the source. Do not create a missing architecture just to translate a PRD.

Preserve the English bytes and existing approval metadata exactly. Use the source marker, semantic comparison and trace checks above; validate a PRD-only package with `check_review_translations.py --prd <existing PRD.md>`. Supply `--architecture` whenever that source exists. Recheck source bytes before creating the companion; if they changed during translation, reconcile first. Create missing copies exclusively: if a review file already exists, inspect it and reconcile under the normal update authority instead of overwriting it as a missing file.

Index the new non-canonical copy in an existing document manifest and record the backfill in the matching Epic. Translation alone does not reopen product approval or authorize implementation. On a read-only task, report the missing copy and proposed path without writing. Limit detection to current sources and explicitly requested documents; do not recursively translate archives or rewrite historical packages. An explicitly requested archived source may receive a separate translation while its source and approval remain untouched.
