# Integrations Reference（整合方式參考）

狀態：Reference only · 查核日期：2026-09-25。本文件只彙整候選方式與判斷依據，不是預設技術棧、不是強制規範、也不授權任何安裝或採購。專案採納某項目後才形成其決策與驗收條件；未採納項目不自動生效。所有外部參照皆屬建議性質。

## PRD 層級問題（可帶入 PRD 對答）

- 哪些外部服務屬於核心資料流，哪些是可替換的外圍整合？
- 同步等待的上限與失敗語意（重試、補償、人工介入）由誰定義？
- 事件可能重複、亂序、遺漏時，下游靠什麼保持一致？
- 各 provider 的簽章、認證、rate limit、資料去向、費用模型是否已逐項核實？
- 更換 provider 時，哪些程式與資料契約需要重寫？

註：以上為通用問題清單，非 PRD 摘錄；套用時以實際 PRD 為準。

## 候選方式比較矩陣

| 候選 | 適合情境 | 避免條件 | 架構／整合義務 | 營運／成本面向 | 遷移／鎖定考量 | 證據狀態 |
|---|---|---|---|---|---|---|
| 同步 API 呼叫 | 即時問答、需立即回傳結果、低失敗率 | 長任務、易失敗的外部呼叫 | 逾時、重試、熔斷、冪等鍵 | 每次呼叫即成本；受執行平台函式時限約束 | 以自訂 client 介面包裝，換 provider 成本可控 | 整合設計建議；目標平台限制另核 |
| Webhook／事件（Svix 為候選） | 第三方被動通知、狀態更新 | 需同步拿到結果的流程 | endpoint 驗簽、事件 ID 去重、處理重送與亂序 | 事件量成本、endpoint 可用性責任在己 | Svix 的端點管理能力可遷移與否待其文件核實 | 官方基本模式已補查 |
| 輪詢／批次同步 | provider 無 webhook、報表或目錄同步 | 即時性要求高 | checkpoint、部分成功處理、續跑設計 | 定時任務成本、API 額度消耗 | 邏輯自持於己方，鎖定低 | 通用整合建議；來源待補 |
| 佇列（Cloudflare Queues 或 Redis Streams 等候選） | 削峰、長任務、生產者與 worker 解耦 | 一次轉發即完成的小任務 | 訊息格式、ack／重試、毒訊隔離 | 佇列資源與持久化成本 | 自架或託管的授權與服務條款要依確切版本核對 | Queues 官方概覽已補查；delivery semantics 與配置需另核 |
| 工作流／iPaaS（n8n 為候選） | 多 SaaS 串接、低碼自動化 | 無法滿足交易、存取控制或稽核要求時 | 流程版本控管、失敗補償路徑 | 平台訂閱或自架維運成本 | 流程定義能否匯出遷移待核實 | 官方確認 workflow automation 定位；連接器與營運細節另核 |
| Provider 專用 adapter（Stripe、Resend 等） | 深用單一品牌功能、官方 SDK 生態 | 需要多 provider 可替換時 | 各家 SDK 版本與 API 版本對齊、憑證管理 | 依 provider 各自計價，未核實前不引用任何數字 | 每家契約不同；抽象層可降低鎖定 | Stripe webhook 與 Resend 基本用途已補查 |

## 已核對能力與整合責任

- [Stripe webhook](https://docs.stripe.com/webhooks)：接收非同步事件；驗證簽章並處理重複、亂序與重送。HTTP 成功與訂單完成分開；驗簽需要保留正確原始 request body。這是 provider 特有契約，不應用通用 JSON 重編碼破壞簽章。
- [Svix](https://docs.svix.com/introduction)：候選用途是自家產品向外發送 webhook 的基礎設施。不要因接收 Stripe webhook 就假設必須加 Svix；其 SDK、重試與 endpoint policy 採用時另核。
- [Cloudflare Queues](https://developers.cloudflare.com/queues/)：官方提供 batch、retry、delay、dead-letter queue 及 HTTP pull consumer 路線。設計事件 ID、ack、毒訊隔離、積壓告警與重播；選服務不等於已解決資料一致性。
- [n8n](https://docs.n8n.io/)：官方定位是 workflow automation，提供 cloud／自架路線。比較特定 connector、憑證保管、流程版本、重試與稽核；使用核心資料前看是否能滿足要求，不因「低碼」一律允許或排除。
- [Resend](https://resend.com/docs/introduction)：郵件 API 候選。需評估寄件網域、SDK、退信／抑制、事件、模板與送達監測；API 接受發送不保證收件人收到。Authentication 與通知郵件可共用 provider，但生命週期和權限分開。

適配、重試與補償設計屬研究建議；官方正文支持上述基本能力。函式 timeout、配額與授權不固定於本文，採用時按版本與方案查明。不要為未出現的第二家 provider 預先做大型抽象框架；先隔離業務狀態與 provider payload。

## 情境建議（條件式範例，非通用預設）

1. 若 PRD 要求支付結果最終一致：發起用同步 API，結果靠 webhook；驗簽、事件 ID 冪等、重放偵測為必查項；若還需把自家業務事件發给客戶，才另評 Svix。
2. 若任務時長可能超過同步上限（如媒體轉檔、批次匯入）：改佇列加 worker；Redis Streams 為已查證候選，Cloudflare Queues 可比較；部署在 Vercel 時先確認所選方案時長上限。
3. 若僅需把表單資料同步到 CRM 與 Email 工具：n8n 這類 iPaaS 候選可先低成本試用；涉及核心資料時，先驗證其存取控制、復原、稽核與契約；不滿足才比較自建。

## 失敗與驗證清單

- 逾時、429／限流、重複與亂序事件、簽章失敗、部分成功、憑證撤銷、重試耗盡，各有已定義行為並實測。
- HTTP 回應碼與業務完成分開驗證；事件端點對重送與停用事件有補償路徑。
- 佇列：ack 遺失、毒訊、積壓告警、消費者離線後恢復。
- 輪詢：checkpoint 可續跑、部分成功可標記與重跑。
- 未測項目在採納紀錄標「未驗證」，不得以靜態審查取代。

## 未解決的版本／方案／授權／SDK 檢查

- Stripe webhook：簽章格式、事件版本、重送政策——待驗證。
- Svix：方案額度、SDK 語言覆蓋、端點管理功能——待驗證。
- Cloudflare Queues：方案可用性與消費語意——待驗證。
- n8n：自架授權條款與雲端方案差異——待驗證。
- Resend：網域驗證流程與 SDK 範圍——待驗證。
- Redis：按實際版本與部署方式核對授權、持久化、淘汰及恢复設定，本文不做法律結論。

## 採納紀錄（對應既有專案文件，不新增閘門）

- 選型結論與理由 → 既有 architecture 文件章節。
- 發佈與環境設定 → 既有 DEPLOYMENT 流程。
- 實際設定與 read-back 證據 → 既有 ACTIVATION 紀錄。
- 各來源「已驗證／待驗證」狀態 → 既有 sources.md。
本文件不觸發安裝、不觸發採購、不變更任何 skill 或 workflow 流程。

## 相關參考

[API](api.md)、[Authentication](authentication-and-identity.md)、[資料](data-storage.md)、[部署](deployment.md)、[Operations](operations.md)。官方來源已在上文逐項連結。
