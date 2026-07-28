# dashboard/laptop_view.py
# 노트북 전용 탭 (게이밍 노트북 RTX5080/5090, AI 노트북 등) — 상세 스펙 필터링,
# 집중 추적, 이미지 갤러리, 가격 변동 연동. render()에 category를 넘겨 여러 탭에서 재사용한다.

import re
import pandas as pd
import streamlit as st

from database.db_manager import (
    load_laptop_products, load_laptop_specs, load_laptop_images,
    load_laptop_price_history, load_laptop_best_buy_stats,
    get_tracked_pcodes, set_laptop_tracked, get_product_code_map,
    set_target_price, load_tracked_targets,
)
from dashboard.theme import (
    price_change_badge, best_buy_badge, card_marker, section_header,
    category_color, new_badge, code_badge,
)


def _open_product_detail(code: str) -> None:
    """상품 코드로 상세보기를 연다 (app.py 최상단의 링크 상세 섹션이 쿼리파라미터를 읽어서 렌더링)"""
    st.query_params["code"] = code
    st.rerun()


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    """엑셀에서 한글이 깨지지 않도록 utf-8-sig로 인코딩한 CSV 바이트"""
    return df.to_csv(index=False).encode("utf-8-sig")

DEFAULT_FILTER_SPEC_KEYS = ["GPU 칩셋", "제조회사", "CPU 세분류", "화면 크기", "램", "용량", "무게"]
AI_FILTER_SPEC_KEYS = ["CPU 제조사", "CPU 세분류", "화면 크기", "램", "용량", "무게"]


def _clean_value(value: str) -> str:
    """스펙 값에서 부가 설명(괄호 등) 제거 — 필터 옵션을 깔끔하게 만들기 위함"""
    if not isinstance(value, str):
        return value
    return re.sub(r"\(.*?\)", "", value).strip()


def _pivot_specs(specs_df: pd.DataFrame) -> pd.DataFrame:
    if specs_df.empty:
        return pd.DataFrame()
    return specs_df.pivot(index="pcode", columns="spec_key", values="spec_value")


def render(
    current_df: pd.DataFrame,
    changed_df: pd.DataFrame,
    has_changes: bool,
    category: str = "게이밍 노트북",
    filter_spec_keys: list = None,
    empty_message: str = None,
) -> None:
    """노트북 탭 렌더링 진입점 (category로 게이밍 노트북/AI 노트북 등 구분)"""
    filter_spec_keys = filter_spec_keys or DEFAULT_FILTER_SPEC_KEYS
    empty_message = empty_message or f"{category} 상세 데이터가 아직 없어요. run_scrapers.bat 을 실행해주세요!"

    laptop_df = current_df[current_df["category"] == category].copy()
    laptop_df = laptop_df[laptop_df["pcode"].notna() & (laptop_df["pcode"] != "")]

    if laptop_df.empty:
        st.info(empty_message)
        return

    # 같은 상품(pcode)의 SSD/RAM 변형 중 최저가만 대표로 표시
    laptop_df = laptop_df.sort_values("price").drop_duplicates(subset="pcode", keep="first")

    # laptop_specs/laptop_images는 pcode 기준 전역 테이블이라 카테고리로 미리 좁혀야
    # 필터 옵션에 다른 카테고리(예: 게이밍 노트북의 인텔/라이젠9) 값이 섞여 나오지 않는다.
    category_pcodes = set(laptop_df["pcode"])
    specs_df = load_laptop_specs()
    specs_df = specs_df[specs_df["pcode"].isin(category_pcodes)]
    images_df = load_laptop_images()
    images_df = images_df[images_df["pcode"].isin(category_pcodes)]
    best_buy_df = load_laptop_best_buy_stats(category)
    products_df = load_laptop_products()
    spec_pivot = _pivot_specs(specs_df)
    tracked = set(get_tracked_pcodes())
    code_map = get_product_code_map(category)

    # 이번 스크래핑 회차(최신 수집일)에 처음 잡힌 상품 = 신제품
    latest_date = laptop_df["date"].max()
    new_pcodes = set()
    if not products_df.empty and "first_seen" in products_df.columns:
        first_seen_date = products_df["first_seen"].astype(str).str[:10]
        new_pcodes = set(products_df.loc[first_seen_date == latest_date, "pcode"])
    new_pcodes &= set(laptop_df["pcode"])

    key_prefix = re.sub(r"\W+", "_", category)

    if new_pcodes:
        st.success(f"🆕 오늘({latest_date}) 새로 발견된 노트북 {len(new_pcodes)}종이 있어요!")
        with st.expander(f"🆕 신제품 목록 보기 ({len(new_pcodes)}개)", expanded=False):
            new_df = laptop_df[laptop_df["pcode"].isin(new_pcodes)]
            for _, nrow in new_df.iterrows():
                npcode = nrow["pcode"]
                ncode = code_map.get(npcode, "")
                nc1, nc2, nc3 = st.columns([1, 4, 1])
                with nc1:
                    st.markdown(code_badge(ncode) or "—", unsafe_allow_html=True)
                with nc2:
                    st.markdown(f"{nrow['product'][:55]} · **{nrow['price']:,}원**")
                with nc3:
                    if ncode and st.button("상세보기", key=f"new_detail_{key_prefix}_{npcode}"):
                        _open_product_detail(ncode)
    tab_all, tab_tracked = st.tabs([f"📋 전체 ({len(laptop_df)})", f"🎯 추적 중 ({len(tracked)})"])

    with tab_all:
        search_term = st.text_input("🔎 상품 검색", key=f"lt_search_{key_prefix}", placeholder="상품명으로 검색...")
        if search_term:
            laptop_df = laptop_df[laptop_df["product"].str.contains(search_term, case=False, na=False, regex=False)]
        filtered_df = _render_filters(laptop_df, spec_pivot, filter_spec_keys, key_prefix)
        st.caption(f"{len(filtered_df)}개 상품 표시 중")
        if not filtered_df.empty:
            st.download_button(
                f"⬇️ {category} 목록 CSV ({len(filtered_df)}개)",
                data=_to_csv_bytes(filtered_df[["product", "category", "price", "date"]]),
                file_name=f"market_pulse_{category}.csv",
                mime="text/csv",
                key=f"csv_dl_{key_prefix}",
            )
        st.divider()
        _render_cards(filtered_df, images_df, specs_df, best_buy_df, tracked, changed_df, has_changes, code_map, new_pcodes)

    with tab_tracked:
        targets_df = load_tracked_targets()
        _render_tracked(laptop_df, tracked, images_df, best_buy_df, category, code_map, targets_df)


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
        text = f"🕒 {best_date}에 샀으면 {savings:,}원 이득이었어요 (-{pct:.1f}%)"
        st.markdown(best_buy_badge(text, is_best_now=False), unsafe_allow_html=True)
    else:
        st.markdown(best_buy_badge("🏆 지금이 역대 최저가예요!", is_best_now=True), unsafe_allow_html=True)


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


