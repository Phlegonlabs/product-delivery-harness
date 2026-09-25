# 驗證與身分參考（Reference only）

狀態：Reference only · 核對日期：2026-09-25 · 本文件只比較候選與檢查面向，不自動採用、不安裝、不變更 skill 流程。外部參照皆為可選建議；採納後才受專案需求與安全設計約束。

## PRD 應先回答的問題

- 使用者是訪客、會員、企業成員、內部員工，還是混合身分？是否支援匿名轉正？
- 需要哪些登入方式：密碼、email 驗證、magic link、OTP、社交登入、SSO、MFA 或 passkey？
- 組織、租戶、角色、邀請、審核、停權、刪除、帳號合併、資料匯出與刪除如何運作？
- Session 存在哪裡？web、API、伺服器渲染頁、native app、webhook、背景工作如何驗證與撤銷？
- 個資所在地、保留期、稽核、事件通知、滲透測試、供應商事故責任與法遵證據要達到什麼程度？
- 驗證成功後，產品內部的資源授權、訂閱權益、角色快取與多租戶隔離由誰判定？

## 候選比較矩陣

| 候選 | 證據狀態 | 適合 | 避免條件 | 架構與整合義務 | 營運／成本／鎖定 | 遷移或退場 |
| --- | --- | --- | --- | --- | --- | --- |
| Clerk | 已補查 Organizations 與 Session tokens 官方正文 | 對外 SaaS、會員產品，想要受管理登入與帳號流程 | 組織模型、SDK、webhook、資料所在地、價格與併發限制未核對時 | 核對前端 SDK、伺服器驗證、session、webhook、使用者映射與多租戶邊界 | 受管理服務減少自建；成本與限制要按計畫核實 | 先保留自家 user id、組織 id 與角色契約 |
| Auth0 | 官方入門頁存在；Auth0.js 頁有部分能力 | 需要 hosted login、嵌入式登入或企業身分整合 | 只讀到 Auth0.js v10 就推斷全產品適配；未核對 RS256、SDK、法遵與費用 | 先選擇符合目標平台的登入流程與 SDK；記錄 issuer、audience、redirect URI、登出、組織與權限映射。不可把某個 Auth0.js 版本的變更當成所有平台的通用設定 | 受管理平台、tenant 設定、log retention 與升級都要納入維運 | 避免把 Auth0 使用者模型直接當成業務主鍵；記錄 token 欄位與角色映射 |
| Supabase Auth | 官方正文充分 | 已用 Supabase Postgres，想讓驗證、JWT、RLS 與資料 API 同生態；也可單獨使用 | 需要非 Supabase 資料庫作為授權主體、複雜企業 provisioning 或供應商控制權很高時 | 支援密碼、magic link、OTP、社交登入與 SSO；使用 JWT；SDK 會帶 token，並可透過 RLS 逐列授權。SSR 需為 Next.js、SvelteKit 等選對 Supabase client | 需要監控 session、token、RLS、資料庫遷移、備份與審計 | 以 Postgres user id、外部身分映射與明確授權契約降低耦合 |
| Firebase Authentication | 已補查 Firebase Authentication 官方總覽 | Google 生態產品、行動端或已有 Firebase 後端 | 組織、角色、企業 SSO、資料控制與 SDK 相容性未核對時 | 先核實平台 SDK、token 驗證、session、自訂 claim、安全規則與後端授權 | 供應商服務與配額會影響長期成本 | 保留自家 user id 與 provider account 映射，分離 Firebase claim 與業務角色 |
| Auth.js | 已補查官方首頁與框架整合示例 | 想把登入流程保留在自家應用，搭配自家資料庫與 session | 需要立即保證供應商法遵、託管管理或企業支援時 | 核對 framework adapter、provider、資料庫 adapter、cookie、CSRF、session 生命週期與伺服器驗證 | 自管邏輯降低供應商費率風險，但把安全責任留在應用 | session 與 user table 由自家掌控，較容易換 provider |
| Keycloak | 已補查 Keycloak 官方能力總覽 | 企業既有 IdP、自管 OIDC、realm/組織模型或本地試驗 | 團隊沒有運行、升級、備份、密碼流程與安全修補能力時 | 選擇 OIDC/OAuth 2.0 或 SAML 整合；依客戶端類型核對流程。伺服器端 confidential client 與 native/SPA public client 不同，不能把 secret 放進瀏覽器或 App | 要負責部署、升級、日誌、備份、憑證輪替與事故處理 | 若作為標準 OIDC IdP，可較容易改接相容 IdP |

## 事實與推論界線

