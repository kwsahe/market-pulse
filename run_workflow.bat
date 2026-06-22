@echo off
echo ============================
echo Market Pulse 워크플로우 실행
echo ============================
echo.

cd /d "%~dp0"

echo [LangGraph] 워크플로우 시작...
python -u workflow/main.py
echo.

echo ============================
echo 완료! %date% %time%
echo ============================
pause