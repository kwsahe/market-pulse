@echo off
echo ============================
echo Market Pulse 데이터 수집 시작
echo ============================
echo.
 
cd /d C:\Users\sangh\Desktop\Code\market-pulse
 
echo [1/2] 가격 데이터 수집 중...
python scraper/price_scraper.py
echo.
 
echo [2/2] 뉴스 데이터 수집 중...
python scraper/news_scraper.py
echo.
 
echo ============================
echo 수집 완료! %date% %time%
echo ============================