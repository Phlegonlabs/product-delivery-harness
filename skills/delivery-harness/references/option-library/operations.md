# Operations & Reliability Reference（營運與可靠性參考）

狀態：Reference only · 查核日期：2026-09-25。本文件彙整觀測與可靠性候選方法，不是預設技術棧、不是強制規範、也不授權安裝或採購。專案採納後才形成決策與驗收條件。所有外部參照皆屬建議性質。

## PRD 層級問題（可帶入 PRD 對答）

- 出問題時誰被通知？通知後誰處理？
- 可接受的中斷時長與資料損失各是多少？
- 是否存在錯誤預算或 SLO？燒盡時誰決定放緩發佈？
- 備份還原多久演練一次？成本上限由誰把關？
- 儀器化（instrumentation）與後端（backend）是否分開決策？

註：以上為通用問題清單；套用時以實際 PRD 為準。

## 先分清兩層：儀器化 vs 後端

- 儀器化層：在程式內產生訊號，如 OpenTelemetry API／SDK 產生 traces、metrics、logs；Sentry SDK 捕捉例外與事件前後文。
- 後端層：接收、儲存、查詢、視覺化、告警，如 Prometheus、Grafana（含 Tempo）、Grafana Cloud、Sentry 後端。
- 兩層可分開替換。OTel 官方將 observability 描述為「從外部理解系統狀態」的能力，並以 SLI／SLO 作為可靠性溝通語彙（https://opentelemetry.io/docs/concepts/observability-primer/ ）。這是本參考的核心理由：先決定量什麼，再決定放哪裡。

## 候選比較矩陣

| 候選 | 適合情境 | 避免條件 | 架構／整合義務 | 營運／成本面向 | 遷移／鎖定考量 | 證據狀態 |
|---|---|---|---|---|---|---|
| OpenTelemetry（儀器化層） | 多服務、想保留後端選擇權 | 單一小服務且簡單告警已足 | SDK 版本管理、error 語意、exporter 設定 | 需量測開銷並維護；recording errors 語意目前為 Development 狀態，可能變動 | 設計目的即避免鎖定，可降低 instrumentation 耦合，但查詢、告警與資料仍需遷移 | OTel 官方文件已驗證 |
| Sentry（錯誤追蹤後端） | 例外聚合、議題分組、串接協作工具 | 需要精確帳務或完整安全稽核時，另設權威紀錄 | SDK 初始化、release 標注、配額與過濾規則 | 依事件量計價（數字未核實）；可過濾不可行動錯誤以控配額 | 資料為其專有格式，遷出需另行轉存 | 僅 PDF 快取可引；主文件站查核日回傳錯誤，待驗證 |
| Prometheus + Grafana OSS（指標後端＋視覺化） | 自架、成本可控、生態成熟 | 不想維運基礎設施 | exporter／collector 維運、儲存規劃 | 自擔基礎設施與人力成本 | 開放格式，鎖定低 | Prometheus 基本 time-series 模型已補查 |
| Grafana Cloud（受管後端） | 不想維運、需四種訊號關聯分析 | 資料不可出域 | 導入端點與 label 規範（service、environment 等） | 用量計價（數字未核實）；Adaptive Traces 可控 trace 儲存 | 官方頁稱與 OTel／Prometheus 相容、instrument once avoid lock-in | 多個官方頁面已驗證 |
| 平台原生監控 | 單服務、快速驗證期 | 需要跨來源關聯分析 | 依平台能力（如用 Vercel logs 檢查函式是否觸及時長上限） | 隨平台計費，常含於方案 | 換平台需重建告警與儀表板 | Vercel 用法為文件事實；其他平台待驗證 |
| 錯誤預算／SLO 程序（approach，非品牌） | 需要明確可靠性目標與取捨規則 | 尚無指標基線的早期產品 | 定義 SLI、計算窗口、燒盡時的決策者 | 主要是溝通與流程成本 | 屬程序，無工具鎖定 | OTel primer 提供 SLI／SLO 定義；SRE SLO 章節已補查 |

## 已核對能力與限制

