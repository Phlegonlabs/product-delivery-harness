# 跨領域情境導覽

Reference only · 2026-09-25。以下都是條件式組合，方便提出方案；不是 starter stack 或固定 recipe。每個專案仍可保留既有技術。

## 內容／品牌網站，加少量會員功能

若大多數頁面是內容、少數元件互動，可比較 Astro islands 與既有 CMS 前端；若已有 React 全端功能和伺服器需求，再比較 Next.js。只在真有會員旅程時加入 auth，不為 landing page 預裝帳號系統。表單通知可用 provider adapter；有耗時內容處理才加 queue。

先讀 [Frontend](frontend.md)、[Design](design.md)、[Components](components-icons.md)、[Motion](motion.md)。驗證代表性內容頁、SEO、表單失敗、長中文標題、圖片與字型載入。需要會員時再讀 [Authentication](authentication-and-identity.md)。成本多在內容維護、媒體、流量與第三方服務。

## B2B SaaS：多租戶、邀請、角色

可比較 managed auth（Clerk/Auth0）、資料生態整合（Supabase Auth）與自管（Better Auth/Auth.js/Keycloak）。它們不是同類產品；先明確誰負責 credential、session、企業連線和安全更新。前端可在熟悉框架中選；後端先比較模組化單體與 BFF 是否足夠，不預拆微服務。

先讀 [Auth](authentication-and-identity.md)、[Architecture](architecture.md)、[API](api.md)、[Security](security.md)。驗證跨租戶拒絕、邀請重送、停權後存取、角色降級及 webhook 補償。比較 org/SSO/SMS/日誌費用維度、自管工時和使用者遷移，不只看免費額度。

## 同時做 Web 展示端和 iOS／Android App

先分開公開展示內容、登入後 Web、App 旅程及可共用的業務/API。展示站不必跟 App 共用渲染框架。React Native／Expo 是可比較路線，原生與其他跨平台方案仍可選；此版未對原生框架做完整比較，不把 Web 元件表冒充原生方案表。

[Frontend](frontend.md) 負責 Web 選型，[API](api.md) 負責跨端契約，[Auth](authentication-and-identity.md) 負責平台 SDK、登入 redirect、session 與撤銷。App 另驗證安全儲存、deep link、離線、權限、鍵盤與真機；HTML 預覽或瀏覽器模擬不能當 App 驗收。當確認要做 App 時，再針對具體 native 能力補充官方比較。

## 匯入、報表或媒體長任務

若同步 request 不適合工作時間或失敗模型，可比較 web + queue + worker、managed workflows 與容器服務。資料庫保存可查詢 job 狀態；物件儲存保存輸入／輸出。先設計 idempotency、progress、cancel、retry、dead-letter 與重跑，之後才選 queue 品牌。

閱讀 [Architecture](architecture.md)、[Deployment](deployment.md)、[Runtime](runtime-selection.md)、[Data](data-storage.md)、[Integrations](integrations.md)。測試 worker 中斷、重複事件、部分成功、輸出已寫但狀態未更新、退款或補償。估算 backlog、compute、資料量與下載成本。

## 具工具副作用的 AI 功能

能以一次模型呼叫或固定步驟完成時，先比較這些方案。只有步驟需要模型判斷才考慮 agent loop；需要等待與恢復才評估 durable runtime；能證明專業分工／隔離收益才加多 agent。

閱讀 [Agentic](ai-agentic.md)、[Runtime](runtime-selection.md)、[Security](security.md)、[Testing](testing-acceptance.md)、[Operations](operations.md)。確認模型、工具、sandbox、狀態與成本上限各自的責任。用固定 eval cases 測工具失敗、惡意內容、拒絕、取消和重複副作用，不以展示影片判定可用。

## 提案紀錄示例

在既有決策文件寫：需求／約束 → 候選 A/B/C → 採用與不採用理由 → 查閱來源與版本 → 未決事項 → 最小驗證 → 遷移與重訪條件。未選項目留在 reference，不複製進所有專案。不新增一套與 PRD、architecture 或既有驗收重疊的權威文件。
