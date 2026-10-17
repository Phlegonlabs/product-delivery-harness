# Jolvex Harness 流程檢查

檢查日：2026-09-16。範圍是 Jolvex 的交付階段、狀態、腳本與既有證據，並將可重現的共通問題修回 Harness skills。本輪沒有操作 Jolvex 的執行中 RUN，沒有重新跑網站的逐頁瀏覽器測試。

## 檢查基準

以下 RUN 數量與 M3 狀態是初次檢查的 snapshot。Jolvex 的另一個 session 仍在推進工作；約 16:06 UTC 以修復後 inspector 複查時，已有 93 筆 attempts、24 筆 retained failed dispatch（新增 M3 的 3 筆），active wave 為 W6 / M3B，M3B 為 worker_passed，worktree head `f422a5259f29e90dae0813cfae9994a6605da3fd` 且乾淨。主 checkout 仍是下列 `9f34c04…`。因此早先的 M3 dirty 不是本輪確認的「卡死」。

- Jolvex：`m11b2-implementation`，HEAD `9f34c04b3fed8957276d00fcc702e4c97e2c019d`，主 checkout 乾淨。
- Harness 修復：`fix-jolvex-flow-skills`，獨立 worktree，從遠端 main `4cc1b55b33ad09e579f61334160a3ec62dfcd5fe`（0.39.0）開始。
- Jolvex RUN：`RUN-M11B2-IMPL`，PLAN v6 / RUN v11，PLAN revision 19。RUN 記錄使用 Harness 0.38，這是既有 session 的記錄，不代表本輪已驗證該 session 的實際程序或已安裝 skills。
- UI impact：none。這輪修改檢查器、診斷輸出及使用說明，不改產品功能、畫面或批准決策。
- 執行方式：direct；一個 GLM writer 修改 skills，parent 核對 Jolvex 證據、review diff 並驗證。
- Gitignore：新研究報告應追蹤；測試日誌放 checkout 外的暫存資料夾。既有 Python cache ignore 已足夠，沒有新增 secret 或 dependency 類型。

## 主要發現

### 1. Stack option map 無法可靠承載規定的欄位名稱

`check_product_package.py` 原本在兩處直接使用 `split(",")` 拆分 Approved option map；商業決策的必要 layer 名稱卻是 `attribution, commission, payout, and reseller operations`。selection 值也可以有逗號。這使合法內容被拆成碎片，解析與決策比對失敗。

Jolvex 的 `docs/DOCUMENTS.md` 與 `stack-decisions.md` 明確記錄 workaround：OPT-MP-01 保留 recommended，採用事實放在 layer 的 Selected 與 repository evidence。現有完整 Product Definition approved 檢查會 PASS。Selected 本身是合約允許的既有採用狀態，因此不能僅憑 option 的 recommended 就指控批准繞過；但因格式缺陷而刻意扭曲 option 的表達，確實應修。

修復方向：單一 option-map parser，明確區分 option 分隔符、layer 分隔符與欄位內容；保留既有合法格式。重複、破損和選擇不匹配必須失敗。不得代替 owner 批准 OPT-MP-01，也不得改寫 Jolvex 的 digest 或批准紀錄。

### 2. 重試很多，但目前不能從保留的紀錄還原每次根因

當次觀察有 77 筆 attempt log，其中 25 筆 dispatch，21 筆結果是 retryable_failure：M1 11、M2 3、M2B 3、M2C 2、M2D 2。這是實際保留的 row 數，不能把 ATTEMPT ID 尾碼當作總次數。

部分 failure 的 evidence 只有「leased worker …」或雜湊引用，並非可直接閱讀的 exception、命令 exit code 或 stderr。因此這些資料證明有反覆失敗，尚不足以將每次失敗歸因於同一個腳本 bug。

修復方向：inspect 輸出按 mission 彙總保留的 dispatch failure 次數、最新 failure 與原始 evidence，讓 parent 快速定位；沒有證據時明確保留未知，不猜測 runtime 是否死亡。

### 3. 歷史 worktree drift 與執行中 dirty 混在一起

當次觀察 M2C 已 superseded，記錄 head 是 `c5822cc780e38d6d078d0e4dee325b8f8f725500`，對應 worktree 現在是 `9f34c04…`；M3 是 worker_running，對應 worktree 有修改。原 inspector 都只顯示 RECONCILE，缺少生命週期說明。

M2C 是歷史對照差異；M3 dirty 可以是正常進行中的修改。兩者均值得核對，但都不足以單獨證明程序卡死。修復應保留原有 needs_reconciliation 與 exit 1 邊界，只增加分類與說明。程序是否仍活著，必須另外查該 host/session 的實際完成或中斷證據。

### 4. 臨時「修復」腳本會破壞恢復證據

Jolvex `.harness/tmp/doctor.py` 會重寫 PLAN 綁定、授權 scope、worker/review context，移除部分 verifier executions，並依 attempt ID 去重歷史。`rebuild_execs.py` 更將 `verifier_executions` 清空再重建。這些是本輪只讀檢查到的腳本行為，沒有執行。

RUN 的 `INTERRUPTED-WK-M1-31-13` 同時明載：先前 retry scripts 重設 attempt history、重寫 retained verifier contexts，恢復需要 fresh checkpoint evidence。這不是憑工作樹狀態推測。

