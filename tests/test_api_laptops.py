# tests/test_api_laptops.py
# GET /api/laptops/{category} 스모크 테스트 (필터 옵션 + 스펙/이미지/베스트바이/추적/신제품 조합).

import pytest
from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data.db"
    monkeypatch.setattr(db_manager, "DB_PATH", str(db_path))
    db_manager.init_db()

    # 2일치 가격(베스트바이/변동값 계산용) — 08-05가 역대 최저가
    db_manager.insert_many_laptop_prices([
        ("2026-08-05", "게이밍 노트북", "ASUS ROG STRIX G18", 3000000, "RTX5080/32GB", "http://img/main.jpg", "PCODE-1"),
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18", 3200000, "RTX5080/32GB", "http://img/main.jpg", "PCODE-1"),
        # 같은 pcode의 SSD 용량 변형 — 최저가만 대표로 남아야 함
        ("2026-08-06", "게이밍 노트북", "ASUS ROG STRIX G18 (SSD 2TB)", 3500000, "RTX5080/32GB", "http://img/main.jpg", "PCODE-1"),
    ])
    db_manager.get_or_create_product_code("게이밍 노트북", "PCODE-1", "ASUS ROG STRIX G18")
    db_manager.save_laptop_specs("PCODE-1", {"GPU 칩셋": "RTX5080", "제조회사": "ASUS(공식)", "무게": "2.5kg"})
    db_manager.save_laptop_images("PCODE-1", [
        ("http://img/main.jpg", "main", 0),
        ("http://img/detail1.jpg", "detail", 0),
    ])
    db_manager.set_laptop_tracked("PCODE-1", True)

    reset_cache()
    from api.main import app
    client = TestClient(app)
    yield client
    reset_cache()


def test_laptops_dedups_by_pcode_to_lowest_price(api_client):
    resp = api_client.get("/api/laptops/게이밍 노트북")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["price"] == 3200000  # 오늘자 두 변형 중 더 싼 쪽(320만 < 350만)


def test_laptops_includes_specs_images_and_best_buy(api_client):
    body = api_client.get("/api/laptops/게이밍 노트북").json()
    item = body["items"][0]

    assert item["tracked"] is True
    assert {s["spec_key"] for s in item["full_specs"]} == {"GPU 칩셋", "제조회사", "무게"}
    assert len(item["images"]) == 2

    # filter_values는 괄호 부가설명이 제거된 "정제된" 값이어야 함 ("ASUS(공식)" -> "ASUS")
    assert item["filter_values"]["제조회사"] == "ASUS"
    assert "ASUS" in body["filter_options"]["제조회사"]

    # 역대 최저가(08-05, 300만)보다 지금(320만)이 비싸므로 best_buy가 채워져야 함
    assert item["best_buy"]["savings"] == 200000
    assert item["best_buy"]["is_best_now"] is False


def test_laptops_unknown_category_returns_empty(api_client):
    resp = api_client.get("/api/laptops/존재하지않는카테고리")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["new_count"] == 0
