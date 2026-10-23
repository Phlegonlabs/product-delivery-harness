# Product Contracts

These are the rule owners for canonical product requirements, bilingual review copies, UI classification, and commercial channels. They carry the same approvals and frozen-input boundaries as the live product sources.

## Source Keep Product Contracts Current

This repository follows [Consumer Keep Product Contracts Current](#consumer-keep-product-contracts-current) below.

## Consumer Keep Product Contracts Current

- English `PRD.md` and `architecture.md` remain implementation authority. When drafting or updating them, maintain complete Chinese `PRD.zh-TW.md` and `architecture.zh-TW.md` review copies under the Product Definition bilingual-review contract; reconcile owner feedback into English first. Chinese copies never replace canonical inputs or grant separate approval. At task entry and change checkpoints, when an existing English PRD or architecture has no Chinese copy, create a complete same-directory `<source-stem>.zh-TW.md` translation under existing write authority, even without a full Harness flow. Preserve English bytes and approvals; validate each available pair and record the backfill in the matching Epic. Read-only tasks report the missing copy; do not overwrite existing translations or automatically rewrite archives.

- When `docs/product/PRD.md` exists, every product change updates the affected PRD requirements, acceptance criteria, and trace IDs in the same change, including small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN.
- Before implementation, classify the change's UI impact as `none`, `structure`, `style`, or `both`. Adding a page, route, visible region, state, or responsive behavior is at least `structure`.
- First classify the work as initial design, enhancement, routine maintenance or explicit full redesign under `ui-design-builder/references/review-workflow.md`. Routine maintenance with UI impact `none` or `style` updates the actual product, effective PRD and accepted change record while retaining historical Wireframe/HiFi/token artifacts; do not treat accepted visual differences as failure. A structural impact (`structure` or `both`) follows affected design gates. New product or stack decisions return to `product-definition-builder`; new initial and explicit full-redesign work uses `ui-design/3`, while a retained `ui-design/2` package keeps its original rules and owner exception. UI work uses `ui-design-builder`, required `frontend-design`, PRD-to-HiFi completeness checks, independent HiFi review and consolidated Visual Approval. `ui-design/3` always requires `design-system/4` and its frozen derived HTML; retained `ui-design/2` compiles `design-system/3` only when the Need Gate requires it. Preserve unrelated pages and old approval semantics. An already frozen managed RUN keeps its pinned contract; reconcile at a task boundary rather than weakening its gates.
- Preserve unaffected requirements, IDs, pages, wireframes, and design decisions. A direct task may stay small, but it is not complete while implementation and the canonical product documents disagree.

## Monetization And Partner Channels

When a product has pricing, paid access, purchase-gated features or outside sellers, read [Monetization And Partner Channels](../project-operating-rules.md#monetization-and-partner-channels) before product, stack or UI changes. Keep those gates in the PRD and separate billing, entitlements and partner responsibilities.
