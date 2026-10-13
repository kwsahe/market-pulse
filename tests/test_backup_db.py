# tests/test_backup_db.py
# 백업이 "만들어졌다"가 아니라 "복원된다"를 검증한다.
# 이 스크립트가 지키는 건 재수집 불가능한 가격 이력이라, 조용히 비는 실패가 가장 위험하다.

import gzip
import os
import shutil
import sqlite3

import pytest

from scripts.backup_db import backup_to, list_archives, run_offsite_backup, snapshot, verify


def make_db(path, rows=100, wal=True):
    conn = sqlite3.connect(path)
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE prices (id INTEGER PRIMARY KEY, date TEXT, v TEXT)")
    conn.execute("CREATE TABLE news (id INTEGER PRIMARY KEY)")
    conn.executemany(
        "INSERT INTO prices (date, v) VALUES (?, ?)",
        [("2026-09-10", f"row{i}") for i in range(rows)],
    )
    conn.commit()
    return conn  # 열어둔 채로 돌려준다 — 체크포인트를 막아 WAL에 데이터가 남게 하려고


def test_snapshot_captures_uncheckpointed_wal_commits(tmp_path):
    """이 프로젝트에서 백업 방식을 바꾼 이유 그 자체.

    연결이 열려 있으면 체크포인트가 안 돌아서 최근 커밋이 -wal 에만 있다.
    본체만 복사하는 shutil.copy2 는 그 데이터를 통째로 놓친다."""
    src = str(tmp_path / "src.db")
    conn = make_db(src, rows=500)
    try:
        assert os.path.exists(src + "-wal"), "WAL 사이드카가 생겨야 이 테스트가 의미를 가진다"

        # (A) 옛 방식이 실제로 실패하는지 먼저 보여준다
        copied = str(tmp_path / "copy2.db")
        shutil.copy2(src, copied)
        with pytest.raises(sqlite3.DatabaseError):
            sqlite3.connect(copied).execute("SELECT COUNT(*) FROM prices").fetchone()

        # (B) 새 방식은 전부 담는다
        dest = str(tmp_path / "snap.db")
        info = snapshot(src, dest)
        assert info["counts"]["prices"] == 500
    finally:
        conn.close()


def test_verify_rejects_empty_prices(tmp_path):
    """빈 백업을 성공으로 처리하면, 복구가 필요한 날에야 빈 걸 알게 된다."""
    empty = str(tmp_path / "empty.db")
    conn = sqlite3.connect(empty)
    conn.execute("CREATE TABLE prices (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="prices 데이터가 없습니다"):
        verify(empty)


def test_snapshot_overwrites_existing_destination(tmp_path):
    """VACUUM INTO 는 대상 파일이 있으면 실패한다 — 두 번째 호출도 성공해야 한다."""
    src = str(tmp_path / "src.db")
    conn = make_db(src, rows=10)
    try:
        dest = str(tmp_path / "snap.db")
        snapshot(src, dest)
        info = snapshot(src, dest)
        assert info["counts"]["prices"] == 10
    finally:
        conn.close()


def test_offsite_backup_is_restorable_and_rotates(tmp_path):
    src = str(tmp_path / "src.db")
    conn = make_db(src, rows=42)
    backup_dir = str(tmp_path / "offsite")
    try:
        result = run_offsite_backup(src, backup_dir, keep=2)
        archive = result["archive"]
        assert archive.endswith(".db.gz")

        # 아카이브를 실제로 풀어서 읽을 수 있어야 한다
        restored = str(tmp_path / "restored.db")
        with gzip.open(archive, "rb") as fin, open(restored, "wb") as fout:
            shutil.copyfileobj(fin, fout)
        assert sqlite3.connect(restored).execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 42

        # 세대 회전: keep=2 를 넘으면 오래된 것부터 지운다
        for _ in range(2):
            run_offsite_backup(src, backup_dir, keep=2)
        assert len(list_archives(backup_dir)) == 2
    finally:
        conn.close()


def test_backup_to_creates_parent_directory(tmp_path):
    """cleanup_*.py 가 부르는 경로. 폴더가 없어도 실패하면 안 된다."""
    src = str(tmp_path / "src.db")
    conn = make_db(src, rows=5)
    try:
        dest = str(tmp_path / "nested" / "deeper" / "snap.db")
        info = backup_to(src, dest)
        assert os.path.exists(dest)
        assert info["counts"]["prices"] == 5
    finally:
        conn.close()


def test_snapshot_reports_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        snapshot(str(tmp_path / "없는파일.db"), str(tmp_path / "out.db"))
