<p align="center">
  <img src="./assets/readme-cover-zh-TW.png" alt="全端交付控制框架：規劃、建置、驗證、落地" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>繁體中文</strong> | <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/fullstack-goal-dev/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/fullstack-goal-dev/actions/workflows/harness-ci.yml/badge.svg?branch=main"></a>
  <img alt="Private marketplace" src="https://img.shields.io/badge/marketplace-private-111827?style=flat-square">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-2563EB?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude_Code-supported-D97706?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-059669?style=flat-square">
</p>

# Full Stack Harness

私有技能市集，讓你用 Codex 或 Claude Code 把產品構想或變更需求轉化為經過驗證的交付流程。

它不是提示詞集合。這個外掛把產品定義、視覺設計與工程執行拆開，讓每個階段都有單一真實來源、清楚的交接邊界，以及自己的驗證方式。

> 定義產品。把設計做具體。只執行已就緒的工作。每次移交前，都驗證實際結果。

## 從這裡開始

| 你目前有什麼 | 從哪個技能開始 | 會得到什麼 |
| --- | --- | --- |
| 一個產品構想 | `prd-builder` | 需求、架構、技術選型、發佈目標、測試義務，以及附來源的市場研究 |
| 已凍結、需要 UI 設計的產品輸入 | `product-design-builder` + `frontend-design` | 低保真線框圖與具約束力的設計系統契約 |
| 既有儲存庫中的明確變更 | `fullstack-harness-engineering` | 小型工作直接實作；大型工作進入受管的 PLAN/RUN 流程 |
| 每個分支各自的 Cloudflare Worker 預覽 | `manage-cloudflare-worker-deployments` | 安全的預覽 Worker 部署與清理，以及可選、獨立設閘的正式環境初始部署 |

這些技能可以單獨使用。不是每個任務都要跑完整條流程。

## 核心保證

- **小型工作維持精簡。** 一個有界變更只走檢查、實作、驗證與審查。
- **大型工作明確記錄。** PLAN v5 定義 typed graph；RUN v10 記錄授權、嘗試與佐證。
- **Worker 彼此隔離。** 寫入任務使用獨立 worktree 與有界範圍；parent 會驗證每個回傳的 commit 與 diff。
- **有能力不等於有權限。** 即使執行環境能推送或清理，每個動作仍需要精確授權。
- **佐證跟著 SHA。** 新的 commit 會讓舊 head 的閘門與 UI 佐證失效。
- **跑到推送為止。** Harness 負責 commit 並推送這次執行自己的分支。把它合進預設分支是你自己的步驟。

## 包含的內容

| 技能 | 適用情境 | 主要產出 |
| --- | --- | --- |
| `prd-builder` | 產品探索、需求、Builder UX Direction 輸入、架構、技術選型、發佈目標、測試義務，以及草稿完成後的市場研究補缺 | `PRD.md`、`architecture.md`、`stack-decisions.md`、`market-research.md` |
| `product-design-builder` | 產品線框圖、視覺方向與設計系統契約。它必須載入獨立的 `frontend-design` 技能；依賴無法使用時會停止。 | `wireframes.md`、`design-system.md`、`design-system.json` |
| `fullstack-harness-engineering` | 共用的規模判定閘、PLAN/RUN、授權、本機驗證，以及整合 | 直接動手、`RUN.md`，或 `PLAN.md` + `RUN.md` |
| `fullstack-harness-codex` | 左側欄的獨立 Codex 任務、每個 mission 一個由 app 管理的 worktree，以及可選的任務級唯讀 Multi-agent 輔助 | 執行環境啟動指令與 worker 結果 |
| `fullstack-harness-claude-code` | Claude Dynamic Workflow 與由 parent 管理的 worktree | 執行環境啟動指令與 worker 結果 |
| `manage-cloudflare-worker-deployments` | 自動為每個分支建立 Cloudflare Worker 預覽、受保護的清理流程，以及可選的手動正式環境初始部署 | 安裝器、生命週期腳本、測試、設定與 GitHub Actions 範本 |

交付核心在啟動受管編排之前，會先做一個規模決策：

