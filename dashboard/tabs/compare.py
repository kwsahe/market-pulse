# dashboard/tabs/compare.py
# 상품 비교 탭 — 같은 카테고리 2~5개 상품을 나란히 비교

import pandas as pd
import streamlit as st

from ml.price_prediction import predict_price_range, FEATURE_EXTRACTORS, FEATURE_LABELS, compute_fair_price_score
from dashboard.theme import card_marker, code_badge, section_header, RED, GREEN, AMBER
from dashboard.tabs.common import (
    match_key_for_row, open_product_detail, get_trained_model, score_badge_bg,
    get_product_code_map_cached, load_price_history_by_match_key_cached,
)


def render(current_df: pd.DataFrame, anomaly_products: set) -> None:
    section_header("🔀", "상품 비교", "같은 카테고리에서 2~5개 상품을 선택해 나란히 비교해보세요.")

    compare_category = st.selectbox("카테고리 선택", list(FEATURE_EXTRACTORS.keys()), key="compare_cat")
    compare_cat_df = current_df[current_df["category"] == compare_category].copy()

    if compare_cat_df.empty:
        st.info("이 카테고리에 조회할 상품이 없어요.")
        return

    compare_options = compare_cat_df["product"].tolist()
    selected_products = st.multiselect(
        "비교할 상품 선택 (2~5개)", compare_options, key="compare_products", max_selections=5,
    )
    if len(selected_products) < 2:
        st.info("비교하려면 2개 이상 선택해주세요.")
        return

    compare_model_info = get_trained_model(compare_category)
    compare_extractor = FEATURE_EXTRACTORS[compare_category]
    compare_code_map = get_product_code_map_cached(compare_category)

    cols_container = st.columns(len(selected_products))
    spec_rows = []
    for idx, pname in enumerate(selected_products):
        prow = compare_cat_df[compare_cat_df["product"] == pname].iloc[0]
        pfeatures = compare_extractor(prow)

        if compare_model_info:
            ppredicted, plow, phigh = predict_price_range(compare_model_info, pfeatures)
        else:
            ppredicted = None

        pmatch_key = match_key_for_row(prow)
        pby_pcode = bool(prow.get("pcode")) and str(prow.get("pcode")).strip() != ""
        phistory = load_price_history_by_match_key_cached(compare_category, pmatch_key, by_pcode=pby_pcode)
        phist_min = phistory["price"].min() if not phistory.empty else None
        phist_max = phistory["price"].max() if not phistory.empty else None
        pis_anomaly = pname in anomaly_products and (ppredicted is not None and prow["price"] >= ppredicted)

        pcode_val = compare_code_map.get(pmatch_key, "")

        with cols_container[idx]:
            card_marker()
            if prow.get("image_url") and str(prow["image_url"]).startswith("http"):
                st.image(prow["image_url"], width=120)
            else:
                st.caption("이미지 없음")
            st.markdown(f"{code_badge(pcode_val)}**{pname[:40]}**", unsafe_allow_html=True)
            st.metric("현재가", f"{prow['price']:,}원")
            if phist_min is not None:
                st.caption(f"과거 최저 {phist_min:,.0f}원 · 최고 {phist_max:,.0f}원")
            if ppredicted is not None:
                pscore, plabel = compute_fair_price_score(prow["price"], ppredicted, phist_min, phist_max, pis_anomaly)
                score_color = GREEN if pscore >= 60 else (AMBER if pscore >= 40 else RED)
                st.caption(f"예측가 {ppredicted:,.0f}원")
                st.markdown(
                    f'<span class="mp-badge" style="background:{score_badge_bg(score_color)};color:{score_color}">'
                    f'{pscore}점 · {plabel}</span>',
                    unsafe_allow_html=True,
                )
            if pcode_val and st.button("🔍 상세보기", key=f"compare_detail_{idx}_{pcode_val}", width="stretch"):
                open_product_detail(pcode_val)

        row_dict = {"상품": pname[:30]}
        for fkey, fval in pfeatures.items():
            row_dict[FEATURE_LABELS.get(fkey, fkey)] = fval
        spec_rows.append(row_dict)

    st.divider()
    st.markdown("**📋 스펙 비교표**")
    spec_df = pd.DataFrame(spec_rows).set_index("상품").T
    st.dataframe(spec_df, width="stretch")
