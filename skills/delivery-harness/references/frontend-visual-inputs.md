# Frontend Visual Inputs

Before every direct or managed frontend dispatch, include one `Visual inputs` block in the actual task sent to the author.
Use the existing task packet; do not create another design specification or approval record.
The author does not inherit the parent's conversation, browser session or inspected images.
Use the executor settings selected by effective agent configuration; this block supplies visual inputs, not execution policy.

Generate the block from the current UI contract when this helper is available:

```text
python "<ui-design-builder-skill-root>/scripts/visual_inputs.py" --repo-root <project-root> --ui-design docs/design/ui-design.md --stage <direction|hifi|implementation>
```

The helper reads current identities and emits source pointers without writing files or granting approval.
It rejects stale inputs and missing stage dependencies. Existing publication and managed source-join checks still govern acceptance.
For implementation maintenance, pass `--task-record docs/epics/<current-epic>.md` after validating the existing `maintenance` record with UI impact `none` or `style`.
This route names current Product/Stack files and retains historical UI, selected studies, captures and target identities without rewriting them.
Other stages keep strict product-source joins. Managed work still requires its exact frozen task record and current Product Definition/PLAN joins.
The task record classifies this packet; it grants no approval or permission and cannot waive those checks.
Ordinary `design-system/4` preview bytes must match the existing deterministic renderer for the bound pair and HiFi.
Maintenance omits the historical derived preview from current input pointers; it retains the authoritative pair and HiFi without requiring fresh rendering or approval.
Run `check_launch_packet.py` on the complete final message with its explicit byte budget.
Overflow requires a smaller scoped assignment or complete named source reads; never silently truncate visual inputs.

## Required Contents

- Stage, approved Product/Stack sources, UI contract path/hash and exact assigned surfaces, states and targets.
- Selected direction, its retained study HTML and screen captures, plus the current approved HiFi target when implementation requires it.
- Font declarations, weights, language coverage and fallbacks from Style Integration, Platform rules and the bound study/HiFi sources.
- Approved image, icon, font and media locations or inline source identities from Motion And Media Intent and the bound studies/complete HiFi package.
- Concrete visual features from the existing Design Brief, selected-direction rationale and Candidate theme.
- The applicable design-system pair and derived preview, and existing repair findings/captures when this is a repair.
- Required reads and the author's own report of files, hashes, captures, fonts, assets and features actually inspected.

Keep values in their existing authoritative sources. The block carries exact pointers and inspection duties, not a competing copy.
System fonts and approved inline assets need no invented external file. Name their source declarations explicitly.
An explicit unused/not-required asset remains so; a missing required asset is a gap, not permission to invent or download a substitute.

## Stage Boundaries

`direction` permits pending selection, study HTML, captures and HiFi. Validate every recorded source identity. Pass the current Design Brief and inspected reference material.
`hifi` requires the owner's selected direction and its captures, while the final HiFi approval may still be pending.
`implementation` requires the selected direction, approved target/scope and applicable design-system sources.
Design-reference repairs use the design stage; production UI repairs use implementation and the existing defect ledger.
Do not change a retained actor's model silently when moving between design and implementation.

Before editing, the author opens the named sources and inspects the actual captures with available image/browser tools.
Reading HTML text alone is not visual inspection. Missing inspection capability blocks the dependent visual work.
The author reports what was actually inspected and any missing input; the parent does not backfill that evidence.
Keep full-tree skill pins, current-source checks, 85/80 thresholds, necessary browser/native/motion evidence and existing repair limits.
No extra taste review, scoring wave, product decision, asset-generation grant or external action is introduced.
