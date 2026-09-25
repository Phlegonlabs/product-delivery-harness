# 後端框架參考

狀態：Reference only · 核對日期：2026-09-25

本文件是決策前的參考素材，不是技術棧決定、強制規範或安裝授權。任何選項採納與否由專案自身的 PRD 與既有驗收記錄決定；未採納項目不生效，本文件也不改變任何 skill 流程。

## PRD 需先回答的問題

以下問題是本文件對 PRD 應回答事項的整理，非 PRD 原文引述：

- 業務規則在哪一層執行：長駐服務、serverless 函式或 managed 平台？
- 交易邊界在哪裡？哪些操作必須原子完成、失敗後如何補償？
- 流量形態：穩定長連線、突發請求、長任務或排程背景工作各佔多少？
- 資料所在地區與延遲要求為何？
- 團隊對 Python、TypeScript、C#、Go 的熟悉度與維運能力？
- 認證、授權與第三方整合是否依賴特定生態？

## 候選比較矩陣

以下六個候選涵蓋不同語言與框架範圍。基本定位已補查官方文件；適配、成本與遷移評估是整理判斷。Go 是語言與標準庫路線，不是同一層級的全功能框架。

| 候選 | 型態 | 已核對能力摘要 | 適配方向 | 來源狀態 |
| --- | --- | --- | --- | --- |
| FastAPI | Python API 框架 | 以 OpenAPI/JSON Schema 為基礎，預設提供 Swagger UI 與 ReDoc 互動文件；Pydantic 驗證涵蓋 URL、email、UUID 等；支援 OAuth2+JWT、API key、HTTP Basic；依賴注入支援巢狀子依賴；承襲 Starlette 的 WebSocket、in-process 背景任務、啟停事件、CORS、串流與 session | 型別清楚的 JSON API，需要自動文件與客戶端生成 | [官方 features 頁](https://fastapi.tiangolo.com/features/)已核對 |
| Django | Python 全功能框架 | ORM 以 Python 描述模型；`makemigrations`/`migrate` 產生並執行結構變更；QuerySet 自動生成資料 API，關聯查詢由框架產生 JOIN | 內容型應用、管理介面需求重、資料層想集中寫 Python | [官方 5.2 overview](https://docs.djangoproject.com/en/5.2/intro/overview/)已核對 |
| NestJS | TypeScript 模組化框架 | Node.js 伺服器框架，支援 TypeScript；預設使用 Express，可改用 Fastify | TypeScript 全端一致性 | [官方文件](https://docs.nestjs.com/)基本定位已核對 |
| Hono | TypeScript Web 框架 | 以 Web Standards 為基礎，提供 middleware 與多 runtime 部署路線 | Edge runtime 與 request 型 serverless | [官方文件](https://hono.dev/docs)基本定位已核對 |
| ASP.NET Core | C# 跨平台 Web 框架 | 提供 HTTP pipeline、驗證授權及 logging/tracing/metrics 整合能力 | 微軟生態或既有 C# 團隊 | [官方 overview](https://learn.microsoft.com/en-us/aspnet/core/introduction-to-aspnet-core)基本定位已核對 |
| Go | 編譯語言，常以標準庫自組服務 | 編譯式語言，提供並行機制、標準庫與測試工具；應用框架可另選 | 高併發入口、單二進位部署 | [官方文件](https://go.dev/doc/)基本定位已核對 |

## 各選項評估（推論與整理）

除標注引用處外，本節為推論，採納前需以官方文件與實測確認。

### FastAPI

- 適配：請求驗證與 API 文件是核心痛點的服務；Pydantic 模型可重用於資料層邊界。
- 避免條件：大量同步阻塞套件且未規劃執行緒或 worker 策略時，async 優勢難以兌現（推論）。
- 架構義務：需自選 ASGI 伺服器與部署拓撲；框架未提供資料庫遷移工具，須另外選定；背景任務為 in-process，重任務需外部 worker（來源僅確認 in-process 存在）。
- 維運成本：長駐行程需管理連線池與水平擴展；官方效能主張為頁面自述，不代表本專案實測。
- 遷移：OpenAPI 可保留外部契約，但 Pydantic 模型、依賴注入與應用邏輯仍要改寫；沒有普遍適用的「低鎖定」結論。

### Django

- 適配：資料模型即產品、需要一致遷移紀律的專案；ORM 查詢降低 SQL 負擔（已核對部分）。
- 避免條件：只需要薄 JSON API 時，全框架慣例可能偏重（推論）。
- 架構義務：schema 變更走 models 定義與 migrate 流程，既有資料庫需對齊此流程；非同步能力不在收錄頁面範圍，採納前須查證。
- 維運成本：長駐服務部署；收錄文件版本為 5.2（頁面 metadata），升級節奏需另行確認。
- 遷移鎖定：中。ORM 把 schema 與 Django 慣例綁在一起，換框架需重寫資料層（推論）。

### NestJS

適合 TypeScript 團隊希望以一致的 modules/providers/controllers 管理成長中的 API；若只是幾條 proxy route，額外框架慣例可能不划算。採納時選 Express 或 Fastify adapter，確認 middleware、驗證、ORM、migration 與 queue 整合。成本來自模組治理、啟動與依賴升級；遷移時 controller、decorator、DI 邊界需要調整，業務規則可盡量留在普通模組。[官方介紹](https://docs.nestjs.com/)

### Hono

適合薄 API、edge gateway 或多 runtime 候選；若想要完整 ORM/admin/job 系統，需比較自行組裝成本。框架的跨 runtime 支援不代表所有第三方套件相容。採納時逐一核對 adapter、authentication middleware、schema validation、DB driver 與背景工作機制。平台 bindings 往往比路由本身更難搬移；成本要看宿主、外部 DB 與網路。[官方介紹](https://hono.dev/docs)

### ASP.NET Core

適合 C# 團隊、既有 .NET domain library 或企業整合；若團隊只熟其他語言，先衡量學習與維護成本。確認 middleware 次序、DI lifetime、資料存取、驗證授權、background service 與 runtime 支援期。可比較雲端或自管部署；使用 ASP.NET Core 不等於必須用 Azure。遷移主要牽涉 .NET 元件與資料層，標準 HTTP 契約可獨立保留。[官方概覽](https://learn.microsoft.com/en-us/aspnet/core/overview?view=aspnetcore-10.0)

### Go／標準庫路線

適合已有 Go 能力、重視明確 process 模型與服務資源使用的團隊；不因「編譯語言」就推定比其他方案快。需自行選擇 router、輸入驗證、DB migration、auth、觀測與錯誤契約。驗證 goroutine 退出、context cancellation、連線池、shutdown 及 native/CGO 相依。編譯產物可簡化部分交付，但不消除 OS/library 依賴；維護成本在自組套件與團隊慣例。[官方文件](https://go.dev/doc/)

## 情境建議（條件式示例，非預設）

1. 若 PRD 是內容型網站加管理後台、資料以關聯為主，且團隊熟 Python：Django 為第一候選，先用 migrate 流程驗證 schema 紀律；若只需要 JSON API，改評 FastAPI。
2. 若部署目標是 edge 或突發型 serverless，且前端已是 TypeScript：先驗證 Hono 的 runtime 相容矩陣（待驗證）；FastAPI/Django 路線需評估冷啟動與資料庫連線模式（推論）。
3. 若有高併發網關或 CPU 密集處理，且團隊已會 Go：Go 進入候選，但須補官方文件驗證與效能實測；不因「聽說快」而採納。

## 失敗與驗證清單

- 每項能力引用是否都有官方來源？二手比較文不採。
- 文件版本與專案鎖定版本是否一致？Django 5.2 與 aspnetcore-10.0 只是版本線索。
- 授權條款是否核對？本輪未核對，採納前必查。
- 官方效能主張是否以本專案工作負載實測取代？
- runtime 相容性（套件、原生依賴、serverless 限制）是否實測？
- 決策是否分層記錄：runtime、框架、資料庫、認證、jobs 各自獨立？

## 來源範圍與採納前核對

六個方案的基本定位均已有官方來源。適配、避免條件、遷移風險與成本維度為研究判斷；未在目標工作負載做效能或相容性測試。Django 來源固定在 5.2，ASP.NET Core 概覽目前導向 10.0；這不代表替專案選定版本。實際採納時核對支援期、授權、宿主限制、資料庫 driver、auth SDK 與測試方案。

## 採納記錄對應

採納時在既有專案文件（PRD、`sources.md`、既有 stack 盤點）記錄，分開記 topology、runtime、框架、資料庫類型、認證授權、API 風格與 jobs；供應商 bundle 不代替分層決策。本參考不新增審批閘門。相關文件：[API](api.md)、[資料](data-storage.md)、[部署](deployment.md)、[Integrations](integrations.md)、[安全](security.md)。
