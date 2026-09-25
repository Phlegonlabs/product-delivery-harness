# Runtime 選擇參考

狀態：Reference only · 核對日期：2026-09-25

本文件比較產品 runtime、agentic runtime 與當次開發執行環境，不指定技術棧，也不授權安裝、採用或改變 skill 流程。被專案採納後才成為該專案決策。

## 三種決策不可混用

產品 runtime 決定服務實際使用的語言、執行模型、相容性、狀態與部署形狀。Agentic runtime 決定 agent 的 orchestration、持久狀態、工具、沙箱、模型邊界與可靠性行為。當次 coding host/model/worker 決定這次任務可用的工作目錄、讀寫範圍、網路、工具、模型與完成訊號。產品 runtime 與 agentic runtime 都可成為產品架構的一部分；coding host/model/worker 是本次交付環境。三者分別驗證。

## PRD 需要回答的問題

要確認：語言與既有相依；npm、PyPI 或 native extension 是否關鍵；request、長駐、排程、佇列哪種執行模型；需要 CPU 時間、wall time、記憶體、檔案、process、thread 或 network 的哪些能力；狀態放哪裡；是否需要固定版本或固定區域；錯誤、重試、逾時與冷啟動如何驗收；agent 是否需要工具、瀏覽器、檔案或外部服務；模型輸出失敗時如何保存部分成果；host、model、worker、工具、權限與結果如何紀錄。

## 候選比較

| 選項 | 適合條件 | 避免條件與待驗證點 | 架構與營運義務 |
| --- | --- | --- | --- |
| Node.js 官方 runtime | 適合已有 npm 生態、明確 Node 版本、可自管容器或 VM 的服務。官方介紹確認 V8 與非阻塞 I/O 模型；CPU 密集工作仍需另設隔離與資源策略。 | 選 LTS、套件 native binding、background thread、file system、network 與 process 行為都要在實際目標 host 驗證。 | 鎖定版本與 lockfile、分離 build/test/runtime 階段、限制 secrets 與網路、量測記憶體與 CPU、設計 graceful shutdown。 |
| Deno | 適合作為可獨立驗證的 TypeScript runtime 候選。官方說明原生執行 TypeScript、Node/npm 整合、內建測試/格式化，以及需授權的資源存取。 | 不能假定它完整相容既有 Node 套件或部署目標。必須先驗證 import map、權限模型、native extension、framework adapter、observability 與部署 runtime。 | 驗證版本升級策略、權限邊界、任務逾時、日誌、trace、測試與容器化需求。 |
| Bun | 適合作為需要快速驗證的 JavaScript runtime 候選。官方 runtime 文件確認可執行 JS/TS/JSX 與 package scripts；不把官方啟動 benchmark 當成產品效能承諾。 | 不能用「相容 Node」作為結論；應逐套件驗證 API、worker、檔案、網路、native addon 與測試工具。 | 鎖定 Bun 版本、記錄套件相容矩陣、單獨驗證 build 與 runtime 差異、確認回滾版本。 |
| Python | 適合資料、模型、腳本或既有 Python 服務。先區分一般 CPython 在容器／VM 的部署與平台特定 Python runtime，兩者的套件和 OS 能力不自動等價。 | C extension、系統相依、長時間計算、GPU、多 process 與固定 Python 版本不應直接假設能在 Workers 執行；容器/VM 候選仍待部署側驗證。 | 鎖定 Python 版本、依賴 hash、虛擬環境或 image、native wheel、測試矩陣、排程與 timeout。 |
| Cloudflare Workers | 適合事件驅動 HTTP 服務。官方文件說明 Workers 的 Node API 支援是子集合；一部分原生支援，一部分部分支援，另一部分由 Wrangler polyfill 或 stub。 | 不能宣稱 Node 套件都能跑。需要注意 stub 可能只讓 import 成功、呼叫後失敗；資源、啟動、bundle 與各種觸發器的時間限制要按當時平台文件確認。 | 先做相容性測試；記錄 compatibility date、正負旗標、依賴清單、錯誤訊號、log、trace、CPU 觀察與回滾版本。CPU 與 wall time 分開量測。 |

## 事實與推論分界