def _render_filters(laptop_df: pd.DataFrame, spec_pivot: pd.DataFrame, filter_spec_keys: list, key_prefix: str) -> pd.DataFrame:
    with st.expander("🔍 필터", expanded=True):
        n = len(filter_spec_keys)
        cols = list(st.columns(3)) + (list(st.columns(3)) if n > 3 else [])
        selections = {}
        for i, key in enumerate(filter_spec_keys[:6]):
            with cols[i]:
                if key in spec_pivot.columns:
                    options = sorted({_clean_value(v) for v in spec_pivot[key].dropna()})
                else:
                    options = []
                selections[key] = st.multiselect(key, options, default=options, key=f"lt_filter_{key_prefix}_{key}")

        min_price = int(laptop_df["price"].min())
        max_price = int(laptop_df["price"].max())
        if min_price < max_price:
            price_range = st.slider(
                "가격대(원)", min_price, max_price, (min_price, max_price),
                step=100_000, key=f"lt_filter_{key_prefix}_price"
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


@st.dialog("🖼️ 노트북 이미지", width="large")
def _image_dialog(product_name: str, prod_imgs: pd.DataFrame) -> None:
    """대표/상세정보 이미지를 별도 창(모달)으로 크게 보여준다"""
    st.markdown(f"**{product_name}**")
    if prod_imgs.empty:
        st.caption("이미지 없음")
        return
    main_imgs = prod_imgs[prod_imgs["image_type"] == "main"]
    detail_imgs = prod_imgs[prod_imgs["image_type"] == "detail"]
    if not main_imgs.empty:
        st.image(main_imgs.iloc[0]["image_url"], caption="대표 이미지", width="stretch")
    for _, img_row in detail_imgs.iterrows():
        st.image(img_row["image_url"], caption="상세정보", width="stretch")


def _render_cards(filtered_df, images_df, specs_df, best_buy_df, tracked, changed_df, has_changes, code_map=None, new_pcodes=None) -> None:
    if filtered_df.empty:
        st.info("조건에 맞는 노트북이 없어요. 필터를 조정해보세요.")
        return
    new_pcodes = new_pcodes or set()
    code_map = code_map or {}

    cols = st.columns(2)
    for idx, (_, row) in enumerate(filtered_df.iterrows()):
        pcode = row["pcode"]
        with cols[idx % 2]:
            with st.container(border=True):
                card_marker()
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
                    name_html = code_badge(code_map.get(pcode, "")) + f"**{row['product'][:55]}**"
                    if pcode in new_pcodes:
                        name_html += " " + new_badge()
                    st.markdown(name_html, unsafe_allow_html=True)
                    st.markdown(f"💰 **{row['price']:,}원**")

                    if has_changes and not changed_df.empty:
                        change_row = changed_df[changed_df["product"] == row["product"]]
                        if not change_row.empty:
                            ch = change_row.iloc[0]
                            st.markdown(price_change_badge(ch["change"], ch["change_pct"]), unsafe_allow_html=True)

                    _render_best_buy(row["price"], pcode, best_buy_df)

                    is_tracked = pcode in tracked
                    new_tracked = st.checkbox("🎯 집중 추적", value=is_tracked, key=f"track_{pcode}")
                    if new_tracked != is_tracked:
                        set_laptop_tracked(pcode, new_tracked)
                        st.rerun()

                gallery_col, spec_col, detail_col = st.columns(3)
                with gallery_col:
                    prod_imgs = images_df[images_df["pcode"] == pcode]
                    if st.button(f"🖼️ 이미지 ({len(prod_imgs)})", key=f"imgbtn_{pcode}", width="stretch"):
                        _image_dialog(row["product"], prod_imgs)
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
                                width="stretch",
                            )
                with detail_col:
                    code = code_map.get(pcode, "")
                    if code and st.button("📈 상세보기", key=f"detail_{pcode}", width="stretch"):
                        _open_product_detail(code)

                st.caption(f"수집일: {row['date']}")