- 小型工作維持直接動手，預設不啟用 planner、scheduler、PLAN/RUN、subagent，也不做外部執行環境的預檢。
- 大型工作進入受管規劃。它可以用 `RUN.md` 走循序交付，或用 `PLAN.md` 加 `RUN.md` 處理多任務與可持久的交棒。
- 只有在大型計畫至少有兩個彼此獨立、已就緒的任務時，scheduler 才會開始扇出。核心接著只載入一個 host 轉接器；只有在選定路線需要時，才對外部執行環境做預檢。
- 工作不需要等待遠端 CI。當驗證過的整合 head 推送到這次執行自己的分支時，這次執行就結束了。

規模指的是協調範圍與影響半徑，而不是原始的檔案或行數。如果小型工作長大了，Harness 會保留已完成的部分，只針對剩下的部分重新規劃。

## 各部分如何組合在一起

```mermaid
flowchart LR
  Idea["產品構想或變更需求"] --> PRD["prd-builder\n產品與技術定義"]
  PRD --> Design["product-design-builder + frontend-design\n線框圖與設計系統"]
  Design --> Harness["fullstack-harness-engineering\n共用交付核心"]
  Harness --> Runtime["單一 host 轉接器\nCodex 或 Claude Code"]
  Runtime --> Evidence["本機測試與 UI 佐證"]
  Evidence --> Push["推送到這次執行自己的分支\n合進預設分支是你自己的步驟"]
```

你可以從任何階段開始。舉例來說，可以只用 Harness 修既有的 app。各技能各司其職：`prd-builder` 定義產品，`product-design-builder` 使用 `frontend-design` 定義 UI 契約，Harness 實作已凍結的結果。

## 交付模型

Harness 是圍繞明確的邊界所打造的：

1. 檢視目前的專案，找出需要做的工作。
2. 凍結相關的契約、來源、範圍與驗證步驟。
3. 當任務大到需要時，先規劃相依關係，再開始實作。
4. 只有在工作彼此獨立、隔離且經過明確授權時，才使用平行 worker。
5. 驗證任務結果、整合、相關的 UI 流程，以及最終的 diff。
6. 除非有人要求遠端結果，否則帶著驗證過的本機佐證停下；要遠端時，在精確的推送授權下，把這次執行自己的分支推送上去。開 PR、合併與部署都是你在 Harness 之外自己做的步驟。

對於有計畫支撐的工作，它會記錄任務範圍、相依關係、worker 歸屬、驗證指令，以及各動作專屬的授權。測試通過並不代表授權推送、移除 worktree 或刪除分支。

```mermaid
flowchart TB
  Intake["Intake: request, repo, instructions"] --> Size{"small or large?"}
  Size -->|small| Direct["Direct parent work<br/>no PLAN/RUN, no scheduler"]
  Size -->|large| Plan["PLAN v5 + RUN v10<br/>frozen contracts, authorization ledger"]
  Plan --> Observe["Record observed git + batch_base_sha<br/>(the selector returns an empty frontier without it)"]
  Observe --> Frontier["Ready frontier<br/>dependencies, scope/resource conflicts, permission gates<br/>bounded by observed slots x isolation x conflicts"]
  Frontier --> Host["One host adapter: codex or claude_code<br/>no cross-host fallback"]
  Host --> Work["Isolated mission worktree<br/>attempt + lease, worker tests + commits"]
  Work --> Review["Exact-head read-only review<br/>required before integration"]
  Review -->|pass| Integrate["Serial integration into the resolved branch"]
  Review -->|fix_required| Work
  Integrate --> Gates["Integration, batch, E2E and UI evidence gates"]
  Gates -->|fix_required| Repair["Bounded repair route"]
  Repair --> Rereview["Re-review on the new head"]
  Rereview --> Gates
  Gates -->|pass| Local["Local verification complete"]
  Direct --> Local
  Local --> Remote{"push requested and authorized?"}
  Remote -->|no| Done["Stop with verified local evidence"]
  Remote -->|yes| Push["Push the run's own branch<br/>run ends here"]
  Push -.-> Yours["PR, merge, and deploy:<br/>your own steps, outside the Harness"]
```


## 輕量的執行環境轉接器

共用核心掌管唯一的 PLAN/RUN 控制平面。執行環境專屬的啟動細節採延遲載入：

- Codex host 只載入 `fullstack-harness-codex`，也只執行 `codex` provider 的 PLAN 節點。
- Claude Code host 只載入 `fullstack-harness-claude-code`，也只執行 `claude_code` provider 的 PLAN 節點。
- 兩個轉接器都無法呼叫另一個執行環境。若某個已就緒節點的 provider 與當前 host 不符，會被回報為因 provider 不符而受阻，留給由對應轉接器主持的執行去處理。

