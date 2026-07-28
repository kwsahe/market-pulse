# tests/test_price_prediction.py
# GroupKFold 도입으로 고친 데이터 누수 회귀 테스트
# (같은 상품이 여러 수집일에 걸쳐 거의 동일한 값으로 반복 등장 -> 일반 KFold로 섞으면
#  같은 상품이 train/test에 동시에 들어가 R2가 과대평가됨. GroupKFold로 상품 단위 분리해야 한다.)

import numpy as np
import pandas as pd
from unittest.mock import patch
from sklearn.model_selection import cross_val_score as real_cross_val_score

from ml.price_prediction import train_model


def _make_ram_df() -> pd.DataFrame:
    """서로 다른 실제 상품(pcode) 3개가 각각 4번의 수집일에 걸쳐 반복 등장하는 것처럼
    합성 데이터를 만든다. variant 없는 단일 pcode이므로 그룹키는 pcode 자체가 돼야 한다."""
    specs_by_pcode = {
        "P1": ("6000MHz CL30 1.35V", "삼성전자 DDR5 (16GB)", 100_000),
        "P2": ("5600MHz CL36 1.1V", "SK하이닉스 DDR5 (32GB)", 150_000),
        "P3": ("6400MHz CL32 1.4V", "마이크론 DDR5 (48GB)", 200_000),
    }
    rows = []
    for pcode, (specs, product, base_price) in specs_by_pcode.items():
        for i, date in enumerate(["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]):
            rows.append({
                "date": date, "category": "DDR5 RAM", "product": product,
                "price": base_price + i * 100, "specs": specs, "pcode": pcode,
            })
    return pd.DataFrame(rows)


def test_train_model_returns_none_for_insufficient_data(monkeypatch):
    df = _make_ram_df().head(3)
    monkeypatch.setattr("ml.price_prediction.load_prices", lambda: df)
    assert train_model("DDR5 RAM") is None


def test_train_model_returns_none_for_unknown_category(monkeypatch):
    df = _make_ram_df()
    monkeypatch.setattr("ml.price_prediction.load_prices", lambda: df)
    assert train_model("존재하지 않는 카테고리") is None


def test_train_model_groups_cv_by_product_not_by_row(monkeypatch):
    """핵심 회귀 테스트: 교차검증이 행 단위(KFold)가 아니라 상품 단위(GroupKFold)로 쪼개져야 한다.
    그렇지 않으면 같은 상품의 반복 수집 행이 train/test에 동시에 들어가는 데이터 누수가 생긴다."""
    df = _make_ram_df()
    monkeypatch.setattr("ml.price_prediction.load_prices", lambda: df)

    captured = {}

    def spy_cross_val_score(estimator, X, y, groups=None, cv=None, scoring=None):
        captured["groups"] = groups
        captured["cv"] = cv
        return real_cross_val_score(estimator, X, y, groups=groups, cv=cv, scoring=scoring)

    with patch("ml.price_prediction.cross_val_score", side_effect=spy_cross_val_score):
        info = train_model("DDR5 RAM")

    assert info is not None
    assert captured["groups"] is not None, "GroupKFold를 쓰려면 groups가 cross_val_score에 전달돼야 한다"

    groups_arr = np.asarray(captured["groups"])
    # 3개의 고유 상품(pcode)만 있으므로 5-fold가 아니라 3-fold여야 한다
    assert captured["cv"].n_splits == 3
    assert set(groups_arr) == {"P1", "P2", "P3"}

    # 어떤 fold에서도 같은 상품이 train/test에 동시에 존재하면 안 된다 (핵심 누수 방지 검증)
    for train_idx, test_idx in captured["cv"].split(np.zeros(len(groups_arr)), groups=groups_arr):
        train_groups = set(groups_arr[train_idx])
        test_groups = set(groups_arr[test_idx])
        assert train_groups.isdisjoint(test_groups)


def test_train_model_returns_expected_shape(monkeypatch):
    df = _make_ram_df()
    monkeypatch.setattr("ml.price_prediction.load_prices", lambda: df)
    info = train_model("DDR5 RAM")

    assert info is not None
    for key in (
        "model", "model_name", "features", "scaler", "lr_r2", "rf_r2",
        "best_r2", "data_count", "category", "residual_p10", "residual_p90",
    ):
        assert key in info
    assert info["data_count"] == len(df)
    assert info["category"] == "DDR5 RAM"
    assert info["model_name"] in ("Linear Regression", "Random Forest")
