<p align="center">
  <img src="./assets/readme-cover-zh-TW.png" alt="產品交付控制框架：定義、設計、交付、驗證" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>繁體中文</strong> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml/badge.svg?branch=main"></a>
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-2563EB?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude_Code-supported-D97706?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-0.32.0-059669?style=flat-square">
</p>

# Product Delivery Harness

技能儲存庫，讓你用 Codex、Claude Code、Pi 或任何會探索使用者 skills 目錄的 host，把產品構想或變更需求轉化為經過驗證的交付流程。

它不是提示詞集合。這套技能把產品定義、視覺設計、工程執行與程式安全審查拆開，讓每個階段都有單一真實來源、清楚的交接邊界，以及自己的驗證方式。

> 定義產品。編譯設計。交付已驗證的軟體。

## 從這裡開始

| 你目前有什麼 | 從哪個技能開始 | 會得到什麼 |
| --- | --- | --- |
| 一個產品構想 | `product-definition-builder` | 需求、涵蓋每個 UI surface 與 state 的 responsive `wireframes/2` 審查檔、瀏覽器版面 QA、架構、技術選型、發佈目標、測試義務，以及附來源的市場研究 |
| 已核准線框稿、需要視覺設計的套件 | `product-definition-builder` UI Design Pass；gate 判定 required 時再進 `design-system-compiler` + `frontend-design` | 一份互相連通、自包含的高擬真 HTML reference，左側欄列出所有頁面，包含完整 CSS、可點擊流程和直接進入已登入 UI 的模擬登入；需要時再加具約束力的設計系統契約 |
| 既有儲存庫中的明確變更 | `delivery-harness` | 小型工作直接實作；大型工作進入受管的 PLAN/RUN 流程 |
| 已固定並完成整合的程式候選 | `code-security-review` | 唯讀、綁定精確 SHA 的安全審查，包含經驗證的 source-to-sink 發現與明確的覆蓋缺口 |
| 已交付、需要外部設定的 release | `product-activation` | 精確授權的 console 動作、已驗證的量測來源，以及逐 target 的 activation readiness |

五個內建技能都可以單獨呼叫；完整流程是選用的。不過每種模式仍會驗證明確宣告的輸入與依賴。

## 核心保證

- **小型工作維持精簡。** 一個有界變更只走檢查、實作、驗證與審查。
- **大型工作明確記錄。** PLAN v6 定義 typed graph；RUN v11 記錄授權、嘗試與佐證。
- **產品定義止於人工關卡。** UI 產品以一份 responsive 低擬真 `wireframes.html` 作結；每個 surface、target、state 與可見 PRD 動作都必須能在本機運作並通過瀏覽器版面檢查，owner 才能核准。Checker 會驗證 page、overlay、feedback flow，以及延後生成的 `mediaIntent` handoff。UI 評分只執行一個完整診斷 wave：預設一位 lead grader；只有 owner 要求或已記錄的高影響風險才可增加最多兩位檢查範圍不重疊的 specialist。Parent 先合併所有發現，再由單一 owner 完成一批修正與一次重驗；第二次仍失敗便回到 PRD 或要求 owner 核准結構性策略，不得展開無上限 round。分數描述視覺品質；明確的契約、行為、版面、state、motion 與 accessibility 義務仍是硬門檻。
- **視覺目標是可互動的 responsive HTML。** 受要求的視覺階段會產出一份連通的高擬真 HTML reference；每個可見控制項都能換頁、切換 state、開啟已記錄的 overlay 或顯示 feedback。PRD Motion Need Gate 會把每個關鍵 surface 標記為 `required`、`recommended`、`not_required` 或 `blocked`；owner 可自行選擇，也可接受 AI 建議，但會改變 scope 或需要生成服務的 motion 仍由人決定。必要的 functional UI motion 可以在 reference 內以本機方式運作，並提供等價的 reduced-motion 路徑。生成式 image 與 motion 位置保留為靜態 placeholder，附專屬 prompt 與 `generationStatus: deferred`；只有後續取得明確授權的 MCP 階段才會呼叫生成工具。Technical Hard Gate 會拒絕 runtime error、意外 request、無法到達的 state、重複事件效果與必要 motion 失效。高擬真人工關卡要求總分至少 90，`H2` 排版、`H4` responsive 與 `H8` accessibility 也都至少 90；非關鍵的 60–79 分是 advisory，不會觸發追分 round。核可的 references 保留在 `docs/design/ui-references/`，被取代的組合採歸檔而非刪除。
- **Worker 彼此隔離。** 寫入任務使用獨立 worktree 與有界範圍；parent 會驗證每個回傳的 commit 與 diff。
- **每個 graph attempt 都可持久追蹤。** 非 mission 節點先保留 attempt，在 RUN lock 外執行檢查或外部動作，再記錄 outcome 與佐證；中斷的非 runtime attempt 也透過同一條結果路徑記為 `blocked`。本機 verifier 只能在 dirty-status 檢查中忽略 tracked RUN；路徑必須解析在 checkout 內，且執行與結果記錄期間都會保護其精確位元組與檔案身分。
- **Runtime binding 明確可驗證。** `lease-worker` 從選取器 directive 衍生 provider、driver、model、effort 與 portable runtime axes；只有 app task 接受 `--task-thread-id`，既有精確目標可直接沿用，新精確目標只能從已啟用的 wildcard 授權 materialize，不會擴大權限。
- **有能力不等於有權限。** 即使執行環境能推送或清理，每個動作仍需要精確授權。
- **Activation 必須讀回驗證。** 外部設定留在 PLAN/RUN 之外，核准綁定精確 action digest，且只有獨立 read-back 與行為證據完成後才算 verified。
- **佐證跟著 SHA。** 新的 commit 會讓舊 head 的閘門與 UI 佐證失效。
- **程式安全是全新的最終審查。** 每個新的受管 PLAN 都要明確標記 required，或說明非程式交付為何 not applicable。Required review 會在 broad final validation 前，讓 `code-security-review` 涵蓋統一整合 SHA 上的每個 mission；其宣告 scope 必須包含每個 mission 的完整 write scope。它會驗證 agent 的結構化結果，並且不能沿用相同 tree 的早期佐證。Security PASS 不得有 exclusions，且至少一個 tool 或人工審查必須記為 `passed` 或 `findings`。Required node 不得跳過或被 supersede；reserve 與 completion 會重查 live Git。精確的 interruption receipt 只能在後續 current reviewer 提供 structured PASS 後作為歷史保留。
- **Promotion 一律 main-only。** RUN 仍預設在本機完成，也只能選擇性推送自己的 run branch。第一次交付與後續 enhancement 都從觀察到的 remote `main` 開始；RUN 關閉後，精確 candidate 必須通過所有本機與隔離 preview environment gate，才能另行授權 fast-forward 到 `main`。

## 包含的內容

| 技能 | 適用情境 | 主要產出 |
| --- | --- | --- |
| `product-definition-builder` | 產品探索、起草前的 research-first 評估與 Research Gate、需求、Builder UX Direction 輸入、含瀏覽器 QA 與依 PRD 執行條件式 multi-agent 評分的可互動 responsive 低擬真 wireframe、架構、技術選型、發佈目標、測試義務、負責對帳的草稿後市場研究補缺、使用可互動高擬真 HTML 且延後 media 與 motion 生成的選用 UI Design Pass，以及部署後的 outcome review | `PRD.md`、`research-assessment.md`、`wireframes.html`（UI 產品）、`architecture.md`、`stack-decisions.md`、`market-research.md`、`outcome-review.md` |
| `design-system-compiler` | 將已核准的 UI Design Handoff 編譯成凍結的設計系統契約，包含完全一致的已核准 responsive set 與版面安全規則。它必須載入獨立的 `frontend-design` 技能；依賴無法使用時會停止。 | `design-system.md`、`design-system.json` |
| `delivery-harness` | 共用的規模判定閘、PLAN/RUN、授權、本機驗證與整合，外加 runtime adapter 參考文件（`references/runtime-adapters.md`）：一份共用契約，加上每個 host（Codex、Claude Code、Pi 或 generic）各一段 provider 段落 | 直接動手，或 `PLAN.md` + `RUN.md` |
| `code-security-review` | 實作與統一整合後的唯讀安全審查，優先由 fresh sibling agent 執行；主動滲透測試與修復不屬於本技能 | 精確 SHA 決策、trust-boundary 覆蓋、驗證後的發現與修復測試 |
| `product-activation` | Web、iOS 與 browser-extension target 的交付後設定，包含 capability routing、精確外部動作授權、read-back、量測來源與 outcome-review 交接 | `docs/ACTIVATION.md` |

交付核心在啟動受管編排之前，會先做一個規模決策：

- 小型工作維持直接動手，預設不啟用 planner、scheduler、PLAN/RUN、subagent，也不做外部執行環境的預檢。
- 大型工作進入受管規劃。它可以用 `PLAN.md` 加 `RUN.md` 走受管循序交付，或處理多任務與可持久的交棒；目標專案的 `docs/tasks.md` 是按需產生的人類視圖，不是必要狀態。本原始碼儲存庫不再另外維護根目錄 `Tasks.md` 流程記錄。
- 選擇器會在實際選中的安全寫入 mission 少於兩個時派生 `managed_sequential`，達到兩個或更多時派生 `parallel_graph`。只有後者才啟用 scheduler 扇出；runtime driver 仍是獨立的傳輸事實。核心只套用 runtime adapter 參考文件裡對應偵測到的 host 的那一個 provider 段落；只有在選定路線需要時，才對外部執行環境做預檢。
- RUN 執行不等待遠端 CI；branch promotion 是獨立 closeout。精確 candidate 與適用的隔離 preview environment 驗證完成前，`main` 不得移動。

規模指的是協調範圍與影響半徑，而不是原始的檔案或行數。如果小型工作長大了，Harness 會保留已完成的部分，只針對剩下的部分重新規劃。

## 各部分如何組合在一起

