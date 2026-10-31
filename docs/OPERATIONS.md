# Market Pulse 운영 문서

매일 자동 수집, 결과 검증, 백업, 환경변수, robots.txt 준수, 단일 주소 배포를 다룹니다.

[← README로 돌아가기](../README.md)

## 자동 수집 운영

수집은 Windows 작업 스케줄러가 **매일 09:10** 에 자동 실행한다.
예전에는 `run_scrapers.bat` 끝의 `pause` 때문에 사람이 창을 닫아줘야 끝나서, 손으로 더블클릭한 날만
수집이 됐다 — 그 결과가 164일 중 28일(17.1%, 2026-03-30~09-09) 수집이었다. 지금은 무인으로 돌고,
스케줄러를 붙인 2026-09-10부터는 52일 중 43일(82.7%) 수집됐다. 빠진 날은 모두 PC가 꺼져 있던 날이다.

```bash
# 등록 상태 확인 / 즉시 1회 실행 / 해제 (PowerShell)
Get-ScheduledTask -TaskName MarketPulse-DailyScrape
Start-ScheduledTask -TaskName MarketPulse-DailyScrape
Unregister-ScheduledTask -TaskName MarketPulse-DailyScrape -Confirm:$false
```

작업은 **창 없이** 돈다. 예전에는 실행될 때마다 콘솔 창이 떴고, 그 창을 닫으면 수집이 기록 없이
중간에 끊겼다(2026-10-11, CPU 수집 도중 종료). 지금은 창 없는 Python(`pythonw`)이 배치를
`CREATE_NO_WINDOW`로 띄우고 배치의 종료코드를 그대로 돌려준다 — 그래서 작업 스케줄러의
"마지막 실행 결과"가 실패를 계속 기록한다. (`conhost --headless`는 종료코드를 항상 0으로 돌려줘서 쓰지 않는다)
실행 결과는 `logs/last_run.log`에 남고, 실패하면 Windows 알림이 뜬다.

