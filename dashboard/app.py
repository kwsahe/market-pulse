# dashboard/app.py
# 게이밍 노트북 & PC 부품 가격/스펙 + 이상치 + 가격변동 + 뉴스 대시보드
# 실제 렌더링 로직은 dashboard/tabs/*.py에 있고, 이 파일은 데이터 로딩 + 조립만 담당한다.

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import dashboard.laptop_view as laptop_view
from dashboard.theme import inject_css, hero_header, stat_cards, section_header, CYAN, RED, GREEN, AMBER
from dashboard.tabs import product_detail, alerts, spotlights, search
from dashboard.tabs import overview, category, changes, anomalies, prediction, compare, scrapes, news
from dashboard.tabs.common import (
    load_prices_cached, load_news_cached, detect_zscore_cached, detect_iqr_cached, detect_price_changes_cached,
)

# ============================
# 페이지 설정
# ============================
st.set_page_config(page_title="Market Pulse", page_icon="📊", layout="wide")
inject_css()

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
today_kr = datetime.now()
today_label = f"{today_kr.strftime('%Y.%m.%d')} ({WEEKDAY_KR[today_kr.weekday()]})"

hero_header(
    "Market Pulse",
    "RTX5080 / RTX5090 게이밍 노트북 & PC 부품 가격 추적 · ML 분석 · IT 뉴스 대시보드",
    date_label=today_label,
    icon="📊",
)

prices_df = load_prices_cached()
news_df = load_news_cached()

# 현재가 표시용 — 최신 수집일의 데이터만 사용
if not prices_df.empty:
    latest_date = prices_df["date"].max()
    current_df = prices_df[prices_df["date"] == latest_date].copy()
else:
    current_df = pd.DataFrame()

# 링크로 열린 상품(?code=RAM-1 등) 상세정보 — 있으면 그 상품 페이지만 단독으로 보여주고 나머지는 생략
linked_code = st.query_params.get("code")
if linked_code and not current_df.empty:
    product_detail.render(prices_df)
    st.stop()

# ML 분석 (최신 데이터 기준)
z_anomalies = detect_zscore_cached(current_df) if not current_df.empty else pd.DataFrame()
iqr_anomalies = detect_iqr_cached(current_df) if not current_df.empty else pd.DataFrame()

anomaly_products = set()
if not z_anomalies.empty:
    anomaly_products.update(z_anomalies["product"].tolist())
if not iqr_anomalies.empty:
    anomaly_products.update(iqr_anomalies["product"].tolist())

# 가격 변동 감지
price_change_result = detect_price_changes_cached() if not prices_df.empty else pd.DataFrame()
has_changes = isinstance(price_change_result, tuple)
if has_changes:
    changed_df, latest_date, prev_date = price_change_result
    up_count = len(changed_df[changed_df["change"] > 0]) if not changed_df.empty else 0
    down_count = len(changed_df[changed_df["change"] < 0]) if not changed_df.empty else 0
else:
    changed_df = pd.DataFrame()
    prev_date = None
    up_count = 0
    down_count = 0

# ============================
# 상단 알림 배너
# ============================
alerts.render_tracked_drop_alert(current_df, changed_df, has_changes)
alerts.render_target_reached_alert(current_df)

# ============================
# 상단 요약
# ============================
z_count = len(z_anomalies) if not z_anomalies.empty else 0
stat_cards([
    {"icon": "📦", "label": "상품", "value": f"{len(current_df)}개"},
    {"icon": "📂", "label": "카테고리", "value": f"{current_df['category'].nunique() if not current_df.empty else 0}개"},
    {"icon": "💰", "label": "평균가", "value": f"{current_df['price'].mean():,.0f}원" if not current_df.empty else "-", "color": CYAN},
    {"icon": "📈", "label": "인상", "value": f"{up_count}개", "color": RED},
    {"icon": "📉", "label": "인하", "value": f"{down_count}개", "color": GREEN},
    {"icon": "⚠️", "label": "이상치", "value": f"{z_count}개", "color": AMBER, "accent": z_count > 0},
])

st.divider()

# ============================
# 오늘의 하이라이트: 변동폭 TOP + 주목할 만한 상품 (자동 순환 카드)
# ============================
spotlights.render_top_movers(current_df, changed_df, has_changes)
spotlights.render_notable_products(current_df, z_anomalies)

# ============================
# 전체 상품 검색
# ============================
search.render(current_df)

# ============================
# 탭 구성
# ============================
if not prices_df.empty:
    categories = prices_df["category"].unique().tolist()
    tab_icons = {
        "게이밍 노트북": "💻", "DDR5 RAM": "🧩",
        "NVMe SSD": "💾", "그래픽카드": "🎮", "CPU": "⚡", "AI 노트북": "🧠"
    }
    tab_labels = (
        ["📋 전체"]
        + [f"{tab_icons.get(c, '🔧')} {c}" for c in categories]
        + ["📊 가격 변동", "⚠️ 이상치", "🔮 가격 예측", "🔀 상품 비교", "🛰️ 수집 이력", "📰 뉴스"]
    )
    tabs = st.tabs(tab_labels)

    # 탭 인덱스 계산
    n = len(categories)
    tab_change   = tabs[n + 1]
    tab_anomaly  = tabs[n + 2]
    tab_predict  = tabs[n + 3]
    tab_compare  = tabs[n + 4]
    tab_scrapes  = tabs[n + 5]
    tab_news     = tabs[n + 6]

    with tabs[0]:
        overview.render(prices_df, categories)

    # 카테고리별 탭 (게이밍/AI 노트북은 laptop_view가 별도 렌더링)
    for i, cat in enumerate(categories):
        with tabs[i + 1]:
            if cat == "게이밍 노트북":
                section_header(tab_icons.get(cat, "🔧"), cat, "RTX5080 / RTX5090")
                laptop_view.render(current_df, changed_df, has_changes, category="게이밍 노트북")
            elif cat == "AI 노트북":
                section_header(tab_icons.get(cat, "🔧"), cat, "맥북 M5 / 라이젠 AI Max — 로컬 RAM으로 AI 구동 가능한 노트북")
                laptop_view.render(
                    current_df, changed_df, has_changes,
                    category="AI 노트북", filter_spec_keys=laptop_view.AI_FILTER_SPEC_KEYS,
                    empty_message="AI 노트북(맥북 M5/라이젠 AI Max) 데이터가 아직 없어요. run_scrapers.bat 을 실행해주세요!",
                )
            else:
                category.render(cat, current_df, changed_df, has_changes, anomaly_products, tab_icons.get(cat, "🔧"))

    with tab_change:
        changes.render(changed_df, has_changes, current_df, prev_date, latest_date)

    with tab_anomaly:
        anomalies.render(categories, current_df, z_anomalies, iqr_anomalies, tab_icons)

    with tab_predict:
        prediction.render(current_df, anomaly_products)

    with tab_compare:
        compare.render(current_df, anomaly_products)

    with tab_scrapes:
        scrapes.render()

    with tab_news:
        news.render(news_df)
else:
    st.info("아직 데이터가 없어요. 스크래퍼를 실행해주세요!")
