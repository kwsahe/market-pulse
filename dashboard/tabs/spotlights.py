# dashboard/tabs/spotlights.py
# 대시보드 상단 자동 순환 카드: 오늘의 변동폭 TOP / 주목할 만한 상품(이상치+신제품)

import pandas as pd
import streamlit as st

from database.db_manager import get_product_code_map, load_laptop_products
from dashboard.theme import price_change_badge, section_header, spotlight_card, rotating_cards, new_badge, AMBER
from dashboard.tabs.common import match_key_for_row, code_for_row

LAPTOP_CATEGORIES = ["게이밍 노트북", "AI 노트북"]


def render_top_movers(current_df: pd.DataFrame, changed_df: pd.DataFrame, has_changes: bool) -> None:
    if not (has_changes and not changed_df.empty):
        return

    top_movers = changed_df.reindex(changed_df["change_pct"].abs().sort_values(ascending=False).index).head(8)
    code_cache: dict = {}
    cards = []
    for _, mrow in top_movers.iterrows():
        mcategory = mrow["category"]
        detail = current_df[current_df["product"] == mrow["product"]]
        mcode = code_for_row(detail.iloc[0], mcategory, code_cache) if not detail.empty else ""
        mimg = detail.iloc[0]["image_url"] if not detail.empty else ""
        cards.append(spotlight_card(
            mcode, mrow["product"], mcategory, mimg,
            f"{mrow['prev_price']:,}원 → <b>{mrow['current_price']:,}원</b>",
            price_change_badge(mrow["change"], mrow["change_pct"]),
        ))

    if cards:
        section_header("🔥", "오늘의 변동폭 TOP", "가격이 가장 많이 움직인 상품이 순서대로 나타나요")
        rotating_cards(cards, seconds_per_card=4)
        st.divider()


def render_notable_products(current_df: pd.DataFrame, z_anomalies: pd.DataFrame) -> None:
    cards = []

    if not z_anomalies.empty:
        top_anomalies = z_anomalies.reindex(z_anomalies["z_score"].abs().sort_values(ascending=False).index).head(5)
        code_cache: dict = {}
        for _, arow in top_anomalies.iterrows():
            acode = code_for_row(arow, arow["category"], code_cache)
            direction = "📈 고가 이상치" if arow["z_score"] > 0 else "📉 저가 이상치"
            cards.append(spotlight_card(
                acode, arow["product"], arow["category"], arow.get("image_url", ""),
                f"{arow['price']:,}원",
                f'<span class="mp-badge" style="background:rgba(250,178,25,.15);color:{AMBER}">{direction} Z={arow["z_score"]:.2f}</span>',
            ))

    if not current_df.empty:
        products_df = load_laptop_products()
        laptop_current = current_df[current_df["category"].isin(LAPTOP_CATEGORIES) & current_df["pcode"].notna()]
        if not products_df.empty and "first_seen" in products_df.columns and not laptop_current.empty:
            latest_laptop_date = laptop_current["date"].max()
            first_seen_date = products_df["first_seen"].astype(str).str[:10]
            new_pcodes_today = set(products_df.loc[first_seen_date == latest_laptop_date, "pcode"])
            new_rows = laptop_current[laptop_current["pcode"].isin(new_pcodes_today)].drop_duplicates(subset="pcode")
            code_cache: dict = {}
            for _, nrow in new_rows.head(5).iterrows():
                ncategory = nrow["category"]
                if ncategory not in code_cache:
                    code_cache[ncategory] = get_product_code_map(ncategory)
                ncode = code_cache[ncategory].get(nrow["pcode"], "")
                cards.append(spotlight_card(
                    ncode, nrow["product"], ncategory, nrow.get("image_url", ""),
                    f"{nrow['price']:,}원", new_badge(),
                ))

    if cards:
        section_header("✨", "주목할 만한 상품", "이상치·신제품이 순서대로 나타나요")
        rotating_cards(cards, seconds_per_card=4)
        st.divider()
