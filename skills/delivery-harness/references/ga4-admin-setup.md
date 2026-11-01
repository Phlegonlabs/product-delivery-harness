# GA4 Admin Setup

Use this when a web or app surface measures behavior with Google Analytics 4 (source role `ga4`). It lists the Admin settings to decide and record in `docs/DEPLOYMENT.md` External Console Setup and Measurement Sources. The rules in [External Setup](external-setup.md) still apply: changing a live property is an external action that needs the owner's explicit instruction, and a setting stays `configured` until a read-back returns data.

Google renames menus and changes limits. Check the linked help page and the [configuration limits](https://support.google.com/analytics/answer/12229528) at execution time; do not copy a number from memory.

## Account And Property

- One property per product, so its web and app streams join into one user journey. Use separate development and production properties.
- Set the property time zone and currency first; reports use them from the change onward.
- Changing the settings below needs the Editor role or above. A read-only agent or service account gets Viewer.

## Data Streams

- **Web:** one stream per production site. Record the stream ID and Measurement ID (`G-…`). Review each enhanced measurement event (scrolls, outbound clicks, site search, video, file downloads, form interactions) against the event contract, so an automatic event does not duplicate a custom one.
- **Tag settings for a web stream:** cross-domain domains, unwanted referrals (payment, sign-in and other hand-off domains), internal-traffic IP rules, and session timeout.
- **App:** one stream per platform and app ID: the iOS bundle ID plus App Store ID, or the Android package name. Adding an app stream in GA4 creates a new Firebase project. When the app already has one, link from Firebase instead (Project settings > Integrations); one Firebase project links to one property. See [set up Analytics for a website and/or app](https://support.google.com/analytics/answer/9304153).
- **Measurement Protocol:** API secrets belong to one stream. Create one only for a named server-side sender and keep it server-side like any other secret.

## Events And Key Events

- Use the PRD's canonical event names. Prefer a [recommended event](https://support.google.com/analytics/answer/9267735) when one fits.
- Mark a key event (formerly "conversion") only for a PRD outcome metric, and record its PRD or `TEST-*` ID.
- Register a custom dimension or metric only for a parameter that a report or exploration reads.

## Data Collection And Filters

- **Data retention:** standard properties keep event data for 2 or 14 months; the default is 2. It limits Explorations and funnel reports only; standard reports keep aggregated data. Pick 14 months unless the privacy policy needs less. Raising it applies to data not yet deleted. Record the choice and whether user data resets on new activity. See [data retention](https://support.google.com/analytics/answer/7667196).
- **Google signals and ads personalization:** turn them on only when consent and the privacy notice cover them. Consent Mode accept, reject and revoke paths follow [External Setup](external-setup.md#web-analytics-and-acquisition).
- **Data filters:** internal traffic (web IP rules only; it cannot filter app users) and developer traffic (debug mode). Create each in Testing, confirm it with the `Test data filter name` dimension, then set it Active. An Active filter drops matching data permanently and does not change past data. See [data filters](https://support.google.com/analytics/answer/13296761).

## Channel Groups

- The default channel group cannot be edited. Create a custom group under Admin > Data display > Channel groups when the Growth Contract tracks channels the default does not separate, such as AI assistant referrals, partners or communities.
- Channel order matters: a session lands in the first channel whose rule matches.
- A custom group can become the primary group; it applies from that point on, not to past data.
- Write channel rules from the UTM policy (source, medium, campaign) and record them. See [custom channel groups](https://support.google.com/analytics/answer/13051316).

## Reports

- **Library:** an Editor builds one collection for the product, with topics for acquisition, engagement, retention and monetization, and publishes it so it appears in the left navigation. See [customize report navigation](https://support.google.com/analytics/answer/10460557).
- **Detail reports:** add the PRD dimensions and metrics, and save a new report instead of changing a default one. See [customize detail reports](https://support.google.com/analytics/answer/10445879).
- **Retention:** the built-in retention report shows returning users and cohort retention. A custom cohort, funnel or path uses an exploration, which only reaches back as far as the data retention setting.
- Record each report or exploration name in the Measurement Sources row evidence.

## Product Links

- **Search Console:** needs Editor on the property and verified ownership in Search Console. A link cannot be edited, only deleted and recreated. See [connect Search Console](https://support.google.com/analytics/answer/10737381).
- **Google Ads:** needs admin on the Ads account and Edit on the property. Link it only when the growth plan runs ads.
- **BigQuery export:** needs Editor on the property and Owner on the Google Cloud project. Use it when a review needs raw events beyond the retention window. See [BigQuery export](https://support.google.com/analytics/answer/9823238).
- **Firebase:** carries the app streams; see Data Streams.

## Tool Access

- Read data with the [Data API](https://developers.google.com/analytics/devguides/reporting/data/v1) (`runReport`, `runRealtimeReport`) and configuration with the Admin API. Give the service account Viewer on the property, and keep its key out of the repository.
- Google's [Analytics MCP server](https://developers.google.com/analytics/devguides/MCP) wraps both APIs as read-only tools such as `run_report`. It is marked experimental. An agent may use it for read-back and growth review.
- Creating streams, key events, filters, channel groups or links stays a console or Admin API write under the owner's explicit instruction.

## Read-Back

- The row is `verified` only when Realtime or DebugView shows the event from the exact release, and a Data API query returns it for the exact property and stream. Installing a tag verifies nothing.
- Record property ID, stream IDs, Measurement ID, retention choice, filter states, key events, channel group, link states, report collection and check time.
