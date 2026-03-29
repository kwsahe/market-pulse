# dashboard/app.py
# 게이밍 노트북 & PC 부품 가격/스펙 + IT 뉴스 대시보드

import streamlit as st
import pandas as pd
import sqlite3
import os

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
st.caption("게이밍 노트북 & PC 부품 가격 추적 · IT 뉴스 대시보드")

prices_df = load_prices()
news_df = load_news()

# ============================
# 상단 요약 카드
# ============================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 수집 상품 수", f"{len(prices_df)}개")
with col2:
    if not prices_df.empty:
        st.metric("📂 카테고리", f"{prices_df['category'].nunique()}개")
    else:
        st.metric("📂 카테고리", "0개")
with col3:
    if not prices_df.empty:
        st.metric("💰 평균 가격", f"{prices_df['price'].mean():,.0f}원")
    else:
        st.metric("💰 평균 가격", "데이터 없음")
with col4:
    st.metric("📰 수집 뉴스 수", f"{len(news_df)}개")

st.divider()

# ============================
# 카테고리 탭
# ============================
if not prices_df.empty:
    categories = prices_df["category"].unique().tolist()
    tab_icons = {"게이밍 노트북": "💻", "DDR5 RAM": "🧩", "NVMe SSD": "💾", "그래픽카드": "🎮", "CPU": "⚡"}
    tab_labels = ["📋 전체"] + [f"{tab_icons.get(c, '🔧')} {c}" for c in categories] + ["📰 뉴스"]
    tabs = st.tabs(tab_labels)

    # --- 전체 탭 ---
    with tabs[0]:
        st.subheader("카테고리별 평균 가격")
        avg_by_cat = prices_df.groupby("category")["price"].mean().sort_values(ascending=False)
        st.bar_chart(avg_by_cat, color="#4A90D9")

        # 카테고리별 상품 수
        st.subheader("카테고리별 상품 수")
        count_by_cat = prices_df.groupby("category")["product"].count()
        st.bar_chart(count_by_cat, color="#50C878")

        # 가격 추이
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

    # --- 카테고리별 탭 ---
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            cat_df = prices_df[prices_df["category"] == category].copy()
            st.subheader(f"{category} — {len(cat_df)}개 상품")

            # 정렬 옵션
            sort_order = st.selectbox(
                "정렬",
                ["가격 낮은 순", "가격 높은 순"],
                key=f"sort_{category}"
            )
            ascending = sort_order == "가격 낮은 순"
            cat_df = cat_df.sort_values("price", ascending=ascending)

            # 상품 카드 (이미지 + 스펙)
            cols = st.columns(2)
            for j, (_, row) in enumerate(cat_df.iterrows()):
                with cols[j % 2]:
                    with st.container(border=True):
                        img_col, info_col = st.columns([1, 2])
                        with img_col:
                            if row["image_url"] and str(row["image_url"]).startswith("http"):
                                st.image(row["image_url"], width=120)
                            else:
                                st.caption("이미지 없음")
                        with info_col:
                            st.markdown(f"**{row['product'][:50]}**")
                            st.markdown(f"💰 **{row['price']:,}원**")
                            # 스펙 표시 (접을 수 있게)
                            if row["specs"] and str(row["specs"]).strip():
                                with st.expander("📋 상세 스펙"):
                                    st.caption(row["specs"])
                            st.caption(f"수집일: {row['date']}")

    # --- 뉴스 탭 ---
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