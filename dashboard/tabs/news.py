# dashboard/tabs/news.py
# IT/과학 뉴스 탭

import pandas as pd
import streamlit as st

from dashboard.theme import section_header


def render(news_df: pd.DataFrame) -> None:
    section_header("📰", "IT/과학 뉴스")
    if news_df.empty:
        st.info("아직 뉴스 데이터가 없어요.")
        return

    all_press = sorted(news_df["press"].unique())
    selected_press = st.multiselect("언론사 필터", options=all_press, default=all_press)
    filtered_news = news_df[news_df["press"].isin(selected_press)]
    for _, row in filtered_news.iterrows():
        with st.container():
            st.markdown(f"**{row['title']}**")
            st.caption(f"📡 {row['press']}  ·  🕐 {row['published_at']}")
            st.divider()
