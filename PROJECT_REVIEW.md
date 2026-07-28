# Market Pulse 프로젝트 재파악 및 개선안

점검일: 2026-07-28

## 1. 현재 프로젝트 구조 요약

Market Pulse는 Danawa 가격 데이터와 Naver IT/과학 뉴스를 수집해 SQLite에 저장하고, Streamlit 대시보드와 LangGraph 기반 자동 리포트 워크플로우로 분석 결과를 보여주는 로컬 데이터 분석 프로젝트입니다.

현재 핵심 축은 다음과 같습니다.

- 수집: `scraper/price_scraper.py`, `scraper/news_scraper.py`, `scraper/laptop_detail_scraper.py`
- 저장: `database/db_manager.py`, `database/data.db`
- 분석/ML: `ml/anomaly_detection.py`, `ml/price_change.py`, `ml/trend_analysis.py`, `ml/price_prediction.py`
- 대시보드: `dashboard/app.py`, `dashboard/laptop_view.py`, `dashboard/theme.py`
- 자동 리포트: `workflow/`, `workflow_dashboard/`
- 실행 배치: `run_scrapers.bat`, `run_workflow.bat`, `run_dashboard.bat`, `run_data_dashboard.bat`

현재 DB 기준 데이터 규모는 다음과 같습니다.

- `prices`: 8,227건
- `news`: 706건
- 가격 카테고리: AI 노트북, CPU, DDR5 RAM, NVMe SSD, 게이밍 노트북, 그래픽카드
- 주요 테이블: `prices`, `news`, `laptop_products`, `laptop_specs`, `laptop_images`, `tracked_laptops`, `product_registry`

## 2. 현재 활용 중인 ML/분석

### 통계 기반 이상치 탐지

- 파일: `ml/anomaly_detection.py`
- 방식: Z-score, IQR
- 목적: 최신 수집일 기준 카테고리별 비정상 고가/저가 상품 탐지
- 성격: 학습 모델이 아니라 통계 규칙 기반 탐지

### 가격 변동 탐지

- 파일: `ml/price_change.py`
- 방식: 최신일과 직전일의 같은 상품명 가격 merge 후 변동액/변동률 계산
- 목적: 가격 인상/인하 상품 리포트
- 성격: pandas 기반 비교 분석

### 가격 추이 분석

- 파일: `ml/trend_analysis.py`
- 방식: 날짜/카테고리별 평균가 집계, 첫날/마지막날 비교
- 목적: 카테고리별 가격 방향성 요약
- 성격: 집계 분석

### 가격 예측

- 파일: `ml/price_prediction.py`
- 모델: `LinearRegression`, `RandomForestRegressor`
- 전처리: 정규식 기반 feature 추출, `StandardScaler`
- 평가: 최대 5-fold 교차검증, R2 score 비교
- 특징: 두 모델의 평균 R2를 비교해 더 좋은 모델을 자동 선택

## 3. 검증 결과

확인한 내용:

- `python -m compileall -q .` 통과
- 대시보드/워크플로우 주요 모듈 import는 통과
- DB 로딩 및 테이블 조회 정상
- Streamlit 실행 경고로 `use_container_width` deprecated 경고 확인
- 수집기 모듈은 import 시 실제 네트워크 수집이 시작되어 import 테스트가 타임아웃됨

## 4. 우선 수정 필요 사항

### P0. 수집기 import 부작용 제거

위치:

- `scraper/price_scraper.py:24`
- `scraper/price_scraper.py:286`
- `scraper/news_scraper.py:14`
- `scraper/news_scraper.py:43`

문제:

- `price_scraper.py`, `news_scraper.py`가 import되는 순간 `init_db()`와 네트워크 요청이 실행됩니다.
- 함수 테스트, 재사용, 워크플로우 통합, IDE 자동 import 시 예기치 않은 수집이 발생합니다.
- 실제로 `import scraper.price_scraper` 검증 중 네트워크 수집이 시작되어 타임아웃이 발생했습니다.

권장 수정:

- 수집 로직을 `main()` 또는 `collect_*()` 함수로 감싸기
- 파일 하단에만 `if __name__ == "__main__": main()` 배치
- 워크플로우에서는 subprocess 대신 함수 호출 또는 명시적 CLI 호출 중 하나로 통일

