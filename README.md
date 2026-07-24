# 📊 Market Pulse

게이밍 노트북 & PC 부품 가격 자동 수집 · ML 분석 · **LangGraph 기반 자동 리포트** · IT 뉴스 대시보드

---

## 🚀 주요 기능

| 기능 | 설명 |
|------|------|
| **자동 데이터 수집** | 다나와 5 개 카테고리 + 네이버 뉴스 매일 자동 수집 |
| **LangGraph 워크플로우** | 체크포인트, 재시도, 상태 추적 가능한 자동화 파이프라인 |
| **실시간 대시보드** | 워크플로우 실행/모니터링 및 리포트 조회 (Streamlit) |
| **이상치 탐지** | Z-score · IQR 통계 기반으로 비정상 가격 감지 |
| **가격 변동 리포트** | 전날 대비 인상/인하 상품 자동 분석 |
| **가격 예측 (ML)** | 스펙 기반 Linear Regression / Random Forest |
| **트렌드 분석** | 카테고리별 평균가 추이 및 상승/하락 방향 |
| **자동 리포트 생성** | Markdown + HTML 형식으로 매일 자동 저장 |

---

## 📦 설치 방법

```bash
# 레포지토리 클론
git clone https://github.com/your-username/market-pulse.git
cd market-pulse

# 의존성 설치
pip install -r requirements.txt
```

---

## 🎮 사용 방법

### **1. 자동 리포트 생성 (추천)**

LangGraph 워크플로우로 한 번에 실행:

```bash
# Windows
run_workflow.bat

# 또는 직접
python workflow/main.py
```

**실행 흐름:**
1. DB 초기화
2. 가격 데이터 수집 (다나와)
3. 뉴스 데이터 수집 (네이버)
4. 가격 변동 분석
5. 이상치 탐지
6. 트렌드 분석
7. 리포트 생성 (Markdown + HTML)

**결과:**
- `reports/report_YYYYMMDD_HHMMSS.md`
- `reports/report_YYYYMMDD_HHMMSS.html`
- `workflow_checkpoints/` (중간 상태 저장)

---

### **2. 대시보드 실행**

두 가지 대시보드가 있습니다:

#### **A. 데이터 분석 대시보드** (실시간 조회)
수집된 데이터를 직접 조회하고 ML 분석 결과를 시각화합니다.

```bash
# Windows
run_data_dashboard.bat

# 또는 직접
streamlit run dashboard/app.py --server.port 8010
```
- **포트**: http://localhost:8010
- **용도**: 특정 상품 가격 추이 조회, 이상치 상세 분석, ML 예측 결과 확인
- **전제 조건**: `run_scrapers.bat` 로 데이터를 먼저 수집해야 함

#### **B. 워크플로우 제어 대시보드** (자동화)
워크플로우 실행, 리포트 생성 및 관리를 합니다.

```bash
# Windows
run_dashboard.bat

# 또는 직접
streamlit run workflow_dashboard/app.py --server.port 8020
```
- **포트**: http://localhost:8020
- **용도**: 자동 리포트 생성, 과거 리포트 조회, 워크플로우 상태 모니터링
- **전제 조건**: 별도 데이터 수집 불필요 (워크플로우가 자동 수행)

---

### **3. 기존 스크래퍼만 실행**

```bash
run_scrapers.bat
```
- **용도**: 데이터만 수집하고 분석/리포트는 수동으로 진행할 때
- **다음 단계**: `dashboard/app.py` 에서 데이터 조회

---

### **4. ML 분석만 실행**

```bash
# 이상치 탐지
python ml/anomaly_detection.py

# 가격 변동
python ml/price_change.py

# 가격 예측
python ml/price_prediction.py

# 트렌드 분석
python ml/trend_analysis.py
```

---

## 📊 수집 카테고리

