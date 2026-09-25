# 安全性參考

狀態：Reference only · 核對日期：2026-09-25。本文件只是可選參考，不自動採納、不安裝任何工具、不改變既有 skill 流程；專案文件明確記錄採納前，任何條目都不生效。

## 事實與推論的分界

「來源事實」僅摘要自證據包內的官方頁面，逐頁轉述刻意精簡；「工作推論」是本研究依情境做出的判斷，須由專案自行驗證。來源不足以確認處標記「待驗證」。

## 來源事實（精簡摘要）

- [OWASP ASVS 專案頁](https://owasp.org/projects/asvs)：ASVS 提供測試網頁應用技術安全控制的需求基準；該頁現行標示最新穩定版為 5.0.0，並建議引用需求編號時標註版本，因為編號可能跨版變動。
- [OWASP API Top 10](https://devguide.owasp.org/en/07-training-education/07-api-top-ten/)：2023 版列出 BOLA、認證失效、物件屬性層授權失效、資源消耗無限制、功能層授權失效、敏感業務流程無限制存取、SSRF、組態錯誤、庫存管理不當、API 消費不安全十類風險。
- [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)：授權與認證是不同概念；建議最小權限、預設拒絕與每次 request 的權限驗證；不可用難猜 ID 取代授權。
- [OAuth2 Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)：OAuth 2.0 是 API 保護與 OpenID Connect 聯合登入的基礎；bearer 與 possession 型權杖的選擇取決於應用的安全需求、威脅模型與實作限制。
- [Mobile Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mobile_Application_Security_Cheat_Sheet.html)：認證授權必須在伺服器端執行；用戶端控制應假設可被繞過；不應以可偽造的裝置識別碼作認證；來源提及 iOS App Attest（iOS 14+）等完整性驗證方向。
- [SecurityRAT](https://devguide.owasp.org/en/03-requirements/04-security-rat/)：OWASP 孵化器專案，可從 ASVS 產生初始需求集並追蹤需求狀態，提供 API 供合規工具整合。
- [Cornucopia AA4 卡片](https://cornucopia.owasp.org/cards/AA4)：以情境卡討論行動端金鑰僅在受控條件下使用、敏感操作前重新認證等議題。

## PRD 應先回答的問題

- 系統保護哪些資產（帳號、租戶資料、付款、金鑰、檔案上傳、外部 URL、模型輸入、Agent 工具副作用）？信任邊界在哪裡？
- 需要多高的驗證強度（借用 ASVS 分級概念，而非宣稱合規）？
- 是否有對外 API、第三方 OAuth/OIDC 整合、行動端或 Agent 工具面？
- 拒絕行為、可疑事件日誌與驗證證據分別由誰、記錄在哪份既有文件？

## 候選方式比較（六種，皆為可選）

下表的適用、成本與鎖定判斷屬工作推論；事實僅見上節。

| 候選方式 | 適用 | 避免條件 | 架構與整合義務 | 營運與成本面向 | 遷移與鎖定 |
| --- | --- | --- | --- | --- | --- |
| ASVS 分級需求集 | Web/API 產品需要可引用、可勾稽的安全需求底稿 | 只需單一議題速查時，全量清單過重 | 採納時須鎖定版本與條目 ID，並在 PRD 與 architecture 記錄適用等級與排除項 | 成本是逐條驗證與覆審人力；文件本身免費 | 標準為純文件，無供應商鎖定；版本升級需重對條目編號 |
| API Top 10 風險審查 | 對外 API、多服務或 BOLA 高風險架構 | 不能取代完整認證/授權設計 | 需建立 API 資產清單，並把各風險對映到拒絕測試 | 以審查會議與測試設計為主；清單免費 | 低；清單改版時需重新盤點 |
| 議題速查表（Authorization／OAuth2／Mobile） | 針對特定風險設計控制時的官方起點 | 速查表不是驗證標準，不可宣稱「已覆蓋」 | 套用建議須落實在伺服器端程式與權杖策略 | 按議題採納，成本最小 | 無技術鎖定；需定期比對上游更新 |
| 威脅情境工作坊（Cornucopia 式卡片） | 行動端金鑰、敏感操作等需要跨角色討論的設計 | 基礎控制尚未建立時，僅開工作坊流於表面 | 需要把卡片結論轉成行為規格與測試案例 | 一次性工作坊加後續驗證人力 | 無技術鎖定 |
| SecurityRAT 需求追蹤 | ASVS 條目量大、需長期追蹤狀態的團隊 | 小專案用表格即可；孵化器狀態的穩定性待驗證 | 需自行部署維運服務，並與需求文件對接 | 部署、升級與維運成本待評估 | 匯出格式與 ASVS 版本相容性未驗證，有流程依賴風險 |
| 平台完整性控制（App Attest 等） | 行動 App 防竄改的輔助層 | 不能取代伺服器端授權；Web 產品不適用 | 需後端驗證整合與裝置支援矩陣 | 平台門檻與裝置覆蓋成本 | 與作業系統平台綁定，跨平台需分案設計 |

## 三個情境建議（條件式範例，非通用預設）

1. 多租戶 SaaS：若 PRD 確認租戶資料是核心資產，可取 ASVS 的適用需求及 Authorization Cheat Sheet 的預設拒絕、逐次驗證建議作底稿，驗證證據採「跨租戶請求被拒且無副作用」；不必全量承諾最高分級。
2. 對外 API 加第三方登入：若系統簽發或接受 OAuth 權杖，先用 OAuth2 速查表決策權杖類型與流程邊界，再以 API Top 10 的 BOLA 與功能層授權條目產出拒絕測試案例。
3. 行動 App 含本機金鑰或 AI 工具呼叫：若裝置端保存金鑰，採「伺服器端授權為主、平台完整性驗證為輔」；敏感操作前重新認證（Cornucopia AA4 提出的議題方向），工具權限以最小範圍與輸入輸出檢查約束。

## 失敗與驗證檢查清單

- 採納前：版本已鎖定（採用具名版本，不能混用不同版本 ID）；適用等級與排除項經負責人確認並寫入 PRD。
- 實作後：每個採納條目有具體測試或審查證據；拒絕案例至少涵蓋跨帳號、跨租戶、屬性篡改與重放。
- 宣稱管理：本參考不產生任何「已合規」結論；code-security-review 仍以實際程式版本為準。

## 採納記錄落點（沿用既有文件，不新增關卡）

- PRD：記錄資產、威脅情境與接受水準。
- architecture 文件：記錄控制執行位置與拒絕行為。
- testing-acceptance 文件：承接對應測試證據。
- code-security-review 與 delivery-acceptance-contract：繼續持有審查與最終驗收結論。Reference 本身不是第二套 PASS 系統。

## 未解決事項

- ASVS 5.0.0 的逐項 ID 與專案適用性尚未做對映；本文件不聲稱完成全標準驗證。
- SecurityRAT 的部署需求、授權條款細節與 SDK 相容性待驗證。
- App Attest 的確切支援版本、Android 對應機制與後端 SDK 相容性未核對。
- OAuth 供應商實作差異（權杖生命週期、撤銷）未核對。

## 來源清單

全部為上方內文已內連的官方頁面：ASVS 專案頁、API Top 10、Authorization／OAuth2／Mobile Cheat Sheet、SecurityRAT、Cornucopia AA4。

## 可組合的控制方案（依威脅選擇）

標準、檢查表與工具不是互斥選項。以下是把它們轉成產品控制的候選方式，均為設計建議：

| 控制方向 | 適用與反例 | 整合及可驗證證據 | 成本與退出考量 |
| --- | --- | --- | --- |
| 集中服務層授權 | 多入口存取同一業務資源；不靠前端隱藏 | actor、tenant、resource、action 共同判定；跨租戶測試沒有讀寫副作用 | 政策和測試維護；替换框架保留政策案例 |
| DB row-level policy | 多租戶資料存取；不能保護資料庫外的副作用 | request context、service role 例外、policy migration 與拒絕測試 | SQL/DB 綁定與 policy 除錯；遷移需重建等價控制 |
| 入口濫用控制 | 登入、搜尋、昂貴 API、上傳；不能取代業務授權 | rate/quota、大小與時間上限、429/拒絕回饋；驗證合法使用者不被錯誤封鎖 | WAF/限流成本、誤判處理；留標準錯誤契約 |
| 第三方／URL 隔離 | webhook、外部 URL fetch、agent tool；資料可能惡意 | 簽章、重放、輸入 schema、網路出口與超時；測重複、錯簽、私網 URL | 營運規則與供應商差異；adapter 中集中限制 |
| 秘密與依賴治理 | 全部部署；尤其 CI 與第三方元件 | secret 留服務端、最小 scope、輪替與依賴更新；確認 logs/artifacts 沒有值 | 修補與輪替人力；不可把掃描 PASS 當安全保證 |

控制方向應對照 [OWASP API Security](https://owasp.org/API-Security/) 與 [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)。上述表格是我們的組合建議，沒有新設一套強制標準。

## Cloudflare 可選組合

平台內產品的責任邊界、搭配與替代路線見 [Cloudflare 參考](cloudflare-platform.md)。可只採用其中一項，不代表整套遷入 Cloudflare。
