# dashboard/app.py
# 게이밍 노트북 & PC 부품 가격/스펙 + 이상치 + 가격변동 + 뉴스 대시보드

import streamlit as st
import pandas as pd
import sqlite3
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from ml.anomaly_detection import detect_zscore, detect_iqr
from ml.price_change import detect_price_changes
from ml.trend_analysis import get_price_trend, get_category_trend, summarize_trends
from ml.price_prediction import train_model, predict_price, FEATURE_EXTRACTORS

# ============================
# DB 연결
# ============================
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price, specs, image_url FROM prices ORDER BY date",
        conn
    )
    conn.close()
    return df


def load_news():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT collected_at, press, title, published_at FROM news ORDER BY published_at DESC",
        conn
    )
    conn.close()
    return df


@st.cache_resource(show_spinner="모델 학습 중...")
def get_trained_model(category):
    """카테고리별 가격 예측 모델 학습 (캐시됨)"""
    return train_model(category)


# ============================
# 페이지 설정
# ============================
st.set_page_config(page_title="Market Pulse", page_icon="📊", layout="wide")
st.title("📊 Market Pulse")
st.caption("게이밍 노트북 & PC 부품 가격 추적 · ML 분석 · IT 뉴스 대시보드")

prices_df = load_prices()
news_df = load_news()

# ML 분석
z_anomalies = detect_zscore(prices_df) if not prices_df.empty else pd.DataFrame()
iqr_anomalies = detect_iqr(prices_df) if not prices_df.empty else pd.DataFrame()

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
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("📦 상품", f"{len(prices_df)}개")
with col2:
    st.metric("📂 카테고리", f"{prices_df['category'].nunique() if not prices_df.empty else 0}개")
with col3:
    st.metric("💰 평균가", f"{prices_df['price'].mean():,.0f}원" if not prices_df.empty else "-")
with col4:
    st.metric("📈 인상", f"{up_count}개", delta=f"+{up_count}" if up_count else None)
with col5:
    st.metric("📉 인하", f"{down_count}개", delta=f"-{down_count}" if down_count else None, delta_color="inverse")
with col6:
    z_count = len(z_anomalies) if not z_anomalies.empty else 0
    st.metric("⚠️ 이상치", f"{z_count}개")

st.divider()

