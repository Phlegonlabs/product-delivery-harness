# CSS 與樣式方案參考

Reference only · 2026-09-25。所有方案均可不採用，沒有預選 Tailwind。框架、樣式引擎、元件庫、icon 和動畫分開決策；保留健康的既有 CSS 是有效方案。

## PRD／設計對答

先問：內容站還是資料密集應用？已有品牌 tokens 或元件嗎？是否多品牌、多語系、dark mode？是否需要 SSR/RSC？團隊偏好 CSS 或 TypeScript？部署有無建置步驟？需要現成樣式還是自訂設計？最重要的是長期由誰維護。

## 候選比較

能力欄依官方來源；適配、避免條件與成本為研究判斷，不是廠商排名。

| 候選 | 能力與適用方向 | 不宜／先驗證 | 維護、成本與遷移 |
| --- | --- | --- | --- |
| 原生 CSS | 標準樣式、custom properties、layout 與 media queries；適合任何可維護的 Web 基礎。[MDN](https://developer.mozilla.org/en-US/docs/Web/CSS) | 新語法需核對目標瀏覽器；大型專案要有 scope／命名和 tokens 慣例 | 無額外樣式引擎；成本在 cascade、共用規則與回歸；可逐步引入其他方法 |
| CSS Modules | class／animation 名稱預設本地 scope；適合元件旁的 CSS。[官方專案](https://github.com/css-modules/css-modules) | 要核對 bundler；不提供設計系統或完整隔離，global 規則仍需管理 | 低 runtime 負擔；遷移牽涉 import／class 映射及建置設定 |
| Sass / SCSS | 編譯為 CSS，提供 mixins、modules 與程式化樣式。[官方指南](https://sass-lang.com/guide/) | 原生 CSS 已足夠時未必值得新增；避免深層 nesting 與難追蹤 extend | 有 compiler／版本維護；移轉時展開 mixin、變數與 module 依賴 |
| Tailwind CSS | utility classes、狀態與響應式 variants。[官方概念](https://tailwindcss.com/docs/styling-with-utility-classes) | 不因元件範例就強制加入；動態 class 組合、版本升級、reset 與 token 衝突先核對 | 維護 markup classes、theme 與掃描範圍；改方案時需要重整 class／token |
| UnoCSS | 可配置的按需 atomic CSS engine。[官方文件](https://unocss.dev/) | presets／rules／extractors 需由團隊管理；不保證任意 Tailwind plugin 可直接用 | 可少生成未用樣式；自訂規則增加交接成本；移轉先盤點 shortcuts 與 presets |
| Panda CSS | 靜態分析 JS/TS，在建置時產生 atomic CSS 與 recipes。[官方入門](https://panda-css.com/docs/overview/getting-started) | 核對可靜態擷取的寫法、codegen、framework 與 monorepo 設定 | 型別化風格有助大型元件維護；遷移會牽涉 recipe／token API 和生成流程 |
| vanilla-extract | 在 TypeScript 撰寫樣式，產生 CSS，樣式輸出無 runtime 引擎。[官方介紹](https://vanilla-extract.style/) | 需對應 bundler integration；執行期動態值仍需設計變數／狀態傳入 | 適合型別化 theme；不是零建置成本，遷移要處理 `.css.ts` 和 theme contracts |
| Bootstrap | 提供樣式與元件體系；適合接受其慣例、要快速形成一致 UI 的團隊。[官方入門](https://getbootstrap.com/docs/5.3/getting-started/introduction/) | 品牌需要大幅覆寫時先比較成本；互動元件的 JS 與框架狀態要協調 | 追蹤 theme、Sass 與元件 API；不是只載入 CSS 就完成互動與無障礙 |
| Bulma | CSS framework 路線，提供 layout／樣式元件。[官方文件](https://bulma.io/documentation/) | 互動行為與可及性仍由應用實作；不要把樣式套件當完整 UI runtime | 適合偏 CSS 工作方式；遷移重點是 class 與結構慣例 |
| Pico CSS | 簡約、偏語意 HTML 的樣式路線。[官方文件](https://picocss.com/docs) | 高度客製、密集後台或複雜元件需求先做代表頁 | 起步設定少；需評估全域元素樣式、scope 與後續覆寫成本 |

## 三個條件式方案

1. 小型內容／活動頁：先比較原生 CSS、CSS Modules 與 Pico。若設計很獨特，原生樣式可能比覆寫現成框架更直接；不為單一頁面引入完整工具鏈。
2. 多頁 React 產品與自有 tokens：比較 CSS Modules、Tailwind、Panda 或 vanilla-extract。選擇依團隊、建置相容性和動態樣式需求；TypeScript 熟悉度不等於一定要 CSS-in-TS。
3. 已有 Bootstrap／Sass 的後台：先保留并修正 tokens 與元件狀態；只有具體維護痛點才做一個受控區域試遷移，不混用兩套 reset 來追求新工具。

## 採用前的代表頁驗證

用包含 sidebar、表單、dialog、table、長中文標題的真實頁面比較。測試開發與 production build、SSR hydration、CSS 順序、dark mode、字型 fallback、390／768／1024／1440 及中間尺寸。確認動態 class／variant 不會在 production 消失，focus 不被 reset 或 overflow 裁掉。

記錄 bundle／生成 CSS、建置速度、無用樣式、改 token 的影響範圍與升級工時。以上需在實際專案量測，不能引用官方 benchmark 當本案結論。靜態 CSS 沒有執行期引擎，仍可能產生過大的 stylesheet 或昂貴 layout。

## 決策落點

在既有 stack-decisions／ui-design 記錄選項、未選理由、版本、瀏覽器支援、tokens 權威與遷移範圍。本文不授權安裝、不新增 gate。搭配 [元件](components-icons.md)、[Icon](icon-systems.md)、[設計](design.md)、[動效](motion.md)；不要求同一供應商或風格套裝包辦全部層。
