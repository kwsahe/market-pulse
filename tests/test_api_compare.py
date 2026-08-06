# tests/test_api_compare.py
# GET /api/compare 스모크 테스트.

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache

RAM_ROWS = [
    ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5-5600 (16GB)", 80000, "DDR5-5600 CL46 1.1V", "http://img/1.jpg"),
    ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5-6000 (32GB)", 150000, "DDR5-6000 CL30 1.35V RGB", "http://img/2.jpg"),
    ("2026-08-06", "DDR5 RAM", "SK하이닉스 DDR5-5600 (16GB)", 85000, "DDR5-5600 CL40 1.1V", "http://img/3.jpg"),
    ("2026-08-06", "DDR5 RAM", "SK하이닉스 DDR5-6400 (32GB)", 170000, "DDR5-6400 CL32 1.4V RGB", "http://img/4.jpg"),
    ("2026-08-06", "DDR5 RAM", "마이크론 DDR5-5200 (8GB)", 45000, "DDR5-5200 CL42 1.1V", "http://img/5.jpg"),
]


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    db_manager.insert_many_prices(RAM_ROWS)
    codes = {row[2]: db_manager.get_or_create_product_code("DDR5 RAM", row[2], row[2]) for row in RAM_ROWS}

    db_manager.insert_many_prices([
        ("2026-08-06", "CPU", "인텔 코어i5", 300000, "6코어", "http://img/cpu.jpg"),
    ])
    codes["cpu"] = db_manager.get_or_create_product_code("CPU", "인텔 코어i5", "인텔 코어i5")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    client.ram_codes = codes
    yield client
    reset_cache()


def test_compare_two_products(api_client):
    c1 = api_client.ram_codes["삼성전자 DDR5-5600 (16GB)"]
    c2 = api_client.ram_codes["삼성전자 DDR5-6000 (32GB)"]
    resp = api_client.get("/api/compare", params={"codes": f"{c1},{c2}"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["products"]) == 2
    assert len(body["spec_table"]) > 0
    assert len(body["spec_table"][0]["values"]) == 2


def test_compare_requires_at_least_two(api_client):
    c1 = api_client.ram_codes["삼성전자 DDR5-5600 (16GB)"]
    resp = api_client.get("/api/compare", params={"codes": c1})
    assert resp.status_code == 400


def test_compare_rejects_mixed_categories(api_client):
    c1 = api_client.ram_codes["삼성전자 DDR5-5600 (16GB)"]
    c2 = api_client.ram_codes["cpu"]
    resp = api_client.get("/api/compare", params={"codes": f"{c1},{c2}"})
    assert resp.status_code == 400
