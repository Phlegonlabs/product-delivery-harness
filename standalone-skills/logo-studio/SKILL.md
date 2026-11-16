---
name: logo-studio
description: Use only when the user explicitly requests logo-studio or a requested skill workflow requires it. Design or redesign a product logo. Write a brand brief, audit the marks of the field, sketch widely in black and white, cull the sketches against stated criteria, refine a shortlist into vector files, stress-test it at small sizes and in the product's real places, and present ranked concepts for the owner's choice. Use for a new logo, a logo redesign, a rejected logo round, or an app icon and favicon derived from a mark; it approves nothing, clears no trademark and replaces no live asset.
---

# Logo Studio

Run only on the user's explicit request, continuation, or a required dependency of that requested skill workflow.
A matching task, installation, discussion, source edit or existing project artifact does not activate it.
Required checks and dependencies stay within the requested outcome; a new top-level stage needs an explicit request.

Give the product a mark that people can read, remember and tell apart.
Work wide first and narrow second: many rough marks, a written cull, then a few finished concepts.
The owner chooses the logo. This skill prepares that choice.

## Ground The Brand

Read effective project instructions and the product sources.
With a PRD, read `## At a Glance` and `## Users and Personas`. Read `docs/gtm/MESSAGING.md` when present.
Read the approved visual direction, its colours and typefaces, and the current mark.
Read every earlier logo round with the owner's words about it.
A repository or Harness installation is not required. Preserve existing document conventions and accepted decisions.

Fill [the brief template](assets/templates/LOGO_BRIEF.template.md) from those sources.
Label each assumption. Ask only for a consequential gap that the sources cannot answer.
Show the brief before any sketch. The owner's correction replaces the assumption.
Never invent a name, a name in another language, or a tagline.

Choose the scope and record it in the brief:

- `new`: no mark exists, or the owner has opened the mark completely. Run every section below.
- `refresh`: the mark has equity to keep. State what stays, then sketch variations of the rest.
- `derive`: an approved mark needs an app icon, a favicon or another format. Start at Refine The Shortlist.

After a rejected round, record the owner's words verbatim.
When the owner gave no reason, ask once what failed, then continue.
Write your own reading of the failure and label it as yours.
Start the next round from new sketches. Do not rework the rejected marks.

## Learn The Rules

Read [principles](references/principles.md) before any drawing.
The parent passes the brief and these rules to the author; the author reads them in its own context.

## Audit, Sketch And Cull

Read [the round process](references/process.md) before the audit.
Look at the real marks of the field before drawing.
Use public sources only, and send no user or project detail to an outside service.
Keep other companies' marks outside the repository.

Draw the sketch sheet in black on white, across the four families in the process reference.
Score every sketch in the cull table and write why each weak sketch is weak.
Keep the sheet and the table. The owner may pick a sketch that the cull dropped.

## Refine The Shortlist

Refine the strongest sketches into finished concepts, as the process reference describes.
Draw every final file as plain vector paths with outlined type.
Route drawing through the target host's required design author and design skills, resolved from the target's effective instructions.
An image generator is a sketch aid only when the project has authorized a generation provider.
A generated image is never a deliverable. Redraw the mark as vector paths.

## Stress-Test

Read [stress tests](references/stress-tests.md) before judging a concept.
Test all concepts side by side, with the current mark as the before.
Render the tests and read the captures yourself. Fix a fused stroke, a clipped shape or uneven spacing before you present.
A concept that fails a test stays in the record with its failure. Do not hide it.

## Present The Choice

Fill [the round record](assets/templates/LOGO_ROUND.template.md) and save it beside the files.
Show the sketch sheet, the cull table, the concepts side by side, your ranking and what still falls short.
Describe each concept in one sentence. Say plainly when no concept meets the three criteria.
The owner selects one concept, names sketches to develop, or asks for another round.
The agent cannot approve its own work. Record the choice only from the owner's actual words.

## After The Choice

Repair the recorded shortfalls of the selected concept and repeat the affected stress tests.
Produce the final file set and a one-page usage sheet: clear space, smallest size, colour versions and misuse cases.
Hand placement to its owner:

- `ui-design-builder`: the mark as a design input, and its placement in the HiFi.
- `delivery-harness`: favicons, app icon sets and other product assets in the build.
- `go-to-market` and `readme-studio`: avatars, store listing art and the README.

Otherwise name the equivalent owner and expected handoff; these skills are optional dependencies.
A resemblance check by eye is not a trademark search. A trademark search and registration are the owner's legal step.
Never state that a mark is cleared or registered.

## Deliver

Return the brief, the round record, the file paths, the captures, your ranking and the owner decisions still needed.
Separate a drawn concept, a stress-tested concept, an owner-selected mark and a mark placed in the product.
When the project has an Epic, rewrite its `## Handoff` block with the round state.
Without an Epic, include the block inline.
Preserve local Git, installation and external-action authorization; selecting this skill does not grant them.
