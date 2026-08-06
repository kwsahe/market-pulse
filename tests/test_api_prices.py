# tests/test_api_prices.py
# GET /api/categories, GET /api/prices 스모크 테스트. 실제 database/data.db는 건드리지 않고
# tests/test_db_manager.py와 동일하게 임시 DB로 DB_PATH를 바꿔치기한다.

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
        ("2026-08-06", "DDR5 RAM", "SK하이닉스 DDR5 32GB", 150000, "32GB/5600MHz", "http://img/b.jpg"),
        ("2026-08-06", "CPU", "AMD 라이젠5 9600X", 300000, "6코어", "http://img/c.jpg"),
    ])
    db_manager.get_or_create_product_code("DDR5 RAM", "삼성전자 DDR5 16GB", "삼성전자 DDR5 16GB")
    db_manager.get_or_create_product_code("DDR5 RAM", "SK하이닉스 DDR5 32GB", "SK하이닉스 DDR5 32GB")
    db_manager.get_or_create_product_code("CPU", "AMD 라이젠5 9600X", "AMD 라이젠5 9600X")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_list_prices_returns_latest_snapshot_only(api_client):
    resp = api_client.get("/api/prices")
    assert resp.status_code == 200
    body = resp.json()
    # 삼성전자 상품은 08-05/08-06 두 번 수집됐지만 최신(08-06) 1건만 나와야 함
    assert body["total"] == 3
    assert all(item["date"] == "2026-08-06" for item in body["items"])


def test_list_prices_filters_by_category(api_client):
    resp = api_client.get("/api/prices", params={"category": "DDR5 RAM"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(item["category"] == "DDR5 RAM" for item in body["items"])


def test_list_prices_search_query(api_client):
    resp = api_client.get("/api/prices", params={"q": "하이닉스"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert "하이닉스" in body["items"][0]["product"]


def test_list_prices_includes_price_change(api_client):
    # 삼성전자 DDR5 16GB는 08-05(80000원) → 08-06(75000원)으로 하락했으니 change가 채워져야 함
    resp = api_client.get("/api/prices", params={"q": "삼성전자"})
    body = resp.json()
    item = body["items"][0]
    assert item["change"] == -5000
    assert item["change_pct"] == pytest.approx(-6.25, rel=1e-3)

    # SK하이닉스는 오늘 하루치 데이터뿐이라 비교 대상이 없어 change가 None이어야 함
    resp2 = api_client.get("/api/prices", params={"q": "하이닉스"})
    item2 = resp2.json()["items"][0]
    assert item2["change"] is None
    assert item2["change_pct"] is None


def test_list_prices_sort_desc(api_client):
    resp = api_client.get("/api/prices", params={"category": "DDR5 RAM", "sort": "price_desc"})
    body = resp.json()
    prices = [item["price"] for item in body["items"]]
    assert prices == sorted(prices, reverse=True)


def test_categories_summary(api_client):
    resp = api_client.get("/api/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product_count"] == 3
    cat_names = {c["category"] for c in body["categories"]}
    assert cat_names == {"DDR5 RAM", "CPU"}


def test_empty_db_returns_empty_not_error(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    reset_cache()

    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/prices")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0}

    resp2 = client.get("/api/categories")
    assert resp2.status_code == 200
    assert resp2.json()["product_count"] == 0
    reset_cache()
