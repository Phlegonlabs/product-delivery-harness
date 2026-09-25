# 部署參考

狀態：Reference only · 核對日期：2026-09-25

本文件只提供候選比較與驗證清單，不是技術決策、安裝授權、發佈授權或新流程。若被專案採納，才寫入該專案的部署決策與驗收條件。文中未定案項目不可自動採用。

## PRD 需要先回答的問題

部署前先確認：發佈對象是網站、API、排程工作、佇列、長駐服務還是原生應用；流量與延遲要求；是否有跨區域或資料在地限制；單次請求和背景任務需要多少時間；資料庫與狀態放在哪裡；Secrets、憑證與審批由誰管理；部署權限、預覽環境、回滾和恢復方式；觀測與告警由誰負責；供應商變更時可搬移的邊界在哪裡。

## 候選比較

| 選項 | 適合條件 | 避免條件與待驗證點 | 整合與營運重點 |
| --- | --- | --- | --- |
| Cloudflare Workers | 已選 Web API、isolate 執行模型，需比較全球入口與外部資料存取 | 不假定完整 Node API 相容；依賴 native addon、process、本機持久磁碟時先做 spike | 設定 compatibility date/flags、bindings、secrets 與 rollback；CPU、wall time、bundle、memory、各觸發器限制分別核對。[limits](https://developers.cloudflare.com/workers/platform/limits/) |
| Vercel Functions | Web 框架、API routes、webhook 或串流 request handler | 常駐程序、長任務與特殊網路需求先核對 function/plan 限制；延後執行不等於 durable job | 選 runtime、區域、preview 權限、日誌與 rollback；成本看 compute、requests、頻寬與方案。[Functions](https://vercel.com/docs/functions) |
| Netlify Functions | 靜態／內容站搭配同步或背景函式 | 比較 synchronous、scheduled、background 各自限制；不能用同一 timeout 代表全部 | 核對函式區域、memory、payload、build input 與 secrets；成本看函式、建置與流量。[configuration](https://docs.netlify.com/build/functions/configuration/) |
| Render | 需要平台管理的 Web service 與獨立 background worker | 沒有 backlog、retry 或 restart 設計時，不能把長駐 worker 當完成保證 | 官方 worker 模型可監聽佇列執行異步工作；管理 concurrency、job id、failure recovery 與資源費用。[Workers](https://render.com/docs/background-workers) |
| AWS ECS/Fargate | 已容器化、AWS 網路/IAM 整合、service 或 batch task | 團隊不熟 IAM/VPC/registry/observability 時，前置成本較高；Fargate 不等於任意硬體可用 | ECS 管理容器；Fargate 是其中的 compute 選擇。配置 task definition、roles、網路、health、autoscaling；估算 compute、LB、NAT、logs 和儲存。[ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html) |
| Fly Machines | VM／machine 生命週期路線候選 | 本次官方入口抓取正文不足，啟停、volume、region 具體行為仍待複查，不列為已證實相容方案 | 擬比較 machine lifecycle、image、health、volume、secrets 與故障接手；成本項與功能以當時方案為準。[官方入口](https://fly.io/docs/machines/) |

## 成本、遷移與證據邊界

Workers 的 binding／觸發器、Vercel 的框架整合、Netlify 的建置／函式配置、Render 的服務設定、ECS 的 IAM／網路、Fly 的 machine／volume 模型，都是各自需要盤點的遷移點。容器化通常能保留應用封裝，仍不能自動搬移資料、網路與身分。不要為降低假想鎖定先建多雲抽象層；先記錄可接受耦合和退場步驟。

前五項基本執行模型已補查官方正文；Fly 保留為待核對候選。適配與成本分析是研究判斷。本參考不固定易變的數值限額；採納時依帳號方案、runtime、觸發器與區域記錄數值和查閱日期。

## 三個條件式情境

1. 若 PRD 要求全球低延遲、HTTP 請求短小、資料可透過外部儲存分離，可先在非正式環境驗證 Cloudflare Workers 的 Node 相容性與 limits；驗證失敗就不升級為決策。
2. 若需要既有 Node/Python 容器、長時間 process 或特殊系統相依，AWS ECS/Fargate、Render 或 Fly 應列為待驗證容器路線；比較候選時先用同一工作負載驗證健康檢查、資源、回滾與成本假設。
3. 若主要是靜態站加上小函式，且工作落在所選函式類型的時間與 payload 範圍，Netlify Functions 可進入驗證；若需要在亞洲固定區域或超過 payload 上限，必須另行比較，不把某一預設區域當成所有專案的選擇。

## 驗證與失敗檢查

每個候選至少留下：目標環境 URL、部署 artifact 或 image digest、相容日期或 runtime 版本、secrets 名稱清單但不留值、資料 migration 次序、健康檢查結果、請求/排程/佇列三種路徑測試、timeout 觀察、區域與資料流確認、log/metric 來源、手動回滾證據。失敗時要分類是相容性、資源限制、網路、IAM、區域、狀態損壞或成本觸發，不能只用部署成功代表驗收。

## 移轉與鎖定

搬移成本主要來自平台觸發器、storage binding、secret 管理、routing、proprietary state、build hook 與部署權限模型。建議在設計時保留六個外部介面：database、queue、object storage、auth、observability 與 IaC。這是降低搬移風險的作法，不代表必須一次做多雲。

## 採納紀錄

若採用，部署決策記入該專案既有 architecture 或 stack-decisions 文件；審批與升級邊界沿用 deployment-contract 與 branch-promotion-contract。本參考不改動現有流程，也不自動建立新閘門。所有引用為 advisory：[Cloudflare Workers limits](https://developers.cloudflare.com/workers/platform/limits/)、[Cloudflare Node.js compatibility](https://developers.cloudflare.com/workers/runtime-apis/nodejs/)、[Netlify Functions configuration](https://docs.netlify.com/build/functions/configuration/)、[Render Background Workers](https://render.com/docs/background-workers)、[AWS ECS overview](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)、[Fly Machines](https://fly.io/docs/machines/)、[Vercel Functions limitations](https://vercel.com/docs/functions/limitations)。

## Cloudflare 可選組合

平台內產品的責任邊界、搭配與替代路線見 [Cloudflare 參考](cloudflare-platform.md)。可只採用其中一項，不代表整套遷入 Cloudflare。
