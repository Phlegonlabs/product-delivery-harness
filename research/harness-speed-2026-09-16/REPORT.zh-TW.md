# Harness skills 加速研究

研究日期：2026-09-16。這是研究提案，沒有更改現行 skill、授權規則或驗證流程。

研究分支：`research-harness-speed`。基準為剛 fetch 的遠端 main：`1c7939de3d29d446684ea771a926efd917937e40`（0.38.0）。原本 `fix-review-findings` 的 0.39.0 工作及未提交修改沒有納入，也沒有被搬動。後續實作前需要重新對照當時 main 和那些修正。

## 建議先做什麼

先補齊耗時記錄，同時落地已量到效果的批次 Git blob 讀取；再縮減重複上下文與驗證準備工作。Container 快取涉及隔離與證據可信度，應另作設計，不能只改一個開關。

目前可確認多處固定成本，但還不能判定哪一項佔你實際產品 RUN 的最大比例。這次沒有操作真實產品 RUN、呼叫模型、啟動 container 或量測使用者等待批准的時間，因此沒有整體加速百分比。

| 優先次序 | 改善項目 | 證據與預期作用 |
|---|---|---|
| 1 | 自動記錄完整階段耗時 | 現在缺少可用來判斷主因的完整時間帳；避免優化錯地方 |
| 1 | `docs_weight` 批次讀 Git blobs | 局部實測 4.85 秒 → 0.23 秒；輸出一致，改動範圍小 |
| 2 | 縮小當前階段的閱讀範圍與交接內容 | 技能本文及 references 合計 132,175 個空白分隔詞；實際 token 與模型耗時待量 |
| 2 | 減少相同 SHA 的 snapshot 準備工作 | 目前每個 container verifier 都另作 archive/extract；實際耗時待量 |
| 3 | verifier 有空位時就補下一個無衝突工作 | 現有批次仍按 wave 等待最慢項目；混合長短測試可能受影響 |
| 3 | 設計可驗證的 container 結果重用 | task/worker 當前路徑必走 container，也必定繞過快取；變更風險較高 |

## 1. 已量到的 Git 子程序成本

環境為 Windows 11、Python 3.14.7。同一個 Python 程序，各測三次，以下取中位數。原始數據及每類子程序耗時保存在 `probe-results.json`。

| 局部操作 | 現況 | 研究原型 | 子程序數 |
|---|---:|---:|---:|
| 讀取固定 HEAD 下 57 份技能文件並計算字數 | 4,853 ms | 232 ms | 116 → 4 |
| `harness_step.observe()`，只觀測 Git 狀態 | 804 ms | 未改 | 16 |

`docs_weight.weights()` 先做一次 `ls-tree`，再對每個檔案做一次 `git show`。每個受保護的 `run_git()` 又先執行一次設定檢查，因此 57 份文件產生 58 次設定檢查和 58 次內容／清單操作。

研究原型改成一次 `ls-tree` 加一次 `cat-file --batch`，兩個 Git 呼叫仍經過原有 `run_git()` 設定檢查。57 個路徑的字數 mapping 與現有 helper 完全一致。局部減少約 95% 時間，不能外推成產品交付快 95%。

這個測試只量 `weights()` helper，沒有量完整 `docs_weight.report()`、CLI 啟動或模型推理。兩個版本都沒有把 report 外層的 object-substitution 檢查算進去。正式實作必須保留外層拒絕 replace refs／grafts 的檢查、基準 ref 的解析語義、錯誤處理與資料保存規則；原型的成功不代表這些邊界已全部測過。

`observe()` 的數字使用最小合成 context 加真實倉庫 Git 讀取；沒有選擇任務或驗證完整 PLAN/RUN。它顯示一次觀測有可見成本，並不證明整個 transition 慢在這裡。不要以長效快取取代 mutation 前的最新 Git 觀測。

來源：`skills/delivery-harness/scripts/docs_weight.py:85`、`harness_git.py:671`、`harness_step.py:55`。

## 2. 文件描述的快取，在當前 worker 路徑不會命中

`run_verifier()` 對 `layer=task|worker` 且 `checkout_role=worker` 的請求要求 container。隨後，只要是 container 就設定 `can_reuse=False`，原因為 `container_execution_not_cacheable`。

