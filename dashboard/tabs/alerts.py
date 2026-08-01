# dashboard/tabs/alerts.py
# 대시보드 상단 알림 배너: 추적 상품 가격 하락 / 목표가 도달

import pandas as pd
import streamlit as st

from database.db_manager import get_tracked_pcodes, load_tracked_targets
from dashboard.theme import card_marker, code_badge
from dashboard.tabs.common import match_key_for_row, open_product_detail, get_product_code_map_cached
from dashboard.tabs.changes import render_change_card


def render_tracked_drop_alert(current_df: pd.DataFrame, changed_df: pd.DataFrame, has_changes: bool) -> None:
    tracked_pcodes = get_tracked_pcodes()
    if not (tracked_pcodes and has_changes and not changed_df.empty and not current_df.empty):
        return

    tracked_names = current_df[current_df["pcode"].isin(tracked_pcodes)]["product"].unique().tolist()
    tracked_drops = changed_df[changed_df["product"].isin(tracked_names) & (changed_df["change"] < 0)]
    if tracked_drops.empty:
        return

    st.success(f"🔔 집중 추적 중인 상품 {len(tracked_drops)}개의 가격이 내렸어요!")
    with st.expander(f"📉 추적 상품 가격 하락 상세 ({len(tracked_drops)}개)", expanded=True):
        code_map_cache: dict = {}
        for i, (_, row) in enumerate(tracked_drops.iterrows()):
            render_change_card(row, current_df, code_map_cache, key_prefix=f"trackeddrop_{i}")
    st.divider()


def render_target_reached_alert(current_df: pd.DataFrame) -> None:
    targets_df = load_tracked_targets()
    if not targets_df.empty:
        targets_df = targets_df[targets_df["target_price"].notna()]
    if targets_df.empty or current_df.empty:
        return

    target_map = dict(zip(targets_df["pcode"], targets_df["target_price"]))
    tracked_current = current_df[current_df["pcode"].isin(target_map.keys())].copy()
    tracked_current["_target"] = tracked_current["pcode"].map(target_map)
    reached = tracked_current[tracked_current["price"] <= tracked_current["_target"]]
    if reached.empty:
        return

    st.success(f"🎯 목표가에 도달한 추적 상품 {len(reached)}개가 있어요!")
    with st.expander(f"🎯 목표가 도달 상품 상세 ({len(reached)}개)", expanded=True):
        code_cache: dict = {}
        for i, (_, row) in enumerate(reached.iterrows()):
            category = row["category"]
            if category not in code_cache:
                code_cache[category] = get_product_code_map_cached(category)
            code = code_cache[category].get(match_key_for_row(row), "")
            with st.container(border=True):
                card_marker()
                img_col, info_col = st.columns([1, 3])
                with img_col:
                    if row.get("image_url") and str(row["image_url"]).startswith("http"):
                        st.image(row["image_url"], width=110)
                    else:
                        st.caption("이미지 없음")
                with info_col:
                    name_html = code_badge(code) if code else ""
                    st.markdown(f"{name_html}**{row['product'][:60]}**", unsafe_allow_html=True)
                    st.markdown(f"💰 현재가 **{row['price']:,}원** · 목표가 {row['_target']:,.0f}원")
                    if code and st.button("🔍 상세보기", key=f"target_reached_detail_{i}_{code}", width="stretch"):
                        open_product_detail(code)
    st.divider()
