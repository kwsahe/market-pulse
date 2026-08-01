# dashboard/tabs/overview.py
# "전체" 탭 — 카테고리별 평균가/상품수 막대차트 + 평균가 추이

import pandas as pd
import altair as alt
import streamlit as st

from ml.trend_analysis import get_price_trend, get_category_trend, summarize_trends
from ml.price_prediction import extract_ram_features, extract_ssd_features
from dashboard.theme import section_header, category_color, CATEGORY_COLORS, BORDER, MUTED

# NVMe SSD/DDR5 RAM은 용량이 섞인 채로 평균을 내면 용량 구성비 변화가 가격 변화처럼 보이므로
# 기준 용량(SSD=1TB, RAM=16GB) 상품만 골라 평균을 낸다.
TREND_CAPACITY_BASIS = {
    "NVMe SSD": (extract_ssd_features, 1024, "1TB"),
    "DDR5 RAM": (extract_ram_features, 16, "16GB"),
}


@st.cache_data(show_spinner=False)
def _compute_trend_source_df(prices_df: pd.DataFrame) -> pd.DataFrame:
    """용량 기준 필터링된 추이용 DataFrame — 정규식 스펙 추출이 무거우니 캐싱한다"""
    trend_source_df = prices_df.copy()
    for cat, (extractor, target_gb, _label) in TREND_CAPACITY_BASIS.items():
        cat_mask = trend_source_df["category"] == cat
        if cat_mask.any():
            cap_series = trend_source_df.loc[cat_mask].apply(lambda r: extractor(r).get("capacity_gb", 0), axis=1)
            drop_idx = cap_series[cap_series != target_gb].index
            trend_source_df = trend_source_df.drop(index=drop_idx)
    return trend_source_df


def _category_bar_chart(series: pd.Series, y_title: str):
    """카테고리별 고정 색상 + 범례가 있는 막대 차트 (dataviz 스킬: 카테고리 색상은 고정 순서, 범례 필수)"""
    df = series.reset_index()
    df.columns = ["category", "value"]
    domain = list(CATEGORY_COLORS.keys())
    range_ = list(CATEGORY_COLORS.values())
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("category:N", title=None, sort=None),
            y=alt.Y("value:Q", title=y_title),
            color=alt.Color("category:N", title="카테고리", scale=alt.Scale(domain=domain, range=range_)),
            tooltip=["category", "value"],
        )
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor=BORDER, domainColor=BORDER, labelColor=MUTED, titleColor=MUTED)
        .configure_legend(labelColor=MUTED, titleColor=MUTED)
        .properties(background="transparent")
    )
    st.altair_chart(chart, width="stretch")


def render(prices_df: pd.DataFrame, categories: list) -> None:
    section_header("📊", "카테고리별 평균 가격")
    avg_by_cat = prices_df.groupby("category")["price"].mean().sort_values(ascending=False)
    _category_bar_chart(avg_by_cat, "평균가(원)")

    section_header("📦", "카테고리별 상품 수")
    count_by_cat = prices_df.groupby("category")["product"].count()
    _category_bar_chart(count_by_cat, "상품 수")

    # 추이 분석 (trend_analysis 모듈 사용)
    trend_source_df = _compute_trend_source_df(prices_df)
    trend_df = get_price_trend(trend_source_df)
    if trend_df.empty:
        st.info("📈 가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")
        return

    section_header(
        "📈", "카테고리별 평균 가격 추이",
        "NVMe SSD는 1TB, DDR5 RAM은 16GB 기준 상품만으로 평균을 계산해요",
    )

    # 전체 기간 방향 요약
    summaries = summarize_trends(trend_source_df)
    if summaries:
        sum_cols = st.columns(len(summaries))
        for col, s in zip(sum_cols, summaries):
            label = s["category"]
            if label in TREND_CAPACITY_BASIS:
                label = f"{label} ({TREND_CAPACITY_BASIS[label][2]} 기준)"
            with col:
                st.metric(
                    label,
                    f"{s['last_price']:,.0f}원",
                    delta=f"{s['change_pct']:+.1f}%",
                    delta_color="inverse" if s["direction"] == "down" else "normal"
                )
        st.caption(f"기간: {summaries[0]['period']}")
        st.divider()

    for cat in categories:
        cat_trend = get_category_trend(trend_source_df, cat)
        if not cat_trend.empty:
            cat_label = cat
            if cat in TREND_CAPACITY_BASIS:
                cat_label = f"{cat} ({TREND_CAPACITY_BASIS[cat][2]} 기준)"
            st.caption(f"**{cat_label}**")
            st.line_chart(cat_trend, x="date", y="avg_price", color=category_color(cat))
