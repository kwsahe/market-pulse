# tests/test_api_alerts.py
# GET /api/alerts 스모크 테스트 (추적 상품 하락 알림 + 목표가 도달 알림).

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
        ("2026-08-05", "게이밍 노트북", "ASUS ROG STRIX G18", 3200000, "RTX5080/32GB", "http://img/gn.jpg", "PCODE-1"),
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18", 2900000, "RTX5080/32GB", "http://img/gn.jpg", "PCODE-1"),
    ])
    db_manager.get_or_create_product_code("게이밍 노트북", "PCODE-1", "ASUS ROG STRIX G18")
    db_manager.set_laptop_tracked("PCODE-1", True)

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_no_alerts_without_target_price(api_client):
    # 가격은 내렸지만(320만→290만) 목표가를 아직 안 정했으니 tracked_drops는 잡히고 target_reached는 비어야 함
    resp = api_client.get("/api/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["tracked_drops"]) == 1
    assert body["tracked_drops"][0]["product"] == "ASUS ROG STRIX G18"
    assert body["target_reached"] == []


def test_target_reached_alert(api_client):
    db_manager.set_target_price("PCODE-1", 3000000, "예산 300만")
    resp = api_client.get("/api/alerts")
    body = resp.json()
    assert len(body["target_reached"]) == 1
    item = body["target_reached"][0]
    assert item["price"] == 2900000
    assert item["target_price"] == 3000000


def test_no_alerts_when_nothing_tracked(tmp_path, monkeypatch):
    db_path = tmp_path / "untracked.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    db_manager.insert_many_laptop_prices([
        ("2026-08-05", "게이밍 노트북", "삼성 갤럭시북", 2000000, "specs", "http://img.jpg", "PCODE-9"),
        ("2026-08-06", "게이밍 노트북", "삼성 갤럭시북", 1800000, "specs", "http://img.jpg", "PCODE-9"),
    ])
    reset_cache()

    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/alerts")
    assert resp.json() == {"tracked_drops": [], "target_reached": []}
    reset_cache()
