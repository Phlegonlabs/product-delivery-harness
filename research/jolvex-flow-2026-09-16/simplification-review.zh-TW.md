# Product Delivery Harness 精簡 review

基準：0.39.0 的 `4cc1b55b33ad09e579f61334160a3ec62dfcd5fe`，加上本分支已驗證的 Jolvex parser／inspector 修復。這份是 review 建議，沒有把下列重構混入修復。本輪也讀取先前 speed 分支的實作報告，避免把已做的工作再列一次。

結論：可以精簡。優先減少需要 agent 手動同步的資料與額外操作，再處理 RUN 的重複快照。減少腳本數量、刪掉授權檢查或拆分大型檔案，本身不是目標。

## 建議順序

### 1. 讓 tasks view 隨正式 checkpoint 更新

目前 `SKILL.md:105` 要求 parent 在開始、接受 wave、記錄修改後另外執行 `render_tasks_view.py`。`harness_transition.py:3718` 保存 RUN 後只處理 packet／request 輸出，沒有更新 tasks view。`render_tasks_view.py:227` 已有可重用的 `build_view()`，不必新增一套進度模型。

Jolvex 已有正式 PLAN/RUN，但本輪觀察到 `docs/tasks.md` 缺失。這不改變 canonical RUN 的真實狀態，卻讓使用者及下一個 agent 缺少可讀的進度。

建議：在既有 parent transition 的指定 checkpoint 完成後，重用現有 renderer 更新已知的 generated view。保留手寫 Update Log、拒絕覆蓋非 generated 檔案；若 view 寫入失敗，回報「RUN 已保存、view 待刷新」，不能回滾或誤報正式 transition 失敗。若已有較新的 RUN，拒絕寫入舊 view。

效果：少一個需要記住的命令、少一份容易過期的資料。需要驗證 view 寫入失敗、使用者手寫檔案、Update Log、並行 state 更新與重試。

### 2. 自動產生 option map，避免手寫第二份 layer 清單

`check_product_package.py:2980` 已能從 approved options 與 executable layer tables 推導 actual map；但 `contract_utils.py:117` 的 finalize helper 明確要求 caller 先自行提供 option map。資料因此被寫兩次，再靠 checker 比對。

本輪新增 `||...||` 格式修好了逗號解析；它仍是一個需要作者記住的序列化格式。Jolvex 的 workaround 正好說明手寫這層容易造成返工。

建議：將 map 的推導／格式化留在 Product Definition candidate 產生步驟，使用既有 table 作來源，先給 owner review 完整候選，再綁定批准與 digest。保留 checker 的獨立比對；生成器不能把 recommended 改成 approved，也不能替既有批准檔案自動重錨。

效果：產品選擇只維護一份，既有輸出合約不必立即改成新 schema。測試重點為 layer 變更、逗號／保留分隔符、Selected／Required 證據、approved option mismatch 及舊批准 bytes 保留。

### 3. 收斂執行中 RUN 的修改路徑

`execution-state-model.md:75` 已提供 guarded `record-worker-result`；同一文件 `:114` 卻仍以「任何 script 或 manual edit 都先過 validator」描述一般修改方式。單純重新驗證新內容，不能證明先前歷史沒有被改寫，也不能代替 transition 的 lock、receipt 與 live-head recheck。

Jolvex 的臨時 doctor/rebuild 腳本曾重寫 retained contexts，RUN 也記錄過這個恢復問題。這個觀察支持收斂操作方式，不代表每次 failure 都由同一原因造成。

建議：清楚區分 PLAN 初稿／正式 revision 作者工作與執行中 RUN transition。正常 dispatch、result、reconcile、integration、close-wave 只走現有命令；read-only validator 用於診斷，不作為任意重寫的通行證。對目前沒有正式 mutation 支援的修訂，明列保留與重新授權程序，不再讓 agent 自行猜一支「修到綠」的腳本。

