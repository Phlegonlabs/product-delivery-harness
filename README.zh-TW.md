<p align="center">
  <img src="./assets/readme-cover-zh-TW.png" alt="產品交付控制框架：定義、設計、交付、驗證" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>繁體中文</strong> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml/badge.svg"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.97.0-059669?style=flat-square">
</p>

# Product Delivery Harness

這套技能讓 Codex、Claude Code、Pi 或其他支援 skills 的 host，把產品構想與變更需求轉成經過驗證的軟體。產品定義、設計、實作、安全與外部設定各自保留來源、證據及 owner 決定。

## 安裝

需要 Python 3.10 以上、Git，以及能探索 `~/.agents/skills/` 的 host。Windows 請在 Git Bash 執行 `./install.sh`。

```bash
git clone https://github.com/Phlegonlabs/product-delivery-harness.git
cd product-delivery-harness
./install.sh
```

安裝器會鎖定目的地，只暫存 Git index 已追蹤的 bundle 檔案。它把目前與舊版 managed ID 備份到 `~/.agents/skill-backups/product-delivery-harness/`，再逐路徑、逐位元組驗證安裝結果。

安裝器拒絕不安全的連結與非預期來源檔案。Attempt ownership marker 讓 rollback 只處理本次建立的路徑，保留外來路徑與舊備份。來源收據記錄 source SHA 與未提交狀態。安裝器會印出新安裝的 five-skill contract digest 與被取代的那一個，並與收據一起保存；`harness_contract.py --skills-root <dir>` 可印出任一 skills tree 的 digest。

安裝器複製 scripts、references、assets 與 templates。測試保留在來源 checkout，請在該處執行。驗證前先安裝固定的 Python 依賴：

```bash
python -m pip install -r skills/delivery-harness/requirements-test.txt
```

更新沿用同一安裝器，不能用 raw-copy 覆蓋。先取得授權、暫停相關 skill session 並保留備份；驗證成功後才開啟新的 host session。安裝失敗會 rollback；後續驗證失敗時，從前一個 release tag 重跑安裝器。consumer repository 接著依 [bundle adoption](skills/delivery-harness/references/bundle-adoption.md) 採用新 bundle：更新 `AGENTS.md` 的 `## Harness Version` 項目，執行 `check_skill_bindings.py --previous-skill-dir <installer backup>` 把每個變動的 pin 標為 `previous_release` 或 `owner_pin`，並在 Epic 的 Change Log 記一列。

從 0.23 或更早版本升級時，在同一份備份中用原 ID 保存各舊目錄：`full-harness` → `delivery-harness`、`prd-builder` → `product-definition-builder`、`product-design-builder` → `design-system-compiler`。自 0.73.0 起安裝器也會退役 `code-security-review`（改為 `delivery-harness/references/security-review.md`）、`product-activation`（改為 deployment record 與 `references/external-setup.md`）與 `seo-growth-review`（改為 `growth-review`）。

UI 工作另需 [dependency manifest](skills/delivery-harness/assets/external-skill-dependencies.json) 固定的完整 `frontend-design` 與 `impeccable` tree。依紀錄的路徑安裝，再執行 `check_external_skill_dependencies.py`。更新 full-tree pin 前須審查變更；專案 Skill Bindings 保留 owner 已確認的選擇，不可悄悄換 skill。

## 從這裡開始

| 目前起點 | Skill | 結果 |
| --- | --- | --- |
| 產品構想 | `product-definition-builder` | 已批准的 PRD、architecture、stack、TEST 義務與 BDD feature 檔案 |
| 已批准且包含 UI 的 Product Definition（Product Thesis 之後即可開始設計，可先做選用的探索輪） | `ui-design-builder` | 方向、journey map、完整 HiFi、瀏覽器證據與 Visual Approval |
| 已批准且需要設計系統的 HiFi | `design-system-compiler` | 凍結的 pair 與來源綁定衍生 HTML |
| 有界實作或維護 | `delivery-harness` | Direct 工作或 managed PLAN/RUN；驗收 scenario 由 PRD 的 feature 檔案產生；UI mission 依已批准的 journey 進行 |
| 有公開搜尋 surface 的產品（PRD 之前），或已發布且有任何可被發現 surface 的產品 | `growth-review` | PRD 之前的 keyword map（`demand_research`）；逐 surface 的增長 review 與已路由後續工作，除 keyword map 外唯讀 |

