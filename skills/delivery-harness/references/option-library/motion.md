# Motion & Animation Reference

狀態：Reference only · 檢查日期：2026-09-25

本文件只彙整候選方向。它不是技術棧決策、安裝授權或 Skill 流程變更；專案未明確採納前，任何項目都不自動生效。Tailwind CSS 只是樣式候選，不是動畫必要條件，也不代表必須引入。

## 採納前要問的問題

PRD 先記錄產品行為、平台、無障礙與效能約束；具體動效偏好在 UI intake 對答，不提前選定風格或套件。UI intake 可問：動效解決什麼任務？狀態變化、導覽、教學、回饋或品牌敘事是否需要它？不動時資訊是否完整？觸發與取消條件為何？Reduced Motion 下如何保留可讀性？路由離開、重複掛載、捲動、低階裝置如何驗證？需要改變已批准技術棧時返回 Product Definition。

## 候選比較矩陣

| 候選 | 適合 | 避免條件 | 架構／整合 | 維運與成本 | 遷移／鎖定 |
| --- | --- | --- | --- | --- | --- |
| CSS transitions/animations | hover、focus、載入、小範圍狀態變化 | 複雜時間軸、需要精確暫停反向或以捲動進度驅動 | 保留在樣式層，配合 class 與媒體查詢；依賴瀏覽器 | 更新少、除錯成本低；檢查瀏覽器一致性 | 遷移容易；主要成本是樣式重整 |
| Web Animations API | 需要用 JS 建立、取消或監聽平台動畫 | 團隊已只需 CSS，或複雜序列會變成手寫狀態機 | 直接使用瀏覽器 API，與框架無強耦合 | 無外部套件，但要自建可測試控制層 | 標準 API 依賴較低；仍須確認目標瀏覽器 |
| Motion for React | React 元件狀態、進出場、集中 reduced motion 策略 | 非 React 專案、只做簡單樣式變化 | 增加依賴與元件包裝；先確認與既有 React 版本相容 | 追蹤版本與 bundle；確認 API 變更 | 元件語法可能滲入 UI；集中封裝可降低替換成本 |
| GSAP timeline | 多元素補間、精確順序、重疊與時間控制 | 動效對任務非必要，或無人維護時間軸 | 通常是前端相依庫；應集中管理 timeline 與清理 | 需要效能與清理驗證；商業授權待確認 | 特有 API 會帶來訓練與遷移成本 |
| GSAP ScrollTrigger | 捲動進度確實承載意義的 scrub 或 pin | 捲動劫持影響可達性，或內容在無捲動動畫時不可用 | 綁定捲動容器、resize 與路由生命週期 | 高風險於長文與行動裝置；需實測 | 和 GSAP 共同依賴；移除時要重設視覺序列 |
| Lottie | 設計端匯出的向量動畫、小型插畫循環 | 互動邏輯複雜，或檔案造成載入與記憶體負擔 | 加入 runtime 與 JSON 資產流程；明確資產大小上限 | 需管理匯出、版本與載入失敗 | JSON 資產可替換，但設計工具流程會影響協作 |
| Rive | 需要狀態機驅動的高品質互動插畫 | 只需要簡單 CSS 動效 | 引入 runtime 與設計檔；確認目標平台 runtime | 追蹤檔案效能與 runtime 更新 | .riv 與編輯器流程形成資產層依賴 |
| 原生 App 動畫 | iOS、Android 或已選框架內平台慣例 | 直接套用 DOM 動效或網頁捲動模型 | 走平台既有 API；與網頁方案分開評估 | 成本取決於已選框架與跨平台共用程度；需驗證無障礙 | 平台能力受 OS 版本影響，但避免跨層轉譯 |
| 影片／motion graphics | 多場景敘事、宣傳片或非即時內容 | 用影片取代真正互動 UI | 產出資產與字幕、播放控制、備援圖像 | 製作與改版成本高；影片音量與無障礙要處理 | 資產版本可替換，但來源檔管理是長期負擔 |

## 融入既有專案的考慮

