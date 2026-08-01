# dashboard/tabs/changes.py
# 가격 변동 탭 + 가격 인상/인하 카드 (상단 "추적 상품 가격 하락 알림"에서도 재사용)

import pandas as pd
import streamlit as st

from dashboard.theme import card_marker, code_badge, price_change_badge, section_header
from dashboard.tabs.common import match_key_for_row, open_product_detail, get_product_code_map_cached


def render_change_card(row: pd.Series, lookup_df: pd.DataFrame, code_map_cache: dict | None = None, key_prefix: str = "change") -> None:
    """가격 인상/인하 카드 — 이미지+스펙까지 같이 보여줘서 어떤 상품인지 바로 알 수 있게"""
    detail = lookup_df[lookup_df["product"] == row["product"]]
    image_url = detail.iloc[0]["image_url"] if not detail.empty else ""
    specs = detail.iloc[0]["specs"] if not detail.empty else ""

    code = ""
    if not detail.empty:
        category = row["category"]
        if code_map_cache is not None:
            if category not in code_map_cache:
                code_map_cache[category] = get_product_code_map_cached(category)
            cmap = code_map_cache[category]
        else:
            cmap = get_product_code_map_cached(category)
        code = cmap.get(match_key_for_row(detail.iloc[0]), "")

    with st.container(border=True):
        card_marker()
        img_col, info_col = st.columns([1, 3])
        with img_col:
            if image_url and str(image_url).startswith("http"):
                st.image(image_url, width=110)
            else:
                st.caption("이미지 없음")
        with info_col:
            name_html = code_badge(code) if code else ""
            st.markdown(f"{name_html}**{row['product'][:60]}**", unsafe_allow_html=True)
            st.caption(f"카테고리: {row['category']}")
            p1, p2 = st.columns([2, 1])
            with p1:
                st.markdown(f"💰 {row['prev_price']:,}원 → **{row['current_price']:,}원**")
            with p2:
                st.markdown(price_change_badge(row["change"], row["change_pct"]), unsafe_allow_html=True)
            if specs and str(specs).strip():
                with st.expander("📋 상세 스펙"):
                    st.caption(specs)
            if code and st.button("🔍 상세보기", key=f"{key_prefix}_detail_{code}", width="stretch"):
                open_product_detail(code)


def render(changed_df: pd.DataFrame, has_changes: bool, current_df: pd.DataFrame, prev_date=None, latest_date=None) -> None:
    section_header("📊", "가격 변동 리포트")

    if has_changes and not changed_df.empty:
        st.caption(f"비교 기간: {prev_date} → {latest_date}")

        up_df = changed_df[changed_df["change"] > 0]
        down_df = changed_df[changed_df["change"] < 0]

        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1:
            st.metric("📈 인상 상품", f"{len(up_df)}개")
        with sum_col2:
            st.metric("📉 인하 상품", f"{len(down_df)}개")
        with sum_col3:
            st.metric("총 변동", f"{len(changed_df)}개")

        st.divider()

        change_tab1, change_tab2 = st.tabs(["📈 가격 인상", "📉 가격 인하"])
        change_code_map_cache: dict = {}

        with change_tab1:
            if not up_df.empty:
                for i, (_, row) in enumerate(up_df.iterrows()):
                    render_change_card(row, current_df, change_code_map_cache, key_prefix=f"up_{i}")
            else:
                st.success("가격 인상 상품 없음!")

        with change_tab2:
            if not down_df.empty:
                for i, (_, row) in enumerate(down_df.iterrows()):
                    render_change_card(row, current_df, change_code_map_cache, key_prefix=f"down_{i}")
            else:
                st.success("가격 인하 상품 없음!")
    else:
        st.info("📊 가격 변동은 2일 이상 데이터가 쌓이면 표시돼요. 내일 다시 스크래퍼를 실행해보세요!")
