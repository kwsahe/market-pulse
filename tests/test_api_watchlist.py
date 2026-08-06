# tests/test_api_watchlist.py
# GET/POST/PUT /api/watchlist 스모크 테스트 (유일한 mutation 엔드포인트).

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    db_manager.insert_many_laptop_prices([
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18", 3200000, "RTX5080/32GB", "http://img/gn.jpg", "PCODE-1"),
    ])
    db_manager.get_or_create_product_code("게이밍 노트북", "PCODE-1", "ASUS ROG STRIX G18")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_watchlist_empty_initially(api_client):
    resp = api_client.get("/api/watchlist")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_track_then_appears_in_watchlist(api_client):
    resp = api_client.post("/api/watchlist/PCODE-1", json={"tracked": True})
    assert resp.status_code == 200

    body = api_client.get("/api/watchlist").json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["pcode"] == "PCODE-1"
    assert item["price"] == 3200000
    assert item["target_price"] is None
    assert item["target_reached"] is False


def test_set_target_price_and_reach_it(api_client):
    api_client.post("/api/watchlist/PCODE-1", json={"tracked": True})

    resp = api_client.put("/api/watchlist/PCODE-1/target", json={"target_price": 3500000, "memo": "예산 여유"})
    assert resp.status_code == 200

    item = api_client.get("/api/watchlist").json()["items"][0]
    assert item["target_price"] == 3500000
    assert item["memo"] == "예산 여유"
    assert item["target_reached"] is True  # 현재가 320만 <= 목표가 350만


def test_set_target_for_untracked_pcode_404s(api_client):
    resp = api_client.put("/api/watchlist/NOT-TRACKED/target", json={"target_price": 100, "memo": ""})
    assert resp.status_code == 404


def test_untrack_removes_from_watchlist(api_client):
    api_client.post("/api/watchlist/PCODE-1", json={"tracked": True})
    api_client.post("/api/watchlist/PCODE-1", json={"tracked": False})

    body = api_client.get("/api/watchlist").json()
    assert body["items"] == []


def test_same_pcode_variants_dedup_to_lowest_price(api_client):
    # 같은 pcode의 SSD 용량 변형 등 여러 행이 있어도 최저가 1건만 대표로 나와야 한다
    # (dashboard/laptop_view.py의 drop_duplicates(subset="pcode", keep="first") 동작과 동일).
    db_manager.insert_many_laptop_prices([
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18 (SSD 2TB)", 3500000, "RTX5080/32GB", "http://img/gn2.jpg", "PCODE-1"),
    ])
    api_client.post("/api/watchlist/PCODE-1", json={"tracked": True})

    body = api_client.get("/api/watchlist").json()
    assert len(body["items"]) == 1
    assert body["items"][0]["price"] == 3200000