```mermaid
flowchart LR
  Idea["產品構想或變更需求"] --> PRD["product-definition-builder\n產品與技術定義"]
  PRD --> Wireframe["wireframes/3 HTML\nresponsive 低擬真矩陣"]
  Wireframe --> Gate{"Wireframe Approval Gate\n人類 owner"}
  Gate -->|"核准且要求視覺設計"| Design["UI Design Pass\n需要時進 design-system-compiler"]
  Gate -->|"核准、不進視覺階段"| Harness["delivery-harness\n共用交付核心"]
  Design -->|"核可的全頁面 HTML reference 或設計系統契約"| Harness
  Harness --> Runtime["單一 host 轉接器\nCodex、Claude Code 或 Pi"]
  Runtime --> Security["code-security-review\n全新統一 exact-SHA 審查"]
  Security --> Evidence["完整最終測試與 UI 佐證"]
  Evidence --> Push["選擇性推送精確 run branch\nRUN 關閉"]
  Push --> Candidate["驗證精確 candidate SHA\n本機 + 隔離 preview gates"]
  Candidate --> Main["另行授權 fast-forward\n精確 SHA 到 main"]
  Main --> Activate["product-activation\n外部設定 + read-back"]
  Activate --> Outcome["已驗證量測來源\n後續 outcome review"]
```

你可以從任何階段開始。舉例來說，可以只用 Harness 修既有的 app。各技能各司其職：`product-definition-builder` 定義產品並止於核准的 `wireframes.html`；選用的 UI Design Pass 與 `design-system-compiler` 定義視覺契約——pass 會在 `docs/design/ui-references/<run-id>/` 留下一份核可的自包含高擬真 HTML reference，左側欄列出所有頁面，包含完整 CSS、可點擊流程與 deferred media/motion handoff；Harness 實作已凍結的結果；`code-security-review` 審查統一候選而不修改它；`product-activation` 則在不重開 delivery RUN 的情況下設定並驗證已交付 release。

### 完整技能生命週期

五個 skill 的完整生命周期，包含每個閘門與橫切機制：

```mermaid
flowchart TB
    user([使用者想法或變更請求])

    subgraph PRD["product-definition-builder — 產品定義"]
        direction TB
        interview[結構化訪談<br/>3 段 free-text + AskUserQuestion]
        pkg["核心套件起草<br/>PRD.md + architecture.md<br/>+ stack-decisions.md"]
        wf["wireframes.html<br/>單一互動式低保真檔（UI 產品）"]
        wgate{{"Wireframe Approval Gate<br/>（人工核可 = 完整停點）"}}
        ra["research-first 評估<br/>research-assessment.md（可跳過）"]
        rgate{{"Research Gate<br/>go | clarify | stop"}}
        interview --> ra --> rgate --> pkg --> wf --> wgate
        mr["market-research.md<br/>（gap pass，可跳過）"]
        ra -.-> mr
        pkg -.-> mr
    end

    subgraph DESIGN["視覺設計（可選；owner 明確要求才進場）"]
        direction TB
        taste["UI Design Pass<br/>依 Skill Bindings 槽位選 taste skill"]
        handoff[UI Design Handoff]
        dgate{{"Design System Need Gate"}}
        pair["design-system-compiler<br/>design-system.md + design-system.json"]
        taste --> handoff --> dgate
        dgate -->|required| pair
        dgate -->|not_required| target[核可的 page-faithful target]
    end

    subgraph HARNESS["delivery-harness — 交付核心"]
        direction TB
        route["System Review And Route<br/>（parent-only、read-only）"]
        size{{"Project Size Gate"}}

        subgraph DIRECT["Direct 路線（small）"]
            direct_impl["直接實作 -> 本地驗證<br/>-> code-security 審查 -> 授權 Git 動作"]
        end

        subgraph MANAGED["Managed 路線（large）"]
            direction TB
            plan["PLAN v6<br/>typed graph：missions / reviews / gates<br/>allowed_providers + 原子 task commit"]
            newrun["new_run.py 產生<br/>RUN v11 + 12 鍵授權 ledger"]

            subgraph LOOP["執行迴圈（每個 wave）"]
                direction TB
                lock["--session-id acquire-run-lock<br/>（run lock + heartbeat）"]
                obs["record-observation<br/>live-Git 快照"]
                sel["select_ready_nodes.py<br/>確定性 frontier 選擇"]
                accept["accept-wave<br/>（batch base 綁定）"]
                adapters["依共用契約解析<br/>可用的 agent driver"]
                lease["lease-worker<br/>（worktree + lease + graph 綁定）"]
                workers["fresh bounded agent workers"]
                record["record-worker-result<br/>重驗證佐證 + 原子 RUN 更新"]
                review["exact-head review<br/>（reserve -> reviewer -> record）"]
                integ["record-integration<br/>（序列整合；統一候選 SHA）"]
                lock --> obs --> sel --> accept --> adapters --> lease --> workers --> record --> review --> integ
            end

            plan --> newrun --> LOOP
            security["code-security-review<br/>fresh sibling；全部 missions；精確 SHA"]
            gates2["廣域 final validation<br/>（E2E / 回歸 / UI 證據矩陣）"]
            LOOP --> security --> gates2
        end

        route --> size
        size -->|small| DIRECT
        size -->|large| MANAGED
    end

    subgraph DEPLOY["部署（git-connected 平台）"]
        direction TB
        handoff["更新 docs/DEPLOYMENT.md<br/>（secret 名稱 + 外部 console 任務）"]
        push["授權 push<br/>run 分支"]
        preview["Preview 自動部署<br/>（平台按 push 建置）"]
        merge([使用者合併到 main])
        prod["Production 部署<br/>（平台從 main 建置）"]
        check["部署後驗證（唯讀）<br/>check_deployment.py"]
        status["核對 deployment 紀錄<br/>（狀態 + 尚待人工處理項目）"]
        handoff --> push --> preview --> merge --> prod --> check --> status
    end

    subgraph ACTIVATE["product-activation — 交付後啟用"]
        direction TB
        profiles["選擇 core + surface profiles<br/>docs/ACTIVATION.md"]
        capability["探測 connector / API / CLI<br/>Browser / Computer Use / manual"]
        actions["精確 ACT-* 動作<br/>授權 + read-back"]
        ready["逐 target activation readiness<br/>已驗證 MS-* 來源"]
        profiles --> capability --> actions --> ready
    end

    subgraph OUTCOME["Release 後 outcome review"]
        outcome["outcome-review.md<br/>（owner 主動要求，量測窗口後）"]
        verdict{{"判定：no_change | enhancement | incident"}}
        outcome --> verdict
    end

    subgraph CROSS["橫切機制（貫穿各階段）"]
        bindings["Skill Bindings<br/>（AGENTS.md 槽位表 + SHA-256 pin）"]
        ledger["授權 ledger<br/>12 個獨立動作鍵"]
        ver["版本閘 + contract digest<br/>（compatible_old 波界）"]
        watch["watchdog + reconcile<br/>（中斷恢復）"]
    end

    user --> interview
    wgate -->|繼續視覺設計| DESIGN
    wgate -->|止於此| HARNESS
    pair --> route
    target --> route
    mr --> route
    DIRECT --> handoff
    gates2 --> handoff
    status --> profiles
    ready --> outcome
    verdict -.->|下一次 enhancement 請求| interview
```

Wireframe Approval 與合併到 `main` 仍是人工閘門。Delivery 執行迴圈留在 PLAN/RUN 內；交付後 Activation 只在 RUN 關閉後開始，並使用自己精確的外部動作授權。

每個可部署版本都以 `docs/DEPLOYMENT.md` 作為操作交接文件。Product Definition 先建立骨架；Delivery Harness 在 push 前按已追蹤的環境宣告、CI 與 auth／integration 程式碼補實，部署後再以唯讀結果更新狀態。每個獨立發布單元使用一個小寫 surface 名稱：production 使用不帶 `-prod` 的標準 `<product-slug>-<surface-suffix>`，development 則在同一個名稱後加 `-dev`。常用後綴是 `web`、`api` 與 `extension`；原生 artifact，以及獨立發布的 admin、worker、job、agent、webhook、realtime 或 CLI 單元，使用各自有意義的後綴。除非 artifact 確實不同，否則 provider 與 store 名稱分開記錄。文件也會列出精確的 secret 與 variable 名稱、preview／production 放置位置，以及 auth callback URL 等外部 console 任務，但永遠不保存 secret 值。

交付之後，`product-activation` 會建立或核對 `docs/ACTIVATION.md`、選擇適用的 web、iOS 或 browser-extension profiles，使用最安全可用的 connector/API/CLI/Browser/Computer Use 路線，而且只執行精確授權的動作。Capability 與 evidence 會綁定精確 target、environment、source SHA 和 artifact/build identity，並由最新的相符結果決定 readiness。它會分開記錄 configured 與 verified、不保存 secret 值、把 hybrid 產品中不支援的 target 留在 gate 之外，並把相符且已驗證的 `MS-*` 來源交給後續 outcome review。

迴圈在兩端都閉合。任何封閉選項決策之前，research-first 評估以人工 `go | clarify | stop` Research Gate 把關起草——發布為含穩定 `RA-*` 發現的 `research-assessment.md`，並由草稿後的 market-research 對帳。Activation 與真實量測窗口結束後，owner 可以要求產出 `outcome-review.md`：對照 PRD metrics 與 `TEST-*` 預期訊號的實測值，只使用相符且已驗證的來源，附帶餵進下一次 enhancement run 的 `no_change | enhancement | incident` 判定。

交付後的小改不必為了維護產品契約而另開 PLAN/RUN。當 `docs/product/PRD.md` 存在時，種子化的 `AGENTS.md` 會要求每次直接修改都在同一份變更中更新受影響的 PRD 需求與追蹤 ID，並先把 UI 影響分類為 `none`、`structure`、`style` 或 `both`。新增頁面或 route 至少屬於 `structure`，因此要更新並重新核准受影響的 UI Surface Contract 與 `wireframes.html` 頁面。樣式變更要重新確認已核准的 UI 方向，只有經核准且需要正式 design-system delta 時才修改 design-system pair；未受影響的 ID、頁面與決策維持不變。

Gitignore 衛生同時適用於 direct 與 managed 工作。scope scan 會記錄任務是否改變 local-only artifact 類型，再依實際工具鏈產生最窄的規則。含值的環境與 credential 檔、可重建的 build output、dependency 目錄、cache、log 與本機平台狀態要忽略；source、tests、lockfiles、migrations、受追蹤的設定範例與 schema，以及權威產品或交付產物必須保持可見。程式新增環境變數讀取時，同一個 task 要更新受追蹤的 example 與 ignore 規則。Harness 會以 `git check-ignore`、`git status --ignored` 和 `git ls-files` 驗證代表路徑；它不讀 secret 值、不以規則隱藏 dirty worktree，若可能的 secret 已被 Git 追蹤，就停止並交由 owner 處理。

