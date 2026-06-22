@echo off
echo ============================
echo Market Pulse 대시보드 실행
echo ============================
echo.

cd /d "%~dp0"

echo [Streamlit] 대시보드 시작...
echo http://localhost:8501
echo.
streamlit run workflow_dashboard/app.py
echo.

echo ============================
echo 종료됨
echo ============================