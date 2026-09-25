# 測試與驗收參考

狀態：Reference only · 核對日期：2026-09-25。本文件是可選參考：不自動採納或安裝任何工具、不新增關卡、不改變既有 skill 流程。

## 事實與推論的分界

- 來源事實：證據包內 Playwright 官方頁（首頁、安裝、斷言、Library）與 Maestro CLI 頁提供實質內容，以下僅精簡轉述。
- 補查事實：Vitest 是 Vite 驅動的測試框架；pytest 支援 Python 的小型到功能測試；Appium 提供多平台 UI 自動化；k6 是效能測試工具。
- 其餘為工作推論，須由專案驗證。

## 來源事實（精簡摘要）

- [Playwright 首頁](https://playwright.dev/)：一套 API 驅動 Chromium、Firefox、WebKit；提供含 auto-wait、斷言、trace、平行與分片的測試 runner；每個測試取得隔離的 browser context；支援 TypeScript、Python、.NET、Java；並提供以無障礙快照為基礎的 MCP 伺服器與 CLI 供 AI 代理使用。
- [Playwright 安裝頁](https://playwright.dev/docs/next/intro)：支援 Windows、Linux、macOS 的本機與 CI、headless 或 headed，並對 Android Chrome 與 Mobile Safari 提供瀏覽器裝置模擬（不是原生 App 或真機證據）。
- [Playwright 斷言頁](https://playwright.dev/docs/test-assertions)：web-first 斷言會自動重試直到通過或逾時（預設 5 秒），也提供 soft assertions。
- [Playwright Library 頁](https://playwright.dev/docs/next/library)：區分 `@playwright/test`（內建 runner）與 `playwright` Library（自行編排）；一般端對端測試使用前者。
- [Maestro CLI 頁](https://docs.maestro.dev/maestro-cli)：開源、單一執行檔，以宣告式 YAML 定義 Flows，涵蓋行動與 Web UI 測試，可接 Maestro Cloud，並提供 WSL 疑難排解文件。

## PRD 應先回答的問題

- 哪些 journey／TEST ID 定義了正常、拒絕、空、錯誤與恢復的預期結果？
- 前後端語言與既有框架為何（直接影響 Vitest 或 pytest 的選擇）？
- 驗收需要哪些層級的證據：單元、契約、瀏覽器 E2E、真機、載入或 Agent 行為？
- 驗收證據最終記錄在哪份既有文件（如 delivery-acceptance-contract）？

## 候選比較矩陣（八種，皆為可選）

各選項的範圍與證據定義如下；表中適用、成本與鎖定判斷屬工作推論。

| 候選 | 範圍與證據 | 適用 | 避免條件 | 架構與整合義務 | 營運與成本 | 遷移與鎖定 |
| --- | --- | --- | --- | --- | --- | --- |
| Vitest | JS/TS 單元與元件層測試 | 前端與 Node 專案的業務規則、mock | 非 JS 後端；DOM 模擬不能代替真實瀏覽器，可另評 Browser Mode | 與 bundler／TS 設定整合 | CI 時間與記憶體；免費開源 | 與 Vite 生態相關；遷移需重寫部分斷言 |
| pytest | Python 測試框架 | Python 後端單元與整合 | UI 行為、非 Python 專案 | fixture 與 conftest 組織 | CI 時間；免費開源 | 慣例可攜，外掛選擇影響移植 |
| Playwright | 瀏覽器 E2E：跨瀏覽器、auto-wait 重試斷言、trace、平行分片、auth state 重用 | Web 使用者旅程與跨瀏覽器回歸 | 行動 App 真機需求；純單元專案 | CI 需備瀏覽器環境；管理登入狀態 | 瀏覽器資源與平行成本；免費開源 | API 隨大版本演進；腳本可讀性高、可攜 |
| Contract／schema 測試（方式） | 以 schema 驗證 API 請求與回應邊界 | 前後端分離、多服務 | 只驗 schema 不足以證明授權和業務語意 | 先定義 schema 來源與版本策略 | 維運成本低 | 契約格式（如 OpenAPI 類）與程式碼產生流程需協調 |
| Appium | 跨平台行動自動化 | 真機／模擬器同測 iOS 與 Android | Web-only 產品 | driver 生態與裝置農場 | 裝置與 driver 維護成本需估算 | driver 版本相容性是主要風險 |
| Maestro | 行動與 Web UI 的 YAML Flows、單一執行檔、Cloud 可選 | 行動 journey 的快速冒煙與回歸 | 需要深度程式化控制時 | 準備裝置／模擬器；YAML 流程檔管理 | 本機免費；Cloud 費用未驗證，不虛構價格 | YAML 流程可攜；授權條款細節待驗證 |
| k6 | 負載與效能測試 | 上線前容量與回歸效能 | 功能未穩時過早壓測 | 隔離測試環境與觀測整合 | 產生流量的資源成本；雲端方案未驗證 | 腳本與其雲端平台可能有綁定風險 |
| Agent evals（方式） | 固定案例集、評分標準、工具呼叫軌跡與預算上限 | AI／Agent 功能的行為驗收 | 無固定成功標準時不可用 | 先由產品定義案例與評分者 | 案例維護與迭代成本高 | 評估框架多且未成熟，避免深綁單一框架 |

各工具證據 distinct：單元測試證明業務規則；契約測試證明 API 邊界；Playwright 證明瀏覽器旅程；Appium/Maestro 只證明所用真機或模擬器上的行為；k6 證明容量；Agent evals 證明任務行為。任何一層都不替代其他層。

## 三個情境建議（條件式範例，非通用預設）

1. 前後端分離 Web 產品（TS 前端、Python 後端）：Vitest 覆蓋業務規則，pytest 加契約測試覆蓋 API 邊界，Playwright 只鋪三到五條主旅程與拒絕案例；安全類負向測試與 security 文件對接。
2. 行動 App：先用 Maestro YAML 做快速 journey 冒煙；只有需要深度跨平台控制或既有 Appium 投資時，才引入 Appium；避免一開始同時養兩套行動框架。
3. 上線前容量與 Agent 功能：k6 在隔離環境壓測關鍵 API 並附環境規格；Agent 功能以固定案例集加工具軌跡審查驗收，不以「回答看起來合理」通過。

## 失敗與驗證檢查清單

- 每個 TEST ID 記錄環境性質（synthetic、mock、sandbox、production read-only）、工具版本、commit 與實際結果。
- 負向與拒絕案例至少一條；單次成功不得宣稱安全或穩定。
- 瀏覽器或真機工具不可用時記錄缺口；靜態檢查不得改稱實機證據。
- 效能結果附環境與資料規模，不跨環境直接比較。

## 採納記錄落點（沿用既有文件，不新增關卡）

PRD 的 journey／TEST ID 對映到測試計畫與任務紀錄；最終驗收結論仍由既有 delivery-acceptance-contract.md 持有。本參考不建立第二套 PASS 系統，也不改變 skill 流程。

## 未解決事項

- 四者基本用途已補查；最低版本、插件／driver 相容性與授權條款仍按採用版本確認。
- Maestro 的具體授權條款名稱與 Maestro Cloud 計費未驗證。
- Playwright 各語言綁定的版本差異與 CI 映像需求未核對。
- 契約測試格式（OpenAPI／JSON Schema 等）與 CI 整合未與專案現況核對。
- Agent eval 的評分標準需產品側定義，任何工具都不能替代該決策。

## 來源清單

上方已內連：Playwright 首頁／安裝／斷言／Library、Maestro CLI；補查來源：[Vitest](https://vitest.dev/guide/)、[pytest](https://docs.pytest.org/en/stable/)、[Appium](https://appium.io/docs/en/latest/)、[k6](https://grafana.com/docs/k6/latest/)。