共用的 script、schema、參考文件與範本仍放在 `fullstack-harness-engineering` 底下；轉接器只是連結到它們，而不會各自夾帶重複的執行環境。這讓預設提示詞維持精簡。

一次執行只有一個 active host。same-repository handoff 只有在 Host A 關閉 wave、且沒有 active 或 proposed wave 後才允許：Host B 保留 PLAN/RUN 與 graph state，重新探測 runtime，並在選取下一波前審查目前的 exact SHA。若需要修復，路由回 Host A 且舊 review 立即失效；除非未來 schema 增加可攜式的儲存庫／狀態身分，否則不支援 cross-machine handoff。

## 圖引擎與 Dynamic Workflow

這些技能使用兩層圖：

- **org 圖**是穩定的角色契約：產品、架構、UX、設計系統、mission-worker、reviewer、審批、整合，以及生命週期職責。
- **work 圖**是單次執行的暫時性任務圖。PRD 與設計工作流只有在 host 能夠強制套用 `builder_readonly` 工具設定檔時，才會使用有界的分析圖；否則會退回循序的 parent。工程流則使用標準的 PLAN v5 圖與 RUN v10 狀態。

訪談與審批留在執行中的工作流之外，因為 Claude Code Dynamic Workflow 無法在執行途中向使用者索取輸入。Parent 會先凍結輸入，執行一個有界的工作流，接著掌管分階段寫入、衝突解決、審批與發佈。

在工程流中，Harness 會先驗證並選出相依已就緒的 frontier，才建立或請求 worktree。原生的 Claude mission 使用位於 `.claude/worktrees/` 底下、由 parent 管理的 worktree，把每個 worker 綁到精確的批次 base，並要求在存取儲存庫前先 `EnterWorktree`。在每一條路線上，parent 都會驗證回傳的 commit 與實際的 Git diff、序列化地整合被接受的 commit，並重新計算圖的 frontier。

Claude Graph Workflow 會把 mixed frontier 按 homogeneous `tool_profile` 分成多個呼叫；同一組內可以使用不同模型與推理強度，但一次呼叫絕不混合寫入 mission 與唯讀 review。tool profile 是標籤與 prompt/result 契約，不是 permission-level tool removal。

- `mission_write` 要求 `EnterWorktree` 與 mission 的有界寫入契約。
- `code_review_readonly` 要求精確路徑審查與唯讀結果佐證；它不會移除繼承的工具。
- `visual_review_readonly` 使用精確的讀取/搜尋允許清單，審查保留下來的截圖或其他既有佐證。任何新的瀏覽器工具都必須先審核並加入設定檔，才能使用。

當 Claude Code 回傳真實的 Workflow 執行 ID 時，RUN 狀態可以保留 workflow/task ID、script digest、node group、圖/base 綁定、工具設定檔、狀態，以及可取得的度量。同一 session 內的續跑可以沿用該綁定；跨 session 的復原則從標準的 PLAN/RUN 狀態重新啟動一次新的 workflow 嘗試。

圖節點的 `allowed_providers` 必須包含實際在執行 Harness 的 host，該節點才能被選取。Claude Code 不能把節點委派給 Codex，Codex 也不能把節點委派給 Claude Code；兩者之間沒有跨 host 的橋接。若某個已就緒節點的 provider 與當前 host 不符，會被記錄為因 provider 不符而受阻，留給由對應轉接器主持的執行去處理。

## 安裝

這是一個私有的 GitHub 市集。你需要有 `Phlegonlabs/fullstack-goal-dev` 的存取權、完成 GitHub CLI 認證，並且安裝 Codex、Claude Code，或兩者皆有。

