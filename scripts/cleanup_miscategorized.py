"""prices 테이블에서 카테고리 선별 규칙에 맞지 않는 행을 정리한다.

스크래퍼에 카테고리 필터가 들어가기 전에 쌓인 데이터를 소급 정리하는 유지보수 스크립트다.
필터가 적용된 뒤 수집분에는 애초에 이런 행이 안 들어오므로 보통 한 번만 돌리면 된다.

판정 기준은 scraper.price_scraper.CATEGORY_FILTERS 를 그대로 재사용한다 —
여기서 SQL로 조건을 다시 쓰면 스크래퍼와 기준이 갈라져서 한쪽만 새게 된다.
필터가 걸린 카테고리(CPU / 게이밍 모니터 / 게이밍 키보드 / 게이밍 마우스)만 검사한다.

이 스크립트를 만들게 된 계기:
다나와 "CPU 프로세서" 검색이 2026-08-19 ~ 09-03 사이에 뒤집혔다. 다나와가 검색어의
"프로세서"를 스마트폰·태블릿의 AP(엑시노스·디멘시티 등) 스펙에 매칭시키면서, 08-19까지
104~138행이던 CPU 수집이 09-03에는 진짜 CPU 2행 + 스마트폰/태블릿 84행이 됐다.
검색어는 "CPU"로 고쳤고(_CATEGORIES), 재발 방지용으로 _is_cpu 필터를 남겼다.
이 스크립트는 그 사이에 이미 저장된 84행을 걷어낸다.

사용법:
    python scripts/cleanup_miscategorized.py            # 미리보기 (기본값, DB를 건드리지 않음)
    python scripts/cleanup_miscategorized.py --apply    # 백업 뜨고 실제 삭제

주의:
- product_registry 는 건드리지 않는다. get_or_create_product_code 가 COUNT(*)+1 로
  다음 번호를 매기기 때문에, 레지스트리 행을 지우면 이미 발급된 번호와 충돌한다.
- 과거 스냅샷이 바뀌므로 카테고리 최저가·평균가와 가격 추이 그래프가 소급해서 달라진다.
"""

import argparse
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DB_PATH
from scripts.backup_db import backup_to
from scraper.price_scraper import CATEGORY_FILTERS


def find_targets(conn) -> list[tuple[int, str, str, int, str]]:
    """삭제 대상 (rowid, category, product, price, date) 목록."""
    targets = []
    for category, keep in CATEGORY_FILTERS.items():
        rows = conn.execute(
            "SELECT rowid, category, product, price, date, specs FROM prices WHERE category = ?",
            (category,),
        ).fetchall()
        targets.extend(row[:5] for row in rows if not keep(row[2], row[5] or ""))
    return targets


def report(conn, targets) -> None:
    total = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"\n전체 {total:,}행 중 삭제 대상 {len(targets):,}행 ({len(targets) / total * 100:.2f}%)")
    print(f"검사한 카테고리: {', '.join(CATEGORY_FILTERS)}")

    if not targets:
        return

    print("\n카테고리별:")
    for cat, n in sorted(Counter(t[1] for t in targets).items()):
        checked = conn.execute("SELECT COUNT(*) FROM prices WHERE category = ?", (cat,)).fetchone()[0]
        print(f"   {cat}: {n:,}행 / {checked:,}행")

    print("\n날짜별:")
    for date, n in sorted(Counter(t[4] for t in targets).items()):
        print(f"   {date}: {n:,}행")

    products = sorted({t[2] for t in targets})
    print(f"\n대상 상품 {len(products)}종 (일부):")
    for p in products[:10]:
        print(f"   {p[:72]}")
    if len(products) > 10:
        print(f"   ... 외 {len(products) - 10}종")


def verify(conn) -> None:
    left = find_targets(conn)
    total = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print("\n=== 검증 ===")
    print(f"규칙 위반 잔존: {len(left)}행  <- 0이어야 정상")
    print(f"남은 총 행수:   {total:,}행")


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