[Prometheus](https://prometheus.io/docs/introduction/overview/) 收集數值時間序列並使用 labels；不是精確逐筆帳務紀錄。[Google SRE](https://sre.google/sre-book/service-level-objectives/) 區分 SLI（量測）、SLO（目標）與 SLA（約定）。[OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/) 提供訊號模型；採納時要另外選擇接收、保存、查詢與告警後端。Grafana 的視覺化層、Prometheus 指標儲存和 Tempo trace backend 是不同責任。

Sentry 本次主文件抓取受限，舊官方 PDF 只支持錯誤追蹤的方向；具體 SDK、效能功能、價格與最新整合不可由舊 PDF 推定。其他表中適配與成本是研究判斷，不是廠商優劣排序。

## 情境建議（條件式範例，非通用預設）

1. 若是單一服務的小產品：Sentry 負責例外、平台 logs 負責執行狀態、一張最小儀表板即可；OTel 可延後；先定義錯誤率與延遲兩個 SLI，再談工具。
2. 若已是多服務架構：採 OTel 儀器化，後端依資料出域與維運意願在 Grafana Cloud 與自架 Prometheus＋Grafana 間選擇；統一 service／environment label，trace 告警用 spanmetrics 或 TraceQL。
3. 若有正式 SLO 需求：以 OTel primer 的 SLI／SLO 定義為語彙基礎，錯誤預算作為程序（approach）而非工具採購；燒盡政策寫入既有 DEPLOYMENT 流程，不另設閘門。

## 失敗與驗證清單

- 每個告警有負責人與處理步驟；無人回應的儀表板不算觀測。
- 備份有還原演練證據；Redis 情境需確認傾印／附加日誌策略與 Sentinel／Cluster 故障轉移實測。
- OTel：確認 exporter 失敗、採樣、丟棄、斷網與 SDK 故障不造成產品失敗；避免高基數 labels 與個資洩漏。
- Sentry：配額與過濾規則有效；release 標注與麵包屑可回溯到具體事件。
- 成本：設定上限與告警；用平台 logs 驗證是否觸及執行上限。
- 未演練項目標「未驗證」，不得以文件審查取代。

## 未解決的版本／方案／授權／SDK 檢查

- OTel recording errors 語意為 Development 狀態，採用前需追蹤變動。
- Sentry：主文件 URL 查核日回傳內部錯誤；PDF 為舊版快取，版本對齊待驗證。
- Prometheus 基本用途已補查；Grafana 所選 backend、plugins 與版本相容性仍需核對。
- 不固定特定 plugin 的最低版本或預設秒數；採納時記錄所選版本與設定。
- SLO 章節已補查；目標與錯誤預算政策仍由專案需求決定。
- 各後端價格未在本輪查核範圍內，本文件一律不引用任何數字。

## 採納紀錄（對應既有專案文件，不新增閘門）

- 可靠性設計 → 既有 architecture 文件章節；發佈與恢復 → 既有 DEPLOYMENT 流程；實際設定與 read-back → 既有 ACTIVATION 紀錄；來源狀態 → 既有 sources.md。
- 本文件不新增審批閘門、不自動觸發安裝或購買、不變更任何 skill 或 workflow 流程。

## 恢復與成本的具體選擇

| 決策 | 候選與取捨 | 可驗證結果 |
| --- | --- | --- |
| 備份 | 定期 snapshot、PITR、跨區副本；副本不能取代隔離備份 | 在隔離環境還原，記錄實際 RPO/RTO 與資料完整性 |
| 發佈 | 全量、rolling、canary；按風險與回滾能力選 | 失敗版本可停止擴散，schema 變更兼容舊程式 |
| 告警 | 使用者旅程失敗、SLI burn rate、資源飽和 | 有 owner、runbook、通知測試與消除誤報方式 |
| 成本 | 平台預算、服務配額、模型／工具每任務預算 | 區分告警與硬上限；預算耗盡時有可預期產品行為 |
| 資料保留 | logs/traces/errors 分類、採樣與刪除 | 不含 token/secret；能追蹤保留期與刪除流程 |

以上是工程建議，可依專案採納。觀測只看得到問題；備份、演練、回滾與責任分工才能使恢復可執行。
