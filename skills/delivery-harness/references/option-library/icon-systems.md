# Icon 系統參考

Reference only · 2026-09-25。沒有強制 icon 套件。既有圖示、平台符號、自有 SVG、純文字都可選；不是每個按鈕都需要 icon。

## 先問的問題

圖示承載什麼語意？受眾能認出嗎？Web 還是 native？需要 outline、filled、duotone 或不同 weight？有多少業務專屬符號？是否要 RTL、多品牌、離線、SSR／RSC？是否允許外部 font 請求？授權要涵蓋哪些產品與交付方式？

## 候選比較

| 候選 | 來源能力／視覺方向 | 適用與避免條件（研究判斷） | 整合與遷移責任 |
| --- | --- | --- | --- |
| 既有圖示／純文字 | 保留使用者已學會的語意 | 已一致且能覆蓋需求時優先比較；只有装飾價值時可不放 icon | 盤點重複與缺漏，保留可存取名稱，無新增套件成本 |
| Lucide | SVG 與按需打包方向。[官方指南](https://lucide.dev/guide/) | 一致線條介面；若產品偏重填色或特殊品牌符號，先檢查缺口 | 核對 framework package、stroke 與 import；替換時逐項核對語意而非只對名稱 |
| Phosphor | 多種 weight，包含 fill／duotone；React 有 SSR 用法。[官方 React 專案](https://github.com/phosphor-icons/react) | 想以 weight 區分狀態或較豐富表達；不要任意混用 weight | 核對 `@phosphor-icons/react`、SSR export、context 差異與開發期 import 成本 |
| Heroicons | 提供多種尺寸／outline、solid 圖示。[官方入口](https://heroicons.com/) | 較精簡的常見 Web 功能；業務特殊符號先檢查覆蓋 | 與 Tailwind 沒有必選綁定；選對尺寸與 framework 路線，維持一致光學重量 |
| Tabler Icons | SVG，提供 framework packages、靜態檔及 webfont。[官方文件](https://docs.tabler.io/icons) | 希望比較較廣符號覆蓋與分發方式；不要為幾個圖示載入整套字型 | 核對按需 import、stroke、SVG／font 的載入差別與版本 |
| Material Symbols | 可變字型軸含 fill、weight、grade、optical size，亦有不同資產形式。[官方指南](https://developers.google.com/fonts/docs/material_symbols) | Material 語彙或需要光學尺寸調整；品牌不同時要測試匹配 | font subset／自託管／SVG 分開比較；失敗時不可露出 ligature 文字或讓按鈕失去名稱 |
| 平台原生符號 | 例如 Apple SF Symbols 與平台 UI 慣例。[Apple](https://developer.apple.com/sf-symbols/) | native App 需要平台一致性；不能假定資產可任意移到所有平台 | 核對 OS availability、平台條款、symbol variants 和 fallback；Web 替代另選 |
| 自有 SVG／品牌資產 | 可精確符合品牌與產品語意 | 有設計維護能力與授權來源；常見控制不必全部重畫 | 記錄 viewBox、stroke、命名、版本與清理；外部 SVG 需審查內容，不能把來路不明檔直接注入 DOM |

表格的用途判斷不是最佳排名。授權以採用時的確切套件／資產版本為準；品牌商標和平台符號不能沿用一般 icon package 的授權推定。圖示總數會變，本文不以數量決定品質。

## 選擇 SVG 還是字型

少量 UI controls 可比較按需 SVG，較容易控制單一圖示與顏色；大量既有 font icon 系統則先看 subset、快取、離線與載入失敗。SSR／RSC 元件路徑、tree-shaking、動態名稱載入可能影響 bundle，要用 production build 證明。圖示 font 與文字 font 不必綁在同一套。

## 三個情境

1. SaaS 後台：若已有 Lucide 且缺漏少，先保留；若需不同填色狀態，可比較 Phosphor 或現有 family 的 variants。不要只因某顆圖示好看引入整套第二家。
2. Material 風格的 App 與 Web：Material Symbols 可作候選；iOS 若採平台原生視覺，可另用 SF Symbols。共用的是「搜尋／返回／收藏」語意，不要求兩端 SVG 一模一樣。
3. 品牌 portfolio：介面導覽可用 Heroicons／Tabler 等候選，作品標誌使用自有合法資產；文案已清楚時，按鈕可只有文字。

## 驗證與維護

Icon-only button 要有名稱；裝飾圖示避免重複朗讀。核對按鈕 hit area、keyboard focus、disabled、loading、selected、dark mode、high contrast、RTL 與字級放大。不要把 glyph 尺寸當點擊區域，也不要只用 icon／顏色表達錯誤。

將產品語意對應到選定 glyph，可用現有元件集中管理少量實際使用圖示；不預造跨所有套件的抽象系統。遷移要比對缺漏、語意歧義、alignment、stroke 和 bundle，保留前後截圖。採用結論写入既有 ui-design／stack-decisions，並與 [元件](components-icons.md)、[CSS](css-styling.md) 分層記錄。