商業產品現在會經過兩個分開的 Product Definition 決策。Monetization Infrastructure Gate 先解析商業模式、定價／offer 規則、購買 surface、entitlement source 與 merchant-of-record／稅務責任，再比較 native store billing、RevenueCat、Qonversion、Adapty、Superwall、Stripe Billing、Paddle 或 Lemon Squeezy 等現行選項；有定價不代表預設 RevenueCat。Partner Channel Gate 則獨立解析 `none`、affiliate、referral、reseller 或 hybrid，再比較 Rewardful、FirstPromoter 這類 link／commission 工具、PartnerStack 這類完整 partner platform、Lemon Squeezy 的整合 affiliate 路線，或自建 reseller service。Billing、entitlement、paywall、稅務、attribution、commission／payout 與 reseller operations 會保持為分開的 PRD、architecture、stack、UI、mission 與 test 契約。

## 交付模型

Harness 是圍繞明確的邊界所打造的：

1. 檢視目前的專案，找出需要做的工作。
2. 凍結相關的契約、來源、範圍與驗證步驟。
3. 當任務大到需要時，先規劃相依關係，再開始實作。
4. 只有在至少兩個安全寫入 mission 實際被選中、工作彼此獨立且隔離，並且每個動作都經過明確授權時，才使用平行 worker；受管循序路線仍要證明隔離 writer、scope/head 與 review gates。
5. 驗證任務結果與整合，執行全新的統一 code-security 審查，再驗證相關 UI 流程與最終 diff。單一 mission 不會憑空增加跨 mission batch gate。
6. RUN 預設以驗證過的本機佐證結束；run-branch push 需要精確授權。RUN 關閉後，完成 exact candidate 與適用的隔離 preview environment 驗證，再另行授權把該 SHA fast-forward 到 `main`，並 read-back 與驗證 production。

對於有計畫支撐的工作，它會記錄任務範圍、相依關係、worker 歸屬、驗證指令，以及各動作專屬的授權。測試通過並不代表授權推送、移除 worktree 或刪除分支。RUN-v11 的推送還需要明確的遠端意圖、唯一的整合分支目標與目前 head 授權；若預設分支身分未知，推送會安全失敗，但不會阻止無關的本機執行。

wave 接受前，Harness 會重新檢查觀測到的非預設整合分支及乾淨產品樹，把 batch 綁到該精確 head，重跑 selector，並且只接受完整的目前 frontier。clean-tree gate 只排除 transition 必然更新的那個精確 tracked RUN 檔案；其他任何變更仍會阻斷。整合分支位於 linked worktree 時，該 checkout 會正確記錄為 parent，Git 的乾淨主要 checkout 則保留為已識別的同層項目。持久 run lock 負責 dispatch；短期作業系統鎖會序列化每一次 RUN 的讀取、驗證與寫入交易。凍結的 PRD、wireframe 與 design-system source 會在獨立驗證和 transition 寫入路徑中按位元組 hash 綁定；即使 PLAN 聲稱 UI surface 為空，凍結的 PRD 仍會被解析。每個結構化 PRD surface 只擁有一個 literal route；帶 UI 的翻譯 PRD 只能有一對語言無關的邊界標記，並且每個條目各有一個 `route` 與 `states` 錨點；各產物的 ID、route 與 state 必須完全一致。design-system 的 Markdown 與 JSON 各有獨立 source row，其 generated contract 與 compiler namespace 必須一致；每個 PLAN `DS-*` trace 也必須在同一個全域唯一的 JSON 註冊表中解析。product-definition-builder 會按問題工具實際的每次容量分批詢問所有適用的封閉決策；沒有 Codex 專屬的呼叫次數目標，也不會為了配合 host 次數而丟掉問題。

```mermaid
flowchart TB
  Intake["Intake: request, repo, instructions"] --> Size{"small or large?"}
  Size -->|small| Direct["Direct parent work<br/>no PLAN/RUN, no scheduler"]
  Size -->|large| Plan["PLAN v6 + RUN v11<br/>frozen contracts, authorization ledger"]
  Plan --> Observe["Record observed git + batch_base_sha<br/>(the selector returns an empty frontier without it)"]
  Observe --> Frontier["Ready frontier<br/>dependencies, scope/resource conflicts, permission gates<br/>bounded by observed slots x isolation x conflicts"]
  Frontier --> Host["One host provider section: codex, claude_code, pi, or generic<br/>no cross-host fallback"]
  Host --> Work["Isolated mission worktree<br/>attempt + lease, worker tests + commits"]
  Work --> Review["Exact-head read-only review<br/>required before integration"]
  Review -->|pass| Integrate["Serial integration into the resolved branch"]
  Review -->|fix_required| Work
  Integrate --> Security["全新統一 code-security 審查<br/>全部 missions；精確 integration SHA"]
  Security -->|pass| Gates["適用的 integration、E2E 與 UI evidence gates"]
  Security -->|fix_required| Repair["Bounded repair route"]
  Gates -->|fix_required| Repair
  Repair --> Rereview["Re-review on the new head"]
  Rereview --> Security
  Gates -->|pass| Local["Local verification complete"]
  Direct --> Local
  Local --> Remote{"explicit remote outcome and exact push grant?"}
  Remote -->|no| Done["Stop with verified local evidence"]
  Remote -->|yes| Push["Push the run's own branch<br/>RUN ends here"]
  Push --> Candidate["驗證精確 candidate<br/>本機 + 隔離 preview gates"]
  Candidate --> Main["另行取得 exact-SHA 授權<br/>fast-forward 到 main"]
  Main --> Prod["Production read-back<br/>and smoke"]
```


## 輕量的執行環境轉接器

共用核心掌管唯一的 PLAN/RUN 控制平面。執行環境專屬的啟動細節放在同一份參考文件 —— `delivery-harness/references/runtime-adapters.md` —— 內含一份共用轉接契約，加上每個 host 一段 provider 段落，按需套用：

- 每個 host 只套用自己的 provider 段落，也只執行 `allowed_providers` 包含該 host 的 PLAN 節點。
- Pi host 沿用 Pi 已安裝的角色、模型與 fallback 設定。
- 任何 provider 段落都無法呼叫另一個執行環境。若某個已就緒節點的 provider 與當前 host 不符，會被 deferred with `runtime_unavailable`，留給由對應 host 主持的執行去處理。
- 未來新增一個執行環境 host，只是在這份參考文件加一段 provider 段落，不需要新增 skill。

共用的 script、schema、參考文件與範本仍放在 `delivery-harness` 底下；各 provider 段落只是連結到它們，而不會各自夾帶重複的執行環境。這讓預設提示詞維持精簡。

一次執行只有一個 active host。same-repository handoff 只有在 Host A 關閉 wave、且 `RUN.active_wave.status` 既不是 `active` 也不是 `proposed` 後才允許；`active_wave` 物件仍保留在 RUN 中，不能把物件缺失當成交接訊號：Host B 保留 PLAN/RUN 與 graph state，重新探測 runtime，並在選取下一波前審查目前的 exact SHA。若需要修復，路由回 Host A 且舊 review 立即失效；除非未來 schema 增加可攜式的儲存庫／狀態身分，否則不支援 cross-machine handoff。

## 圖引擎與 Dynamic Workflow

這些技能使用兩層圖：

- **org 圖**是穩定的角色契約：產品、架構、UX、設計系統、mission-worker、surface reviewer、security reviewer、審批、整合，以及生命週期職責。
- **work 圖**是單次執行的暫時性任務圖。PRD 與設計工作流只有在 host 能夠強制套用 `builder_readonly` 工具設定檔時，才會使用有界的分析圖；否則會退回循序的 parent。工程流則使用標準的 PLAN v6 圖與 RUN v11 狀態。

訪談與審批留在執行中的工作流之外，因為 Claude Code Dynamic Workflow 無法在執行途中向使用者索取輸入。Parent 會先凍結輸入，執行一個有界的工作流，接著掌管分階段寫入、衝突解決、審批與發佈。

在工程流中，Harness 會先驗證並選出相依已就緒的 frontier，才建立或請求 worktree。原生的 Claude mission 使用位於 `.claude/worktrees/` 底下、由 parent 管理的 worktree，把每個 worker 綁到精確的批次 base，並要求在存取儲存庫前先 `EnterWorktree`。在每一條路線上，parent 都會驗證回傳的 commit 與實際的 Git diff、序列化地整合被接受的 commit，並重新計算圖的 frontier。

非 runtime graph 節點採用 reserve／execute／record 順序：`reserve-node-attempt` 在 RUN lock 內建立 receipt，approval、external wait、deterministic verifier 或 lifecycle side effect 在 lock 外執行，`record-node-result` 只關閉相符的 attempt，並以宣告的 outcome 推導 graph phase。Lifecycle transition 只記錄佐證，不執行動作。`lease-worker` 把選取器衍生的 runtime binding 與精確 task／thread 身分帶入 RUN，並遵守 compatibility 檢查與既有 wildcard 授權。

Claude Graph Workflow 會把 mixed frontier 按 homogeneous `tool_profile` 分成多個呼叫；同一組內可以使用不同模型與推理強度，但一次呼叫絕不混合寫入 mission 與唯讀 review。tool profile 是標籤與 prompt/result 契約，不是 permission-level tool removal。

- `mission_write` 要求 `EnterWorktree` 與 mission 的有界寫入契約。
- `code_review_readonly` 要求 frontend、backend、integration 或 security 的精確路徑審查與唯讀結果佐證；它不會移除繼承的工具。
- `visual_review_readonly` 使用 host 繼承的工具審查保留下來的截圖或其他既有佐證；新增瀏覽器存取必須先審核並加入設定檔契約，才能使用。

當 Claude Code 回傳真實的 Workflow 執行 ID 時，RUN 狀態可以保留 workflow/task ID、script digest、node group、圖/base 綁定、工具設定檔、狀態，以及可取得的度量。同一 session 內的續跑可以沿用該綁定；跨 session 的復原則從標準的 PLAN/RUN 狀態重新啟動一次新的 workflow 嘗試。

圖節點的 `allowed_providers` 必須包含實際在執行 Harness 的 host，該節點才能被選取。Codex、Claude Code 與 Pi 不能彼此委派節點；它們之間沒有跨 host 的橋接。若某個已就緒節點的 provider 與當前 host 不符，會被 deferred with `runtime_unavailable`，留給由對應轉接器主持的執行去處理。

## 安裝

這是公開儲存庫，不需要存取權。你只需要至少有一個會探索 `~/.agents/skills/` 這類使用者 skills 目錄的 host——Codex、Claude Code、Pi 或其他都可以。

