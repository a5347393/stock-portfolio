@echo off
echo ========================================
echo 股票追蹤 API 伺服器啟動
echo ========================================
echo.

echo 正在啟動 Flask API 服務...
echo 服務位址: http://localhost:5000
echo.
echo 按 Ctrl+C 可停止服務
echo ========================================
echo.

python api_server_fixed.py

pause
