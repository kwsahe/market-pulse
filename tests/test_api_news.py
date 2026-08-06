# tests/test_api_news.py
# GET /api/news 스모크 테스트.

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    db_manager.insert_many_news([
        ("2026-08-06 09:00", "IT조선", "RTX5090 출시", "2026-08-06 08:00"),
        ("2026-08-06 09:00", "지디넷", "DDR5 가격 상승", "2026-08-05 12:00"),
    ])

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_news_returns_all_items(api_client):
    resp = api_client.get("/api/news")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    titles = {item["title"] for item in body["items"]}
    assert titles == {"RTX5090 출시", "DDR5 가격 상승"}


def test_news_sorted_by_published_at_desc(api_client):
    body = api_client.get("/api/news").json()
    assert body["items"][0]["title"] == "RTX5090 출시"  # 08-06이 08-05보다 최신
