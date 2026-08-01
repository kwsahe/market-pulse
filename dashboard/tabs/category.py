# dashboard/tabs/category.py
# DDR5 RAM / NVMe SSD / 그래픽카드 / CPU 공용 카테고리 탭
# (게이밍 노트북 / AI 노트북은 dashboard/laptop_view.py가 별도로 담당)

import pandas as pd
import streamlit as st

from ml.price_prediction import extract_ram_features, extract_ssd_features
from dashboard.theme import card_marker, code_badge, price_change_badge, section_header
from dashboard.tabs.common import (
    match_key_for_row, open_product_detail, to_csv_bytes, format_capacity_label, get_product_code_map_cached,
)

CAPACITY_EXTRACTORS = {"NVMe SSD": extract_ssd_features, "DDR5 RAM": extract_ram_features}


def render(
    category: str, current_df: pd.DataFrame, changed_df: pd.DataFrame, has_changes: bool,
    anomaly_products: set, tab_icon: str = "🔧",
) -> None:
    cat_df = current_df[current_df["category"] == category].copy()
    section_header(tab_icon, category, f"{len(cat_df)}개 상품")

    cat_search = st.text_input("🔎 상품 검색", key=f"search_{category}", placeholder="상품명으로 검색...")
    if cat_search:
        cat_df = cat_df[cat_df["product"].str.contains(cat_search, case=False, na=False, regex=False)]

    code_map = get_product_code_map_cached(category)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
    with s2:
        st.metric("최저", f"{cat_df['price'].min():,.0f}원")
    with s3:
        st.metric("최고", f"{cat_df['price'].max():,.0f}원")
    with s4:
        st.metric("중간값", f"{cat_df['price'].median():,.0f}원")

    capacity_extractor = CAPACITY_EXTRACTORS.get(category)
    if capacity_extractor:
        cat_df["_capacity_gb"] = cat_df.apply(lambda r: capacity_extractor(r).get("capacity_gb", 0), axis=1)
        cat_df["_capacity_label"] = cat_df["_capacity_gb"].apply(format_capacity_label)
        capacity_order = sorted(cat_df["_capacity_gb"].unique())
        capacity_options = [format_capacity_label(c) for c in capacity_order] + ["전체"]
        selected_capacity = st.selectbox(
            "용량 선택", capacity_options, index=len(capacity_options) - 1, key=f"cap_filter_{category}"
        )
        if selected_capacity != "전체":
            cat_df = cat_df[cat_df["_capacity_label"] == selected_capacity]

    sort_order = st.selectbox("정렬", ["가격 낮은 순", "가격 높은 순"], key=f"sort_{category}")
    cat_df = cat_df.sort_values("price", ascending=(sort_order == "가격 낮은 순"))

    if capacity_extractor:
        st.caption(f"{len(cat_df)}개 상품 표시 중")

    if not cat_df.empty:
        st.download_button(
            f"⬇️ {category} 목록 CSV ({len(cat_df)}개)",
            data=to_csv_bytes(cat_df[["product", "category", "price", "date"]]),
            file_name=f"market_pulse_{category}.csv",
            mime="text/csv",
            key=f"csv_dl_{category}",
        )
    else:
        st.info("조건에 맞는 상품이 없어요. 필터를 조정해보세요.")

    cols = st.columns(2)
    for j, (_, row) in enumerate(cat_df.iterrows()):
        with cols[j % 2]:
            is_anomaly = row["product"] in anomaly_products
            with st.container(border=True):
                card_marker()
                img_col, info_col = st.columns([1, 2])
                with img_col:
                    if row["image_url"] and str(row["image_url"]).startswith("http"):
                        st.image(row["image_url"], width=120)
                    else:
                        st.caption("이미지 없음")
                with info_col:
                    code = code_map.get(match_key_for_row(row), "")
                    name_html = code_badge(code)
                    if is_anomaly:
                        name_html += f"⚠️ **{row['product'][:50]}**"
                    else:
                        name_html += f"**{row['product'][:50]}**"
                    st.markdown(name_html, unsafe_allow_html=True)
                    if is_anomaly:
                        st.caption("이상치 감지됨")
                    st.markdown(f"💰 **{row['price']:,}원**")

                    # 가격 변동 표시
                    if has_changes and not changed_df.empty:
                        change_row = changed_df[changed_df["product"] == row["product"]]
                        if not change_row.empty:
                            ch = change_row.iloc[0]
                            st.markdown(price_change_badge(ch["change"], ch["change_pct"]), unsafe_allow_html=True)

                    spec_col, detail_col = st.columns(2)
                    with spec_col:
                        if row["specs"] and str(row["specs"]).strip():
                            with st.expander("📋 상세 스펙"):
                                st.caption(row["specs"])
                    with detail_col:
                        if code and st.button("🔍 상세보기", key=f"detail_{category}_{j}", width="stretch"):
                            open_product_detail(code)
                    st.caption(f"수집일: {row['date']}")
