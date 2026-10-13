"""prices 테이블에서 미끼가·비정상 가격 행을 정리한다.

스크래퍼에 미끼가 필터가 들어가기 전에 쌓인 데이터를 소급 정리하는 1회성 유지보수 스크립트다.
필터가 적용된 뒤 수집분에는 애초에 이런 행이 안 들어오므로 보통 한 번만 돌리면 된다.

판정 기준은 scraper.price_scraper._drop_bogus_variant_prices 를 그대로 재사용한다 —
여기서 비율 계산을 다시 쓰면 스크래퍼와 기준이 갈라져서 한쪽만 새게 된다.

같은 날짜 + 같은 pcode 로 묶은 변형 그룹을 스크래퍼와 똑같이 통과시켜서, 탈락한 행만 지운다.
변형이 하나뿐인 그룹은 비교 기준이 없어 손대지 않는다(스크래퍼도 마찬가지다).

두 번째 기준은 scraper.price_scraper._is_absurd_price — 같은 날 같은 카테고리 중앙값의
100배 초과 / 1/100 미만. 옵션이 하나뿐이라 위 기준으로 못 잡는 행(예: 2026-09-29부터
439,824,000원으로 수집된 앱코 HACKER A660 마우스)을 잡는다.

사용법:
    python scripts/cleanup_bogus_prices.py            # 미리보기 (기본값, DB를 건드리지 않음)
    python scripts/cleanup_bogus_prices.py --apply    # 백업 뜨고 실제 삭제

주의:
- product_registry 는 건드리지 않는다. get_or_create_product_code 가 COUNT(*)+1 로
  다음 번호를 매기기 때문에, 레지스트리 행을 지우면 이미 발급된 번호와 충돌한다.
- 과거 스냅샷이 바뀌므로 카테고리 최저가·평균가와 가격 추이 그래프가 소급해서 달라진다.
"""

import argparse
import os
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DB_PATH
from scripts.backup_db import backup_to
from scraper.price_scraper import (
    ABSURD_PRICE_RATIO, BOGUS_PRICE_RATIO, _drop_bogus_variant_prices, _is_absurd_price,
)

# 저장된 상품명은 "<상품명> (<변형 라벨>)" 꼴이다. 스크래퍼가 붙인 마지막 괄호가 변형 라벨이다.
VARIANT_LABEL_PATTERN = re.compile(r"\(([^()]*)\)\s*$")


def variant_label(product: str) -> str | None:
    match = VARIANT_LABEL_PATTERN.search(product or "")
    return match.group(1) if match else None


def find_targets(conn) -> list[tuple[int, str, str, int, str]]:
    """삭제 대상 (rowid, category, product, price, date) 목록.

    스크래퍼가 수집 시점에 보는 것과 같은 단위(같은 날짜·같은 pcode의 변형 묶음)로 복원한 뒤
    _drop_bogus_variant_prices 에 그대로 통과시켜, 걸러진 라벨에 해당하는 행만 고른다."""
    rows = conn.execute(
        "SELECT rowid, category, product, price, date, pcode FROM prices "
        "WHERE pcode IS NOT NULL AND pcode != ''"
    ).fetchall()

    groups = defaultdict(list)
    for rowid, category, product, price, date, pcode in rows:
        label = variant_label(product)
        if label is None:
            continue  # 변형 라벨이 없는 행은 애초에 변형 경로로 저장된 게 아니다
        groups[(date, pcode)].append((rowid, category, product, price, date, label))

    targets = []
    for items in groups.values():
        variants = [(item[5], item[3]) for item in items]
        kept = set(_drop_bogus_variant_prices(list(variants)))
        for item in items:
            if (item[5], item[3]) not in kept:
                targets.append(item[:5])

    # 비정상 가격: 스크래퍼가 저장 직전에 하는 것처럼 (날짜, 카테고리) 묶음의 중앙값과 비교한다
    by_day = defaultdict(list)
    for row in conn.execute("SELECT rowid, category, product, price, date FROM prices"):
        by_day[(row[4], row[1])].append(row)
    seen = {t[0] for t in targets}
    for rows_of_day in by_day.values():
        median = statistics.median(r[3] for r in rows_of_day)
        targets.extend(r for r in rows_of_day if r[0] not in seen and _is_absurd_price(r[3], median))
    return targets


def report(conn, targets) -> None:
    total = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"\n전체 {total:,}행 중 삭제 대상 {len(targets):,}행 ({len(targets) / total * 100:.4f}%)")
    print(f"판정 기준: 같은 상품의 다른 변형 중앙값 대비 {BOGUS_PRICE_RATIO:.0%} 미만, "
          f"또는 같은 날 카테고리 중앙값의 {ABSURD_PRICE_RATIO}배 초과·1/{ABSURD_PRICE_RATIO} 미만")

    if not targets:
        return

    print("\n카테고리별:")
    for cat, n in sorted(Counter(t[1] for t in targets).items()):
        print(f"   {cat}: {n:,}행")

    print("\n대상 행:")
    for rowid, category, product, price, date in sorted(targets, key=lambda t: t[4]):
        print(f"   {date}  [{category}] {product[:56]}  {price:,}원")


def verify(conn) -> None:
    left = find_targets(conn)
    total = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print("\n=== 검증 ===")
    print(f"잔존:         {len(left)}행  <- 0이어야 정상")
    print(f"남은 총 행수: {total:,}행")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="실제로 삭제한다 (기본은 미리보기)")
    parser.add_argument("--db", default=DB_PATH, help="대상 DB 경로")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[!] DB를 찾을 수 없습니다: {args.db}")
        raise SystemExit(1)

    conn = sqlite3.connect(args.db)
    try:
        targets = find_targets(conn)
        report(conn, targets)

        if not targets:
            print("\n정리할 행이 없습니다.")
            return

        if not args.apply:
            print("\n미리보기 모드입니다. 실제로 지우려면 --apply 를 붙여 다시 실행하세요.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = os.path.join(os.path.dirname(args.db), f"data.backup-{stamp}.db")
        # WAL 모드에서는 파일 복사로 뜬 백업이 조용히 비어 있다 — 최근 커밋이 본체가 아니라
        # -wal 에 있기 때문(실측: 5,000행 커밋 직후 본체 4,096B, 복원 시 'no such table').
        # VACUUM INTO 기반 스냅샷을 쓴다.
        backup_to(args.db, backup)
        print(f"\n백업: {os.path.basename(backup)} ({os.path.getsize(backup):,} bytes)")

        conn.executemany("DELETE FROM prices WHERE rowid = ?", [(t[0],) for t in targets])
        conn.commit()
        print(f"삭제: {len(targets):,}행")

        verify(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
