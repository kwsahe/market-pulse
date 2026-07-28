# tests/test_price_change.py
# 가격 변동 감지의 pcode 우선 매칭 로직 검증
# (2026-07-28 세션에서 "상품명이 살짝 바뀌면 매칭이 끊기는" 문제를 고치며 추가된 회귀 테스트)

import pandas as pd
import pytest

from ml.price_change import _pcode_match_key, detect_price_changes


def test_pcode_match_key_uses_pcode_when_unique():
    """그날 그 pcode가 한 번만 등장하면(용량 variant 없음) pcode 자체를 키로 쓴다"""
    df = pd.DataFrame({
        "product": ["삼성전자 9100 PRO 1TB", "SK하이닉스 P51 1TB"],
        "pcode": ["111", "222"],
    })
    key = _pcode_match_key(df)
    assert list(key) == ["111", "222"]


def test_pcode_match_key_falls_back_to_product_for_variants():
    """같은 pcode가 여러 번(용량 variant) 등장하면 pcode만으로 구분이 안 되므로
    상품명 매칭(2순위)에 맡기기 위해 빈 문자열을 반환해야 한다"""
    df = pd.DataFrame({
        "product": ["삼성전자 RAM (16GB)", "삼성전자 RAM (32GB)"],
        "pcode": ["999", "999"],
    })
    key = _pcode_match_key(df)
    assert list(key) == ["", ""]


def test_pcode_match_key_falls_back_to_empty_when_missing():
    """pcode가 없는(과거 데이터) 행은 빈 문자열 — 상품명 매칭 폴백 대상"""
    df = pd.DataFrame({
        "product": ["옛날 상품"],
        "pcode": [None],
    })
    key = _pcode_match_key(df)
    assert list(key) == [""]


def test_detect_price_changes_matches_by_pcode_despite_name_drift(monkeypatch):
    """다나와가 상품명 표기를 살짝 바꿔도(예: 프로모 문구 추가) pcode가 같으면
    같은 상품으로 인식해서 가격 변동을 잡아내야 한다"""
    df = pd.DataFrame([
        {"date": "2026-07-27", "category": "CPU", "product": "AMD 라이젠5 9600X", "price": 300_000, "pcode": "500"},
        {"date": "2026-07-28", "category": "CPU", "product": "AMD 라이젠5 9600X (신규입고)", "price": 280_000, "pcode": "500"},
    ])
    monkeypatch.setattr("ml.price_change.load_prices", lambda: df)

    changed, latest_date, prev_date = detect_price_changes()

    assert latest_date == "2026-07-28"
    assert prev_date == "2026-07-27"
    assert len(changed) == 1
    row = changed.iloc[0]
    assert row["product"] == "AMD 라이젠5 9600X (신규입고)"
    assert row["prev_price"] == 300_000
    assert row["current_price"] == 280_000
    assert row["change"] == -20_000


def test_detect_price_changes_falls_back_to_product_name_without_pcode(monkeypatch):
    """pcode가 없는(구버전 스크래퍼로 모은) 데이터는 기존처럼 상품명으로 매칭돼야 한다"""
    df = pd.DataFrame([
        {"date": "2026-07-27", "category": "DDR5 RAM", "product": "삼성전자 DDR5 32GB", "price": 150_000, "pcode": None},
        {"date": "2026-07-28", "category": "DDR5 RAM", "product": "삼성전자 DDR5 32GB", "price": 160_000, "pcode": None},
    ])
    monkeypatch.setattr("ml.price_change.load_prices", lambda: df)

    changed, _, _ = detect_price_changes()

    assert len(changed) == 1
    assert changed.iloc[0]["change"] == 10_000


def test_detect_price_changes_ignores_unchanged_prices(monkeypatch):
    df = pd.DataFrame([
        {"date": "2026-07-27", "category": "CPU", "product": "동일 가격 상품", "price": 100_000, "pcode": "1"},
        {"date": "2026-07-28", "category": "CPU", "product": "동일 가격 상품", "price": 100_000, "pcode": "1"},
    ])
    monkeypatch.setattr("ml.price_change.load_prices", lambda: df)

    changed, _, _ = detect_price_changes()
    assert changed.empty


def test_detect_price_changes_empty_df_returns_empty_dataframe(monkeypatch):
    monkeypatch.setattr("ml.price_change.load_prices", lambda: pd.DataFrame())
    result = detect_price_changes()
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_detect_price_changes_single_date_returns_empty_dataframe(monkeypatch):
    df = pd.DataFrame([
        {"date": "2026-07-28", "category": "CPU", "product": "상품", "price": 100_000, "pcode": "1"},
    ])
    monkeypatch.setattr("ml.price_change.load_prices", lambda: df)
    result = detect_price_changes()
    assert isinstance(result, pd.DataFrame)
    assert result.empty
