# tests/test_api_changes.py
# GET /api/changes 스모크 테스트.

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    db_manager.insert_many_prices([
        ("2026-08-05", "DDR5 RAM", "삼성전자 DDR5 16GB", 80000, "16GB/5600MHz", "http://img/a.jpg"),
        ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5 16GB", 75000, "16GB/5600MHz", "http://img/a.jpg"),
        ("2026-08-05", "CPU", "AMD 라이젠5 9600X", 300000, "6코어", "http://img/c.jpg"),
        ("2026-08-06", "CPU", "AMD 라이젠5 9600X", 320000, "6코어", "http://img/c.jpg"),
    ])
    db_manager.get_or_create_product_code("DDR5 RAM", "삼성전자 DDR5 16GB", "삼성전자 DDR5 16GB")
    db_manager.get_or_create_product_code("CPU", "AMD 라이젠5 9600X", "AMD 라이젠5 9600X")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_changes_splits_up_and_down(api_client):
    resp = api_client.get("/api/changes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_changes"] is True
    assert body["prev_date"] == "2026-08-05"
    assert body["latest_date"] == "2026-08-06"

    up_products = {i["product"] for i in body["up"]}
    down_products = {i["product"] for i in body["down"]}
    assert "AMD 라이젠5 9600X" in up_products
    assert "삼성전자 DDR5 16GB" in down_products

    up_item = next(i for i in body["up"] if i["product"] == "AMD 라이젠5 9600X")
    assert up_item["change"] == 20000
    assert up_item["code"] == "CPU-1"


def test_changes_no_data_returns_has_changes_false(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    reset_cache()

    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/changes")
    assert resp.status_code == 200
    assert resp.json() == {"has_changes": False, "prev_date": None, "latest_date": None, "up": [], "down": []}
    reset_cache()