```powershell
# 작업을 다시 만들 때의 동작 설정
$arg = "-c `"import subprocess,sys; sys.exit(subprocess.call(['cmd.exe','/c',r'C:\Users\sangh\Desktop\run_scraper.bat','auto'], creationflags=0x08000000))`""
Set-ScheduledTask -TaskName MarketPulse-DailyScrape -Action (New-ScheduledTaskAction -Execute 'C:\Users\sangh\anaconda3\pythonw.exe' -Argument $arg)
```

배치는 5단계로 돈다. 1~4단계 중 하나라도 실패하면 종료코드 1로 끝난다.

| 단계 | 내용 |
|---|---|
| 1 | `scraper/price_scraper.py` — 가격 수집 (카테고리마다 검색 2페이지, 하루 22번 요청) |
| 2 | `ml/price_change.py` — 가격 변동 분석 |
| 3 | `scripts/backup_db.py` — 백업 (검증보다 먼저 — 검증이 실패한 날에도 그날치 사본을 남긴다) |
| 4 | `scripts/verify_last_scrape.py` — 수집 결과 검증 |
| 5 | `scripts/publish_demo.py` — 공개 데모 데이터 갱신 (검증을 통과한 날만. 실패해도 종료코드는 0이고 별도 알림만 띄운다) |

### 공개 데모 갱신 (`scripts/publish_demo.py`)

실제 API 응답을 JSON으로 떠서(`scripts/export_static_demo.py`) `demo-data` 브랜치에 커밋 하나로 강제 푸시하고,
Pages 배포 워크플로(`.github/workflows/pages.yml`)를 실행한다. 워크플로는 main 의 화면 코드와 `demo-data` 브랜치의
데이터로 빌드한다. 데이터를 main 에 커밋하지 않는 이유는 매일 데이터 커밋이 코드 이력을 묻고 저장소가 날마다 몇 MB씩
커지기 때문이다 — 커밋 하나를 덮어쓰면 이전 데이터는 남지 않는다.

푸시는 저장소 주인(`origin` 의 owner) 계정의 gh 로그인으로 한다. gh 기본 계정이 다른 계정이어도 되고, 그 계정
로그인이 없는 PC 에서는 아무것도 하지 않고 넘어간다. 손으로 돌리려면 `python scripts/publish_demo.py`,
푸시 없이 확인만 하려면 `--dry-run`. 내보내기·커밋에 약 2분 걸린다.

### 수집 검증 (`scripts/verify_last_scrape.py`)

`scrape_runs.status` 는 신뢰하지 않는다. 실측상 price 런 22회가 **전부** `success` 였고,
CPU 카테고리가 스마트폰·태블릿으로 오염된 런도, 0건 수집한 런 3개도 `success` 였다.
대신 결과 데이터의 형상을 본다 — 최신 날짜가 오늘인지, 직전 수집일에 있던 카테고리가 사라지지
않았는지, 카테고리별 행수가 급감(-40%)/급증(+100%) 하지 않았는지.

임계값 근거: 사고일을 뺀 149건의 카테고리별 전일 대비 변화율이 중앙값 0.9%, p90 5.1%, 최대 28.7%.
CPU 오염 사고는 -98.1% 였다.

### 백업 (`scripts/backup_db.py`)

`shutil.copy2` 로 백업하면 **안 된다**. WAL 모드에서는 최근 커밋이 `data.db` 본체가 아니라
`data.db-wal` 에 있어서, 본체만 복사한 백업은 조용히 비어 있다
(실측: 5,000행 커밋 직후 본체 4,096B, 복원 시 `no such table`).
`VACUUM INTO` 로 일관 스냅샷을 뜨고, gzip 한 뒤 **다시 풀어서 열어보는 것까지** 성공 조건에 넣었다.

```bash
python scripts/backup_db.py          # 오프사이트 폴더에 백업 + 7세대(일주일치) 회전
python scripts/backup_db.py --list   # 보관 목록
```

### 환경변수

| 이름 | 기본값 | 용도 |
|---|---|---|
| `MARKET_PULSE_DB_PATH` | `database/data.db` | DB 경로 |
| `MARKET_PULSE_BACKUP_DIR` | `~/OneDrive/market-pulse-backup` | 오프사이트 백업 폴더 |
| `MARKET_PULSE_FETCH_LAPTOP_DETAIL` | `0` (끔) | 노트북 상세 스펙 수집 (아래 참고) |
| `VITE_API_BASE_URL` | `http://localhost:8000` | 프론트가 호출할 API 주소 |
| `MARKET_PULSE_HEALTHCHECK_URL` | (없음) | 데드맨 스위치 핑 URL (아래 참고) |
| `MARKET_PULSE_READONLY` | `0` | `1`이면 워치리스트 쓰기 라우트를 등록하지 않는다 |
| `MARKET_PULSE_CORS_ORIGINS` | `localhost:5173` | 개발용 CORS 허용 오리진 (콤마 구분) |

### 데드맨 스위치 (선택, 아직 미설정)

배치 실패는 종료코드로 알 수 있지만 **배치가 아예 안 돈 날**은 종료코드조차 없다.
PC가 꺼져 있었거나 스케줄러가 죽으면 "침묵"과 "정상"이 구분되지 않는다 —
이 구성의 가장 그럴듯한 실패 유형이 정확히 그것이다.

