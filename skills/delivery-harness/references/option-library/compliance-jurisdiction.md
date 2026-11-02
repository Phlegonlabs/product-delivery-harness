# 法域合規參考（Compliance by Jurisdiction）

狀態：Reference only · 核對日期：2026-11-01。本文件只是可選參考，不是法律或稅務意見，不自動採納、不安裝任何工具、不新增關卡，也不改變既有 skill 流程。它提醒 PRD 的 Data and Trust 列，以及 program PRD 的 Integrations Register（採用 program 設定檔時），該問哪些法域問題；答案由專案負責人與有資格的專業人士確認。

## PRD 層級問題

- 產品在哪些法域有公司、客戶、員工或資料主體？
- 發票、收款與報稅由誰執行：自建系統、會計師，還是第三方平台？
- 帳務紀錄、發票與薪資資料各保存多久、放在哪個區域？刪除請求和保存義務衝突時誰決定？
- 個人資料是否離開所在法域（雲端區域、子處理者、遠端支援）？依據是什麼？
- 哪些申報有固定期限？由系統產出、由人工提交，還是由外部服務提交？

## 比較矩陣（六個法域）

儲存格內的〔代號〕指向文末來源表。`UNVALIDATED` 表示本輪沒有找到官方來源或無法確認，不可當成「沒有規定」。

