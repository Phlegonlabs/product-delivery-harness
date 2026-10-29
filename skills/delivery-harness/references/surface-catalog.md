# Surface Catalog

One project is a set of surfaces. Every stage routes from this catalog: the architecture `## Release Targets` section lists build surfaces, the PRD `### Discovery Surfaces` table lists presence surfaces, `docs/DEPLOYMENT.md` records their setup and measurement sources, and the growth review reads each surface with its own lens. Nothing is inferred from the Shape track alone.

Two kinds of surface exist:

- A **build surface** is a release target. It is built from a Git SHA, has an artifact or deployment identity, and appears in `docs/DEPLOYMENT.md` Release Target Status. Its `Surface class` must be one of the classes below (`release_targets.py` enforces the set).
- A **presence surface** is an account on a platform. It has no SHA. It appears in the PRD Growth Contract as `<platform>:<handle-or-url>` with a presence kind, and is measured through that platform's insights.

## Tracks

The PRD Shape `track` names the primary surface family. It labels the product; it does not replace per-surface routing.

| Track | Primary surfaces | Companion rule | Re-engagement rule |
| --- | --- | --- | --- |
| web | hosted_web | public surface or `none` | at least one mechanism |
| app | ios, android, macos, windows, browser_extension | public companion when AEO/SEO is required | at least one mechanism |
| agent | agent, assistant_listing, messaging_bot | public docs surface or `none (reason)` | mechanism or `none (reason)` |
| tool | mcp_server, cli, library_or_sdk, skill_or_plugin, container_or_self_hosted, internal_service | public docs surface or `none (reason)` | mechanism or `none (reason)` |
| content | presence surfaces only; release targets may be `none` with a reason | `none` allowed | mechanism or `none (reason)` |

## Build Surfaces

| Surface class | What it is | Distribution | Default source roles | Setup profile | Growth lens | Required early missions |
| --- | --- | --- | --- | --- | --- | --- |
| hosted_web | Public website or web app served to a browser | Hosting platform and domain | search_console, ga4, production_page | web | seo, geo | SEO cluster and internal-link skeleton; structured data, `llms.txt`, citeable pages; measurement events; the re-engagement hook |
| hosted_api | Separately released HTTP API or backend | Hosting platform | first_party, service_health | api / backend | none | Contract and error evidence; logs and one alert that reaches its owner |
| worker, job, webhook, realtime | Backend units released on their own | Hosting platform | first_party, service_health | api / backend | none | Heartbeat, timeout, retry and alert ownership |
| browser_extension | Chrome, Firefox or Safari extension | Browser store | first_party, crash | browser extension | store-listing | Listing assets; stable extension ID; store-compliant telemetry |
| ios | Native or cross-platform iOS app | App Store, TestFlight | app_store_connect, crash, revenuecat when subscriptions exist | ios | aso | Deep links joined to the companion surface; push and onboarding events; store assets; crash and analytics setup |
| android | Native or cross-platform Android app | Play Console tracks | play_console, crash, revenuecat when subscriptions exist | android | aso | Same as ios, with App Links and Play data safety |
| macos | Desktop app for macOS | Direct download, notarized DMG/PKG, or store | crash, first_party | macos | store-listing when a store is used | Install, upgrade and uninstall smoke; crash source keyed to build |
| windows | Desktop app for Windows | Microsoft Store, winget or signed installer | crash, first_party | windows | store-listing when a store is used | Same as macos, with signing and SmartScreen evidence |
| cli | Command-line tool released on its own | Package registry or release artifact | registry, first_party | cli / toolchain | directory | Install smoke from a clean machine; telemetry policy; `--help` and version read-back |
| agent | Hosted agent or automation with side effects | Hosting platform | first_party, service_health | agent / automation plus api / backend | directory | Directory metadata; `llms.txt` and public docs; usage events; tool permission boundary; console health when `console: operations` |
| mcp_server | MCP server exposing tools or resources | npm, PyPI, MCP registry | registry, first_party | mcp server | directory | Registry metadata; tool list and permission boundary; install smoke; README quickstart that runs |
| skill_or_plugin | Agent skill bundle, Claude or Codex plugin, editor extension | Install script or marketplace | registry, first_party | skill / plugin | directory | Install from a clean host; version pin read-back; marketplace or README metadata |
| library_or_sdk | Package imported by other code | npm, PyPI, Go module or similar registry | registry | library / sdk | directory | Semver and changelog; install and import smoke; one API docs page |
| messaging_bot | Telegram, Discord, LINE, Slack or WhatsApp bot | Bot platform | bot_platform, first_party | messaging bot | directory | Command list; webhook or polling health; opt-in and rate limits; platform app directory entry |
| marketplace_app | App or template inside another platform: Shopify, WordPress, Figma, Notion, Office | Platform marketplace | registry, first_party | marketplace app | store-listing | Listing and review requirements; OAuth scopes; install and uninstall smoke |
| assistant_listing | Custom GPT, Claude app or similar assistant-store entry | Assistant store | registry | assistant listing | store-listing | Listing metadata; action and auth boundary; usage read-back |
| container_or_self_hosted | Docker image, Home Assistant add-on or other self-hosted package | Docker Hub, GHCR or release page | registry | container / self-hosted | directory | Tag and digest read-back; upgrade path; health endpoint |
| internal_service | Long-running local or private service with no public listing | None; runs on an owned machine or private host | service_health | internal service | none | Port and PID record; health check; restart owner; conflict check before start |
| other_nonpublic | Any other non-public unit | Recorded per target | first_party | other_nonpublic | none | Prove why each normal overlay is `n/a` |

