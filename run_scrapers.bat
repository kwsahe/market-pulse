@echo off
echo ============================
echo Market Pulse 데이터 수집 시작
echo ============================
echo.

cd /d "%~dp0"

echo [1/3] 가격 데이터 수집 중...
python -u scraper/price_scraper.py
echo.

echo [2/3] 뉴스 데이터 수집 중...
python -u scraper/news_scraper.py
echo.

echo [3/3] 가격 변동 분석 중...
python -u ml/price_change.py
echo.

echo ============================
echo 수집 완료! %date% %time%
echo ============================
pause