### P0. LangGraph edge 중복 정의 정리

위치:

- `workflow/graph.py:42-50`
- `workflow/graph.py:53-88`

문제:

- 같은 단계 연결을 일반 `add_edge()`와 `add_conditional_edges()`로 동시에 정의하고 있습니다.
- 그래프 실행 경로가 중복되거나 LangGraph 버전 변경 시 오류/중복 실행으로 이어질 수 있습니다.

권장 수정:

- 실패 분기 처리가 필요하면 conditional edge만 유지
- 단순 순차 실행이면 일반 edge만 유지하고 각 노드에서 실패 상태를 일관 처리
- 추천안: conditional edge만 남기고 일반 edge 제거

### P1. `requirements.txt` 누락 의존성 보완

위치:

- `requirements.txt`
- `dashboard/app.py:6`
- `generate_erd.py:1`
- `screenshots/take_screenshot.py:8`
- `screenshots/generate_architecture_png.py:2`

문제:

- `dashboard/app.py`는 `altair`를 직접 사용하지만 `requirements.txt`에 없습니다.
- `generate_erd.py`는 `matplotlib`을 사용하지만 의존성에 없습니다.
- 스크린샷/시각화 스크립트는 `playwright`, `Pillow`가 필요하지만 의존성에 없습니다.

권장 수정:

- 앱 필수 의존성과 개발/시각화 의존성을 분리
- 예: `requirements.txt`, `requirements-dev.txt`
- 최소 보완: `altair` 추가

### P1. Streamlit deprecated API 교체

위치:

- `dashboard/app.py:73`, `dashboard/app.py:113`, `dashboard/app.py:216`, `dashboard/app.py:345`, `dashboard/app.py:545`, `dashboard/app.py:638`, `dashboard/app.py:664`, `dashboard/app.py:760`, `dashboard/app.py:786`
- `dashboard/laptop_view.py:206`, `dashboard/laptop_view.py:208`, `dashboard/laptop_view.py:258`, `dashboard/laptop_view.py:271`, `dashboard/laptop_view.py:275`

문제:

- Streamlit 1.56.0에서 `use_container_width` 제거 예정 경고가 발생합니다.
- 2025-12-31 이후 제거 예정이라고 경고됩니다.

권장 수정:

- `use_container_width=True` -> `width="stretch"`
- `use_container_width=False` -> `width="content"` 또는 고정 width

### P1. DB 마이그레이션 체계 분리

위치:

- `database/db_manager.py:34`
- `database/db_manager.py:62`
- `database/db_manager.py:96`

문제:

- 테이블 생성과 ALTER TABLE이 `init_db()` 안에 누적되어 있습니다.
- 스키마 변경 이력이 명확하지 않고, 운영 중 마이그레이션 실패를 추적하기 어렵습니다.

권장 수정:

- `schema_migrations` 테이블 추가
- `migrations/001_initial.sql`, `002_laptop_tables.sql`처럼 SQL 파일 분리
- `init_db()`는 현재 스키마 적용 여부를 확인하고 필요한 마이그레이션만 실행

## 5. 기능 개선 과제

### 데이터 품질

- 가격 unique key가 `(date, product)` 중심이라 상품명 변경/variant 변경에 취약합니다.
- `product_registry`가 생겼으므로 가격 변동 비교도 `product`보다 `pcode` 또는 `internal_code` 중심으로 이동하는 것이 좋습니다.
- Danawa HTML 클래스 변경에 대비해 파서 실패율/수집 건수 급감 알림을 추가하는 것이 좋습니다.

### 수집 안정성

- `requests.Session()` 재사용
- retry/backoff 적용
- 요청 실패와 파싱 실패를 분리 기록
- 수집 결과를 `scrape_runs` 테이블에 저장
- 카테고리별 수집 성공/실패 건수 기록

### ML 개선

- 현재 가격 예측은 정규식 feature 품질에 크게 의존합니다.
- 모델 평가 시 데이터 누수 가능성이 있습니다. 같은 상품의 날짜별 가격이 train/test에 섞이면 R2가 과대평가될 수 있습니다.
- 개선안:
  - `GroupKFold`를 사용해 동일 상품이 train/test에 동시에 들어가지 않도록 분리
  - 브랜드, 제조사, pcode, 출시일, 최저가 이력, 최근 변동률 feature 추가
  - 모델 저장/로드 구조 추가: `models/{category}.joblib`
  - 예측 정확도와 실제 오차를 대시보드에 누적 표시

