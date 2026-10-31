# Lifecycle Messaging

Draft copy for the PRD Growth Contract `### Re-engagement` mechanisms and for onboarding sequences.
This reference prepares reviewable drafts. It never configures a provider, sends a message or installs an SDK.

## Scope

Cover two message families:

- Onboarding: the first-use welcome and the early follow-ups that help a user finish the task.
- Re-engagement: copy that returns an inactive or stuck user to an available product surface.

Draft each family from the [messaging record](messaging-house.md) at `docs/gtm/MESSAGING.md`, and cite the record revision on every item.
A mechanism the Growth Contract does not record stays a proposal. Route the product-record gap to `product-definition-builder`.

## Onboarding Sequence

Propose four steps as a starting point: first use, day 1, day 3 and day 7.
Treat that proposal as a default to adjust, not a rule. Fit the steps to the product's activation path and the team's reply capacity.
State the user task each step advances and the proof it uses. Drop a step that advances no task.

## Re-engagement Triggers

Draft against an event, never against a person.

| Trigger | Draft responds to | Event source |
| --- | --- | --- |
| Inactivity | A user has not returned within the proposed window | The Growth Contract return trigger or activity event |
| Abandoned task | A user started a task and did not finish it | The abandonment event the PRD names |
| New relevant content | A shipped change serves the user's recorded task | A release or content piece the team owns |

Name the event in the item fields. Never name, identify or profile a recipient in copy.

## Transactional Versus Marketing

| Message class | Purpose | Consent and unsubscribe |
| --- | --- | --- |
| Transactional | Confirms or supports an action the user took | Follows the channel's transactional rules; carries no marketing content |
| Marketing | Promotes a return, a release or new content | Needs consent where required and a working unsubscribe |

Label each draft with its class. Never dress marketing copy as transactional.
Consent and unsubscribe requirements come from the channel and market the project operates in. Mark them as checks to confirm at execution readiness; do not invent legal text.

## Channel Fit

| Channel | Fits | The draft carries |
| --- | --- | --- |
| Email | Longer explanations, receipts and digests | Subject, body, sender and unsubscribe placement |
| Push | Short, time-relevant prompts | Title, body and tap destination |
| In-app | Help inside the product at the moment of need | Placement, visible copy and dismissal behavior |
| Messaging bot | Conversational replies on an account the team runs | Opening message, reply branches and opt-out wording |

Propose channels the project actually operates. Provider choice comes from `docs/product/stack-decisions.md`; this skill never selects or configures a provider.

## Item Fields

Give each lifecycle item the [campaign template](../assets/templates/CAMPAIGN.template.md) item fields plus two fields:

- `trigger`: the event or condition that fires the message, named as the PRD records it.
- `delay`: the proposed wait between the trigger and the send, stated as a duration.

## Measurement

Bind each mechanism to its Growth Contract `TEST ID`. Cite the `MS-*` row that reads the outcome.
Apply the measurement rules in [experiment review](experiment-review.md).
A missing `TEST ID` or `MS-*` source stays an explicit gap in the package.

## Boundaries

This skill drafts copy and proposes triggers, delays and measurement bindings.
Trigger implementation, provider configuration, SDK installation and sending route to `delivery-harness` and the project's authorized tools.
No personal data enters a draft: no names, contact details, identifiers or behavioral profiles of real people.
The owner reviews every sequence before any send, under the skill's publication boundary.
