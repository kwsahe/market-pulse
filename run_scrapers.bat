@echo off
chcp 65001 >nul
setlocal

REM Market Pulse 일일 수집 배치. 작업 스케줄러가 무인으로 호출하는 진입점이다.
REM
REM pause 를 두지 않는다 — 예전에는 마지막 줄의 pause 때문에 사람이 창을 닫아줘야 끝났고,
REM 그래서 손으로 더블클릭할 때만 수집이 됐다. 그 결과가 165일 중 29일(17.6%) 수집이다.
REM 사람이 직접 실행할 때 결과를 보고 싶으면 바탕화면의 run_scraper.bat 을 쓰면 된다.
REM
REM 종료코드: 0 = 정상, 1 = 어느 단계든 실패. 스케줄러와 알림이 이 값을 본다.

cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

echo ============================
echo Market Pulse 데이터 수집 시작
echo %date% %time%
echo ============================
echo.

echo [1/4] 가격 데이터 수집 중...
python -u scraper/price_scraper.py
if errorlevel 1 goto fail
echo.

REM 뉴스 수집은 중단 상태다.
REM news.naver.com/robots.txt 가 "User-agent: * / Disallow: /" 로 전면 금지인데
REM scraper/news_scraper.py 가 news.naver.com/section/105 를 직접 긁는다.
REM 회색지대가 아니라 명확한 위반이라, 무인 배치에 넣어둘 수 없다.
REM 네이버 개발자센터 검색 API로 교체한 뒤 이 자리에 되살린다.
REM   python -u scraper/news_scraper.py

echo [2/4] 가격 변동 분석 중...
python -u ml/price_change.py
if errorlevel 1 goto fail
echo.

REM 백업이 검증보다 **먼저** 온다.
REM 반대로 두면 검증이 실패한 날에 백업이 통째로 건너뛰어진다 — 정작 뭔가 잘못됐을 때
REM 그날치 사본이 안 남는다는 뜻이라 순서가 거꾸로다. 검증 결과와 무관하게 일단 남긴다.
echo [3/4] 백업 중...
python -u scripts/backup_db.py
if errorlevel 1 goto fail
echo.

echo [4/4] 수집 결과 검증 중...
python -u scripts/verify_last_scrape.py
if errorlevel 1 goto fail
echo.

echo ============================
echo 수집 완료! %date% %time%
echo ============================
call :ping_health ""
exit /b 0

:fail
echo.
echo ============================
echo [!] 수집 실패 — 위 로그를 확인하세요. %date% %time%
echo ============================
call :ping_health "/fail"
REM 무인 실행이라 콘솔을 보는 사람이 없다. 실패는 화면에 띄워서 알린다.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\notify.ps1" -Title "Market Pulse 수집 실패" -Message "%date% %time% 배치가 실패했습니다. 로그: logs\last_run.log" -Level error
exit /b 1

REM ── 데드맨 스위치 (선택) ──────────────────────────────────────────
REM 이 배치의 실패는 종료코드로 알 수 있지만, "배치가 아예 안 돈 날"은 종료코드조차 없다.
REM PC가 꺼져 있었거나 스케줄러가 죽으면 침묵과 정상이 구분되지 않는다.
REM 외부 관측자(healthchecks.io 등)를 두면 핑이 안 오는 것만으로 알림이 온다.
REM
REM 켜려면 환경변수 MARKET_PULSE_HEALTHCHECK_URL 에 체크 URL을 넣으면 된다.
REM 안 넣으면 아무 일도 하지 않는다.
:ping_health
if not defined MARKET_PULSE_HEALTHCHECK_URL exit /b 0
curl -fsS -m 10 --retry 3 "%MARKET_PULSE_HEALTHCHECK_URL%%~1" >nul 2>&1
exit /b 0
