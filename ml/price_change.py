# ml/price_change.py
# 가격 변동 감지 모듈
# 전날 대비 가격이 오르거나 내린 상품을 찾아내요

import pandas as pd
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price FROM prices ORDER BY date",
        conn
    )
    conn.close()
    return df


def detect_price_changes():
    """전날 대비 가격 변동 감지
    
    같은 상품명 기준으로 가장 최근 날짜와 그 이전 날짜의 가격을 비교해요.
    
    반환: DataFrame (상품명, 카테고리, 이전가격, 현재가격, 변동액, 변동률)
    """
    df = load_prices()

    if df.empty:
        return pd.DataFrame()

    # 날짜 목록 (최신순)
    dates = sorted(df["date"].unique(), reverse=True)

    if len(dates) < 2:
        return pd.DataFrame()

    # 최신 날짜와 그 이전 날짜
    latest_date = dates[0]
    prev_date = dates[1]

    latest = df[df["date"] == latest_date][["product", "category", "price"]].copy()
    prev = df[df["date"] == prev_date][["product", "price"]].copy()

    # 컬럼명 구분
    latest.columns = ["product", "category", "current_price"]
    prev.columns = ["product", "prev_price"]

    # 같은 상품명으로 merge
    merged = pd.merge(latest, prev, on="product", how="inner")

    # 변동 계산
    merged["change"] = merged["current_price"] - merged["prev_price"]
    merged["change_pct"] = (merged["change"] / merged["prev_price"] * 100).round(2)

    # 변동 있는 것만 필터 (0원 변동 제외)
    changed = merged[merged["change"] != 0].copy()

    # 변동률 절대값 기준 정렬
    changed = changed.sort_values("change_pct", key=abs, ascending=False)

    return changed, latest_date, prev_date


def run_report():
    """가격 변동 리포트 출력"""
    result = detect_price_changes()

    if isinstance(result, pd.DataFrame) and result.empty:
        print("📊 가격 변동 데이터가 충분하지 않아요.")
        print("   2일 이상 스크래퍼를 실행해야 비교할 수 있어요!")
        return

    if isinstance(result, tuple):
        changed, latest_date, prev_date = result
    else:
        print("📊 가격 변동 데이터가 충분하지 않아요.")
        return

    print(f"📊 가격 변동 리포트 ({prev_date} → {latest_date})")
    print(f"{'='*70}")

    if changed.empty:
        print("✅ 가격 변동 없음! 모든 상품의 가격이 동일해요.")
        return

    # 가격 인상 상품
    up = changed[changed["change"] > 0]
    down = changed[changed["change"] < 0]

    print(f"\n📈 가격 인상: {len(up)}개 상품")
    print(f"📉 가격 인하: {len(down)}개 상품")
    print(f"{'='*70}")

    if not up.empty:
        print(f"\n{'─'*70}")
        print("📈 가격 인상 TOP 10")
        print(f"{'─'*70}")
        for _, row in up.head(10).iterrows():
            print(f"   {row['product'][:50]}")
            print(f"   [{row['category']}] {row['prev_price']:,}원 → {row['current_price']:,}원 (+{row['change']:,}원, +{row['change_pct']}%)")
            print()

    if not down.empty:
        print(f"\n{'─'*70}")
        print("📉 가격 인하 TOP 10")
        print(f"{'─'*70}")
        for _, row in down.head(10).iterrows():
            print(f"   {row['product'][:50]}")
            print(f"   [{row['category']}] {row['prev_price']:,}원 → {row['current_price']:,}원 ({row['change']:,}원, {row['change_pct']}%)")
            print()

    print(f"{'='*70}")
    print(f"📋 요약: 인상 {len(up)}개, 인하 {len(down)}개, 총 변동 {len(changed)}개")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_report()