# ============================
# 탭 구성
# ============================
if not prices_df.empty:
    categories = prices_df["category"].unique().tolist()
    tab_icons = {
        "게이밍 노트북": "💻", "DDR5 RAM": "🧩",
        "NVMe SSD": "💾", "그래픽카드": "🎮", "CPU": "⚡"
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
        st.subheader("카테고리별 평균 가격")
        avg_by_cat = prices_df.groupby("category")["price"].mean().sort_values(ascending=False)
        st.bar_chart(avg_by_cat, color="#4A90D9")

        st.subheader("카테고리별 상품 수")
        count_by_cat = prices_df.groupby("category")["product"].count()
        st.bar_chart(count_by_cat, color="#50C878")

        # 추이 분석 (trend_analysis 모듈 사용)
        trend_df = get_price_trend(prices_df)
        if not trend_df.empty:
            st.subheader("📈 카테고리별 평균 가격 추이")

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
                    st.line_chart(cat_trend, x="date", y="avg_price", color="#4A90D9")
        else:
            st.info("📈 가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.")

    # ============================
    # 카테고리별 탭
    # ============================
    for i, category in enumerate(categories):
        with tabs[i + 1]:
            cat_df = prices_df[prices_df["category"] == category].copy()
            st.subheader(f"{category} — {len(cat_df)}개 상품")

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("평균", f"{cat_df['price'].mean():,.0f}원")
            with s2:
                st.metric("최저", f"{cat_df['price'].min():,.0f}원")
            with s3:
                st.metric("최고", f"{cat_df['price'].max():,.0f}원")
            with s4:
                st.metric("중간값", f"{cat_df['price'].median():,.0f}원")

            sort_order = st.selectbox("정렬", ["가격 낮은 순", "가격 높은 순"], key=f"sort_{category}")
            cat_df = cat_df.sort_values("price", ascending=(sort_order == "가격 낮은 순"))

            cols = st.columns(2)
            for j, (_, row) in enumerate(cat_df.iterrows()):
                with cols[j % 2]:
                    is_anomaly = row["product"] in anomaly_products
                    with st.container(border=True):
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
                                    if ch["change"] > 0:
                                        st.caption(f"📈 +{ch['change']:,}원 (+{ch['change_pct']}%)")
                                    else:
                                        st.caption(f"📉 {ch['change']:,}원 ({ch['change_pct']}%)")

                            if row["specs"] and str(row["specs"]).strip():
                                with st.expander("📋 상세 스펙"):
                                    st.caption(row["specs"])
                            st.caption(f"수집일: {row['date']}")

    # ============================
    # 가격 변동 탭
    # ============================
    with tab_change:
        st.subheader("📊 가격 변동 리포트")

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
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 1, 1])
                            with c1:
                                st.markdown(f"**{row['product'][:55]}**")
                                st.caption(f"카테고리: {row['category']}")
                            with c2:
                                st.metric("현재가", f"{row['current_price']:,}원", delta=f"+{row['change']:,}원")
                            with c3:
                                st.metric("변동률", f"+{row['change_pct']}%")
                else:
                    st.success("가격 인상 상품 없음!")

            with change_tab2:
                if not down_df.empty:
                    for _, row in down_df.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 1, 1])
                            with c1:
                                st.markdown(f"**{row['product'][:55]}**")
                                st.caption(f"카테고리: {row['category']}")
                            with c2:
                                st.metric("현재가", f"{row['current_price']:,}원", delta=f"{row['change']:,}원")
                            with c3:
                                st.metric("변동률", f"{row['change_pct']}%")
                else:
                    st.success("가격 인하 상품 없음!")
        else:
            st.info("📊 가격 변동은 2일 이상 데이터가 쌓이면 표시돼요. 내일 다시 스크래퍼를 실행해보세요!")

    # ============================
    # 이상치 탭
    # ============================
    with tab_anomaly:
        st.subheader("⚠️ 이상치 탐지 결과")

        method_tab1, method_tab2, method_tab3 = st.tabs(
            ["📊 카테고리별 통계", "🔵 Z-score", "🟠 IQR"]
        )

        with method_tab1:
            for cat in categories:
                cat_df = prices_df[prices_df["category"] == cat]
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
        st.subheader("🔮 가격 예측")
        st.caption("스펙을 입력하면 현재 시장 데이터 기반으로 적정 가격을 예측해드려요.")

        pred_category = st.selectbox("카테고리 선택", list(FEATURE_EXTRACTORS.keys()), key="pred_cat")

        model_info = get_trained_model(pred_category)

        if model_info is None:
            st.warning("데이터가 부족해 예측 모델을 만들 수 없어요. (카테고리당 최소 5개 필요)")
        else:
            r2 = model_info["best_r2"]
            if r2 > 0.8:
                quality_label, quality_color = "높음", "normal"
            elif r2 > 0.5:
                quality_label, quality_color = "보통", "off"
            else:
                quality_label, quality_color = "낮음 — 데이터 더 수집 필요", "off"

            info_c1, info_c2, info_c3 = st.columns(3)
            with info_c1:
                st.metric("모델", model_info["model_name"])
            with info_c2:
                st.metric("R² 점수", f"{r2:.3f}")
            with info_c3:
                st.metric("학습 데이터", f"{model_info['data_count']}개")

            st.divider()

            # 카테고리별 입력 폼
            features = {}

            if pred_category == "DDR5 RAM":
                c1, c2 = st.columns(2)
                with c1:
                    features["clock_mhz"] = st.number_input("클럭 (MHz)", 4800, 8000, 6000, 200)
                    features["cl_timing"] = st.number_input("CL 타이밍", 28, 46, 30, 2)
                    features["voltage"] = st.number_input("전압 (V)", 1.1, 1.5, 1.35, 0.05)
                with c2:
                    features["capacity_gb"] = st.selectbox("용량 (GB)", [8, 16, 32, 48, 64, 96])
                    features["is_pack"] = 1 if st.checkbox("2개입(2x) 묶음") else 0
                    features["has_led"] = 1 if st.checkbox("RGB/LED") else 0

            elif pred_category == "NVMe SSD":
                c1, c2 = st.columns(2)
                with c1:
                    features["pcie_gen"] = st.selectbox("PCIe 세대", [3, 4, 5])
                    features["read_speed"] = st.number_input("순차읽기 (MB/s)", 0, 14000, 7000, 500)
                    features["write_speed"] = st.number_input("순차쓰기 (MB/s)", 0, 14000, 6500, 500)
                with c2:
                    cap_val = st.selectbox("용량", ["250GB", "500GB", "1TB", "2TB", "4TB"])
                    cap_map = {"250GB": 250, "500GB": 500, "1TB": 1024, "2TB": 2048, "4TB": 4096}
                    features["capacity_gb"] = cap_map[cap_val]
                    features["has_dram"] = 1 if st.checkbox("DRAM 탑재") else 0
                    features["is_tlc"] = 1 if st.checkbox("TLC 낸드") else 0
                    features["is_external"] = 1 if st.checkbox("외장형") else 0

            elif pred_category == "그래픽카드":
                c1, c2 = st.columns(2)
                with c1:
                    features["gpu_model"] = st.selectbox(
                        "GPU 모델 번호", [4060, 4070, 4080, 4090, 5060, 5070, 5080, 5090]
                    )
                    features["vram_gb"] = st.number_input("VRAM (GB)", 8, 32, 12, 4)
                with c2:
                    features["boost_mhz"] = st.number_input("부스트 클럭 (MHz)", 1500, 3000, 2500, 100)
                    features["length_mm"] = st.number_input("카드 길이 (mm)", 150, 400, 300, 10)
                    features["power_w"] = st.number_input("정격 파워 (W)", 100, 800, 450, 50)

            elif pred_category == "CPU":
                c1, c2 = st.columns(2)
                with c1:
                    features["total_cores"] = st.number_input("총 코어 수", 4, 32, 14, 2)
                    features["max_ghz"] = st.number_input("최대 클럭 (GHz)", 2.0, 6.0, 5.2, 0.1)
                    features["generation"] = st.number_input("세대", 10, 15, 14, 1)
                with c2:
                    features["has_igpu"] = 1 if st.checkbox("내장 그래픽") else 0
                    features["is_bulk"] = 1 if st.checkbox("벌크 제품") else 0
                    features["is_series2"] = 1 if st.checkbox("시리즈2 (Arrow Lake)") else 0

            elif pred_category == "게이밍 노트북":
                c1, c2 = st.columns(2)
                with c1:
                    features["screen_inch"] = st.number_input("화면 크기 (인치)", 13.0, 18.0, 16.0, 0.5)
                    features["weight_kg"] = st.number_input("무게 (kg)", 1.0, 4.0, 2.2, 0.1)
                    features["brightness_nit"] = st.number_input("밝기 (nit)", 100, 1000, 300, 50)
                with c2:
                    features["cpu_ghz"] = st.number_input("CPU 클럭 (GHz)", 1.0, 5.0, 3.5, 0.1)
                    ssd_val = st.selectbox("SSD 용량", ["512GB", "1TB", "2TB"])
                    ssd_map = {"512GB": 512, "1TB": 1024, "2TB": 2048}
                    features["ssd_gb"] = ssd_map[ssd_val]
                    features["ram_gb"] = st.selectbox("RAM (GB)", [8, 16, 32, 64])

            if st.button("예측하기", type="primary"):
                predicted = predict_price(model_info, features)
                st.success(f"### 예측 가격: {predicted:,.0f}원")
                if r2 <= 0.5:
                    st.caption("신뢰도가 낮아요 — 데이터가 더 쌓이면 정확도가 올라가요.")

    # ============================
    # 뉴스 탭
    # ============================
    with tab_news:
        st.subheader("📰 IT/과학 뉴스")
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
