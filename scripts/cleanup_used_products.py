"""prices 테이블에서 중고/리퍼비시/병행수입/해외구매 상품 행을 정리한다.

스크래퍼에 중고 필터가 들어가기 전에 쌓인 데이터를 소급 정리하는 1회성 유지보수 스크립트다.
필터가 적용된 뒤 수집분에는 애초에 이런 행이 안 들어오므로 보통 한 번만 돌리면 된다.

삭제 기준은 scraper.price_scraper._is_new_product 를 그대로 재사용한다 —
여기서 SQL LIKE로 조건을 다시 쓰면 스크래퍼와 기준이 갈라져서 한쪽만 새게 된다.

사용법:
    python scripts/cleanup_used_products.py            # 미리보기 (기본값, DB를 건드리지 않음)
    python scripts/cleanup_used_products.py --apply    # 백업 뜨고 실제 삭제

주의:
- product_registry 는 건드리지 않는다. get_or_create_product_code 가 COUNT(*)+1 로
  다음 번호를 매기기 때문에, 레지스트리 행을 지우면 이미 발급된 번호와 충돌한다
  (예: CPU 242개 중 20개 삭제 → 다음 발급이 CPU-223 인데 이미 존재 → PRIMARY KEY 충돌).
- 과거 스냅샷이 바뀌므로 카테고리 최저가·평균가와 가격 추이 그래프가 소급해서 달라진다.
"""

import argparse
import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DB_PATH
from scraper.price_scraper import USED_PRODUCT_PATTERN, _is_new_product


def find_targets(conn) -> list[tuple[int, str, str, int]]:
    """삭제 대상 (rowid, category, product, price) 목록."""
    rows = conn.execute("SELECT rowid, category, product, price FROM prices").fetchall()
    return [row for row in rows if not _is_new_product(row[2])]


def report(conn, targets) -> None:
    total = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"전체 {total:,}행 중 삭제 대상 {len(targets):,}행 ({len(targets) / total * 100:.2f}%)")
    print(f"제외 패턴: {USED_PRODUCT_PATTERN.pattern}")
    print("  ('벌크'는 무포장 정품이라 대상이 아니다)")

    print("\n카테고리별:")
    for cat, n in sorted(Counter(t[1] for t in targets).items()):
        print(f"   {cat}: {n:,}행")

    products = sorted({t[2] for t in targets})
    print(f"\n대상 상품 {len(products)}종 (일부):")
    for p in products[:10]:
        print(f"   {p[:72]}")
    if len(products) > 10:
        print(f"   ... 외 {len(products) - 10}종")


def verify(conn) -> None:
    rows = conn.execute("SELECT product FROM prices").fetchall()
    left = [p for (p,) in rows if not _is_new_product(p)]
    bulk = sum(1 for (p,) in rows if "벌크" in (p or ""))
    print("\n=== 검증 ===")
    print(f"중고/리퍼 잔존: {len(left)}행  <- 0이어야 정상")
    print(f"벌크 유지:      {bulk:,}행")
    print(f"남은 총 행수:   {len(rows):,}행")


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
        shutil.copy2(args.db, backup)
        print(f"\n백업: {os.path.basename(backup)} ({os.path.getsize(backup):,} bytes)")

        conn.executemany("DELETE FROM prices WHERE rowid = ?", [(t[0],) for t in targets])
        conn.commit()
        print(f"삭제: {len(targets):,}행")

        verify(conn)

        # VACUUM은 디스크 공간 회수용이라 실패해도 정리 자체는 이미 끝났다.
        # 트랜잭션 안에서는 못 돌고, 임시 파일을 못 만들면 "unable to open database file"이 난다.
        try:
            conn.isolation_level = None
            conn.execute("VACUUM")
            print("VACUUM 완료")
        except sqlite3.OperationalError as e:
            print(f"[!] VACUUM 건너뜀 ({e}) — 삭제는 정상 완료됐고 파일 크기만 그대로입니다.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