```bash
git ls-remote https://github.com/Phlegonlabs/product-delivery-harness.git HEAD
```

### 最快安裝方式

clone 儲存庫並執行安裝腳本。它會把現有副本移到 `~/.agents/skill-backups/product-delivery-harness/` 下同一個帶時間戳的備份，把五個 Product Delivery Harness skills 複製進 `~/.agents/skills/`，並驗證每個複製出來的 `SKILL.md`：

```bash
git clone https://github.com/Phlegonlabs/product-delivery-harness.git
cd product-delivery-harness
./install.sh             # macOS / Linux / Git Bash
# Windows PowerShell：powershell -ExecutionPolicy Bypass -File install.ps1
```

手動等效做法：

```bash
cp -r product-delivery-harness/skills/delivery-harness \
      product-delivery-harness/skills/product-definition-builder \
      product-delivery-harness/skills/design-system-compiler \
      product-delivery-harness/skills/code-security-review \
      product-delivery-harness/skills/product-activation \
      ~/.agents/skills/
```

如果 checkout 的 `skills/` 下有本機 `__pycache__` 目錄，複製時排除或刪掉——host 不需要位元碼。Windows 上改用 `Copy-Item -Recurse` 即可。安裝腳本同時就是更新腳本：重跑一次會先備份舊副本再替換。更新前必須取得明確的安裝／更新授權，並結束所有正在使用這些 skills 的 session。複製五個目前目錄，驗證檔案與 checkout 相同，然後開啟新的 host session。驗證失敗時還原備份；不要直接覆寫或刪除舊副本。

從 0.23 或更早版本升級時，先在同一份備份中用原 ID 保存各舊目錄。然後安裝對應的新版本——`full-harness` → `delivery-harness`、`prd-builder` → `product-definition-builder`、`product-design-builder` → `design-system-compiler`——以及新的 `product-activation` skill。複製完成後，驗證 `~/.agents/skills/` 中已沒有三個舊 ID；否則 host 會探索到重複且觸發範圍重疊的 skills。

五個內建技能都可以獨立呼叫，但跨技能模式會驗證各自的依賴。凍結 wireframe 驗證會使用 `delivery-harness` 旁的 `product-definition-builder` checker；`design-system-compiler` 需要已核准的 PRD UI Design Handoff、已核准的 `wireframes.html` 與 `frontend-design`；選用的 UI Design Pass 需要 design-direction skill 與 frontend-implementation skill；新的受管程式交付會在整合後透過 `code_security_verification` 槽位使用 `code-security-review`；`product-activation` 在 Delivery 後使用 release 與 deployment 交接。只需安裝所選模式要求的依賴。

### Zero-to-one 流程（從零開始）

1. 安裝一個受支援的 host（Codex、Claude Code、Pi 或任何會探索 `~/.agents/skills/` 的 host）與五個 Product Delivery Harness skills，並用該 host 執行這次交付。
2. 開啟新的 host session，確認技能可見，然後呼叫 `delivery-harness`。
3. 讓規模閘決定直接工作或 PLAN/RUN；小型工作不要預先建立 worker。
4. 大型執行一次只保留一個 active host，並在 same-repository handoff 前關閉與審查每個 wave。

## 常見提示詞

Codex 接受下列的 `$skill-name` 寫法。在 Claude Code 或其他 host 中，直接用名稱指定技能，例如 `product-definition-builder`。在 Pi 中，可以使用自動找到的 project skill，或用 `--skill` 傳入技能目錄，再直接指定 `delivery-harness`。

```text
Use $product-definition-builder to turn this idea into a PRD, responsive low-fidelity wireframes for every page, target, and state, browser layout QA, architecture, stack decisions, release targets, and test obligations.
```

```text
Use $product-definition-builder to review every page-target-state in the staged wireframes.html, confirm no unintended overlap or overflow in a real browser, and record the Wireframe Approval decision before visual or implementation work.
```

```text
The wireframes are approved; continue into visual design with $product-definition-builder's UI Design Pass. Render every page and approved state in one self-contained high-fidelity HTML with complete CSS, a left sidebar listing all pages, clickable flows, and mock login that jumps directly to the authenticated UI. Browser-check the full responsive/state matrix and retain the approved file under docs/design/ui-references/, invoking $design-system-compiler only when the Design System Need Gate is required.
```

```text
Use $delivery-harness to implement the approved plan, building each page from its approved HTML reference in docs/design/ui-references/ within the recorded tolerance.
```

```text
Use $delivery-harness to review the existing app, plan the required work, and stop before implementation.
```

```text
Use $delivery-harness to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
Use $delivery-harness to implement this plan and push the verified branch. I will open the PR and handle the merge myself.
```

```text
The delivery is complete. Use $product-activation for the production release targets, configure only the exact external actions I approve, verify each result by read-back, and stop after recording activation readiness and the measurement-window handoff.
```

```text
Use delivery-harness on this Pi host to execute this plan. Preserve Pi's installed frontend_designer, worker, reviewer, model, and fallback settings.
```

多任務交付仍要說清楚本機與遠端結果；建立分支、commit、整合、每次 push、deployment、移除 worktree 與刪除分支都是獨立動作。Post-RUN promotion 只有在 exact action-time authorization、fast-forward 證明、read-back 與完整 candidate 測試齊全時才能更新 `main`。

## Codex、Claude Code 與 Pi 的執行

Harness 記錄的是實際的執行環境能力，而不是從已安裝的 CLI 去假設一個。

| 執行環境 | 偏好的平行路線 | 退回方案 |
| --- | --- | --- |
| Codex app | 在隔離、由 app 管理的 worktree 中執行 app 任務 | 直接使用 subagent，再退到單一循序的 parent |
| Claude Code | 使用對齊 base、由 parent 管理的 `.claude/worktrees/` worktree 執行 Dynamic Workflow | 直接使用 subagent，再退到單一循序的 parent |
| Pi | 在 parent 管理的 worktree 中使用已安裝的 Pi 角色，並由 Pi 選擇模型與 fallback | 單一循序的 parent |
| 其他任何 host | 由 parent 隔離的 fresh subagent | 單一循序的 parent |

在 Codex 中，每個選中的 mission 都會在左側欄開一個獨立的 top-level conversation，並綁定自己的 app-managed worktree。任何唯讀 explorer 或 reviewer 都由 Harness parent 另行作為同層節點派發；mission 任務不能建立子代理。Coordinator 直接建立的 subagent 不能取代這些 top-level 任務。若 project/thread 工具一開始尚未載入，轉接器會先從目前的 Codex 工具介面找出它們，再考慮退回方案。當使用者明確要求這個結構時，缺少 thread 能力是 blocker，不能把工作縮回同一個 conversation。

目標 repo 的 branch 規則優先；否則第一次交付與 enhancement 都從觀察到的 remote `main` 建立 run branch。Mission worktree 只整合進 run branch 並接受 exact-head review。RUN 關閉後，candidate 通過所有必要的本機與隔離 preview environment gate，再以獨立授權把未變更的同一 SHA fast-forward 到 `main`。任何修正都要在新 SHA 上重跑 candidate 驗證。

每個 provider 段落只執行那些允許 provider 包含自身 host 的 PLAN 節點；沒有跨 host 的路線。若某個節點需要其他 host 的 provider，會被 deferred with `runtime_unavailable`，而不會在這裡執行。

平行實作預設沒有固定的小上限；設定中的寫入 worker 上限刻意設得很高，實際波次由觀察到的 worker 名額、隔離容量，以及相依已就緒、無衝突的 frontier 大小界定。一個可獨立驗證的目標對應一個 mission。每個 writer 都有明確的檔案 ownership，以及獨立、乾淨、固定基線的 worktree。共享 API、schema 與型別必須先凍結，再開始依賴它們的平行寫入。探索、寫入與 reviewer 都由 parent 作為同層節點派發；worker 與 reviewer 都不能再次分派。每個 mission 通過 exact-head review 後，由 parent 串行整合；統一整合完成後啟動 fresh reviewers，由 sibling agent 執行必要的 `code-security-review`，最後只對固定候選 SHA 執行一次完整驗證。Worker 絕不編輯 parent 的 `PLAN.md` 或 `RUN.md`，也不推送、開 PR、合併、部署或移除 worktree。Parent 掌管整合以及每一個落地或生命週期動作。

## 儲存庫結構

```text
.agents/skills/                                      標準技能來源
assets/                                              README 封面
.github/workflows/harness-ci.yml                     契約、單元與 E2E 檢查
```

## 維護技能

只編輯 `.agents/skills/` 中的標準來源，接著跑核心驗證套件：

```bash
python -m pip install -r .agents/skills/delivery-harness/requirements-test.txt
python .agents/skills/delivery-harness/scripts/check_skill_spec.py
python -m pyflakes .agents/skills/delivery-harness/scripts .agents/skills/product-definition-builder/scripts .agents/skills/design-system-compiler/scripts .agents/skills/product-activation/scripts
python -m unittest discover -s .agents/skills/delivery-harness/scripts/tests -v
python -m unittest discover -s .agents/skills/product-definition-builder/scripts/tests -v
python -m unittest discover -s .agents/skills/design-system-compiler/scripts/tests -v
python -m unittest discover -s .agents/skills/product-activation/scripts/tests -v
git diff --check
```

CI 也會執行端到端主幹檢查。本機可用 `HARNESS_GOLDEN_PATH=1 python -m unittest discover -s .agents/skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v` 執行；它會用一個合成產品套件走真實 CLI 主幹（`new_run.py` → 含 sibling skill 完整 wireframe checker 的凍結 join → `validate_result.py --repo-root`），讓跨 skill 契約漂移一次爆紅。

## 維持 README 與時俱進

README 是紀錄文件：每個新增或改動 skill、規則、表格、圖或文件化流程的變更，都要在同一份變更裏更新 README 的對應描述段落，四種語言一起改。版本 badge 與版本紀錄條目屬於發佈時的工作，照下面《發佈》的規則走。

## 發佈

每個落在 `main` 的流程就是一次 release，版本號提升要在同一份變更裏完成——預設升 patch，skill bundle 有破壞性變更升 minor。以下幾個地方要一起更新：

1. `package.json` 的 `version` 欄位與 `.agents/skills/delivery-harness/VERSION` 中會隨技能目錄複製的版本。
2. 四份 README（`README.md`、`README.zh-TW.md`、`README.zh-CN.md`、`README.es.md`）的版本 badge 與版本紀錄條目。
3. `.agents/skills/delivery-harness/assets/templates/MISSION_RUNBOOK.template.md` 的 RUNBOOK `required_harness_version` 預設值。
4. `.agents/skills/delivery-harness/scripts/tests/test_skill_contract.py` 裏釘住的版本斷言。

