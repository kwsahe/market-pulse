@echo off
chcp 65001 >nul
setlocal

REM Keep every REM line in this file ASCII-only.
REM Under chcp 65001, cmd.exe misreads long lines full of multi-byte (Korean) text:
REM on 2026-10-18 it split a Korean comment and ran the tail fragment as a command
REM ("'da.' is not recognized ..."). It was harmless in a comment, but the same
REM split inside a command line could silently skip a step. Short Korean echo
REM lines are tested OK.
REM
REM Market Pulse daily collection batch, the unattended entry point for Task Scheduler.
REM
REM No pause at the end: an old trailing pause meant a human had to close the window,
REM so data was only collected on days someone double-clicked it (29 of 165 days, 17.6%).
REM To watch a manual run, use run_scraper.bat on the Desktop instead.
REM
REM Exit code: 0 = ok, 1 = any step failed. The scheduler and the alert read this value.

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

REM News collection is disabled.
REM news.naver.com/robots.txt is "User-agent: * / Disallow: /" (fully disallowed),
REM and scraper/news_scraper.py scrapes news.naver.com/section/105 directly.
REM That is a clear violation, not a gray area, so it cannot run unattended.
REM Bring it back here after switching to the Naver Developers search API.
REM   python -u scraper/news_scraper.py

echo [2/4] 가격 변동 분석 중...
python -u ml/price_change.py
if errorlevel 1 goto fail
echo.

REM Backup comes BEFORE verification.
REM The other order would skip the backup on exactly the days verification fails,
REM i.e. no copy of the day when something went wrong. Always keep it first.
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
REM Unattended run: nobody watches the console, so show the failure on screen.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\notify.ps1" -Title "Market Pulse 수집 실패" -Message "%date% %time% 배치가 실패했습니다. 로그: logs\last_run.log" -Level error
exit /b 1

REM -- Dead man's switch (optional) ----------------------------------------
REM A failure of this batch shows up in the exit code, but a day when the batch
REM never ran has no exit code at all: PC off or scheduler dead looks like silence.
REM An external watcher (healthchecks.io etc.) alerts when the ping does not arrive.
REM
REM To enable, put the check URL in env var MARKET_PULSE_HEALTHCHECK_URL.
REM If unset, this does nothing.
:ping_health
if not defined MARKET_PULSE_HEALTHCHECK_URL exit /b 0
curl -fsS -m 10 --retry 3 "%MARKET_PULSE_HEALTHCHECK_URL%%~1" >nul 2>&1
exit /b 0
