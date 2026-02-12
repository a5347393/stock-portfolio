# CHANGELOG - 股票績效追蹤器

## v2.0.0 (2026-02-12) — 全面優化版

### Phase 1: Bug 修復與安全性 (P0)

- **1.1** 修復 `updateGroupNamesInUI()` Element ID 不匹配：`filterGroup1~4` → `groupFilterName1~4`，改用 `textContent` 更新
- **1.2** 實作 `sortByColumn()` 函數：新增 `currentSortColumn` + `currentSortDir` 全域變數，支援表頭點擊排序，升降序切換
- **1.3** 修復 `updateChartPeriod()` 隱式 `event` 引用：HTML 改為 `onclick="updateChartPeriod('1mo', this)"`，函數簽名加 `el` 參數
- **1.4** 修復分組預設值不一致：`openEditModal()` 中 `'core'` → `'group1'`
- **1.5** 修復 `closeModal()` 一次關閉所有 Modal：改為只關閉當前 `.active` 的 Modal
- **1.6** XSS 防護強化：CSV 預覽、股票名稱、onclick handler 皆通過 `escapeHtml()` 處理
- **1.7** `importCSV()` 加入 try-catch-finally 確保 importBtn 在錯誤時恢復可用

### Phase 2: 效能與穩定性 (P1)

- **2.1** 修復 `setInterval` 記憶體洩漏：儲存 interval ID 至 `window._autoRefreshInterval`，`beforeunload` 時 `clearInterval`
- **2.2** Toast 堆積限制：最多同時 3 個 Toast，支援垂直堆疊，超出時移除最早的
- **2.3** `refreshPrices` 防並發：加入 `isRefreshing` flag，防止重複請求
- **2.4** API 錯誤處理強化：`fetchStockPrice()` 失敗時顯示 Toast 通知

### Phase 3: UX 增強 (P2)

- **3.1** 表格欄位排序指示器：CSS `th.sorted::after` 顯示 ▲/▼ 箭頭
- **3.2** 刪除確認優化：自訂確認 Modal 取代原生 `confirm()`，5 秒 Undo Toast 支援撤銷
- **3.3** 空狀態優化：SVG 圖示 + 引導文字 + CTA 按鈕
- **3.4** 數字動畫效果：`animateValue()` CountUp 漸變動畫，PnL 漲跌閃爍提示
- **3.5** Sparkline 繪製函數：`drawSparkline()` Canvas 繪製迷你走勢線（需搭配歷史數據 API）
- **3.6** 股票搜尋建議：`<datalist>` 自動完成，預載常見台美股代號

### Phase 4: 新功能 (P3)

- **4.1** 交易紀錄：新增交易紀錄區塊 + Modal，支援買入/賣出/手續費，localStorage + Firestore 同步
- **4.2** 股息追蹤：`dividendData` 資料結構，`getDividendYield()` 計算殖利率，`getTotalAnnualDividendIncome()` 年化股息收入
- **4.3** 目標價提醒：每支股票可設定上限/下限，到價時 Toast + Notification API 推播
- **4.4** 績效基準比較：`toggleBenchmark()` 切換 S&P 500 / 加權指數疊加（需搭配圖表數據）
- **4.5** XIRR 年化報酬率：Newton-Raphson 法實作，搭配交易紀錄計算
- **4.6** Watchlist 觀察名單：獨立觀察清單（不計入總市值），支援「想要買入價」提醒
- **4.7** 多帳戶支援：帳戶切換下拉選單 + 合併總覽模式，各帳戶獨立 portfolio
- **4.8** PWA 離線支援：`manifest.json` + `sw.js`，快取靜態資源 + API 回應，安裝提示

### Phase 5: 程式碼品質 (P4)

- **5.1** 無障礙性：所有 Modal 加入 `role="dialog"` + `aria-labelledby` + `aria-modal="true"`，按鈕加 `aria-label`，搜尋欄加 `<label class="sr-only">`
- **5.2** CSS 變數統一：圖表顏色移入 `:root` CSS 變數（`--chart-line`, `--chart-grid` 等），深色/淺色主題各自定義
- **5.3** 程式碼模組化：所有 JS 區塊加上 `// ========== SECTION NAME ==========` 標記

---

## 已知限制與後續可改善方向

1. **Sparkline 整合**：`drawSparkline()` 函數已就緒，需在 `renderPortfolio()` 中呼叫並傳入 7 天歷史數據（需 Local API 支援）
2. **基準比較圖表**：`toggleBenchmark()` 已建立，需在 `updatePortfolioChart()` 中加入第三條 dataset 顯示基準走勢
3. **股息欄位 UI**：殖利率計算邏輯完成，需在新增/編輯 Modal 加入「年化配息」輸入欄位
4. **Firestore 多帳戶**：目前多帳戶僅支援 localStorage，登入後需擴展 Firestore 路徑為 `users/{uid}/accounts/{accountId}/portfolio`
5. **PWA 圖示**：目前使用 SVG emoji 替代，正式上線建議提供 192x192 與 512x512 PNG 圖示
6. **XIRR 顯示**：計算邏輯完成，需在績效摘要區塊加入顯示欄位
7. **交易紀錄與持股同步**：可根據交易紀錄自動計算平均成本與持股數
8. **效能優化**：大量持股（>100支）時可考慮虛擬捲動 (virtual scrolling)

---

## 檔案結構

```
stock-portfolio-optimized.html  — 主應用（單一 HTML 檔）
manifest.json                   — PWA manifest
sw.js                           — Service Worker
CHANGELOG-stock-portfolio.md    — 本檔案
stock-portfolio-optimized.backup-20260212.html — 備份
```

---

## 版本歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| v2.0.0 | 2026-02-12 | 全面優化版：27+ 項修復與增強 |
| v1.0.0 | - | 原始版本 |
