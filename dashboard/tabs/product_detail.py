# dashboard/tabs/product_detail.py
# ?code=XXX 로 열린 상품 단독 페이지 (공유 링크 대상)

import pandas as pd
import streamlit as st

from dashboard.theme import card_marker, code_badge, category_color
from dashboard.tabs.common import (
    match_key_for_row, load_product_registry_cached, load_laptop_images_cached,
    load_price_history_by_match_key_cached,
)


def _resolve_code(code: str, prices_df: pd.DataFrame):
    """상품번호 -> (category, 최신 데이터 행) 조회. 없으면 (None, None)"""
    reg = load_product_registry_cached()
    match = reg[reg["internal_code"] == code]
    if match.empty:
        return None, None
    category = match.iloc[0]["category"]
    match_key = match.iloc[0]["match_key"]
    latest_date = prices_df["date"].max()
    cat_latest = prices_df[(prices_df["date"] == latest_date) & (prices_df["category"] == category)]
    row = cat_latest[(cat_latest["pcode"] == match_key) | (cat_latest["product"] == match_key)]
    if row.empty:
        # 오늘 목록엔 없지만(품절 등) 과거에는 있었을 수 있으니 가장 최근 스냅샷을 대신 보여줌
        hist = prices_df[(prices_df["category"] == category) & ((prices_df["pcode"] == match_key) | (prices_df["product"] == match_key))]
        if hist.empty:
            return category, None
        row = hist.sort_values("date").tail(1)
    return category, row.iloc[0]


def render(prices_df: pd.DataFrame) -> None:
    """URL의 ?code=XXX 로 열린 상품을 페이지 맨 위에 상세정보+가격추이로 보여준다 (=상품별 공유 링크)"""
    code = st.query_params.get("code")
    if not code:
        return

    category, row = _resolve_code(code, prices_df)
    with st.container(border=True):
        card_marker()
        header_col, close_col = st.columns([5, 1])
        with header_col:
            st.markdown(f"🔗 **링크로 열린 상품** {code_badge(code)}", unsafe_allow_html=True)
        with close_col:
            if st.button("✕ 닫기", key="close_linked_product"):
                st.query_params.clear()
                st.rerun()

        if row is None:
            st.warning(f"상품번호 '{code}'를 찾을 수 없어요.")
            return

        match_key = match_key_for_row(row)
        by_pcode = bool(row.get("pcode")) and str(row.get("pcode")).strip() != ""
        pcode = row.get("pcode")

        prod_imgs = pd.DataFrame()
        if pcode and str(pcode).strip():
            all_images_df = load_laptop_images_cached()
            prod_imgs = all_images_df[all_images_df["pcode"] == pcode]

        img_col, info_col = st.columns([1, 3])
        with img_col:
            main_imgs = prod_imgs[prod_imgs["image_type"] == "main"] if not prod_imgs.empty else prod_imgs
            if not main_imgs.empty:
                st.image(main_imgs.iloc[0]["image_url"], width=160)
            elif row.get("image_url") and str(row["image_url"]).startswith("http"):
                st.image(row["image_url"], width=160)
            else:
                st.caption("이미지 없음")
        with info_col:
            st.markdown(f"**{row['product']}**")
            st.caption(f"카테고리: {category} · 최근 수집일: {row['date']}")
            st.markdown(f"💰 **{row['price']:,}원**")
            if row.get("specs") and str(row["specs"]).strip():
                with st.expander("📋 상세 스펙"):
                    st.caption(row["specs"])

        detail_imgs = prod_imgs[prod_imgs["image_type"] == "detail"] if not prod_imgs.empty else prod_imgs
        if not detail_imgs.empty:
            with st.expander(f"🖼️ 상세정보 이미지 ({len(detail_imgs)})", expanded=False):
                img_cols = st.columns(3)
                for i, (_, img_row) in enumerate(detail_imgs.iterrows()):
                    with img_cols[i % 3]:
                        st.image(img_row["image_url"], width="stretch")

        history = load_price_history_by_match_key_cached(category, match_key, by_pcode=by_pcode)
        st.markdown("**📈 가격 추이**")
        if len(history) >= 2:
            history = history.copy()
            history["date"] = pd.to_datetime(history["date"])
            hist_min = history["price"].min()
            hist_max = history["price"].max()
            latest_hist_date = history["date"].max()
            last7 = history[history["date"] >= latest_hist_date - pd.Timedelta(days=7)]
            last30 = history[history["date"] >= latest_hist_date - pd.Timedelta(days=30)]

            stat_cols = st.columns(4)
            with stat_cols[0]:
                st.metric("전체 최저가", f"{hist_min:,.0f}원")
            with stat_cols[1]:
                st.metric("전체 최고가", f"{hist_max:,.0f}원")
            with stat_cols[2]:
                st.metric("최근 7일 평균", f"{last7['price'].mean():,.0f}원" if not last7.empty else "-")
            with stat_cols[3]:
                st.metric("최근 30일 평균", f"{last30['price'].mean():,.0f}원" if not last30.empty else "-")

            diff_from_min_pct = (row["price"] - hist_min) / hist_min * 100 if hist_min else 0
            if diff_from_min_pct > 0.5:
                st.caption(f"현재가가 역대 최저가보다 {diff_from_min_pct:.1f}% 높아요.")
            else:
                st.caption("🏆 지금이 역대 최저가예요!")

            st.line_chart(history, x="date", y="price", color=category_color(category))
        else:
            st.caption("가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")

    st.divider()
