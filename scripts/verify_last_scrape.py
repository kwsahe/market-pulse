"""마지막 수집이 제대로 됐는지 데이터 형상으로 판정한다. 배치 끝에서 실행해 종료코드를 만든다.

왜 scrape_runs.status 를 안 보는가:
    실측 — price 런 22회가 **전부** status='success' 였다. CPU 카테고리가 스마트폰·태블릿으로
    오염된 런도(fetched 834) success 였고, 아무것도 못 가져온 런 3개(id 16·22·27, fetched 0)도
    success 였다. status 는 "예외 없이 끝났다"는 뜻이지 "제대로 가져왔다"는 뜻이 아니다.
    지금까지 사고가 발각된 건 사람이 콘솔 로그를 눈으로 봤기 때문인데,
    스케줄러에 등록하는 순간 아무도 안 본다. 그래서 결과 데이터의 형상을 직접 본다.

판정 기준 (모두 prices 테이블 기준):
    1. 최신 수집 날짜가 오늘이 아니다        -> 실패 (배치가 안 돌았거나 전부 실패)
    2. 직전 수집일에 있던 카테고리가 사라졌다  -> 실패 (검색어/필터가 깨진 신호)
    3. 카테고리 행수가 직전 대비 급감/급증     -> 실패

    임계값은 누적 데이터에서 도출했다. 사고일(2026-09-03, 09-10)을 뺀 149건의
    카테고리별 전일 대비 변화율은 중앙값 0.9%, p90 5.1%, 최대 28.7% 였다.
    반면 CPU 오염 사고는 -98.1% 였다. 그래서 하락 40%면 오탐 없이 사고만 잡는다.
    증가 쪽은 실패로 치지 않고 경고만 남긴다. 정상 회복(사고 복구 시 +5100%)이 섞여서
    실패로 처리하면 오탐이 되고, 오탐이 반복되면 알림 자체를 안 보게 된다.

알고 있는 사각지대:
    이 가드는 "행수가 줄어드는" 사고만 잡는다. 오염이 빠진 자리를 **채우는** 경우는 못 잡는다.
    실제로 2026-09-03 CPU 사고 당시 행수는 104 -> 86 으로 -17.3% 였다(진짜 CPU 2행 +
    스마트폰·태블릿 84행). 지금 같은 사고가 나면 _is_cpu 필터가 폰·태블릿을 거부해서
    행수가 2로 붕괴하므로 잡힌다 — 즉 이 가드의 실효성은 **그 카테고리에 필터가 있느냐**에 달려 있다.
    필터가 없는 DDR5 RAM / NVMe SSD / 그래픽카드 / 게이밍 노트북은 여전히 사각지대다.
    (다음 단계: 카테고리별 필터 거부 건수를 scrape_runs 에 남기고 급증을 감시)

사용법:
    python scripts/verify_last_scrape.py           # 오늘 기준 검사
    python scripts/verify_last_scrape.py --date 2026-09-10
    종료코드 0 = 정상, 1 = 이상 (배치가 이 코드로 알림을 낸다)
"""

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DB_PATH

DROP_LIMIT = 0.40   # 직전 대비 40% 이상 감소하면 이상
SURGE_LIMIT = 1.00  # 직전 대비 100% 이상 증가하면 이상


def category_counts(conn, target_date: str) -> dict:
    rows = conn.execute(
        "SELECT category, COUNT(*) FROM prices WHERE date = ? GROUP BY category",
        (target_date,),
    ).fetchall()
    return {cat: n for cat, n in rows}


def previous_date(conn, target_date: str):
    row = conn.execute(
        "SELECT MAX(date) FROM prices WHERE date < ?", (target_date,)
    ).fetchone()
    return row[0] if row and row[0] else None


def check(conn, target_date: str) -> tuple:
    """(실패 항목, 경고 항목)을 돌려준다. 실패가 비어 있으면 종료코드 0."""
    problems = []
    warnings = []

    latest = conn.execute("SELECT MAX(date) FROM prices").fetchone()[0]
    if latest != target_date:
        problems.append(f"최신 수집 날짜가 {latest} 입니다 (기대: {target_date}) — 배치가 돌지 않았거나 전부 실패")
        return problems, warnings  # 오늘 데이터 자체가 없으면 나머지 비교는 의미가 없다

    current = category_counts(conn, target_date)
    if not current:
        problems.append(f"{target_date} 수집 행이 0건입니다")
        return problems, warnings

    prev_date = previous_date(conn, target_date)
    if prev_date is None:
        print("  (직전 수집일이 없어 증감 비교는 건너뜁니다 — 첫 수집으로 보입니다)")
        return problems, warnings

    previous = category_counts(conn, prev_date)
    print(f"  직전 수집일: {prev_date}")

    for cat, before in sorted(previous.items()):
        now = current.get(cat, 0)
        if now == 0:
            problems.append(f"[{cat}] 카테고리가 통째로 사라졌습니다 ({prev_date} {before}행 -> 0행)")
            continue
        delta = (now - before) / before
        mark = "OK"
        if delta <= -DROP_LIMIT:
            problems.append(f"[{cat}] 급감 {before}행 -> {now}행 ({delta * 100:+.1f}%)")
            mark = "급감"
        elif delta >= SURGE_LIMIT:
            # 급증은 실패로 치지 않는다 — 사고 복구·신제품 대량 등록 같은 정상 사유가 섞인다.
            warnings.append(f"[{cat}] 급증 {before}행 -> {now}행 ({delta * 100:+.1f}%)")
            mark = "급증"
        print(f"    {mark:4} {cat:12} {before:>4} -> {now:>4}행 ({delta * 100:+6.1f}%)")

    for cat, now in sorted(current.items()):
        if cat not in previous:
            print(f"    신규 {cat:12} {'':>4}    {now:>4}행 (직전일에 없던 카테고리)")

    return problems, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DB_PATH, help="대상 DB 경로")
    parser.add_argument("--date", default=date.today().isoformat(), help="검사할 수집 날짜 (기본: 오늘)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[!] DB를 찾을 수 없습니다: {args.db}")
        raise SystemExit(1)

    print(f"수집 검증: {args.date}")
    conn = sqlite3.connect(args.db)
    try:
        problems, warnings = check(conn, args.date)
    finally:
        conn.close()

    if warnings:
        print()
        print(f"[경고] {len(warnings)}건 (실패로 처리하지 않음)")
        for w in warnings:
            print(f"  - {w}")

    if problems:
        print(f"\n[!] 이상 {len(problems)}건")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)

    print("\n[OK] 수집 정상")


if __name__ == "__main__":
    main()
