@echo off
echo ============================
echo Market Pulse 워크플로우 대시보드 실행
echo ============================
echo.

cd /d "%~dp0"

echo [Streamlit] 워크플로우 대시보드 시작...
echo 포트: http://localhost:8420
echo.
streamlit run workflow_dashboard/app.py --server.port 8420
echo.

echo ============================
echo 종료됨
echo ============================