`Public discoverability: yes` is valid for hosted_web, mcp_server, skill_or_plugin, library_or_sdk, messaging_bot, marketplace_app, assistant_listing and container_or_self_hosted. Store-listed apps and extensions stay `no`; their listing is a presence surface of kind `store-listing`.

## Presence Surfaces

Presence surfaces are rows in the PRD `### Discovery Surfaces` table. The first five kinds attach to a build surface; the last five are platform accounts written as `<platform>:<handle-or-url>`.

| Kind | What it is | Surface cell | Default source roles | Owner stage |
| --- | --- | --- | --- | --- |
| seo-cluster | A group of public pages answering one query cluster | UI surface ID, release target or landing path | search_console | growth |
| geo-page | A citeable page for answer engines | UI surface ID or landing path | production_page, public_serp | growth |
| landing | A public landing path for one action | Landing path | ga4 | growth or gtm |
| store-listing | App, extension, marketplace or assistant store page | Release target ID | app_store_connect, play_console or registry | activation |
| directory | Agent directory, MCP registry, package registry or bot directory entry | Release target ID | registry | activation |
| social | Account on X, Threads, Instagram, Facebook or LinkedIn | `instagram:@handle` | platform_insights | gtm |
| video_channel | YouTube, TikTok or Reels channel | `youtube:@handle` | platform_insights | gtm |
| newsletter | Email list the team can send to | `newsletter:<provider or URL>` | platform_insights | gtm |
| community | Discord, Telegram group, forum or subreddit the team runs | `discord:<invite or name>` | platform_insights | gtm |
| docs_site | Public documentation or README site | `docs:<URL>` | production_page, search_console | growth |

A presence surface needs an owner, a posting or update cadence the team can keep, and one read-back metric. It never proves adoption by itself.

## Source Roles

The closed set for `Source role` in `docs/DEPLOYMENT.md` Measurement Sources:

`search_console`, `ga4`, `production_page`, `google_trends`, `keyword_planner`, `public_serp`, `first_party`, `app_store_connect`, `play_console`, `revenuecat`, `auth_provider`, `crash`, `registry`, `bot_platform`, `platform_insights`, `service_health`.

Resolve the provider for each role from the project's own records: the Measurement Sources table first, then `docs/product/stack-decisions.md`, then the platform default (App Store Connect for ios, Play Console for android, the registry the target publishes to). `revenuecat` is read-only subscription truth when the stack records it; `auth_provider` is whatever the stack decision names, never an assumed vendor.

## Adding A Surface

1. Add one row to the matching table above.
2. Add the class to `SURFACE_CLASSES` in `product-definition-builder/scripts/release_targets.py`, or the kind to `VALID_DISCOVERY_KINDS` in `check_product_package.py`.
3. Add its section to [External Setup](external-setup.md) and, when a source role is new, to the Source Roles list and the Measurement Sources check in `check_deployment.py`.
4. Add its lens to the growth review method when the surface can be read back publicly.

No other file needs a change. A surface that is not in this catalog is not a valid target.
