"""data.db 백업 — VACUUM INTO 기반 일관 스냅샷 + 오프사이트 보관.

왜 shutil.copy2가 아닌가:
    WAL 모드에서는 최근 커밋이 data.db 본체가 아니라 data.db-wal 에 먼저 쌓인다.
    본체만 복사한 백업은 "조용히" 비어 있다 — 실측: 5,000행을 커밋한 직후 본체는 4,096B였고
    데이터 전체(94,792B)가 -wal 에 있었다. 그 복사본을 열면 'no such table: prices'가 난다.
    실패가 백업 시점이 아니라 복구가 필요한 날에야 드러나는 유형이라 특히 위험하다.
    VACUUM INTO 는 WAL 내용을 포함한 일관 스냅샷을 단일 파일로 만든다.

이 스크립트의 완료 조건은 "백업 파일을 만들었다"가 아니라 "그 백업을 실제로 열어봤다"이다.
gzip 으로 압축한 뒤 다시 풀어서 integrity_check 와 행수 확인까지 끝내고 나서야 성공으로 친다.

사용법:
    python scripts/backup_db.py                    # 오프사이트 폴더에 gzip 백업 + 세대 회전
    python scripts/backup_db.py --list             # 보관 중인 백업 목록
    python scripts/backup_db.py --dest path.db     # 특정 경로에 비압축 스냅샷 1개
                                                   #   (cleanup_*.py 가 삭제 직전에 쓰는 경로)

환경변수:
    MARKET_PULSE_DB_PATH      대상 DB (기본: database/data.db)
    MARKET_PULSE_BACKUP_DIR   오프사이트 폴더 (기본: %USERPROFILE%/OneDrive/market-pulse-backup)
"""

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DB_PATH

# 7세대 = 일주일치. 검증이 실패한 날에도 백업은 돌기 때문에, 문제를 알아채기 전에
# 성한 백업이 밀려나지 않도록 여유를 둔다. 압축본이 1.7MB라 7개여도 12MB다.
DEFAULT_KEEP = 7
ARCHIVE_PREFIX = "data-"
ARCHIVE_SUFFIX = ".db.gz"

# 스냅샷이 "열리기만" 하는 게 아니라 내용이 들어 있는지 보려고 세는 테이블.
# prices 가 비어 있으면 백업으로서 의미가 없으므로 0행은 실패로 친다.
CORE_TABLES = ("prices", "news", "laptop_specs", "product_registry")


def default_backup_dir() -> str:
    env = os.getenv("MARKET_PULSE_BACKUP_DIR")
    if env:
        return env
    home = os.path.expanduser("~")
    return os.path.join(home, "OneDrive", "market-pulse-backup")


def snapshot(src_db: str, dest_path: str) -> dict:
    """src_db 의 일관 스냅샷을 dest_path 에 만들고, 그 스냅샷을 검사해서 결과를 돌려준다.

    VACUUM INTO 는 대상 파일이 이미 있으면 실패하므로 호출 전에 지워둔다."""
    if not os.path.exists(src_db):
        raise FileNotFoundError(f"DB를 찾을 수 없습니다: {src_db}")
    if os.path.exists(dest_path):
        os.remove(dest_path)

    with sqlite3.connect(src_db) as conn:
        conn.execute("VACUUM INTO ?", (dest_path,))

    return verify(dest_path)


def verify(db_path: str) -> dict:
    """스냅샷을 실제로 열어 무결성과 핵심 테이블 행수를 확인한다."""
    conn = sqlite3.connect(db_path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"무결성 검사 실패({db_path}): {integrity}")

        counts = {}
        for table in CORE_TABLES:
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = None  # 아직 없는 테이블은 실패로 치지 않는다

        if not counts.get("prices"):
            raise RuntimeError(f"백업에 prices 데이터가 없습니다({db_path}) — 빈 백업은 실패로 처리합니다.")

        latest = conn.execute("SELECT MAX(date) FROM prices").fetchone()[0]
    finally:
        conn.close()

    return {"path": db_path, "bytes": os.path.getsize(db_path), "counts": counts, "latest_date": latest}


def backup_to(src_db: str, dest_path: str) -> dict:
    """비압축 스냅샷 1개를 dest_path 에 남긴다. cleanup_*.py 가 삭제 직전에 호출한다.

    shutil.copy2 를 대체하는 자리이므로 시그니처를 (원본, 대상)으로 맞춰 두었다."""
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    return snapshot(src_db, dest_path)