接著跑完上面的完整驗證、檢視整份 diff，並依 `branch-promotion-contract.md` 落地。Repository protection 要求時使用 PR；若 provider 產生新的 main SHA，必須先證明其 tree 與 verified candidate 相同，並立即在該 exact main SHA 上重跑完整 suite 與 security review，才能 tag 或宣告 release 完成。落地之後，在 `main` 的 release commit 上打上對應的 `v<版本>` tag（例如 `v0.30.0`）；tag 是 release 的一部分，不是可有可無的附加動作。每個釋出的版本都要有它的 tag——`git tag` 和 `package.json` 必須說同一個故事。

## 安全性與資料安全

- 別把 GitHub token 及其他憑證放進這個儲存庫。
- 在確認新的技能副本能正確載入之前，別刪掉舊的安裝副本。
- 編排技能對於每一個會改變狀態的 GitHub 或生命週期動作，都要求明確授權。
- `code-security-review` 預設唯讀；沒有另外的明確授權時，它不會安裝 scanner、啟用網路、修復程式或探測 live target。

## 授權

本儲存庫採用 MIT 授權，全文見 [LICENSE](LICENSE)。

## 版本紀錄

每次發佈都要更新這一節，連同上面《發佈》一節描述的版本號提升與 tag 一起完成。

- **0.32.0** — 把 Product Definition UI 評分限制為一個完整診斷 wave、一份 root-cause ledger、一批修正與一次重驗。預設只用一位 lead grader；最多兩位不重疊的 specialist 必須由 owner 要求或有高影響風險。數字分數只描述視覺品質；PRD 與 Technical Hard Gate 問題仍以二元結果處理，高擬真設計總分以及 `H2`、`H4`、`H8` 都要達到 90，非關鍵的 60–79 分是 advisory，已通過的 candidate 不會為追求 100 分而重做。PRD 新增 Motion Need Gate；高擬真 HTML 可以展示必要的本機 UI motion 與 reduced-motion 路徑，生成式 motion 則維持 deferred，直到另行授權。

- **0.31.0** — 統一 Product Definition 與 Deployment 的發布單元命名。Production 使用不帶 `-prod` 的標準 `<product-slug>-<surface-suffix>` 名稱，development 再加 `-dev`，不同 surface 不得重用同一個 release name。常用後綴為 `web`、`api` 與 `extension`；原生 artifact 與獨立發布單元使用明確的 surface 後綴，並把 provider/store 身分分開記錄。Product Definition workflow 現在要求並驗證 `surface_suffix`／`release_name` 配對，`docs/DEPLOYMENT.md` 會記錄每個發布單元，其 checker 也執行同一命名契約。這是 workflow 輸入與 deployment record 的 breaking change。

- **0.30.0** — 以永久 main-only 流程取代持久 `development` branch。第一次交付與後續 enhancement 都從觀察到的 remote `main` 開始；非預設 candidate branch 承載實作、exact-SHA review、完整測試與適用的隔離 preview environment 驗證，之後才另行授權 fast-forward 到 `main`。退役的 `development` 名稱仍會被拒絕作為 RUN target，且只有通過 ancestry 與 dependency 檢查後才能刪除。本版也加入可互動 `wireframes/3`、PRD-bound 0–100 multi-agent UI 評分、80 分 refinement loop、element-level responsive/layout 檢查、accessibility、設計一致性、創意表現、deferred MCP media/motion handoff，以及 `wireframes/2` 向後讀取相容。

- **0.29.1** — 新增 `README.es.md` 作為第四種 README 語言。語言切換列、《維持 README 與時俱進》規則、《發佈》清單、repo 的 AGENTS.md，以及 pine 住的 README 合約測試，都在同一份變更裏涵蓋四種語言。沒有 skill 行為變更。

- **0.29.0** — 新增 development-first promotion 與持續維護的產品治理閘門。第一次交付從 `main` 開始，後續 enhancement 從持久的 `development` 開始；RUN 仍只能推自己的 branch。RUN 關閉後，exact candidate 要另行 promotion 到 `development`、read-back 並完成內部測試，才能進 production。RUN guards 會拒絕把 `development` 或 `main` 當成 integration／push target，包含大小寫變體。若 repository rule 強制 PR 並產生不同 merge SHA，必須驗證其 tree 與 checks，並如實回報 protected refs。Product Definition 現在會在直接 follow-up 中更新既有 PRD 與受影響 wireframe，記錄 monetization 與 partner-channel gates，比較 RevenueCat 與現行替代方案而不預設選用，並分開 affiliate、referral、reseller operations。Gitignore 管理依實際 toolchain 決定、保留 example，且發現可能的 secret 已被追蹤時停止。

- **0.28.0** — 新增 `code-security-review` 作為第五個內建 skill。每個新的受管 PLAN 都把 security 記為 `required`，或用非程式原因標記 `not_applicable`。Required review 會在序列整合後、broad final validation 前派發 fresh sibling；`security` 必須涵蓋每個 mission、包含每個 mission 的完整 write scope，且不得跳過或被 supersede。`record-review-attempt --security-result` 會驗證另一個 agent 的結構化 decision、精確 SHA 與 base、scope、trust boundaries、tools、coverage、findings，以及 PASS 的空 exclusions。Security reserve 與 completion 會重查 live Git。中斷 reviewer 以精確 receipt reconciliation；後續 current PASS 成立後可保留為歷史，但 receipt 本身不能滿足 gate。PASS 至少需要一個 tool 或人工審查記為 `passed` 或 `findings`，malformed reviewer identity 會回傳 validation errors，不會 crash。本機 verifier 會用位元組與檔案身分快照保護 tracked RUN 的 dirty exception，並在記錄結果時重新核對 hash。Design-system 原子寫入會拒絕 symlink 目標。本版也包含受守衛的非 runtime node transitions、精確 runtime bindings、可識別 CSS escapes 的 self-contained artifact checks，以及五 skill 安裝與 contract digest。
- **0.27.0** — 新增 `product-activation` 作為第四個內建 skill。它在 Delivery 後啟動，把精確的交付後動作與已驗證量測來源記入 `docs/ACTIVATION.md`，透過 connector/API/CLI/Browser/Computer Use/manual handoff 路由工作，並把授權與 evidence 綁定到精確 target、environment、action digest、source SHA 與 artifact identity。Product Definition 只在缺少時建立 Activation seed；Delivery 會先關閉再交接；後續 outcome review 只使用相符且已驗證的 `MS-*` 來源。本版也把 browser extension 納入一級 release-target surface，並同步四 skill 安裝、contract digest、CI 與 cross-skill tests。
- **0.26.0** — Responsive UI 契約現在從產品定義到交付全程阻擋不完整結果。每個 `UI-*` 條目宣告同一組至少兩個 web viewport 或原生／桌面 size class；`wireframes/2` 會為每個目標明確投影區域順序、可見性、網格跨度、重排、互動規則與不可捨棄區域。線框稿與高擬真 HTML 的核准要求真實瀏覽器中的 page-target-state 完整矩陣，不得出現非預期重疊、裁切、遮擋或水平溢出；刻意疊層必須記錄層級、焦點、安全區域與關閉行為。設計系統契約與 PLAN 使用同一 responsive set，Harness 會拒絕缺失、重複、單一目標、未排序、額外或漂移的覆蓋，同時維持舊 schema 可讀。
- **0.25.7** — 移除原始碼儲存庫根目錄的 `Tasks.md` 流程記錄及其本機記錄規則。受管目標專案仍會按需渲染非權威的 `docs/tasks.md` 檢視；目標專案的 skill 行為不變。
- **0.25.6** — 在 state-model 參考加上腳本轉換的旗標面文件（`pause`/`resume`/`cancel`、review-attempt、wave、lease 與驗證旗標），為 wireframe HTML 與 PRD 契約 checker 新增直接測試，安裝說明加上了排除位元碼的提示。skill 行為不變。
- **0.25.5** — `Tasks.md` 流程記錄改為累積在本機，搭下一個實際變更的分支與 PR 一起落地，不再為記錄單獨開 release。
- **0.25.4** — 加入儲存庫流程記錄檔 `Tasks.md`：每個最小步驟一行、逐項勾選。skill 行為不變。
- **0.25.3** — 儲存庫改採 MIT 授權：新增 LICENSE 檔、三語 README 加上授權段落，並在 package.json 設定 `license` 欄位。skill 行為不變。
- **0.25.2** — 儲存庫由 `fullstack-goal-dev` 更名為 `product-delivery-harness`，與產品名一致。README badge、clone 指令與安裝路徑全部改用新名，安裝說明也改為描述公開儲存庫；skill 行為不變。
- **0.25.1** — 修正受管 run 與佐證寫入。`new_run.py` 現在把 graph revision 綁到實際 PLAN revision，從會隨技能目錄複製的 `VERSION` 讀取 release identity，並在寫檔前驗證產生的 RUN。`record-worker-result` 會直接觀察綁定 worktree 的 live branch、head、dirty state、diff 與 ancestry，再原子記錄接受或被 validator 拒絕的佐證；`reject-worker-result` 可記錄 parent 拒絕的目前 candidate，不必手改 RUN。寫入前還會重查 worker HEAD 與 PLAN。Attempt 與 lease identity 遇到模糊重用時會 fail closed。真實跨 skill golden path 現在是必要 CI step，安裝說明也已區分可獨立呼叫的階段與明確依賴。

- **0.25.0** — Research-first 把關、outcome review、單一 wireframe checker。`delivery-harness` 的凍結 wireframe join 現在直接對凍結 bytes 執行 `product-definition-builder` 的完整 `check_wireframe_html.py`（reviewer shell、自包含、填寫完成、approved 狀態、PRD 對 wireframe 的 join），取代原本的縮減重實作；`validate_harness_plan.py --wireframes` 走同一個 checker，sibling skill 缺失時回明確錯誤。`validate_result.py` 新增 `--repo-root`，在單次 manifest walk 內重跑 凍結 source 的 byte 與語意 join。`product-definition-builder` 新增起草前的 research-first 評估（workflow 步驟 4，早於任何封閉選項決策）：人工 `go | clarify | stop` Research Gate 記錄在 `PRD.md`，發布含穩定 `RA-*` ID 的 `research-assessment.md`，草稿後的 market-research 改為對帳而非冷啟研究；並新增部署後的 `outcome-review.md`——部署 SHA、每個 metric 的 baseline/target/actual、`no_change | enhancement | incident` 判定——下一次 enhancement run 會完整讀取。可部署套件同時播種只含名稱的 `docs/DEPLOYMENT.md` 操作交接（Required Secrets and Variables 與 External Console Setup），由 `delivery-harness` 在首次可部署 push 前與部署後透過 `check_deployment.py` 對帳。另新增 opt-in 的 golden-path E2E（`HARNESS_GOLDEN_PATH=1`，不在 CI 內），以一個合成套件走真實 CLI 主幹，讓跨 skill 漂移一次爆紅。

