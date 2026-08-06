# tests/test_api_spotlights.py
# GET /api/spotlights 스모크 테스트 (변동폭 TOP + 이상치/신제품 하이라이트).

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    # 가격 변동(top_movers)용 — 2일치 데이터
    db_manager.insert_many_prices([
        ("2026-08-05", "DDR5 RAM", "삼성전자 DDR5 16GB", 80000, "16GB", "http://img/a.jpg"),
        ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5 16GB", 120000, "16GB", "http://img/a.jpg"),
    ])
    db_manager.get_or_create_product_code("DDR5 RAM", "삼성전자 DDR5 16GB", "삼성전자 DDR5 16GB")

    # Z-score 이상치(notable)용 — n=10 (정상 9 + 극단치 1), tests/test_api_anomalies.py와 동일한 이유로
    # 표본이 작으면 |Z|>2.5를 절대 못 넘는다(표본표준편차 기준 한 점의 최대 |Z|는 sqrt(n-1)).
    normal_prices = [78000, 78500, 79000, 79500, 80000, 80500, 81000, 81500, 82000]
    rows = [
        ("2026-08-06", "CPU", f"CPU 상품{i}", price, "specs", f"http://img/cpu{i}.jpg")
        for i, price in enumerate(normal_prices)
    ]
    rows.append(("2026-08-06", "CPU", "CPU 이상고가", 50_000_000, "specs", "http://img/cpu_hi.jpg"))
    db_manager.insert_many_prices(rows)
    for row in rows:
        db_manager.get_or_create_product_code("CPU", row[2], row[2])

    # 신제품(notable)용 — 오늘 처음 잡힌 노트북
    db_manager.upsert_laptop_product("PCODE-NEW", "신형 노트북", "RTX5090", "http://detail", "raw specs")
    db_manager.insert_many_laptop_prices([
        ("2026-08-06", "게이밍 노트북", "신형 노트북", 4000000, "RTX5090", "http://img/new.jpg", "PCODE-NEW"),
    ])
    db_manager.get_or_create_product_code("게이밍 노트북", "PCODE-NEW", "신형 노트북")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_top_movers_includes_price_change(api_client):
    resp = api_client.get("/api/spotlights")
    assert resp.status_code == 200
    body = resp.json()
    mover_products = {i["product"] for i in body["top_movers"]}
    assert "삼성전자 DDR5 16GB" in mover_products


def test_notable_includes_anomaly_and_new_product(api_client):
    body = api_client.get("/api/spotlights").json()
    kinds = {(i["product"], i["kind"]) for i in body["notable"]}
    assert ("CPU 이상고가", "anomaly") in kinds
    assert ("신형 노트북", "new") in kinds
