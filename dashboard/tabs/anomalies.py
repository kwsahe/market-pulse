# dashboard/tabs/anomalies.py
# 이상치 탐지 탭 (카테고리별 통계 / Z-score / IQR)

import pandas as pd
import streamlit as st

from dashboard.theme import card_marker, code_badge, section_header
from dashboard.tabs.common import match_key_for_row, open_product_detail, get_product_code_map_cached


def render(categories: list, current_df: pd.DataFrame, z_anomalies: pd.DataFrame, iqr_anomalies: pd.DataFrame, tab_icons: dict) -> None:
    section_header("⚠️", "이상치 탐지 결과")

    method_tab1, method_tab2, method_tab3 = st.tabs(
        ["📊 카테고리별 통계", "🔵 Z-score", "🟠 IQR"]
    )

    with method_tab1:
        for cat in categories:
            cat_df = current_df[current_df["category"] == cat]
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

    with method_tab2:
        st.markdown("**Z-score**: 평균에서 표준편차 2.5배 이상 벗어나면 이상치")
        if not z_anomalies.empty:
            st.warning(f"⚠️ {len(z_anomalies)}개 이상치 발견!")
            z_code_map_cache: dict = {}
            for i, (_, row) in enumerate(z_anomalies.iterrows()):
                direction = "📈 고가" if row["z_score"] > 0 else "📉 저가"
                category = row["category"]
                if category not in z_code_map_cache:
                    z_code_map_cache[category] = get_product_code_map_cached(category)
                code = z_code_map_cache[category].get(match_key_for_row(row), "")
                with st.container(border=True):
                    card_marker()
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        name_html = code_badge(code) if code else ""
                        st.markdown(f"{name_html}{direction} **{row['product'][:55]}**", unsafe_allow_html=True)
                        st.caption(f"{row['category']}")
                    with c2:
                        st.metric("가격", f"{row['price']:,}원")
                        st.caption(f"Z: {row['z_score']:.2f}")
                    if code and st.button("🔍 상세보기", key=f"zscore_detail_{i}_{code}", width="stretch"):
                        open_product_detail(code)
        else:
            st.success("✅ 이상치 없음!")

    with method_tab3:
        st.markdown("**IQR**: 중간 50% 범위의 1.5배를 벗어나면 이상치")
        if not iqr_anomalies.empty:
            st.warning(f"⚠️ {len(iqr_anomalies)}개 이상치 발견!")
            iqr_code_map_cache: dict = {}
            for i, (_, row) in enumerate(iqr_anomalies.iterrows()):
                direction = "📈 고가" if row["price"] > row["upper_bound"] else "📉 저가"
                category = row["category"]
                if category not in iqr_code_map_cache:
                    iqr_code_map_cache[category] = get_product_code_map_cached(category)
                code = iqr_code_map_cache[category].get(match_key_for_row(row), "")
                with st.container(border=True):
                    card_marker()
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        name_html = code_badge(code) if code else ""
                        st.markdown(f"{name_html}{direction} **{row['product'][:55]}**", unsafe_allow_html=True)
                        st.caption(f"{row['category']}")
                    with c2:
                        st.metric("가격", f"{row['price']:,}원")
                        st.caption(f"범위: {row['lower_bound']:,.0f}~{row['upper_bound']:,.0f}원")
                    if code and st.button("🔍 상세보기", key=f"iqr_detail_{i}_{code}", width="stretch"):
                        open_product_detail(code)
        else:
            st.success("✅ 이상치 없음!")
