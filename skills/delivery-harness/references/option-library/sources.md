# 來源索引

Reference only · 查閱日期：2026-09-25

2026-10-02 增補的來源按下方領域標示；原有條目不因本輪增補而取得新的查核日期。

此處按領域列出最終稿引用的官方來源。連結支持其附近的能力敘述，不能擴大成整個產品已驗證。適配、成本、遷移與情境組合是研究判斷。

本次以官方文件為主；沒有把搜尋排行當推薦順序。數值配額、價格、license、SDK/框架支援與帳號權限採用時再核對。

## 來源狀態與限制

- 主要方案的基本定位已取得官方正文；正文範圍以各文件引用為準。
- Nuxt rendering 有官方搜尋摘要，直接 markdown 取回失敗。
- Fly Machines 本次可用正文不足；仍是候選入口。Phosphor 已在後續擴充補查官方 React repository；具體授權與採用版本仍需核對。
- Sentry 主文件抓取受限，舊官方 PDF 只支持方向，未證明最新 SDK 與方案。
- Apple HIG 有官方搜尋內容，但部分直接頁面只有 metadata；本版不將 iOS 細節當已完成實測。
- Taste 與 GPT Taste 來自本地 skill 內容，是設計方法來源，不是標準或自動執行指令。

各領域文件中的待驗證行保留本輪查閱限制；未取得正文的入口仍只是候選來源，不是完成驗證的證據。

## [ai-agentic.md](ai-agentic.md)

