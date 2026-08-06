# api/routers/categories.py
# GET /api/categories — 카테고리별 평균가/상품수(오늘자 스냅샷 기준) + 개요 스탯 카드 요약
# dashboard/app.py의 stat_cards 6종(상품/카테고리/평균가/인상/인하/이상치) 계산 로직과 동일하게 맞춘다.

import pandas as pd
from fastapi import APIRouter

from ml.anomaly_detection import detect_zscore
from api.routers.prices import _load_prices_cached, _price_changes_cached, latest_snapshot
from api.schemas import CategoriesResponse, CategoryStat

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=CategoriesResponse)
def get_categories() -> CategoriesResponse:
    prices_df = _load_prices_cached()
    current_df = latest_snapshot(prices_df)

    if current_df.empty:
        return CategoriesResponse(
            categories=[], product_count=0, avg_price=0.0,
            up_count=0, down_count=0, anomaly_count=0,
        )

    avg_by_cat = current_df.groupby("category")["price"].mean()
    count_by_cat = current_df.groupby("category")["product"].count()
    categories = [
        CategoryStat(category=cat, avg_price=float(avg_by_cat[cat]), count=int(count_by_cat[cat]))
        for cat in avg_by_cat.index
    ]

    z_anomalies = detect_zscore(current_df)
    anomaly_count = len(z_anomalies) if not z_anomalies.empty else 0

    change_result = _price_changes_cached() if not prices_df.empty else pd.DataFrame()
    if isinstance(change_result, tuple):
        changed_df, _latest_date, _prev_date = change_result
        up_count = int((changed_df["change"] > 0).sum()) if not changed_df.empty else 0
        down_count = int((changed_df["change"] < 0).sum()) if not changed_df.empty else 0
    else:
        up_count = 0
        down_count = 0

    return CategoriesResponse(
        categories=categories,
        product_count=len(current_df),
        avg_price=float(current_df["price"].mean()),
        up_count=up_count,
        down_count=down_count,
        anomaly_count=anomaly_count,
    )
