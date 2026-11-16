# Design Reference

狀態：Reference only · 核對日期：2026-09-25
本文件根據官方來源與研究複核整理。它不授權採用、安裝、改動 skill flow 或發布任何程式。以下連結是核對能力用的官方來源；未取得正文者一律列為待驗證。

## PRD 對照問題

PRD 正文未隨附，採用前要先回答：
1. 每個 surface 是 landing、portfolio、內容站、後台、原生 App，還是多者混合？
2. 是否已有品牌 tokens、字體、icon、設計系統或既定 React／原生 stack？
3. 無障礙、多語系、深色模式、效能預算、資安或法遵有哪些硬需求？
4. Tailwind 只是樣式候選，還是既有專案已綁定？
5. 誰負責相依套件升級、瀏覽器相容性與驗收？

## 事實與推論

事實：MUI 官方頁描述 Material UI、MUI X、templates 與 customization；[Material UI overview](https://mui.com/material-ui/getting-started/) 與 [MUI X overview](https://mui.com/x/introduction/) 說明基礎與進階元件分工。Base UI 官方頁說它是 headless、accessible、composable 的 React 元件庫，並說明 React 17+、現代 bundler 與 WAI-ARIA 方向；見 [About](https://base-ui.com/react/overview/about) 與 [Accessibility](https://base-ui.com/react/overview/accessibility)。Radix Primitives 官方頁說明可增量採用的 low-level、unstyled 元件；見 [Introduction](https://www.radix-ui.com/primitives/docs/overview/introduction)。shadcn/ui 官方頁定位為 open code 與組合式元件庫建置方法；見 [Introduction](https://ui.shadcn.com/docs)。Android 官方頁提供 window size classes 與 canonical layouts 的裝置適配思路；見 [window size classes](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes?authuser=19&hl=en) 與 [canonical layouts](https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts?hl=en)。WAI 的 [Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) 是觸控目標驗證參考。
推論：本節矩陣、輪廓與條件建議是研究判斷，不是任何供應商的保證。

## 至少五個頁面／風格輪廓

| 輪廓 | 目標 | 可用 Taste／GPT Taste 想法 | 避免 |
| --- | --- | --- | --- |
| B2B／SaaS landing | 讓買家快速理解價值、信任與下一步 | 先寫一行 design read；hero 說一個問題、一個結果、一個 CTA；證據區用真實案例；適度 reveal | 假數據、缺乏品牌理由的漸層、內容不適合卻重複套用的卡片 |
| Creative portfolio | 展示作品辨識度與敘事 | 非對稱網格、大尺度排版、作品前後切換；動效只服務節奏 | 隨機排版、無目的 GSAP、看不見的按鈕 |
| 後台／工作台 | 效率、可掃讀、狀態完整 | 穩定導覽、表格密度、明確空／載入／錯誤狀態；功能型動效 | 行銷化 hero、常駐動畫、遮住資料的玻璃效果 |
| 公共／信任服務 | 低誤解、高對比、可預測 | 單欄優先、長文案、清晰焦點與錯誤訊息；低變化、低動效 | 行銷炫技、dark tech、縮小對比 |
| 原生／跨裝置 App | 跟平台互動與視窗變化 | 用平台慣例與 window size classes；list-detail、rail、drawer 按空間決定 | 把 web glass 或桌面排版硬搬到小螢幕 |
| 內容／文件 | 閱讀與搜尋 | 合理行寬、清晰標題層級、目錄與代碼塊；低動效 | 過大 hero、遮蔽正文的浮動元素 |

Tailwind CSS 是 utility-class 樣式的可選候選；官方正文確認可組合 utility classes 與狀態／響應式 variants，採用前要核對版本與專案整合，見 [Tailwind](https://tailwindcss.com/docs/styling-with-utility-classes)。

## 視覺方向候選（2026-10-02 增補）

以下是研究整理的方向詞彙，用來表達字體、密度、色彩、圖像與動效之間的關係，不是指定頁面骨架或八個必做方案。先保留既有品牌，再按 PRD 的受眾和任務提案；正式 direction studies 仍遵循 UI flow 的數量、相同內容、owner selection 和 HiFi gates。

| 方向 | 適用任務 | 字體／構圖／密度 | 色彩／圖像／動效 |
| --- | --- | --- | --- |
| 編輯與知識權威（Editorial authority） | 內容、研究、文件、顧問 | display/serif 與易讀正文分工、清楚閱讀順序、低至中密度 | 紙與墨的角色色、來源圖表／攝影、克制揭示 |
| 產品清晰表達（Product-led clarity） | SaaS、產品介紹、註冊轉換 | 產品主次明確、sans 與數據字體分工、中密度 | 中性色面與少量品牌重點、真實產品圖、功能性轉場 |
| 安靜操作工作台（Quiet operator console） | 管理、監控、資料操作 | 緊湊文字、tabular figures、穩定表格／detail 層級、高密度 | 低彩度底色、語意訊號、狀態回饋；資料優先 |
| 策展作品展示（Curated portfolio） | 工作室、創作者、作品 | 有性格的 display、非對稱／滿幅作品、低密度 | 作品決定色彩、項目敘事與有目的的揭示 |
| 溫暖商務與社群（Warm commerce/community） | 市集、會員、在地服務 | 易讀親切字體、商品／人物分组、中密度 | 暖色但維持對比、真實人與商品、hover／crossfade 回饋 |
| 技術平台（Technical platform） | API、開發工具、基礎設施 | sans 與 mono 分工、code／docs／demo 層級、中密度 | 明確 light/dark 對比、真實工具畫面、示範優先 |
| 公共信任（Civic trust） | 公共、金融、健康等高誤解成本流程 | humanist／system 正文、可預測任務順序、中至高密度 | 高對比語意色、解釋圖像、驗證／恢復回饋 |
| 空間產品展示（Spatial showcase） | 硬體、3D、媒體產品 | 產品展示面與資訊層分開、低密度 | 場景與產品重點色、解說型 3D／scroll、靜態替代 |

每一方向都要用真實中文與中英混排驗證：CJK 字體角色、數字、行長、字級、fallback 與載入预算不能直接照抄西文案例。圖表的資料意義、filter 和狀態由 PRD 決定；方向只處理呈現。[Material 3](https://m3.material.io/)、[Fluent 2](https://fluent2.microsoft.design/) 和 [Carbon](https://carbondesignsystem.com/) 可協助比較控制項、字體與狀態設計，不自動指定品牌或套件。

## 案例與動效來源（2026-10-02 增補）

| 來源 | 主要用途 | 參考邊界 |
| --- | --- | --- |
| [Mobbin](https://mobbin.com/) | 實際產品畫面、操作流程與狀態 | 看完整任務與前後狀態；不要只按單張畫面定產品流程 |
| [Dribbble](https://dribbble.com/) | 視覺語言、排版、配色與設計師作品 | 作品可能是概念展示；實際操作、響應式和原網站另行核對 |
| [Awwwards](https://www.awwwards.com/websites/) | 品牌網站、作品集、字體、滾動與互動案例 | 原網站上驗證速度、可及性與手機行為；獎項不代表適合本產品 |
| [Refero](https://refero.design/) | Web App／SaaS 的畫面、流程、table、filter、pricing 等模式 | 把 pattern 對應具體 UI 任務，不整套複製資訊架構 |
| [MotionSites](https://motionsites.ai/) | Landing／Hero／section 的方向與生成提示詞 | 網址按本輪名稱暫定；prompt、示範與生成結果各自驗證，不能當正式產品契約 |
| [React Bits](https://www.reactbits.dev/get-started/index) | 可挑選的 React 文字、背景、卡片與互動效果 | 屬元件／程式來源；先查所選版本、license、依賴及效能，再決定是否重用 |
| [Anime.js](https://animejs.com/) | 自訂 timeline、scroll、SVG、path 或拖曳動效 | 屬動畫引擎；與 CSS/WAAPI、Motion、GSAP 比較，按需要選用 |

參考收集以手動網站搜尋為主：owner 分享案例 URL／截图、想學的部分和適用頁面；有 Visit Website 或原站連結時，直接檢查原站。動效附短錄影或可操作頁面。沒有觀察到的狀態標成未檢查；不從搜尋摘要、作品縮圖或 prompt 宣稱完成視覺驗證。owner 已連接的參考 MCP（例如 Inspo、Awwwards）或瀏覽器工具（例如 agent-browser）可用來找候選案例與擷取頁面、錄影；agent 不自行安裝或連接，需要時詢問 owner。工具找到的結果只是候選，須檢查實際頁面、視窗與狀態並擷取後才成為 `REF-*`。

將實際觀察寫進既有 Design Brief 的 `REF-*`，再提出有頁面範圍的 `RP-*` 原則，沿用原有確認步驟。搜尋、靈感、程式碼重用與依賴安裝分開處理；所選素材／元件的 license、成本、來源、版本與修改責任必須確認。網站類型或案例外觀不會選定元件、CSS、框架或 PRD 範圍。

## 方法比較

| 方法 | 適合 | 避免條件 | 整合義務 | 成本／鎖定 |
| --- | --- | --- | --- | --- |
| 既有／原生平台 | 已有系統、平台慣例、低相依 | 品牌需要高度客製但舊系統太封閉 | 尊重既有 tokens、平台字體與導覽 | 維護成本低；重新設計時受舊契約限制 |
| Material／MUI | 需要成熟 React 元件、資料密集 UI 或 Material 語彙 | 品牌距離 Material 很遠、強制覆寫大部分樣式 | 主題、表單狀態、SSR、bundle 測試 | 生態成熟；升級與樣式覆寫要紀錄 |
| Radix／Base headless | 要保留自有品牌、可及性與互動語意 | 團隊無能力自建 focus、ARIA 與樣式 | 自建 tokens、focus ring、鍵盤與測試 | 彈性高；互動品質責任仍在專案 |
| shadcn/ui | React 團隊要擁有可改程式碼的元件庫 | 需要多框架、長期上游補丁或零客製 | 程式碼入庫、更新策略、樣式 token 統一 | 開放碼可改；專案自己承擔漂移與修補 |
| Utility-first 樣式 | 小型團隊快速統一 spacing、響應式與 dark variant | 既有 CSS 系統已穩定或團隊無治理 | 選單一策略，不混用兩套 token | 樣式層不是元件層；避免成為強制規則 |
| 制度型系統 | 法遵、企業或公共服務 | 品牌自由度優先於制度一致性 | 安裝、版本、平台限制與文案規範 | 一致性好；跨品牌複用受限 |

## 三個條件式例子

1. 若是全新 React SaaS 且沒有既有 DS：可評估 Base UI／Radix 加自有 tokens；shadcn/ui 只在團隊願意維護入庫程式碼時採用。不要把它當全案預設。
2. 若是既有 MUI 工作台且需要 Data Grid、Picker 等進階元件：先核對 MUI X Community／Pro／Premium 功能與授權，再決定是否納入；避免同一 app 另建第二套基礎元件。
3. 若是藝術家 portfolio：可走原生 CSS／既有 tokens 的編輯式排版；只有當敘事需要 pinning、scrub 或水平敘事時，才評估 GSAP，並提供 reduced-motion 靜態替代。

## 驗證清單

用真實 Traditional Chinese 文案檢查換行、截斷與字距；核對 keyboard、focus、zoom、touch target、contrast、空／載入／錯誤狀態；在 light/dark、窄中寬視窗與 reduced motion 下實測；檢查 hero 是否壓住 CTA、圖片是否造成 layout shift、第三方程式是否延遲載入；未跑過的瀏覽器與平台不得宣稱支援。

## 待驗證

Material UI 對 Material Design 版本、MUI X 各 tier 功能、Base UI／Radix／shadcn 最新版本與 framework 支援、Tailwind v4 整合、Chakra 目前版本、Ant Design、21st.dev、Lucide、Phosphor 與平台 icon 授權，均需回到官方正文與 lockfile 查核。Apple 的 [Motion](https://developer.apple.com/design/human-interface-guidelines/motion) 本次僅有入口 metadata，不做結論。

## 採納紀錄

採用時寫入既有 PRD、stack decisions、frontend、wireframe、sources 與測試文件：候選、問題、官方 URL、版本、拒絕理由、owner、驗收證據。未寫入的候選只是參考，不改變產品決策。

## 把 Taste 轉成具體設計選擇

這是從本地 `design-taste-frontend` 與 `gpt-taste` 整理的可選方法，不是把它們的整套 prompt 設為強制規則。

| 決策 | 可以借用的做法 | 何時調整 | 具體驗證 |
| --- | --- | --- | --- |
| 視覺方向 | 先寫一句產品專屬 design intent，再選排版、色彩、圖像 | 有既有品牌時延伸品牌；不用隨機風格重寫產品 | 能指出三個與內容／受眾相關的視覺決定 |
| 字體 | 少量 font roles、清楚的 display/body/data 層級 | CJK、語系、授權和載入預算優先；不強制某款西文字體 | 真實中英混排、数字表格、fallback、200% zoom |
| 標題 | 語意完整、有控制的行寬與換行 | 兩行 headline 是可選構圖，不能在每個寬度硬切兩行 | 390／768／1024／1440 及中間寬度無截斷與孤字 |
| 網格 | 有共同基線、節奏與主次；非對稱可服務作品敘事 | 後台重可掃讀，landing 可用更大對比 | 邊線、欄寬、節距與 CTA 對齊；長文案仍成立 |
| 動畫 | 每個主要動效有意圖、觸發、完成和減弱方案 | 後台以狀態回饋為主；不強制入場動畫或 GSAP | reduced motion、取消、路由重入、慢裝置可用 |
| 真實內容 | 用產品證據、實際資料形狀與圖片 | 缺素材時明確留待補，不能虛構用戶或成效 | 空、錯、長、缺圖、載入和滿資料狀態皆可辨識 |

上述四寬度沿用本次已選 wireframe 檢視尺寸，不是所有 CSS breakpoint 或原生 App 尺寸的普遍規則。超寬畫面可依需求增加檢查，觀察 max-width、閱讀行長與側欄，不必先增加固定第五檔。Android 以可用 window space 及平台適配處理；iOS 另檢查 safe area、Dynamic Type 與平台導覽。

## 按鈕／layer 擠壓與重疊的診斷

先判定是文案超長、容器 min-width、固定高度、overflow、定位、stacking context 還是 z-index 問題。不要一律加 z-index 或縮字解決。建立 header、sidebar、content、popover、dialog、toast 的層級；dialog 需核對焦點、返回與遮罩；sticky 區不能蓋住焦點或提交按鈕。

驗收用實際長標籤、多語系、放大字級、窄視窗、鍵盤開啟及錯誤提示。檢查 button group 能換行、文字不推走 icon、sidebar 有清楚 section/current item、捲动容器不互相困住。建議保留同頁不同寬度與狀態的截圖，標記不符合設計意圖的位置；這才是修正「AI slop」的可驗證依據，單靠禁用某色或某字體不足。