### 대시보드 UX

- `dashboard/app.py`가 700줄 이상으로 비대합니다.
- 탭별 렌더링을 모듈로 분리하는 것이 좋습니다.
- 추천 분리:
  - `dashboard/tabs/overview.py`
  - `dashboard/tabs/category.py`
  - `dashboard/tabs/changes.py`
  - `dashboard/tabs/anomalies.py`
  - `dashboard/tabs/prediction.py`
  - `dashboard/tabs/news.py`

### 워크플로우

- 현재 `workflow/nodes.py`는 수집기를 subprocess로 실행합니다.
- 함수 호출 기반으로 바꾸면 테스트, 오류 처리, 로그 수집이 쉬워집니다.
- 체크포인트는 최종 상태 저장 중심이라 README의 “각 단계 체크포인트” 설명과 차이가 있습니다.
- 각 노드 종료 후 checkpoint를 저장하도록 개선하는 것이 좋습니다.

### 문서/인코딩

- 터미널에서 README와 일부 주석이 깨져 보입니다.
- 파일 자체가 UTF-8이어도 Windows 콘솔 출력이 CP949/UTF-8 설정에 따라 깨질 수 있습니다.
- 실행 배치에 `chcp 65001`을 추가하고, README 한글이 실제로 깨진 상태인지 별도 확인/복구하는 것이 좋습니다.

## 6. 추천 작업 순서

1. 수집기 import 부작용 제거
2. LangGraph edge 중복 제거
3. `requirements.txt`에 `altair` 추가 및 dev 의존성 분리
4. Streamlit `use_container_width` 교체
5. 가격 변동 기준을 `product`에서 `pcode/internal_code`로 전환
6. DB migration 체계 도입
7. 대시보드 탭 모듈 분리
8. ML 평가를 `GroupKFold` 기반으로 개선
9. 수집 실행 이력/실패 로그 테이블 추가

## 7. 바로 적용하면 좋은 최소 패치 범위

첫 번째 패치로는 다음 네 가지를 묶는 것을 추천합니다.

- `price_scraper.py`, `news_scraper.py`에 `main()` 도입
- `workflow/graph.py`의 일반 edge 제거
- `requirements.txt`에 `altair` 추가
- Streamlit deprecated API 일부 또는 전체 교체

이 범위는 기능 추가보다 안정화 성격이 강하고, 기존 DB 데이터를 건드리지 않아 위험도가 낮습니다.

## 8. 추가할 만한 기능 제안

### 8.1 바로 체감되는 기능

#### 관심 상품 가격 알림

- 설명: 사용자가 특정 상품을 추적 대상으로 등록하고, 목표가 이하로 내려가면 대시보드/리포트에서 알림 표시
- 활용 테이블: `tracked_laptops`, `prices`, `product_registry`
- 기대 효과: 단순 가격 조회에서 “구매 타이밍 추천 도구”로 발전
- 구현 난이도: 낮음

구현 아이디어:

- `tracked_laptops`에 `target_price`, `memo`, `notify_enabled` 컬럼 추가
- 최신가가 목표가 이하이면 대시보드 상단에 알림 카드 표시
- 자동 리포트에 “목표가 도달 상품” 섹션 추가

#### 가격 히스토리 상세 페이지 강화

- 설명: 상품 상세 페이지에서 최저가, 최고가, 평균가, 최근 7일 변동률, 최저가 날짜 표시
- 기대 효과: 상품별 가격 판단이 쉬워짐
- 구현 난이도: 낮음

추가 지표:

- 현재가
- 전체 기간 최저가/최고가
- 최근 7일/30일 평균가
- 현재가가 최저가 대비 몇 % 높은지
- 가격 변동 그래프

#### CSV/Excel 리포트 다운로드

- 설명: 대시보드에서 카테고리별 가격표, 가격 변동표, 이상치 목록을 Excel로 다운로드
- 기대 효과: 발표 자료, 보고서, 개인 기록으로 재사용 쉬움
- 구현 난이도: 낮음

권장 파일:

- `market_pulse_latest_prices.xlsx`
- `market_pulse_price_changes.xlsx`
- `market_pulse_anomalies.xlsx`

