# AI & Agentic Reference

狀態：Reference only · 檢查日期：2026-09-25

本文件比較 agent、固定模型 workflow 與持久執行的參考方向。它不授權安裝、採用 provider、修改 Skill 流程或把任何方案當成預設。模型選擇、orchestration、持久狀態、工具、追蹤與驗收是不同決策。

## 採納前要問的問題

在 PRD 對答時可先問：輸入、步驟與輸出能否預先定義？模型判斷是否真的必要？哪些工具會造成外部副作用？失敗、取消、超時與預算用盡後如何恢復？人工確認點在哪裡？狀態要保存多久？誰能讀寫 session、追蹤與工具結果？評估集能否覆蓋正常、惡意、拒絕與恢復案例？

## 候選比較矩陣

| 候選 | 適合 | 避免條件 | 架構／整合 | 維運與成本 | 遷移／鎖定 |
| --- | --- | --- | --- | --- | --- |
| 單次模型呼叫 | 分類、擷取、摘要、單段生成 | 需要選工具、依結果改變下一步或長時間恢復 | 應用持有 prompt、驗證、重試與紀錄 | 成本較容易估算；要監看品質與錯誤率 | 最容易替換模型或 prompt |
| 固定多步 workflow | 順序、分支與輸出契約可預定 | 每步都必須由模型重排，或失敗恢復需求極高 | 明確 step API、idempotency、checkpoint、佇列或重試 | 比單次呼叫複雜，但可逐步驗證 | 邏輯留在自家程式碼，模型與 runtime 可替換 |
| OpenAI Agents SDK | 需要應用內 agent loop、工具、handoffs、sessions、guardrails 或 HITL | 短期單回應，或固定步驟已足夠 | SDK 管理回合、工具執行與審批中斷；RunState 可序列化恢復 | 追蹤 SDK 維護狀態、session 後端、序列化安全與版本相容 | 開源 SDK 不等於無遷移成本；狀態格式、工具定義與審批流程需設計隔離層 |
| LangGraph | 想把有界 agent 決策表達為可檢視圖狀態 | 步驟固定、圖狀態只增加心智負擔 | 需要狀態 schema、節點邊界、checkpoint 與測試策略 | 追蹤版本與狀態升級；觀測性要另設 | LangChain 生態內的 API 變化與整合依賴待核 |
| Temporal | 長時間工作、外部等待、重試、跨程序恢復 | 短請求或狀態已由簡單 DB 事務足夠 | workflow 定義、activity、重試、資料序列化與操作環境 | 帶來伺服或雲服務、可觀測性與版本相容成本 | workflow 語言與歷史記錄會成為平台依賴 |
| Cloudflare Agents / Workflows | Workers 內聊天、多步資料處理、報告、審批與需要持久執行 | 應用不在 Cloudflare，或目標只是單次呼叫 | Agent 可與 Workflow 雙向通訊；步驟可等待事件或審批 | 依平台可觀測性、配額、區域、保留期與錯誤處理 | Workers 進入點與平台 API 有環境依賴；遷移需重接狀態與事件 |
| Dapr / Restate / DBOS integration | OpenAI SDK 需要持久執行但不想自建恢復 | 流程短、無程序重啟風險 | 依所選 runtime 增加 SDK 與儲存依賴 | 不同整合對 DB、二進位檔或 runtime 要求不同 | 屬於執行層鎖定；先試狀態遷移與版本升級 |
| 多 agent | 有可驗證的專業分工、並行檢查或隔離收益 | 只是名稱多、無審查、無權限邊界 | 明確 handoff、共用狀態、衝突解法、權限與上限 | 成本與延遲倍增；需要 eval、trace 與人工審查 | 交接契約改動會波及多個 agent；先保持條件式 |

## 官方能力摘要

[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) 官方文件描述 tools、handoffs、guardrails、tracing 與 sessions。HITL 與 RunState 的使用要對照所選 SDK 版本，不把可序列化 state 當成完整耐故障執行。

[LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) 定位是有狀態 agent 的 orchestration runtime，可混合固定步驟與模型步驟，提供 persistence、streaming 與 human-in-the-loop 方向。[Temporal](https://docs.temporal.io/workflow-execution) 以事件歷史和 replay 恢復 workflow；外部副作用仍需 activity、重試與冪等設計，不能把 workflow 恢復等同外部 API exactly-once。

[Cloudflare Workflows](https://developers.cloudflare.com/workflows/) 可作為 Agents 的持久多步執行層；只有需求包含等待、恢復、重試時才比較。平台配額、計費、區域與保存期限採用時再核對，不以固定秒數替代需求分析。

## 情境化建議

- 條件式建議一：若 PRD 是表單抽取、文案改寫或單段客服回覆，先做單次模型呼叫加輸出驗證；若任務本身有多個可預定步驟，可用固定 workflow；模型決定下一步與否是另一項選擇。
- 條件式建議二：若流程包含寫入外部系統、付款、刪除或大規模變更，無論是否用 agent，都應在副作用前加入人工或程式化審批。若應用已部署在 Workers，可把 Cloudflare Workflows 列為持久等待候選；若應用不在該平台，不要因此遷移。
- 條件式建議三：若任務需要在程序重啟、人工等待或跨日處理後恢復，把 OpenAI Agents SDK 的 HITL 模型與 Temporal、Dapr、Restate 或 DBOS 整合一起評估。多 agent 只有在可指出獨立專業、並行收益或權限隔離時才採用；否則用單 agent 或固定步驟。

## 架構與驗收

把責任分成：模型與 provider、workflow 控制、持久狀態、工具與 sandbox、資料存取、評估、追蹤與費用控管。記錄允許行為、拒絕規則、人工確認點、工具權限、資料邊界、取消語意、重試次數、超時、部分失敗與最終一致性行為。序列化狀態要視為敏感資料，避免秘密進入 run context；恢復時使用同一 session 後端並避免並發恢復。驗收集應包含正常案例、惡意輸入、無證據問題、工具失敗、審批拒絕、程序重啟、重複事件與預算耗盡。失敗時要能取消、通知、保留審計並不重複副作用。

## 引用

[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)、[Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)、[Run state](https://openai.github.io/openai-agents-python/ref/run_state/)、[Running agents](https://openai.github.io/openai-agents-python/running_agents/)、[Cloudflare Agents Workflows](https://developers.cloudflare.com/agents/concepts/workflows/)、[Cloudflare Workflows overview](https://developers.cloudflare.com/workflows/)、[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)、[Temporal Workflow Execution](https://docs.temporal.io/workflow-execution)。

## 事實、推論與待驗證

已核事實：上節有官方正文支持的基本定位與恢復模型。推論：矩陣適合情境、權限設計、驗收條件、情境建議與鎖定風險是研究判斷，不是官方保證。待驗證：LangGraph API 與版本、Temporal 部署與授權、Cloudflare 配額與保留期、SDK 的版本與託管服務差異、各 provider 模型與工具相容性、資料保留與安全控制。多 agent 不是預設架構；任何採納都應對應 PRD 與既有專案文件的採納紀錄，而不是新增自動生效閘門。

## Cloudflare 可選組合

平台內產品的責任邊界、搭配與替代路線見 [Cloudflare 參考](cloudflare-platform.md)。可只採用其中一項，不代表整套遷入 Cloudflare。
