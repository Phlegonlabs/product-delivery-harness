# Product Delivery Harness：逐步流程

這是開發來源的流程導覽。發布狀態看四語 README 與對應 Epic；導覽不授權外部操作，也不取代各 skill 的 checker、核准紀錄或 pinned RUN。既有核准和舊 RUN 按原版本保留。

## 角色與分工

角色名稱是職責，不是固定模型。Codex、Pi、Claude Code 或其他 host 都先依有效本機政策與實際工具完成綁定。
整體派工與證據流向見 [Delivery Collaboration Overview](../skills/delivery-harness/references/delegation-contract.md#delivery-collaboration-overview)；詳細分解、結果、runtime 與 receipt 規則仍以原有檔案為準。

| 角色 | 何時使用 | 交付責任 |
| --- | --- | --- |
| Parent / integrator | 全程 | 範圍、依賴、權限、派工、結果核對、序列整合及 owner 溝通 |
| Market researcher | 產品前後的獨立市場問題、UI 參考研究 | 有來源的事實、假設與未知；不決定產品 |
| Code explorer | 現有程式、介面、影響範圍與測試路徑 | 唯讀定位；不以研究結果冒充驗證 |
| Code architect | 跨模組、介面、資料或遷移方案 | 提出依賴與接口；parent 在既有核准決定內對帳並凍結；不替 owner 核准產品／技術選擇 |
| Frontend writer | 方向、HiFi、HTML/CSS、元件、互動、前端及視覺修復 | 讀完整 frontend-design；依核准來源實作並自查 |
| Backend writer | API、資料、權限、背景工作及服務行為 | 凍結接口內的實作、負面案例和資料安全 |
| Integration / test writer | 指定的跨層接線或測試檔 | 不越權修改 frontend；有獨立檔案與資源 ownership |
| Reviewer | Mission 整合前、統一候選及安全審查 | 獨立唯讀，綁精確 SHA；視覺審查要有自身瀏覽器能力 |
| Owner | 產品、技術、方向、Visual Approval 及未授權的外部動作 | 作出需要人決定的選擇；已有有效授權不重問 |

同一 section 可以有多個 writer。先凍結共享接口，再把列表、編輯流程、API 等真正獨立的工作分開；同一檔案、tokens、router、lockfile、schema 或 migration 各保留一位 owner。每個 checkout 同時只准一位 writer。每位 writer 可以依序完成多個小任務；每個 executable task 驗證後立即留下自己的 atomic commit。

## 入口與既有專案對帳

1. 確認 repository、有效指令鏈、工作目錄、分支、HEAD、staged／unstaged 與未追蹤檔案。
2. 先套用 `AGENTS.md` 的 Mandatory Governance Routes；沒有 `AGENTS.md` 才從目前 `PROJECT_AGENTS.template.md` 建立。已有檔案按觸發讀取 `delivery-harness/references/governance/` 的完整 rule owner，並保留本地規則和 precedence。
3. 合併時保留本地規則、路徑、bindings、owner 決定與歷史；對有差異的同名規則作語意對帳，不整份覆蓋、不追加矛盾指令。
4. 若 host 使用 `CLAUDE.md`，使用獨立 `PROJECT_CLAUDE.template.md`；保留已有 overlay 和原本 precedence。
5. 讀 `docs/DOCUMENTS.md`、適用產品／設計文件、未完成 Epic 及既有 PLAN/RUN；先辨認現有工作，不新建重複流程。
6. 執行 document-sync；分開記錄 source、installed 與實際 loaded skill identity。未知 loaded identity 保持未知。
7. 對第一次觀察或改變的文件讀適用完整內容；只有相同 bytes、同一階段且完整閱讀內容仍在 context 時才重用閱讀。
8. 為新增成果選定 Epic；同成果修復追加原 Epic。使用 `EPIC.template.md` 所需欄位並更新索引。
9. 檢查 `.gitignore` 是否需要新增已觀察到的本機產物規則；保留 lockfile、fixtures、schema 和正式設計文件。
10. 分類 initial delivery、enhancement、maintenance 或明確 full redesign；另記 UI impact：none、structure、style、both。
11. 新產品或新 stack 決策走 Product Definition；已核准的有限修復沿用現有範圍，不重做訪談。
12. 一位 writer、一段連貫驗證足夠時走 Direct；需要持久任務圖、交接或隔離整合時才走 Managed。
13. 盤點目前 host 的邏輯角色、實際工具、模型政策、獨立 reviewer、隔離空間及可用容量；工具存在不代表可操作指定 target。
14. 分開核對外部 runtime、subagent、使用者 task、worktree、branch、commit、integration、push、cleanup 的適用授權。
15. 凍結每份派工的問題或成果、來源 hash、依賴、write/deny scope、技能、工具、驗收與 result contract。
16. 至少兩個獨立而實質的研究問題，有能力和授權時派不同 sibling；依賴就緒的一批先全部啟動，再等待結果。
17. 缺少必要角色／工具／授權就只阻擋依賴它的工作；不得由 parent 偽裝成獨立 frontend 或 reviewer。

## Product Definition

18. 讀取既有同產品 package、staging、成果回顧與 Activation；enhancement 保留原內容與 ID。
19. 新產品依序完成「產品與使用者」「工作流、資料與規則」「交付、成功與風險」三段訪談；不重問已回答內容。
20. 核對答案覆蓋；只補實質缺口，不把後續設計偏好混進產品訪談。
21. 執行 research disclosure：只用可公開且已去敏感資訊的問題研究。
22. 新產品先研究功能基線、差異、商業模式與類別基準；明確記錄被允許的 skip 或沒有可靠來源。
23. Parent 核對研究者身分、問題與 frozen inputs，合併來源；owner 決定 go、clarify 或 stop。
24. 確定產品 archetype 與 validation depth，再決定相依的部署目標、作業系統／瀏覽器等選項。
25. 對適用產品確認 data/trust、security、AI/automation、monetization 和 partner gates；不適用也給理由。新版 package 明確記錄 eval-policy/1 的 applicability；適用產品凍結 rubric、樣本分母、重跑次數、pass rate、critical cases 與 judge 輸入，不使用全項目共用門檻。
26. 將 billing、entitlement、merchant-of-record、affiliate／reseller 等責任分開，不用單一供應商名稱取代設計。
27. 收集已選 stack 與 unresolved layers，記錄 owner 如何選擇 coherent 技術方案；沒有偏好不等於核准。
28. 需要時派 architect、frontend/backend 分析角色研究接口與技術選項；architect 只提出方案，parent 在核准決定內對帳並凍結接口，分析不直接建立 Approved 決定。
29. 在 staging 撰寫唯一英文 `PRD.md`、`architecture.md` 與 `stack-decisions.md`。
30. 同步完整 `PRD.zh-TW.md` 與 `architecture.zh-TW.md`；中文供 owner 審閱，英文維持實作權威。
31. 建立穩定需求、UI、operation、TEST 與 release-target ID，列出完整 journey、states、copy、responsive、accessibility 和 recovery。
32. Release targets 分開 development／production 身分；新版 main-preview/1 使用 candidate Preview 與 main，不要求永久 development branch。
33. 依 `DEPLOYMENT.template.md` 建立適用部署 seed；只寫 secret 名稱與目的地，不寫值、不猜實作未決名稱。
34. 依 `ACTIVATION.template.md` 建立適用 seed，列產品 profiles、metrics／TEST coverage；已有 live Activation 則保留，待後續對帳。
35. 依 `DOCUMENTS.template.md` 建立或更新文件索引，區分候選、核准、發布及待完成。
36. 草稿後進行市場對帳：重用有效研究，僅研究新缺口，列出有證據的優化建議。
37. Owner 對建議選 accepted、revise、deferred 或 rejected；pending 與沉默都不是決定。
38. 只把接受的變更合回同一 PRD、acceptance、architecture 與 stack；保留未接受建議和阻擋項。
39. 完成 Stack Decision Checkpoint；提出整套耦合層、成本假設、替代方案、維運 owner 與重訪條件。
40. 由原作者自查完整 journey、跨文件、研究及 TEST coverage；修復後重新綁定候選 hash。
41. 將實際完整候選文件連結交 owner，取得 Product Definition Approval；未解決的 required gate 不得通過。
42. 跑完整適用 Product package／雙語 checker，保留失敗与修復證據。
43. 依 artifact lifecycle 核對正式路徑與要保留的舊版本；已有精確出版授權就完成，否則只詢問缺少的動作。
44. 發布產品 package 並更新索引、指令合併與適用 stage bindings；不要把未確認技能 pin 當作可用。
45. 若本次只要求產品定義，交付後結束；若已要求完整交付，接續已授權 UI／implementation。Headless 不產虛構 UI 文件。

## UI 設計：三方向到完整核准

46. 確認 Product Definition 與 stack 核准有效，跑目前 UI 版本的產品 preflight。
47. 依本輪 initial／enhancement／maintenance 分流；保留 unaffected pages、方向與舊核准。
48. 確認 frontend writer 綁定，作者在自己的 context 讀完整 pinned `frontend-design` 與適用設計技能。
49. 合併未回答的 reference、視覺、圖片及動效問題；重用 owner 已給的連結、圖片和偏好。
50. UI 研究者核對適用 references、平台與動效方案，記錄採用、改寫或避免的原則；不另選未核准 stack。
51. 在 `docs/design/directions/<round>/` 建立 A、B、C 三個可實際渲染的方向；只有 owner 明示單方向才縮減。
52. 三方向使用相同主要與壓力案例及平台，呈現真正不同的字體、層次、布局、媒體與適用動效取捨。
53. 讓適用動效可播放；標出 reduced motion、效能與媒體來源限制，不用描述文字冒充動效實測。
54. 各方向原作者檢查實際畫面、operations、主要／壓力內容和尺寸，修復後留同作者自查證據。
55. Owner 選擇、混合、修改或拒絕方向；parent 記錄精確候選、選擇與範圍，不推定核准。
56. 混合或修改由 frontend writer 落成一致方向；必要檢查與 owner 決定綁到修改後候選。
57. 依選定方向建立 `docs/design/ui-references/<run-id>/` 的完整 connected HiFi；enhancement 只動受影響頁及必要接線。
58. 使用 `HIFI_REVIEWER.template.html`、共享 reviewer CSS 與正式 assembler；保留 reviewer／product 樣式隔離。
59. 覆蓋每個 PRD surface、route、copy、state、product control 和 operation destination。
60. 加入 loading、empty、error、permission、expired、long content 等適用狀態與真實返回／取消／復原行為。
61. 跑所有核准 viewports／size classes，另檢查相鄰核准網頁寬度間的中間尺寸與 layout 轉換。沒有相鄰網頁寬度時，`ui-design/3` 記錄完整的 `Intermediate width check: not_applicable — no adjacent approved web viewport widths`；原生尺寸與其他 HiFi 證據仍須完成。
62. 檢查 menu、tabs、dialog、forms、keyboard、Escape、focus return；切 active class 不等於操作完成。
63. 執行便宜的 HiFi completeness preflight；先修缺頁、漏字、漏 state、斷 operation 和非法資源。
64. 原作者再自查完整 HiFi 畫面、copy、layout、responsive 與 interactions，記錄實際檢查與修復。
65. 由適用獨立 review 執行 Impeccable critique／audit、browser matrix 與 H1–H9；總分至少 85、每項至少 80，且無阻擋缺陷或爭議。核對該 reviewer 自身所需工具。
66. 收斂同原因缺陷成一批，交原作者修復；對新候選複查原缺陷及受影響部分，不另開全面的美感探索。Impeccable、必要瀏覽器覆蓋與當前候選完整評估仍須完成；保留原 retry budget。
67. 所有 required findings、browser checks 和分數門檻通過，才呈現完整 HiFi entry、siblings 與 UI 記錄。
68. 取得一次 Visual Approval，涵蓋文案、結構、menus、tabs、其他互動、視覺及 tokens，綁精確候選與 scope。

## Design System 編譯與展示

69. Visual Approval 後執行 Need Gate。新版完整 UI 要交 Markdown、JSON、HTML；判斷 compile、update 或驗證後 reuse。
70. Headless 不適用；不改共用契約的有限 maintenance 不重建歷史設計。舊 pinned package 保留原 gate 語意。
71. Compiler 讀核准 PRD／stack／UI／完整 HiFi，以及既有 pair；保留穩定 DS／component ID 和未改項目。
72. 使用 `DESIGN_SYSTEM.template.md`、`.json` 與 `DESIGN_SYSTEM_SHOWCASE.template.json`，只編譯已核准的 tokens、primitives、product components、states、responsive 和 motion。
73. 從核准 HiFi 綁定實際 specimen 的來源、hash、component／variant／state 對應；資料不足就由適用 frontend owner 補核准來源。
74. 不從元件名稱猜樣式，不另外手寫第三套設計真相，不在編譯時重開產品或視覺方向。
75. 產生 `design-system-preview.html`，展示全部登記的色彩、字體、間距、尺寸區間、元件和適用狀態。
76. 在展示中保留適用互動、responsive 切換、motion replay／stop／reduced motion 與 provenance；native HTML 樣本不冒充 native 實測。
77. 執行 pair/source/coverage checker、contrast、type-scale 與 HTML exact-byte 檢查；stale 或缺 specimen 必須失敗。
78. 在瀏覽器檢查生成 HTML 的可視覆蓋、鍵盤、尺寸與動效；checker PASS 本身不是視覺 PASS。
79. 透過原 artifact lifecycle 將適用 UI 與完整 design package 一起發布，更新 source bindings 與索引。
80. 完成 Harness design handoff：確認來源、作者自查、獨立審查、owner 核准和 frozen package 都對得上。

## 任務圖、分工與驗收契約

81. 重新觀察 Git、外部變動及文件影響；核對已有授權和目前 host 能力。
82. 新一般工作與 hotfix 都凍結 remote main，以 main-preview/1 切暫時工作分支；歷史 RUN 保留原有 pin。
83. main 永久保護；現有 development 不自動刪除。Worker 與 RUN 在暫時工作分支 author。
84. Managed 使用 `HARNESS_PLAN.template.md`，凍結產品、設計、接口、原始 branch base、需求 traces、scope、verifiers 與 stop conditions。
85. 使用 `MISSION_RUNBOOK.template.md`、`WORKER_GOAL.template.md` 等適用模板建立角色正確且有界的派工；不用空白自由文取代必填契約。
86. 將每個 mission 拆成小而能獨立驗證的 executable tasks；每個 task 一個初始 atomic commit，不為每一步重新啟動 agent。
87. 先完成共用 API/schema/types/tokens 契約任務，再派相依 frontend／backend；下游 deny scope 保護共用來源。
88. 一個 section 若可分開列表、編輯、API、測試，分到不同隔離 writer；同檔高耦合工作留單一 owner。
89. 把測試／browser／DB／port／cache 等實際共享資源列入 ownership；worktree 隔離不代表外部資源隔離。
90. 以 `DELIVERY_ACCEPTANCE.template.json` 凍結 TEST、platform、auth、environment、build、scenario 及真實 assertions。
91. 用 `DELIVERY_RESULTS.template.json` 和適用 `E2E_VERIFICATION.template.md` 記實際結果；預期契約與執行結果分開。
92. 分清 mock、synthetic accounts、real authentication、candidate environment 和 production-safe smoke；不以測試授權動 production 資料。
93. PLAN readiness 檢查整個 graph 可執行、所有必要角色與來源有效；缺依賴不能先標 ready。
94. 用正式 `new_run.py` 產生 RUN；全部 mutation grants 預設 false，只填已取得的精確授權。
95. 觀察真正可用 slots、isolation、RAM 和 reviewer capacity；預設 1 不是硬性單 worker 上限。
96. Managed selector 決定 dependency-ready 且 scope／resource 不衝突的 wave；選中的 siblings 全部啟動後才等。

## 實作、review 與整合

97. Parent 保留每份 assignment／attempt／launch 身分，核對實際 role、model、工具與 result，不能只相信 worker 自述。
98. Worker 只讀自己的有界 packet 和必讀來源；一位 checkout writer，不寫 parent PLAN/RUN，不自行 push。
99. Frontend writer 依核准 HiFi／design system 實作 components、client states、accessibility 與 responsive。
100. Backend writer 實作 API、資料、auth、權限與服務行為；對成功和拒絕／隔離／失敗案例都驗證。
101. 每個 task 完成後先跑受影響 focused checks，檢查 staged scope，再立即建立自己的 atomic commit。
102. Task 修復以新小 commit 記錄；不可把多個已完成 task 最後合成大 commit 或 squash 掉任務邊界。
103. Worker 回傳 ordered task SHAs、實際 tests、write-scope 結果、未知與剩餘問題；沒有執行就不能填 PASS。
104. Parent 用 terminal event／cursor wait 接收結果，避免反覆全量輪詢；沒有事件工具才用有界 polling。
105. 一個 mission 完成即可派獨立 pre-integration reviewer，不必等最慢 sibling。
106. Reviewer 對 exact head 和完整指定 scope 檢查接口、缺陷、測試與需求；具體 findings 交原 writer 修复。
107. Parent 驗證通過的 mission commits 後序列整合，每次最多一個 integration；其他隔離 writer 可繼續。
108. 整合後跑必要 interface／integration checks；失敗按原範圍修復並產生新候選，舊 review 不冒充新 SHA 證據。
109. Managed 按正式 transitions 記 result、integration、coordination checkpoint 和 wave close；tasks view 從 RUN 產生。
110. Wave 未收齊不啟動目前 scheduler 不支持的新 writer frontier；不要以文件宣稱已有 rolling scheduler。
111. 完成 wave 後重新對帳和選下一批，直到全部 required missions 完成或留下明確 blocker。
112. 每個 task 使用 focused verification；固定統一候選才跑完整必要 suite，避免每小步都重複全產品測試。
113. Host verifier 在同 runner 內序列；只有已隔離且契約允許的 container／workspace 才平行，維持資源與清理邊界。
114. 對同一未變候選不重開相同 scope review；security、browser、live、migration 等 freshness 要求仍保留。

## 統一安全、驗收與候選關閉

115. 完成真實 acceptance scenarios，結果寫入分離 register，記錄精確平台、帳戶種類、環境、build 與證據。AI eval 保留 quality 與另一乾淨 checkout 的完整 handoff 報告，交付 runner、grader、lockfile 與 runbook；必要功能 TEST 仍全部 PASS。
116. 保留 H1 情境執行與 results/evidence-only H2 的來源關係；H2 不混產品修復，產品變更要新候選。
117. Frontend 完成 Final Visual Parity Loop，依適用平台跑實際 UI／native 驗證，不用 HTML 投影替代裝置證據。
118. 固定乾淨的統一候選 SHA，派獨立 code-security reviewer，讀適用安全需求和完整 declared scope。
119. Reviewer 追 entry point 到 sensitive sink，核對 auth、資料隔離、injection、path/command、secrets、供應链與競態等適用風險。
120. 安全工具或人工 source review 必須有實際執行結果；全部 skipped 不得 PASS，不為速度隱藏 coverage。
121. 安全修復改變 SHA 就重新 review 新候選；不把 tree 相同的一般 review 例外套給 security。
122. Review 通過後執行固定候選的 broad final regression／必要 E2E／UI／migration／acceptance gates。適用 Eval 的 always-run 順序為 broad final checks → eval acceptance → delivery acceptance → closeout；>=0.60 pin 需要明確 applicability，舊 pin 加入 marker 也採用檢查。
123. 收集所有精確候選結果與 scope；缺少、失效或 failure 都不能標完整交付。
124. Managed RUN 在 C 以 local_only 關閉，push grant 保持 false；Direct 沒有 RUN 就不製造 archive 流程。
125. Managed 用正式 archive 工具、expected main 與不可變 checkout-external anchor 搬移協調檔案，保留歷史。
126. 僅 archive bookkeeping 建立直接子 commit A，驗證 receipt、anchor、relocation 與 exact candidate；不把 C 的證據改標成 A 執行。
127. 若需發布工作分支 A，使用另外授權的正式 trusted-host publication request／attempt／receipt，無 force 並 read back exact A。
128. Archive 後修復保留 A 和原 RUN，走有界 correction continuation；不得改舊 receipt 或重寫歷史。

## PR／分支 Preview、main 與部署

129. Direct candidate 或 Managed A 完成本機檢查和 exact-SHA review，準備 PR／分支 Preview。
130. Cloudflare 優先使用 Wrangler 4.135.0+ 原生 Previews；不支援的必要流程需隔離替代方案或保持 blocked。核准採用 Void 時，direct target 仍是 `cloudflare`。先證明 pinned build／config 支援原生 Preview；否則經核准使用分離 config／lock 的 development Worker，以 project-local `void deploy --platform cloudflare` 完成 fresh build 與隔離部署。檢查資源副作用、migration rollback 與 exact deploy readback，不沿用一般 Wrangler 指令。
131. 記錄 Preview 固定 deployment URL／ID、candidate SHA、資料隔離及實際驗收結果。
132. 凍結已驗 candidate；分支 Preview URL 後續更新不改寫既有驗收證據。
133. 完成必要 release matrix、fresh security、migration 與隔離 Preview 驗證。
134. 完成精確 main promotion 授權與最新 main／ancestry 對帳；drift 或 non-fast-forward 先重新處理，不 force。
135. 依保護規則將已驗 SHA 升到 main，read back exact 結果；新 server SHA 須 tree equality 與完整 exact-SHA 驗證。
136. 部署綁定正確 account／project／environment、SHA、artifact 及非 secret config identity；提交成功不等於部署成功。
137. Read back 真正部署版本並做 production-safe smoke／適用 UI parity；不重播 synthetic fixture 建立或破壞性測試。
138. Hotfix 使用同一 main／Preview 流程，不再要求回整 development；歷史 dual-branch RUN 保留原規則。
139. 任何 cleanup 都永久排除 development 和 main；其他 branch／worktree 刪除也保留個別授權與依賴檢查。

## Product Activation：完成外部設定

140. 讀目前 Product、Deployment、existing Activation 與實作設定名稱，找本次真正新增、變更或失效的外部工作。
141. 先驗精確 release target、SHA、artifact、account、project 與 environment；不明就阻擋寫入。
142. 選 core 加適用 surface／feature profiles，從既有模板建立或接續唯一 staging record。
143. 拆最小 ACT actions，保留 metrics／TEST／MS coverage；只先填安全執行必需欄位，不把整輪花在美化文件。
144. 綁目前 host 真正可用的 connector、API、CLI、Browser、Computer Use 或 manual 路線；先對確切 target 做非修改 probe。
145. 準備每個 action 的 current state、desired state、digest、風險、write／readback routes；能力不是授權。
146. 沿用仍有效的 exact grants；缺少授權才呈現具體 action batch，高風險維持 action-time confirmation。
147. 變更前重新讀 target／precondition；drift 使舊 digest 失效。已是期望狀態就直接讀回驗證，不浪費 write grant。
148. Target 內循序執行已授權動作，首次 mutation attempt 就消耗 grant，包含結果不明的 timeout。
149. 每次 action 後獨立 read back，再執行允許的 behavior check；HTTP 2xx 或成功 toast 只證明 mutation 回應。
150. 結果不明先查狀態，不換工具盲重試；失敗保留證據和具體下一步。
151. 只把 password、OTP、MFA、CAPTCHA、帳務／法律確認等必要一步交 owner；回報完成後立即讀回並繼續。
152. 不變的外部物件可沿用有效設定證據，但新 build/config 的行為證據仍須檢查是否失效。
153. 執行結束檢查：已授權、可執行的 required action 不能沒嘗試又沒有具體 blocker／owner 延後就結束宣稱完成。
154. 區分 verified、configured-but-unverified、blocked、not-attempted 與 already-correct；只產文件最多是 prepared。
155. 逐 release target 跑 readiness，驗證 MS source／signal；缺必要設定不藏入 backlog 後宣稱 ready。
156. 核對 live baseline 未變，按既有授權發布 validated Activation，回報實際完成數及精確剩餘動作。
157. DNS、store review 或 measurement window 要等就保留狀態並結束本輪；不讓 agent 空等，也不冒充已完成。

## Outcome、SEO 與下一輪

158. 真實 measurement window 結束且 owner 要求後，Product Definition 讀 verified MS 與 Deployment，核對 baseline、target、guardrail 和實際值。
159. 依 `OUTCOME_REVIEW.template.md` 建立新的 dated record，或按明確續寫契約追加；保留舊 evidence 與 verdict history。
160. 每 target 得出 no_change、enhancement 或 incident，按原 owner flow 返回有界 Epic／incident，不另起第二份 PRD。
161. 公開可搜尋的 surface 才執行適用 SEO review，依證據選 baseline、growth_review 或 traffic_drop。
162. 先驗 production domain、Search Console／Analytics scope、窗口與來源 freshness，再判讀可爬取性、索引、頁面和 query。
163. 分開 observed、estimated、hypothesis；不把 Search Console clicks 和 Analytics sessions 硬當同一指標。
164. 先排序 existing pages 可改善項，再評估新增內容；每項指定 owner route 與可衡量 follow-up。
165. 預設交 inline 唯讀結果；要求保存時使用 `SEO_REVIEW.template.md`、dated path 與 lifecycle checker。
166. SEO 發現不授權改 metadata、發文、submit sitemap 或外部設定；按已授權範圍交回相應 skill。

## 交接與僅限技能原始碼 repository 的發布

167. 每次交接重新核對 repository／branch／HEAD／working tree，更新 meaningful change 的 Epic、索引及受影響文件。
168. 比對 observed installed AGENTS template 與本地共用規則，報 current／stale／unknown 和具體差異；保留專案特例。
169. 回報實際 tests、review、SHA、release／installation 狀態和下一 owner；未完成就明說未完成。
170. 以下僅適用本 skills 原始碼庫：選定 Epic，先讀受影響 canonical SKILL／references，再改 `skills/` 正式來源。
171. 每個語意／流程變更同步四語 README 描述；小任務 focused checks 後 atomic commit，不每任務 bump release。
172. 依變更影響選本地 focused suite；未知或跨契約影響走完整必要驗證，不任意略過測試。
173. 只在需要時準備 Python test dependencies、`npm ci` 和對應 Playwright Chromium；正確版本的安裝可沿用，required browser prerequisites 缺少就失敗。
174. 固定 release 統一更新 package version、Harness VERSION、四語 badge／版本記錄與 RUNBOOK 預設版本。
175. 對該固定候選跑 skill spec、Pyflakes、docs weight、Harness、enabled golden path、Product Definition、UI、Design System、Activation、SEO 和 diff checks。
176. CI 統一候選 SHA，保留 Linux／macOS／Windows 的必要覆蓋；排除 feature push／PR 重複 full run，聚合 required gate 不得因 skip 誤綠。
177. 跨平台長 suite 在獨立 jobs 分片，保留完整 coverage 與每檔 timing；cache 只存相容依賴下載，不存測試 PASS。
178. 對最終精確候選做獨立 review；修復後新候選重新跑受影響檢查，維持正式 release 所需完整結果。
179. 依 main-only 來源維護流程升版；同 SHA 和輸入可保留 deterministic suite 來源，新 SHA／配置／toolchain 則重驗。
180. 驗證正式 main release commit 後才建立對應 `v<version>` tag；本地未推送成果不宣稱正式發布。
181. 正式 release 成功且 bundle digest 改變時，在安全載入邊界執行一次正式 installer，保留 backup、rollback 和 byte verification；feature／development push 不自動取代使用中的正式 skills。
182. 安裝成功且需載入新版才重新啟動相關 host；不恢復已退役的 per-runtime copies，不停止無關 session。

上述步驟按適用性執行。沒有產品的技能原始碼維護不跑 consumer 訪談、Visual Approval 或真實 Activation；仍要跑會驗證這些能力的 source tests。所有 skipped／不適用／blocked 都要有實際理由。

## Generate、Verify、Correct

Product、UI、Design System、task／mission、feature、platform handoff 與 integrated candidate 都用[共用 stage-loop 指引](../skills/delivery-harness/references/gen-verify-correct.md)。先用最短有效 focused check，到 mission、feature、platform handoff 或 integration 才擴大；PASS 就停止。

每個 stage 的 author/corrector 是 Product author、bound frontend author、compiler author、assigned writer 或 owning platform mission；verifier 是既有 checker、independent review 或 owner decision。Reviewer 只回報具體 expected／actual／evidence，不變成 author、remediator 或外部 target 的 mutator。

PASS 綁精確 candidate SHA 與輸入；受影響輸入變更會讓相關證據失效。沿用既有 attempt／time budget 與 gate，成功後不要求最低迭代數，也不因失敗放寬閘門或宣稱零 bug。

平台手上的 retained integration PASS 只是歷史 handoff；平台目前健康要用 unified candidate SHA 重新回歸。Human decisions 保持 human，review 或 capability 都不授權外部動作。

## 現有模板怎樣進入流程

使用目前 installed skill 的適用模板；已有文件先合併／更新，不為使用模板而重建。下列路徑皆在對應 skill 的 `assets/templates/`。

| 模板／共用資產 | 使用時點與產物 |
| --- | --- |
| `PROJECT_AGENTS.template.md` | 步驟 2–3：建立缺少的 AGENTS 或審閱後合併共用規則 |
| `PROJECT_CLAUDE.template.md` | 步驟 4：適用 host 的獨立 overlay，保留現有 precedence |
| `EPIC.template.md` | 步驟 8：記錄新成果與每次有意義變更，不取代 PRD／RUN |
| `DOCUMENTS.template.md` | 步驟 35、167：適用文件索引和現況 |
| `DEPLOYMENT.template.md` | 步驟 33、136：部署 seed 到真實版本／設定讀回 |
| `ACTIVATION.template.md` | 步驟 34、142：seed 到 staging，再記實際執行和 verified evidence |
| `HIFI_REVIEWER.template.html`、`REVIEWER_SHARED.css` | 步驟 58：由正式 assembler 建立 reviewer shell，不手抄第二份 shell |
| `composition-patterns.json` | 方向／HiFi 的可選構圖參考；不是固定頁面 recipe，不超越 PRD 或 owner 選擇 |
| `DESIGN_SYSTEM.template.md`、`DESIGN_SYSTEM.template.json`、`DESIGN_SYSTEM_SHOWCASE.template.json` | 步驟 72：同一編譯契約；HTML 由 renderer 產生，不能手寫平行真相 |
| `GOAL.template.md` | Direct 小任務或明確需要 copy-ready prompt 時選用；通常目標直接存在 PLAN／RUN，模板不自授權 |
| `HARNESS_PLAN.template.md` | 步驟 84：Managed 靜態範圍／任務圖；RUN 由正式 generator 建立 |
| `MISSION_RUNBOOK.template.md`、`WORKER_GOAL.template.md` | 步驟 85：目前 runtime pin、任務執行手冊及有界 worker 派工 |
| `TASKS.template.md` | 步驟 109：可選人類檢視；正式 renderer 從 PLAN／RUN 產生，不手編狀態 |
| `DELIVERY_ACCEPTANCE.template.json`、`DELIVERY_RESULTS.template.json` | 步驟 90–91、115：預期與結果分離，綁真實 scenario 和 candidate |
| `E2E_VERIFICATION.template.md` | 步驟 91、115：適用端到端案例／證據，不代替實際執行 |
| `PROJECT_CI.template.yml` | 有 GitHub CI 且需建立／更新 workflow 時填入產品的真實 commands；其他 host 使用自身等效 CI，不能照抄本來源庫 suites |
| `REFINEMENT_BACKLOG.template.md` | 只有 RUN 內 backlog 太難閱讀才展開；保留 TEST／failure／next action，不因此產生新授權 |
| `OUTCOME_REVIEW.template.md` | 步驟 159：窗口結束後的新 dated outcome，保留既有 verdict history |
| `SEO_REVIEW.template.md` | 步驟 165：owner 要求保存的 lifecycle SEO review；inline 唯讀 review 不強制建檔 |
| `WIREFRAMES.template.html`、`WIREFRAMES_V4.template.html` | 僅維護原本採用該契約的歷史 package；新版完整 UI 沿 PRD → 三方向 → HiFi，不重啟已退役的 Wireframe stage |

HTML 展示的參考來源：[Bootstrap Cheatsheet](https://getbootstrap.com/docs/5.3/examples/cheatsheet/) 的單頁元件目錄、[Storybook Controls](https://storybook.js.org/docs/essentials/controls) 的變體控制，以及 [Carbon Motion](https://carbondesignsystem.com/elements/motion/overview/) 的動效說明。這些只供展示方式參考；實際元件與樣式仍取自產品已核准的 HiFi，不因此更換 stack 或增加套件。

## 契約索引

- [Delegation](../skills/delivery-harness/references/delegation-contract.md)、[Runtime](../skills/delivery-harness/references/runtime-performance.md)、[atomic commits](../skills/delivery-harness/references/commit-convention.md)
- [Product Definition](../skills/product-definition-builder/SKILL.md)、[UI](../skills/ui-design-builder/SKILL.md)、[Design System](../skills/design-system-compiler/SKILL.md)
- [Delivery acceptance](../skills/delivery-harness/references/delivery-acceptance-contract.md)、[Security](../skills/code-security-review/SKILL.md)、[Branch promotion](../skills/delivery-harness/references/branch-promotion-contract.md)
- [Activation](../skills/product-activation/SKILL.md)、[SEO](../skills/seo-growth-review/SKILL.md)