先讀現有 UI 文件與已安裝相依，確認是否已有可用方案。若專案已用某套動畫庫，新增第二套要有明確能力缺口。React 元件若採 Motion，集中包裝觸發點、清理和 reduced motion 設定。GSAP 的 timeline 與 ScrollTrigger 應以元件生命週期建立、銷毀；若用於捲動，必須確保關閉動畫後內容仍能完成任務。Lottie 與 Rive 應由設計端定義資產版本與大小預算，再接入前端載入流程。原生 App 不以網頁套件為預設；影片與網頁互動分開驗收。

## 情境化建議

- 條件式建議一：若 PRD 要求登入按鈕、卡片 hover 或 focus 回饋，且目前無動畫庫，先以 CSS transition 做最小候選；只有在需要取消、排序或 JS 狀態驅動時，才評估 Web Animations API 或 Motion。
- 條件式建議二：若 PRD 需要長卷頁解釋產品流程，且捲動進度與敘事直接相關，可把 GSAP timeline 加 ScrollTrigger 列入評估；驗收必須包含 reduced motion、內部連結、鍵盤導覽與關閉 JavaScript 的可達性。若捲動只是裝飾，避免採納。
- 條件式建議三：若 PRD 是品牌活動頁，含多場景非互動開場，可將影片或 motion graphics 定位成片段資產，後續 UI 仍用網頁技術；只有在行銷明確要求可被使用者操作的狀態機插畫時，才比較 Rive 與 Lottie。

## 驗證與失敗檢查

逐項記錄觸發、完成、取消與反向行為。驗證 reduced motion 仍有替代；內容在 CSS、JS 或捲動失敗時可讀；鍵盤與觸控可完成任務；大型 transform、parallax、自動播放影片有節制。檢查路由離開與重進、重複掛載、resize、長文字、RTL、低階裝置、慢網路、資產載入錯誤與 layout shift。需要 pin 或 scrub 時，確認使用者能跳過並抵達全部內容。錯誤情況下不得白屏或阻擋操作。

## 引用與證據

- Motion accessibility：`reducedMotion="user"` 會停用 transform 與 layout 動畫，保留 opacity 與 backgroundColor；`useReducedMotion` 可自訂策略。[Motion for React accessibility](https://motion.dev/docs/react-accessibility)
- GSAP 與 [ScrollTrigger](https://gsap.com/docs/v3/Plugins/ScrollTrigger/) 的官方文件可確認 Tween/Timeline、清理與捲動 trigger/scrub/pin 方向；具體版本、授權與框架整合仍需核對。[GSAP Docs](https://gsap.com/docs/v3/)
- [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)、[LottieFiles Developer Portal](https://developers.lottiefiles.com/)、[Rive runtimes](https://rive.app/docs/runtimes) 已列為來源；本輪摘要不足以核實平台相容性、授權或 runtime 版本。

## 事實與推論

已核事實：Motion accessibility 摘要中的 reduced motion 行為；上述 URL 存在於受控來源清單。推論：矩陣中的適合情境、包裝方式、資產預算、清理策略、遷移風險與情境建議是研究判斷，不是官方承諾。待驗證：GSAP 商業授權、Lottie runtime、Rive runtime、原生平台 API、目標瀏覽器與框架版本。沒有任何候選應視為預設勝出。

## 沿用既有 Skill 分工

若專案已選 GSAP：一般補間可參考 `gsap-core`；需要多元素順序、重疊和控制時參考 `gsap-timeline`；只有捲動觸發／進度／pin 需求才參考 `gsap-scrolltrigger`。實際使用遵循各 skill 自身入口與專案既有授權，不因文件提到便自動呼叫。Motion、CSS 或原生動畫已足夠時，不額外引入 GSAP。

`motion-doctrine` 可作動畫意圖與節奏的參考；HyperFrames／Remotion 類技能用在影片資產，不等同 live UI 動效。Taste／GPT Taste 的動畫偏好只提供方向，不能覆蓋 PRD、reduced motion 或效能需求。採納結論寫入既有 ui-design／motion specification 與驗收紀錄。
