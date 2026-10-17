# Harness 精簡修改與 review

分支：`fix-jolvex-flow-skills`。本輪基準：`7589ced33fa5e74048e002e6f070ddedfbdeec04`。UI impact：none。

## 完成的修改

1. 建立 RUN 與七個正式 checkpoint 自動刷新已宣告的 `docs/tasks.md`：`accept-wave`、`record-worker-result`、`reject-worker-result`、`record-integration`、`reconcile-interrupted`、`reconcile-interrupted-reviews`、`close-wave`。重用已驗證的 PLAN/RUN，保留 Update Log。刷新失敗只回報 warning 與修復命令，不把已完成的 RUN transition 誤報為失敗。
2. 新增唯讀 `render_stack_option_map.py`，從 stack decision tables 產生 option map，避免手抄。既有 checker 仍獨立比對；工具不修改批准、狀態或 digest。沒有新增 approved option 的 Selected／Required 套件仍可保留 `Approved option map: None`。
3. 收斂 RUN 操作說明：已有正式 transition 的操作使用 guarded commands；未有通用命令的 authoring、revision、closeout，明確保留各自的授權與 review 程序。Validator 通過不代表可以改寫歷史或 grant。
4. 同步英文、繁中、簡中、西文 README 的 checkpoint、自動刷新、失敗修復與 option-map 說明。核心 SKILL 為 3,590 字，符合既有文件預算。

## Parent review 修正

- 自動產生的 tasks view 原先會讓下一個操作判定 checkout dirty。現在只豁免已宣告、符合 generation marker 與本 RUN 身分的 view；其他產品修改、手寫檔案與 foreign view 仍受檢查。
- 原先直接寫 view 可能覆蓋同時發生的修改。現在使用既有原子寫入機制、來源比對與 exclusive creation；遇到 PLAN/RUN 或目的檔變動就停止刷新。
- 移除每次 transition 保存後無條件重讀 RUN，避免不必要工作與來源混用。
- Verifier 對豁免的 view 仍保留完整性檢查。測試涵蓋 reserve、execute、record 流程及執行後竄改 view 被拒絕。
- 聚焦測試涵蓋刷新失敗、Update Log、非 generated 檔案、並行更新、外部 RUN 路徑、option-map 格式與批准邊界。

## GLM 執行

使用 `glm-workers` 外部 dispatcher，model `glm-5.3-flash`，run ID `20260916-093238-e94011c6dfdb44d9aea8f3abd0ac0893`。GLM 留下程式、測試與 README 初稿後，因 `429 Too Many Requests` 超過重試次數而中止，exit 1。未自動重新派發 writable worker；parent 接手 review、修正與驗證。沒有把 worker failure 記為成功。

## 驗證

第一輪完整測試發現兩個文件合約問題：舊 assertion 未反映自動刷新，以及核心 SKILL 超過字數預算。修正後，57 個文件合約測試通過，再重跑完整規定流程。

所有命令從 worktree root 執行。最終 test requirements、check_skill_spec、全範圍 pyflakes、docs_weight、git diff --check 均 exit 0。

| 最終完整測試 | 結果 |
| --- | --- |
| Delivery Harness | 1,027 個；12 skipped，其餘通過 |
| Golden Path（HARNESS_GOLDEN_PATH=1） | 1 個通過 |
| Product Definition | 196 個通過 |
| UI Design | 106 個通過 |
| Design System Compiler | 93 個；3 skipped，其餘通過 |
| Product Activation | 56 個通過 |
| SEO Growth Review | 16 個通過 |

合計 1,495 個測試案例，15 個 skipped，沒有 failure/error。Skipped 包含 Windows 不適用的 POSIX fixture、缺少 symlink 權限，以及主 suite 預設略過的 Golden Path；Golden Path 已另行啟用並通過。Delivery suite 約 1,082 秒，這是驗證耗時，不是效能改善基準。

最終日誌、逐命令結果與 SHA-256 清單：`C:/Users/mps19/AppData/Local/Temp/pdh-simplify-final-q260_ygt/`。完整驗證期間 227 份 skills／README 檔案雜湊未變。第一輪失敗證據保留於 `C:/Users/mps19/AppData/Local/Temp/pdh-simplify-review-6gn4hh2x/`。

Gitignore 無需更動：現有 Python cache 規則已涵蓋新增腳本，source、tests 與研究報告保持 Git 可見，測試日誌放在 checkout 外。已核對 check-ignore、status --ignored 與 ls-files。

## 交付狀態

- 上一輪 14 份檔案依使用者授權分成三個本機 commit：`0365856`、`5780c1a`、`7589ced`。
- 本輪 20 份 source／README／test 修改與這份報告尚未提交。沒有 push、merge、tag 或安裝 skills；本輪沒有修改 Jolvex 或其他 worktree。
- 已完成未提交 diff 的 parent review。固定 commit SHA 的 code-security gate 為 UNVALIDATED，不宣稱已完成發布候選驗證。
- Snapshot evidence 去重仍是另批 schema 工作，本輪沒有端到端速度提升的量測結果。
