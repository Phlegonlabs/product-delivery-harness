# Architecture 選型參考：模組化單體、BFF、Web-Queue-Worker、事件驅動、微服務、Serverless 部署拓撲

狀態：Reference only · 核對日期 2026-09-25。本文件提供可評估的架構選項與取捨，不是部署指令、基礎設施採購授權或自動採納規則。任何選項要先落到既有 PRD、Architecture、Runtime、Deployment 與 Integration 文件，才成為專案決策。參考不代表安裝、建立雲端資源或改變 skill 流程。

## 適用範圍與 PRD 提問

架構要回答的不是「哪個名稱較流行」，而是實際旅程如何跨畫面、客戶端、API、權限、資料、外部服務與失敗恢復運作。

沿用既有 reference baseline `architecture.md` 中對應 PRD 的追問，仍需按實際需求覆核：核心旅程是什麼？有哪些角色與租戶？延遲、可用性與資料地區要求為何？哪些工作是長任務？團隊能否維運分散式系統？服務與部署單位的責任人是谁？失敗、重試、部分完成與資料一致性由誰處理？

## 主要比對矩陣

| 選項 | 適合 | 避免/重訪條件 | 架構與整合義務 | 營運與成本面 | 遷移與鎖定 |
| --- | --- | --- | --- | --- | --- |
| 模組化單體 | 單一團隊、產品仍在驗證、領域邊界可先以程式碼模組表達 | 若模組開始互相讀取內部資料表、共享隱藏狀態，或不同領域有衝突發布節奏，應重新審視邊界 | 定義 module ownership、public interface、資料存取邊界、事件邊界與測試邊界；避免以資料夾名稱冒充架構 | 發布、觀測、交易與除錯較簡單；主要成本是持續守住邊界 | 通常最低；拆出服務前應保留模組契約與資料所有權 |
| Full-stack/BFF | 多種客戶端、畫面資料形狀差異大、前端團隊需要貼近其體驗的 API 層 | 若所有介面請求相近、只有一個客戶端，或團隊無法維護多個 API 層，BFF 可能只是重複成本 | 依前端劃定 BFF 責任；共用監控、授權、限流與路由；BFF 不應重造領域規則 | 增加 API 層、部署單位與版本協調；可換取客戶端簡化與故障隔離 | BFF 契約會與前端耦合；共用服務仍需穩定介面 |
| Web-Queue-Worker | 相對清楚的核心領域，但有報表、匯入、通知等長任務 | 若佇列只是把所有同步操作包一層，或 worker 與 web 共用隱藏 schema 而失去解耦，應重審 | web 前端與 worker 透過訊息解耦；記錄佇列語意、重試、死信、冪等、逾時、outbox 與任務狀態查詢 | web 與 worker 可獨立伸縮；需付佇列、觀測、 poison message 與一致性處理成本 | 訊息格式與狀態查詢 API 會形成邊界；佇列服務可替換但語意需保留 |
| 事件驅動 | 多個消費者對同一業務事實反應、近即時整合、解耦外部系統 | 若團隊沒有非同步除錯能力，或流程需要強同步回應，先用 request/response；若事件只是遠端程序呼叫的另一種寫法，重訪設計 | 定義事件、schema 版本、producer/consumer 契約、至少一次、亂序、idempotency、死信、補償與可觀測性；避免事件夾帶過多敏感資料 | 解耦帶來伸縮與新消費者擴充；也帶來最終一致性、時序、重放、測試與故障追蹤成本 | 事件 schema 與 broker 語意是核心契約；消費者獨立演進必須有版本策略 |
| 微服務 | 複雜領域、明確自治邊界、不同服務有獨立伸縮或發布需求 | 若沒有成熟 DevOps、資料一致性與分散式觀測能力，或只是為了「技術先進」，不應啟動 | 每個服務有 bounded context、資料所有權、API/event 契約、部署與回滾策略；閘道、服務發現、追蹤與治理要一起設計 | 獨立部署與伸縮是優點；也增加網路故障、版本協調、基礎設施與跨服務測試成本 | 服務契約、資料副本與平台工具會形成多點耦合；拆分應由可驗證邊界驅動 |
| Serverless 部署拓撲 | 事件觸發、突發負載、低狀態 worker、需要快速最小化維運的部署單位 | 若長連線、極低延遲、長任務、硬體控制或可預測高利用率是核心要求，應先做 workload spike；不應把 serverless 誤當成免維運 | 記錄冷啟動、逾時、併發、狀態存放、佇列整合、身分、網路出口與部署回滾 | 可按使用量與事件規模調整；但觀測、併發限制、跨服務除錯與供應商功能差異會轉成營運成本 | 平台觸發器、身分與限制會耦合；核心邏輯應與部署單位分離 |

