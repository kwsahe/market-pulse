# tests/test_api_products.py
# GET /api/products/{code} 스모크 테스트 (조회 성공 / 404 / 노트북 이미지 포함 케이스).

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
        ("2026-08-05", "DDR5 RAM", "삼성전자 DDR5 16GB", 82000, "16GB/5600MHz", "http://img/a.jpg"),
        ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5 16GB", 78000, "16GB/5600MHz", "http://img/a.jpg"),
    ])
    code = db_manager.get_or_create_product_code("DDR5 RAM", "삼성전자 DDR5 16GB", "삼성전자 DDR5 16GB")

    db_manager.insert_many_laptop_prices([
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18", 3200000, "RTX5080/32GB", "http://img/gn.jpg", "PCODE-1"),
    ])
    laptop_code = db_manager.get_or_create_product_code("게이밍 노트북", "PCODE-1", "ASUS ROG STRIX G18")
    db_manager.save_laptop_images("PCODE-1", [
        ("http://img/gn_main.jpg", "main", 0),
        ("http://img/gn_detail.jpg", "detail", 0),
    ])

    reset_cache()
    from api.main import app
    client = TestClient(app)
    client.ram_code = code
    client.laptop_code = laptop_code
    yield client
    reset_cache()


def test_get_product_detail_returns_history_and_stats(api_client):
    resp = api_client.get(f"/api/products/{api_client.ram_code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product"] == "삼성전자 DDR5 16GB"
    assert body["price"] == 78000
    assert len(body["history"]) == 2
    assert body["hist_min"] == 78000
    assert body["hist_max"] == 82000


def test_get_product_detail_includes_laptop_images(api_client):
    resp = api_client.get(f"/api/products/{api_client.laptop_code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pcode"] == "PCODE-1"
    image_types = {img["image_type"] for img in body["images"]}
    assert image_types == {"main", "detail"}


def test_get_product_detail_404_for_unknown_code(api_client):
    resp = api_client.get("/api/products/RAM-999")
    assert resp.status_code == 404