| 法域 | 稅制與電子發票 | 帳務紀錄保存年限 | 資料在地與跨境傳輸 | 薪資與法定申報節奏 |
| --- | --- | --- | --- | --- |
| 香港 | 無 VAT／GST，只課利得稅、薪俸稅與物業稅〔HK1〕；強制電子發票制度：UNVALIDATED | 營業紀錄自交易完成起至少 7 年〔HK2〕；公司會計紀錄自最後記載所屬財政年度結束起 7 年〔HK3〕 | 個人資料（私隱）條例第 33 條（限制境外傳輸）依 PCPD 公布的條例文本尚未實施〔HK4〕；PCPD 的建議契約條款屬自願採用〔HK5〕 | MPF 供款日為每月 10 日〔HK6〕；雇主報稅表 2026 年於 4 月 1 日發出，限一個月內遞交〔HK7〕 |
| 台灣 | 營業稅；電子統一發票經財政部電子發票整合服務平台，B2C 於 48 小時內、B2B 於 7 日內上傳〔TW1〕〔TW2〕；營業稅法 2024-08-07 修正明定上傳義務〔TW2〕；哪些營業人必須開立電子發票：UNVALIDATED | 憑證至少 5 年，帳簿與財務報表至少 10 年，自年度決算程序完成起算，未結事項除外〔TW3〕 | 個資法第 21 條：中央目的事業主管機關得在國家重大利益、條約要求、接收國保護不足、規避本法等情形限制國際傳輸〔TW4〕 | 營業稅每兩個月申報一次，於 1、3、5、7、9、11 月 15 日前〔TW5〕；扣繳稅款次月 10 日前繳納，扣繳憑單於次年 1 月底前申報〔TW6〕；雇主每月至少提繳月薪 6% 至勞退個人專戶〔TW7〕 |
| 新加坡 | GST 稅率 9%（2024-01-01 起）〔SG1〕；GST InvoiceNow：2025-11-01 起新設公司的自願 GST 登記者、2026-04-01 起所有新自願登記者須經 InvoiceNow 傳送發票資料給 IRAS，既有登記者分階段，2031 年 4 月前全部納入〔SG2〕〔SG3〕 | GST 與所得稅紀錄自會計期間結束起至少 5 年〔SG4〕；公司法第 199 條：自交易完成之財政年度結束起不少於 5 年〔SG5〕 | PDPA 轉移限制義務（第 26 條）：境外接收方的保護水準須與 PDPA 相當，除非獲豁免〔SG6〕 | CPF 到期日為當月底，次月 14 日前未繳即採取執法〔SG7〕；適用的雇主每年 3 月 1 日前以 AIS 電子申報員工收入〔SG8〕 |
| 日本 | 消費稅標準稅率 10%、軽減稅率 8%〔JP1〕；適格請求書等保存方式（インボイス制度）自 2023-10-01 起，進項稅額扣除須保存帳簿與適格請求書〔JP2〕；電子帳簿保存法對電子取引資料的保存要求：具體條件 UNVALIDATED（只確認 NTA 有 2024 年 1 月起的保存方式指引）〔JP8〕 | 法人帳簿書類 7 年（自確定申告書提出期限翌日起），產生青色欠損金的事業年度 10 年〔JP3〕；消費稅帳簿與請求書等 7 年，自課稅期間末日翌日起算 2 個月後起算〔JP4〕 | APPI：向境外第三方提供個人資料，原則須本人事前同意並先提供對方國制度資訊；PPC 指定的同等保護國與具同等措施的接收方為例外〔JP5〕 | 源泉所得稅於付款月次月 10 日前繳納，符合條件的小規模給付者可申請半年一次〔JP6〕；給與所得源泉徴収票等法定調書於翌年 1 月 31 日前提出〔JP7〕 |
| 歐盟 | VAT 指令 2006/112/EC；指令 (EU) 2025/516（ViDA，2025-03-11）使電子發票成為預設開立方式，跨境交易的結構化電子發票加近即時數位申報自 2030-07-01 起強制，境內 B2B 由成員國自訂〔EU1〕〔EU2〕；各成員國現行境內強制範圍：UNVALIDATED | 發票保存期由各成員國決定（指令第 244 條）；Commission 2019 評估研究：4 至 10 年，多數 5 至 7 年〔EU3〕 | GDPR 第五章：充分性認定、標準契約條款等適當保障，傳出歐盟的資料須符合第 44 條以下的條件〔EU4〕 | VAT 申報期間由成員國定為 1、2 或 3 個月（可至一年），申報期限不得晚於期間結束後 2 個月〔EU5〕；薪資與社會保險申報：UNVALIDATED |
| 美國（州見下方備註） | 聯邦層級無全國性銷售稅或 VAT，銷售與使用稅由州與地方課徵〔US1〕；無實體據點的賣家可因經濟連結被州要求代收〔US2〕；聯邦強制電子發票：UNVALIDATED | IRS：一般為申報後 3 年，少報逾 25% 為 6 年，壞帳與證券無價損失 7 年〔US3〕；僱傭稅紀錄至少 4 年〔US4〕 | 聯邦層級一般性的資料在地或跨境傳輸規則：UNVALIDATED；DOJ 28 CFR Part 202（2025-01-08 公布）限制與受關注國家或其涵蓋人員的大宗敏感個資與政府相關資料交易〔US5〕 | 回溯期稅額 $50,000 以下為每月存款（次月 15 日前），超過為每半週〔US7〕；Form 941 每季（季後次月底）、Form 940 與 W-2 為 1 月 31 日〔US8〕 |

美國州備註：州另有銷售稅、州所得稅預扣、失業保險與隱私法。阿拉斯加、德拉瓦、蒙大拿、新罕布夏與奧勒岡沒有州層級銷售稅，其中阿拉斯加與蒙大拿有地方銷售稅〔US1〕；加州 CCPA 適用於符合 AG 頁面所列門檻的營利事業〔US6〕；其餘各州的稅率、申報節奏與隱私法：UNVALIDATED。

## 事實與推論的分界

「來源事實」是矩陣中帶〔代號〕的內容，轉述自文末的官方頁面，刻意精簡。本輪以限定官方網域的搜尋取得頁面摘要，沒有逐頁開啟全文，所以條號、稅率、期限與門檻在寫入 PRD 前必須開啟原頁面核對。

「工作推論」是下列情境建議與採納落點，是本研究依情境做的判斷，須由專案自行驗證。

## 情境建議（條件式範例，非通用預設）