Source-runtime plate 也支援具唯一標記、且 surface、state 與 target 條件符合該列的共用主體。產品腳本執行前會先綁定選定狀態。只有內容與檢視器面板位置完全符合的已知 design-token 填值腳本會被排除；內容相同的產品腳本仍保留綁定，樣本有歧義仍會失敗。 初始 hidden 可由元素自身宣告的狀態規則控制；沒有狀態控制器的隱藏路徑仍會失敗。

五個核心 skills 與五個獨立 skills 都只在你明確點名呼叫時啟動，例如 `$delivery-harness`；亦可繼續已呼叫的工作。一般任務不會自動跑 Harness 分流、文件同步、Epic 紀錄或 PLAN/RUN。安裝、專案指令與既有文件都不代表呼叫。被呼叫的 skill 保留必要檢查與依賴；新的頂層階段需要明確要求。Codex 設定為 `allow_implicit_invocation: false`，其他 host 依同一指令邊界執行。

相關選擇尚未解決，或既有決定需要參考背景時，使用[參考選擇規則](skills/delivery-harness/references/reference-selection.md)與[可選目錄](skills/delivery-harness/references/option-library/README.md)。兩者都不是前置條件，也不授予執行權限；既有決定與批准仍有效。

## 常見提示詞

Codex 使用 `$skill-name`；其他 host 可直接指定 skill 名稱。說明準確寫入範圍，以及本機或遠端的預期結果。

```text
Use $growth-review in `demand_research` mode before the PRD: research search demand for this product's public pages, group the keywords into clusters with stable `KW-*` IDs and write `docs/product/keyword-map.md`, labeling every figure observed, estimated or hypothesis. Change no other file.
```

```text
Use $product-definition-builder to define this product, including complete frontend/backend architecture, data/auth/deployment choices, coherent stack options, UI behavior, release targets, tests with their feature files, and Product Definition Approval. Stop before UI design.
```

```text
The Product Definition is approved. Use $ui-design-builder with the `ui-design/3` contract and mandatory $frontend-design. Run the product preflight, read the PRD UI Surface Contract directly, and show three materially different directions over the same representative cases for my selection.
```

```text
I selected a direction. Continue $ui-design-builder with $frontend-design: build the kit and pilot pages first, then the complete connected HiFi, run the HiFi completeness preflight, then run $impeccable critique and audit plus H1-H9 grading. Ask for one full Visual Approval covering copy, structure, product menus, tabs, visuals and tokens, then use $design-system-compiler for the required `design-system/4` pair and frozen derived HTML.
```

```text
Use $delivery-harness to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
The delivery is complete. Use $delivery-harness to perform the external setup rows in docs/DEPLOYMENT.md for the production release targets, configure only the exact actions I approve, verify each result by read-back, and record the Measurement Sources status.
```

```text
Use $growth-review to read back every surface of this released product with its own lens, reconcile the verified measurement sources against the Growth Contract, prioritize evidence-backed opportunities per surface, and route every proposed change without modifying the product or external accounts.
```

## 包含的內容