| 카테고리 | 수집 항목 |
|---------|----------|
| 게이밍 노트북 | 가격, SSD 용량, 스펙, 이미지 |
| DDR5 RAM | 가격, 용량, 클럭, 타이밍 |
| NVMe SSD | 가격, 용량, 읽기/쓰기 속도 |
| 그래픽카드 | 가격, GPU 모델, VRAM |
| CPU | 가격, 코어 수, 클럭 |
| IT 뉴스 | 제목, 언론사, 발행시간 |

---

## 🏗️ 프로젝트 구조

```
market-pulse/
├── workflow/                 # LangGraph 워크플로우
│   ├── state.py             # 상태 정의 (TypedDict)
│   ├── nodes.py             # 각 단계 실행 함수
│   ├── graph.py             # 워크플로우 그래프 구성
│   ├── checkpoint.py        # 체크포인트 저장/복구
│   ├── report_generator.py  # 리포트 생성 (MD/HTML)
│   └── main.py              # 실행 진입점
├── workflow_dashboard/       # Streamlit 대시보드
│   └── app.py
├── workflow_checkpoints/     # 자동 생성: 중간 상태 저장
├── reports/                  # 자동 생성: 생성된 리포트
├── scraper/                  # 데이터 수집 스크래퍼
│   ├── price_scraper.py
│   └── news_scraper.py
├── database/                 # DB 관리
│   ├── db_manager.py
│   └── data.db
├── ml/                       # 머신러닝 분석
│   ├── anomaly_detection.py
│   ├── price_change.py
│   ├── price_prediction.py
│   └── trend_analysis.py
├── run_workflow.bat          # 워크플로우 실행
├── run_dashboard.bat         # 대시보드 실행
├── run_scrapers.bat          # 기존 스크래퍼 실행
└── requirements.txt
```

---

## 🔧 기술 스택

| 역할 | 도구 |
|------|------|
| **워크플로우** | LangGraph (StateGraph, 체크포인트) |
| **스크래핑** | requests, BeautifulSoup |
| **데이터 저장** | SQLite |
| **ML 분석** | scikit-learn, pandas, numpy, scipy |
| **대시보드** | Streamlit |
| **자동화** | Windows 작업 스케줄러 + bat |

---

## 📈 LangGraph 워크플로우 구조

```
init_db
   ↓
collect_prices ──┐
                 ├→ (병렬 실행 가능)
collect_news ────┘
   ↓
analyze_changes
   ↓
detect_anomalies
   ↓
analyze_trends
   ↓
generate_report
   ↓
finalize
```

**특징:**
- ✅ 각 단계 후 체크포인트 자동 저장
- ✅ 에러 발생 시 해당 단계에서 재시작 가능
- ✅ 상태 추적 및 모니터링
- ✅ 향후 병렬 실행/조건 분기 확장 가능

---

## 📝 예시 리포트

```markdown
# Market Pulse 리포트

**생성일:** 2026-06-22 15:17:33
**실행 ID:** 20260622_151733
**소요시간:** 24.4 초

## 📊 요약
- **가격 데이터:** 4886 개 (신규: 550 개)
- **뉴스 데이터:** 442 개 (신규: 28 개)
- **카테고리:** 게이밍 노트북, DDR5 RAM, NVMe SSD, 그래픽카드, CPU
- **총 상품:** 4886 개

## 📈 가격 변동 (327 개)
- **인상:** 191 개
- **인하:** 136 개

### TOP 5 인상
- **삼성 990 EVO Plus M.2NVMe (4TB)** (NVMe SSD)
  746,180 원 → 1,122,400 원 (+50.42%)
...
```

---

## 🔮 향후 계획

- [ ] 워크플로우 병렬 실행 최적화
- [ ] Slack/이메일 알림 통합
- [ ] LLM 기반 뉴스 요약 및 키워드 추출
- [ ] 가격 예측 모델 대시보드 연동
- [ ] 시계열 예측 (Prophet) 추가
- [ ] Docker 컨테이너화

---

## 📄 라이선스

MIT License

---

**Made with ❤️ by Market Pulse Team**