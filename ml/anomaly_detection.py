# ml/anomaly_detection.py
# 가격 이상치 탐지 모듈
# 방법 1: Z-score — 평균에서 얼마나 떨어져 있는지
# 방법 2: IQR — 사분위 범위 기반 (더 안정적)

import pandas as pd
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    """DB에서 가격 데이터를 DataFrame으로 불러오기"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price, specs, image_url FROM prices",
        conn
    )
    conn.close()
    return df


# ============================
# 방법 1: Z-score 이상치 탐지
# ============================
def detect_zscore(df, threshold=2.5):
    """Z-score 방식 이상치 탐지
    
    Z-score란?
    → 각 값이 평균에서 표준편차 몇 개만큼 떨어져 있는지를 나타내는 수치
    → Z = (값 - 평균) / 표준편차
    → |Z| > 2.5이면 "비정상적으로 멀리 떨어진 값" = 이상치
    
    예시: RAM 평균 60만원, 표준편차 10만원일 때
    → 85만원: Z = (85-60)/10 = 2.5 → 이상치!
    → 30만원: Z = (30-60)/10 = -3.0 → 이상치! (비정상적으로 저렴)
    
    threshold: 이 값 이상이면 이상치로 판단 (기본 2.5)
    """
    results = []

    # 카테고리별로 따로 계산 (RAM과 GPU 가격 범위가 다르니까)
    for category in df["category"].unique():
        cat_df = df[df["category"] == category].copy()

        if len(cat_df) < 3:
            # 데이터가 3개 미만이면 통계적 의미 없음
            continue

        mean = cat_df["price"].mean()
        std = cat_df["price"].std()

        if std == 0:
            continue

        # Z-score 계산
        cat_df["z_score"] = (cat_df["price"] - mean) / std
        cat_df["is_anomaly"] = cat_df["z_score"].abs() > threshold

        # 이상치만 필터링
        anomalies = cat_df[cat_df["is_anomaly"]].copy()
        anomalies["method"] = "Z-score"
        anomalies["mean"] = mean
        anomalies["std"] = std

        results.append(anomalies)

    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()


# ============================
# 방법 2: IQR 이상치 탐지
# ============================
def detect_iqr(df, multiplier=1.5):
    """IQR(사분위범위) 방식 이상치 탐지
    
    IQR이란?
    → Q1 (25번째 백분위): 하위 25% 지점의 값
    → Q3 (75번째 백분위): 상위 25% 지점의 값
    → IQR = Q3 - Q1 (중간 50% 데이터의 범위)
    
    이상치 기준:
    → Q1 - 1.5*IQR 보다 작으면 → 비정상적으로 싼 가격
    → Q3 + 1.5*IQR 보다 크면 → 비정상적으로 비싼 가격
    
    Z-score보다 나은 점:
    → 평균/표준편차는 극단값에 영향을 많이 받지만
    → IQR은 중간값 기반이라 극단값에 덜 민감해요
    """
    results = []

    for category in df["category"].unique():
        cat_df = df[df["category"] == category].copy()

        if len(cat_df) < 4:
            continue

        q1 = cat_df["price"].quantile(0.25)
        q3 = cat_df["price"].quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        # 이상치 판별
        cat_df["is_anomaly"] = (cat_df["price"] < lower_bound) | (cat_df["price"] > upper_bound)
        cat_df["lower_bound"] = lower_bound
        cat_df["upper_bound"] = upper_bound

        anomalies = cat_df[cat_df["is_anomaly"]].copy()
        anomalies["method"] = "IQR"
        anomalies["q1"] = q1
        anomalies["q3"] = q3

        results.append(anomalies)

    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()


# ============================
# 통합 분석 리포트
# ============================
def run_analysis():
    """두 가지 방법으로 이상치 탐지 실행 & 리포트 출력"""
    df = load_prices()
    print(f"📊 전체 데이터: {len(df)}개 상품, {df['category'].nunique()}개 카테고리\n")

    # 카테고리별 기본 통계
    print("=" * 70)
    print("📈 카테고리별 가격 통계")
    print("=" * 70)
    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        print(f"\n🏷️  {cat} ({len(cat_df)}개)")
        print(f"   평균: {cat_df['price'].mean():,.0f}원")
        print(f"   최저: {cat_df['price'].min():,.0f}원")
        print(f"   최고: {cat_df['price'].max():,.0f}원")
        print(f"   중간값: {cat_df['price'].median():,.0f}원")
        print(f"   표준편차: {cat_df['price'].std():,.0f}원")

    # Z-score 이상치
    print(f"\n{'='*70}")
    print("🔍 Z-score 이상치 탐지 (|Z| > 2.5)")
    print("=" * 70)
    z_anomalies = detect_zscore(df)
    if not z_anomalies.empty:
        for _, row in z_anomalies.iterrows():
            direction = "📈 비정상 고가" if row["z_score"] > 0 else "📉 비정상 저가"
            print(f"\n   {direction}")
            print(f"   상품: {row['product'][:50]}")
            print(f"   가격: {row['price']:,}원 (평균: {row['mean']:,.0f}원)")
            print(f"   Z-score: {row['z_score']:.2f}")
    else:
        print("   ✅ Z-score 이상치 없음")

    # IQR 이상치
    print(f"\n{'='*70}")
    print("🔍 IQR 이상치 탐지 (1.5 × IQR)")
    print("=" * 70)
    iqr_anomalies = detect_iqr(df)
    if not iqr_anomalies.empty:
        for _, row in iqr_anomalies.iterrows():
            direction = "📈 비정상 고가" if row["price"] > row["upper_bound"] else "📉 비정상 저가"
            print(f"\n   {direction}")
            print(f"   상품: {row['product'][:50]}")
            print(f"   가격: {row['price']:,}원")
            print(f"   정상 범위: {row['lower_bound']:,.0f}원 ~ {row['upper_bound']:,.0f}원")
    else:
        print("   ✅ IQR 이상치 없음")

    # 요약
    z_count = len(z_anomalies) if not z_anomalies.empty else 0
    iqr_count = len(iqr_anomalies) if not iqr_anomalies.empty else 0
    print(f"\n{'='*70}")
    print(f"📋 요약: Z-score 이상치 {z_count}개, IQR 이상치 {iqr_count}개")
    print("=" * 70)

    return z_anomalies, iqr_anomalies


if __name__ == "__main__":
    run_analysis()