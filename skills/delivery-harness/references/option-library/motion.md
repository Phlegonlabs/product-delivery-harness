# Motion & Animation Reference

狀態：Reference only · 檢查日期：2026-09-25（Motion、Three.js 條目：2026-09-27；平台動效、dotLottie、Rive、GSAP 授權、動效元件來源與原生動效：2026-11-15）

本文件只彙整候選方向。它不是技術棧決策、安裝授權或 Skill 流程變更；專案未明確採納前，任何項目都不自動生效。Tailwind CSS 只是樣式候選，不是動畫必要條件，也不代表必須引入。

動效上限在技術棧決策的 [motion 層](../../../product-definition-builder/references/frontend-stack-selection.md#motion-layer) 核准。本文件只比較候選，不核准任何一項。

## 採納前要問的問題

PRD 先記錄產品行為、平台、無障礙與效能約束；具體動效偏好在 UI intake 對答，不提前選定風格或套件。UI intake 可問：動效解決什麼任務？狀態變化、導覽、教學、回饋或品牌敘事是否需要它？不動時資訊是否完整？觸發與取消條件為何？Reduced Motion 下如何保留可讀性？路由離開、重複掛載、捲動、低階裝置如何驗證？需要改變已批准技術棧時返回 Product Definition。

## 候選比較矩陣

| 候選 | 適合 | 避免條件 | 架構／整合 | 維運與成本 | 遷移／鎖定 |
| --- | --- | --- | --- | --- | --- |
| CSS transitions/animations | hover、focus、載入、小範圍狀態變化 | 複雜時間軸、需要精確暫停反向或以捲動進度驅動 | 保留在樣式層，配合 class 與媒體查詢；依賴瀏覽器 | 更新少、除錯成本低；檢查瀏覽器一致性 | 遷移容易；主要成本是樣式重整 |
| Web Animations API | 需要用 JS 建立、取消或監聽平台動畫 | 團隊已只需 CSS，或複雜序列會變成手寫狀態機 | 直接使用瀏覽器 API，與框架無強耦合 | 無外部套件，但要自建可測試控制層 | 標準 API 依賴較低；仍須確認目標瀏覽器 |
| View Transitions API（同文件／跨文件） | 同一頁狀態切換或頁面導覽時，舊畫面與新畫面之間的共享元素轉場 | 逐元素精細時序；跨文件轉場須在所有瀏覽器都生效 | 零相依平台功能。同文件用 `document.startViewTransition()` 與 `view-transition-name`；跨文件用 CSS `@view-transition`。屬漸進增強：以特性偵測包住，不支援時直接換內容。各瀏覽器版本見下方「平台動效支援」 | 無套件；自行測 Reduced Motion、焦點、捲動位置，以及轉場快照期間的互動 | 標準 API，退出成本低；若由框架包裝，保留包裝邊界 |
| CSS scroll-driven animations（`animation-timeline`） | 讓捲動或元素進入視窗的進度驅動 CSS 動畫，不寫捲動監聽 | 捲動進度承載必要資訊，或內容在不支援的瀏覽器上無法完成任務 | 零相依平台功能：`animation-timeline`、`scroll()`、`view()`、`animation-range`。屬漸進增強：不支援時動畫不跑，內容與操作仍須完整 | 無套件；長頁與行動裝置要實測，並確認 Reduced Motion 下有替代 | 純 CSS，移除成本低；需要 scrub、pin 或跨瀏覽器一致時再比較 GSAP ScrollTrigger |
| Motion（JS） | 不綁框架的 `animate()`、spring、`scroll()`、`hover()`、序列 | 只需 CSS transition，或已有 GSAP 覆蓋同一需求 | `npm install motion`；mini `animate()` 很小，可內嵌 HiFi 做設計投影 | MIT；Motion+ 範例與教學為付費訂閱，採用前確認授權 | 函式式 API 較易替換 |
| Motion for React | React 元件狀態、layout 動畫、`AnimatePresence` 進出場、手勢、`whileInView`／`useScroll` | 非 React 專案、只做簡單樣式變化 | 由 `motion/react` 匯入；先確認與既有 React 版本相容 | 追蹤版本與 bundle；確認 API 變更 | 元件語法可能滲入 UI；集中封裝可降低替換成本 |
| [Anime.js](https://animejs.com/) | 自訂 JS 動效、timeline、scroll、SVG morph/path、拖曳互動 | CSS/WAAPI 或既有動畫庫已足夠，或無人维护清理與取消 | 引擎套件為 `animejs`；按版本選 API，隔離 DOM／framework 生命週期、scope 與 cleanup | 按需匯入；實測 bundle、低階裝置、取消與 reduced motion | 動效邏輯與 SVG 資產要保留可替換邊界 |
| [React Bits](https://www.reactbits.dev/get-started/index) | 已選 React 的文字、背景、卡片與創意互動元件 | 當一般控制項基礎，或複製效果時未知相依／授權 | 按單一元件檢查 source、JS/TS／styling variant、動畫／3D 相依、SSR 和 cleanup | 入庫後由專案負責更新與效能；避免不需要的整套效果 | 元件來源不是單一引擎；退出時保留內容及操作語意 |
| [Magic UI](https://magicui.design/docs) | 已選 React＋Tailwind CSS 的行銷頁動效元件與特效 | 當 form、dialog、menu 基礎，或複製前未查單一元件相依 | 官網稱 150+ 免費開源動畫元件，以 React、TypeScript、Tailwind CSS 與 Motion 製作；GitHub repository 標 MIT。逐元件查 source、動畫相依、SSR 與 cleanup | 元件免費；另有付費的 Magic UI Pro（blocks 與 templates）。GitHub 最後 commit 2026-11-13（2026-11-15 查），無 release | 元件碼入庫後由專案維護；退出時保留內容與操作語意 |
| [Aceternity UI](https://ui.aceternity.com/docs) | 已選 React＋Tailwind CSS 的 hero、卡片與背景等展示元件 | 當一般控制項基礎，或要求 OSI 開源授權 | 定價頁稱免費層含 100+ 元件，以 Next.js、React、Tailwind CSS 與 Framer Motion 製作。逐元件查動畫相依、SSR 與 cleanup | 免費層加付費 Pro（blocks、templates、pages、interactions；定價頁另列 1 年、終身與團隊方案，金額不在此抄錄）。授權是自有的 [Aceternity License](https://ui.aceternity.com/licence)：可用於不限數量的終端產品，禁止轉售或再散布元件本身；部分元件含第三方授權。查不到公開 repository，維護訊號只有官網 2026 年仍有更新內容 | 元件碼入庫後由專案維護；授權條款要隨專案留存 |
| [Motion Primitives](https://motion-primitives.com/) | 已選 React＋Tailwind CSS 的文字、過場與互動動效元件 | 要穩定 API，或當一般控制項基礎 | 官網稱免費、開源、可複製貼上；README 稱以 motion 與 Tailwind CSS 製作，GitHub 標 MIT。逐元件查相依、SSR 與 cleanup | 免費。README 與官網導覽標示為 beta，預期有重大程式更新；GitHub 最後 commit 2026-09-28（2026-11-15 查，約七週前），無 release | beta 來源要固定複製當時的版本與修改紀錄，不依賴上游更新 |
| [Animate UI](https://animate-ui.com/docs) | 已選 shadcn/ui 的專案，要替 Radix UI、Base UI 或 React Aria primitive 換成帶動畫版本 | 沒有 shadcn/ui 或這三套 primitive 之一，或要求 OSI 開源授權 | 官方文件稱以 Motion 製作，換 primitive 的 import 即可；也提供 CLI。授權是 MIT＋Commons Clause：可用於任何商業或非商業產品，禁止販售或再散布元件本身（README）。逐元件查相依、SSR 與 cleanup | 查閱的首頁、docs 與 README 未見付費層。GitHub 最後 commit 與 v2.4.6 皆在 2026-11-15，維護活躍 | 換回原 primitive 只需改 import；仍要確認 Commons Clause 是否符合專案的散布方式 |
| GSAP timeline | 多元素補間、精確順序、重疊與時間控制 | 動效對任務非必要，或無人維護時間軸 | 通常是前端相依庫；應集中管理 timeline 與清理 | 需要效能與清理驗證；授權見下方「GSAP 授權」，Standard License 目前不收費 | 特有 API 會帶來訓練與遷移成本 |
| GSAP ScrollTrigger | 捲動進度確實承載意義的 scrub 或 pin | 捲動劫持影響可達性，或內容在無捲動動畫時不可用 | 綁定捲動容器、resize 與路由生命週期 | 高風險於長文與行動裝置；需實測 | 和 GSAP 共同依賴；移除時要重設視覺序列 |
| Lottie／dotLottie | 設計端匯出的向量動畫、小型插畫循環；要把多個動畫、主題與 state machine 打成一包時用 dotLottie | 互動邏輯複雜到要大量程式分支（改比較 Rive 或 CSS），或檔案造成載入與記憶體負擔 | Lottie JSON 或 dotLottie（`.lottie`）。dotLottie 是 ZIP 容器（Deflate 壓縮），MIME 為 `application/zip+dotlottie`，可含多個動畫、圖片資源、主題與 state machine；v2.0 規格涵蓋這些內容。官方網頁播放器 `@lottiefiles/dotlottie-web` 以 Rust＋WASM 為核心（ThorVG 繪製），可播 `.json` 與 `.lottie`，後端有 Canvas2D、WebGL2 與實驗性的 WebGPU，另有 React、Vue、Svelte、Solid 與 Web Component 封裝。WASM 檔要計入載入預算；明確資產大小上限 | 規格站標 MIT，官方播放器 repository 為 MIT；需管理匯出、版本、WASM 載入與失敗備援 | JSON 資產可替換；`.lottie` 的主題與 state machine 是 dotLottie 專有，換回 JSON 播放器會失去這些能力 |
| Three.js | 產品 3D 展示、空間型資料視覺化、品牌 hero 場景 | 純裝飾、主要客群是低階手機、內容本身不需要 3D | `three` ES module；WebGL／WebGPU renderer；模型用 GLB 等資產 | MIT；GPU、記憶體與載入成本高，要定預算與備援 | 場景程式與資產管線是長期依賴 |
| React Three Fiber | React 專案裡的 Three.js 場景 | 非 React 專案，或只有一個小場景而不值得加一層 | 以 JSX 表達 three.js；v8 配 React 18、v9 配 React 19 | MIT；版本要跟 React 主版本對齊 | 仍依賴 three.js；移除時要改寫場景元件 |
| Rive | 需要狀態機驅動的高品質互動插畫 | 只需要簡單 CSS 動效 | 引入 runtime 與設計檔；官方 runtime 涵蓋 Web、React、React Native、Flutter、Apple、Android、Unity、Unreal 等，確認目標平台 | 官方 runtimes 為 MIT，可商用（Rive 文件與 rive-wasm LICENSE）；rive-wasm 最新 release 2.50.0（2026-11-09），維護中。追蹤檔案效能與 runtime 更新；編輯器方案與費用待驗證 | .riv 與編輯器流程形成資產層依賴 |
| React Native Reanimated | 已選 React Native，要 UI thread 動畫、手勢驅動與共享值 | 專案仍用舊架構：4.x 只支援 New Architecture，3.x 官方稱不再積極維護 | 4.x（npm latest 4.7.1，2026-10-02）要求 New Architecture（Fabric）；`react-native-worklets` 需另裝（4.7 對應 0.13.x）；npm peer 標 React Native 0.86–0.88。Expo 專案裝完後需 prebuild | MIT；升級前對照官方相容表（React Native 與 worklets 版本） | 綁 React Native 生態，API 不通用於其他平台 |
| React Native Skia | 已選 React Native，要自繪圖形、shader、粒子或自訂圖表動畫 | 一般元件轉場（Reanimated 或內建動畫已足夠） | `@shopify/react-native-skia` 2.14.0（2026-10-01）；npm peer：react ≥19、react-native ≥0.78；`react-native-worklets` ≥0.7.0 與 `react-native-reanimated` ≥4.0.0 標為 optional peer | MIT；GPU、記憶體與 bundle 成本要實測 | 繪圖程式屬 Skia 範式，換框架要重寫 |
| SwiftUI animations | 已選 SwiftUI，Apple 平台的狀態驅動動畫 | 畫面是 UIKit-only，或目標含非 Apple 平台 | Apple 官方文件「Animations」：隨 state 變化更新畫面，含 state-based、phase-based、keyframe-based 與自訂動畫。各 API 的最低 OS 版本須逐項查 | 無第三方套件；功能隨 OS 版本 | 綁 Apple 平台 |
| Jetpack Compose animation | 已選 Jetpack Compose，Android 的狀態驅動動畫 | 畫面是 View 系統，未使用 Compose | 官方文件列 `AnimatedVisibility`、`animateContentSize()`、`AnimatedContent`、`animate*AsState`、`Transition`。`androidx.compose.animation` 最新 stable 為 1.12.1（2026-11-04），另有 1.13.0-rc01 | 隨 AndroidX 發佈；授權與 Compose 版本對齊待驗證 | 綁 Android 與 Compose |
| 影片／motion graphics | 多場景敘事、宣傳片或非即時內容 | 用影片取代真正互動 UI | 產出資產與字幕、播放控制、備援圖像 | 製作與改版成本高；影片音量與無障礙要處理 | 資產版本可替換，但來源檔管理是長期負擔 |

## 平台動效支援（2026-11-15）

資料取自 MDN 瀏覽器相容資料（`@mdn/browser-compat-data` 8.1.9，MDN 相容表的來源）；Baseline 欄取自 `web-features` 3.46.0。行動版（Chrome Android、Safari iOS）版本與桌面相同，只有 Firefox Android 不支援跨文件轉場。

| 功能 | Chrome／Edge | Firefox | Safari | Baseline（web-features） |
| --- | --- | --- | --- | --- |
| 同文件 View Transitions（`startViewTransition`） | 111 | 144 | 18 | newly available，2025-10-14 |
| 跨文件 View Transitions（`@view-transition`） | 126 | 標為 `preview`，未發布 | 18.2 | 否 |
| CSS scroll-driven animations（`animation-timeline`、`scroll()`、`view()`） | 115 | 159 | 26 | newly available，2026-10-27 |

這兩項都只能當漸進增強。沒有支援的瀏覽器必須仍得到完整內容與可完成任務的操作；動畫只是加分。跨文件轉場在 Firefox 尚未發布，不能是唯一的導覽回饋。

## GSAP 授權（2026-11-15）

[Standard License](https://gsap.com/standard-license/)（生效 2025-04-30，最後修改 2025-05-30）與 [Webflow 公告](https://webflow.com/blog/gsap-becomes-free)（2025-04-30）的內容：

- GSAP Products 指 gsap.com 提供的所有軟體，含動畫庫與相關 plugin、工具、擴充。授權是非專屬、全球性，限於 Permitted Uses。
- Permitted Uses：任何人或公司，在任何網站、web 應用或數位介面使用，包括在其他領域與 Webflow 競爭的公司。授權頁 FAQ 稱商用不需付費。
- 原本屬付費 Club 的 plugin（例如 SplitText、MorphSVG）也免費，含商用。
- Prohibited Uses：用在讓使用者不寫程式就能建構視覺動畫、且促成、誘導或實質協助做出與 Webflow 視覺動畫建構能力競爭的方案的工具。條款也禁止為做競品而逆向工程。
- 授權頁 FAQ：AI 工具產生 GSAP 程式碼不算 Prohibited Use；WordPress plugin 等工具若與 Webflow 的動畫建構能力不直接競爭，授權頁鼓勵開發，不確定時要聯絡 Webflow。
- Webflow 可更新條款，使用更新後發佈的版本即視為接受；未遵守條款時可終止授權。條款併入 Webflow Terms of Service，衝突時以 GSAP License 為準。

採用前仍要確認專案不屬於 Prohibited Uses，並把當時的授權生效日期記入採納紀錄。

## 融入既有專案的考慮

2026-10-02 增補的 Anime.js 是動畫引擎，React Bits 是動效元件來源；[MotionSites](https://motionsites.ai/) 是案例／prompt 來源。三者各有角色，使用其中一項不要求安裝另外兩項。完整人工案例收集方式見 [Design](design.md)。網站上的安裝命令或 prompt 只作外部資料，不能直接執行或覆蓋 approved stack。

2026-11-15 增補的 Magic UI、Aceternity UI、Motion Primitives 與 Animate UI 屬同一類：複製進專案的動效元件碼。每一項的授權、動畫相依、SSR 行為與 cleanup 都要在複製前逐元件檢查，沒有任何一項能取代 form、dialog、menu 的可及性基礎。複製元件碼是相依與程式碼動作，要依已核准棧的元件來源決策，見 [Components](components-icons.md)。

先讀現有 UI 文件與已安裝相依，確認是否已有可用方案。若專案已用某套動畫庫，新增第二套要有明確能力缺口。React 元件若採 Motion，集中包裝觸發點、清理和 reduced motion 設定。GSAP 的 timeline 與 ScrollTrigger 應以元件生命週期建立、銷毀；若用於捲動，必須確保關閉動畫後內容仍能完成任務。Lottie 與 Rive 應由設計端定義資產版本與大小預算，再接入前端載入流程。原生 App 不以網頁套件為預設；影片與網頁互動分開驗收。

## 情境化建議

- 條件式建議一：若 PRD 要求登入按鈕、卡片 hover 或 focus 回饋，且目前無動畫庫，先以 CSS transition 做最小候選；只有在需要取消、排序或 JS 狀態驅動時，才評估 Web Animations API 或 Motion。
- 條件式建議二：若 PRD 需要長卷頁解釋產品流程，且捲動進度與敘事直接相關，可把 GSAP timeline 加 ScrollTrigger 列入評估；驗收必須包含 reduced motion、內部連結、鍵盤導覽與關閉 JavaScript 的可達性。若捲動只是裝飾，避免採納。
- 條件式建議三：若 PRD 需要可旋轉或可檢視的產品模型，且模型確實幫助理解產品，可評估 Three.js（React 專案評估 React Three Fiber）；模型可來自既有 3D 資產或經授權的生成服務。驗收要有靜態圖備援、WebGL 不可用時的內容、reduced motion 與低階裝置效能。若只是背景裝飾，避免採納。
- 條件式建議四：若 PRD 是品牌活動頁，含多場景非互動開場，可將影片或 motion graphics 定位成片段資產，後續 UI 仍用網頁技術；只有在行銷明確要求可被使用者操作的狀態機插畫時，才比較 Rive 與 Lottie。

## 驗證與失敗檢查

逐項記錄觸發、完成、取消與反向行為。驗證 reduced motion 仍有替代；內容在 CSS、JS 或捲動失敗時可讀；鍵盤與觸控可完成任務；大型 transform、parallax、自動播放影片有節制。檢查路由離開與重進、重複掛載、resize、長文字、RTL、低階裝置、慢網路、資產載入錯誤與 layout shift。需要 pin 或 scrub 時，確認使用者能跳過並抵達全部內容。錯誤情況下不得白屏或阻擋操作。

## 引用與證據

- Motion accessibility：`reducedMotion="user"` 會停用 transform 與 layout 動畫，保留 opacity 與 backgroundColor；`useReducedMotion` 可自訂策略。[Motion for React accessibility](https://motion.dev/docs/react-accessibility)
- GSAP 與 [ScrollTrigger](https://gsap.com/docs/v3/Plugins/ScrollTrigger/) 的官方文件可確認 Tween/Timeline、清理與捲動 trigger/scrub/pin 方向；具體版本與框架整合仍需核對。授權見上方「GSAP 授權」。[GSAP Docs](https://gsap.com/docs/v3/)
- Motion 提供不綁框架的 `animate()`、`scroll()`、`hover()`，mini `animate()` 約 2.3kb；Motion+ 為付費訂閱。[Motion quick start](https://motion.dev/docs/quick-start)；React 版由 `motion/react` 匯入，含 layout、exit、手勢與捲動動畫。[Motion for React](https://motion.dev/docs/react)
- Three.js 為 MIT、以 ES module 發佈，現行 build 含 WebGL 與 WebGPU renderer。[three.js repository](https://github.com/mrdoob/three.js)；React Three Fiber v8 需要 React 18、v9 需要 React 19。[React Three Fiber](https://r3f.docs.pmnd.rs/getting-started/introduction)
- [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)、[LottieFiles Developer Portal](https://developers.lottiefiles.com/) 已列為來源；Web Animations API 的各瀏覽器版本未在本輪核實。
- 2026-11-15 核對：[View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) 與 [CSS scroll-driven animations](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_scroll-driven_animations) 的瀏覽器版本取自 [browser-compat-data](https://github.com/mdn/browser-compat-data)，Baseline 取自 [web-features](https://github.com/web-platform-dx/web-features)。
- dotLottie：[規格與工具站](https://dotlottie.io/)（v2.0 規格、MIT 標示）與官方播放器 [dotlottie-web](https://github.com/LottieFiles/dotlottie-web)（MIT、Rust＋WASM、React／Vue／Svelte／Solid／Web Component）。Developer Portal 為前端渲染頁，本輪未能讀取其內文。
- Rive：[runtimes 文件](https://rive.app/docs/runtimes)稱官方 runtimes 皆為 MIT；[rive-wasm](https://github.com/rive-app/rive-wasm) 標 MIT，release 2.50.0（2026-11-09）。
- [GSAP Standard License](https://gsap.com/standard-license/) 與 [Webflow 公告](https://webflow.com/blog/gsap-becomes-free)。授權頁原始碼中另有一段被 HTML 註解隱藏的舊式摘要（要求終端使用者不付費）；它不顯示於頁面，本文不採用，以頁面可見條款為準。
- 動效元件來源：[Magic UI](https://magicui.design/docs)、[Aceternity UI 定價](https://ui.aceternity.com/pricing)與 [Licence](https://ui.aceternity.com/licence)、[Motion Primitives](https://motion-primitives.com/) 及其 [repository](https://github.com/ibelick/motion-primitives)、[Animate UI](https://animate-ui.com/docs) 及其 [repository](https://github.com/imskyleen/animate-ui)。
- 原生動效：[Reanimated 入門](https://docs.swmansion.com/react-native-reanimated/docs/fundamentals/getting-started/)與[相容表](https://docs.swmansion.com/react-native-reanimated/docs/guides/compatibility/)、[React Native Skia](https://shopify.github.io/react-native-skia/)、[SwiftUI Animations](https://developer.apple.com/documentation/swiftui/animations)、[Compose 動畫](https://developer.android.com/develop/ui/compose/animation/introduction)與 [compose-animation 版本頁](https://developer.android.com/jetpack/androidx/releases/compose-animation)。npm 版本與 peer 取自 npm registry。

## 事實與推論

已核事實：Motion accessibility 摘要中的 reduced motion 行為；Motion JS／React 的 API 與 Motion+ 付費層；Three.js 授權、模組格式與 renderer；React Three Fiber 的 React 版本對應；上述 URL 存在於受控來源清單。2026-11-15 增補的已核事實：兩項平台動效的瀏覽器版本與 Baseline 狀態、dotLottie 容器格式與官方播放器、Rive 與 dotLottie 的 MIT 授權、GSAP Standard License 條款、四個動效元件來源的授權與付費層、Reanimated／Skia／SwiftUI／Compose 的官方文件與版本。推論：矩陣中的適合情境、包裝方式、資產預算、清理策略、遷移風險與情境建議是研究判斷，不是官方承諾。待驗證：Motion 與 Three.js 內嵌 HiFi 時能否通過離線 surface 檢查、GSAP 的版本與框架整合、Rive 編輯器方案與費用、LottieFiles 平台方案、dotLottie 播放器在目標框架的 SSR 行為、Aceternity UI 的公開 repository 與 commit 紀錄、SwiftUI 各 API 的最低 OS 版本、Compose animation 的授權條款、Web Animations API 與目標瀏覽器版本、各動效元件逐元件的相依。沒有任何候選應視為預設勝出。

## 沿用既有 Skill 分工

若專案已選 GSAP：一般補間可參考 `gsap-core`；需要多元素順序、重疊和控制時參考 `gsap-timeline`；只有捲動觸發／進度／pin 需求才參考 `gsap-scrolltrigger`。這些是可選的外部 skill，安裝器不隨附；缺少時不新增安裝授權，也不改變已選動效路線。實際使用遵循各 skill 自身入口與專案既有授權，不因文件提到便自動呼叫。Motion、CSS 或原生動畫已足夠時，不額外引入 GSAP。Three.js 只用在已核准的 3D 區塊，不拿來做一般 UI 動效。

`motion-doctrine` 可作動畫意圖與節奏的參考；HyperFrames／Remotion 類技能用在影片資產，不等同 live UI 動效。Taste／GPT Taste 的動畫偏好只提供方向，不能覆蓋 PRD、reduced motion 或效能需求。採納結論寫入既有 ui-design／motion specification 與驗收紀錄。
