@echo off
echo ============================
echo Market Pulse 데이터 분석 대시보드 실행
echo ============================
echo.

cd /d "%~dp0"

echo [Streamlit] 데이터 분석 대시보드 시작...
echo 포트: http://localhost:8010
echo.
streamlit run dashboard/app.py --server.port 8010
echo.

echo ============================
echo 종료됨
echo ============================