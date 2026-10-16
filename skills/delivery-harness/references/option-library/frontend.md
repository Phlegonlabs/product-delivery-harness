# 前端框架參考（Reference only）

狀態：Reference only · 核對日期：2026-09-25 · 本文件只供比較，不自動採用、不安裝、不改變現有流程。所有外部參照都是可選建議；採納後才由專案決策與驗收約束。

## PRD 應先回答的問題

- 產品是內容站、登入後應用、混合式網站，還是既有系統中的一小塊互動？
- 需要哪些渲染模式：靜態、單頁、伺服器渲染、按路由混合，或原生 App？
- 目標平台與部署限制是什麼？是否需要自架、託管平台、Node/邊緣 runtime 或靜態輸出？
- 團隊熟悉 React、Vue、Svelte 哪一種？既有元件、測試、CMS、API 與樣式系統能否保留？
- 效能預算、SEO、多語系、可及性、離線、行為埋點與錯誤監控分別要達到什麼程度？

## 候選比較矩陣

| 候選 | 定位 | 適合 | 避免條件 | 架構與整合義務 | 營運／成本／鎖定 | 遷移或退場 |
| --- | --- | --- | --- | --- | --- | --- |
| Next.js | React 全端應用框架 | 需要 React、伺服器渲染、路由與資料整合 | 純靜態小型站或團隊不想承擔 App Router 升級語意 | 核對 App Router／Pages Router、React 版本、快取、Server/Client 邊界與部署 adapter | runtime、快取儲存與平台整合會影響維運成本；避免只綁單一託管假設 | 保留資料層與 UI 元件邊界，降低框架耦合 |
| TanStack Start | 基於 TanStack Router 的全端 React／Solid 框架 | 型別化路由、SSR、streaming、server functions 與互動型應用 | 查核時為 RC；產品不能承受其升級或目標 adapter 尚未驗證 | 分開路由 loader、server functions、外部 API、session、mutation 與資料快取；核對 runtime/build | auth、DB、jobs、UI foundation 和 host 仍要選；Start 不等於完整雲端 stack | 保留服務與資料契約，先測代表性路由再遷移 |
| React Router framework mode | React 的 framework／data／declarative 分層路線 | loader/action、SSR、表單與路由模組 | 把單純 router 誤當完整 framework，或部署路線未驗證 | 明確選 mode，核對 rendering、session、actions、pending/error 和 host adapter | 自管 Node 或相容平台各有維運責任；資料與 auth 不隨路由自動提供 | 保留 route/data 契約，逐路由替换與回歸 |
| Astro islands | 靜態內容與局部互動島架構 | 多數內容頁、少量互動、重視初始載入 | 每頁都是高度狀態化應用，或島嶼間大量即時共享狀態 | 確認互動島、資料取得、session、表單、部署 adapter 與 所選樣式載入 | 內容主體可靜態化，但互動與動態路由仍需維運 | 互動元件若用框架元件撰寫，可評估逐島遷移 |
| Nuxt/Vue | Vue 生態的全端框架候選 | 團隊已有 Vue、需要路由與伺服器整合 | 生態套件、版本或部署 adapter 尚未核對 | Nuxt 官方渲染指南列出 universal、client-side 與 hybrid rendering；需核對路由規則、Nitro 目標、狀態與資料策略 | 成本來自 runtime、建置、監控與生態維護 | 用標準 Vue 元件與 API 合約降低鎖定 |
| SvelteKit | Svelte 生態的全端框架候選 | 團隊偏好 Svelte、需要應用級路由 | 元件庫、測試與部署路徑未核對 | SvelteKit 提供 routing、SSR 與部署 adapters；需選擇目標 adapter 並區分 server/client 資料 | 需自訂建置與觀測；避免把生態成熟度當成既成事實 | 以路由資料契約與伺服器 API 為邊界 |
| React + Vite SPA | 官方說明的從零建置路徑之一 | 既有後端穩定、只需互動前端、團隊能自組路由與資料 | 未來需要 SSR、SSG、RSC 或更多框架級整合 | 自行補 routing、資料取得、快取、程式碼切割、錯誤與狀態管理 | Vite、Parcel、Rsbuild 都可作為建置工具；成本轉為自管生態 | SPA 可放在既有頁面或子路徑，但不要清除宿主 HTML |
| Server templates＋htmx | Server-driven HTML 與局部互動組合 | 表單／後台、server 持有主要 state | 離線 editor、canvas 或大量 client state 未驗證 | backend 產生頁面／fragment；htmx 提供請求／DOM 更新；保留 session、CSRF、焦點與快取責任 | server app、SQL 和需要時的 jobs 各有成本；不因省去 SPA 就免除可及性測試 | templates／fragment 與 interaction attributes 需改寫；保留 domain/API 邊界 |
| 既有前端／原生替代 | 保留可維護系統，或另選原生／跨平台方案 | 既有棧健康、需求局部；目標是 iOS/Android 原生體驗 | 因新框架流行而整站重寫 | 先定義整合點、資料契約、樣式、測試與回滾 | 保留既有投資；原生需求必須另行評估工具鏈 | 局部新增、擴充或漸進替換，不做未核對的全域遷移 |