既有 `test_exact_pass_reuses_equivalent_task_and_worker_declarations` 雖然名稱提到重用，實際断言卻是兩次皆 bypass，而且 counter 等於 2。這次執行此測試通過，證實這是當前被測試保護的政策，並非偶發 cache miss。

因此不能把 `session_exact` 寫進 PLAN，就預期 task 與 worker 的相同命令只跑一次。其他合法非 container 路徑仍可能重用，不能說整套 cache 都失效。

低風險第一步是修正文件與測試名稱的期待，讓輸出直接說明為何不能重用。真正加入 container reuse 前，必須列清 input tree、命令、工作目錄、環境、runtime 身分、image RepoDigest、sandbox policy、預檢、protected paths 與證據來源；新 reservation 仍需自己的有效證據，不能複製舊 attestation。不可讓不受信任的 repository 或 worker 偽造 PASS cache。

來源：`skills/delivery-harness/scripts/verifier_runtime.py:1495`、`:1544`；`scripts/tests/test_verifier_runtime.py:973`；`SKILL.md` 的 Verify Local-First。

## 3. 現有計時漏掉一部分準備成本

`new_run.py` 初始化 `runtime_metrics: None`。搜尋 scripts 後，找到 schema 驗證與初始化，沒有找到自動填滿 RUN phase events 的寫入路徑。操作方仍可能手動或在 host 端記錄，但目前程式沒有自動提供整體耗時拆分。

單次 `run_verifier()` 在前置 input validation、Git guard、cache lookup、snapshot archive/extract 完成後才啟動計時；因此個別結果的 `duration_ms` 不含這些成本。批次 `duration_ms` 包住 executor，範圍較大，不能把兩種 duration 當成相同口徑。

建議增加唯讀觀測輸出：完整 elapsed、validation、Git observation、snapshot、command、review、queue/wait、owner wait。模型 token 與 host 等待只收實際可得值，拿不到就留空；不要用估算值填滿。優先使用現有 result／外部 trace 承載，避免每個計時事件額外觸發一次 RUN 全量驗證。統計不作為 gate PASS。

來源：`skills/delivery-harness/scripts/new_run.py:350`；`verifier_runtime.py:1619`、`:1628`、`:1681`；`references/runtime-performance.md` 的 Machine Telemetry。

## 4. Skill 上下文有縮減空間，但須保留必讀契約

| Skill | SKILL.md 詞數 | references 詞數 |
|---|---:|---:|
| delivery-harness | 3,594 | 60,667 |
| product-definition-builder | 5,152 | 35,335 |
| ui-design-builder | 1,517 | 9,164 |
| design-system-compiler | 1,338 | 2,781 |
| product-activation | 1,709 | 5,186 |
| code-security-review | 796 | 705 |
| seo-growth-review | 1,372 | 2,859 |

這是可用文件庫的大小，並不表示每次都會全讀，也不是 tokenizer 計數。Harness 已規定 Reference Routing、fresh bounded packet、只選當前 host adapter。應先量每個任務實際讀了哪些文件、重讀幾次，再刪除不必要的上下文輸入。

值得實作的範圍：SKILL.md 保留路由、授權邊界及當前階段必需規則；完整 schema、相容性細節和範例留在精確路由的 references。交接 packet 提供任務所需資料及原文路徑，不重播 parent 全部對話，也不要求讀完整 PLAN/RUN 才能取得已在 packet 的欄位。

上游也需檢查：Product Definition enhancement 現在要求完整閱讀既有核心包與每份 outcomes。歷史累積會增加固定閱讀量。未來可設計帶 source digest 的索引，先定位受影響決策，再讀指定歷史原文；這是待批准的契約變更，現行 mandatory reading 不能自行跳過。

既有決策已回答的訪談問題，按現行 enhancement 規則不應重問。Product、Wireframe 和 Visual Approval 各有用途，不能用「加速」把它們當成同一次 approval。

來源：`skills/delivery-harness/SKILL.md` 的 Reference Routing、Default Mission Topology；`skills/product-definition-builder/SKILL.md` 的 Workflow step 2、Interview Rules。

## 5. 相同 SHA 的驗證仍重做 snapshot

每次 container verifier 都獨立呼叫 `_materialize_git_snapshot()`，執行 `git archive`、驗證 tar members、extract 到外部臨時目錄。`run_verifier_batch()` 的每個 job 仍各自走這條路徑。