| Skill | 負責範圍 |
| --- | --- |
| `product-definition-builder` | 含 `## Ambition`、At a Glance `Shape` 列與 `## Growth Contract` 的 `PRD.md`、`architecture.md`、`stack-decisions.md`、`docs/product/features/` 內的 feature 檔案、研究、各輪 PRD delta 與 Product Definition Approval；多模組產品的 `program` 交付檔（程式級 PRD 加每模組一個[模組套件](skills/product-definition-builder/assets/templates/PROGRAM_PRD.template.md)，逐模組驗證）、[AI 功能契約](skills/product-definition-builder/references/ai-feature-contract.md) 與多模組產品的 modular monolith 模式；每張 stack 表都有 `BDD runner` 列，批准區塊帶 `Feature files` digest，Test Obligations 一旦指明其 feature 檔案，套件 checker 就檢查 feature 覆蓋（含 eval-policy 的 scenario id）；適用時，PRD 引用 `docs/product/keyword-map.md` 的 `KW-*` cluster |
| `ui-design-builder` | 由 `UI_DESIGN.template.md` 建立的 `docs/design/ui-design.md`、方向研究與完整已批准 HiFi 包，另有集中缺陷 ledger（`UI_DEFECT_LEDGER.template.json`）以及 grader、Impeccable operator、pilot 診斷與複查 packet（`UI_REVIEW_PACKET.template.md`）的模板；新視覺範圍另保留 `docs/design/directions/<round>/references/` 下的參考板截圖 |
| `design-system-compiler` | 凍結的 `design-system.md`／`design-system.json` 與 `design-system-preview.html`；`check_design_system_pair.py --write-bindings` 由 `ui-design.md` 填入 `sourceBindings`，`--write` 把 `contrastPairs` 與 `typeSteps` 的比值寫入產生的證據區塊，`design-system/4` 的 JSON token 須與 HiFi CSS 中的同名宣告一致 |
| `delivery-harness` | 範圍路由、授權、任務、整合、驗證、由 PRD feature 檔案加一份 run profile 產生的交付驗收 register、PRD delta 規則（新增或修訂需求的每個 Required TEST 都須有新增或改動的 scenario）、安全 lens、`docs/DEPLOYMENT.md` 內的外部設定與量測來源（含 [GA4 後台設定](skills/delivery-harness/references/ga4-admin-setup.md) 與 AI 供應商設定）、[效能與成本預算](skills/delivery-harness/references/performance-and-cost-budget.md)、跑完會清掉自己產物的原生驗證，需要時的 PLAN/RUN，以及 managed stage cards 與自主執行用的 launch brief；初始化的專案 `AGENTS.md` 含 `Harness Version` 與 `Behavior Specs` 段落，另有 direct 路線的 [assignment](skills/delivery-harness/assets/templates/ASSIGNMENT.template.md) 與 [review brief](skills/delivery-harness/assets/templates/DIRECT_REVIEW_BRIEF.template.md) 模板、由 `build_delivery_results.py` 轉成 `delivery-results.json` 的 [delivery evidence](skills/delivery-harness/assets/templates/DELIVERY_EVIDENCE.template.md) 檔案，以及對既有 app 先取證再改的 [open-ended refinement](skills/delivery-harness/references/open-ended-refinement.md) |
| `growth-review` | 依 Surface Catalog 逐 surface 各用一個 lens：搜尋與答案引擎、商店列表、registry 與目錄、bot 平台、桌面 app，以及團隊經營的帳號；含 `pre_launch`、`demand_research`、`baseline`、Day 7 與 Day 30 `growth_review` 與 `traffic_drop` 模式，直接回覆，唯 `demand_research` 在 PRD 之前執行並寫出唯一的輸出 `docs/product/keyword-map.md`；與 `docs/gtm/MESSAGING.md` 矛盾的線上文案算 finding |

## 獨立 skills

[Go To Market](standalone-skills/go-to-market/SKILL.md) 選擇渠道與實驗、每個專案保留一份 messaging record、把 PRD 的 Launch Window 延伸成 launch runbook、為 Growth Contract 的再觸及機制撰寫 lifecycle messaging，並準備各渠道草稿、素材、日曆與附兩個 hook 的各渠道變體，涵蓋開發者渠道與商店 listing。

[Customer Discovery](standalone-skills/customer-discovery/SKILL.md) 規劃使用者訪談、整理去識別化筆記，並把 `RA-*` 候選發現交回 Product Definition。[README Studio](standalone-skills/readme-studio/SKILL.md) 用實際展示編寫專案 README，有 messaging record 時從中取第一行。[Release Packager](standalone-skills/release-packager/SKILL.md) 驗證 release artifact 與使用者安裝路徑。[Logo Studio](standalone-skills/logo-studio/SKILL.md) 由品牌簡報開始設計 logo：先畫大量黑白草圖，寫明篩選理由，再把入選構思精修並做壓力測試，最後由 owner 選定。

