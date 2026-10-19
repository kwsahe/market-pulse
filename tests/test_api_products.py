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


def _main_images(body):
    return [img["image_url"] for img in body["images"] if img["image_type"] == "main"]


def test_get_product_detail_falls_back_to_listing_image_for_parts(api_client):
    """부품은 laptop_images 에 사진이 없다 — 가격 행의 image_url 을 대표 이미지로 쓴다.
    예전엔 API가 laptop_images 만 봐서 부품 상세가 전부 '이미지 없음'이었다(Streamlit 쪽은 이미 이렇게 했다)."""
    assert _main_images(api_client.get(f"/api/products/{api_client.ram_code}").json()) == ["http://img/a.jpg"]

    db_manager.insert_many_laptop_prices([
        ("2026-08-06", "NVMe SSD", "삼성전자 990 PRO (1TB)", 200000, "", "https://img/ssd.jpg", "SSD-PC"),
    ])
    ssd_code = db_manager.get_or_create_product_code("NVMe SSD", "SSD-PC (1TB)", "삼성전자 990 PRO (1TB)")
    reset_cache()
    assert _main_images(api_client.get(f"/api/products/{ssd_code}").json()) == ["https://img/ssd.jpg"]


def test_get_product_detail_keeps_laptop_main_image_without_duplicate(api_client):
    """노트북은 laptop_images 의 대표 이미지가 있으니 가격 행 이미지를 또 붙이지 않는다."""
    assert _main_images(api_client.get(f"/api/products/{api_client.laptop_code}").json()) == ["http://img/gn_main.jpg"]


def test_get_product_detail_404_for_unknown_code(api_client):
    resp = api_client.get("/api/products/RAM-999")
    assert resp.status_code == 404