1. 在台灣與香港收款的訂閱產品：在 Data and Trust 列同時記下兩地的保存年限（台灣憑證 5 年、帳簿 10 年；香港 7 年），並與刪除請求流程對照。台灣電子發票由哪個系統上傳、是否守住 48 小時與 7 日期限，寫入 Integrations Register。
2. 新加坡或日本客戶資料由境外雲端區域處理：在 Data and Trust 列記下資料區域、子處理者與傳輸依據。新加坡看接收方的保護水準是否相當，日本看本人同意或同等措施。
3. 歐盟與美國並行的 B2B 銷售：歐盟的發票保存期與電子發票範圍隨成員國而異，美國的銷售稅隨州而異。把各地的稅額計算、發票與薪資服務分別列入 Integrations Register，不要假設一個供應商涵蓋全部。

## 失敗與核對清單

- 進入 PRD 的每個數字與日期都附官方 URL 與查閱日期；找不到就維持 `UNVALIDATED`。
- 寫入前開啟原頁面核對條文、生效日與門檻；矩陣來自搜尋摘要，可能已過時。
- 稅務、會計與法務結論由有資格的人確認。本文件不產生「已合規」結論。
- 保存年限與刪除請求、備份保存期衝突時，列為 Open Question 並指定負責人。
- 外部申報或電子發票服務進入 Integrations Register 時，填完方向與頻率、冪等鍵、對帳報表與錯誤佇列負責人，並各有對應 TEST。
- 未取得官方確認的項目標「未驗證」，不得以文件審查取代。

## 採納紀錄（對應既有專案文件，不新增閘門）

- PRD Data and Trust 列：保存年限、資料存放區域、跨境傳輸依據、刪除與保存的衝突。
- program PRD 的 Integrations Register：稅務機關、電子發票平台、薪資與退休金供應商。
- architecture 文件：資料區域與部署位置。
- 本文件不是關卡，不審批任何內容；條目在專案文件明確記錄採納前不生效。

## 未解決事項

- UNVALIDATED 儲存格：香港與美國聯邦的強制電子發票制度、台灣哪些營業人必須開立電子發票、日本電子取引資料保存的具體條件、歐盟各成員國的境內電子發票範圍與薪資申報、美國聯邦的一般跨境傳輸規則與各州細節。
- 未逐項核對：新加坡 GST 申報頻率、日本消費稅申報頻率、台灣勞保與健保、日本社會保險的申報節奏。
- 來源措辭不一：香港稅務紀錄從交易完成起算，公司會計紀錄從財政年度結束起算，兩者不同；CPF 頁面對次月 14 日是到期日還是執法起點的用語不一。
- 日本軽減稅率頁面出現 2027 至 2029 年飲食料品的敘述，摘要被截斷，內容未確認。
- 日本 APPI 的條號在 2022 年修正後可能變動，本文不引條號。
- 台灣 2024 年修正的過渡期細節未取得。

## 來源

全部為官方頁面，查閱日期 2026-11-01。「文件日期」只填頁面上看得到的版本或日期，其餘以查閱日期為準。