原有 skills 已要求 append-only evidence、exact-head verification 與 guarded transitions。本輪補充的是可操作的恢復指引：先 inspect；辨識真正中斷的 worker；以既有 reconciliation/result recording 路徑保留 terminal evidence；需要重跑時建立新的 attempt。不可透過全面換 digest、scope 或 verifier context 讓 validator 變綠。

## 各階段結果

| 階段 | 當次證據 | 判斷與處理 |
| --- | --- | --- |
| Product Definition / stack | 完整 `--require-filled --require-approved` 檢查 PASS；commercial option 留有逗號 workaround | 修 parser 與格式文件；不替產品作新決策 |
| Wireframe / Copy Freeze | 正式 `docs/design/wireframes.html` 通過 filled + approved 檢查；舊 `docs/product/wireframes.html` 已標 superseded | 正式檔已完成 schema 4；不要被舊檔或過期文字引導回去重做 |
| UI Design / HiFi | 帶正式 HiFi `docs/design/ui-references/20260915-m11/index.html` 的完整 wireframe + visual approval gate PASS | 這是合約/證據檢查，不是本輪新做的實際瀏覽器 review |
| Skill bindings | `check_skill_bindings.py --stage all` 對照實際 `~/.agents/skills`：ui-design-builder、design-system-compiler、code-security-review 的 tree hash 與 Jolvex pin 不符 | 下一個需要這些 slot 的階段須 deliberate review 後更新 pin；不能用產品文件 PASS 取代 binding PASS，也不能直接改 active session 的載入內容 |
| PLAN / 任務分解 | revision 19，M1/M2/M2B/M2C superseded、M2D integrated、M3 worker_running、M4–M9 queued | 以現行狀態決定剩餘工作，勿重做已整合 mission；本輪不接管 active wave |
| Dispatch / worker | 21 筆保留的 retryable failure，多筆缺少可讀的失敗根因 | 新診斷摘要降低翻查成本；不能靠 ID 尾碼補造失敗次數 |
| Task / worker verifier | 保留 34 筆 task_verifier、11 筆 worker_verifier attempt，另有 3 個 verifier execution records | 不因數量不同就認定證據遺失；須依 exact attempt/head/receipt 合約核對 |
| Review / integration | 保留 3 筆 review；M2B 曾 fix_required，M2D 後續 PASS 並整合 | bounded repair 是正常流程；舊 review 不可套用到新 SHA |
| Resume / runtime upgrade | inspector 未觀察程序；RUN 記錄 0.38；worktree 同時含歷史 drift 與 active dirty | 先核對程序與 checkpoint。0.39 修復不熱替換進 active 0.38 session |
| 人類進度頁 / 文件 | 當次 `docs/tasks.md` 不存在；`render_tasks_view.py --check` 回報缺檔。DOCUMENTS.md 仍說 goal 尚待建立、bindings 缺失、wireframe 未投影；實際已往前推進 | 正式 RUN 是 authority。由持有 RUN 的 parent 在正規 checkpoint 更新產生的 view 與文件摘要；本輪不寫入 Jolvex |
| Release / activation | `docs/ACTIVATION.md` 還是 product-activation/1、M8 seeded；部署/測量/法律批准等任務仍標 pending | 這份舊 seed 不能證明現在已完成或仍未完成；需在交付後另以 exact release/live readback reconcile |

## 歷史報告的使用邊界

當次 RUN 原檔為 3,662,044 bytes。將各 top-level 值各自以一般 JSON 編碼比較，`verifier_executions` 約 2,230,000 bytes，遠高於其餘欄位；這個數字是內容量比較，不是原檔中該區塊的精確 byte 範圍。RUN 的 runtime_metrics 尚未填寫，所以不能宣稱讀檔、驗證或模型等待各佔多少時間。上一輪加速分支的 bounded context、snapshot 重用與 verifier 排程可針對此類重複工作改善；本輪不藉清空歷史縮短檔案。

M7 / M9 報告記錄過產品作者流程、legal、affiliate、部署、hosted Admin 等問題；後續 DECISIONS 又記錄多次修復與上線。這些報告用於辨識容易出問題的交接，不直接列為目前 HEAD 的未修缺陷。

同理，`tests/e2e/journeys/` 包含 Bun 驅動的本地 synthetic domain journey。它們有價值，但不能取代實際頁面的點擊、console error、focus、網路失敗與 hosted 身份驗證證據。若「每個 frame」指的是所有產品頁面的互動體驗，需另做目前候選版本的 browser journey review；本報告未宣稱已完成該範圍。

## 主要證據位置

以下路徑均相對 Jolvex root：

- `docs/goal/PLAN.md`、`docs/goal/RUN.md`。
- `docs/product/stack-decisions.md`、`docs/DOCUMENTS.md`。
- `docs/design/ui-design.md`、`docs/design/wireframes.html`、`docs/product/wireframes.html`。
- `.harness/tmp/doctor.py`、`.harness/tmp/rebuild_execs.py`（只讀，未執行）。
- `docs/ACTIVATION.md`。
- `docs/goal/archive/20260915-021603-m7-m10-closeout/DECISIONS.md`。
- 同 archive 的 `evidence/m7/FINAL-REPORT.md`、`evidence/m9-import/FINAL-REPORT.md`、`evidence/m10/ui-review/admin-full/ADMIN-FULL-REPORT.md`。

實作、parent review 與完整測試結果另見同目錄的驗證報告。