- **0.24.0** — 完整技能套件改名為 Product Delivery Harness。`prd-builder` 改為 `product-definition-builder`，`product-design-builder` 改為 `design-system-compiler`，`full-harness` 改為 `delivery-harness`。正式目錄、skill frontmatter、UI metadata、範本、CI、測試、安裝指令、封面與三語 README 都已使用新名稱。既有安裝現在有可復原的遷移流程：先結束活動中的 session，把舊 ID 與既有目標目錄備份到探索目錄之外，再複製並按位元組驗證三個目前 skills，確認舊 ID 不再被探索；失敗時還原備份。package id 改為 `product-delivery-harness`；現有 GitHub 儲存庫 slug 暫時保留，等另行改名後再更新連結。

- **0.23.0** — 寫入路徑與跨產物驗證加固。`close-wave` 會記錄持久 wave tombstone；在 `run_complete` 授權邊界下，已驗證的 `worker_passed` mission 可以進入收尾，而 `wave_closed` 授權仍要求先解決 mission。`accept-wave` 現在只在 control 為 `running` 時執行，要求 live Git 位於觀測到的乾淨、非預設整合分支及 `observed.git.parent_head_sha`，重跑 selector，並且只接受完整的目前 dispatchable mission frontier；`lease-worker` 拒絕重疊的 write scope 與 serialized 或 exclusive resource，只有明確的可重試失敗或 interrupted-worker reconciliation 能重新啟用被阻塞的 mission。`record-integration` 會證明觀測到的整合 checkout 與分支、乾淨產品樹、batch base 和上一個 integration head 的祖先關係，以及 worker head 包含關係，不能切到遺失先前整合結果的分叉。clean-tree gate 只排除 transition 必然更新的那個精確 tracked RUN 檔案；linked integration checkout 會把自己記錄為 parent，同時保留 Git 的乾淨主要 checkout 為已識別的同層項目。所有 mutation 都拒絕外來 lock，不受 stale 或 heartbeat 能否解析影響；五個 dispatch 指令要求持有持久 lock，作業系統鎖加精確文字比較會序列化完整的 RUN 讀取、驗證與寫入交易。prd-builder 現在使用穩定的封閉決策清單，按問題工具實際的每次容量詢問所有適用決策，不再設定 Codex 專屬的總呼叫次數目標。design-system 註冊表接受 primitive 的選填 `dsId`，並對每個精確的 `DS-[A-Z]+-\d+` token 強制一個全域命名空間；PLAN 中的所有 DS trace 都必須解析，凍結 Markdown 的 generated block、已填寫值與精確 compiler namespace 也必須和 JSON 一致。凍結的 PRD、wireframe，以及分別記錄的 design-system Markdown/JSON source，都必須在獨立驗證與 transition 驗證中符合位元組 hash；凍結的 PRD 即使在 PLAN 聲稱沒有 UI 時仍會被解析，每份 UI contract 只能有一對邊界標記且每個條目各有一個 `route`/`states` 錨點，PRD、PLAN 與 wireframe 的 ID、route、state 必須完全一致。CI 與三語文件已釘住同一套行為。

- **0.22.0** — 私有市集與外掛套件正式退休。`plugins/`、`.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json` 與 `scripts/sync_plugin_skills.py` 全數移除；`.agents/skills/` 是唯一來源，安裝與更新就是把三個 harness skills 複製進使用者 skills 目錄（`~/.agents/skills/`），跟「最快安裝方式」描述的完全一致。README 移除市集 badge、各 host 的外掛安裝指令與本機市集章節；`runtime-upgrades.md` 改為把技能同步定位成唯一的 Harness 更新面，各 host 的更新說明縮減為 host 自屬安裝器與重啟。同一版同時擴充了 run 紀錄與部署契約：mid-run 的修改——額外修復、後續編輯、使用者回報的改動——一律透過 plan revision 記錄成自己的 mission（`execution-state-model.md` 的 Mid-Run Modification Recording），`docs/tasks.md` 改為最新 mission 在上、M1 在下，run 結束時這份檢視列出 run 做過的每一項修改。部署面新增跨平台的「Adding A Binding」runbook（seed 進 `docs/DEPLOYMENT.md`）：兩側都是先開資源再寫宣告、preview 驗證先於 default branch 落地、secrets 永不進 wrangler 設定檔、D1 migration 先套 preview 庫——wrangler 步驟限 cloudflare，具名環境統一為 `env.development`/`env.production`。README 並補上發佈流程本身：版本提升清單、落地後打 `v<版本>` tag，以及「任何 skill、規則或文件化流程的變更，都要在同一份變更裏更新三語 README 的描述段落」的規則。

