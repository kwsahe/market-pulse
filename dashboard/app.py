# dashboard/app.py
# 게이밍 노트북 & PC 부품 가격/스펙 + IT 뉴스 + 이상치 탐지 대시보드

import streamlit as st
import pandas as pd
import sqlite3
import os
import sys

# ML 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from ml.anomaly_detection import detect_zscore, detect_iqr

# ============================
# DB 연결
# ============================
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price, specs, image_url FROM prices ORDER BY date",
        conn
    )
    conn.close()
    return df


def load_news():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT collected_at, press, title, published_at FROM news ORDER BY published_at DESC",
        conn
    )
    conn.close()
    return df


# ============================
# 페이지 설정
# ============================
st.set_page_config(
    page_title="Market Pulse",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Market Pulse")
st.caption("게이밍 노트북 & PC 부품 가격 추적 · IT 뉴스 · ML 분석 대시보드")

prices_df = load_prices()
news_df = load_news()

# ============================
# 이상치 탐지 실행
# ============================
z_anomalies = detect_zscore(prices_df) if not prices_df.empty else pd.DataFrame()
iqr_anomalies = detect_iqr(prices_df) if not prices_df.empty else pd.DataFrame()

# 이상치 상품 목록 (두 방법 모두에서 잡힌 것)
anomaly_products = set()
if not z_anomalies.empty:
    anomaly_products.update(z_anomalies["product"].tolist())
if not iqr_anomalies.empty:
    anomaly_products.update(iqr_anomalies["product"].tolist())

# ============================
# 상단 요약 카드
# ============================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📦 수집 상품", f"{len(prices_df)}개")
with col2:
    if not prices_df.empty:
        st.metric("📂 카테고리", f"{prices_df['category'].nunique()}개")
    else:
        st.metric("📂 카테고리", "0개")
with col3:
    if not prices_df.empty:
        st.metric("💰 평균 가격", f"{prices_df['price'].mean():,.0f}원")
    else:
        st.metric("💰 평균 가격", "-")
with col4:
    st.metric("📰 뉴스", f"{len(news_df)}개")
with col5:
    z_count = len(z_anomalies) if not z_anomalies.empty else 0
    iqr_count = len(iqr_anomalies) if not iqr_anomalies.empty else 0
    st.metric("⚠️ 이상치", f"{z_count + iqr_count}개")

st.divider()

# ============================
# 탭 구성
# ============================
if not prices_df.empty:
    categories = prices_df["category"].unique().tolist()
    tab_icons = {
        "게이밍 노트북": "💻", "DDR5 RAM": "🧩",
        "NVMe SSD": "💾", "그래픽카드": "🎮", "CPU": "⚡"
    }
    tab_labels = (
        ["📋 전체"]
        + [f"{tab_icons.get(c, '🔧')} {c}" for c in categories]
        + ["⚠️ 이상치 탐지", "📰 뉴스"]
    )
    tabs = st.tabs(tab_labels)

    # ============================
    # 전체 탭
    # ============================
    with tabs[0]:
        st.subheader("카테고리별 평균 가격")
        avg_by_cat = prices_df.groupby("category")["price"].mean().sort_values(ascending=False)
        st.bar_chart(avg_by_cat, color="#4A90D9")

        st.subheader("카테고리별 상품 수")
        count_by_cat = prices_df.groupby("category")["product"].count()
        st.bar_chart(count_by_cat, color="#50C878")

        if prices_df["date"].nunique() >= 2:
            st.subheader("📈 카테고리별 평균 가격 추이")
            trend_df = prices_df.groupby(["date", "category"])["price"].mean().reset_index()
            for cat in categories:
                cat_trend = trend_df[trend_df["category"] == cat]
                if len(cat_trend) >= 2:
                    st.caption(f"**{cat}**")
                    st.line_chart(cat_trend, x="date", y="price", color="#4A90D9")
        else:
            st.info("📈 가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")

    # ============================
    # 카테고리별 탭
    # ============================
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            cat_df = prices_df[prices_df["category"] == category].copy()
            st.subheader(f"{category} — {len(cat_df)}개 상품")

            # 카테고리 통계
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            with stat_col1:
                st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
            with stat_col2:
                st.metric("최저", f"{cat_df['price'].min():,.0f}원")
            with stat_col3:
                st.metric("최고", f"{cat_df['price'].max():,.0f}원")
            with stat_col4:
                st.metric("중간값", f"{cat_df['price'].median():,.0f}원")

            # 정렬 옵션
            sort_order = st.selectbox(
                "정렬",
                ["가격 낮은 순", "가격 높은 순"],
                key=f"sort_{category}"
            )
            ascending = sort_order == "가격 낮은 순"
            cat_df = cat_df.sort_values("price", ascending=ascending)

            # 상품 카드
            cols = st.columns(2)
            for j, (_, row) in enumerate(cat_df.iterrows()):
                with cols[j % 2]:
                    # 이상치 상품은 빨간 테두리 표시
                    is_anomaly = row["product"] in anomaly_products
                    with st.container(border=True):
                        img_col, info_col = st.columns([1, 2])
                        with img_col:
                            if row["image_url"] and str(row["image_url"]).startswith("http"):
                                st.image(row["image_url"], width=120)
                            else:
                                st.caption("이미지 없음")
                        with info_col:
                            if is_anomaly:
                                st.markdown(f"⚠️ **{row['product'][:50]}**")
                                st.caption("이상치 감지됨")
                            else:
                                st.markdown(f"**{row['product'][:50]}**")
                            st.markdown(f"💰 **{row['price']:,}원**")
                            if row["specs"] and str(row["specs"]).strip():
                                with st.expander("📋 상세 스펙"):
                                    st.caption(row["specs"])
                            st.caption(f"수집일: {row['date']}")

    # ============================
    # 이상치 탐지 탭
    # ============================
    with tabs[-2]:
        st.subheader("⚠️ 이상치 탐지 결과")
        st.caption("두 가지 통계 방법으로 비정상 가격을 탐지해요")

        method_tab1, method_tab2, method_tab3 = st.tabs(
            ["📊 카테고리별 통계", "🔵 Z-score 방식", "🟠 IQR 방식"]
        )

        # --- 카테고리별 통계 ---
        with method_tab1:
            for cat in categories:
                cat_df = prices_df[prices_df["category"] == cat]
                st.markdown(f"### {tab_icons.get(cat, '🔧')} {cat}")

                s1, s2, s3, s4, s5 = st.columns(5)
                with s1:
                    st.metric("상품 수", f"{len(cat_df)}개")
                with s2:
                    st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
                with s3:
                    st.metric("최저", f"{cat_df['price'].min():,.0f}원")
                with s4:
                    st.metric("최고", f"{cat_df['price'].max():,.0f}원")
                with s5:
                    st.metric("표준편차", f"{cat_df['price'].std():,.0f}원")
                st.divider()

        # --- Z-score ---
        with method_tab2:
            st.markdown("**Z-score란?** 평균에서 표준편차 몇 개만큼 떨어져 있는지 측정. |Z| > 2.5이면 이상치.")

            if not z_anomalies.empty:
                st.warning(f"⚠️ {len(z_anomalies)}개 이상치 발견!")

                for _, row in z_anomalies.iterrows():
                    direction = "📈 비정상 고가" if row["z_score"] > 0 else "📉 비정상 저가"
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"{direction}")
                            st.markdown(f"**{row['product'][:60]}**")
                            st.caption(f"카테고리: {row['category']}")
                        with c2:
                            st.metric("가격", f"{row['price']:,}원")
                            st.caption(f"평균: {row['mean']:,.0f}원")
                            st.caption(f"Z-score: {row['z_score']:.2f}")
            else:
                st.success("✅ Z-score 이상치 없음!")

        # --- IQR ---
        with method_tab3:
            st.markdown("**IQR이란?** 중간 50% 데이터 범위 기반. Q1 - 1.5×IQR ~ Q3 + 1.5×IQR 밖이면 이상치.")

            if not iqr_anomalies.empty:
                st.warning(f"⚠️ {len(iqr_anomalies)}개 이상치 발견!")

                for _, row in iqr_anomalies.iterrows():
                    direction = "📈 비정상 고가" if row["price"] > row["upper_bound"] else "📉 비정상 저가"
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"{direction}")
                            st.markdown(f"**{row['product'][:60]}**")
                            st.caption(f"카테고리: {row['category']}")
                        with c2:
                            st.metric("가격", f"{row['price']:,}원")
                            st.caption(f"정상 범위: {row['lower_bound']:,.0f} ~ {row['upper_bound']:,.0f}원")
            else:
                st.success("✅ IQR 이상치 없음!")

    # ============================
    # 뉴스 탭
    # ============================
    with tabs[-1]:
        st.subheader("📰 IT/과학 뉴스")
        if not news_df.empty:
            all_press = sorted(news_df["press"].unique())
            selected_press = st.multiselect(
                "언론사 필터",
                options=all_press,
                default=all_press
            )
            filtered_news = news_df[news_df["press"].isin(selected_press)]

            for _, row in filtered_news.iterrows():
                with st.container():
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"📡 {row['press']}  ·  🕐 {row['published_at']}")
                    st.divider()
        else:
            st.info("아직 뉴스 데이터가 없어요.")
else:
    st.info("아직 데이터가 없어요. 스크래퍼를 실행해주세요!")