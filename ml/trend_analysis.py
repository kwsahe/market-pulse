# ml/trend_analysis.py
# 카테고리별 가격 추이 분석 모듈

import pandas as pd
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price FROM prices ORDER BY date",
        conn
    )
    conn.close()
    return df


def get_price_trend(df):
    """날짜별·카테고리별 평균 가격 추이 반환

    반환: DataFrame (date, category, avg_price)
    데이터가 2일 미만이면 빈 DataFrame 반환
    """
    if df.empty or df["date"].nunique() < 2:
        return pd.DataFrame()
    trend = df.groupby(["date", "category"])["price"].mean().reset_index()
    trend.columns = ["date", "category", "avg_price"]
    return trend


def get_category_trend(df, category):
    """특정 카테고리의 날짜별 평균 가격 반환

    반환: DataFrame (date, avg_price)
    """
    cat_df = df[df["category"] == category]
    if cat_df.empty or cat_df["date"].nunique() < 2:
        return pd.DataFrame()
    trend = cat_df.groupby("date")["price"].mean().reset_index()
    trend.columns = ["date", "avg_price"]
    return trend


def summarize_trends(df):
    """각 카테고리의 전체 기간 가격 방향 요약

    반환: list of dict
        - category: 카테고리명
        - direction: "up" / "down" / "flat"
        - change_pct: 변동률 (%)
        - first_price: 첫날 평균가
        - last_price: 마지막날 평균가
        - period: "YYYY-MM-DD → YYYY-MM-DD"
    """
    if df.empty or df["date"].nunique() < 2:
        return []

    dates = sorted(df["date"].unique())
    first_date, last_date = dates[0], dates[-1]

    results = []
    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        first_price = cat_df[cat_df["date"] == first_date]["price"].mean()
        last_price = cat_df[cat_df["date"] == last_date]["price"].mean()

        if pd.isna(first_price) or pd.isna(last_price) or first_price == 0:
            continue

        change_pct = (last_price - first_price) / first_price * 100

        if change_pct > 1:
            direction = "up"
        elif change_pct < -1:
            direction = "down"
        else:
            direction = "flat"

        results.append({
            "category": cat,
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "first_price": first_price,
            "last_price": last_price,
            "period": f"{first_date} → {last_date}",
        })

    return results


if __name__ == "__main__":
    df = load_prices()
    print(f"전체 데이터: {len(df)}개")

    summaries = summarize_trends(df)
    if not summaries:
        print("추이 분석을 위해 2일 이상 데이터가 필요해요.")
    else:
        for s in summaries:
            icon = "📈" if s["direction"] == "up" else ("📉" if s["direction"] == "down" else "➡️")
            print(f"{icon} {s['category']}: {s['first_price']:,.0f}원 → {s['last_price']:,.0f}원 ({s['change_pct']:+.2f}%)")
            print(f"   기간: {s['period']}")
