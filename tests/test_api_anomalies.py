# tests/test_api_anomalies.py
# GET /api/anomalies 스모크 테스트 (카테고리 통계 + Z-score + IQR).

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    # Z-score(|Z|>2.5)는 표본 크기가 작으면 어떤 값도 절대 그 임계값을 넘을 수 없다
    # (표본표준편차 기준 한 점의 최대 |Z|는 sqrt(n-1) — n=5면 최대 2.0이라 이상치가 아무리 극단적이어도 못 잡힘).
    # n=10(정상 9개 + 극단치 1개)으로 sqrt(9)=3 여유를 두고, 정상 9개도 약간씩 값을 흩어서
    # IQR이 0이 되지 않게(0이면 detect_iqr이 그 카테고리를 통째로 건너뜀) 한다.
    normal_prices = [78000, 78500, 79000, 79500, 80000, 80500, 81000, 81500, 82000]
    rows = [
        ("2026-08-06", "DDR5 RAM", f"상품{i} (16GB)", price, "DDR5-5600 CL46", f"http://img/{i}.jpg")
        for i, price in enumerate(normal_prices)
    ]
    rows.append(("2026-08-06", "DDR5 RAM", "상품9-이상고가 (128GB)", 50_000_000, "DDR5-5600 ECC", "http://img/9.jpg"))
    db_manager.insert_many_prices(rows)
    for row in rows:
        name = row[2]
        db_manager.get_or_create_product_code("DDR5 RAM", name, name)

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_anomalies_category_stats(api_client):
    resp = api_client.get("/api/anomalies")
    assert resp.status_code == 200
    body = resp.json()
    stat = next(s for s in body["category_stats"] if s["category"] == "DDR5 RAM")
    assert stat["count"] == 10


def test_anomalies_detects_high_outlier(api_client):
    body = api_client.get("/api/anomalies").json()
    zscore_products = {a["product"] for a in body["zscore"]}
    iqr_products = {a["product"] for a in body["iqr"]}
    assert "상품9-이상고가 (128GB)" in zscore_products
    assert "상품9-이상고가 (128GB)" in iqr_products
    z_entry = next(a for a in body["zscore"] if a["product"] == "상품9-이상고가 (128GB)")
    assert z_entry["direction"] == "고가"
    assert z_entry["code"] != ""
