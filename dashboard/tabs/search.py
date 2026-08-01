# dashboard/tabs/search.py
# 대시보드 상단 전체 상품 검색 + CSV 내보내기

import pandas as pd
import streamlit as st

from dashboard.theme import code_badge, section_header
from dashboard.tabs.common import match_key_for_row, open_product_detail, to_csv_bytes, get_product_code_map_cached


def render(current_df: pd.DataFrame) -> None:
    if current_df.empty:
        return

    section_header("🔎", "상품 검색", "상품명으로 전체 카테고리에서 찾기")
    search_col, dl_col = st.columns([2, 1])
    with search_col:
        global_search = st.text_input(
            "검색어 입력", key="global_search",
            placeholder="예: RTX5080, DDR5, 삼성전자...", label_visibility="collapsed",
        )
    with dl_col:
        export_df = current_df
        export_label = "⬇️ 전체 상품 CSV"
        if global_search:
            export_df = current_df[current_df["product"].str.contains(global_search, case=False, na=False, regex=False)]
            export_label = "⬇️ 검색 결과 CSV"
        st.download_button(
            export_label,
            data=to_csv_bytes(export_df[["product", "category", "price", "date"]]),
            file_name="market_pulse_products.csv",
            mime="text/csv",
            width="stretch",
        )
    if global_search:
        matches = current_df[current_df["product"].str.contains(global_search, case=False, na=False, regex=False)]
        st.caption(f"'{global_search}' 검색 결과: {len(matches)}개")
        code_map_cache = {}
        for idx, (_, mrow) in enumerate(matches.head(30).iterrows()):
            mcat = mrow["category"]
            if mcat not in code_map_cache:
                code_map_cache[mcat] = get_product_code_map_cached(mcat)
            mcode = code_map_cache[mcat].get(match_key_for_row(mrow), "")
            c1, c2, c3 = st.columns([1, 4, 1])
            with c1:
                st.markdown(code_badge(mcode) or "—", unsafe_allow_html=True)
            with c2:
                st.markdown(f"{mrow['product'][:55]} · **{mrow['price']:,}원**")
                st.caption(mcat)
            with c3:
                if mcode and st.button("상세보기", key=f"gsearch_{idx}_{mcode}"):
                    open_product_detail(mcode)
    st.divider()