效果：減少自製恢復程式與隱性分支。這需要收斂文件與補齊確定缺少的操作，不能以加一個 `--force` 或自動改 grant 代替。

### 4. 對完全相同的 verifier snapshot 去重

`verifier_runtime.py:1523` 把完整 `tracked_files` map 複製到每份 attestation。約 16:20 UTC 的 Jolvex RUN 已有 6 份 verifier records，原檔為 **7,230,562 bytes**；其中 6 份 tracked-files maps 各有 2,639 個 path，只有 4 份不同內容。

以排序、無空白的 JSON bytes 比較，這些 maps 合計 **4,254,338 bytes**，獨立內容合計 **2,836,552 bytes**，完全重複部分為 **1,417,786 bytes**。這只是該子物件的資料量比較，並非實測儲存節省、token 節省或執行時間改善。

建議：在新 RUN schema 中，同一份不可變 snapshot 只保存一次；每個 verifier record 仍保留自己的 attempt、SHA、guard、receipt 與 snapshot digest 引用。讀取、closeout、archive 和跨 worktree 搬移都必須驗證引用內容完整且雜湊一致。

這比前三項改動大，應獨立處理：缺檔、被改寫、引用錯誤、不同 host／checkout／SHA、archive portability 都要 fail closed。不能直接重寫正在跑的 0.38 RUN，也不能只保留一個無法還原的 hash。

## 暫時不建議做的事

- **不再加一套通用 orchestrator／dispatcher。** 現有 `harness_step.py` 已合併 live observation 與 selection；`validate_result.py` 已合併 node／worker preflight；`record-worker-result` 已在 transaction 中驗證及記錄。把它們再包一層，未必少任何狀態。
- **不為很小的 helper 建共用框架。** AST 比對只找到少量完全相同的 `_section`、`_rows`、`_diff`。十幾行的 helper 不是目前主要成本。
- **不把大型檔案行數當成刪除理由。** `harness_manifest.py` 約 7,564 行，確實難維護，但現行入口已先拒絕錯誤 schema pair。舊 schema 還有歷史恢復用途；單純拆檔不會減少操作或驗證。應待一個具體、可獨立測試的責任邊界需要改動時再抽離。
- **不合併不同的 owner 決策。** Product Definition、Copy Freeze／Visual Approval、12 個 action grants、exact-SHA verification、外部 publication／main promotion 各自解決不同問題。可以批次呈現已知問題，不能用一個模糊「全部同意」取代精確授權。
- **不把小修改重新拉進 PLAN/RUN。** 現有 Project Size Gate 已讓小工作走 direct route，應落實這條，而不是再發明一種 light RUN schema。
- **不重做上一輪已完成的效能修改。** Review packet 去重、snapshot materialization 重用、verifier 排程及 container cache 已在 speed 分支實作；仍需與 0.39 基準整合及驗證，不能當成這輪新發現或已安裝功能。

## 建議第一批

先做 1、2、3：進度 view 自動更新、candidate 自動產生 option map、收斂 RUN mutation 說明與必要操作。三者都直接減少 agent 要記住、手抄或猜測的事情。Snapshot evidence 去重另開一批 schema 工作。

相關 canonical 入口：

- `skills/delivery-harness/SKILL.md:21`、`:43`、`:105`。
- `skills/delivery-harness/scripts/render_tasks_view.py:227`、`:288`。
- `skills/delivery-harness/scripts/harness_transition.py:3718`。
- `skills/product-definition-builder/scripts/contract_utils.py:117`。
- `skills/product-definition-builder/scripts/check_product_package.py:1432`、`:2980`。
- `skills/delivery-harness/references/execution-state-model.md:75`、`:114`。
- `skills/delivery-harness/scripts/verifier_runtime.py:1518`。
- `skills/delivery-harness/scripts/harness_manifest.py:7494`。

這次 review 沒有修改 canonical source；前一輪 Jolvex 修復的完整測試與 source hashes 保持有效。