#### 상품 비교 기능

- 설명: 사용자가 2~5개 상품을 선택해 가격, 스펙, 최저가 이력, 예측가를 나란히 비교
- 기대 효과: 구매 의사결정에 직접 도움
- 구현 난이도: 중간

비교 항목:

- 현재가
- 최저가
- 가격 변동률
- 주요 스펙
- ML 예측 적정가
- 예측가 대비 고평가/저평가 여부

### 8.2 분석/ML 고도화 기능

#### 적정가 점수

- 설명: 실제 가격과 ML 예측 가격, 최근 최저가, 카테고리 평균가를 조합해 0~100점의 구매 매력도 산출
- 기대 효과: “싸다/비싸다”를 직관적인 점수로 표현 가능
- 구현 난이도: 중간

예시 공식:

- 예측가 대비 저렴할수록 가점
- 최근 30일 최저가에 가까울수록 가점
- 가격 하락 추세면 가점
- 이상치 고가로 탐지되면 감점

#### 가격 하락 가능성 예측

- 설명: 최근 가격 흐름, 변동 빈도, 상품 카테고리, 현재가 위치를 기반으로 며칠 내 가격 하락 가능성을 예측
- 기대 효과: “지금 살지 기다릴지” 판단 지원
- 구현 난이도: 높음

초기 버전:

- 규칙 기반으로 시작
- 최근 7일 상승률이 높고 현재가가 30일 평균보다 높으면 “기다림 추천”
- 현재가가 30일 최저가 근처면 “구매 검토”

고도화 버전:

- 분류 모델 사용
- target: 향후 7일 내 3% 이상 하락 여부
- 모델 후보: Logistic Regression, Random Forest, Gradient Boosting

#### 상품 클러스터링

- 설명: 스펙이 비슷한 상품끼리 자동으로 그룹화
- 기대 효과: 비슷한 제품군 안에서 가성비 비교 가능
- 구현 난이도: 중간

활용 예:

- RTX 5080 노트북끼리 묶기
- DDR5 32GB 6000MHz 제품끼리 묶기
- NVMe 1TB PCIe 4.0 제품끼리 묶기

모델 후보:

- KMeans
- DBSCAN
- cosine similarity 기반 유사 상품 검색

#### 뉴스 기반 시장 이벤트 태깅

- 설명: IT 뉴스 제목에서 GPU, CPU, RAM, SSD, AI PC 등 키워드를 추출해 가격 변동과 연결
- 기대 효과: 가격 변동 원인을 설명하는 리포트 가능
- 구현 난이도: 중간

초기 구현:

- 키워드 사전 기반 태깅
- 예: NVIDIA, RTX, 메모리, NAND, DRAM, 환율, 출시, 품절

고도화:

- TF-IDF 키워드 추출
- LLM 기반 뉴스 요약
- 뉴스 이벤트와 카테고리 가격 변동 상관 분석

### 8.3 대시보드 기능

#### 구매 후보 보드

- 설명: 관심 상품을 “관심”, “비교 중”, “구매 대기”, “구매 완료” 상태로 관리
- 기대 효과: 가격 추적 앱에서 개인 구매 관리 앱으로 확장
- 구현 난이도: 중간

필요 테이블:

- `watchlist_items`
- `watchlist_status`
- `watchlist_notes`

#### 필터 프리셋 저장

- 설명: 사용자가 자주 쓰는 필터 조건을 저장
- 예: “RTX 5090 노트북 500만원 이하”, “NVMe 2TB”, “DDR5 32GB”
- 기대 효과: 반복 조회 편의성 향상
- 구현 난이도: 중간

#### 가격 변동 타임라인

- 설명: 날짜별로 어떤 상품이 크게 오르고 내렸는지 타임라인 형태로 표시
- 기대 효과: 시장 흐름을 빠르게 파악 가능
- 구현 난이도: 낮음~중간

표시 예:

- 2026-07-28: NVMe SSD 12개 하락, CPU 8개 상승
- 최대 하락 상품 TOP 5
- 최대 상승 상품 TOP 5

#### 모바일 보기 최적화

- 설명: Streamlit 대시보드의 카드/탭/이미지 레이아웃을 모바일 화면에 맞게 조정
- 기대 효과: 휴대폰에서 가격 확인 가능
- 구현 난이도: 중간

