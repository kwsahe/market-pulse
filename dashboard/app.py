# dashboard/app.py
# 게이밍 노트북 & PC 부품 가격/스펙 + 이상치 + 가격변동 + 뉴스 대시보드

import streamlit as st
import pandas as pd
import altair as alt
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_manager import load_prices, load_news
from ml.anomaly_detection import detect_zscore, detect_iqr
from ml.price_change import detect_price_changes
from ml.trend_analysis import get_price_trend, get_category_trend, summarize_trends
from ml.price_prediction import (
    train_model, predict_price, predict_price_range, FEATURE_EXTRACTORS, FEATURE_LABELS,
    compute_feature_contributions, find_similar_products,
    extract_ram_features, extract_ssd_features,
)
import dashboard.laptop_view as laptop_view
from dashboard.theme import (
    inject_css, price_change_badge, hero_header, stat_cards, section_header, card_marker,
    CYAN, RED, GREEN, AMBER, CATEGORY_COLORS, category_color, SURFACE, BORDER, MUTED,
)


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
    st.altair_chart(chart, use_container_width=True)


def _render_change_card(row: pd.Series, lookup_df: pd.DataFrame) -> None:
    """가격 인상/인하 카드 — 이미지+스펙까지 같이 보여줘서 어떤 상품인지 바로 알 수 있게"""
    detail = lookup_df[lookup_df["product"] == row["product"]]
    image_url = detail.iloc[0]["image_url"] if not detail.empty else ""
    specs = detail.iloc[0]["specs"] if not detail.empty else ""

    with st.container(border=True):
        card_marker()
        img_col, info_col = st.columns([1, 3])
        with img_col:
            if image_url and str(image_url).startswith("http"):
                st.image(image_url, width=110)
            else:
                st.caption("이미지 없음")
        with info_col:
            st.markdown(f"**{row['product'][:60]}**")
            st.caption(f"카테고리: {row['category']}")
            p1, p2 = st.columns([2, 1])
            with p1:
                st.markdown(f"💰 {row['prev_price']:,}원 → **{row['current_price']:,}원**")
            with p2:
                st.markdown(price_change_badge(row["change"], row["change_pct"]), unsafe_allow_html=True)
            if specs and str(specs).strip():
                with st.expander("📋 상세 스펙"):
                    st.caption(specs)


def _format_capacity_label(capacity_gb: int) -> str:
    """128, 256, 512, 1024(=1TB) 같은 용량 값을 다나와 스타일 라벨로 변환"""
    if not capacity_gb or capacity_gb <= 0:
        return "정보없음"
    if capacity_gb >= 1024 and capacity_gb % 1024 == 0:
        return f"{capacity_gb // 1024}TB"
    return f"{capacity_gb}GB"


@st.cache_data(show_spinner="모델 학습 중...")
def get_trained_model(category):
    """카테고리별 가격 예측 모델 학습 (캐시됨)"""
    try:
        return train_model(category)
    except Exception as e:
        st.error(f"모델 학습 실패 ({category}): {e}")
        return None


# ============================
# 페이지 설정
# ============================
st.set_page_config(page_title="Market Pulse", page_icon="📊", layout="wide")
inject_css()

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
today_kr = datetime.now()
today_label = f"{today_kr.strftime('%Y.%m.%d')} ({WEEKDAY_KR[today_kr.weekday()]})"

hero_header(
    "📊 Market Pulse",
    "RTX5080 / RTX5090 게이밍 노트북 & PC 부품 가격 추적 · ML 분석 · IT 뉴스 대시보드",
    date_label=today_label,
)

prices_df = load_prices()
news_df = load_news()

# 현재가 표시용 — 최신 수집일의 데이터만 사용
if not prices_df.empty:
    latest_date = prices_df["date"].max()
    current_df = prices_df[prices_df["date"] == latest_date].copy()
else:
    current_df = pd.DataFrame()

# ML 분석 (최신 데이터 기준)
z_anomalies = detect_zscore(current_df) if not current_df.empty else pd.DataFrame()
iqr_anomalies = detect_iqr(current_df) if not current_df.empty else pd.DataFrame()

anomaly_products = set()
if not z_anomalies.empty:
    anomaly_products.update(z_anomalies["product"].tolist())