可先研究同一批、同一 repo/SHA 的 immutable archive bytes 重用，再考慮可信的唯讀 snapshot 共用。需要確保工作輸出留在各自可寫空間，不能讓任一 job 修改其他 job 的輸入；現有 path、link、device、protected-file 檢查不能略過。由父層管理生命週期，保留每個 verifier 自己的結果與驗證。

若實測 archive/extract 只佔很小比例，就不應優先建 snapshot cache。這次沒有啟動 container，因此未量化此项收益。

來源：`skills/delivery-harness/scripts/verifier_runtime.py:1157`、`:1619`、`:1825`。

## 6. Verifier batch 仍有整波等待

`run_verifier_batch()` 先排好 waves，再完整等一波結束才啟動下一波。假如兩個 slot 中一個跑很久、另一個很快完成，下一波無衝突的工作仍可能等待。

後續可換成「有空位便從 ready queue 補上無衝突 job」的小型排程，保留 `parallel_safe: false`、exclusive/shared resources、最大並行數和每個 job 的独立結果。它只改 verifier 排程，不改 writer wave、授權、review、serial integration 的邊界。

相對地，mission 完成後立刻 review/integrate、事件式等待和 verifier batching 已是現有功能；不要再花一輪實作相同能力。先核對真實 RUN 是否有使用它們。

來源：`skills/delivery-harness/scripts/verifier_runtime.py:1814`、`:1847`；`references/runtime-performance.md` 的 Shared Fast Path。

## 實作拆分與驗收建議

1. 計時：一個完整 verifier 輸出能拆出前置準備及執行時間；不多寫 RUN，不改 PASS 語義。以一個小型 direct 任務及一個既有 managed 案例建立真實基準。
2. Blob 批次：只改 `docs_weight` 的基準內容讀取；一般、空清單、缺失 blob、非 UTF-8 既有行為、特殊路徑和 Git 安全拒絕案例結果一致。比較相同 SHA 的 wall time 和子程序数。
3. 上下文：挑一個常用路徑，記錄實際載入 bytes、重讀次數、parent tool round-trips；縮減後保持相同 required reading、scope、verifier 與 reviewer evidence。
4. Snapshot：先量真實 container setup；收益足夠才作同批 immutable source 重用，並測相互污染、來源漂移及 cleanup ownership。
5. Verifier queue：以長短混合 job 證明 slot 可即時補位；exclusive resources 絕不重疊，錯誤結果不丟失。
6. Container reuse：獨立設計與安全審查後才實作，不混入前面的低風險批次。

各項保持最小 task 與自己的驗證／原子 commit；commit、push 仍按授權執行。真正修改 skill 或 flow 時，必須同步四語 README，並跑 AGENTS.md 的完整驗證清單。這份研究本身不更改規則、無 UI impact，也不需要 release bump。

## 本次驗證與重現

- `probe.py`：三次基準與批次讀取的 57 個路徑字數 mapping 全部一致；三次觀測 HEAD 都未改變。
- 五個既有 verifier 測試通過：task/worker cache bypass、平行 batch、exclusive resource、未標記 verifier、明確 opt-out。Container 執行由既有測試 fake 代替，不構成真實 container 效能證據。
- `python -m pyflakes research/harness-speed-2026-09-16/probe.py` 通過。
- `python skills/delivery-harness/scripts/check_skill_spec.py` 通過。
- `git diff --check` 通過；新增研究檔另檢查尾端換行、行尾空白與 JSON 數據一致性。`git status --short --ignored`、`git check-ignore -v`、`git ls-files` 確认研究檔可追蹤，Python caches 被既有規則忽略，canonical sources 無修改。
- 未更改 production skills，所以沒有宣稱跑過完整 release suite。
- 研究腳本與測量 JSON 是應保留的研究證據；沒有引入新的本機秘密或快取類型。既有 `__pycache__/` 規則覆蓋 Python import 產生物，`.gitignore` 不需新增。

在此 worktree 根目錄重跑；輸出路徑必須是新檔，避免覆蓋既有結果：

```powershell
python research/harness-speed-2026-09-16/probe.py --out research/harness-speed-2026-09-16/probe-results-repeat.json
```

量測為同機 warm-process 微型測試，樣本數僅三次，先 sequential 後 bulk，未隨機交錯，會受 OS cache 與當時負載影響。正式效能驗收應交錯多次執行，固定模型、硬體、任務、驗證範圍和並行預算；owner 等待時間另列。
