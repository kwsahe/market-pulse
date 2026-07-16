# dashboard/laptop_view.py
# 게이밍 노트북(RTX5080/5090) 전용 탭 — 상세 스펙 필터링, 집중 추적, 이미지 갤러리, 가격 변동 연동

import re
import pandas as pd
import streamlit as st

from database.db_manager import (
    load_laptop_products, load_laptop_specs, load_laptop_images,
    load_laptop_price_history, load_laptop_best_buy_stats,
    get_tracked_pcodes, set_laptop_tracked,
)

FILTER_SPEC_KEYS = ["GPU 칩셋", "제조회사", "CPU 세분류", "화면 크기", "램", "용량", "무게"]


def _clean_value(value: str) -> str:
    """스펙 값에서 부가 설명(괄호 등) 제거 — 필터 옵션을 깔끔하게 만들기 위함"""
    if not isinstance(value, str):
        return value
    return re.sub(r"\(.*?\)", "", value).strip()


def _pivot_specs(specs_df: pd.DataFrame) -> pd.DataFrame:
    if specs_df.empty:
        return pd.DataFrame()
    return specs_df.pivot(index="pcode", columns="spec_key", values="spec_value")


def render(current_df: pd.DataFrame, changed_df: pd.DataFrame, has_changes: bool) -> None:
    """게이밍 노트북 탭 렌더링 진입점"""
    laptop_df = current_df[current_df["category"] == "게이밍 노트북"].copy()
    laptop_df = laptop_df[laptop_df["pcode"].notna() & (laptop_df["pcode"] != "")]

    if laptop_df.empty:
        st.info("RTX5080/5090 노트북 상세 데이터가 아직 없어요. run_scrapers.bat 을 실행해주세요!")
        return

    # 같은 상품(pcode)의 SSD/RAM 변형 중 최저가만 대표로 표시
    laptop_df = laptop_df.sort_values("price").drop_duplicates(subset="pcode", keep="first")

    specs_df = load_laptop_specs()
    images_df = load_laptop_images()
    best_buy_df = load_laptop_best_buy_stats()
    spec_pivot = _pivot_specs(specs_df)
    tracked = set(get_tracked_pcodes())

    tab_all, tab_tracked = st.tabs([f"📋 전체 ({len(laptop_df)})", f"🎯 추적 중 ({len(tracked)})"])

    with tab_all:
        filtered_df = _render_filters(laptop_df, spec_pivot)
        st.caption(f"{len(filtered_df)}개 상품 표시 중")
        st.divider()
        _render_cards(filtered_df, images_df, specs_df, best_buy_df, tracked, changed_df, has_changes)

    with tab_tracked:
        _render_tracked(laptop_df, tracked, images_df, best_buy_df)


def _render_best_buy(current_price: int, pcode: str, best_buy_df: pd.DataFrame) -> None:
    """'언제 샀으면 얼마 이득이었나' — 역대 최저가 시점 대비 손익 계산"""
    if best_buy_df.empty:
        return
    stat = best_buy_df[best_buy_df["pcode"] == pcode]
    if stat.empty:
        return
    best_date = stat.iloc[0]["best_date"]
    best_price = int(stat.iloc[0]["best_price"])
    savings = current_price - best_price
    if savings > 0:
        pct = savings / current_price * 100
        st.caption(f"🕒 **{best_date}**에 샀으면 **{savings:,}원** 이득이었어요 (-{pct:.1f}%)")
    else:
        st.caption("🏆 지금이 역대 최저가예요!")


def _apply_spec_filter(pcodes: set, spec_pivot: pd.DataFrame, key: str, selected_values: list) -> set:
    """선택된 스펙 값으로 pcode 집합을 좁힌다. 옵션 전체 선택 시 필터 없음으로 간주하고,
    해당 스펙 정보가 아예 없는 상품은 필터 대상에서 제외하지 않는다."""
    if key not in spec_pivot.columns:
        return pcodes
    col_clean = spec_pivot[key].dropna().apply(_clean_value)
    all_values = set(col_clean.unique())
    if set(selected_values) >= all_values:
        return pcodes
    keep = set(col_clean[col_clean.isin(selected_values)].index)
    no_info = set(spec_pivot.index) - set(col_clean.index)
    return pcodes & (keep | no_info)


