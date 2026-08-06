# tests/test_api_prediction.py
# GET /api/prediction/{code} 스모크 테스트. ml/price_prediction.train_model이 None을 반환하지 않으려면
# 같은 카테고리에 최소 5개 이상의, 스펙 정규식이 파싱 가능한 상품이 있어야 한다.

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache

RAM_ROWS = [
    ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5-5600 (16GB)", 80000, "DDR5-5600 CL46 1.1V", "http://img/1.jpg"),
    ("2026-08-06", "DDR5 RAM", "삼성전자 DDR5-6000 (32GB)", 150000, "DDR5-6000 CL30 1.35V RGB", "http://img/2.jpg"),
    ("2026-08-06", "DDR5 RAM", "SK하이닉스 DDR5-5600 (16GB)", 85000, "DDR5-5600 CL40 1.1V", "http://img/3.jpg"),
    ("2026-08-06", "DDR5 RAM", "SK하이닉스 DDR5-6400 (32GB)", 170000, "DDR5-6400 CL32 1.4V RGB", "http://img/4.jpg"),
    ("2026-08-06", "DDR5 RAM", "마이크론 DDR5-5200 (8GB)", 45000, "DDR5-5200 CL42 1.1V", "http://img/5.jpg"),
    ("2026-08-06", "DDR5 RAM", "마이크론 DDR5-6000 (16GB)", 95000, "DDR5-6000 CL36 1.2V", "http://img/6.jpg"),
]


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    db_manager.insert_many_prices(RAM_ROWS)
    codes = {}
    for row in RAM_ROWS:
        product = row[2]
        codes[product] = db_manager.get_or_create_product_code("DDR5 RAM", product, product)

    # AI 노트북: FEATURE_EXTRACTORS에 없는 카테고리라 예측 미지원(404) 케이스 검증용.
    db_manager.insert_many_prices([
        ("2026-08-06", "AI 노트북", "맥북에어 M5 (16GB)", 2000000, "M5 / 16GB", "http://img/ai.jpg"),
    ])
    codes["ai"] = db_manager.get_or_create_product_code("AI 노트북", "맥북에어 M5 (16GB)", "맥북에어 M5 (16GB)")

    reset_cache()
    from api.main import app
    client = TestClient(app)
    client.ram_codes = codes
    yield client
    reset_cache()


def test_prediction_returns_full_breakdown(api_client):
    code = api_client.ram_codes["삼성전자 DDR5-6000 (32GB)"]
    resp = api_client.get(f"/api/prediction/{code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["product"] == "삼성전자 DDR5-6000 (32GB)"
    assert body["actual_price"] == 150000
    assert body["predicted_price"] >= 0
    assert body["model_name"] in ("Random Forest", "Linear Regression")
    assert body["data_count"] == 6
    assert len(body["contributions"]) > 0
    assert all(c["label"] for c in body["contributions"])


def test_prediction_404_for_unknown_code(api_client):
    resp = api_client.get("/api/prediction/RAM-999")
    assert resp.status_code == 404


def test_prediction_404_for_unsupported_category(api_client):
    resp = api_client.get(f"/api/prediction/{api_client.ram_codes['ai']}")
    assert resp.status_code == 404
