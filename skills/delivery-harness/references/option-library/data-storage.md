# 資料儲存參考

狀態：Reference only · 核對日期：2026-09-25

本文件是決策前的參考素材，不是資料庫選型決定或安裝授權。採納由專案 PRD 與既有驗收記錄決定；未採納項目不生效，本文件不改變 skill 流程。先分清主資料、快取、附件與衍生索引；D1 的 SQLite 語意不代表部署和備份模型等同本機 SQLite。

## PRD 需先回答的問題

- 資料實體有哪些？各自的擁有者與生命週期？
- 主要讀寫模式：依 id 取單一聚合、多表關聯查詢、範圍掃描或全文檢索？
- 哪些寫入需要跨實體交易與約束？
- 規模成長曲線與可接受延遲？
- 各類資料的可丟失程度？備份與恢復目標？
- 資料地區、保留與刪除義務？
- 附件、快取、搜尋索引與主資料的責任邊界？

## 候選比較矩陣

以下選項分屬關聯資料、文件資料、快取與物件層，常可組合。基本定位已補查；工作負載適配為整理判斷。

| 候選 | 型態 | 已核對能力摘要 | 適配方向 | 來源狀態 |
| --- | --- | --- | --- | --- |
| PostgreSQL | 關聯式資料庫 | 關聯式 SQL 路線；官方教學涵蓋查詢、JOIN、外鍵與交易 | 強關聯、交易與約束為核心的系統 | [官方教學](https://www.postgresql.org/docs/current/tutorial.html)基本定位已核對 |
| SQLite | 內嵌式關聯資料庫 | 提供應用／裝置的本機資料儲存；官方提醒大量跨網路共享寫入宜比較 client/server DB | 單機工具、離線與本機持久化 | [官方頁](https://www.sqlite.org/whentouse.html)基本定位已核對 |
| Cloudflare D1 | 雲端 SQL 資料庫服務 | managed serverless SQL，採 SQLite 語意，透過 Workers/HTTP API 存取 | Cloudflare Workers 生態內的 SQL 需求 | [官方概覽](https://developers.cloudflare.com/d1/)基本定位已核對 |
| MongoDB | 文件型資料庫 | 彈性 schema；「一起讀的資料放一起」原則；embed 與 reference 二選一建模；標準 collection 每文件必有唯一 `_id` 主鍵；支援 Decimal128；schema 驗證可只加在需要的部分 | 聚合式讀寫、欄位異質、多型文件 | 多頁官方文件已核對（見下節） |
| Redis | 記憶體導向資料儲存 | 官方型別比較頁列出 Strings、Hashes、JSON、Lists、Sets、Sorted sets、Streams，以及地理、機率、時序、向量等特化型別；各型別在效能、記憶體與功能上有取捨；Streams 提供 consumer group；投遞／重送結果仍取決於 ack、pending recovery、持久化與故障設定 | 快取、計數器、佇列、排行榜 | [官方比較頁](https://redis.io/docs/latest/develop/data-types/compare-data-types/)已核對 |
| Amazon S3／物件儲存 | 物件儲存服務 | bucket/object 模型，提供存取政策、版本與生命週期管理 | 圖片、附件、大型二進位物件 | [官方頁](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)基本定位已核對 |

## 各選項評估（推論與整理）

### MongoDB

- 已核對依據：彈性 schema 與 embed/reference 原則出自[資料建模概念](https://www.mongodb.com/docs/v8.0/data-modeling/concepts/)；四步設計流程與「生產規模 schema 難改」出自[設計流程頁](https://www.mongodb.com/docs/v8.0/data-modeling/schema-design-process/)；多型模式出自[多型資料頁](https://www.mongodb.com/docs/v8.2/data-modeling/design-patterns/polymorphic-data/polymorphic-schema-pattern/)；Atlas ER 工具與「關係僅為標註、不存入資料庫」出自 [Atlas 資料建模](https://www.mongodb.com/docs/atlas/atlas-ui/data-modeling/)；`_id` 主鍵與 Decimal128 出自 [BSON 型別](https://www.mongodb.com/docs/v8.0/reference/bson-types/)。
- 適配：查詢天然以一個聚合為單位、文件欄位異質；官方多型模式允許同一 collection 存不同文件形狀以服務共同查詢。
- 避免條件：核心需求是跨多實體的強約束與多文件交易時（推論，收錄頁未覆蓋交易上限）；團隊無法維持 schema 紀律時——彈性 schema 允許同欄位不同型別，Atlas 分析頁即展示此異質現象。
- 架構義務：生產前先跑 workload 盤點、關係映射、設計模式、索引建立四步；embed 或 reference 按存取模式決定；大型線上 schema 變更困難需前置設計。
- 維運成本：self-host 或 managed 平台二選一，責任邊界不同。
- 遷移鎖定：文件模型與查詢語言是主要鎖定點；關聯式轉入可用官方 [Relational Migrator](https://www.mongodb.com/docs/relational-migrator/mapping-rules/introduction/) 的 mapping rules（含型別自動對應），反向遷移未在收錄來源確認。

### PostgreSQL

適合交易、關聯與查詢需求交錯的服務；只有本機小資料時，獨立 server 可能增加負擔。採納時設計約束、索引、transaction boundary、connection pool、migration 與備份還原。成本包含儲存、IO、HA、replica 及維護；SQL 較可攜，但 extensions、stored procedures 與 managed 平台功能仍可能綁定。[官方教學](https://www.postgresql.org/docs/current/tutorial.html)

### SQLite

適合離線 App、單機工具、嵌入式持久化，亦可支援適當規模的網站。若多個服務直接透過網路檔案系統共用高寫入 DB，先比較 client/server DB。採納時測寫入競爭、transaction 時間、備份一致性及檔案權限；低維運不等於免備份。往 PostgreSQL 遷移要核對型別、SQL 方言與並發語意。[適用情境](https://www.sqlite.org/whentouse.html)

### Cloudflare D1

適合已選 Workers 的 SQL 需求；大型跨庫交易或特殊擴充先核對實際支援。設計 migrations、bindings、query limits、讀取副本一致性及 Time Travel 恢復流程。成本看讀寫與儲存，不能把本機 SQLite 的效能推定成 D1 配額。SQL 可匯出不代表服務 API、區域、備份和部署無遷移成本。[官方概覽](https://developers.cloudflare.com/d1/)

### Amazon S3／物件儲存

適合附件、圖片與匯出檔；不能當成具有跨物件交易的關聯 DB。設計私有預設、object key、metadata、限時存取、上傳驗證、生命週期與刪除；DB row 與 object 的一致性要有補償。成本包括容量、請求、下載流量、複本與封存取回。S3 API 相容服務仍需逐項確認 IAM、versioning、事件與一致性差異。[S3 概覽](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)

### Redis

- 適配：可重建的讀取加速、計數、排行榜與簡單佇列；型別選擇直接影響記憶體與語義（官方明言各型別有取捨）。
- 避免條件：把快取當主資料庫；持久化、淘汰與故障恢復行為不在收錄頁面範圍，採納前必須核對（推論＋待驗證）。
- 架構義務：明確標示哪些資料可重建；失效策略與重建成本先設計；Streams 消費端需處理 ack、pending 恢復、重複與故障；不能只靠資料型別名稱保證投遞。

## 情境建議（條件式示例，非預設）

1. 若核心實體有強關聯、跨實體交易與報表查詢：關聯式候選優先（例如 PostgreSQL）；Redis 僅作可重建的分層，不承擔主資料。
2. 若讀寫天然以聚合為單位、欄位異質（如不同產品有不同屬性）：MongoDB 為候選；先完成四步 schema 流程與索引計畫，再寫第一行生產碼。
3. 若產品是單機／離線優先工具需要本機持久化：SQLite 為候選；附件走物件儲存層；不要假設之後能把 SQLite 檔直接換成 D1，兩者遷移屬獨立評估。

## 失敗與驗證清單

- 約束與交易是否在並發寫入下實測，而非只看文件？
- 快取失效、過期與重建是否演練？快取資料被當主資料的程式路徑是否存在？
- 刪除義務是否涵蓋主資料、附件、快取、索引與備份政策，而不只是刪一列？
- 遷移是否有演練與回滾路徑？MongoDB 轉入的 mapping rules 是否先行審視？
- 資料地區、保留與租戶隔離要求是否由專案確認？
- 「已核對」與「待驗證」的區分是否在後續決策中被維持？

## 來源範圍與採納前核對

基本儲存模型已補查官方文件，方案建議與成本維度是整理判斷。MongoDB 引用涉及 v8.0/v8.2；需對照實際版本。Redis 作為主資料儲存並非一律禁止，但必須另設持久化、淘汰、備份與可接受資料損失契約；本文情境優先將它當可重建快取。各方案的最新配額、授權、HA、備份保留及 SDK/ORM 相容性仍需採用時確認。

## 採納記錄對應

採納時在既有專案文件（PRD、`sources.md`、既有資料盤點）記錄：主資料來源、識別碼策略、約束、租戶擁有權、遷移次序、備份與恢復目標；物件儲存與快取作為獨立分層分開記錄。本參考不新增審批閘門。相關文件：[後端](backend.md)、[安全](security.md)、[維運](operations.md)。

## Cloudflare 可選組合

平台內產品的責任邊界、搭配與替代路線見 [Cloudflare 參考](cloudflare-platform.md)。可只採用其中一項，不代表整套遷入 Cloudflare。