```bash
gh auth login
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### 最快安裝方式

```powershell
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
powershell -File .\scripts\update-private-skills.ps1
```

clone 只是為了拿到這個腳本。更新器一律從 GitHub 安裝（預設是 `Phlegonlabs/fullstack-goal-dev` 的 `main`），不會讀取你目前的工作目錄。本機的修改不會透過這個方式安裝；要測試本機修改，請看下面的「開發期間使用本機 checkout」。

接著開啟新的 Codex 任務，或重新載入 Claude Code。確認外掛已出現在清單中：

```powershell
codex plugin list
claude plugin list
```

### Zero-to-one 流程（從零開始）

1. 安裝一個受支援的 host（Codex 或 Claude Code）與本外掛，並用該 host 執行這次交付。
2. 開啟新的 host session，確認外掛可見，然後呼叫 `$fullstack-harness-engineering`。
3. 讓規模閘決定直接工作或 PLAN/RUN；小型工作不要預先建立 worker。
4. 大型執行一次只保留一個 active host，並在 same-repository handoff 前關閉與審查每個 wave。

### 單一指令更新器

共用更新器會偵測已安裝的執行環境、新增或更新市集，並在支援的地方安裝外掛。這個儲存庫更新後，重跑同一個指令即可。

搭配 PowerShell 7（`pwsh`）的 Windows：

```powershell
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

`pwsh` 要另外安裝。Windows 內建的 Windows PowerShell 5.1 也能執行這個腳本：

```powershell
Set-Location .\fullstack-goal-dev
powershell -File .\scripts\update-private-skills.ps1
```

搭配 PowerShell 7 的 macOS 或 Linux shell：

```bash
cd fullstack-goal-dev
pwsh -File ./scripts/update-private-skills.ps1
```

更新後請開一個新的 Codex 任務。更新 Claude Code 的外掛後，請重新載入或重啟 Claude Code。

### 直接在 Codex 中安裝

```bash
codex plugin marketplace add Phlegonlabs/fullstack-goal-dev --ref main
codex plugin add fullstack-harness@fullstack-goal-dev
codex plugin list
```

### 直接在 Claude Code 中安裝

```bash
claude plugin marketplace add Phlegonlabs/fullstack-goal-dev --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
claude plugin list
```

外掛安裝完成後，執行 `/reload-plugins` 或重啟 Claude Code。

### 開發期間使用本機 checkout

當你要測試這個儲存庫中的變更時，使用本機市集。不要在同一時間用同一個名稱同時註冊本機與 GitHub 市集。

