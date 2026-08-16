# tests/test_api_categories.py
# GET /api/categories/{category}/pulse 스모크 테스트 (3D 데스크 부품 패널용 단일 카테고리 요약).

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
        # 어제 스냅샷
        ("2026-08-05", "DDR5 RAM", "삼성 DDR5 16GB", 82000, "16GB", "http://img/a.jpg"),
        ("2026-08-05", "DDR5 RAM", "마이크론 DDR5 32GB", 150000, "32GB", "http://img/b.jpg"),
        ("2026-08-05", "DDR5 RAM", "커세어 DDR5 64GB", 300000, "64GB", "http://img/c.jpg"),
        ("2026-08-05", "CPU", "라이젠 9800X3D", 620000, "8코어", "http://img/d.jpg"),
        # 오늘 스냅샷 — RAM은 하나 내리고 하나 오름
        ("2026-08-06", "DDR5 RAM", "삼성 DDR5 16GB", 78000, "16GB", "http://img/a.jpg"),
        ("2026-08-06", "DDR5 RAM", "마이크론 DDR5 32GB", 165000, "32GB", "http://img/b.jpg"),
        ("2026-08-06", "DDR5 RAM", "커세어 DDR5 64GB", 300000, "64GB", "http://img/c.jpg"),
        ("2026-08-06", "CPU", "라이젠 9800X3D", 620000, "8코어", "http://img/d.jpg"),
    ])

    reset_cache()
    from api.main import app
    yield TestClient(app)
    reset_cache()


def test_pulse_returns_snapshot_stats_and_trend(api_client):
    resp = api_client.get("/api/categories/DDR5 RAM/pulse")
    assert resp.status_code == 200
    body = resp.json()

    assert body["category"] == "DDR5 RAM"
    assert body["latest_date"] == "2026-08-06"
    assert body["count"] == 3
    assert body["min_price"] == 78000
    assert body["max_price"] == 300000
    assert body["median_price"] == 165000

    # 수집일 2개 → 추이 포인트 2개, 평균가 상승(177,333 vs 181,000)
    assert [p["date"] for p in body["trend"]] == ["2026-08-05", "2026-08-06"]
    assert body["trend"][0]["count"] == 3
    assert body["trend_pct"] > 0


def test_pulse_counts_changes_within_category_only(api_client):
    body = api_client.get("/api/categories/DDR5 RAM/pulse").json()
    # RAM만 집계돼야 한다 — 가격이 그대로인 CPU는 애초에 변동 목록에 없다
    assert body["up_count"] == 1
    assert body["down_count"] == 1

    movers = {m["product"]: m for m in body["movers"]}
    assert set(movers) == {"삼성 DDR5 16GB", "마이크론 DDR5 32GB"}
    assert movers["삼성 DDR5 16GB"]["change"] == -4000
    assert movers["마이크론 DDR5 32GB"]["change"] == 15000


def test_pulse_cheapest_is_sorted_ascending(api_client):
    body = api_client.get("/api/categories/DDR5 RAM/pulse").json()
    prices = [item["price"] for item in body["cheapest"]]
    assert prices == sorted(prices)
    assert prices[0] == 78000
    assert body["cheapest"][0]["image_url"] == "http://img/a.jpg"


def test_pulse_404_for_unknown_category(api_client):
    resp = api_client.get("/api/categories/없는카테고리/pulse")
    assert resp.status_code == 404