### 8.4 자동화/운영 기능

#### 수집 실행 이력 대시보드

- 설명: 매 수집마다 성공/실패, 수집 건수, 신규 저장 건수, 소요 시간을 기록하고 시각화
- 기대 효과: 크롤러 장애를 빠르게 파악 가능
- 구현 난이도: 중간

필요 테이블:

- `scrape_runs`
- `scrape_run_details`

기록 항목:

- run_id
- started_at, finished_at
- source
- category
- fetched_count
- inserted_count
- skipped_count
- error_message

#### 자동 백업

- 설명: `database/data.db`와 `reports/`를 날짜별로 백업
- 기대 효과: DB 손상이나 수집 오류 발생 시 복구 쉬움
- 구현 난이도: 낮음

백업 예:

- `backups/data_20260728.db`
- `backups/reports_20260728.zip`

#### 오류 알림

- 설명: 수집 실패, 수집 건수 급감, DB 오류 발생 시 알림 표시
- 기대 효과: 조용히 데이터가 끊기는 문제 방지
- 구현 난이도: 중간

알림 채널 후보:

- Streamlit 대시보드
- HTML 리포트
- 이메일
- Slack/Discord Webhook
- Telegram

### 8.5 리포트 기능

#### 일간 요약 카드

- 설명: 매일 자동 리포트 맨 위에 핵심 숫자만 요약
- 기대 효과: 리포트 가독성 향상
- 구현 난이도: 낮음

요약 항목:

- 신규 수집 상품 수
- 가격 상승/하락 상품 수
- 목표가 도달 상품 수
- 이상치 수
- 가장 많이 하락한 상품
- 가장 많이 상승한 카테고리

#### 주간/월간 리포트

- 설명: 일간 리포트 외에 주간/월간 가격 흐름을 자동 생성
- 기대 효과: 장기 추세 파악 가능
- 구현 난이도: 중간

포함 내용:

- 카테고리별 평균가 변화
- 주간 최대 하락 상품
- 최저가 갱신 상품
- 가격 변동이 큰 카테고리
- 뉴스 키워드 TOP 10

#### HTML 리포트 시각화 강화

- 설명: 현재 HTML 리포트에 차트와 표 스타일을 강화
- 기대 효과: 공유 가능한 보고서 품질 향상
- 구현 난이도: 중간

추가 요소:

- 가격 변화 bar chart
- 카테고리별 추이 line chart
- 이상치 table
- 구매 추천 상품 card

### 8.6 데이터 확장 기능

#### 판매처/몰 정보 수집

- 설명: 상품 가격뿐 아니라 최저가 판매처, 배송비, 카드 할인 여부까지 저장
- 기대 효과: 실제 구매 비용 계산 가능
- 구현 난이도: 높음

필요 데이터:

- mall_name
- base_price
- shipping_fee
- card_discount
- final_price
- stock_status

#### 환율/반도체 가격 지표 연동

- 설명: USD/KRW 환율, DRAM/NAND 가격 지표를 함께 저장
- 기대 효과: PC 부품 가격 변동 원인 분석 가능
- 구현 난이도: 중간~높음

활용 예:

- 환율 상승 후 GPU 가격 상승 여부 분석
- NAND 가격 하락과 SSD 가격 하락의 시차 분석

#### 다나와 외 가격 소스 추가

- 설명: 네이버 쇼핑, 쿠팡, 11번가 등 다른 가격 소스와 비교
- 기대 효과: 특정 사이트 편향 감소
- 구현 난이도: 높음

주의 사항:

- 사이트별 이용 약관 확인 필요
- 파서 구조를 source별 adapter로 분리하는 것이 좋음

## 9. 기능 추가 우선순위 추천

가장 먼저 추가할 기능은 다음 순서를 추천합니다.

1. 관심 상품 목표가 알림
2. 상품 상세 가격 히스토리 강화
3. 가격 변동 기준을 `pcode/internal_code`로 전환
4. 수집 실행 이력 저장
5. 적정가 점수
6. 상품 비교 기능
7. 주간/월간 리포트
8. 뉴스 키워드와 가격 변동 연결

이 순서가 좋은 이유는 기존 DB 구조와 대시보드를 가장 적게 흔들면서도 사용자 체감 가치가 빠르게 커지기 때문입니다.