```powershell
$repo = (Resolve-Path .).Path
codex plugin marketplace add $repo
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add $repo --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

## 常見提示詞

Codex 接受下列的 `$skill-name` 寫法。在 Claude Code 中，請呼叫已安裝、帶命名空間的技能，例如 `/fullstack-harness:prd-builder`，或直接用名稱指定。

```text
Use $prd-builder to turn this idea into a PRD, architecture, stack decisions, release targets, and test obligations.
```

```text
Use $product-design-builder with $frontend-design to create wireframes and the design-system contract from the approved docs/product/ product inputs.
```

```text
Use $fullstack-harness-engineering to review the existing app, plan the required work, and stop before implementation.
```

```text
Use $fullstack-harness-engineering to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
Use $fullstack-harness-engineering to implement this plan and push the verified branch. I will open the PR and handle the merge myself.
```

```text
Use $manage-cloudflare-worker-deployments to configure safe per-branch Cloudflare Worker previews and cleanup for this repository.
```

若要進行多任務交付，請在需求中說清楚預期的本機與遠端結果。建立分支、提交、整合、儲存庫設定、推送、移除 worktree 與刪除分支，都是各自獨立的動作。Harness 不會開 PR、不會合併、也不會部署——這些步驟由你自己完成。

## Codex 與 Claude Code 的執行

Harness 記錄的是實際的執行環境能力，而不是從已安裝的 CLI 去假設一個。

| 執行環境 | 偏好的平行路線 | 退回方案 |
| --- | --- | --- |
| Codex app（`fullstack-harness-codex`） | 在隔離、由 app 管理的 worktree 中執行 app 任務 | 直接使用 subagent，再退到單一循序的 parent |
| Claude Code（`fullstack-harness-claude-code`） | 使用對齊 base、由 parent 管理的 `.claude/worktrees/` worktree 執行 Dynamic Workflow | 直接使用 subagent，再退到單一循序的 parent |

在 Codex 中，偏好的路線分成兩層：每個選中的 mission 先在左側欄開一個獨立的 top-level conversation，並綁定自己的 app-managed worktree；接著由該任務按需執行可選的、有界 Multi-agent 輔助。Coordinator 直接建立的 subagent 不能取代這些 top-level 任務。若 project/thread 工具一開始尚未載入，轉接器會先從目前的 Codex 工具介面找出它們，再考慮退回方案。當使用者明確要求這個結構時，缺少 thread 能力是 blocker，不能把工作縮回同一個 conversation。

目標 repo 自己的 branch 規則優先。當 repo 未定義其他流程時，mission worktree 從目前預設分支的 SHA 開始，在綁定當前 head 的唯讀 review 通過後整合進這次執行自己的分支；當驗證過的分支推送完成，這次執行就結束了。把它合進預設分支是你自己的步驟。若有修正，必須對新 head 重新 review。

每個轉接器只執行那些允許 provider 包含自身 host 的 PLAN 節點；沒有跨 host 的路線。若某個節點需要另一個 host 的 provider，會被回報為因 provider 不符而受阻，而不會在這裡執行。

平行實作預設沒有固定的小上限；設定中的寫入 worker 上限刻意設得很高，實際的波次是由觀察到的 worker 名額、隔離容量，以及相依已就緒、無衝突的 frontier 大小來界定。每個 worker 都需要隔離的工作區、有界的寫入範圍、一個 verifier，以及明確的授權。Codex nested helpers 是可選的，但 parent/review graph 的 exact-head PASS 仍是強制閘門。Worktree 只有在選出就緒 frontier 之後才會配置。原生的 Claude mission 會進入分派給它的、由 parent 管理的 worktree。Worker 絕不編輯 parent 的 `PLAN.md` 或 `RUN.md`，也不推送、開 PR、合併、部署或移除 worktree。Parent 掌管整合以及每一個落地或生命週期動作。

## 儲存庫結構

```text
.agents/skills/                                      標準技能來源
plugins/fullstack-harness/skills/                    產生的外掛副本；請勿直接編輯
plugins/fullstack-harness/.claude-plugin/plugin.json Claude Code 外掛 manifest
plugins/fullstack-harness/.codex-plugin/plugin.json  Codex 外掛 manifest
.agents/plugins/marketplace.json                     Codex 市集定義
.claude-plugin/marketplace.json                      Claude Code 市集定義
assets/                                              README 封面
scripts/sync_plugin_skills.py                        把標準技能複製進外掛套件
scripts/update-private-skills.ps1                    更新已安裝的市集與外掛
.github/workflows/harness-ci.yml                     契約、單元與 E2E 檢查
```

## 維護市集

只編輯 `.agents/skills/` 中的標準來源，接著同步並驗證產生出來的外掛套件。

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
python -m unittest discover -s .agents/skills/prd-builder/scripts/tests -v
python -m unittest discover -s .agents/skills/product-design-builder/scripts/tests -v
python -m unittest discover -s plugins/fullstack-harness/skills/fullstack-harness-engineering/scripts/tests -p "test_packaged_*.py" -v
git diff --check
```

發佈之前，請在兩份外掛 manifest 與 `.claude-plugin/marketplace.json` 中更新一致的版本號、檢視完整的 diff，並使用儲存庫的 PR 流程。不要直接推送到 `main`。

## 安全性與資料安全

- 別把 GitHub token 及其他憑證放進這個儲存庫。
- 更新器使用你既有的 GitHub CLI session；它不會在專案裡儲存 token。
- 在確認外掛能正確載入之前，別刪掉舊的獨立技能副本。
- 編排技能對於每一個會改變狀態的 GitHub 或生命週期動作，都要求明確授權。

## 版本紀錄

每次發佈都要更新這一節，並搭配上面說明的版本號提升。

- **0.3.0** — 移除 GitHub 落地轉接器與整套部署／發佈模型。Harness 現在到「推送這次執行自己的分支」為止；把分支合進預設分支是使用者自己的步驟。授權帳本從 19 個動作縮到 12 個；`landing` 精簡為 `mode`、`remote`、`pushed_head_sha`、`continuity`；`integration.branch` 是唯一的分支欄位。移除分支保護佐證、`target_sources`、三個契約標記、`post_merge_cleanup`、`plan.release` 與 `run.targets`。
- **0.2.0** — 預設每個 mission 一個 worktree；PLAN v5 / RUN v10 typed graph，支援多 reviewer 扇出；Cloudflare 的 dispatched-deploy 與 Auto-Deploy（原生 Git 自動部署）發佈模型；持久的整合分支；以逐頁通用 HTML 樣稿取代已退役的 page UI matrix；行動裝置／桌面平台支援，包含一份專屬的行動裝置技術選型指南（原生 iOS/Android、Flutter、React Native/Expo）；透過 `.env.example` 產生環境密鑰的 scaffolding；為有界／機械式的委派工作新增 Haiku 成本層級。
