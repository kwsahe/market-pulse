# tests/test_db_manager.py
# DB 스키마 초기화 + 상품번호 레지스트리 + 수집 실행 이력 스모크 테스트.
# 실제 database/data.db를 건드리지 않도록 매 테스트마다 임시 DB 파일로 DB_PATH를 바꿔치기한다.

import pytest

import database.db_manager as db_manager


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """테스트 전용 임시 SQLite 파일로 DB_PATH를 바꿔서 실제 데이터에 영향을 주지 않는다"""
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    return db_path


def test_init_db_is_idempotent(temp_db):
    """init_db()를 여러 번 실행해도 에러 없이 통과해야 한다 (ALTER TABLE 가드 확인)"""
    db_manager.init_db()
    db_manager.init_db()


def test_schema_migrations_recorded(temp_db):
    """알려진 마이그레이션 이름들이 schema_migrations에 기록돼야 한다"""
    with db_manager.get_connection() as conn:
        rows = conn.execute("SELECT name FROM schema_migrations").fetchall()
    names = {row[0] for row in rows}
    assert "001_initial_prices_news" in names
    assert "008_tracked_laptops_target_price" in names


def test_product_registry_assigns_sequential_codes(temp_db):
    """같은 카테고리에서 새 상품마다 접두사+번호가 순서대로 발급돼야 한다 (RAM-1, RAM-2 ...)"""
    code1 = db_manager.get_or_create_product_code("DDR5 RAM", "pcode-a", "삼성전자 DDR5 16GB")
    code2 = db_manager.get_or_create_product_code("DDR5 RAM", "pcode-b", "SK하이닉스 DDR5 32GB")
    assert code1 == "RAM-1"
    assert code2 == "RAM-2"


def test_product_registry_is_idempotent_per_match_key(temp_db):
    """같은 (category, match_key)로 다시 호출하면 새 코드를 발급하지 않고 기존 코드를 반환해야 한다"""
    code1 = db_manager.get_or_create_product_code("CPU", "pcode-x", "AMD 라이젠5 9600X")
    code2 = db_manager.get_or_create_product_code("CPU", "pcode-x", "AMD 라이젠5 9600X (재고입고)")
    assert code1 == code2 == "CPU-1"

    code_map = db_manager.get_product_code_map("CPU")
    assert code_map["pcode-x"] == "CPU-1"


def test_scrape_run_lifecycle(temp_db):
    """수집 실행 시작->종료 기록이 정확히 남아야 한다"""
    run_id = db_manager.start_scrape_run("price")
    db_manager.finish_scrape_run(run_id, fetched_count=50, inserted_count=10, status="success")

    runs = db_manager.load_scrape_runs()
    assert len(runs) == 1
    row = runs.iloc[0]
    assert row["source"] == "price"
    assert row["status"] == "success"
    assert row["fetched_count"] == 50
    assert row["inserted_count"] == 10
    assert row["finished_at"] is not None


def test_scrape_run_records_failure(temp_db):
    run_id = db_manager.start_scrape_run("news")
    db_manager.finish_scrape_run(run_id, status="failed", error_message="네트워크 오류")

    runs = db_manager.load_scrape_runs()
    row = runs.iloc[0]
    assert row["status"] == "failed"
    assert row["error_message"] == "네트워크 오류"


def test_tracked_target_price_roundtrip(temp_db):
    """추적 대상 등록 -> 목표가 설정 -> 조회가 정상 동작해야 한다"""
    db_manager.set_laptop_tracked("pcode-1", True)
    db_manager.set_target_price("pcode-1", 1_000_000, "세일 노리는 중")

    targets = db_manager.load_tracked_targets()
    row = targets[targets["pcode"] == "pcode-1"].iloc[0]
    assert row["target_price"] == 1_000_000
    assert row["memo"] == "세일 노리는 중"

    # 목표가 해제
    db_manager.set_target_price("pcode-1", None, "")
    targets = db_manager.load_tracked_targets()
    row = targets[targets["pcode"] == "pcode-1"].iloc[0]
    assert row["target_price"] is None
