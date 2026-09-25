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
| Astro islands | 靜態內容與局部互動島架構 | 多數內容頁、少量互動、重視初始載入 | 每頁都是高度狀態化應用，或島嶼間大量即時共享狀態 | 確認互動島、資料取得、session、表單、部署 adapter 與 所選樣式載入 | 內容主體可靜態化，但互動與動態路由仍需維運 | 互動元件若用框架元件撰寫，可評估逐島遷移 |
| Nuxt/Vue | Vue 生態的全端框架候選 | 團隊已有 Vue、需要路由與伺服器整合 | 生態套件、版本或部署 adapter 尚未核對 | Nuxt 官方渲染指南列出 universal、client-side 與 hybrid rendering；需核對路由規則、Nitro 目標、狀態與資料策略 | 成本來自 runtime、建置、監控與生態維護 | 用標準 Vue 元件與 API 合約降低鎖定 |
| SvelteKit | Svelte 生態的全端框架候選 | 團隊偏好 Svelte、需要應用級路由 | 元件庫、測試與部署路徑未核對 | SvelteKit 提供 routing、SSR 與部署 adapters；需選擇目標 adapter 並區分 server/client 資料 | 需自訂建置與觀測；避免把生態成熟度當成既成事實 | 以路由資料契約與伺服器 API 為邊界 |
| React + Vite SPA | 官方說明的從零建置路徑之一 | 既有後端穩定、只需互動前端、團隊能自組路由與資料 | 未來需要 SSR、SSG、RSC 或更多框架級整合 | 自行補 routing、資料取得、快取、程式碼切割、錯誤與狀態管理 | Vite、Parcel、Rsbuild 都可作為建置工具；成本轉為自管生態 | SPA 可放在既有頁面或子路徑，但不要清除宿主 HTML |
| 既有前端／原生替代 | 保留可維護系統，或另選原生／跨平台方案 | 既有棧健康、需求局部；目標是 iOS/Android 原生體驗 | 因新框架流行而整站重寫 | 先定義整合點、資料契約、樣式、測試與回滾 | 保留既有投資；原生需求必須另行評估工具鏈 | 局部新增、擴充或漸進替換，不做未核對的全域遷移 |

## 事實與推論界線

事實：React 官方說明從零建置可用 Vite、Parcel 或 Rsbuild，但這類 SPA 預設不含 routing、資料取得與樣式方案；若未來需要 SSR、SSG 或 React Server Components，會變成自行承擔框架級問題。React 也支援漸進採用、加入既有頁面，並已淘汰 Create React App。Next.js 官方定義為 React 全端 Web 應用框架，提供 App Router 與 Pages Router；App Router 使用內建 React canary，Pages Router 使用專案宣告的 React 版本。

推論：內容多、互動少時，Astro islands 值得列入；登入後互動與伺服器整合時，Next.js、Nuxt 或 SvelteKit 更值得比較。這些適配判斷不是官方聲明。補查 SvelteKit 正文、Astro islands 與 Nuxt 官方渲染搜尋摘要後，可確認上述基本定位；實際版本與 adapter 相容性仍需專案驗證。

## Tailwind CSS 與元件／icon 分離

Tailwind CSS 是可選樣式候選，且不新增 12px 規則。Tailwind 是樣式層，不是應用框架；按鈕、表單元件與 icon 是另一層決策。Next.js 與 Astro 的官方文件選單都出現 Tailwind 相關項目，但安裝與版本正文未收錄，因此 Tailwind v3/v4 相容性、CSS 入口、PostCSS、設計 tokens、暗色模式與 purge 行為全部標記為待驗證。不要從元件庫的樣式推導出整個專案必須使用 Tailwind，也不要把 icon 授權與框架授權混在一起。

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
