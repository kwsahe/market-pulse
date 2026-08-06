# tests/test_api_scrapes.py
# GET /api/scrape-runs 스모크 테스트.

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    run1 = db_manager.start_scrape_run("danawa")
    db_manager.finish_scrape_run(run1, fetched_count=100, inserted_count=10, status="success")
    run2 = db_manager.start_scrape_run("naver_news")
    db_manager.finish_scrape_run(run2, fetched_count=0, inserted_count=0, status="failed", error_message="timeout")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_scrape_runs_summary_and_latest(api_client):
    resp = api_client.get("/api/scrape-runs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == {"total": 2, "success": 1, "failed": 1, "running": 0}
    sources = {r["source"] for r in body["latest_by_source"]}
    assert sources == {"danawa", "naver_news"}
    failed_run = next(r for r in body["latest_by_source"] if r["source"] == "naver_news")
    assert failed_run["error_message"] == "timeout"


def test_scrape_runs_empty_db(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    reset_cache()

    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/scrape-runs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["runs"] == []
    assert body["summary"]["total"] == 0
    reset_cache()