## 事實與推論界線

事實：React 官方說明從零建置可用 Vite、Parcel 或 Rsbuild，但這類 SPA 預設不含 routing、資料取得與樣式方案；若未來需要 SSR、SSG 或 React Server Components，會變成自行承擔框架級問題。React 也支援漸進採用、加入既有頁面，並已淘汰 Create React App。Next.js 官方定義為 React 全端 Web 應用框架，提供 App Router 與 Pages Router；App Router 使用內建 React canary，Pages Router 使用專案宣告的 React 版本。

推論：內容多、互動少時，Astro islands 值得列入；登入後互動與伺服器整合時，Next.js、Nuxt 或 SvelteKit 更值得比較。這些適配判斷不是官方聲明。補查 SvelteKit 正文、Astro islands 與 Nuxt 官方渲染搜尋摘要後，可確認上述基本定位；實際版本與 adapter 相容性仍需專案驗證。

上述 server-driven HTML 組合於 2026-10-02 補查：[htmx 官方文件](https://htmx.org/docs/) 說明以 HTML 元素發送請求、通常取得 HTML response 更新 DOM。Django templates＋htmx＋PostgreSQL 是比較示例，適配為研究判斷；htmx 不決定 backend、資料庫或樣式。完整責任與 negative cases 見 [Architecture](architecture.md)。

## Void 全端 SDK（2026-10-16 增補）

[Void](https://void.cloud/guide/quickstart) 是專案本機的 SDK／CLI，不取代 Stack Decision Checkpoint。它可同時觸及 rendering、routing、backend、deployment 與 build-tool 層；Vite+ 是其預設 build context，但不是自動採用 Vite+ 全套工具的理由。

Native Void 模式可提供 own routing、server loaders、actions 與 rendering。Framework 模式保留 TanStack Start、React Router、SvelteKit、Nuxt、Analog 或 Astro 既有的 routing 與 rendering，只加入資料、bindings、jobs 與 deployment。既有核准的 framework routing 權威不因加入 Void 改變。

Auth 是另一層決策。官方 framework 說明目前指出 framework mode 尚無 Void-managed auth，並描述使用該框架的 Better Auth 整合；這不是核准新的 auth provider，也不能取代專案既有核准 auth。

適合條件是產品確實需要整合的 Workers backend、storage、jobs 與 Cloudflare deployment，且團隊接受 package／CLI 版本一致與 init／deploy 的 diff review。避免條件是健康前端棧只需 build tool、目標 framework 未獲官方支援，或只想省略 routing／auth／資料決策。採納前先檢查 [framework overview](https://void.cloud/integrations/frameworks/overview)、[agents](https://void.cloud/integrations/agents) 與 [Cloudflare](https://void.cloud/integrations/cloudflare)。

## TanStack 生態分工（2026-10-02 增補）

[官方目錄](https://tanstack.com/start/latest) 查核時列出以下 18 項 library，以及 Application Starter／Builder 工具。這是按需求選用的模組群；使用 Start 不要求全套安裝，使用 Query／Table 也不要求換成 Start。用途摘要用來比較，版本、framework adapter、成熟度、授權與安裝命令以每項當時文件為準。

| 官方入口 | 分工與何時評估 | 專案需要補齊的責任 |
| --- | --- | --- |
| [Start](https://tanstack.com/start/latest) | 全端路由、SSR、server functions；查核時 RC | 目標部署、auth、DB、jobs、錯誤與快取邊界 |
| [Router](https://tanstack.com/router/latest) | 型別化路由、URL/search state、route loaders | route schema、權限、pending/error、深連結與 code splitting |
| [Query](https://tanstack.com/query/latest) | server-state 取得、快取、mutation | query keys、失效、重試、SSR hydration、租戶與登入切換；不是全域 UI state |
| [Table](https://tanstack.com/table/latest) | headless 表格行為 | markup、樣式、鍵盤、排序／篩選、server pagination；不附帶完整視覺 UI |
| [Virtual](https://tanstack.com/virtual/latest) | 長列表／網格的虛擬化 | item sizing、scroll restore、screen reader、列焦點與空狀態 |
| [Form](https://tanstack.com/form/latest) | 表單 state 與驗證協作 | server validation、錯誤回饋、提交權限與可及性 |
| [DB](https://tanstack.com/db/latest) | client collections、同步及 live-query 路線 | authoritative backend、同步 adapter、離線／衝突與權限；不是託管資料庫 |
| [Store](https://tanstack.com/store/latest) | 應用 state | 與 Query/server state 分界、持久化與 framework adapter |
| [Pacer](https://tanstack.com/pacer/latest) | debounce、throttle、排程與節奏控制 | 取消、重試、背景/前景生命週期；不取代伺服器限流 |
| [Hotkeys](https://tanstack.com/hotkeys/latest) | 快捷鍵與鍵盤操作 | focus scope、輸入法、瀏覽器衝突與可發現性 |
| [AI](https://tanstack.com/ai/latest) | 模型、streaming、tool-call 與 UI 整合候選 | provider、工具授權、server secrets、evals、費用與 durable execution；React client 套件另行選擇 |
| [Charts](https://tanstack.com/charts/latest) | 圖表候選 | 資料意義、label、可及性、互動與效能；不從圖表外觀推定產品指標 |
| [Markdown](https://tanstack.com/markdown/latest) | Markdown rendering 候選 | 不可信內容、sanitization、link policy、streaming 與 target adapter |
| [Highlight](https://tanstack.com/highlight/latest) | 語法高亮候選 | language/grammar 載入、長 code blocks、contrast 與 bundle |
| [Devtools](https://tanstack.com/devtools/latest) | 開發期觀察與除錯 | 是否進正式 build、資料暴露、adapter 相容性與卸載 |
| [Config](https://tanstack.com/config/latest) | 共享開發／建置設定 | 所選工具與版本相容性；不把維護者 monorepo 設定照搬成產品架構 |
| [CLI](https://tanstack.com/cli/latest) | scaffolding／開發工具入口 | 先讀產物、依賴與執行副作用；生成不代表 stack 已批准 |
| [Intent](https://tanstack.com/intent/latest) | 提供 agent 可讀的 library 使用知識 | 檢查來源、版本和 agent side effects；不能覆蓋專案指令或技能授權 |

[Application Starter](https://tanstack.com/application-starter)／[Builder](https://tanstack.com/builder) 查核時標為 Alpha，只作生成／探索候選；不是另一個產品 runtime。RC、Alpha、Beta 屬於單項的日期快照，不能從穩定的 Query 推定 Start、AI 或其他新項目同樣穩定。安裝前回看官方 release/security advisories，固定修補版本和 lockfile，核對實際使用的 adapter／peer dependencies；本目錄不固定永久安全版本下限。

條件式起點：React SPA 可先比較 Vite＋Router＋Query；需要 SSR/server functions 再比較 Start 與其他 React framework；資料工作台按需要加 Table／Virtual／Form；local-first 或 AI 能力各自驗證 DB／AI。離線寫入、同步與撤權義務另見 [Data](data-storage.md)／[Architecture](architecture.md)，不由 client collection 套件自動完成。UI foundation 與樣式仍見 [Components](components-icons.md) 和 [CSS](css-styling.md)，完整組合見 [Architecture](architecture.md)。

## Tailwind CSS 與元件／icon 分離

Tailwind CSS 是可選樣式候選。Tailwind 是樣式層，不是應用框架；按鈕、表單元件與 icon 是另一層決策。Next.js 與 Astro 的官方文件選單都出現 Tailwind 相關項目，但安裝與版本正文未收錄，因此 Tailwind v3/v4 相容性、CSS 入口、PostCSS、設計 tokens、暗色模式與 purge 行為全部標記為待驗證。不要從元件庫的樣式推導出整個專案必須使用 Tailwind，也不要把 icon 授權與框架授權混在一起。

## 情境式建議

- 若是新內容站且每頁只有少數互動：先以 Astro islands 作為候選，核對互動島、表單、session、SEO、多語系與部署 adapter，再決定是否採納。
- 若是 React 團隊、需要全端路由與伺服器能力：把 Next.js 列入主要候選，先驗證 App Router React 版本、快取、Server/Client 邊界、驗證整合與目標 runtime。
- 若是既有系統只需局部互動：評估在既有頁面加入 React，或保留原棧補 Vite/Parcel/Rsbuild 一類建置能力；不要因範例美觀而重寫健康前端。若是原生 App 需求，另行評估原生或跨平台方案，不把 DOM 元件當原生元件。

## 架構、營運與成本面向

按候選記錄渲染策略、路由、資料取得、快取、session、表單驗證、錯誤邊界、觀測、部署 adapter 與回滾。成本不給虛構價格，改問：建置時間、bundle 大小、server 費用、快取儲存、圖片與字型處理、錯誤監控、支援回應、升級人力、長期維護。供應商或平台的專屬功能可以帶來便利，但會提高遷移成本；先定義哪些能力屬於通用契約，哪些可接受平台耦合。

## 遷移與鎖定檢查

- 路由與連結：核對動態路由、巢狀 layout、重導、查詢參數與預覽／草稿模式。
- 資料：分開伺服器取得、客戶端快取、mutation 與錯誤重試；不要讓元件直接拉資料造成網路瀑布。
- 樣式：若採用 Tailwind，確認版本、CSS 入口、tokens、元件覆寫與視覺回歸。
- 渲染：確認哪些路由要 SSG、SSR、SPA 或混合；不要只看首頁結果。
- 平台：列出 runtime 版本、環境變數、圖片、快取、headers、中間件與自架限制。
- 退場：保留 API 契約、內容模型、analytics 事件與測試，避免框架內部型別外洩到產品層。

## 失敗／驗證清單

1. 版本矩陣通過：框架、React/Vue/Svelte、Tailwind、元件庫、icon、測試與部署 adapter 版本一致。
2. 每種代表性路由通過：登入前、登入後、內容、表單、搜尋、空狀態、錯誤、慢網路。
3. 建置產物通過：bundle、首屏、快取 headers、圖片、字型、Source Map 與安全 headers。
4. 既有整合通過：CMS、API、驗證、webhook、多語系、觀測與回滾。
5. 視覺與可及性通過：所選樣式 tokens、鍵盤、焦點、語意 HTML、響應式、暗色模式。
6. 採納記錄完成：PRD 只寫需求；stack-decisions 記錄前端與 Tailwind 決策；architecture 記錄路由、資料、渲染與 session 邊界；wireframes/視覺驗收記錄樣式，不把本參考文件當成新審批閘門。

## 待驗證

Nuxt 渲染頁本次僅有官方搜尋摘要，直接抓取 markdown 失敗；其餘基本定位已補查。Tailwind、元件與 icon 的細節見 [元件與圖示](components-icons.md)。React、Next.js 與 Tailwind 相關版本相容性必須在採納前重跑版本檢查。

## 來源

[React：從零建置](https://react.dev/learn/build-a-react-app-from-scratch)、[React：安裝](https://react.dev/learn/installation)、[React：Quick Start](https://react.dev/learn)、[React：加入既有專案](https://react.dev/learn/add-react-to-an-existing-project)、[Next.js Docs](https://nextjs.org/docs)、[Astro islands](https://docs.astro.build/en/concepts/islands/)、[Nuxt introduction](https://nuxt.com/docs/4.x/guide/concepts/rendering)、[SvelteKit introduction](https://svelte.dev/docs/kit/introduction)。

## 樣式與圖示候選

[CSS 方案](css-styling.md) 與 [Icon 方案](icon-systems.md) 分開比較。上述檢查中出現 Tailwind，僅適用於已選 Tailwind 的專案；其他方案核對各自的版本、tokens、build 與狀態行為。沒有預設套件。
