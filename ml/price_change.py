# ml/price_change.py
# 가격 변동 감지 모듈
# 전날 대비 가격이 오르거나 내린 상품을 찾아내요

import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import load_prices


def _pcode_match_key(df: pd.DataFrame) -> pd.Series:
    """1순위 매칭 키: 그날 그 카테고리에서 유일하게 등장하는(variant 없는) pcode만 사용한다.
    같은 pcode에 용량 variant가 여러 개 걸리면(같은 상품이 여러 행) pcode만으로는
    어느 variant인지 구분할 수 없으므로 빈 문자열을 반환해 상품명 매칭(2순위)에 맡긴다.
    pcode가 아예 없는 행(과거 데이터, 아직 pcode 수집 전 스냅샷)도 빈 문자열."""
    pcode = df["pcode"].fillna("").astype(str).str.strip()
    counts = pcode[pcode != ""].value_counts()
    is_unique = pcode.map(counts).fillna(0).eq(1)
    return pcode.where(is_unique, "")


def detect_price_changes():
    """전날 대비 가격 변동 감지

    가장 최근 날짜와 그 이전 날짜의 가격을 비교해요.
    상품명이 그대로면 상품명으로, pcode가 양쪽 다 있으면 pcode로 우선 매칭해서
    (다나와가 상품명 표기를 살짝 바꿔도) 같은 상품임을 더 안정적으로 인식해요.
    pcode 매칭이 안 되는 경우(과거 데이터 등)는 기존처럼 상품명 매칭으로 자동 대체돼요.

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

    latest = df[df["date"] == latest_date][["product", "category", "price", "pcode"]].copy()
    prev = df[df["date"] == prev_date][["product", "price", "pcode"]].copy()

    latest["_pcode_key"] = _pcode_match_key(latest)
    prev["_pcode_key"] = _pcode_match_key(prev)

    latest = latest.rename(columns={"price": "current_price"})
    prev = prev.rename(columns={"price": "prev_price"})

    # 1순위: pcode 매칭 (양쪽 다 유효한 pcode가 있을 때만)
    pcode_matched = pd.merge(
        latest[latest["_pcode_key"] != ""][["product", "category", "current_price", "_pcode_key"]],
        prev[prev["_pcode_key"] != ""][["prev_price", "_pcode_key"]],
        on="_pcode_key", how="inner",
    ).drop(columns="_pcode_key")

    # 2순위: pcode로 못 찾은 나머지는 상품명으로 매칭 (기존 방식과 동일한 폴백)
    already_matched = set(pcode_matched["product"])
    latest_remain = latest[~latest["product"].isin(already_matched)][["product", "category", "current_price"]]
    name_matched = pd.merge(latest_remain, prev[["product", "prev_price"]], on="product", how="inner")

    merged = pd.concat([pcode_matched, name_matched], ignore_index=True)

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
        print("[!] 가격 변동 데이터가 충분하지 않아요.")
        return

    print(f"[+] 가격 변동 리포트 ({prev_date} → {latest_date})")
    print(f"{'='*70}")

    if changed.empty:
        print("[OK] 가격 변동 없음! 모든 상품의 가격이 동일해요.")
        return

    # 가격 인상 상품
    up = changed[changed["change"] > 0]
    down = changed[changed["change"] < 0]

    print(f"\n[+] 가격 인상: {len(up)}개 상품")
    print(f"[-] 가격 인하: {len(down)}개 상품")
    print(f"{'='*70}")

    if not up.empty:
        print(f"\n{'─'*70}")
        print("[+] 가격 인상 TOP 10")
        print(f"{'─'*70}")
        for _, row in up.head(10).iterrows():
            print(f"   {row['product'][:50]}")
            print(f"   [{row['category']}] {row['prev_price']:,}원 → {row['current_price']:,}원 (+{row['change']:,}원, +{row['change_pct']}%)")
            print()

    if not down.empty:
        print(f"\n{'─'*70}")
        print("[-] 가격 인하 TOP 10")
        print(f"{'─'*70}")
        for _, row in down.head(10).iterrows():
            print(f"   {row['product'][:50]}")
            print(f"   [{row['category']}] {row['prev_price']:,}원 → {row['current_price']:,}원 ({row['change']:,}원, {row['change_pct']}%)")
            print()

    print(f"{'='*70}")
    print(f"[+] 요약: 인상 {len(up)}개, 인하 {len(down)}개, 총 변동 {len(changed)}개")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_report()