if not iqr_anomalies.empty:
    anomaly_products.update(iqr_anomalies["product"].tolist())

# 가격 변동 감지
price_change_result = detect_price_changes() if not prices_df.empty else pd.DataFrame()
has_changes = isinstance(price_change_result, tuple)
if has_changes:
    changed_df, latest_date, prev_date = price_change_result
    up_count = len(changed_df[changed_df["change"] > 0]) if not changed_df.empty else 0
    down_count = len(changed_df[changed_df["change"] < 0]) if not changed_df.empty else 0
else:
    changed_df = pd.DataFrame()
    up_count = 0
    down_count = 0

# ============================
# 상단 요약
# ============================
z_count = len(z_anomalies) if not z_anomalies.empty else 0
stat_cards([
    {"icon": "📦", "label": "상품", "value": f"{len(current_df)}개"},
    {"icon": "📂", "label": "카테고리", "value": f"{current_df['category'].nunique() if not current_df.empty else 0}개"},
    {"icon": "💰", "label": "평균가", "value": f"{current_df['price'].mean():,.0f}원" if not current_df.empty else "-", "color": CYAN},
    {"icon": "📈", "label": "인상", "value": f"{up_count}개", "color": RED},
    {"icon": "📉", "label": "인하", "value": f"{down_count}개", "color": GREEN},
    {"icon": "⚠️", "label": "이상치", "value": f"{z_count}개", "color": AMBER},
])

st.divider()