- [官方來源：developers.cloudflare.com — agents/concepts/workflows/](https://developers.cloudflare.com/agents/concepts/workflows/)
- [官方來源：developers.cloudflare.com — workflows/](https://developers.cloudflare.com/workflows/)
- [官方來源：docs.langchain.com — oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [官方來源：docs.temporal.io — workflow-execution](https://docs.temporal.io/workflow-execution)
- [官方來源：openai.github.io — openai-agents-python/](https://openai.github.io/openai-agents-python/)
- [官方來源：openai.github.io — openai-agents-python/human_in_the_loop/](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- [官方來源：openai.github.io — openai-agents-python/ref/run_state/](https://openai.github.io/openai-agents-python/ref/run_state/)
- [官方來源：openai.github.io — openai-agents-python/running_agents/](https://openai.github.io/openai-agents-python/running_agents/)

## [api.md](api.md)

- [官方來源：developer.mozilla.org — en-US/docs/Web/API/Server-sent_events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [官方來源：developer.mozilla.org — en-US/docs/Web/API/WebSockets_API](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
- [官方來源：graphql.org — learn/](https://graphql.org/learn/)
- [官方來源：grpc.io — docs/what-is-grpc/introduction/](https://grpc.io/docs/what-is-grpc/introduction/)
- [官方來源：spec.openapis.org — oas/latest.html](https://spec.openapis.org/oas/latest.html)
- [官方來源：trpc.io — docs/](https://trpc.io/docs/)

## [architecture.md](architecture.md)

2026-10-02 完整組合的官方定位來源：[TanStack Start](https://tanstack.com/start/latest)、[Next.js](https://nextjs.org/docs)、[Vercel Next.js](https://vercel.com/docs/frameworks/nextjs)、[Supabase](https://supabase.com/docs)、[React Router framework mode](https://reactrouter.com/start/framework/installation)、[Astro islands](https://docs.astro.build/en/concepts/islands/)、[Nuxt rendering](https://nuxt.com/docs/4.x/guide/concepts/rendering)、[SvelteKit](https://svelte.dev/docs/kit/introduction)、[Convex](https://docs.convex.dev/quickstarts)、[FastAPI](https://fastapi.tiangolo.com/features/)、[Rails](https://rubyonrails.org/)、[Django](https://docs.djangoproject.com/en/stable/intro/overview/)、[Laravel](https://laravel.com/docs)。組合本身與產品適配是研究判斷，未在本輪建立或部署。

2026-10-02 架構能力增補：

- [htmx](https://htmx.org/docs/)：HTML request／response 與局部 DOM 更新；backend、auth、樣式與 fallback 義務由專案決定。
- [PowerSync overview](https://docs.powersync.com/intro/powersync-overview)：client SQLite、sync service、資料分配和 SDK。嘗試的 `/architecture/overview` 入口取回失敗，已改讀此官方 overview；未核對完整 SDK／DB／host 版本矩陣。
- [Temporal workflow execution](https://docs.temporal.io/workflow-execution)：event history／replay；不以此證明外部副作用 exactly-once。
- [Microsoft multitenant storage](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data)：共用／獨立／混合資料拓撲、restore 和 migration 取捨；Azure 實作另行核對。
- [Payload Live Preview](https://payloadcms.com/docs/live-preview/overview) 與 [Shopify cart/checkout](https://shopify.dev/docs/storefronts/headless/building-with-the-storefront-api/cart/manage)：frontend preview 與 cart／checkout 邊界；沒有驗證兩者的組合或商務方案。
- [Hono RPC](https://hono.dev/docs/guides/rpc)：TypeScript input/output type sharing 與 validator；跨語言公開 API 仍需其明確契約。

來源支持各工具定位；需求適配、組合、negative cases 和退出成本是本輪研究判斷。未做安裝、帳號、benchmark、價格、license、完整相容矩陣或部署驗證。

- [官方來源：learn.microsoft.com — en-gb/azure/architecture/guide/architecture-styles/](https://learn.microsoft.com/en-gb/azure/architecture/guide/architecture-styles/)
- [官方來源：learn.microsoft.com — en-us/azure/architecture/guide/architecture-styles/event-driven](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven)
- [官方來源：learn.microsoft.com — en-us/azure/architecture/guide/architecture-styles/web-queue-worker](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker)
- [官方來源：learn.microsoft.com — en-us/azure/architecture/patterns/backends-for-frontends](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends)
- [官方來源：learn.microsoft.com — en-us/azure/architecture/patterns/cqrs](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)

## [authentication-and-identity.md](authentication-and-identity.md)

- [官方來源：auth0.com — docs/get-started](https://auth0.com/docs/get-started)
- [官方來源：auth0.com — docs/libraries/auth0js](https://auth0.com/docs/libraries/auth0js)
- [官方來源：authjs.dev — ](https://authjs.dev/)
- [官方來源：authjs.dev — getting-started](https://authjs.dev/getting-started)
- [官方來源：better-auth.com — docs/introduction](https://better-auth.com/docs/introduction)
- [官方來源：clerk.com — docs](https://clerk.com/docs)
- [官方來源：clerk.com — docs/guides/organizations/overview](https://clerk.com/docs/guides/organizations/overview)
- [官方來源：firebase.google.com — docs/auth](https://firebase.google.com/docs/auth)
- [官方來源：supabase.com — docs/guides/auth](https://supabase.com/docs/guides/auth)
- [官方來源：supabase.com — docs/guides/auth/social-login/auth-keycloak](https://supabase.com/docs/guides/auth/social-login/auth-keycloak)
- [官方來源：supabase.com — docs/guides/auth/third-party/overview](https://supabase.com/docs/guides/auth/third-party/overview)
- [官方來源：www.keycloak.org — ](https://www.keycloak.org/)
- [官方來源：www.keycloak.org — guides](https://www.keycloak.org/guides)

## [backend.md](backend.md)

- [官方來源：docs.djangoproject.com — en/5.2/intro/overview/](https://docs.djangoproject.com/en/5.2/intro/overview/)
- [官方來源：docs.nestjs.com — ](https://docs.nestjs.com/)
- [官方來源：fastapi.tiangolo.com — features/](https://fastapi.tiangolo.com/features/)
- [官方來源：go.dev — doc/](https://go.dev/doc/)
- [官方來源：hono.dev — docs](https://hono.dev/docs)
- [官方來源：learn.microsoft.com — en-us/aspnet/core/introduction-to-aspnet-core](https://learn.microsoft.com/en-us/aspnet/core/introduction-to-aspnet-core)
- [官方來源：learn.microsoft.com — en-us/aspnet/core/overview?view=aspnetcore-10.0](https://learn.microsoft.com/en-us/aspnet/core/overview?view=aspnetcore-10.0)

## [components-icons.md](components-icons.md)

2026-10-02 增補：[React Aria](https://react-aria.adobe.com/getting-started)、[Mantine](https://mantine.dev/getting-started/)、[Nuxt UI](https://ui.nuxt.com/)、[shadcn-svelte](https://www.shadcn-svelte.com/docs/installation)。新項目只核對基本定位與官方入口；實際 peer dependencies、授權、樣式、SSR 與 framework 版本在採納時驗證。

- [官方來源：21st.dev — ](https://21st.dev/)
- [官方來源：ant.design — docs/react/introduce/](https://ant.design/docs/react/introduce/)
- [官方來源：base-ui.com — react/overview/about](https://base-ui.com/react/overview/about)
- [官方來源：base-ui.com — react/overview/accessibility](https://base-ui.com/react/overview/accessibility)
- [官方來源：chakra-ui.com — docs/get-started/installation](https://chakra-ui.com/docs/get-started/installation)
- [官方來源：lucide.dev — guide/](https://lucide.dev/guide/)
- [官方來源：mui.com — material-ui/getting-started/](https://mui.com/material-ui/getting-started/)
- [官方來源：mui.com — x/introduction/](https://mui.com/x/introduction/)
- [官方來源：phosphoricons.com — ](https://phosphoricons.com/)
- [官方來源：tailwindcss.com — docs/styling-with-utility-classes](https://tailwindcss.com/docs/styling-with-utility-classes)
- [官方來源：ui.shadcn.com — docs](https://ui.shadcn.com/docs)
- [官方來源：v2.chakra-ui.com — ](https://v2.chakra-ui.com/)
- [官方來源：www.radix-ui.com — primitives/docs/overview/introduction](https://www.radix-ui.com/primitives/docs/overview/introduction)
- [官方來源：www.w3.org — WAI/WCAG22/Understanding/target-size-minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)

## [data-storage.md](data-storage.md)

- [官方來源：developers.cloudflare.com — d1/](https://developers.cloudflare.com/d1/)
- [官方來源：docs.aws.amazon.com — AmazonS3/latest/userguide/Welcome.html](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [官方來源：redis.io — docs/latest/develop/data-types/compare-data-types/](https://redis.io/docs/latest/develop/data-types/compare-data-types/)
- [官方來源：www.mongodb.com — docs/atlas/atlas-ui/data-modeling/](https://www.mongodb.com/docs/atlas/atlas-ui/data-modeling/)
- [官方來源：www.mongodb.com — docs/relational-migrator/mapping-rules/introduction/](https://www.mongodb.com/docs/relational-migrator/mapping-rules/introduction/)
- [官方來源：www.mongodb.com — docs/v8.0/data-modeling/concepts/](https://www.mongodb.com/docs/v8.0/data-modeling/concepts/)
- [官方來源：www.mongodb.com — docs/v8.0/data-modeling/schema-design-process/](https://www.mongodb.com/docs/v8.0/data-modeling/schema-design-process/)
- [官方來源：www.mongodb.com — docs/v8.0/reference/bson-types/](https://www.mongodb.com/docs/v8.0/reference/bson-types/)
- [官方來源：www.mongodb.com — docs/v8.2/data-modeling/design-patterns/polymorphic-data/polymorphic-schema-pattern/](https://www.mongodb.com/docs/v8.2/data-modeling/design-patterns/polymorphic-data/polymorphic-schema-pattern/)
- [官方來源：www.postgresql.org — docs/current/tutorial.html](https://www.postgresql.org/docs/current/tutorial.html)
- [官方來源：www.sqlite.org — whentouse.html](https://www.sqlite.org/whentouse.html)

## [deployment.md](deployment.md)

- [官方來源：developers.cloudflare.com — workers/platform/limits/](https://developers.cloudflare.com/workers/platform/limits/)
- [官方來源：developers.cloudflare.com — workers/runtime-apis/nodejs/](https://developers.cloudflare.com/workers/runtime-apis/nodejs/)
- [官方來源：docs.aws.amazon.com — AmazonECS/latest/developerguide/Welcome.html](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
- [官方來源：docs.netlify.com — build/functions/configuration/](https://docs.netlify.com/build/functions/configuration/)
- [官方來源：fly.io — docs/machines/](https://fly.io/docs/machines/)
- [官方來源：render.com — docs/background-workers](https://render.com/docs/background-workers)
- [官方來源：vercel.com — docs/functions](https://vercel.com/docs/functions)
- [官方來源：vercel.com — docs/functions/limitations](https://vercel.com/docs/functions/limitations)

2026-10-16 Void 官方頁面查核：[quickstart](https://void.cloud/guide/quickstart)、[coding agents](https://void.cloud/integrations/agents)、[meta-framework overview](https://void.cloud/integrations/frameworks/overview)、[project setup CLI](https://void.cloud/reference/cli/setup)、[deploy CLI](https://void.cloud/reference/cli/deploy)、[Cloudflare integration](https://void.cloud/integrations/cloudflare)、[deployment guide](https://void.cloud/guide/deployment)、[project structure](https://void.cloud/reference/structure)。來源支持 SDK／CLI、framework mode、auth 限制、direct Cloudflare 行為、generated `.void/`／`.void-wrangler.jsonc` 邊界與 rollback；未驗證帳號、pricing 或實際部署。

## [design.md](design.md)

2026-10-02 發布者入口：[Mobbin](https://mobbin.com/)、[Dribbble](https://dribbble.com/)、[Awwwards](https://www.awwwards.com/websites/)、[Refero](https://refero.design/)、[MotionSites](https://motionsites.ai/)。這次核對來源用途，沒有替任何個別作品做視覺／操作驗收。MotionSites 網址由名稱暫定，沒有宣稱 owner 已確認。制度型設計參考：[Material 3](https://m3.material.io/)、[Fluent 2](https://fluent2.microsoft.design/)、[Carbon](https://carbondesignsystem.com/)。八種方向為本輪研究判斷，不是官方分類。

- [官方來源：base-ui.com — react/overview/about](https://base-ui.com/react/overview/about)
- [官方來源：base-ui.com — react/overview/accessibility](https://base-ui.com/react/overview/accessibility)
- [官方來源：developer.android.com — develop/adaptive-apps/guides/canonical-layouts?hl=en](https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts?hl=en)
- [官方來源：developer.android.com — develop/adaptive-apps/guides/use-window-size-classes?authuser=19&hl=en](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes?authuser=19&hl=en)
- [官方來源：developer.apple.com — design/human-interface-guidelines/motion](https://developer.apple.com/design/human-interface-guidelines/motion)
- [官方來源：mui.com — material-ui/getting-started/](https://mui.com/material-ui/getting-started/)
- [官方來源：mui.com — x/introduction/](https://mui.com/x/introduction/)
- [官方來源：tailwindcss.com — docs/styling-with-utility-classes](https://tailwindcss.com/docs/styling-with-utility-classes)
- [官方來源：ui.shadcn.com — docs](https://ui.shadcn.com/docs)
- [官方來源：www.radix-ui.com — primitives/docs/overview/introduction](https://www.radix-ui.com/primitives/docs/overview/introduction)
- [官方來源：www.w3.org — WAI/WCAG22/Understanding/target-size-minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)

## [frontend.md](frontend.md)

2026-10-02：TanStack 的 [Start 及官方 library 導覽](https://tanstack.com/start/latest) 支持 18 項 library 與 Starter／Builder 的目錄觀察。各項細節、成熟度與安裝入口直接連在 frontend 矩陣，採納時逐項回查；不將一項已核對的能力擴大成整套已驗證。另見 [React Router framework mode](https://reactrouter.com/start/framework/installation)。

- [官方來源：docs.astro.build — en/concepts/islands/](https://docs.astro.build/en/concepts/islands/)
- [官方來源：nextjs.org — docs](https://nextjs.org/docs)
- [官方來源：nuxt.com — docs/4.x/guide/concepts/rendering](https://nuxt.com/docs/4.x/guide/concepts/rendering)
- [官方來源：react.dev — learn](https://react.dev/learn)
- [官方來源：react.dev — learn/add-react-to-an-existing-project](https://react.dev/learn/add-react-to-an-existing-project)
- [官方來源：react.dev — learn/build-a-react-app-from-scratch](https://react.dev/learn/build-a-react-app-from-scratch)
- [官方來源：react.dev — learn/installation](https://react.dev/learn/installation)
- [官方來源：svelte.dev — docs/kit/introduction](https://svelte.dev/docs/kit/introduction)

## [integrations.md](integrations.md)

- [官方來源：developers.cloudflare.com — queues/](https://developers.cloudflare.com/queues/)
- [官方來源：docs.n8n.io — ](https://docs.n8n.io/)
- [官方來源：docs.stripe.com — webhooks](https://docs.stripe.com/webhooks)
- [官方來源：docs.svix.com — introduction](https://docs.svix.com/introduction)
- [官方來源：resend.com — docs/introduction](https://resend.com/docs/introduction)

## [motion.md](motion.md)

2026-10-02 增補：[React Bits index](https://www.reactbits.dev/get-started/index)、[Anime.js](https://animejs.com/) 及 [官方文件](https://animejs.com/documentation)、[MotionSites](https://motionsites.ai/)。分開動效元件、動畫引擎與案例／prompt；本輪不核准元件 license、下載、安裝或個別示範品質。

- [官方來源：developer.mozilla.org — en-US/docs/Web/API/Web_Animations_API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)
- [官方來源：developers.lottiefiles.com — ](https://developers.lottiefiles.com/)
- [官方來源：github.com — mrdoob/three.js](https://github.com/mrdoob/three.js)
- [官方來源：gsap.com — docs/v3/](https://gsap.com/docs/v3/)
- [官方來源：gsap.com — docs/v3/Plugins/ScrollTrigger/](https://gsap.com/docs/v3/Plugins/ScrollTrigger/)
- [官方來源：motion.dev — docs/quick-start](https://motion.dev/docs/quick-start)
- [官方來源：motion.dev — docs/react](https://motion.dev/docs/react)
- [官方來源：motion.dev — docs/react-accessibility](https://motion.dev/docs/react-accessibility)
- [官方來源：r3f.docs.pmnd.rs — getting-started/introduction](https://r3f.docs.pmnd.rs/getting-started/introduction)
- [官方來源：rive.app — docs/runtimes](https://rive.app/docs/runtimes)

## [operations.md](operations.md)

- [官方來源：opentelemetry.io — docs/concepts/observability-primer/](https://opentelemetry.io/docs/concepts/observability-primer/)
- [官方來源：opentelemetry.io — docs/concepts/signals/](https://opentelemetry.io/docs/concepts/signals/)
- [官方來源：prometheus.io — docs/introduction/overview/](https://prometheus.io/docs/introduction/overview/)
- [官方來源：sre.google — sre-book/service-level-objectives/](https://sre.google/sre-book/service-level-objectives/)

## [runtime-selection.md](runtime-selection.md)

- [官方來源：bun.com — docs/runtime](https://bun.com/docs/runtime)
- [官方來源：developers.cloudflare.com — workers/configuration/compatibility-flags/](https://developers.cloudflare.com/workers/configuration/compatibility-flags/)
- [官方來源：developers.cloudflare.com — workers/platform/limits/](https://developers.cloudflare.com/workers/platform/limits/)
- [官方來源：developers.cloudflare.com — workers/runtime-apis/nodejs/](https://developers.cloudflare.com/workers/runtime-apis/nodejs/)
- [官方來源：docs.deno.com — runtime/](https://docs.deno.com/runtime/)
- [官方來源：nodejs.org — learn/getting-started/introduction-to-nodejs](https://nodejs.org/learn/getting-started/introduction-to-nodejs)

## [security.md](security.md)

- [官方來源：cheatsheetseries.owasp.org — cheatsheets/Authorization_Cheat_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [官方來源：cheatsheetseries.owasp.org — cheatsheets/Mobile_Application_Security_Cheat_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/Mobile_Application_Security_Cheat_Sheet.html)
- [官方來源：cheatsheetseries.owasp.org — cheatsheets/OAuth2_Cheat_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
- [官方來源：cornucopia.owasp.org — cards/AA4](https://cornucopia.owasp.org/cards/AA4)
- [官方來源：devguide.owasp.org — en/03-requirements/04-security-rat/](https://devguide.owasp.org/en/03-requirements/04-security-rat/)
- [官方來源：devguide.owasp.org — en/07-training-education/07-api-top-ten/](https://devguide.owasp.org/en/07-training-education/07-api-top-ten/)
- [官方來源：owasp.org — API-Security/](https://owasp.org/API-Security/)
- [官方來源：owasp.org — projects/asvs](https://owasp.org/projects/asvs)

## [testing-acceptance.md](testing-acceptance.md)

- [官方來源：appium.io — docs/en/latest/](https://appium.io/docs/en/latest/)
- [官方來源：docs.maestro.dev — maestro-cli](https://docs.maestro.dev/maestro-cli)
- [官方來源：docs.pytest.org — en/stable/](https://docs.pytest.org/en/stable/)
- [官方來源：grafana.com — docs/k6/latest/](https://grafana.com/docs/k6/latest/)
- [官方來源：playwright.dev — ](https://playwright.dev/)
- [官方來源：playwright.dev — docs/next/intro](https://playwright.dev/docs/next/intro)
- [官方來源：playwright.dev — docs/next/library](https://playwright.dev/docs/next/library)
- [官方來源：playwright.dev — docs/test-assertions](https://playwright.dev/docs/test-assertions)
- [官方來源：vitest.dev — guide/](https://vitest.dev/guide/)

## CSS、Icon 與 Cloudflare 擴充（2026-09-25）

本輪官方頁面查閱支持文內基本能力；使用條件、成本與遷移分析是研究判斷。套件授權／帳號方案／相容性仍需採用時核對。Phosphor 本輪補讀官方 React repository，取代先前只有首頁 metadata 的限制。

### [css-styling.md](css-styling.md)

- [bulma.io — 官方文件](https://bulma.io/documentation/)
- [developer.mozilla.org — 官方文件](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [getbootstrap.com — 官方文件](https://getbootstrap.com/docs/5.3/getting-started/introduction/)
- [github.com — 官方文件](https://github.com/css-modules/css-modules)
- [panda-css.com — 官方文件](https://panda-css.com/docs/overview/getting-started)
- [picocss.com — 官方文件](https://picocss.com/docs)
- [sass-lang.com — 官方文件](https://sass-lang.com/guide/)
- [tailwindcss.com — 官方文件](https://tailwindcss.com/docs/styling-with-utility-classes)
- [unocss.dev — 官方文件](https://unocss.dev/)
- [vanilla-extract.style — 官方文件](https://vanilla-extract.style/)

### [icon-systems.md](icon-systems.md)

- [developer.apple.com — 官方文件](https://developer.apple.com/sf-symbols/)
- [developers.google.com — 官方文件](https://developers.google.com/fonts/docs/material_symbols)
- [docs.tabler.io — 官方文件](https://docs.tabler.io/icons)
- [github.com — 官方文件](https://github.com/phosphor-icons/react)
- [heroicons.com — 官方文件](https://heroicons.com/)
- [lucide.dev — 官方文件](https://lucide.dev/guide/)

### [cloudflare-platform.md](cloudflare-platform.md)

2026-10-02 開發平台增補定位：[官方目錄](https://developers.cloudflare.com/directory/)、[AI Gateway](https://developers.cloudflare.com/ai-gateway/)、[AI Search](https://developers.cloudflare.com/ai-search/)、[Agents](https://developers.cloudflare.com/agents/)、[MCP handler APIs](https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/)、[Browser Run](https://developers.cloudflare.com/browser-run/)、[Sandboxes](https://developers.cloudflare.com/sandbox/)、[Containers](https://developers.cloudflare.com/containers/)、[Email Service](https://developers.cloudflare.com/email-service/)、[Images](https://developers.cloudflare.com/images/)、[Stream](https://developers.cloudflare.com/stream/)、[Basin](https://developers.cloudflare.com/basin/)、[K2](https://developers.cloudflare.com/k2/)、[Artifacts](https://developers.cloudflare.com/artifacts/)、[Cache API](https://developers.cloudflare.com/workers/runtime-apis/cache/)、[Analytics Engine](https://developers.cloudflare.com/analytics/analytics-engine/)、[Observability](https://developers.cloudflare.com/workers/observability/)、[Pages](https://developers.cloudflare.com/pages/)。各自支持正文的定位，未完成帳號或部署驗證。

當日成熟度／遷移：[Artifacts open beta changelog](https://developers.cloudflare.com/changelog/product/artifacts/)、[deprecated McpAgent](https://developers.cloudflare.com/agents/model-context-protocol/apis/agent-api/)、[cf beta](https://developers.cloudflare.com/cf/)。框架／工具：[TanStack Start on Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/tanstack-start/)、[Vite plugin](https://developers.cloudflare.com/workers/vite-plugin/)、[Next.js on Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/)、[vinext compatibility and Agent Skill](https://github.com/cloudflare/vinext)、[Cloudflare Skills inventory](https://github.com/cloudflare/skills)。Sandbox 官方概覽與 skills 的 preview／stable 用語需採用時再比對；upstream 列表不證明本機 loaded 內容相同。

- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/cloudflare-one/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/d1/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/durable-objects/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/hyperdrive/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/kv/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/kv/concepts/how-kv-works/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/queues/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/r2/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/turnstile/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/vectorize/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/workers-ai/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/workers/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/workers/static-assets/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/workers/wrangler/)
- [developers.cloudflare.com — 官方文件](https://developers.cloudflare.com/workflows/)