def _render_tracked(
    laptop_df: pd.DataFrame, tracked: set, images_df: pd.DataFrame, best_buy_df: pd.DataFrame,
    category: str, code_map: dict = None, targets_df: pd.DataFrame = None,
) -> None:
    code_map = code_map or {}
    if targets_df is None:
        targets_df = pd.DataFrame(columns=["pcode", "target_price", "memo"])
    if not tracked:
        st.info("추적 중인 모델이 없어요. '전체' 탭에서 🎯 집중 추적 체크박스를 눌러보세요!")
        return

    tracked_df = laptop_df[laptop_df["pcode"].isin(tracked)]
    if tracked_df.empty:
        st.info("추적 중인 모델이 최신 수집 데이터에는 없어요 (품절/단종 가능성).")
        return

    for _, row in tracked_df.iterrows():
        pcode = row["pcode"]
        target_row = targets_df[targets_df["pcode"] == pcode]
        existing_target = int(target_row.iloc[0]["target_price"]) if not target_row.empty and pd.notna(target_row.iloc[0]["target_price"]) else 0
        existing_memo = target_row.iloc[0]["memo"] if not target_row.empty and pd.notna(target_row.iloc[0]["memo"]) else ""

        with st.container(border=True):
            card_marker()
            c1, c2 = st.columns([1, 2])
            with c1:
                main_imgs = images_df[(images_df["pcode"] == pcode) & (images_df["image_type"] == "main")]
                if not main_imgs.empty:
                    st.image(main_imgs.iloc[0]["image_url"], width=140)
                prod_imgs = images_df[images_df["pcode"] == pcode]
                if st.button(f"🖼️ 이미지 ({len(prod_imgs)})", key=f"tracked_imgbtn_{pcode}"):
                    _image_dialog(row["product"], prod_imgs)
                code = code_map.get(pcode, "")
                if code and st.button("📈 상세보기", key=f"tracked_detail_{pcode}"):
                    _open_product_detail(code)
            with c2:
                st.markdown(code_badge(code_map.get(pcode, "")) + f"**{row['product']}**", unsafe_allow_html=True)
                st.markdown(f"💰 현재가 **{row['price']:,}원**")
                _render_best_buy(row["price"], pcode, best_buy_df)
                if existing_target and row["price"] <= existing_target:
                    st.success(f"🎯 목표가({existing_target:,}원) 도달! 지금이 구매 타이밍이에요.")
                if st.button("추적 해제", key=f"untrack_{pcode}"):
                    set_laptop_tracked(pcode, False)
                    st.rerun()

            with st.expander(f"🎯 목표가 설정{f' ({existing_target:,}원)' if existing_target else ''}"):
                target_col, memo_col = st.columns([1, 2])
                with target_col:
                    new_target = st.number_input(
                        "목표가(원, 0=해제)", min_value=0, step=10_000,
                        value=existing_target, key=f"target_price_{pcode}",
                    )
                with memo_col:
                    new_memo = st.text_input("메모", value=existing_memo, key=f"target_memo_{pcode}")
                if st.button("저장", key=f"target_save_{pcode}"):
                    set_target_price(pcode, new_target if new_target > 0 else None, new_memo)
                    st.rerun()

            history = load_laptop_price_history(pcode)
            if len(history) >= 2:
                st.line_chart(history, x="date", y="price", color=category_color(category))
            else:
                st.caption("가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")