這五個完整 skill 目錄須另行向 host 註冊；`install.sh` 只安裝五個核心 skills。註冊、build、下載、簽章、發佈、排程與帳戶變更保留各自授權。沿用既有產品與量測紀錄，不新增 review wave。

## 各部分如何組合在一起

```mermaid
flowchart LR
  Product["Product Definition 與 Ambition、Growth Contract、feature 檔案、owner 批准"] --> UI["UI 方向、journey map 與完整 HiFi"] --> Design["Visual Approval 與必要設計系統 pair"]
  Product -.->|"Product Thesis 之後的選用探索輪 R0"| UI
  Product -->|"無 UI，或限域增強或維護"| Harness["Direct 或 managed 交付"]
  Design -->|"mission 依已批准的 journey 進行"| Harness
  Harness --> Review["最終 SHA 的一次合併 review"] --> Tests["一次 broad final validation 與交付驗收 register"] --> C["固定候選 C"]
  C -->|managed| A["僅 managed：archive-only A"] --> Publish["已授權候選發佈與適用 Preview"]
  C -->|direct| Publish
  Publish --> Main["另行授權 exact-SHA main landing"] --> Setup["逐 target 外部設定讀回"] --> Outcome["量測成效與可選 growth review"]
```

初次 UI 交付須先完成設計與所有適用自查，才能進入 Harness 執行。依[作者自查](skills/delivery-harness/references/pre-delivery-self-review.md)，在下表的 Product、方向與 HiFi 既有出口完成檢查。

## 運作規則

以下流程規則只適用於你明確呼叫的 skill 工作。

Delivery core 只做一次規模判斷：一位 writer 配一段連貫驗證即可完成的工作走 direct；幾個互不依賴、檔案不重疊的部分走 [Direct Fan-Out](skills/delivery-harness/references/direct-fan-out.md)：每位 writer 一個 worktree，merge check 一通過就合回工作分支。互相依賴的 missions、持久交接或有界 correction graph 使用 PLAN/RUN。Mission 是功能批次，細 task 各自保留 atomic commit。owner 選擇 `Delivery profile: mvp` 時，小型專案或一週 MVP 走壓縮路線：stack 與產品批准一次合併呼叫、必要頁面才做 HiFi、一次合併交付 review 併入 Final UI Acceptance，owner gate 最多四個；證據、安全與資料保護規則不變。

