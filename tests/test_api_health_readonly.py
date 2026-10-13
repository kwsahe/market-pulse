# tests/test_api_health_readonly.py
# 배포 관련 두 장치를 고정한다.
#   1) /api/health 가 "데이터 신선도"를 돌려주는가 (예전엔 {"status":"ok"} 고정이라 무용했다)
#   2) READONLY 모드에서 공개 노출면에 쓰기 라우트가 정말 0개인가
#
# 두 값 모두 api.main 이 **import 시점에** 읽으므로, 환경변수를 바꾼 뒤 모듈을 다시 불러와야 한다.

import importlib
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


def load_app(monkeypatch, tmp_path, *, readonly: bool, latest_date=None, rows=3):
    """임시 DB를 채우고 api.main 을 원하는 모드로 다시 로드한다."""
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()
    if latest_date:
        db_manager.insert_many_prices([
            (latest_date, "DDR5 RAM", f"삼성전자 DDR5 {i}", 80000 + i, "16GB", "http://img/a.jpg")
            for i in range(rows)
        ])

    monkeypatch.setenv("MARKET_PULSE_READONLY", "1" if readonly else "0")
    # health() 는 db_manager.DB_PATH 를 import 시점 값으로 잡으므로 같이 맞춰준다
    monkeypatch.setenv("MARKET_PULSE_DB_PATH", str(db_path))

    for mod in ("api.main",):
        sys.modules.pop(mod, None)
    api_main = importlib.import_module("api.main")
    reset_cache()
    return TestClient(api_main.app)


def test_health_reports_freshness(monkeypatch, tmp_path):
    today = date.today().isoformat()
    client = load_app(monkeypatch, tmp_path, readonly=False, latest_date=today, rows=5)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["last_scrape_date"] == today
    assert body["days_stale"] == 0
    assert body["rows"] == 5
    assert body["categories"] == 1


def test_health_flags_stale_data(monkeypatch, tmp_path):
    """수집이 조용히 멈추는 게 이 프로젝트의 가장 그럴듯한 실패다.
    하루 지연은 아직 정상(오늘 배치 전), 이틀부터 이상으로 본다."""
    old = (date.today() - timedelta(days=4)).isoformat()
    client = load_app(monkeypatch, tmp_path, readonly=False, latest_date=old)
    body = client.get("/api/health").json()
    assert body["status"] == "stale"
    assert body["days_stale"] == 4


def test_health_yesterday_is_still_ok(monkeypatch, tmp_path):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client = load_app(monkeypatch, tmp_path, readonly=False, latest_date=yesterday)
    body = client.get("/api/health").json()
    assert body["status"] == "ok", "하루 지연은 오늘 배치 전이라 정상이어야 한다"


def test_health_reports_empty_db(monkeypatch, tmp_path):
    client = load_app(monkeypatch, tmp_path, readonly=False, latest_date=None)
    body = client.get("/api/health").json()
    assert body["status"] == "empty"
    assert body["rows"] == 0


def test_readonly_exposes_no_write_routes(monkeypatch, tmp_path):
    """공개 URL에 인증 없는 쓰기가 열리는 것을 구조적으로 막는다.
    라우트를 등록하지 않으므로 인증 코드 0줄로 노출면이 사라진다."""
    client = load_app(monkeypatch, tmp_path, readonly=True, latest_date=date.today().isoformat())
    spec = client.get("/openapi.json").json()
    writes = [
        (path, method)
        for path, ops in spec["paths"].items()
        for method in ops
        if method in ("post", "put", "patch", "delete")
    ]
    assert writes == [], f"읽기전용인데 쓰기 라우트가 노출됨: {writes}"


def test_readonly_keeps_watchlist_readable(monkeypatch, tmp_path):
    """조회까지 막으면 프론트가 SPA 폴백 HTML을 받아 JSON 파싱 에러로 죽는다.
    위험한 건 쓰기지 조회가 아니다."""
    client = load_app(monkeypatch, tmp_path, readonly=True, latest_date=date.today().isoformat())
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


def test_writable_mode_registers_writes(monkeypatch, tmp_path):
    client = load_app(monkeypatch, tmp_path, readonly=False, latest_date=date.today().isoformat())
    spec = client.get("/openapi.json").json()
    writes = [
        (path, method)
        for path, ops in spec["paths"].items()
        for method in ops
        if method in ("post", "put")
    ]
    assert writes, "쓰기 허용 모드에서는 워치리스트 쓰기 라우트가 있어야 한다"


@pytest.fixture(autouse=True)
def _restore_api_main():
    """모듈을 다시 로드하는 테스트라, 끝난 뒤 다른 테스트에 영향이 가지 않게 되돌린다."""
    yield
    sys.modules.pop("api.main", None)
    reset_cache()