部署拓撲與服務分解不互斥。同一產品可以是「模組化單體＋serverless worker」、「微服務＋佇列」，或「BFF＋事件驅動整合」。選擇應依旅程與失敗模型組合，不應因標籤互斥而錯配。

## 來源事實與研究判斷

來源事實：Azure Architecture Center 將 Web-Queue-Worker 描述為 web 前端、message queue 與後端 worker 的組合，前端處理請求，worker 處理耗時或批次工作，兩者可獨立伸縮，並提醒元件可能長成大型單體。微服務則由自治服務組成，每個服務有明確業務能力與資料自主性，但帶來服務發現、資料一致性與分散式管理複雜度。見 [Architecture styles](https://learn.microsoft.com/en-gb/azure/architecture/guide/architecture-styles/) 與 [Web-Queue-Worker](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker)。

來源事實：事件驅動架構由 producer、consumer 與 event channel 組成，可使用 pub/sub 或 event stream；Azure 文件提醒 eventual consistency、處理順序、idempotency、錯誤處理與事件 schema 演進。見 [Event-driven architecture](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven)。BFF 是針對特定前端建立後端層，避免所有介面競爭同一通用後端；Azure 也提醒若介面請求相近或只有一個介面，可能不適合。見 [Backends for Frontends](https://learn.microsoft.com/en-us/azure/architecture/patterns/backends-for-frontends)。

研究推論與待驗證：模組化單體與 serverless 部署拓撲的完整官方原文未收錄，因此其細節屬於研究層級整理。採納前需以專案實際 Runtime、Deployment 與供應商文件驗證。CQRS 可作為讀寫分離的方法參考，見 [CQRS](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)，但只在讀寫負載、安全或資料形狀確實分歧時考慮。

## 三個條件式情境示例

1. 若新產品由單一團隊開發，核心域尚在驗證，但已有 CSV 匯入與報表，可組合模組化單體＋Web-Queue-Worker：核心 API 保持同步，匯入與通知走佇列 worker；先守住模組邊界，不預先拆服務。
2. 若同一業務要支援 Web、行動 App 與外部儀表板，而各端畫面資料形狀差異明顯，可評估針對各前端的小型 BFF，共用領域服務與授權；若各端只是呼叫相同 API，就不要為了模式而增加一層。
3. 若訂單完成會觸發出貨、通知、帳務與分析，且各下游處理速度不同，可評估事件驅動整合；前提是接受最終一致性、至少一次與補償流程，並先建立事件 schema 版本與死信處理。

## 失敗與核對清單

- 旅程：一條核心旅程是否畫出客戶端、API、權限、資料、外部服務與失敗恢復？
- 邊界：模組、服務、BFF、worker 或 serverless 函式的所有權、資料存取與介面是否明確？
- 非同步：佇列與事件是否定義重試、亂序、死信、冪等、補償與查詢進度？
- 一致性：同步回應、最終一致讀取、跨服務補償與遷移期間的過渡狀態是否可測？
- 觀測：跨 web、worker、佇列、事件與外部呼叫是否可追蹤同一請求或任務？
- 恢復：部分失敗、重複處理、下游逾時、部署回滾與資料回補責任是否清楚？
- 相容性：Runtime、訊息工具、serverless 觸發器、身分、網路、SDK 與資料遷移是否逐項核對？

## 採納記錄與文件映射

採納時更新既有 PRD、Architecture、Runtime、Deployment、Integration 與驗收文件，記錄：部署單位、服務或模組邊界、資料所有權、佇列/事件語意、失敗恢復、伸縮假設、替代方案與重訪條件。這是研究記錄，不新增審批關卡，也不授權建立或安裝基礎設施。
