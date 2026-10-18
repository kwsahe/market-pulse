# tests/test_variant_product_codes.py
# 회귀: 같은 pcode의 용량 변형(1TB/2TB/4TB)이 상품번호 하나를 공유해서, 변동 TOP에는 4TB로 뜬 번호가
# 상세페이지에선 1TB 가격·이력으로 열렸다 (실데이터 SSD-244, 2026-10-13).

from fastapi.testclient import TestClient

import database.db_manager as db_manager
from api.deps import reset_cache

PCODE = "28621400"


def test_variant_mover_code_opens_same_variant(tmp_path, monkeypatch):
    monkeypatch.setattr(db_manager, "DB_PATH", str(tmp_path / "test_data.db"))
    db_manager.init_db()
    db_manager.insert_many_laptop_prices([
        # 다나와 표기가 바뀐 날(띄어쓰기) — 같은 SKU로 이력이 이어져야 한다
        ("2026-10-11", "NVMe SSD", "삼성전자 포터블SSDT9 (1TB)", 282590, "", "", PCODE),
        ("2026-10-11", "NVMe SSD", "삼성전자 포터블SSDT9 (4TB)", 930060, "", "", PCODE),
        ("2026-10-12", "NVMe SSD", "삼성전자 포터블 SSD T9 (1TB)", 282590, "", "", PCODE),
        ("2026-10-12", "NVMe SSD", "삼성전자 포터블 SSD T9 (4TB)", 930050, "", "", PCODE),
        ("2026-10-13", "NVMe SSD", "삼성전자 포터블 SSD T9 (1TB)", 284390, "", "", PCODE),
        ("2026-10-13", "NVMe SSD", "삼성전자 포터블 SSD T9 (4TB)", 1320070, "", "", PCODE),
    ])
    # 이미 발급돼 있던 pcode 단위 번호 — 지우지 않고 그대로 둔 채 변형별 번호가 새로 나가야 한다
    db_manager.get_or_create_product_code("NVMe SSD", PCODE, "삼성전자 포터블 SSD T9")
    db_manager.backfill_product_registry()

    reset_cache()
    from api.main import app
    client = TestClient(app)
    try:
        movers = client.get("/api/spotlights").json()["top_movers"]
        mover = next(m for m in movers if m["product"].endswith("(4TB)"))
        detail = client.get(f"/api/products/{mover['code']}").json()
    finally:
        reset_cache()

    assert detail["product"] == "삼성전자 포터블 SSD T9 (4TB)"
    assert detail["price"] == mover["current_price"] == 1320070
    assert [p["price"] for p in detail["history"]] == [930060, 930050, 1320070]


def test_laptop_detail_headline_is_cheapest_option(tmp_path, monkeypatch):
    """노트북은 SSD 옵션을 한 모델(pcode)로 묶고 이력은 날짜별 최저가다. 헤드라인도 최저가 옵션이어야
    이력과 맞는다 — 예전엔 아무 행이나 골라서 999.9만 원 옵션 링크가 1,296만 원 옵션으로 열렸다 (GN-575)."""
    monkeypatch.setattr(db_manager, "DB_PATH", str(tmp_path / "test_data.db"))
    db_manager.init_db()
    db_manager.insert_many_laptop_prices([
        # 비싼 옵션을 먼저 넣는다 — '첫 행'을 고르는 구현이면 여기서 틀린다
        ("2026-10-18", "게이밍 노트북", "Razer Blade 16 (SSD 2TB + SSD 2TB)", 12960000, "", "", "PC-1"),
        ("2026-10-18", "게이밍 노트북", "Razer Blade 16 (SSD 2TB)", 9999000, "", "", "PC-1"),
    ])
    code = db_manager.get_or_create_product_code("게이밍 노트북", "PC-1", "Razer Blade 16")

    reset_cache()
    from api.main import app
    try:
        detail = TestClient(app).get(f"/api/products/{code}").json()
    finally:
        reset_cache()

    assert detail["product"] == "Razer Blade 16 (SSD 2TB)"
    assert detail["price"] == 9999000 == detail["history"][-1]["price"]
