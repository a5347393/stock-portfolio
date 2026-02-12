# 股票績效統計網站

使用 yfinance API 的台美股投資組合追蹤系統，設計靈感來自 skillsmp.com。

## 功能特色

✨ **即時股價追蹤**
- 支援台股和美股
- 使用 Yahoo Finance API (yfinance)
- 自動每 60 秒更新

📊 **資產走勢圖表**
- 參考 skillsmp.com 的折線圖設計
- 支援 1個月、3個月、6個月、1年、2年視圖
- 顯示資產總值與成本基準線

📈 **績效統計**
- 總市值、總成本
- 總損益（金額 + 百分比）
- 報酬率計算

🎨 **極簡設計**
- 深色主題
- JetBrains Mono 等寬字體
- 綠色上漲 / 紅色下跌配色

## 安裝步驟

### 1. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 2. 啟動 API 服務

```bash
python api_server.py
```

服務將運行在 `http://localhost:5000`

### 3. 開啟網頁

用瀏覽器開啟 `stock-portfolio-v2.html`

## 使用方式

### 新增持股

1. 點擊「+ 新增持股」按鈕
2. 選擇市場（台股/美股）
3. 輸入股票代號
   - 台股：輸入代號即可（例如：2330）
   - 美股：輸入股票代碼（例如：AAPL）
4. 輸入持股數量
5. 輸入平均成本
6. 點擊「新增」

### 股票代號範例

**台股：**
- 2330 → 台積電
- 2454 → 聯發科
- 2317 → 鴻海

**美股：**
- AAPL → Apple
- TSLA → Tesla
- GOOGL → Google
- MSFT → Microsoft

### 查看資產走勢

- 點擊圖表上方的時間區間按鈕（1M, 3M, 6M, 1Y, 2Y）
- 圖表會顯示該期間的資產變化
- 綠線：資產總值
- 灰虛線：成本基準

### 更新報價

- 點擊「🔄 更新報價」手動更新
- 系統每 60 秒自動更新一次

## API 端點

### GET `/api/stock/<symbol>`
取得單一股票報價

### POST `/api/stocks/batch`
批次取得多支股票報價

```json
{
  "symbols": ["AAPL", "2330.TW", "TSLA"]
}
```

### GET `/api/indices`
取得主要指數（台股加權、S&P 500、Nasdaq、Dow Jones）

### GET `/api/history/<symbol>?period=1y`
取得股票歷史數據

### POST `/api/portfolio/history`
計算投資組合歷史價值

```json
{
  "holdings": [
    {"symbol": "AAPL", "shares": 10, "avgCost": 150},
    {"symbol": "2330.TW", "shares": 1000, "avgCost": 500}
  ],
  "period": "1y"
}
```

## 技術架構

### 後端
- **Flask** - Web 框架
- **yfinance** - Yahoo Finance API 客戶端
- **Flask-CORS** - 跨域支援

### 前端
- **HTML/CSS/JavaScript** - 純前端實現
- **Chart.js** - 圖表繪製
- **LocalStorage** - 本地數據儲存

## 資料儲存

所有持股資料儲存在瀏覽器的 LocalStorage，不會上傳到伺服器。

清除瀏覽器快取會刪除所有持股記錄。

## 注意事項

1. **API 限制**：yfinance 依賴 Yahoo Finance，可能有請求頻率限制
2. **台股代號**：系統會自動加上 `.TW` 後綴
3. **匯率**：台股和美股使用各自貨幣，需手動轉換
4. **數據延遲**：免費 API 可能有 15-20 分鐘延遲

## 故障排除

### API 無法連接

確認 Python 後端服務正在運行：
```bash
python api_server.py
```

### 股價無法更新

1. 檢查網路連線
2. 確認股票代號正確
3. 查看瀏覽器開發者工具的 Console 錯誤訊息

### 圖表無法顯示

確認至少有一支持股，並且已成功取得價格數據。

## 檔案說明

- `stock-portfolio-v2.html` - 主要網頁應用（整合版）
- `api_server.py` - Flask API 後端服務
- `requirements.txt` - Python 依賴套件
- `README.md` - 說明文件

## 未來功能

- [ ] 匯率自動轉換
- [ ] 支援更多市場（港股、陸股）
- [ ] 交易記錄功能
- [ ] 股息追蹤
- [ ] 資產配置分析
- [ ] 匯出報表（PDF/Excel）
- [ ] 多投資組合管理

## 授權

MIT License
