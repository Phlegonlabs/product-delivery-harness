# Jolvex 流程修復：parent review 與驗證

分支：`fix-jolvex-flow-skills`。Base：`4cc1b55b33ad09e579f61334160a3ec62dfcd5fe`（0.39.0）。逐階段調查見 [audit.zh-TW.md](audit.zh-TW.md)。

## 修改結果

1. Product Definition 的 Approved option map 共用一個 parser。新格式使用 `||OPT-ID=layer=>selection;layer=>selection||`，可承載規定的商業 layer 名稱及 selection 內的逗號。既有逗號分隔格式仍可讀。完整 map 必須對應實際批准的 option 與 executable layers；批准、repository evidence 與 digest 檢查維持原狀。
2. `inspect_harness_run.py` 從保留的 attempts 列出每個 mission 的 failed dispatch 次數與最新 failure evidence。次數來自紀錄，不從 ID 尾碼推算。歷史 drift、active dirty 與未知的程序狀態有明確區分。工具仍唯讀。
3. 恢復說明先要求確認 host/session 的程序狀態，再走既有 guarded reconciliation；新工作建立新 attempt，既有結果只可記入匹配的 current receipt/lease。不得透過改寫 history、grant 或 verifier context 讓 gate 通過。
4. 同步三份 reference 與四種語言 README。UI impact 為 none，沒有版本 bump。

## Parent review 補強

- 拒絕只有單邊 `||` 的不完整格式與空 selection；加入單一 commercial option、多 layer 的直接回歸案例。
- 最新 `fix_required` 證據不能被較舊的 failure 蓋過；review failure 不應誤增 dispatch 次數。
- 非 list 的 optional attempt history 明確回報 `attempt_log_valid: false`，不拋出例外或假裝有效。
- 恢復提示不再叫使用者直接 reconcile active worker；先確認中斷，並保留 RUN lock 與 current attempt/lease 前提。
- 對同一份 Jolvex RUN 及同一組快取的 Git 觀察，比對修改前後 inspector：所有 mission 的 `needs_reconciliation` 與 warning exit 行為一致。
- 沒有採納 worker 報告中「Jolvex required partner gate 一定因 recommended option 而失敗」的推論。實際完整 approved 檢查仍 PASS；既有 Selected layer 以 repository evidence 支持採用，是現行合約允許的路徑。本輪沒有擴大或改寫批准語意。

## GLM 執行紀錄

使用 `glm-workers` 的外部 dispatcher，model `glm-5.3-flash`，run ID `20260916-083035-ed366d31c5a444f282e1ba556f887e69`。Worker 回傳的聚焦測試為產品 checker 60 個、inspector 8 個通過。

Worker process exit code 為 0，但 dispatcher 最後將本輪 parent 建立的 `research/jolvex-flow-2026-09-16/audit.zh-TW.md` 判為 scope violation，因此 wrapper exit code 為 1。該檔有本 task 的 parent `apply_patch` 建立紀錄，worker 也明示未修改 research。未重新派發 writable worker；parent 檢查完整 diff 並接手補強及驗證。這不是把 wrapper failure 記成成功。

## 驗證

所有 Harness 測試命令都從本分支 worktree root 執行。測試日誌及修改檔 SHA-256 清單位於：

`C:/Users/mps19/AppData/Local/Temp/pdh-jolvex-review-16gbyoc5/`

- 安裝 test requirements：成功，既有套件已滿足需求。
- Parent 聚焦測試：Product checker 62 個 PASS；inspector 9 個 PASS。
- Jolvex 完整 Product Definition approved gate：PASS。
- Jolvex 正式 wireframe filled + approved gate：PASS。
- Jolvex UI Design filled + wireframe + visual approved gate：帶正式 HiFi path，PASS。
- Inspector 同輸入判定相容性：PASS。

| 完整檢查 | 結果 |
| --- | --- |
| check_skill_spec、全範圍 pyflakes、docs_weight、git diff --check | PASS |
| Delivery Harness | 1,014 個；11 skipped，其餘 PASS |
| HARNESS_GOLDEN_PATH=1 | 1 個 PASS |
| Product Definition | 189 個 PASS |
| UI Design | 106 個 PASS |
| Design System Compiler | 93 個；3 skipped，其餘 PASS |
| Product Activation | 56 個 PASS |
| SEO Growth Review | 16 個 PASS |

全部命令 exit 0。完整 suite 期間的 11 份 canonical 修改檔 SHA-256 均未變動。Main suite 耗時約 837 秒；沒有因新一輪精簡 review 修改 source 或使結果失效。

## 保留的界線

- 沒有修改 Jolvex 的產品文件、程式碼、RUN、歷史證據或執行中 worker。
- 沒有安裝 skills，也沒有替 active session 升級版本或更新 pin。
- 沒有建立修復 commit、push、merge、tag，沒有刪除 branch/worktree。
- 本輪是未提交 diff 的 parent review；固定 commit SHA 的 code-security gate 為 UNVALIDATED，不宣稱已有可發布候選。
- Jolvex 的三個 skill pin mismatch、過期文件／缺少 tasks view、舊 Activation seed 與實際 browser journey 待核對範圍，詳見調查報告。歷史缺陷沒有被冒充為目前版本的未修問題。

Gitignore 無需更動：既有 `__pycache__/` 規則涵蓋 Python cache；`.env` 等值檔仍被 ignore，example 例外仍可追蹤；沒有新增 secret 或 dependency 類型。研究報告應留在 Git 可見範圍，驗證 log 留在 checkout 外。
