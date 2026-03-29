# dashboard/app.py
# 게이밍 노트북 가격 & IT 뉴스 대시보드
 
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
    df = pd.read_sql_query("SELECT date, product, price FROM prices ORDER BY date", conn)
    conn.close()
    return df
 
 
def load_news():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT collected_at, press, title, published_at FROM news ORDER BY published_at DESC", conn)
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
st.caption("게이밍 노트북 가격 추적 & IT 뉴스 대시보드")
 
# ============================
# 데이터 불러오기
# ============================
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
        avg_price = prices_df["price"].mean()
        st.metric("💰 평균 가격", f"{avg_price:,.0f}원")
    else:
        st.metric("💰 평균 가격", "데이터 없음")
with col3:
    if not prices_df.empty:
        min_price = prices_df["price"].min()
        st.metric("🔽 최저가", f"{min_price:,.0f}원")
    else:
        st.metric("🔽 최저가", "데이터 없음")
with col4:
    st.metric("📰 수집 뉴스 수", f"{len(news_df)}개")
 
st.divider()
 
# ============================
# 2열 레이아웃: 가격 | 뉴스
# ============================
left_col, right_col = st.columns([3, 2])
 
# --- 왼쪽: 가격 분석 ---
with left_col:
    st.subheader("💻 게이밍 노트북 가격")
 
    if not prices_df.empty:
        def get_brand(name):
            brands = {
                "MSI": "MSI", "ASUS": "ASUS", "HP": "HP",
                "레노버": "레노버", "에이서": "에이서",
                "삼성": "삼성", "LG": "LG"
            }
            for key, value in brands.items():
                if key in name:
                    return value
            return "기타"
 
        prices_df["brand"] = prices_df["product"].apply(get_brand)
 
        all_brands = sorted(prices_df["brand"].unique())
        selected_brands = st.multiselect(
            "브랜드 필터",
            options=all_brands,
            default=all_brands
        )
 
        filtered_df = prices_df[prices_df["brand"].isin(selected_brands)]
 
        st.bar_chart(
            filtered_df.groupby("brand")["price"].mean().sort_values(ascending=False),
            color="#4A90D9"
        )
 
        st.caption("가격 낮은 순")
        display_df = filtered_df[["product", "price", "brand", "date"]].copy()
        display_df["price"] = display_df["price"].apply(lambda x: f"{x:,}원")
        display_df.columns = ["상품명", "가격", "브랜드", "수집일"]
        st.dataframe(
            display_df.sort_values("가격"),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("아직 가격 데이터가 없어요. price_scraper.py를 실행해주세요!")
 
# --- 오른쪽: 뉴스 피드 ---
with right_col:
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
        st.info("아직 뉴스 데이터가 없어요. news_scraper.py를 실행해주세요!")
 
# ============================
# 하단: 가격 추이
# ============================
if not prices_df.empty:
    date_count = prices_df["date"].nunique()
    if date_count >= 2:
        st.divider()
        st.subheader("📈 가격 추이")
 
        trend_df = prices_df.groupby("date")["price"].mean().reset_index()
        st.line_chart(trend_df, x="date", y="price", color="#4A90D9")
    else:
        st.divider()
        st.info("📈 가격 추이 그래프는 2일 이상 데이터가 쌓이면 표시돼요. 매일 스크래퍼를 실행해보세요!")
 