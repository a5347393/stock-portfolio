# Changelog — Stock Portfolio Performance Tracker

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- 鍵盤快捷鍵增強（T 切換主題、C 切換貨幣、/ 聚焦搜尋）
- 匯率警示功能（設定目標匯率、到價通知）
- 股票價格警示（個股目標價、到價通知）
- 圖表互動增強（點擊、縮放、詳細視圖）
- 交易記錄系統
- 進階績效指標（夏普比率、最大回撤）
- PWA 支援（離線使用、安裝到桌面）

---

## [2026-02-06] — Bug 修復 & 短期優化

### Fixed
- **未定義函數引用**：Firestore 同步回調中 `refreshAllPrices()` → `refreshPrices()`，`renderTable()` → `renderPortfolio()`（共 4 處）
- **stockGroups 未初始化**：新增 `let stockGroups = JSON.parse(localStorage.getItem('stockGroups')) || {}` 防止 Firestore 同步分組時 ReferenceError
- **記憶體洩漏**：新增 `unsubscribeGroupSettings` / `unsubscribeStockGroups` 追蹤 Firestore listeners；登出、重複呼叫、頁面卸載時正確清除；新增 `beforeunload` 清理所有 listeners 和 Chart.js 實例
- **ID 型別不一致**：`editStock()` 從 `parseInt()` 改為 `Number()`；`deleteStock()` / `openEditModal()` 統一使用 `Number()` 比較；CSV 匯入 ID 從浮點數改為整數

### Added
- **搜尋防抖（Debounce）**：新增通用 `debounce()` 工具函數，搜尋輸入延遲 300ms 觸發篩選
- **圖表增量更新**：主題切換時改為只更新顏色後呼叫 `chart.update('none')`，消除切換卡頓
- **指數批次請求**：後端 `/api/indices` 改為 `yf.Tickers()` 一次批次抓取，含快取和 fallback
- **新聞 XSS 防護**：新增 `escapeHtml()` 和 `sanitizeUrl()` 函數，全面防護新聞內容
- **CDN SRI 完整性校驗**：Chart.js 和 Firebase SDK CDN 標籤加上 `integrity` 和 `crossorigin`
- **手機底部導航實際切換**：`switchMobileView()` 實作區塊顯示/隱藏；新增完整設定頁面；新增 `resize` 監聽從手機切回桌面時恢復所有區塊

---

## [2026-01-25] — 功能擴充

### Added
- **股票新聞整合**：美股用 yfinance `.news`，台股用 Google News RSS；`/api/news/<symbol>` 和 `/api/news/batch` 端點；30 分鐘快取；相對時間顯示；前端新聞 Modal
- **自訂分組名稱**：可自訂 4 個分組名稱（預設：組別1-4）；分組設定 modal；LocalStorage 持久化；動態更新所有 UI 元素
- **手機版 API 連接修復**：伺服器綁定改為 `0.0.0.0`；前端動態使用 `window.location.hostname`
- **手機底部導航（初版）**：3-tab 底部導航（持股/圖表/設定）
- **下拉刷新**：Touch-based pull-to-refresh with visual feedback
- **持股熱力圖**：依績效顯示背景漸層（>10% 亮綠 / 0–10% 淡綠 / -10%–0 淡紅 / <-10% 亮紅）
- **趨勢箭頭指示器**：↗ 漲 / ↘ 跌 / → 持平，含脈衝動畫
- **股票分組系統**：4 個預設分組（核心/成長/配息/投機）；Color-coded badges；分組過濾按鈕；LocalStorage 持久化
- **深色/淺色主題切換**：CSS 變數切換；LocalStorage 持久化；平滑動畫過渡；圖表同步更新

### Fixed
- **資產走勢圖表貨幣轉換**：後端分別追蹤 TW/US 持股價值；前端依選擇貨幣正確換算
- **JavaScript 初始化流程**：元素存在性檢查；完整 try-catch；`updateGroupNamesInUI()` 導致中斷問題修復
- **所有 modal 關閉機制**：背景點擊、Esc 鍵、統一關閉函數

---

## [2026-01-24] — 優化與新功能

### Added
- **編輯持股功能**：編輯 modal（持股數/成本預填）；台股固定 TWD 顯示、美股固定 USD
- **批次 API 優化**：`yf.Tickers()` 同時請求，速度提升 5–10×；智慧快取；fallback 機制
  - 5 支：~3s → ~1s　｜　10 支：~6s → ~1–2s　｜　20 支：~12s → ~2–3s
- **CSV 批次匯入**：檔案選擇 modal；CSV 解析與驗證；預覽功能；重複偵測（⚠️）；範本下載
- **搜尋功能**：即時股票搜尋
- **市場過濾器**：All / TW / US 切換
- **排序系統**：8 種排序選項
- **CSV 匯出**：UTF-8 BOM 格式
- **Loading skeleton screens**：載入動畫
- **Toast 通知系統**
- **鍵盤快捷鍵**：N 新增、R 刷新、Esc 關閉

### Fixed
- **Yahoo Finance 429 錯誤**：改用 `.history()` 方法；period 從 2d 改為 5d；500ms 請求間隔；graceful fallback

---

## [2026-01-23] — v3 匯率與圖表

### Added
- **USD/TWD 匯率 API**：即時匯率顯示於 header
- **多幣別支援**：TWD/USD 切換按鈕；自動換算所有持股
- **資產配置圓餅圖**：含色彩圖例，Chart.js 實作
- **兩欄圖表佈局**：資產走勢 + 圓餅圖並排
- **響應式設計**：桌面/手機自適應

---

## [2026-01-22] — v2 圖表版

### Added
- **資產走勢圖**：skillsmp.com 風格折線圖，Chart.js 實作
- **時間區間選擇**：1M / 3M / 6M / 1Y / 2Y
- **Portfolio 歷史計算**：以成本為基準線

---

## [2026-01-21] — v1 基礎版

### Added
- **股票表格**：即時報價追蹤（台股/美股）
- **大盤指數**：台股加權、S&P 500、Nasdaq、Dow Jones
- **新增/刪除持股**：支援 TW / US 市場
- **績效統計**：總市值、成本、損益、報酬率
- **自動刷新**：60 秒間隔
- **深色主題**：等寬字型、極簡美學
- **Flask 後端**：yfinance API 整合；`/api/stocks`、`/api/indices`、`/api/portfolio/history` 端點
