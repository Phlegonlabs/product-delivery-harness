# Tasks

流程中每完成一步，就在這裡加一行記錄。任務要拆到最小：一行只記一個最小動作（一個檔案、一道命令、一個決定），做完一格勾一格。只在本機更新，除非用戶要求才 commit/push。

## 固定流程備忘：版本更新上 GitHub

完整清單以 README 的 Releasing 章節為準，最小步驟：

- [ ] `package.json` 版本號
- [ ] `.agents/skills/delivery-harness/VERSION`
- [ ] README badge（en / zh-CN / zh-TW 三份）
- [ ] README 版本歷史加條目（三份，描述段同步）
- [ ] RUNBOOK `required_harness_version`
- [ ] `test_skill_contract.py` 版本斷言
- [ ] 跑完整驗證
- [ ] push run 分支、回報 head SHA
- [ ] 用戶落地 `main`
- [ ] 打 `v<version>` tag
- [ ] 同步 `~/.agents/skills/` 三個 skill（push 同輪）

## 2026-09-06

- [x] `.gitignore` 加 `.zcode/`
- [x] commit（`e38d5f0`）
- [x] push 到 `harness-architecture-fixes`
- [x] 刪本地分支 `harness-architecture-fixes`
- [x] 刪遠端分支 `origin/harness-architecture-fixes`
- [x] 建立 `Tasks.md` 記錄規則
- [x] `AGENTS.md` 加 Task Logging 規則
- [x] 加入版本更新固定備忘（README 三語 log、版本號、tag）
- [x] 記錄改成最小拆分（本次重構）
- [x] `AGENTS.md` Git Flow 加 atomic commit 規則（一個 commit 一個最小變更）
- [x] `AGENTS.md` 加 Mission Task Split 規則（PRD 拆 mission 時每個 mission 拆更多細 tasks，一 task 一 commit）
- [x] `gh repo rename product-delivery-harness`（本機 remote 同步換新網址）
- [x] 從 `origin/main` 開分支 `rename-product-delivery-harness`（AGENTS.md 本機規則先 stash 再 pop）
- [x] 三語 README 換掉 21 處 `fullstack-goal-dev`
- [x] 版本 bump 0.25.2（package.json、VERSION、三語 badge、三語版本歷史、RUNBOOK、test_skill_contract.py）
- [x] 完整驗證：check_skill_spec、pyflakes、627+1(golden)+67+76 顆測試全綠、git diff --check
- [x] push `rename-product-delivery-harness`，head `43451d2`
- [x] 三語 README 改為描述公開儲存庫（簡介、安裝說明、移除 gh auth 前置），commit `33aaf5a` 並 push（head `33aaf5a`）
- [x] 本機 skills 更新：三個 skill 備份到 `~/.agents/skill-backups/product-delivery-harness/`、複製新版、驗證一致、legacy ID 確認不存在
- [x] commit `.gitignore`（`.zcode/`）、`AGENTS.md` 規則、`Tasks.md` 三個 atomic commits 並 push
- [x] `main` fast-forward 合併 `rename-product-delivery-harness` 並 push
- [x] 打 `v0.25.2` tag 並 push
- [ ] 用戶：重啟 host 讓 skills 重新載入
- [x] MIT 授權：LICENSE（Phlegonlabs）、三語 README 授權段、package.json license 欄位；release 0.25.3 七觸點；PR #78 squash 落地（e094dd8）、tag v0.25.3 已推、本機 skills 已同步驗證
- [ ] 用戶：重啟 host 讓 skills 重新載入
