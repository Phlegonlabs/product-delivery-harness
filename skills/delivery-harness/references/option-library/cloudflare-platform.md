# Cloudflare 平台選型參考

Reference only。查閱日期：2026-09-25。產品能力依官方文件；適用條件、組合與驗收建議是研究判斷。可以只選一項，也可以與其他供應商混用。這份文件不批准安裝、部署或技術棧；選定結果回填專案現有 PRD、architecture、stack decision 與部署文件。

2026-10-02 增補下方開發平台、框架與工具候選；原有條目的查閱日期保留。覆蓋的是本輪討論的應用開發選項，不宣稱已盤點 Cloudflare 全部企業網路產品或確認每個帳號可用。其他產品從 [官方目錄](https://developers.cloudflare.com/directory/) 按需求補查。

## 產品責任與選擇

| 候選與官方來源 | 負責什麼 | 何時考慮 | 限制與評估重點 |
|---|---|---|---|
| [Workers](https://developers.cloudflare.com/workers/)／[Static Assets](https://developers.cloudflare.com/workers/static-assets/) | 執行請求處理程式與提供網站資產 | 網站、API、邊緣請求處理 | 核對框架 adapter、Node API 相容性、執行限制；不假設等同完整 Node 伺服器 |
| [D1](https://developers.cloudflare.com/d1/) | SQLite 基礎的受管 SQL 資料庫 | 結構化資料、新服務的 SQL 查詢 | 驗證 SQL／交易需求、容量、遷移、備份還原；不是 PostgreSQL 原樣替代 |
| [KV](https://developers.cloudflare.com/kv/) | 分散式 key-value 儲存與快取讀取 | 可容忍短暫舊資料的設定、讀多寫少資料 | 最終一致；不要用作庫存扣減、付款狀態鎖或原子協調 |
| [R2](https://developers.cloudflare.com/r2/) | 物件儲存 | 圖片、文件、匯出檔、模型產物 | 權限、CORS、上傳限制、生命週期；交易型 SQL 是另一項需求 |
| [Durable Objects](https://developers.cloudflare.com/durable-objects/) | 按物件組織的狀態與協調、附帶強一致儲存 | 房間、協作、逐實體協調 | 一致性邊界是物件；規劃分區、熱點與跨物件行為，不能當全系統自動序列化 |
| [Queues](https://developers.cloudflare.com/queues/) | 非同步訊息、批次、重試、延遲與死信處理 | 請求外工作、緩衝突發流量 | 業務冪等、重複投遞、重試耗盡與保留期限需要設計 |
| [Workflows](https://developers.cloudflare.com/workflows/) | 持久多步工作、重試、等待事件 | 長流程、人工核准、可恢復處理管線 | 步驟副作用必須可安全重試；不必把每個快速 API 都改成 workflow |
| [Hyperdrive](https://developers.cloudflare.com/hyperdrive/) | 連接既有 PostgreSQL／MySQL 的連線池與查詢快取 | 保留既有資料庫，讓 Workers 存取 | 不是主資料庫；快取依敏感度與一致性需求配置，核對驅動相容性 |
| [Workers AI](https://developers.cloudflare.com/workers-ai/) | 受管模型推論 | 模型目錄符合產品需求的 AI 功能 | 逐模型評估品質、語言、延遲、資料政策、可用性與費用，不保證任意模型皆可部署 |
| [Vectorize](https://developers.cloudflare.com/vectorize/) | 向量索引與相似度查詢 | 語意搜尋、RAG | embeddings、維度、更新／刪除、租戶過濾與評估集需另外設計 |
| [Turnstile](https://developers.cloudflare.com/turnstile/) | 公開互動的防濫用訊號 | 登入、註冊、表單、敏感提交 | 不是帳號、session 或授權服務；前端 widget 之外必須伺服器驗證 |
| [Cloudflare One：Access／Tunnel](https://developers.cloudflare.com/cloudflare-one/) | 應用存取政策與私有服務連接 | 員工／合作方使用的內部工具 | Tunnel 提供連接，不等於授權；Access 不自動補齊消費者帳號生命週期 |

## 開發平台增補（2026-10-02）

| 候選與官方來源 | 負責什麼 | 何時考慮 | 限制與評估重點 |
|---|---|---|---|
| [AI Gateway](https://developers.cloudflare.com/ai-gateway/) | 模型請求的觀測、快取、限流與路由 | 多模型供應商、成本與失敗處理 | 不提供應用帳號或自動批准模型替換；快取、日誌敏感資料與各功能成熟度分開核對 |
| [AI Search](https://developers.cloudflare.com/ai-search/) | 受管資料索引、檢索與 RAG | 希望減少索引管線維護的搜尋產品 | 與自行組合 Vectorize 比較；來源權限、租戶隔離、更新／刪除、API 遷移與品質仍需驗證 |
| [Agents SDK](https://developers.cloudflare.com/agents/) | Agent 的持久身分、狀態、連線、排程與恢復 | 有持久互動或工具呼叫的應用 | Agent loop、模型、工具授權和外部動作仍要另外設計；不等於本次開發代理的 runtime |
| [MCP handler APIs](https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/) | 建置產品需要的 MCP 服務 | 產品明確需要向 MCP client 提供工具 | 核對 transport、OAuth、session 與副作用授權；不是設計參考網站的連接方式 |
| [Browser Run](https://developers.cloudflare.com/browser-run/) | 受管 headless Chrome、截圖、PDF 與自動化 | 程式化瀏覽器工作 | 原名 Browser Rendering；分清 Quick Actions 與長 session，評估登入資料、逾時、並行、費用與清理 |
| [Sandboxes](https://developers.cloudflare.com/sandbox/) | 隔離執行生成或使用者提供的程式 | Agent runner、資料分析、預覽與建置 | 依工作選 Linux container 或 Dynamic Worker；限制網路、憑證、資源與存活時間，核對目前 SDK／遷移路線 |
| [Containers](https://developers.cloudflare.com/containers/) | 執行自訂 Linux image 與程序 | Worker isolate 無法滿足的 native／長程序需求 | 映像、冷啟動、排程、持久檔案、故障與終止各自驗證；不假設是完整 Kubernetes 平台 |
| [Email Service](https://developers.cloudflare.com/email-service/) | Email Sending 與 Email Routing | 交易郵件、通知、來信處理 | DNS／寄件者驗證、送達、退信／suppression 與帳號限制；Routing 本身不代表可任意對外寄信 |
| [Images](https://developers.cloudflare.com/images/)／[Stream](https://developers.cloudflare.com/stream/) | 圖片處理／交付與影片上傳、編碼、播放 | 需要媒體管線的產品 | 與 R2 檔案儲存分開；核對 signed delivery、媒體權限、轉換、播放成本與刪除 |
| [Basin](https://developers.cloudflare.com/basin/) | Pipelines 收集／轉換、Catalog 管 Iceberg tables、SQL 作 OLAP 分析 | 事件與分析資料平台 | 原 Cloudflare Data Platform：Pipelines、R2 Data Catalog、R2 SQL 已更名；不當交易型 D1／PostgreSQL 替代 |
| [K2](https://developers.cloudflare.com/k2/) | 持久事件 log 與獨立訂閱消費 | 需要保留、重讀或多消費者的事件 | 與工作佇列分開比較；設計 retention、offset、重複、重放、排序邊界與帳號限制 |
| [Artifacts](https://developers.cloudflare.com/artifacts/) | Git 相容的版本化檔案與 repository 儲存 | 使用者程式、專案或 Agent 工作樹 | 不等於完整 GitHub 工作流程；權限、匯出、事件、保存、費用與 push／部署授權分開 |
| [Workers Cache API](https://developers.cloudflare.com/workers/runtime-apis/cache/) | 程式控制回應快取 | 明確可快取的 HTTP 輸出 | 不當持久或強一致資料來源；確認快取位置、key、私人回應隔離與失效語意 |
| [Workers Analytics Engine](https://developers.cloudflare.com/analytics/analytics-engine/)／[Observability](https://developers.cloudflare.com/workers/observability/) | 自訂事件分析與 Worker logs／traces | 產品事件、錯誤與服務觀測 | sampling、查詢、保留、敏感資料與成本分開核對；不是所有業務資料的永久來源 |
| [Pages](https://developers.cloudflare.com/pages/) | 網站部署的另一條平台路線 | 維護既有 Pages 或 owner 明確選用 | 新選型仍遵守現有 frontend 平台規則；Pages 與 Workers 的 bindings、SSR、預覽與遷移不可假設等價 |

DNS／CDN、WAF 與 Cloudflare One 是另有方案、政策和權限的產品層。按 [Security](security.md)、[Deployment](deployment.md) 與 [Operations](operations.md) 的需要選取，不由選用 Workers 一併批准或啟用。

### 當日成熟度與遷移紀錄

| 觀察日期 | 官方觀察 | 採用時的處理 |
|---|---|---|
| 2026-10-02 | [Basin](https://developers.cloudflare.com/basin/) 於 2026-10-01 GA；保留舊資源／配置的相容路線 | 新文件使用 Basin 名稱；不自動改既有 bindings 或搬資料 |
| 2026-10-02 | [K2](https://developers.cloudflare.com/k2/) 是 public beta；[Artifacts](https://developers.cloudflare.com/changelog/product/artifacts/) 於 2026-10-01 open beta | 先核對帳號、費用與限制；Beta 不等於專案已批准用於正式產品 |
| 2026-10-02 | [McpAgent](https://developers.cloudflare.com/agents/model-context-protocol/apis/agent-api/) 已 deprecated、feature-frozen | 新服務核對 `createMcpHandler`；既有 stateful server 依官方指南分階段遷移，不直接換 import |
| 2026-10-02 | [Sandboxes](https://developers.cloudflare.com/sandbox/) 區分目前 API、Dynamic Workers 與 SDK 0.x 遷移；Durable Object container scheduling 是 public beta | 先辨識已用版本與執行模型；不把 stable／next skill 名稱當目前 runtime 狀態 |

以上是當日觀察；採用時重查 changelog、release／SDK、方案與 limits。未列明 GA 不代表已證明 GA，也不將整個 Cloudflare 的成熟度套到每項功能。

## 最容易混淆的邊界

- KV 採最終一致，可能讀到舊值；即使同區域也不能自行假設即時可見。快取失效要有產品可接受的行為。見 [KV 如何運作](https://developers.cloudflare.com/kv/concepts/how-kv-works/)。
- Durable Objects 管協調，Queues 傳遞工作，Workflows 管持久步驟；可以組合，但不是三個同義選項。
- D1 管關聯資料，R2 管物件，Vectorize 管向量索引。資料來源、索引與檔案之間仍要處理刪除同步與存取權。
- Hyperdrive 保留外部 DB 作為資料來源，並可能快取查詢結果；不能寫成「完全不存資料」。
- Turnstile token 必須由後端驗證，失敗、重複與過期路徑都要處理；防濫用仍需配合適合產品的速率限制與授權。見 [伺服器驗證](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)。
- Access 常用於受保護應用的政策存取；消費者登入要另評估帳號、恢復、組織、session 與產品權限。見 [Authentication 參考](authentication-and-identity.md)。

## 九種條件式組合

| 情境 | 候選組合 | 採用前要成立的條件 |
|---|---|---|
| 展示網站＋少量 API | Workers／Static Assets | 框架輸出、SSR／快取與預覽部署經過驗證；純靜態網站不必額外引入 DB |
| 可容忍舊值的設定 | Workers＋KV | 明確定義可接受的更新延遲與失效行為 |
| 新 SQL 應用 | Workers＋D1 | SQLite 語意與服務限制符合需求，還原演練可通過 |
| 已有 PostgreSQL／MySQL | Workers＋Hyperdrive＋既有 DB | 連線、查詢快取與跨區延遲實測可接受；不為統一品牌搬資料 |
| 即時協作房間 | Workers＋Durable Objects | 能按房間／實體切分狀態，重連與熱點有解法 |
| 匯入、通知、背景任務 | Workers＋Queues；需要時加 Workflows | 訊息冪等、重試耗盡、死信與人工補救已定義 |
| 多步媒體處理＋核准 | Workflows＋R2＋選定推論服務 | 等待、逾時、取消、重試與發布授權分開；推論服務不限定 Workers AI |
| RAG／語意搜尋 | Vectorize＋選定 embeddings＋資料來源 | 品質評估、租戶隔離、來源權限與刪除同步已定義；資料來源不限平台內 |
| 公開提交／內部後台 | 公開端評估 Turnstile；內部端評估 Access＋Tunnel | 依使用者與威脅模型分別選擇，可同時存在；都不能取代業務授權 |

增補的條件式組合：TanStack Start＋Workers＋按需求選的 D1／R2；Agents SDK＋Browser Run／Sandboxes；AI Search 或自組 Vectorize 檢索；K2＋Basin 分析；Email Service＋Queues 通知。各層獨立選用；TanStack Query 不是資料庫，AI Gateway 不是推論模型，分析 SQL 不是交易資料庫。這些是比較方案，未在本輪建立或部署。

## 框架、CLI 與可安裝內容

| 候選與官方來源 | 角色與採用檢查 |
|---|---|
| [TanStack Start on Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/tanstack-start/)／[Vite plugin](https://developers.cloudflare.com/workers/vite-plugin/) | 應用框架與 workerd 整合分開；核對目前 `@cloudflare/vite-plugin`、SSR、bindings、compatibility date 和部署 adapter |
| [Next.js on Workers](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/)／[vinext](https://github.com/cloudflare/vinext) | 官方目前推薦 vinext，但 upstream 明列 Next.js 相容缺口；是 Vite 上的 API 重實作，不將其描述為所有 Next.js 專案的直接替換。既有 OpenNext 有維護路線，保留已批准方案 |
| [Wrangler](https://developers.cloudflare.com/workers/wrangler/)／[Cloudflare CLI `cf`](https://developers.cloudflare.com/cf/) | Wrangler 維護既有 Worker 配置；`cf` 涵蓋 Cloudflare API 與 Workers 專案，當日為 beta。可並用資源命令；專案 build／dev／deploy 的轉換需依官方 migration，不自行改現有配置 |
| [Void](https://void.cloud/guide/quickstart) | 專案本機 full-stack SDK／CLI，可保留 framework routing 或使用 native Void routing；direct Cloudflare 是 `cloudflare` target，team Void platform 是另一個 deployment 決策。核對 init／migrate 的 manifest、config、AGENTS 與 skill-link diff，固定 matching package／CLI 版本，並檢查 [deployment](https://void.cloud/guide/deployment) 的 resources、migrations、secrets 與 rollback |
| [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) | Tunnel 連接工具，與前兩個管理／開發 CLI 分工不同 |
| [Cloudflare Skills](https://github.com/cloudflare/skills)／[vinext Agent Skill](https://github.com/cloudflare/vinext#optional-migrate-with-an-ai-agent) | Skills 是開發指引，npm package 是應用／CLI 依賴；MCP server 是另一種連接。按實際 runtime 盤點 installed／loaded 身分與版本，只選需要的項目，不從本目錄推定已安裝或啟用 |

可比較的技能包含 `cloudflare`、`basin`、`k2`、`nextjs-on-cloudflare`、`agents-sdk`、`durable-objects`、`workers-best-practices`、`wrangler`、`cloudflare-email-service`、`turnstile-spin`、`web-perf`、`cloudflare-one`、`cloudflare-one-migrations` 與 Sandbox stable／next／migration 路線。使用前核對上游與本地內容；preview、stable 與舊 SDK 的差異以目前官方文件為準。這裡新增候選與來源，不執行 installer、遷移或任何帳號動作。

## 平台外與混合路線

先對照 [部署](deployment.md)、[runtime](runtime-selection.md)、[資料儲存](data-storage.md) 與 [agentic](ai-agentic.md) 的候選，保留既有可用基礎。網站可比較其他託管平台；既有 SQL 可保留；物件儲存可比較 S3 類服務；持久流程可比較 Temporal 類方案。這些是比較方向，不宣稱 API、交易語意、維運責任或費用等價。

不要把 KV 與 Redis、Durable Objects 與一般資料庫直接畫等號。先寫清楚需要快取、原子操作、協調、查詢還是持久工作，再比較實作。選擇 Cloudflare 某項產品不要求 DNS、身分、資料庫和模型一起遷移。

## 整合、維運與成本

[Wrangler](https://developers.cloudflare.com/workers/wrangler/) 是開發與管理工具的候選入口。採用時核對版本、compatibility date／flags、bindings、環境隔離、secret 管理、預覽與正式資源分離。參考文件不執行部署指令，也不帶入真實憑證。

R2 的公開讀取、CORS 與簽名存取必須按實際流程配置；不要為了讓瀏覽器讀取而直接公開私人 bucket。Queues／Workflows 需要監控失敗、補償與重放。資料服務需要备份、還原演練、刪除保留政策與租戶隔離證據。詳見 [Security](security.md) 與 [Operations](operations.md)。

成本表至少列請求、執行資源、資料庫讀寫／容量、儲存與操作、訊息、持久步驟、推論、向量與可觀測性。以當時官方 Pricing／Limits 及帳號方案核對；不要把單一產品的免 egress 敘述解讀為整套零成本。這份文件不固定價格、免費額度或 Beta／GA 狀態。

## 進入與退出成本

進入時測試 Node 相容性、框架 adapter、驅動、長連線與背景任務限制。既有 DB 透過 Hyperdrive 接入仍需測試，不是無成本搬接。

退出時分開估算資料匯出、索引重建、物件權限、bindings 改寫與協調／工作流語意遷移。提供匯出工具不代表零停機或權限設定可原樣轉移；保留還原與回滾演練結果。

## PRD 對答與驗收建議

先問：服務對象與主要地區？資料居留限制？現有 DB 能否保留？哪些操作要求強一致？可接受多少舊值？是否等待人審？模型與來源資料能否外送？預估尖峰、成本上限及故障恢復要求？

| 領域 | 採用前的代表性驗證 |
|---|---|
| Workers／資產 | 代表路由、SSR、快取、錯誤頁、預覽與正式環境隔離 |
| D1／Hyperdrive | 代表查詢、交易需求、遷移／還原、突發連線、快取舊值 |
| KV／Durable Objects | 舊值處理、同實體併發、跨實體邊界、热點與重連 |
| R2 | 私人檔案不可越權讀取，上傳限制、CORS、刪除與還原 |
| Queues／Workflows | 重複、失敗重試、死信、逾時、取消、重放不重複扣款／發布 |
| AI／Vectorize | 品質與延遲、越權檢索、租戶過濾、刪除同步、費用上限 |
| Turnstile／Access | 後端驗證失敗、過期／重複 token、存取拒絕、登入恢復與無障礙 |

以上是建議測試，不表示已實作或通過。Cloudflare One 的產品方向已確認；具體 Access／Tunnel 配置、帳號條件與限制在選用時補查。D1／Durable Objects 的正文已補查。來源連結集中於上表及 [Sources](sources.md)。
