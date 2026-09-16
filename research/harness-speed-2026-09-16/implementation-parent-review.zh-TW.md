# Harness 加速：實作與 parent review

日期：2026-09-16。UI impact：none。

分支為 `research-harness-speed`，獨立 worktree 為 `product-delivery-harness-speed-research`。基準是遠端 main `1c7939de3d29d446684ea771a926efd917937e40`；唯一新增 commit 是已授權的三份研究檔 `98fa418a5bbed1fb73d0b90b30ccd24fb98758dd`。程式修改尚未提交、推送或安裝。

GLM-5.3-Flash worker 完成第一輪實作，parent 隨後檢查完整 diff、補修與驗證。`implementation-2026-09-16.md` 保留 worker 返回時的紀錄；本文件記錄後續結果，取代其中未完成 single-flight 與待 parent 驗證的狀態。

## 最終修改

1. 文件字數統計使用固定 commit、一次 NUL 分隔 `ls-tree` 和一次 `cat-file --batch`，保留 Git 安全檢查及輸出格式。
2. Verifier 增加唯讀階段計時。`command_ms` 單獨量命令；原 `duration_ms` 保留包含 cleanup、postcheck 的區間。沒有新增 RUN 寫入，也沒有估算模型或 owner 等待時間。
3. Review packet 移除完整 diff 已包含的路徑列表與 diff stat。截斷時仍保留完整路徑列表；scope、SHA、acceptance、工具、證據與 finding lineage 保持不變。
4. 同一批的相同 checkout／SHA 只建立一次 immutable archive；每個 verifier 仍獨立解壓、檢查及清理。
5. 排程有空位便補入無資源衝突的工作，保留並行上限與 exclusive／shared／opt-out 規則。Container 命令期間不持有全域 runtime lock，各命令仍持有 executable descriptor／Windows handle。
6. 同一批明確 opt-in 的 read-only task／worker deterministic PASS 可以重用。相同請求共用一次執行，失敗會釋放等待者供重新執行。Cache 綁定 execution key、canonical checkout、Git guard 及 protected inputs；每個 consumer 重驗 guard 與 runtime／image，保留自己的 reservation 和 attestation，並指向原始執行。Container 不使用磁碟 PASS cache。

四語 README 與相關 canonical references 已同步。沒有改產品批准、授權或發布流程。

## Review 補修

- 無關 submodule 不應被當成文件 blob 而報錯。
- Git 自訂 `ls-tree --format` 對 Unicode 路徑仍會 quoting，改用原生 NUL 分隔格式；新增 Unicode 檔名測試。
- Batch 的非預期 exception 會讓 callback 遺留 active job 而卡住；改由主排程消費 completed futures，保留 ERROR 結果。
- 補上 archive 和 container 相同請求的 single-flight，以及失敗後釋放、重試的測試。
- 重用來源驗證補上 context hash、實際 stdout／stderr、guard、opt-in 條件和缺少 origin 的檢查。同批尚未寫入 RUN 的原始結果也可接受；所有結果仍先通過原有宣告和 context 驗證。
- 修正 `command_ms` 把 postcheck 重複計入的問題，避免替未啟用 cache 的命令額外執行一次 guard。

## 量測與限制

Parent 以固定 main SHA 的 57 份文件交錯量測四次，逐檔字數 mapping 一致。`weights()` helper 中位數為 **4680 ms → 141 ms**，子程序 **116 → 4**。數據在 `implementation-parent-benchmark.json`。量測時完整測試也在執行，時間受機器負載影響；這不是完整 CLI 或產品 RUN 的效能數字。

文件庫總量目前為 132572 個空白分隔詞，較研究基準多 397 詞。上下文縮減發生在實際 review packet 的重複材料，沒有宣稱整個 skill 文件庫縮小。

真實 Podman 在 Harness 的精簡環境中回報 `cannot determine user's homedir`，無法完成既有 preflight。這輪沒有改該環境政策，因此 container 重用與並行只有測試替身的證據，尚無實機端到端加速數字。

## 驗證

所有必跑指令都已執行，結果如下：

| 驗證 | 結果 |
|---|---|
| requirements-test.txt | 已安裝所需依賴 |
| check_skill_spec、全範圍 pyflakes、docs_weight、git diff --check | 通過 |
| Delivery Harness 全套 | 1013 項；首次 1 failure、1 error、11 skipped；兩個失敗項停止改檔後各自重跑通過 |
| HARNESS_GOLDEN_PATH=1 | 1 項通過 |
| Product Definition | 180 項通過 |
| UI Design | 96 項通過 |
| Design System Compiler | 93 項，3 skipped，其餘通過 |
| Product Activation | 55 項通過 |
| SEO Growth Review | 16 項通過 |
| 最後修正的 focused checks | Runtime 44 項（2 skipped）、worker-result 34 項、packet 1 項通過；最後 docs-weight＋skill-contract 69 項通過 |

首次完整 suite 與 parent 最後的來源修正重疊。`test_powershell_has_migration_rollback_and_complete_install_parity` 明確回報來源 bytes／manifest 不符；`test_powershell_foreign_race_target_is_never_deleted` 缺少測試 sentinel。停止修改 canonical sources 後，兩項單獨重跑分別在 59 秒及 27 秒通過。沒有宣稱首次完整 suite 一次全綠，也沒有略過 installer 檢查。

測試及量測都從研究 worktree 根目錄執行。詳細 log 與最終修改檔案的 SHA-256 清單保存在 `C:\Users\mps19\AppData\Local\Temp\pdh-speed-review-dcclpbyf`。Python caches 由現有 `.gitignore` 覆蓋，log／暫存證據放在 checkout 外；研究文件保留追蹤，沒有新增需忽略的產物類型。已檢查 `git check-ignore -v`、`git status --short --ignored` 與 `git ls-files`。

本次 diff review 發現的問題都已修正並補測。這是未提交工作目錄的 review，不是 exact-SHA 安全 gate 或 release promotion。真實 container 效能仍待前述 Podman 環境問題解決後量測。