- [進場與交接](skills/delivery-harness/references/governance/task-and-handoff.md)：檢查目前指令與來源；未知的 loaded identity 維持未知。目前 Epic 就是 `docs/DOCUMENTS.md` 的 `Current Epic:` 行所指的那份；索引只留一列 `docs/epics/`，各 Epic 的狀態寫在自己的檔案。初始化會從 `PROJECT_GITATTRIBUTES.template` 建立缺少的 `.gitattributes`，讓雜湊綁定的檔案逐位元組保存（[gitattributes 契約](skills/delivery-harness/references/gitattributes-contract.md)）；`configure_project_context.py --check` 不寫入任何檔案，回報 attribute 缺口、每個過時 `AGENTS.md` 段落的 diff，加上 `--documents` 時也回報 `docs/DOCUMENTS.md` 的偏差。managed run 從 inspector 的 `Next` 區塊恢復；停滯的 `running` RUN 先要 owner 決定，自主執行從已簽署的 launch brief 開始。
- [分工](skills/delivery-harness/references/delegation-contract.md)：agent 設定與 AGENTS 決定 executor、model、effort 與 fallback。每個 checkout 只有一位 writer；被分派的 worker 不能再次分派。brief 與 review packet 在啟動前先依路線的時間、turn 與 byte 上限切好大小。期限已到卻沒有 verdict，視為環境受阻，改以較小的 scoped 呼叫重新分派。變動邊界的設計與 review 依 [architecture method](skills/delivery-harness/references/architecture-method.md) 進行。
- [驗證](skills/delivery-harness/references/verification-gates.md)：必要證據綁定準確候選；缺能力或證據維持 blocked。阻擋性的程式碼發現必須附上他人可重跑的證據；改動碰到信任邊界時，若已設定另一廠商的 reviewer，會加入第二位 reviewer。瀏覽器矩陣的獨立 review 採先驗證再抽樣：驗證 receipt，檢查 FAIL 與經 diff 標記的列，再抽樣 PASS 列。瀏覽器能力探測在同一 session 內重複使用。沙箱內跑不了 git 的 reviewer 以 `review_input.py` packet 證明身分與 checkout 乾淨。`build_verifier_request.py` 依 live lease 建立 worker 與 task 的 verifier request；`security_review_result.py --result <file> --reviewed-sha <sha>` 不寫入任何檔案，檢查 direct 路線的安全審查結果。
- [交付驗收](skills/delivery-harness/references/delivery-acceptance-contract.md)：feature 檔案是 owner 批准的 PRD 內容，step definition 是程式碼。交付驗收 register 由 feature 檔案產生，不能手動編輯。改 scenario 文字是產品決定，須走 PRD delta；只改 step definition 是現有 Epic 上的小修正。BDD runner 是 stack 決策的一部分。run profile 的 `variants` 與 `assign` 對照可產生混合平台的 register；`render_delivery_acceptance.py --check` 只回報偏差，不寫入。
- [候選發佈與晉升](skills/delivery-harness/references/branch-promotion-contract.md)：保留準確 target、授權與遠端讀回，不得 force-push。符合資格的 repository 可以憑 owner 事先記錄的授權落地一個 Epic，每個動作之前由 `landing_gate.py` 對照確切候選版本檢查。[Card 8](skills/delivery-harness/references/stages/stage-cards.md#card-8-archive-publish-and-promote) 依序列出歸檔、發佈與晉升指令。
- [來源維護](skills/delivery-harness/references/governance/source-maintenance.md)：每個 atomic task 跑聚焦檢查，固定候選跑一次完整 matrix。

每次交接前，核對來源雜湊（source hashes）、Epic 紀錄與文件一致性，並原地重寫 Epic 的 `## Handoff` 區塊（階段、有效核准、剩餘工作、下一步）；每個 skill 進場先讀這個區塊。文件同步計算每份 Epic 的雜湊時不含該區塊，所以重寫它不算 drift。`docs/tasks.md` 由 RUN 衍生，交付驗收 register 由 `render_delivery_acceptance.py` 從 feature 檔案產生；不能手動編輯產生區段。[文件同步](skills/delivery-harness/references/document-sync-contract.md)、[有界修復](skills/delivery-harness/references/bounded-enhancement.md) 與[交付驗收](skills/delivery-harness/references/delivery-acceptance-contract.md) 擁有這些檢查規則。

| 階段 | 預設 review 與停止條件 |
| --- | --- |
| Product Definition | 草稿與研究對帳完成後，作者自查整套文件一次；owner 批准前重查受影響變更；之後再做一次獨立唯讀 PRD review 與一次定向複查，owner 依十題 review 指南決定。其後的缺陷走隔離修復加 scoped review。 keyword map 先於頁面清單；route 的 `<title>` 與 meta description 是內容欄位，不需 PRD delta 即可改寫。 |
| 方向 | 新視覺範圍先建立 9–12 張截圖的參考板，owner 有參考庫時先從庫裡挑。各研究的作者先檢查並修復自己已渲染的研究，再交 owner 選擇；檢查包含 `slop_scan.py` 與對照參考板的比對頁。三個研究，主機有容量時由不同作者同時撰寫。owner 在 `_compare.html` 並排看到參考板、提議的原則和各研究，一次回覆就確認原則並選定方向，也可以要求一次針對某個研究的三個變體。 |
| HiFi | 三層，先建 kit（token 與每個控制項的所有狀態，一份產品樣式表）和 pilot 頁，再做組合與美術；先做靜態，再加動效。作者在每條 journey 之後跑檢查，含量測無障礙。完整性 preflight 後，原作者先自查及修復，再交獨立 review；自查包含 `slop_scan.py`，以及用 `capture_sheet.py` 把選定方向和候選稿並排的比對頁。每個候選稿只做一次矩陣擷取；一輪 review 加同一批 reviewer 的一次收斂複查，不再有 scoped 複查；block 必須附上可重現的失敗、違反的規則與關閉條件。Impeccable `critique` **與** `audit` 完成，且四捨五入的 H1–H9 總平均 **至少 85**、每項 **至少 80** 後，才取得 Visual Approval。 |
| 交付 | `review_policy: final_candidate`：固定最終 SHA 上一次合併 code、適用 UI visual 與 security review（UI 使用真實瀏覽器），另加一次定向複查。之後每個剩餘缺陷各成一筆有界修復，只對其修復差異做 scoped review。 |
| Release | 一個 owner 指令可指定多個準確 release 動作。Archive-only A 與 tree 相同的 server main S 按下列規則繼承已驗證證據；tree 不同就是新候選。 |
| 外部設定 | `docs/DEPLOYMENT.md` 每個動作一列 External Console Setup，另有 Measurement Sources 表，每次 release 在 Release Log 記一列。逐 release target 驗證授權、獨立讀回與適用行為；前置準備與 production readiness 分開。商店或安裝程式 target 須有安裝或下載證明；只有上傳時維持 `pending`。 |

## 通用 runtime adapter

目前 driver 為 `subagents` 與 `sequential_parent`，由 [runtime adapter](skills/delivery-harness/references/runtime-adapters.md) 對應實際觀察到的 native 工具。Parent 執行不能替代獨立 review。Host verifier 使用目前使用者權限，不提供檔案系統或網路隔離；有能力不等於有授權。

保留十二個[動作權限](skills/delivery-harness/references/execution-state-model.md#authorization-action-ledger)：

```text
invoke_external_runtime, spawn_subagents, create_user_owned_tasks,
create_local_worktrees, create_app_managed_worktrees, create_local_branches,
create_local_commits, integrate_locally, push, archive_worker_tasks,
remove_worktrees, delete_branches
```

目前 RUN 在本機以 `local_only` 結束，`push` 為 false，`pushed_head_sha` 為 null。發佈、受保護分支 landing、部署、安裝、歸檔與清理保留各自授權。任務通過時 worker 回傳 `WORKER_RESULT`，阻塞或失敗時回傳 `worker_result: null` 的 graph node result，驗證、review 與整合權保留在 parent。

## 儲存庫結構

| 路徑 | 用途 |
| --- | --- |
| `skills/` | 五個 canonical skills、references、assets、templates 與來源測試 |
| `standalone-skills/` | 另行註冊的可選 skills |
| `assets/` | README 封面素材 |
| `docs/` | 現行索引與任務紀錄 |
| `.github/workflows/harness-ci.yml` | Exact-candidate CI |
| `install.sh` | 經驗證的 bundle 安裝與更新 |

## 維護技能

修改 canonical 來源時，同步更新四種語言 README 的說明。依變動檔案選擇聚焦測試與反例；在來源 checkout 執行：

```bash
python skills/delivery-harness/scripts/check_skill_spec.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_skill_contract.py"
python skills/delivery-harness/scripts/docs_weight.py
python skills/delivery-harness/scripts/prepare_release.py --check
git diff --check
```

[必要 matrix](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) 在固定候選上透過 CI 跑一次，只有 CI 不可用時才在本機用 `python skills/delivery-harness/scripts/ci_test_shards.py matrix --base <released main SHA> --log-dir <new directory>` 執行完整 matrix，它為每一步寫一份 log 與 `summary.txt`。保留瀏覽器與 native 覆蓋，失敗或輸入變更時重驗受影響部分；沿用證據須保留原始來源。

## 發佈

遵循[來源 Git flow](skills/delivery-harness/references/governance/source-maintenance.md#git-flow) 與[必要驗證](skills/delivery-harness/references/governance/source-maintenance.md#required-verification)。已審查的來源候選經必要 PR 進入受保護 `main`，並在該 commit 加上 `v<version>` tag。設定版本時，把四段版本紀錄寫進同一目錄的 `en.md`、`zh-TW.md`、`zh-CN.md` 與 `es.md`（各一行），再執行 `python skills/delivery-harness/scripts/prepare_release.py --version <X.Y.Z> --entries <dir>`。任何版本欄位不一致時它會拒絕；一致時把新版本寫進 `VERSION`、`package.json`、`package-lock.json` 與四份 README，並把 README 最舊的一筆紀錄移到 `CHANGELOG.md`。測試從 `VERSION` 讀取版本，不新增 hard-coded literal。

Archive-only A 須為 C 的直接子 commit，通過準確、receipt-bound 歸檔驗證後才繼承 C 的證據。差異只可包含收據列出的 coordination／evidence 搬移、可選的衍生 `docs/tasks.md`、`docs/DOCUMENTS.md` 更新與 `ARCHIVE_RECEIPT.json`，其他路徑保持不變。保留 C 已審 SHA 與各結果的原始來源，不把繼承證據當作 A 的新執行。Server 產生的 main SHA S 若 tree 相同，連同原始來源繼承候選證據，由 `promotion_readback.py post` 的 JSON 證明；不因 tree 相同而重跑完整 suite 或安全審查。Tree 不同則重新驗證新候選。

發佈須綁定 owner 授權的準確 SHA 與 branch，使用 no-force push 並讀回遠端。一個 release 指令可同時綁定這些授權；遇到 drift 或 gate 失敗就停止。正式 release 驗證完成後，若已安裝 bundle 不同，在相關 session 靜止時以官方安裝器更新，保留備份及驗證。Badge 不能證明已安裝或已部署。

## 安全與資料保護

憑證與使用者資料不得進入儲存庫。保留無關檔案、worktree 與備份，刪除或替換須有準確 owner 授權。唯讀安全審查不會擅自安裝 scanner、改程式或探測線上 target。詳見[安全審查](skills/delivery-harness/references/security-review.md)與[資料保護](skills/delivery-harness/references/governance/development-rules.md#protect-local-data)。

## 授權

[MIT](LICENSE)。重用第三方程式與素材時保留授權與署名。

## 版本紀錄

- **0.97.0** — 專案現在可以讓 HiFi 和前端作者查詢 Google 的 Modern Web Guidance，而不必安裝它。Skill Bindings 多了選用的 `web_platform_guidance` 列：保持 `pending`，或綁定 `modern-web-guidance@1.0.1` 和它 registry tarball 的 SHA-256；`check_skill_bindings.py` 只接受這個 pin。作者一律透過 `delivery-harness/scripts/modern_web_guidance.py` 執行：固定這個版本、關閉用量資料和它自己的檔案記錄、只允許 `search`、`list`、`retrieve`，並把 PRD 的 Baseline 目標交給 `retrieve`，讓指南只列出這個目標還需要的 fallback。`visual_inputs.py` 產生的 HiFi 和 implementation 作者區塊，現在會帶上 PRD 的 Browser support 值和 Modern Web Guidance 規則的位置。在 HiFi 裡，output contract 要求的標記和 ARIA 屬性優先於任何指南。PRD 的 Frontend Delivery Requirements 改為以 `Browser support:` 開頭，填 `Baseline Widely available`、`Baseline Newly available` 或 `Baseline <年份>` 其中之一；現有 PRD 不受影響。

- **0.96.0** — `hifi_matrix_capture.py` 的互動測試改成每個產品互動只在最小的來源寬度用鍵盤觸發一次，點擊仍在每個寬度都測。在 0.95.0 實測的十個 repo 裡，1,293 個操作中只有 3 個的點擊和鍵盤結果不同，不同寬度結果不同的則有 56 個；而其他寬度的鍵盤測試佔了互動時間的 35%。用那幾次 run 重算，測試從 9,946 次減為 6,266 次，623 個有錯的操作中只會漏掉 1 個：hk-car-care 較大手機寬度上的一個鍵盤焦點錯誤。檢查器接受新的結果列，也接受舊版 driver 寫的、每個寬度都有鍵盤列的收據；介於兩者之間的都不通過。0.96.0 driver 寫的收據需要 0.96.0 的檢查器。

- **0.95.1** — 修補版本，收錄用 0.95.0 實測十個 repo 後的三項修正。`hifi_matrix_capture.py` 的無障礙量測在任何畫布縮放下都略過只給螢幕閱讀器的文字：在 `zoom-200` 下，這類文字的 1 px 方框被放大一倍而被量測，上一次 jolvex run 的 652 筆 `text-clip` 失敗裡有 580 筆是這種情況。目的地在來源頁面上的互動，現在 10 秒後判定失敗，不再等滿 30 秒的動作上限；那幾次 run 的 276 次目的地等待失敗裡，有 236 次是這種狀態切換。會載入頁面的嘗試仍保留 30 秒上限，因為進入 jolvex 大頁面的導覽最多等了約 10.4 秒。在 direct 路線上，修復只重跑失敗的套件和改動檔案選出的檢查，其他套件沿用原結果並註明執行時的 SHA；tree 與已驗證 tree 相同的 head 直接引用那次的確定性結果，不再重跑。這取代了「修復不沿用任何結果」的舊規則。

- **0.95.0** — UI review 的次數更少，瀏覽器時間更短。一輪 review 固定兩位 reviewer，即 lead grader 和 Impeccable operator，不按頁組拆分；他們用肉眼看每頁的最小尺寸、機器結果標記的每個案例和 stress axis 樣本。他們的觀察紀錄只需涵蓋這個範圍：critique、audit 和 grading 的 receipt 不再要求每個案例都有觀察。複查只判斷先前的發現和這次修復：未改動內容裡原本就有的缺陷記為下一輪的備註，除非它是修復造成的，或屬高或嚴重的安全問題。派出一輪 review 或複查之前，`review_evidence.py ready` 檢查作者對凍結 package 的擷取，印出 READY、NOT READY 或 INVALID；卡死或 driver 故障只重跑一次，之後交給 owner。`hifi_matrix_capture.py` 的中間寬度只掃每個畫面的 axis 取樣狀態，也不再在那裡重跑所有互動：jolvex 上一次 run 的 630 個案例變成 150 個，4,344 次重複嘗試不再執行，約佔那次瀏覽器時間的一半。舊的中間寬度 receipt 仍然有效。重啟次數上限按頁面和操作計算，同一操作的嘗試無論幾個 worker 都在同一個瀏覽器執行；無法重啟的瀏覽器只擋住它所在的頁面；結果行會印出時間花在哪裡。新的 `text-split` 量測找出被斷成兩行的數字和短的中日韓詞語。`parity_capture.py --recapture <IDs>` 只重拍修復影響的路由，HiFi 沿用改為逐頁比對。一輪工作在結束前保持它的 Harness 版本，`review_input.py --remove` 刪除已通過的 review packet，`docs/evidence/` 和 `docs/design/evidence/` 下的原始擷取不進 Git，審批檢查會列出需要強制加入的引用截圖。停止卡住的 driver 或發佈包 CLI 時，不再沿用 Windows 重用的父程序 id，因此不會誤殺無關的程式。

- **0.94.0** — 交接檢查遇到讀不懂的內容，現在會拒絕而不是略過。已核准的公開主張會對照目前的研究：研究發現已撤回、未驗證，或觀察到的受訪者少於三人，都會失敗；campaign 稿引用過期、讀不懂或重複的核准，也會失敗。PRD 引用不存在的 `KW-*` 會失敗，關鍵字地圖指定的頁面必須引用對應的 cluster。無介面的工具可以記錄「沒有公開曝光」及其理由，之後只能經自有渠道上線。Growth Contract 的 Launch Window 必須用六欄表格，每列寫明 Destination；舊的五欄表格要補上這一欄。`growth-review` 會把搜尋需求對應到各語系的商店上架欄位，優化新增公開頁面時也會做需求研究。Release packager 會檢查 npm 套件檔內實際的圖片和 CLI 範例，拒絕 shell 語法，並在時限到時停止 CLI 的整個程序樹；無法確認已停止時會如實說明。預設的規格檢查涵蓋五個獨立 skill。

較早版本：[英文 CHANGELOG.md](CHANGELOG.md)。
