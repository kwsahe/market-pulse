@echo off
echo ============================
echo Market Pulse API 서버 실행
echo ============================
echo.

cd /d "%~dp0"

echo [FastAPI] API 서버 시작...
echo 포트: http://localhost:8000
echo.
uvicorn api.main:app --reload --port 8000
echo.

echo ============================
echo 종료됨
echo ============================