# ============================
# 탭 구성
# ============================
if not prices_df.empty:
    categories = prices_df["category"].unique().tolist()
    tab_icons = {
        "게이밍 노트북": "💻", "DDR5 RAM": "🧩",
        "NVMe SSD": "💾", "그래픽카드": "🎮", "CPU": "⚡", "AI 노트북": "🧠"
    }
    tab_labels = (
        ["📋 전체"]
        + [f"{tab_icons.get(c, '🔧')} {c}" for c in categories]
        + ["📊 가격 변동", "⚠️ 이상치", "🔮 가격 예측", "📰 뉴스"]
    )
    tabs = st.tabs(tab_labels)

    # 탭 인덱스 계산
    n = len(categories)
    tab_change   = tabs[n + 1]
    tab_anomaly  = tabs[n + 2]
    tab_predict  = tabs[n + 3]
    tab_news     = tabs[n + 4]

    # ============================
    # 전체 탭
    # ============================
    with tabs[0]:
        section_header("📊", "카테고리별 평균 가격")
        avg_by_cat = prices_df.groupby("category")["price"].mean().sort_values(ascending=False)
        _category_bar_chart(avg_by_cat, "평균가(원)")

        section_header("📦", "카테고리별 상품 수")
        count_by_cat = prices_df.groupby("category")["product"].count()
        _category_bar_chart(count_by_cat, "상품 수")

        # 추이 분석 (trend_analysis 모듈 사용)
        trend_df = get_price_trend(prices_df)
        if not trend_df.empty:
            section_header("📈", "카테고리별 평균 가격 추이")

            # 전체 기간 방향 요약
            summaries = summarize_trends(prices_df)
            if summaries:
                sum_cols = st.columns(len(summaries))
                for col, s in zip(sum_cols, summaries):
                    icon = "📈" if s["direction"] == "up" else ("📉" if s["direction"] == "down" else "➡️")
                    with col:
                        st.metric(
                            s["category"],
                            f"{s['last_price']:,.0f}원",
                            delta=f"{s['change_pct']:+.1f}%",
                            delta_color="inverse" if s["direction"] == "down" else "normal"
                        )
                st.caption(f"기간: {summaries[0]['period']}")
                st.divider()

            for cat in categories:
                cat_trend = get_category_trend(prices_df, cat)
                if not cat_trend.empty:
                    st.caption(f"**{cat}**")
                    st.line_chart(cat_trend, x="date", y="avg_price", color=category_color(cat))
        else:
            st.info("📈 가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")

    # ============================
    # 카테고리별 탭
    # ============================
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            if category == "게이밍 노트북":
                section_header(tab_icons.get(category, "🔧"), category, "RTX5080 / RTX5090")
                laptop_view.render(current_df, changed_df, has_changes, category="게이밍 노트북")
                continue

            if category == "AI 노트북":
                section_header(tab_icons.get(category, "🔧"), category, "맥북 M5 / 라이젠 AI Max — 로컬 RAM으로 AI 구동 가능한 노트북")
                laptop_view.render(
                    current_df, changed_df, has_changes,
                    category="AI 노트북", filter_spec_keys=laptop_view.AI_FILTER_SPEC_KEYS,
                    empty_message="AI 노트북(맥북 M5/라이젠 AI Max) 데이터가 아직 없어요. run_scrapers.bat 을 실행해주세요!",
                )
                continue

            cat_df = current_df[current_df["category"] == category].copy()
            section_header(tab_icons.get(category, "🔧"), category, f"{len(cat_df)}개 상품")

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
            with s2:
                st.metric("최저", f"{cat_df['price'].min():,.0f}원")
            with s3:
                st.metric("최고", f"{cat_df['price'].max():,.0f}원")
            with s4:
                st.metric("중간값", f"{cat_df['price'].median():,.0f}원")

            capacity_extractor = {"NVMe SSD": extract_ssd_features, "DDR5 RAM": extract_ram_features}.get(category)
            if capacity_extractor:
                cat_df["_capacity_gb"] = cat_df.apply(lambda r: capacity_extractor(r).get("capacity_gb", 0), axis=1)
                cat_df["_capacity_label"] = cat_df["_capacity_gb"].apply(_format_capacity_label)
                capacity_order = sorted(cat_df["_capacity_gb"].unique())
                capacity_options = [_format_capacity_label(c) for c in capacity_order] + ["전체"]
                selected_capacity = st.selectbox(
                    "용량 선택", capacity_options, index=len(capacity_options) - 1, key=f"cap_filter_{category}"
                )
                if selected_capacity != "전체":
                    cat_df = cat_df[cat_df["_capacity_label"] == selected_capacity]

            sort_order = st.selectbox("정렬", ["가격 낮은 순", "가격 높은 순"], key=f"sort_{category}")
            cat_df = cat_df.sort_values("price", ascending=(sort_order == "가격 낮은 순"))

            if capacity_extractor:
                st.caption(f"{len(cat_df)}개 상품 표시 중")

            if cat_df.empty:
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
                            if is_anomaly:
                                st.markdown(f"⚠️ **{row['product'][:50]}**")
                                st.caption("이상치 감지됨")
                            else:
                                st.markdown(f"**{row['product'][:50]}**")
                            st.markdown(f"💰 **{row['price']:,}원**")

                            # 가격 변동 표시
                            if has_changes and not changed_df.empty:
                                change_row = changed_df[changed_df["product"] == row["product"]]
                                if not change_row.empty:
                                    ch = change_row.iloc[0]
                                    st.markdown(price_change_badge(ch["change"], ch["change_pct"]), unsafe_allow_html=True)

                            if row["specs"] and str(row["specs"]).strip():
                                with st.expander("📋 상세 스펙"):
                                    st.caption(row["specs"])
                            st.caption(f"수집일: {row['date']}")

    # ============================
    # 가격 변동 탭
    # ============================
    with tab_change:
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

            with change_tab1:
                if not up_df.empty:
                    for _, row in up_df.iterrows():
                        _render_change_card(row, current_df)
                else:
                    st.success("가격 인상 상품 없음!")

            with change_tab2:
                if not down_df.empty:
                    for _, row in down_df.iterrows():
                        _render_change_card(row, current_df)
                else:
                    st.success("가격 인하 상품 없음!")
        else:
            st.info("📊 가격 변동은 2일 이상 데이터가 쌓이면 표시돼요. 내일 다시 스크래퍼를 실행해보세요!")

    # ============================
    # 이상치 탭
    # ============================
    with tab_anomaly:
        section_header("⚠️", "이상치 탐지 결과")

        method_tab1, method_tab2, method_tab3 = st.tabs(
            ["📊 카테고리별 통계", "🔵 Z-score", "🟠 IQR"]
        )

        with method_tab1:
            for cat in categories:
                cat_df = current_df[current_df["category"] == cat]
                st.markdown(f"### {tab_icons.get(cat, '🔧')} {cat}")
                s1, s2, s3, s4, s5 = st.columns(5)
                with s1:
                    st.metric("상품 수", f"{len(cat_df)}개")
                with s2:
                    st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
                with s3:
                    st.metric("최저", f"{cat_df['price'].min():,.0f}원")
                with s4:
                    st.metric("최고", f"{cat_df['price'].max():,.0f}원")
                with s5:
                    st.metric("표준편차", f"{cat_df['price'].std():,.0f}원")
                st.divider()

        with method_tab2:
            st.markdown("**Z-score**: 평균에서 표준편차 2.5배 이상 벗어나면 이상치")
            if not z_anomalies.empty:
                st.warning(f"⚠️ {len(z_anomalies)}개 이상치 발견!")
                for _, row in z_anomalies.iterrows():
                    direction = "📈 고가" if row["z_score"] > 0 else "📉 저가"
                    with st.container(border=True):
                        card_marker()
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"{direction} **{row['product'][:55]}**")
                            st.caption(f"{row['category']}")
                        with c2:
                            st.metric("가격", f"{row['price']:,}원")
                            st.caption(f"Z: {row['z_score']:.2f}")
            else:
                st.success("✅ 이상치 없음!")

        with method_tab3:
            st.markdown("**IQR**: 중간 50% 범위의 1.5배를 벗어나면 이상치")
            if not iqr_anomalies.empty:
                st.warning(f"⚠️ {len(iqr_anomalies)}개 이상치 발견!")
                for _, row in iqr_anomalies.iterrows():
                    direction = "📈 고가" if row["price"] > row["upper_bound"] else "📉 저가"
                    with st.container(border=True):
                        card_marker()
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"{direction} **{row['product'][:55]}**")
                            st.caption(f"{row['category']}")
                        with c2:
                            st.metric("가격", f"{row['price']:,}원")
                            st.caption(f"범위: {row['lower_bound']:,.0f}~{row['upper_bound']:,.0f}원")
            else:
                st.success("✅ 이상치 없음!")

    # ============================
    # 가격 예측 탭
    # ============================
    with tab_predict:
        section_header("🔮", "가격 예측", "제품을 선택하면 스펙 기반 적정 가격을 예측하고 실제 판매가와 비교해드려요.")

        pred_category = st.selectbox("카테고리 선택", list(FEATURE_EXTRACTORS.keys()), key="pred_cat")

        model_info = get_trained_model(pred_category)
        pred_cat_df = current_df[current_df["category"] == pred_category].copy()

        if model_info is None:
            st.warning("데이터가 부족해 예측 모델을 만들 수 없어요. (카테고리당 최소 5개 필요)")
        elif pred_cat_df.empty:
            st.info("이 카테고리에 조회할 상품이 없어요.")
        else:
            r2 = model_info["best_r2"]

            info_c1, info_c2, info_c3 = st.columns(3)
            with info_c1:
                st.metric("모델", model_info["model_name"])
            with info_c2:
                st.metric("R² 점수", f"{r2:.3f}")
            with info_c3:
                st.metric("학습 데이터", f"{model_info['data_count']}개")

            st.divider()

            product_options = pred_cat_df["product"].tolist()
            selected_product = st.selectbox("제품 선택", product_options, key="pred_product")
            row = pred_cat_df[pred_cat_df["product"] == selected_product].iloc[0]

            extractor = FEATURE_EXTRACTORS[pred_category]
            features = extractor(row)
            predicted, pred_low, pred_high = predict_price_range(model_info, features)
            actual = row["price"]
            diff = actual - predicted
            diff_pct = (diff / predicted * 100) if predicted else 0

            img_col, result_col = st.columns([1, 3])
            with img_col:
                if row.get("image_url") and str(row["image_url"]).startswith("http"):
                    st.image(row["image_url"], width=140)
                else:
                    st.caption("이미지 없음")
            with result_col:
                st.markdown(f"**{selected_product}**")
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("실제 가격", f"{actual:,}원")
                with m2:
                    st.metric("예측 가격", f"{predicted:,.0f}원")
                    st.caption(f"예상 범위(80%): {pred_low:,.0f} ~ {pred_high:,.0f}원")
                with m3:
                    st.metric("차이", f"{diff:+,.0f}원", delta=f"{diff_pct:+.1f}%", delta_color="inverse")

                if diff_pct > 10:
                    st.warning(f"⚠️ 실제 가격이 예측보다 {diff_pct:.1f}% 높아요 — 고평가 가능성")
                elif diff_pct < -10:
                    st.success(f"💡 실제 가격이 예측보다 {abs(diff_pct):.1f}% 낮아요 — 저평가/좋은 가격일 수 있어요")
                else:
                    st.info("예측 가격과 실제 가격이 비슷해요 — 적정 가격대")

                if r2 <= 0.5:
                    st.caption("⚠️ 모델 신뢰도가 낮아요 — 데이터가 더 쌓이면 정확도가 올라가요.")

            st.divider()

            # ---- 스펙별 가격 기여도 ----
            contrib_col, similar_col = st.columns(2)
            with contrib_col:
                section_header("📊", "스펙별 가격 기여도", "모든 스펙이 평균일 때 대비, 이 스펙 값이 가격을 얼마나 움직였는지")
                contributions, baseline_pred = compute_feature_contributions(model_info, features)
                contrib_df = pd.DataFrame(contributions)
                contrib_df = contrib_df[contrib_df["contribution"].abs() > 1]  # 사실상 0인 기여는 숨김
                if contrib_df.empty:
                    st.caption("뚜렷한 기여 스펙을 찾지 못했어요.")
                else:
                    chart = (
                        alt.Chart(contrib_df)
                        .mark_bar()
                        .encode(
                            x=alt.X("contribution:Q", title="가격 기여도(원)"),
                            y=alt.Y("label:N", title=None, sort="-x"),
                            color=alt.condition("datum.contribution > 0", alt.value(RED), alt.value(GREEN)),
                            tooltip=[alt.Tooltip("label:N", title="스펙"), alt.Tooltip("value:N", title="값"), alt.Tooltip("contribution:Q", title="기여도(원)", format=",.0f")],
                        )
                        .configure_view(strokeWidth=0)
                        .configure_axis(gridColor=BORDER, domainColor=BORDER, labelColor=MUTED, titleColor=MUTED)
                        .properties(height=max(120, 28 * len(contrib_df)))
                    )
                    st.altair_chart(chart, use_container_width=True)

            # ---- 비슷한 스펙의 제품과 비교 ----
            with similar_col:
                section_header("🔍", "비슷한 스펙 제품 비교", "스펙이 가장 비슷한 다른 제품들의 실제 판매가")
                similar_df = find_similar_products(
                    pred_cat_df, features, extractor, model_info,
                    exclude_product=selected_product, top_n=5,
                )
                if similar_df.empty:
                    st.caption("비교할 제품이 없어요.")
                else:
                    for _, srow in similar_df.iterrows():
                        sdiff = srow["price"] - actual
                        badge = f"🔺 +{sdiff:,.0f}원" if sdiff > 0 else (f"🔻 {sdiff:,.0f}원" if sdiff < 0 else "동일")
                        st.markdown(f"**{srow['product'][:45]}**")
                        st.caption(f"{srow['price']:,.0f}원 · {selected_product[:20]} 대비 {badge}")

            st.divider()

            # ---- 스펙 특성 표 ----
            with st.expander("📋 추출된 스펙 특성 보기"):
                feature_rows = [
                    {"스펙": FEATURE_LABELS.get(f, f), "값": v}
                    for f, v in features.items()
                ]
                st.dataframe(pd.DataFrame(feature_rows), hide_index=True, use_container_width=True)

    # ============================
    # 뉴스 탭
    # ============================
    with tab_news:
        section_header("📰", "IT/과학 뉴스")
        if not news_df.empty:
            all_press = sorted(news_df["press"].unique())
            selected_press = st.multiselect("언론사 필터", options=all_press, default=all_press)
            filtered_news = news_df[news_df["press"].isin(selected_press)]
            for _, row in filtered_news.iterrows():
                with st.container():
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"📡 {row['press']}  ·  🕐 {row['published_at']}")
                    st.divider()
        else:
            st.info("아직 뉴스 데이터가 없어요.")
else:
    st.info("아직 데이터가 없어요. 스크래퍼를 실행해주세요!")
