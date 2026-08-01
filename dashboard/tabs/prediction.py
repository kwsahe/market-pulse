# dashboard/tabs/prediction.py
# 가격 예측 탭 — 스펙 기반 적정가 예측, 적정가 점수, 기여도, 비슷한 제품 비교

import pandas as pd
import altair as alt
import streamlit as st

from ml.price_prediction import (
    predict_price_range, FEATURE_EXTRACTORS, FEATURE_LABELS,
    compute_feature_contributions, find_similar_products, compute_fair_price_score,
)
from dashboard.theme import section_header, RED, GREEN, AMBER, BORDER, MUTED
from dashboard.tabs.common import match_key_for_row, get_trained_model, load_price_history_by_match_key_cached


def render(current_df: pd.DataFrame, anomaly_products: set) -> None:
    section_header("🔮", "가격 예측", "제품을 선택하면 스펙 기반 적정 가격을 예측하고 실제 판매가와 비교해드려요.")

    pred_category = st.selectbox("카테고리 선택", list(FEATURE_EXTRACTORS.keys()), key="pred_cat")

    model_info = get_trained_model(pred_category)
    pred_cat_df = current_df[current_df["category"] == pred_category].copy()

    if model_info is None:
        st.warning("데이터가 부족해 예측 모델을 만들 수 없어요. (카테고리당 최소 5개 필요)")
        return
    if pred_cat_df.empty:
        st.info("이 카테고리에 조회할 상품이 없어요.")
        return

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

    pred_match_key = match_key_for_row(row)
    pred_by_pcode = bool(row.get("pcode")) and str(row.get("pcode")).strip() != ""
    pred_history = load_price_history_by_match_key_cached(pred_category, pred_match_key, by_pcode=pred_by_pcode)
    hist_min = pred_history["price"].min() if not pred_history.empty else None
    hist_max = pred_history["price"].max() if not pred_history.empty else None
    is_anomaly_high = selected_product in anomaly_products and actual >= predicted
    fair_score, fair_label = compute_fair_price_score(actual, predicted, hist_min, hist_max, is_anomaly_high)
    fair_color = GREEN if fair_score >= 60 else (AMBER if fair_score >= 40 else RED)

    img_col, result_col = st.columns([1, 3])
    with img_col:
        if row.get("image_url") and str(row["image_url"]).startswith("http"):
            st.image(row["image_url"], width=140)
        else:
            st.caption("이미지 없음")
    with result_col:
        st.markdown(f"**{selected_product}**")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("실제 가격", f"{actual:,}원")
        with m2:
            st.metric("예측 가격", f"{predicted:,.0f}원")
            st.caption(f"예상 범위(80%): {pred_low:,.0f} ~ {pred_high:,.0f}원")
        with m3:
            st.metric("차이", f"{diff:+,.0f}원", delta=f"{diff_pct:+.1f}%", delta_color="inverse")
        with m4:
            st.markdown('<div class="mp-stat-label">적정가 점수</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="mp-stat-value" style="color:{fair_color}">{fair_score}점 · {fair_label}</div>', unsafe_allow_html=True)

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
            st.altair_chart(chart, width="stretch")

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
        st.dataframe(pd.DataFrame(feature_rows), hide_index=True, width="stretch")