def _render_filters(laptop_df: pd.DataFrame, spec_pivot: pd.DataFrame) -> pd.DataFrame:
    with st.expander("🔍 필터", expanded=True):
        cols = list(st.columns(3)) + list(st.columns(3))
        selections = {}
        for i, key in enumerate(FILTER_SPEC_KEYS[:6]):
            with cols[i]:
                if key in spec_pivot.columns:
                    options = sorted({_clean_value(v) for v in spec_pivot[key].dropna()})
                else:
                    options = []
                selections[key] = st.multiselect(key, options, default=options, key=f"lt_filter_{key}")

        min_price = int(laptop_df["price"].min())
        max_price = int(laptop_df["price"].max())
        if min_price < max_price:
            price_range = st.slider(
                "가격대(원)", min_price, max_price, (min_price, max_price),
                step=100_000, key="lt_filter_price"
            )
        else:
            price_range = (min_price, max_price)

    matched_pcodes = set(laptop_df["pcode"])
    for key, selected_values in selections.items():
        matched_pcodes = _apply_spec_filter(matched_pcodes, spec_pivot, key, selected_values)

    filtered = laptop_df[
        laptop_df["pcode"].isin(matched_pcodes)
        & laptop_df["price"].between(price_range[0], price_range[1])
    ]
    return filtered


def _render_cards(filtered_df, images_df, specs_df, best_buy_df, tracked, changed_df, has_changes) -> None:
    if filtered_df.empty:
        st.info("조건에 맞는 노트북이 없어요. 필터를 조정해보세요.")
        return

    cols = st.columns(2)
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        pcode = row["pcode"]
        with cols[idx % 2]:
            with st.container(border=True):
                img_col, info_col = st.columns([1, 2])
                with img_col:
                    main_imgs = images_df[(images_df["pcode"] == pcode) & (images_df["image_type"] == "main")]
                    if not main_imgs.empty:
                        st.image(main_imgs.iloc[0]["image_url"], width=140)
                    elif str(row.get("image_url", "")).startswith("http"):
                        st.image(row["image_url"], width=140)
                    else:
                        st.caption("이미지 없음")

                with info_col:
                    st.markdown(f"**{row['product'][:55]}**")
                    st.markdown(f"💰 **{row['price']:,}원**")

                    if has_changes and not changed_df.empty:
                        change_row = changed_df[changed_df["product"] == row["product"]]
                        if not change_row.empty:
                            ch = change_row.iloc[0]
                            if ch["change"] > 0:
                                st.caption(f"📈 +{ch['change']:,}원 (+{ch['change_pct']}%)")
                            else:
                                st.caption(f"📉 {ch['change']:,}원 ({ch['change_pct']}%)")

                    _render_best_buy(row["price"], pcode, best_buy_df)

                    is_tracked = pcode in tracked
                    new_tracked = st.checkbox("🎯 집중 추적", value=is_tracked, key=f"track_{pcode}")
                    if new_tracked != is_tracked:
                        set_laptop_tracked(pcode, new_tracked)
                        st.rerun()

                gallery_col, spec_col = st.columns(2)
                with gallery_col:
                    with st.expander("🖼️ 이미지"):
                        prod_imgs = images_df[images_df["pcode"] == pcode]
                        if prod_imgs.empty:
                            st.caption("이미지 없음")
                        else:
                            for _, img_row in prod_imgs.iterrows():
                                label = "대표 이미지" if img_row["image_type"] == "main" else "상세정보"
                                st.image(img_row["image_url"], caption=label, use_container_width=True)
                with spec_col:
                    with st.expander("📋 전체 스펙"):
                        prod_specs = specs_df[specs_df["pcode"] == pcode]
                        if prod_specs.empty:
                            st.caption("상세 스펙 정보 없음")
                        else:
                            st.dataframe(
                                prod_specs[["spec_key", "spec_value"]].rename(
                                    columns={"spec_key": "항목", "spec_value": "값"}
                                ),
                                hide_index=True,
                                use_container_width=True,
                            )

                st.caption(f"수집일: {row['date']}")


def _render_tracked(laptop_df: pd.DataFrame, tracked: set, images_df: pd.DataFrame, best_buy_df: pd.DataFrame) -> None:
    if not tracked:
        st.info("추적 중인 모델이 없어요. '전체' 탭에서 🎯 집중 추적 체크박스를 눌러보세요!")
        return

    tracked_df = laptop_df[laptop_df["pcode"].isin(tracked)]
    if tracked_df.empty:
        st.info("추적 중인 모델이 최신 수집 데이터에는 없어요 (품절/단종 가능성).")
        return

    for _, row in tracked_df.iterrows():
        pcode = row["pcode"]
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                main_imgs = images_df[(images_df["pcode"] == pcode) & (images_df["image_type"] == "main")]
                if not main_imgs.empty:
                    st.image(main_imgs.iloc[0]["image_url"], width=140)
            with c2:
                st.markdown(f"**{row['product']}**")
                st.markdown(f"💰 현재가 **{row['price']:,}원**")
                _render_best_buy(row["price"], pcode, best_buy_df)
                if st.button("추적 해제", key=f"untrack_{pcode}"):
                    set_laptop_tracked(pcode, False)
                    st.rerun()

            history = load_laptop_price_history(pcode)
            if len(history) >= 2:
                st.line_chart(history, x="date", y="price", color="#E8734A")
            else:
                st.caption("가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")