事實：Supabase Auth 將驗證與資料授權分開，JWT 可與 RLS 整合。[官方 Auth 指南](https://supabase.com/docs/guides/auth)。Clerk 支援組織、角色與工作階段中的 active organization；多分頁場景要避免拿錯組織 context。[Organizations](https://clerk.com/docs/guides/organizations/overview)。Firebase 提供跨平台驗證 SDK；Auth.js 提供多個 Web 框架整合；Keycloak 支援 OIDC、OAuth 2.0、SAML 與 LDAP/AD federation。[Firebase](https://firebase.google.com/docs/auth)、[Auth.js](https://authjs.dev/)、[Keycloak](https://www.keycloak.org/)。

推論：選 managed 或自管，主要比較控制權、團隊維運能力及遷移成本；不代表安全程度或價格排序。下列例子不構成合規認證。

### 第七個候選：Better Auth

[Better Auth](https://better-auth.com/docs/introduction) 是 TypeScript authentication/authorization framework，官方列出帳號、session、組織與外掛能力。適合希望把驗證保留在程式碼與自有資料庫、願意管理升級與部署的團隊。若需要供應商直接承擔完整 IdP 維運，應與 Clerk/Auth0 類服務另外比較。

採用前逐一核對 framework/database adapter、cookie/CSRF、session 撤銷、郵件送達、MFA/passkey 外掛及企業功能條款。成本包含主機、DB、郵件與安全維護；自管不等於零成本。遷移要演練 user/account/session schema、密碼 hash 相容性與帳號連結，不把共用 TypeScript 語言當成可直接替換 Auth.js 的保證。

## 安全與設計路徑

- 受管理 IdP：把登入、MFA、郵件流程、風控與帳號生命週期交給供應商；先核對資料所在地、log、webhook、SLA、法遵證據與出口策略。
- 資料庫耦合授權：驗證後由資料庫 RLS 逐列限制；先驗證所有 query 路徑、service role 使用範圍、RLS 測試與預設拒絕。
- 應用內 session：以自家資料庫保存使用者、帳號連結與 session；先驗證 cookie 屬性、CSRF、登出、撤銷、並發裝置與滲透測試。
- 自管 OIDC IdP：按需求選擇 realm、client 與組織模型；不能把 client 自動當成租戶隔離邊界；先驗證憑證輪替、備份、升級、審計、暴力破解防護與災難還原。

以上四種只是路徑分類，不代表任何供應商優於另一個，也不代表符合特定法規。

## 情境式建議

- 若產品已有 Supabase Postgres、RLS 可清楚表達授權，且以 web 應用為主：先評估 Supabase Auth。設計時保留 server-side client、RLS 測試、service role 界限與登出後資料路徑驗證。
- 若已有企業 IdP、需要 SSO 與組織治理：優先核對既有 IdP，其次評估 Keycloak 或相容 OIDC 路徑。要求證明 realm、群組、角色、停權與登出事件如何映射到應用授權。
- 若是小型對外 SaaS、團隊希望減少自建登入：把 Clerk、Auth0、Firebase Authentication 一併列入比較。先用假資料驗證註冊、邀請、社交登入、組織、角色、webhook 重送、帳號刪除與資料所在地，再談費用與採納。

## 架構與整合義務

- 統一身分鍵：供應商 id 之外保留穩定內部 user id；記錄 email 變更、多 provider、帳號連結與合併規則。
- 授權模型：authentication 只證明身分；資源權限、訂閱權益、組織角色與租戶隔離要有應用層或資料庫層判定。
- token 驗證：記錄 issuer、audience、簽章、時鐘誤差、refresh、撤銷與 secret/key rotation。
- session：定義 cookie 名稱、屬性、生命週期、登出、強制登出、裝置清單與 API 行為。
- 事件：webhook 可能重複、延遲或亂序；消費者要可重送、可補償、可追蹤。
- 隱藏資料：前端不得只靠畫面隱藏授權；伺服器與資料層要重複驗證。

## 營運、成本與遷移面向

成本不給價格，先比較月活、MAU 定義、org 數、SSO 計費、MFA、SMS/OTP 供應商、email 額度、log retention、支援等級、資料所在地、自架主機與人力。遷移檢查至少包括：密碼 hash 可否轉移、社交帳號連結、MFA 註冊、組織與角色、session 撤銷、webhook 補償、email 模板、審計匯出、刪除請求與回滾。若短期只試驗 Keycloak，不要直接把生產使用者遷入；先分離測試 realm。

## 失敗／驗證清單

1. 註冊、登入、錯誤訊息、防枚舉、密碼重設、email 變更與重複提交通過。
2. MFA、社交登入、SSO、邀請、停權、恢復、刪除與匿名轉正通過。
3. 登出、refresh、撤銷、token 過期、跨裝置並發與跨租戶拒絕通過。
4. webhook 重複、亂序、延遲、重送、失敗補償與監控通過。
5. 授權通過：會員不能讀他人資料、降級使用者不能觸發舊權益、service role 不外洩、RLS 預設拒絕。
6. 隱私通過：資料所在地、保留期、匯出、刪除、備份生命週期與事故通知有證據。
7. 採納記錄完成：PRD 記錄登入與帳號生命週期；stack-decisions 記錄 provider；architecture 記錄 token、session、租戶與授權；security/API/integrations 文件記錄風險與契約。本參考文件本身不是審批閘門。

## 待驗證

各選項目前版本、授權條款、資料處理協議、SOC/ISO 佐證、定價、SDK 支援、Next.js/React 版本、native SDK、webhook 格式、SSO provider 限制與 MFA/passkey 能力都需在採納前逐項核實。四者基本定位已補查；企業能力、區域、SDK 版本與帳號方案仍需逐項確認。

## 來源

[Clerk Docs](https://clerk.com/docs)、[Auth0 Get Started](https://auth0.com/docs/get-started)、[Auth0.js](https://auth0.com/docs/libraries/auth0js)、[Supabase Auth](https://supabase.com/docs/guides/auth)、[Supabase 第三方 auth](https://supabase.com/docs/guides/auth/third-party/overview)、[Supabase：Sign in with Keycloak](https://supabase.com/docs/guides/auth/social-login/auth-keycloak)、[Firebase Authentication](https://firebase.google.com/docs/auth)、[Auth.js Getting Started](https://authjs.dev/getting-started)、[Keycloak Guides](https://www.keycloak.org/guides)。