| 代號 | 發布者與頁面 | 文件日期 |
| --- | --- | --- |
| HK1 | [財經事務及庫務局：Prevailing Tax Policy](https://www.fstb.gov.hk/en/treasury/general/prevailing-tax-policy.htm) | 未標示 |
| HK2 | [IRD：Record Keeping](https://www.ird.gov.hk/eng/tax/bus_rke.htm)、[Keeping Business Records 小冊子](https://www.ird.gov.hk/eng/pdf/51c_pam.pdf) | 未標示 |
| HK3 | [公司註冊處：Cap. 622 Part 9 要點](https://www.cr.gov.hk/en/companies_ordinance/docs/NewCO_C622_HL_Part9-e.pdf) | 未標示 |
| HK4 | [PCPD：Cap. 486 條例文本](https://www.pcpd.org.hk/english/files/pdpo.pdf) | 未標示 |
| HK5 | [PCPD：Recommended Model Contractual Clauses 指引](https://www.pcpd.org.hk/english/resources_centre/publications/files/guidance_model_contractual_clauses.pdf) | 2022-05-12 |
| HK6 | [積金局：Contribution Day](https://www.mpfa.org.hk/en/contribution-day)、[2026 供款日曆](https://www.mpfa.org.hk/en/-/media/files/mpf_system/mandatory_contributions/mpf_contribution_days_calendar/2026_contribution_days_calendar_eng.pdf) | 2026 年 |
| HK7 | [IRD：Employers](https://www.ird.gov.hk/eng/tax/ere.htm) | 2026-04-01 發出之 2026 年表格 |
| TW1 | [全國法規資料庫：營業稅法](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=G0340080)、[統一發票使用辦法](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=G0340082) | 現行條文 |
| TW2 | [財政部：電子發票上傳期限說明](https://www.mof.gov.tw/singlehtml/f48d641f159a4866b1d31c0916fbcc71?cntId=65b3f045d16d4c77bf0e39db0ca24c5e) | 未標示 |
| TW3 | [全國法規資料庫：商業會計法](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=J0080009) | 現行條文 |
| TW4 | [全國法規資料庫：個人資料保護法](https://law.moj.gov.tw/Eng/LawClass/LawAll.aspx?PCode=I0050021) | 現行條文 |
| TW5 | [eTax 入口：營業稅申報與繳稅](https://www.etax.nat.gov.tw/etwmain/en/cbec-tax-area/business-tax/taxation-system-intro/q-and-a/Gz6MjlP)、[營業稅法施行細則](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=G0340081) | 現行條文 |
| TW6 | [全國法規資料庫：所得稅法](https://law.moj.gov.tw/eng/LawClass/LawAll.aspx?PCode=G0340003) | 現行條文 |
| TW7 | [全國法規資料庫：勞工退休金條例](https://law.moj.gov.tw/ENG/LawClass/LawAll.aspx?pcode=N0030020)、[勞保局：提繳率](https://www.bli.gov.tw/en/0010797.html) | 現行條文 |
| SG1 | [IRAS：GST rate change 概覽](https://www.iras.gov.sg/taxes/goods-services-tax-%28gst%29/gst-rate-change/gst-rate-change-for-business/overview-of-gst-rate-change) | 未標示 |
| SG2 | [IRAS：GST InvoiceNow requirement](https://www.iras.gov.sg/taxes/goods-services-tax-%28gst%29/gst-invoicenow-requirement) | 未標示 |
| SG3 | [IRAS：Committee of Supply 2026 InvoiceNow 延伸](https://www.iras.gov.sg/news-events/newsroom/committee-of-supply-2026--extension-of-gst-invoicenow-requirement-to-all-gst-registered-businesses-by-april-2031) | 2026 年 |
| SG4 | [IRAS：GST keeping records](https://www.iras.gov.sg/taxes/goods-services-tax-%28gst%29/basics-of-gst/invoicing-price-display-and-record-keeping/keeping-records) | 未標示 |
| SG5 | [Singapore Statutes Online：Companies Act 1967](https://sso.agc.gov.sg/Act/CoA1967?ProvIds=P16-) | 現行條文 |
| SG6 | [PDPC：Data Protection Obligations](https://www.pdpc.gov.sg/overview-of-pdpa/the-legislation/personal-data-protection-act/data-protection-obligations) | 未標示 |
| SG7 | [CPF Board：CPF 繳納到期日](https://www.cpf.gov.sg/service/article/when-is-the-due-date-for-cpf-contributions) | 未標示 |
| SG8 | [IRAS：Auto-Inclusion Scheme](https://www.iras.gov.sg/taxes/individual-income-tax/employers/auto-inclusion-scheme-%28ais%29-for-employment-income) | 未標示 |
| JP1 | [NTA：消費稅の軽減稅率制度（No.6102）](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6102.htm) | 未標示 |
| JP2 | [NTA：適格請求書等保存方式小冊子](https://www.nta.go.jp/publication/pamph/shohi/shohizei_r07.pdf)、[No.6496](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6496.htm) | 令和7年6月 |
| JP3 | [NTA：帳簿書類等の保存期間（No.5930）](https://www.nta.go.jp/taxes/shiraberu/taxanswer/hojin/5930.htm) | 令和8年4月1日現在法令等 |
| JP4 | [NTA：適格請求書等の記載事項（No.6625）](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6625.htm) | 未標示 |
| JP5 | [PPC：APPI 英譯](https://www.ppc.go.jp/files/pdf/APPI_english.pdf) | 2020-06 版 |
| JP6 | [NTA：Withholding Tax Guide](https://www.nta.go.jp/publication/pamph/gensen/shikata_r05/pdf/16.pdf) | 令和5年版 |
| JP7 | [NTA：給与所得の源泉徴収票の提出範囲（No.7411）](https://www.nta.go.jp/taxes/shiraberu/taxanswer/hotei/7411.htm)、[令和7年分 法定調書の手引](https://www.nta.go.jp/publication/pamph/hotei/tebiki2025/PDF/all.pdf) | 令和7年9月1日現在法令 |
| JP8 | [NTA：電子取引関係（電子帳簿保存法）](https://www.nta.go.jp/law/joho-zeikaishaku/sonota/jirei/tokusetsu/01.htm) | 未標示 |
| EU1 | [EUR-Lex：Directive (EU) 2025/516](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025L0516) | 2025-03-11 |
| EU2 | [European Commission：eInvoicing](https://single-market-economy.ec.europa.eu/single-market/public-procurement/digital-procurement/einvoicing_en)、[ViDA implementation strategy](https://taxation-customs.ec.europa.eu/document/download/d5c72f2a-df00-473d-8f8a-5400b999e1aa_en?filename=Implementation+strategy.pdf) | 未標示 |
| EU3 | [EUR-Lex：Directive 2006/112/EC](https://eur-lex.europa.eu/eli/dir/2006/112/oj/eng)、[Commission：發票規則評估研究](https://taxation-customs.ec.europa.eu/system/files/2019-07/report_evaluation_invoicing_rules_vol1_en.pdf) | 研究 2019-07 |
| EU4 | [EDPB：International data transfers](https://www.edpb.europa.eu/sme/be-compliant/international-data-transfers_en)、[EUR-Lex：GDPR 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj) | 未標示 |
| EU5 | [European Commission：VAT returns](https://taxation-customs.ec.europa.eu/taxation/vat/vat-directive/vat-returns_en) | 未標示 |
| US1 | [trade.gov：Key U.S. Tax Considerations](https://www.trade.gov/sites/default/files/2022-07/Taxes2022.pdf)、[GAO-18-114](https://www.gao.gov/assets/gao-18-114.pdf)、[CRS：Consumption Taxes](https://www.congress.gov/crs-product/R44342) | trade.gov 2022-07；GAO 2018 |
| US2 | [Supreme Court：South Dakota v. Wayfair](https://www.supremecourt.gov/opinions/17pdf/17-494_j4el.pdf) | 2018-06-21 |
| US3 | [IRS：How long should I keep records?](https://www.irs.gov/businesses/small-businesses-self-employed/how-long-should-i-keep-records) | 未標示 |
| US4 | [IRS：Employment tax recordkeeping](https://www.irs.gov/businesses/small-businesses-self-employed/employment-tax-recordkeeping) | 未標示 |
| US5 | [Federal Register：28 CFR Part 202 最終規則](https://www.federalregister.gov/documents/2025/01/08/2024-31486/preventing-access-to-us-sensitive-personal-data-and-government-related-data-by-countries-of-concern) | 2025-01-08 |
| US6 | [California AG：CCPA](https://oag.ca.gov/privacy/ccpa) | 未標示 |
| US7 | [IRS：Publication 15 (2026)](https://www.irs.gov/publications/p15) | 2026 |
| US8 | [IRS：Employment tax due dates](https://www.irs.gov/businesses/small-businesses-self-employed/employment-tax-due-dates)、[SSA：W-2 deadlines](https://www.ssa.gov/employer/filingDeadlines.htm) | 未標示 |