- **0.21.12** — SEO metadata 現在是 PRD surface contract 的一部分。每個 `UI-*` 條目記錄該 route 專屬且不重複的 `<title>` 與 meta description，加上 canonical URL、Open Graph/社交、robots 與 structured-data 決策（或明確的 `n/a — <reason>`）；整站 SEO（索引策略、sitemap 與 robots 政策、canonical 政策、預設 structured data）記在 Frontend Delivery Requirements 並帶自己的 `TEST-*` 追蹤。harness 端綁到底：實作必須如實渲染記錄的 `<head>`，缺少 SEO 紀錄是改道 `prd-builder` 的 PRD 契約缺口，UI 證據新增 rendered-head 檢查——integration head 上的 `<title>` 與 meta description 必須與 PRD 紀錄一致。這批同時移除已退休的 `update-private-skills.ps1` 單一指令更新器：per-runtime 副本已於 2026-09-03 刻意移除，安裝與更新從此就是單純的 skills 同步——把 `.agents/skills/` 的三個 harness skills 複製進 `~/.agents/skills/`——README 也不再教這個腳本。在三個具名 runtime 之外的 host 上執行現在免檢測：不是明確的 Codex、Claude Code 或 Pi 的 session 直接記 `provider: generic`，不去探測其他 runtime 的 CLI；版本閘門也不再用「拿不到 host 自身版本號」擋通用 host——載入中的 Harness release 加上所選 driver 的即時能力探測即完成觀察。種子化的 `AGENTS.md` 另新增 Commit Messages 一節，寫明訊息格式（`<type>(<scope>): <imperative summary>` 加 `Task`/`Trace`/`Verified` 尾行）、一個提交一種變更的規則與 mission 層級的 integration 提交格式，讓每個 runtime 在 commit 與 push 時寫法一致。
- **0.21.11** — UI run 現在以 Final Page-Quality Pass 收尾。Final Visual Parity Loop 之後，綁定在新增 `ui_quality_verification` 槽位的 skill（預設 `impeccable`）會在確切的 integration head 上，對每個交付的高保真頁面各跑一次 `critique` 與一次 `audit`。阻斷性發現進入既有修復預算；與凍結的 PRD、wireframes 或視覺來源衝突的發現改道 `prd-builder` 處理為 design-input delta，而不是本地改動；此步驟只用 evaluate 指令、不建立任何競爭性 product authority；綁定的 skill 不可用時該 gate 記為 `UNVALIDATED`，除非使用者明確接受否則擋下 closeout。種子化的 `AGENTS.md` Skill Bindings 表帶有這個新槽位。
- **0.21.10** — 渲染產生的 tasks view 改放在 `docs/tasks.md`，不再位於 `docs/goal/tasks.md`。`docs/goal/` 只保留權威 run 狀態（PLAN、RUN、DECISIONS、evidence）；非權威的人類閱讀 view 與 `DOCUMENTS.md`、`DEPLOYMENT.md` 同放在 `docs/`。SKILL 路由、DOCUMENTS manifest 列、renderer 說明文字、stray 檢查措辭與 pin 住的契約測試都改用新路徑。種子化的專案 `AGENTS.md` 現在直接寫明 goal 完成後的歸檔規則：擁有者宣告 goal 完成且 Closeout Bar 通過後，完成的 plan runtime（`PLAN.md`/`RUN.md` 加 evidence）即移入 `docs/goal/archived/<YYYYMMDD-HHMMSS>-<initiative-slug>/`——只搬移、不刪除，也不動 `docs/product/`。
- **0.21.9** — 來自四視角架構评审的加固清理。真實 bug 修復：RUN-v11 head 交叉檢查的後續 git 呼叫（merge-base、diff）現在會降級為錯誤條目，而不是讓 validator 崩潰。`CURRENT_SCHEMA_PAIR`/`is_current_pair` 取代八處手打的 `(6, 11)` 字面值；刪除了假的測試 patch seam 與過期的 `__all__`。selector 的「只會發出這些 deferral code」清單補齊了缺失的十一個 code 與 reviewer-tool 前綴，並有新測試把文件清單綁定到實際發出的 code。sequential-parent 綁定改為在錨點標題下定義一次（原先重複七處）、review 嘗試預算收斂到 Root-Cause Repair Escalation 一處；契約測試改為 pin 單一定義加指標句，不再凍結重複陳述。integration/bookkeeping 提交拆分定案（先 merge commit，隨後配對 bookkeeping commit），parity 修復明寫為既有預算下的普通 candidate-changing repair。約 1200 行 fixture 庫從 test_harness_manifest.py 移入 manifest_fixtures.py 並保留 re-export，canonical fixture 改從 harness_schema 讀版本號，contract_digest 的 CRLF/LF 正規化與 tests/__pycache__ 排除新增直接測試。
- **0.21.8** — 原子性現在貫穿整個 run 的提交契約，不再只是 worker 規則。任何參與者建立的每個提交都只承載一種變更：任務提交承載一個已驗證的結果，修復提交承載歸屬單一根因任務的修復，integration 提交只承載已審查的 mission heads 與協調狀態（絕不含無關修復或清理），bookkeeping 提交只承載 `PLAN.md`/`RUN.md` 檔案、絕不含產品程式碼。run 的任何一層——任務、修復、integration、wave 收尾、closeout——都不落地 catch-all 或混合提交；兩種變更就按依賴順序落兩個提交。
- **0.21.7** — UI run 現在以 Final Visual Parity Loop 收尾。最終 gate 上，每個 route-breakpoint-state 截圖都與該 run 的視覺權威比對：target-conformance 模式下把 approved HTML reference 與實作頁並排渲染比對，system-conformance 模式下以乾淨的 `check_ui_contract.py` 執行加完整截圖矩陣作為比對證據。每條 RUN-v11 `ui_evidence` 紀錄都帶有 `target_comparison`（baseline、baseline artifact、verdict）並由 harness 校驗；超出 tolerance 的差異進入最多兩輪的修復循環，仍無法解決的差異如實上報，不再改標籤了事。
- **0.21.6** — production/preview 資源分離現在有紀錄、有檢查，不再只是一句原則。部署紀錄新增 Resource Isolation 表——每個有狀態的 binding class（D1 database、KV namespace、R2 bucket、Durable Objects）各自紀錄 production 與 preview 的 resource ID——`check_deployment.py` 發現兩欄共用同一個 ID 即判失敗。契約要求在第一次 preview push 服務流量之前，把 preview environment 宣告的 bindings 與紀錄的 production ID 唯讀交叉核對；seeded 專案 `AGENTS.md` 寫明完全分離規則；前端 stack decision 也按 binding class 紀錄兩套 ID。
- **0.21.5** — Workers 的 preview 綁定隔離現在是配置出來的，不是預設就有的。契約記下：version preview URL 服務的是同一個 Worker 的新 version，並共用該 Worker 的現有 bindings——production Worker 的 version preview 會直接寫 production D1/KV/R2——因此有狀態的 preview 流量必須走 named Wrangler environment 部署的另一個具名 preview Worker，且其完整 binding 集要逐項明確宣告，因為 named environments 不繼承 bindings。非 production 的 D1/KV/R2 資源在專案建立時、第一次 preview push 之前就要建立；preview 綁到 production 資源是 blocker 而非配置偏好，這條邊界也不得依賴實驗性 flag。
- **0.21.4** — Enhancement 不再將被取代的 CSS 或舊版本視覺帶進更新後的結果。style 影響的 enhancement 更新 retained HTML reference 時，UI Design Pass 必須重新生成受影響 screen 的 style layer——在舊檔案 CSS 上追加不可審批，孤兒、重複、被覆蓋的 style block 要在 owner 審查前移除；就地編輯也要刷新 handoff 紀錄的 SHA-256 並歸檔編輯前副本。Harness 實作側現在會移除新 reference 不再包含的樣式與 class，絕不把新 reference 嫁接到舊實作的 CSS 上；refinement 流程並新增 stale-carryover 檢查：after 狀態不得出現 accepted delta 已取代的任何東西，delta 紀錄要列明每個被取代樣式及其 call site。同一套紀律覆蓋後端與 app 面——被取代的 endpoint、business rule、query、flag、job 要麼移除、要麼留下明確紀錄的相容保留；默默把舊路徑留在新路徑旁邊即是 contract violation。
- **0.21.3** — 部署紀錄新增第三種 mode：`ci_connected`——由 repo 自己的 CI workflow 在 push 時部署，取代平台 Git 連接。Cloudflare 上即 Wrangler bootstrap：`wrangler pages project create` 加上 push 觸發、跑 `wrangler pages deploy --branch` 的 workflow；branch 分流與 git_connected 完全一致（production branch 進 production，其餘 branch 進 preview URL），邊界也一樣：CI 部署不新增任何 authorization key，Harness 永不觸發它。在 Workers 上，同一個 workflow 對 production branch 跑 `wrangler deploy`、對其餘 branch 跑 `wrangler versions upload`，每個 version 各有自己的 preview URL，preview version 永不觸碰 production 流量。契約同時記下硬限制：Wrangler 建立的 Direct Upload 項目永遠不能事後轉成 git-connected；並寫明常設預設：Cloudflare 路線一律 Workers with Static Assets，Pages 只有 owner 明確決定才採用。部署後嘅唯讀驗證而家亦會將嗰次 push 嘅 preview URL 直接報喺對話入面——由 workflow 輸出或平台列表唯讀觀察得嚟,絕不自行拼湊或猜測。
- **0.21.2** — 原生 surface 與 web 同等待遇的 wireframe 與 HTML 預覽。`wireframe-guide.md` 明說原生手機／桌面 app 一樣交付單一 `wireframes.html` 審查投影（以產品自身的 size class 作為 viewport 切換），UI Preview Gate 也改為所有 UI-bearing surface——web、原生或跨平台手機、桌面——預設產出該 size class 的高保真 HTML mock，只有 HTML 無法呈現的 surface 才退回圖像生成。原生 surface 更進一步：單一自給自足的高保真 HTML 裝下每個 `UI-*` 畫面並附畫面切換器——與 `wireframes.html` 同一的單檔原則——讓 owner 在一個檔案裡審完整個 app。視覺階段的起手配方也明文化：從已核准的 PRD package 出發、兩個 skill 配套跑——`design-taste-frontend` 主導整體設計方向，`frontend-design` 執行 Taste 排除的面。
- **0.21.1** — Wireframe 參考查找與 enhancement 的 UI 影響分類。起草 `wireframes.html` 前，prd-builder 會先抓 2–4 個同類別主流活產品的頁面結構，再上 Dribbble 這類設計 gallery 找構圖參考，並把每個來源（或跳過原因）記進 `PRD.md` 的 `### Wireframe Approval`；參考只影響結構。Enhancement 流程現在會在起草前與 owner 明確分類 UI 影響（`none` / `structure` / `style` / `both`），不再預設 none：結構影響會重生成受影響的 wireframe 頁並重跑 approval gate，風格影響必須留下 owner 決定（重跑 UI Design Pass 或維持既有方向）——過期的視覺契約不再能默默發佈。UI Design Pass 現在也透過線上查找選擇 iconography——候選集封閉為 Lucide、Phosphor、Heroicons、Tabler 四套——推薦一套主力加指定備援，並在 handoff 的 `Iconography:` 行記錄引用來源——不再默默憑記憶預設某套 library。字體也比照同一套查找紀律——display/body 配對、Latin 加 CJK 涵蓋、載入策略記進 `Typography:` 行——handoff 並新增 `Color & dark mode:` 行記錄 palette 推導與深色模式範圍。前端技術選型新增 styling approach 層（Tailwind、CSS Modules、vanilla modern CSS），與其他層同樣逐列紀錄狀態與引用來源。
- **0.21.0** — browser-extension archetype 端到端支援。prd-builder 的訪談、架構與技術選型現在涵蓋 browser-extension archetype，full-harness 新增對應的平台 archetype。市場研究結論現在可以落進 `stack-decisions.md`；`architecture.md` 新增 Frontend/Backend Architecture 小節；暫定（provisional）stack 列現在會擋住發佈；`implementation-plan.md` 的排序意圖成為必填的 PLAN 輸入。
- **0.20.2** — 三份 README 新增完整技能生命週期圖：一張 mermaid 涵蓋 prd-builder → 選用視覺設計 → full-harness 的路由與每波執行迴圈（lock、observe、select、accept、adapters、lease、workers、validate、review、integrate）→ git-connected 部署，並標出橫切機制（skill 綁定、授權 ledger、版本閘、watchdog）與兩個人工停點。
- **0.20.1** — 審查後強化。lease-worker 接受真實的失敗 phase（`worker_failed`、`blocked`）並清除殘留的 `last_outcome`/`blockers`——失敗或 reconciled 的 mission 不再需要手改即可重試，`reconcile-interrupted` 不再是死路。畸形 verifier 改為回報鍵值錯誤而非 crash 驗證器。`--packet-out` 只在轉移後驗證閘通過後渲染。Run lock 在持有者自己的成功轉移時刷新心跳、時區天真/無法解析的心跳 fail-closed、非 dict `run_lock` 過不了 schema。`record-integration` 從 PLAN 圖解析節點而非命名慣例；`accept-wave` 同 id 也拒絕活躍 wave；`record-observation` 容忍死 worktree 並依 workspace 模式推導 `managed_by`。文件與閘門：AGENTS.md 驗證清單補 pyflakes、種入檢查器涵蓋自己模板的佔位符、鎖文件更正 `--session-id` 位置、driver 階梯補回 Pi、`cursor_wait` 改為 schema 標籤 `thread_poll`、worker 回報標題/File-Size-Limit 指向/種入文件清單/E2E 與 CI 模板引用修正。六個回歸測試釘住這些修復。
- **0.20.0** — 結構分解，行為全程保持（550 測試不變）。四處近似相同的 verifier-group 迴圈合併為單一 `_validate_verifier_group`；`validate_plan`（約 680 行）分解為九個 section helper；`validate_run` 瘦身約 700 行進五個 helper（`observed`、`attempt_log`、`waves`、約 400 行的 `workers`、`review_lineages`），共用區域變數顯式傳遞——剩餘的 `review_workers` 與 `runtime_capabilities` 段留待專門批次。Selector 改為每次選擇只建一次索引（`nodes_by_id`、workers-by-mission、review-workers-by-node），不再逐節點重建。每一步都以全套測試綠燈為閘。
- **0.19.1** — 程式碼簡化批次，行為完全不變（550 測試原樣通過）。移除死碼（TOOL_PROFILES、未使用的 helper/import/區域變數）；`new_run.py` 改 import 12 鍵帳本而非重複宣告；穿隧包裝器與倒裝守衛移除；source-path 四個函式合併為兩個參數化 helper；git blob 讀取器收斂至 `harness_core.read_git_blob`；`changed_files_digest` 由兩個 validator 共用；測試 git 管線收進 `manifest_fixtures`；`harness_manifest` 以 `__all__` 明示 re-export API；CI 加入 pyflakes 步驟（45 項清到 0），死碼無法再悄悄回歸。
- **0.19.0** — Runtime 提速：寫入路徑全面腳本化。`record-observation` 寫入 live-Git 觀測快照、`accept-wave` 記錄 wave 與 batch base、`lease-worker` 以一次原子驗證寫入綁定 graph/mission/task/worker/attempt、`record-integration` 對 live Git 收結 mission——取代原本讓 parent 輸出二次方增長的手工 RUN JSON 編輯。`reserve-review-dispatch --packet-out` 從記憶體中的 reserved run 直接渲染 reviewer packet（一個指令、一次驗證、省掉獨立渲染），selector 接受 `manifest_already_validated` 略過剛驗證過的重複步行；`plan_digest` 提出迴圈不再逐筆重算。
- **0.18.1** — 種入的運營文件移到 `docs/` 底下：`DEPLOYMENT.md` 與 `DOCUMENTS.md` 改發佈到 `docs/`（檢查器預設路徑跟進），repo root 只留 runtime 會自動發現的 `AGENTS.md` 與 `CLAUDE.md`。artifact lifecycle 的 root 發佈例外句隨之取消，root 禁則回到無例外。
- **0.18.0** — 最後一批技術債。PRD 的 artifact lifecycle 現在會盤點、暫存、發佈並回報種入的 root `DEPLOYMENT.md`/`DOCUMENTS.md`；`configure_project_context.py --check --require-resolved` 在種入的 `AGENTS.md` 仍有未解析佔位符時失敗，並作為發佈的最後一步；`docs/goal/DECISIONS.md` 有了定義（parent 擁有的執行中決策日誌），DOCUMENTS 清單補上 `implementation-plan.md`、歸檔文件與 DECISIONS 列；contract-digest 的遞延分支（不一致、未觀測）有測試；`check_deployment.py` 唯讀驗證部署紀錄結構；`render_tasks_view.py` 輸出狀態指紋（plan 修訂/digest、graph 修訂、wave）並提供 `--check` 過期偵測。
- **0.17.1** — 第二輪技術債清掃。`watchdog --reclaim` 正確使用 `--stale-after-minutes`、無鎖時不再重寫檔案；`--session-id` 統一放在子指令前並有明確錯誤訊息；`inspect_harness_run.py` 顯示 run lock 與 control 狀態；DOCUMENTS 清單把 design-system pair 標回 `docs/product/` 並統一 `tasks.md` 大小寫；`skip-integration-review`、`--tree-sha` 與 lock/watchdog 指令寫進正典文件和 runbook 清單；skill pins 在 resume 閘驗證；`check_skill_spec` 支援 frontmatter 接續行；必跑驗證從測試依賴安裝開始、與 CI 一致；專屬 provider 收斂為單一事實來源（`RUNTIME_DRIVER_PRIORITY`）。
- **0.17.0** — 強化與標準整理。Tier 1 技術債修畢：DOCUMENTS 清單與 TASKS 措辭回歸正典 `docs/goal/` 位置、同 tree 的 integration review skip 補上工具路徑（`record-review-attempt --tree-sha`、對 live Git 驗證的 `skip-integration-review`）、種入模板的殘留 adapter 措辭清除。新增：`check_skill_spec.py` 在 CI 强制 Agent Skills 開放規格；Skill Bindings 以 SKILL.md 的 SHA-256 釘住綁定的 skill，`check_skill_bindings.py` 重算比對（skill 變更 = 需刻意審視的 pin 更新）；耐久執行加入 run lock（`acquire/release/heartbeat-run-lock`，外來 session 被擋、15 分鐘後過期可接管）與回報中斷候選的 `watchdog` 轉移。
- **0.16.0** — PRD 流程在發佈時種入新 `AGENTS.md`，現在會順勢把 Skill Bindings 表填滿：列出該 session 看得到的本地已安裝 skills 作為各槽位候選、owner 用一個問題確認綁定、沒有候選的槽位留在隨附預設。既有的 `AGENTS.md` 絕不為此重開——綁定更新本身是一次明確的編輯。
- **0.15.0** — Skill 選擇改為專案設定而非修改 harness：種入的 `AGENTS.md` 新增 Skill Bindings 表，把階段槽位（design_direction、design_compilation、frontend_implementation）綁到安裝的 skills，隨附 skills 為預設。PRD 的 UI Design Pass 與 harness 的 UI 契約都從綁定表解析——採用新的 taste 或 frontend skill 只需改專案裡的一張表，綁定的 skill 繼承相同的模式、凍結來源與 review 閘門。
- **0.14.0** — PRD 流程現在會種入兩份 root 文件：`DEPLOYMENT.md`（平台紀錄、git connection 與 Cloudflare/Vercel/AWS 接線的人工設定清單、環境狀態表）和 `DOCUMENTS.md`（全流程文件總清單：位置、擁有者、是否 canonical）。`TASKS.md` 在 run 開始與每次接受 wave 後於 root 渲染。root 放運營文件；PRD 家族留在 `docs/product/`。
- **0.13.0** — 新增 deployment 契約：git-connected、平台抽象的部署階段——preview 綁 run 分支、production 綁預設分支（main 即 production），各平台一段（cloudflare、vercel、aws、generic，任何小寫 id 皆可）、綁定部署 SHA 的唯讀部署後驗證、只改紀錄不改流程的遷移路徑，並在專案 `AGENTS.md`/`CLAUDE.md` 種入 Deployment 段落。12-key ledger 不變；部署不新增任何授權鍵。
- **0.12.1** — runtime 升級閘新增重新編排契約：更新後，新的 session 執行 Resume Reconciliation、重新推導 frontier，並以新的 attempt 把所有未完成的節點綁到新 runtime（已完成節點永不重跑）；更換 provider 必須透過明確的 `allowed_providers` replan，絕不由升級自行推斷。
- **0.12.0** — integration review 的 skip 改以位元組相同的 tree 為準，不再限於同一個 commit：單一 mission 的 wave 以 merge commit 整合、tree 與已通過的 review 相同時，記錄 `integration.integration_tree_sha` 與 `review_workers[].tree_sha` 並跳過 unified dispatch。仍需派遣時，unified reviewer 拿到接縫導向的 packet：列出各 mission 已審 head，聚焦 merge 接縫、衝突解算與跨 mission 交互。
- **0.11.0** — Provider id 開放：任何小寫 id（市場 runtime 如 `gemini_cli`、`cursor`）在 `allowed_providers` 與 RUN `runtime_adapter` 都是 schema 合法值，直接走 generic 路線與 driver ladder，不需要改 schema；專屬 section 與 `RUNTIME_DRIVER_PRIORITY` 條目降為選用優化。generic 段落的市場 host 名稱為示意，非支援清單。
- **0.10.1** — generic provider 段落補成完整路線，任何未具名的 agent host 都能直接執行（driver 選擇、版本閘、模型傳遞、context 探索、chrome_devtools 遞延）；市集與 README 的對外描述改為適配任何 coding agent，而非只列三個命名執行環境。
- **0.10.0** — 三個 runtime adapter skill 合併為一份共用參考文件 `full-harness/references/runtime-adapters.md`，各 provider 一段章節並附新增 provider 的步驟；`fullstack-harness-codex`、`fullstack-harness-claude-code`、`fullstack-harness-pi` 自 bundle 移除（breaking）。review 可宣告 required tools，RUN 在 `runtime_capabilities.reviewer_tools` 記錄逐工具的 reviewer probe 佐證，selector 對未探測或不可用的工具改為 defer，不以 parent 的瀏覽器代替。mission 需通過 cohesion gate，每個 task 對應一個有序的 atomic commit 邊界。
- **0.9.0** — UI Design Pass 的 web 預覽路線改為預設由設計技能產出高擬真 HTML。核可的 HTML references 保留在 `docs/design/ui-references/<run-id>/`，被取代的組合歸檔到 `docs/design/archived/`；target-conformance 實作依每頁核可的 HTML reference 進行，並逐檔凍結 hash。
- **0.8.0** — 為 prd-builder 加入線框稿階段：每個 UI 產品包都會把 UI surface contract 投影成單一自包含的可互動 wireframes.html，並經人類 Wireframe Approval Gate 核可；視覺設計改為獨立、需明確要求的階段（UI Design Pass、provider 中立的 preview gate、Design System Need Gate）。product-design-builder 只編譯已核可的 UI Design Handoff。同時修復 design-system pair 檢查命令路徑、統一線框核可詞彙、讓 sync --check 忽略 runtime bytecode，並在 CI 加入 git diff --check。
- **0.7.0** — 將 managed work 升級為 PLAN v6 / RUN v11：加入 durable pause/cancel、跨 revision review lineage 與 owner grant、只含協調檔提交時不失效的 candidate head、loaded/installed contract digest、受控狀態轉移指令，以及有界 review packet。
- **0.6.0** — 為 Codex、Claude Code 與 Pi 加入共用 runtime upgrade gate。RUN-v10 會記錄 host／Harness 版本，只允許已啟動且仍相容的舊版 wave 跑到安全邊界，阻擋不相容或等待 restart 的 session，並在更新及重新 probe 後用新的 attempt 繼續未完成工作。更新器現在支援 Pi package；host binary 更新與 standalone Pi skill migration 仍需明確啟用。
- **0.5.0** — 降低 Codex、Claude Code 與 Pi 的 managed-run 開銷：加入有界 fresh context、event-driven completion、active-wave 串流 review、資源安全的平行 verifier batch、exact session cache、effort routing、較小 task slice，以及 RUN-v10 runtime telemetry。量測目標為 wall time 至少降低 75%，stretch target 為 85%；授權與 exact-SHA gate 維持不變。
- **0.4.0** — 新增 repository 內設計圖片探索，並把 Impeccable concept generation 接到 Product Design Builder 的 visual-direction gate。Creation mode 現在要求 `product-design-builder`、`impeccable` 與 `frontend-design`，同時保留現有 PRD 與三檔設計 package 作為唯一正式的產品與設計來源。
- **0.3.0** — 移除 GitHub 落地轉接器與整套部署／發佈模型。Harness 現在到「推送這次執行自己的分支」為止；把分支合進預設分支是使用者自己的步驟。授權帳本從 19 個動作縮到 12 個；`landing` 精簡為 `mode`、`remote`、`pushed_head_sha`、`continuity`；`integration.branch` 是唯一的分支欄位。移除分支保護佐證、`target_sources`、三個契約標記、`post_merge_cleanup`、`plan.release` 與 `run.targets`。
- **0.2.0** — 預設每個 mission 一個 worktree；PLAN v5 / RUN v10 typed graph，支援多 reviewer 扇出；Cloudflare 的 dispatched-deploy 與 Auto-Deploy（原生 Git 自動部署）發佈模型；持久的整合分支；以逐頁通用 HTML 樣稿取代已退役的 page UI matrix；行動裝置／桌面平台支援，包含一份專屬的行動裝置技術選型指南（原生 iOS/Android、Flutter、React Native/Expo）；透過 `.env.example` 產生環境密鑰的 scaffolding；為有界／機械式的委派工作新增 Haiku 成本層級。