외부 관측자를 두면 핑이 안 오는 것만으로 알림이 온다. [healthchecks.io](https://healthchecks.io)
무료 체크 1개를 만들고(grace 26시간 권장) 그 URL을 환경변수에 넣으면 켜진다.

```powershell
[Environment]::SetEnvironmentVariable('MARKET_PULSE_HEALTHCHECK_URL', 'https://hc-ping.com/<uuid>', 'User')
```

배치는 성공 시 그 URL로, 실패 시 `<URL>/fail` 로 핑을 보낸다. 환경변수가 없으면 아무 일도 하지 않는다.

계정 없이도 동작하는 감지 장치 두 개가 이미 붙어 있다 — 서로 다른 실패를 담당한다.

| 장치 | 잡는 실패 | 계정 |
|---|---|---|
| 헤더 신선도 배지 (`/api/health`) | 수집이 멈춘 채 며칠 지남 — 화면을 여는 순간 보인다 | 불필요 |
| Windows 토스트 (`scripts/notify.ps1`) | 배치가 돌았는데 실패 | 불필요 |
| healthchecks.io 핑 | **배치가 아예 안 돔** (PC 꺼짐·스케줄러 죽음) | 필요 |

앞의 둘로는 "PC가 꺼져 있던 날"을 못 잡는다. 그건 외부 관측자만 알 수 있다.

### robots.txt 준수

무인 배치로 매일 도는 이상, 명시된 금지 경로와 크롤 간격을 지킨다.

- **다나와 상세 스펙 수집이 기본 꺼져 있다.** `prod.danawa.com/robots.txt` 가 `/info/ajax/` 를
  금지하는데 스펙표·상세이미지가 전부 그 ajax 응답에만 있다(허용된 `/info/?pcode=` 페이지는
  ajax 호출 파라미터만 준다). 켜려면 `MARKET_PULSE_FETCH_LAPTOP_DETAIL=1`.
  AI 노트북(통합 메모리) 판정은 검색 결과 페이지의 스펙만으로 하므로 꺼져 있어도 매일 수집된다.
  이미 모은 노트북 상세 스펙·이미지는 보존된다.
- **뉴스 수집이 중단돼 있다.** `news.naver.com/robots.txt` 가 `Disallow: /` 전면 금지다.
  매일 배치와 LangGraph 워크플로우 양쪽에서 뺐고, 네이버 개발자센터 검색 API로 교체한 뒤 되살린다.
- 검색 요청 사이에 `Crawl-delay: 10` 을 지킨다(`search.danawa.com/robots.txt`).

---

## 단일 오리진 배포

FastAPI 하나가 API와 프론트 빌드(`frontend/dist`)를 **같은 출처**에서 서빙한다.
오리진이 하나면 CORS가 "설정할 것"이 아니라 "존재하지 않는 것"이 되고,
배포 산출물·도메인·인증 지점이 각각 하나로 줄어든다.

```bash
npm run build --prefix frontend      # 프론트 빌드 (먼저)
python scripts/serve_prod.py         # 읽기전용, http://127.0.0.1:8002
python scripts/serve_prod.py --writable   # 워치리스트 편집 허용 (로컬 전용)
```

### 읽기전용이 기본인 이유

워치리스트 쓰기 라우트(`POST /api/watchlist/{pcode}`, `PUT .../target`)에는 인증이 전혀 없다.
공개 URL에 그대로 노출하면 누구나 추적 목록과 목표가를 바꿀 수 있다.
인증을 새로 만드는 대신 **그 라우트를 등록하지 않는다** — 인증 코드 0줄로 노출면이 사라진다.

- 조회(`GET /api/watchlist`)는 무해하므로 남긴다. 통째로 빼면 SPA 폴백이 HTML을 돌려줘서
  프론트가 JSON 파싱 에러로 죽는다.
- 프론트도 `/api/health` 의 `readonly` 를 보고 편집 컨트롤을 감춘다(`useReadonly`).
- 확인: `curl -s localhost:8002/openapi.json` 의 쓰기 메서드가 0개여야 한다.

### 공개 URL (미설정 — 계정이 필요한 단계)

집 PC를 인터넷에 노출하는 터널이 필요하다. 둘 다 계정 로그인이 필요해서 자동 설정이 불가능하다.

**Tailscale Funnel** (도메인·인증서 불필요, 무료)

```powershell
winget install tailscale.tailscale
tailscale up                          # 브라우저에서 로그인
tailscale funnel 8002                 # https://<machine>.<tailnet>.ts.net
```

주의 — Funnel 호스트명은 TLS 인증서 발급과 함께 공개 Certificate Transparency 로그에 남아
스캐너가 열거할 수 있다. "URL을 안 알려주면 안전"은 성립하지 않으므로,
방어는 URL 은닉이 아니라 위의 읽기전용에 둔다.

가용성이 PC 가동률에 묶이므로, 포트폴리오처럼 남에게 보여줄 목적이면
도메인 + Cloudflare Tunnel + Access 쪽이 맞다.
