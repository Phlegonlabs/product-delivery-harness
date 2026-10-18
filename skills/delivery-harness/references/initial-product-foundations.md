# Initial Product Foundations

Plan these foundations during Product Definition for new website and app projects.
Execute them from the first usable implementation build, before the features that depend on them.
Enhancements inspect existing setup and repair only the accepted gaps.
This uses existing stages, TEST obligations and dependency edges; it adds no approval gate or readiness schema.

## Define Before Implementation

Product Definition records the following in existing PRD, architecture and stack sections.
Give required behavior a canonical `TEST-*` obligation and a human owner.
Keep approved alternatives and record explicit non-applicability; never omit a foundation silently.

| Foundation | Initial decision | Initial evidence |
| --- | --- | --- |
| AEO and SEO | Public discovery surfaces, content owner, rendering, crawl/index policy, metadata and canonical URLs | Implemented public-page HTML, crawl controls and metadata match the approved contract |
| Deployment | Provider, account/project owner, candidate and production targets, isolated resources, config placement and recovery | Exact initial build reaches its authorized isolated target; identity, bindings and smoke are read back |
| Google Analytics | GA4 property/stream mapping, applicable Firebase app registration, event definitions, privacy and test-traffic policy | Implemented events reach the intended test destination with correct parameters and no duplicate collection |
| Build access | Selected local/CI toolchain, device/emulator route, source-owned app or bundle IDs, and needed signing preparation | Observed toolchain, target route, owned IDs, and signing path before the first artifact |

AEO means answer-engine discovery of public content. For apps, identify the approved public product or companion-web surface that supplies that content.
Native screens alone cannot satisfy a required AEO outcome. Resolve missing public scope through the existing app-and-companion-web contract before implementation.
Private surfaces stay private. App-store optimization is separate; no new website or store publication is authorized by this reference.
Use crawlable useful text, clear product facts, internal links, accurate route metadata and applicable structured data matching visible content.
Define crawler access separately from model-training permission. Preview remains access-controlled or non-indexable under the product's environment policy.
Google's AI search features require the normal search foundations, not a new mandatory AI file or special schema.
No foundation check promises indexing, citations or ranking. See [Google AI search guidance](https://developers.google.com/search/docs/appearance/ai-features) and [OpenAI crawler controls](https://developers.openai.com/api/docs/bots).

Include Google Analytics in initial website/mobile-app setup, subject to the existing Stack Decision Checkpoint and product privacy decisions.
Preserve an already approved alternative or a reasoned no-collection requirement.
Web uses its intended GA4 Web stream and one tag owner. Applicable iOS/Android builds use Firebase/native SDK integration for the selected stack.
Record each product/environment mapping explicitly; never mix unrelated products or send test traffic to production measurement.
Define key events, parameters, collection controls, personal-data exclusions, duplicate prevention and performance obligations before dependent feature implementation.
Search Console property verification belongs to public discovery setup when applicable; indexing and production search results remain later observations.
See [GA4 setup](https://support.google.com/analytics/answer/9304153) and [Firebase event validation](https://firebase.google.com/docs/analytics/debugview).

Pre-build work is planning plus observed local facts. External provisioning needed to create the first artifact is a separately authorized operator/provider prerequisite outside Harness/RUN.
That prerequisite does not become setup evidence and does not require paid distribution membership for every local experiment.

## Execute From A Fixed Initial Build

1. Reuse approved product, stack and applicable design inputs. Implement the smallest usable scaffold, metadata, configuration declarations and measurement hooks.
2. Commit and identify its actual SHA and platform artifact/build. Respect the approved platform order and mandatory frontend ownership.
3. Reconcile `docs/DEPLOYMENT.md` from tracked declarations. Keep names, placements, isolation and console prerequisites there, without secret values or duplicate action authority.
4. Separately invoke `product-activation` preparation for that fixed build. It owns account probes, `ACT-*` grants, setup, independent read-back and behavior evidence.
5. Perform deployment/bootstrap only through its separately authorized operator/provider route under [Deployment Contract](deployment-contract.md). Harness and RUN gain no deployment authority.
6. Resume each dependent feature when its own required setup has verified evidence. Continue independent work during access, DNS or unavailable-platform blockers.

For approved Cloudflare projects, configure the existing Workers Preview or approved alternative before dependent features need deployment.
Set up the repository/build path, non-production bindings, required variables/secrets and production placement plan using the existing platform procedure.
Verify one authorized initial deployment and smoke. Keep production traffic, schema changes and main promotion separately authorized.
A production Worker Version URL does not prove resource isolation.
Follow the pinned Wrangler or Void route; do not add another deployment mechanism.
See [Workers Preview setup](https://developers.cloudflare.com/workers/previews/get-started/) and [resource isolation](https://developers.cloudflare.com/workers/previews/resources/).

Property creation is only configuration. Verify implemented hooks in the appropriate debug/realtime view and exercise the approved collection controls.
Keep final feature events, production measurement and search availability pending until their implementation and release can be observed.
Record setup progress in existing Activation tasks and deployment evidence; no second setup checklist or review wave is required.

Before external trials, use one scoped support inbox, form, or named interview route and name its owner.
Keep one test report joined to the tested build and context, with the product's privacy controls applied. No feedback vendor or new tracker is required.

## Preserve Incomplete Preparation

Early setup never becomes `handoff_ready` by renaming a preparation result.
Run the existing Activation checks and terminal closeout; retain actual findings and blocked status while final obligations remain.
A required final-release verification action stays concretely blocked when its prerequisites are absent; a blocker row alone cannot replace that action.
Use only real available build bindings. In a Web-first hybrid, keep unavailable native artifacts pending instead of borrowing the Web artifact.
Pending future bindings can prevent filled validation or closeout. Report that preparation as incomplete and preserve the same staged record for resumption.
This blocks only work that needs those missing prerequisites, not independent product or design work.

At release, read back existing objects before creating anything. Reuse their identities, then rebind and reverify the actual released SHA/artifact.
Earlier behavior evidence and action digests do not transfer to a changed build.
Activation alone verifies final readiness and measurement sources; later SEO and outcome reviews consume their applicable live evidence.

Official provider guidance checked on 2026-10-18; refresh relevant documentation when executing provider setup.