def list_archives(backup_dir: str) -> list:
    """오프사이트 폴더의 백업 목록 (최신순)."""
    if not os.path.isdir(backup_dir):
        return []
    names = [
        n for n in os.listdir(backup_dir)
        if n.startswith(ARCHIVE_PREFIX) and n.endswith(ARCHIVE_SUFFIX)
    ]
    return sorted(names, reverse=True)  # 이름이 시각 스탬프라 사전순 역정렬 = 최신순


def run_offsite_backup(src_db: str, backup_dir: str, keep: int) -> dict:
    """스냅샷 -> gzip -> 압축본을 다시 풀어서 검증 -> 세대 회전."""
    os.makedirs(backup_dir, exist_ok=True)
    # 파일명이 초 단위라 같은 초에 두 번 돌면 서로 덮어써서 세대가 조용히 사라진다.
    # 하루 1회 배치에서는 안 드러나지만 손으로 재실행할 때 나온다 — 겹치면 번호를 붙인다.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = os.path.join(backup_dir, f"{ARCHIVE_PREFIX}{stamp}{ARCHIVE_SUFFIX}")
    seq = 2
    while os.path.exists(archive):
        archive = os.path.join(backup_dir, f"{ARCHIVE_PREFIX}{stamp}_{seq:02d}{ARCHIVE_SUFFIX}")
        seq += 1

    workdir = tempfile.mkdtemp(prefix="market-pulse-backup-")
    try:
        raw = os.path.join(workdir, "snapshot.db")
        info = snapshot(src_db, raw)
        print(f"  스냅샷: {info['bytes']:,}B | prices {info['counts']['prices']:,}행 | 최신 {info['latest_date']}")

        with open(raw, "rb") as fin, gzip.open(archive, "wb", compresslevel=9) as fout:
            shutil.copyfileobj(fin, fout)
        packed = os.path.getsize(archive)
        print(f"  압축   : {packed:,}B ({packed / info['bytes'] * 100:.1f}%)")

        # 여기가 이 스크립트의 핵심 — 만든 아카이브를 실제로 풀어서 열어본다.
        restored = os.path.join(workdir, "restored.db")
        with gzip.open(archive, "rb") as fin, open(restored, "wb") as fout:
            shutil.copyfileobj(fin, fout)
        check = verify(restored)
        if check["counts"] != info["counts"]:
            raise RuntimeError(f"복원 검증 불일치: 원본 {info['counts']} vs 복원 {check['counts']}")
        print(f"  복원검증: OK — {check['counts']['prices']:,}행 다시 읽음")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    removed = []
    for name in list_archives(backup_dir)[keep:]:
        os.remove(os.path.join(backup_dir, name))
        removed.append(name)
    if removed:
        print(f"  회전   : {len(removed)}개 삭제 ({', '.join(removed)})")

    return {"archive": archive, "info": info, "removed": removed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DB_PATH, help="대상 DB 경로")
    parser.add_argument("--backup-dir", default=default_backup_dir(), help="오프사이트 백업 폴더")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help=f"보관 세대 수 (기본 {DEFAULT_KEEP})")
    parser.add_argument("--dest", help="이 경로에 비압축 스냅샷 1개만 만들고 끝낸다")
    parser.add_argument("--list", action="store_true", help="보관 중인 백업 목록만 출력")
    args = parser.parse_args()

    if args.list:
        names = list_archives(args.backup_dir)
        print(f"백업 폴더: {args.backup_dir}")
        if not names:
            print("  (없음)")
            return
        for n in names:
            size = os.path.getsize(os.path.join(args.backup_dir, n))
            print(f"  {n}  {size:,}B")
        return

    if args.dest:
        info = backup_to(args.db, args.dest)
        print(f"스냅샷 생성: {args.dest}")
        print(f"  {info['bytes']:,}B | prices {info['counts']['prices']:,}행 | 최신 {info['latest_date']}")
        return

    print(f"백업 시작: {args.db}")
    print(f"보관 위치: {args.backup_dir}")
    try:
        result = run_offsite_backup(args.db, args.backup_dir, args.keep)
    except Exception as e:
        print(f"\n[!] 백업 실패: {type(e).__name__}: {e}")
        raise SystemExit(1)
    print(f"\n[OK] {os.path.basename(result['archive'])}")


if __name__ == "__main__":
    main()