Cloudflare Workers、Workers limits、compatibility flags、Python Workers 與 Cloudflare changelog 的能力描述來自官方內文。Node.js、Deno 與 Bun 官方正文已補查。具體套件相容性仍需測試。跨 runtime 的風險判斷、容器優先、工具沙箱與紀錄設計是研究推論，不是已驗證的平台結論。

## 成本與移轉差異（整理判斷）

| Runtime | 成本／維護來源 | 移轉邊界 |
| --- | --- | --- |
| Node.js | host CPU/RAM、依賴修補、LTS 升級、event-loop 監測 | Node API、native addons、CJS/ESM 與環境依賴 |
| Deno | host、權限設定、npm 相容驗證、工具鏈重整 | Deno API、imports/permissions、npm 套件行為 |
| Bun | host、相容測試、工具鏈與 runtime 分階段升级 | Bun API、lockfile、測試與 Node 行為差異 |
| Python | host、wheel/系統庫、CPU/GPU、process/worker 維護 | Python 版本、native wheels、模型與資料相依 |
| Workers | requests/compute、bindings、外部資料、觀測 | isolate API、compatibility flags、供應商服務 |

使用 Bun 安裝套件不代表生產已改為 Bun；用 Node 建置也不代表成品一定在 Node 執行。保留 build、test、production 三份實際能力記錄，比只寫一個 runtime 名稱更清楚。

## 三個條件式情境

1. 若服務是短 HTTP request、依賴少量 npm API，先在 Workers 的一組 compatibility date/flag 下測 Buffer、crypto、fs、HTTP、process 與目標套件；通過才進產品 runtime 決策。
2. 若目標套件依賴 Node 專有 API、native addon、child process、長駐 socket 或本地檔案，不要先押 Workers；以 Node 官方 runtime 或容器/VM 候選做隔離測試，再決定 Render、ECS/Fargate 或 Fly 是否可行。
3. 若是 Python 資料或模型工作，先確認 wheel、Python 版本、CPU/wall time 與外部資料庫；Workers Python 路線只能在小 dependency 的 request 服務上驗證，不能自動取代容器路線。

## Agentic runtime 與當次執行

Agentic runtime 要分開記錄：planner、executor、工具伺服器、瀏覽器、檔案沙箱、網路範圍、credential、重試與終止條件。當次執行要記錄 host、model ID、worker 類型、實際工具可用性、輸入範圍、逾時、部分成果位置與驗證結果。供應商名稱或 worker 標籤不是能力證據；能力必須在當次任務裡觀察。一次失敗不應默默換 provider，換 provider 要有預先記錄的條件與授權。

## 驗證與失敗檢查

每個 runtime 候選留下：版本、OS/image、依賴 lockfile、相容日期或旗標、請求與背景兩種測試、逾時值、CPU 與 wall time 分開量測、記憶體峰值、錯誤輸出、log 來源、回滾方式。Agentic 執行另留：模型 ID、worker ID、工具版本、網路與寫入邊界、prompt/task hash、部分成果檔、完成證據。失敗要分為 runtime 缺 API、依賴不相容、資源限制、網路阻擋、權限、模型品質或工具失效。

## 採納紀錄

產品 runtime 決策進入既有 architecture 或 stack-decisions；agentic 行為進入既有 ai-agentic 或 agent 設計；runtime adapter、效能與升級仍沿用 runtime-adapters、runtime-performance、runtime-upgrades。當次執行能力記在任務紀錄或 RUN，不回寫成產品需求。所有引用為 advisory：[Node.js introduction](https://nodejs.org/learn/getting-started/introduction-to-nodejs)、[Deno runtime](https://docs.deno.com/runtime/)、[Bun Runtime](https://bun.com/docs/runtime)、[Cloudflare Node.js compatibility](https://developers.cloudflare.com/workers/runtime-apis/nodejs/)、[Cloudflare compatibility flags](https://developers.cloudflare.com/workers/configuration/compatibility-flags/)、[Cloudflare Workers limits](https://developers.cloudflare.com/workers/platform/limits/)。

## Cloudflare 可選組合

平台內產品的責任邊界、搭配與替代路線見 [Cloudflare 參考](cloudflare-platform.md)。可只採用其中一項，不代表整套遷入 Cloudflare。
