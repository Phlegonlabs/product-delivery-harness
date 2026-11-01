# GA4 Admin Setup

Use this when a web or app surface measures behavior with Google Analytics 4 (source role `ga4`). Run it for every product that ships with GA4, and again after a release adds or changes tracked actions. The rules in [External Setup](external-setup.md) still apply: changing a live property is an external action that needs the owner's explicit instruction, and a setting stays `configured` until a read-back returns data.

Google renames menus and changes limits. Check the linked help page and the [configuration limits](https://support.google.com/analytics/answer/12229528) at execution time; do not copy a number from memory.

## After Every Launch

Work through these in order. Each step links to its section below.

1. The production property and its streams exist, and the release build sends to the right Measurement ID ([Data Streams](#data-streams)).
2. The tracking plan and funnels are written ([What To Track](#what-to-track), [Funnels](#funnels)).
3. Key events match the plan. GA marks `purchase` as a key event by default; unmark it when the product sells nothing ([Events And Key Events](#events-and-key-events)).
4. Every event parameter the plan reads is a registered custom dimension or metric.
5. Event data retention is 14 months ([Data Collection And Filters](#data-collection-and-filters)).
6. Internal and developer traffic filters are Active. GA creates the internal-traffic filter in Testing, where it removes nothing.
7. Unwanted referrals and cross-domain domains are set on each web stream.
8. Every public site is linked to Search Console ([Product Links](#product-links)).
9. A custom channel group exists when the Growth Contract tracks channels the default does not separate ([Channel Groups](#channel-groups)).
10. Each funnel is saved as a report, and the product's report collection is published ([Reports](#reports)).
11. After 24 to 48 hours, the read-back passes ([Read-Back](#read-back)). A key event that still shows "No stream data detected" means the site does not send it; fix the tag before calling the source verified.

## Account And Property

- One property per product, so its web and app streams join into one user journey. Use separate development and production properties.
- Set the property time zone and currency first; reports use them from the change onward.
- Changing the settings below needs the Editor role or above; marking key events needs Marketer or above. A read-only agent or service account gets Viewer.

## Data Streams

- **Web:** one stream per production site. Record the stream ID and Measurement ID (`G-…`). Review each enhanced measurement event (scrolls, outbound clicks, site search, video, file downloads, form interactions) against the tracking plan, so an automatic event does not duplicate a custom one.
- **Tag settings for a web stream:** cross-domain domains, unwanted referrals (payment, sign-in and other hand-off domains), internal-traffic IP rules, and session timeout.
- **App:** one stream per platform and app ID: the iOS bundle ID plus App Store ID, or the Android package name. Adding an app stream in GA4 creates a new Firebase project. When the app already has one, link from Firebase instead (Project settings > Integrations); one Firebase project links to one property. See [set up Analytics for a website and/or app](https://support.google.com/analytics/answer/9304153).
- **Measurement Protocol:** API secrets belong to one stream. Create one only for a named server-side sender and keep it server-side like any other secret.

## What To Track

Build the tracking plan from the PRD metrics and `TEST-*` signals. Track nothing that no metric, report or decision reads. Keep the plan in `docs/measurement/ga4.md` as one table (event, trigger, parameters, owner, PRD or `TEST-*` ID, key event yes/no) followed by the funnels, index it in `docs/DOCUMENTS.md`, and cite it from the GA4 `MS-*` row in `docs/DEPLOYMENT.md`.

1. **Collected automatically:** `first_visit`, `session_start`, `user_engagement`, plus `page_view` on web and `screen_view` in apps. Nothing to add.
2. **Enhanced measurement (web toggles):** scrolls, outbound clicks, site search, video engagement, file downloads and form interactions. Keep the ones the plan reads; turn off one that a custom event replaces.
3. **Recommended events** for actions the product has: `sign_up`, `login`, `search`, `share`, `generate_lead`, `view_item`, `add_to_cart`, `begin_checkout`, `purchase`, `refund`. Use Google's names and parameters so the built-in reports fill in.
4. **Custom events** for product actions with no recommended name, in snake_case `verb_object` form, such as `create_project` or `click_affiliate`.
5. **Event parameters** for the splits a report needs, such as `method`, `content_type`, `cta_location` or `partner`.
6. **User properties** for slow-changing facts about a user, such as plan tier, signup month or preferred language.
7. **Key events** (formerly "conversions"): only the few outcomes the PRD measures success by, usually signup or lead, purchase, and the product's core action.

Never send personal data (email, name, phone number, street address, precise location) in an event, parameter, user property or page URL. Set `user_id` only to an internal ID that does not reveal the person.

## Funnels

A funnel counts how many people move through ordered steps toward one outcome. Define funnels with the tracking plan, before launch, so every step already has an event.

- One funnel per PRD outcome metric, named after the outcome, such as "Visit to affiliate click".
- Each step is one event, optionally narrowed by a parameter or page, such as `page_view` where the page path starts with `/pricing`. Two to five steps cover most journeys; GA allows up to 10.
- Common shapes:
  - Content site: landing `page_view` → article view → outbound, sponsor or support click.
  - Catalog or affiliate: `page_view` → `view_item` → affiliate click.
  - Lead form: `page_view` → `form_start` → `generate_lead`.
  - Sign-up product: `page_view` → `sign_up` → first core action.
  - Store: `view_item` → `add_to_cart` → `begin_checkout` → `purchase`.
- Decide for each funnel:
  - **Closed or open:** closed counts only people who start at step 1; open lets them enter at any step. Use closed unless people often land mid-journey.
  - **Followed directly or indirectly:** indirectly allows other actions between steps and is the usual choice. Directly means the next event must come right after.
  - **Time limit:** add one only when the PRD metric has a time window, such as "signs up within one day".
  - **Breakdown:** one dimension, usually device category or session default channel group.
- Build it in Explore > Funnel exploration, then use "Save as a report in the Library" and add the report to the product collection. A saved funnel report cannot be edited in place; change the exploration and save a new report. Trended funnels and funnels with more than five filters cannot be saved as reports. See [funnel exploration](https://support.google.com/analytics/answer/9327974) and [custom funnel report](https://support.google.com/analytics/answer/13012015).
- A funnel counts each person's first completion in the date range. It reads past data, so one added after launch still works, but only back to the event retention window.
- Record each funnel's name, steps, type and PRD metric in the tracking plan, and cite it from the `MS-*` row's retrieval.

## Events And Key Events

- Use the tracking plan's event names. Prefer a [recommended event](https://support.google.com/analytics/answer/9267735) when one fits.
- Mark a key event only for a PRD outcome metric, and record its PRD or `TEST-*` ID. Unmarking affects new data only; past events keep their key-event status. See [mark events as key events](https://support.google.com/analytics/answer/13128484).
- Register a custom dimension or metric for each parameter that a report, funnel or exploration reads. An unregistered parameter is collected but cannot be split in reports.

## Data Collection And Filters

- **Data retention:** standard properties keep event data for 2 or 14 months; the default is 2. It limits Explorations and funnels only; standard reports keep aggregated data. Pick 14 months unless the privacy policy needs less. Raising it applies to data not yet deleted. Record the choice and whether user data resets on new activity. See [data retention](https://support.google.com/analytics/answer/7667196).
- **Google signals and ads personalization:** turn them on only when consent and the privacy notice cover them. Consent Mode accept, reject and revoke paths follow [External Setup](external-setup.md#web-analytics-and-acquisition).
- **Data filters:** internal traffic (web IP rules only; it cannot filter app users) and developer traffic (debug mode). Create each in Testing, confirm it with the `Test data filter name` dimension, then set it Active. An Active filter drops matching data permanently and does not change past data. See [data filters](https://support.google.com/analytics/answer/13296761).

## Channel Groups

- The default channel group cannot be edited. Create a custom group under Admin > Data display > Channel groups when the Growth Contract tracks channels the default does not separate, such as AI assistant referrals, partners or communities.
- Channel order matters: a session lands in the first channel whose rule matches.
- A custom group can become the primary group; it applies from that point on, not to past data.
- Write channel rules from the UTM policy (source, medium, campaign) and record them. See [custom channel groups](https://support.google.com/analytics/answer/13051316).

## Reports

- **Library:** an Editor builds one collection for the product, with topics for acquisition, engagement, retention, monetization and the saved funnels, and publishes it so it appears in the left navigation. See [customize report navigation](https://support.google.com/analytics/answer/10460557).
- **Detail reports:** add the custom dimensions and metrics, and save a new report instead of changing a default one. See [customize detail reports](https://support.google.com/analytics/answer/10445879).
- **Retention:** the built-in retention report shows returning users and cohort retention. A custom cohort or path uses an exploration, which only reaches back as far as the data retention setting.
- **Sharing:** explorations are private to their author until shared; property users with Viewer can open a shared one but not change it.

## Product Links

- **Search Console:** needs Editor on the property and verified ownership in Search Console. A link cannot be edited, only deleted and recreated. See [connect Search Console](https://support.google.com/analytics/answer/10737381).
- **Google Ads:** needs admin on the Ads account and Edit on the property. Link it only when the growth plan runs ads.
- **BigQuery export:** needs Editor on the property and Owner on the Google Cloud project. Use it when a review needs raw events beyond the retention window. See [BigQuery export](https://support.google.com/analytics/answer/9823238).
- **Firebase:** carries the app streams; see Data Streams.

## Tool Access

- Read data with the [Data API](https://developers.google.com/analytics/devguides/reporting/data/v1) (`runReport`, `runRealtimeReport`) and configuration with the Admin API. Give the service account Viewer on the property, and keep its key out of the repository.
- Google's [Analytics MCP server](https://developers.google.com/analytics/devguides/MCP) wraps both APIs as read-only tools such as `run_report`. It is marked experimental. An agent may use it for read-back and growth review.
- Creating streams, key events, filters, channel groups, funnels or links stays a console or Admin API write under the owner's explicit instruction.

## Read-Back

- The row is `verified` only when Realtime or DebugView shows each planned event from the exact release, and a Data API query returns it for the exact property and stream. Installing a tag verifies nothing.
- After 24 to 48 hours, the Events report lists every planned event, every key event has data, and each funnel shows counts at step 1.
- Record property ID, stream IDs, Measurement ID, retention choice, filter states, key events, custom dimensions, funnels, channel group, link states, report collection and check time.
