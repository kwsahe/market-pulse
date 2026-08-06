# api/routers/anomalies.py
# GET /api/anomalies — dashboard/tabs/anomalies.py의 3개 서브탭(카테고리별 통계/Z-score/IQR)을
# 한 응답으로 합친다. z_anomalies/iqr_anomalies를 한 번만 계산해 공유하는 원본 구조와 동일.

import pandas as pd
from fastapi import APIRouter

from ml.anomaly_detection import detect_zscore, detect_iqr
from api.routers.prices import _load_prices_cached, latest_snapshot, code_for_row
from api.schemas import AnomaliesResponse, AnomalyCategoryStat, ZScoreAnomaly, IqrAnomaly

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("", response_model=AnomaliesResponse)
def get_anomalies() -> AnomaliesResponse:
    prices_df = _load_prices_cached()
    current_df = latest_snapshot(prices_df)
    if current_df.empty:
        return AnomaliesResponse(category_stats=[], zscore=[], iqr=[])

    category_stats = [
        AnomalyCategoryStat(
            category=cat,
            count=len(cat_df),
            mean=float(cat_df["price"].mean()),
            min=float(cat_df["price"].min()),
            max=float(cat_df["price"].max()),
            std=float(cat_df["price"].std()) if len(cat_df) > 1 else 0.0,
        )
        for cat, cat_df in current_df.groupby("category")
    ]

    code_map_cache: dict = {}

    z_df = detect_zscore(current_df)
    zscore = [
        ZScoreAnomaly(
            code=code_for_row(row, code_map_cache),
            category=row["category"],
            product=row["product"],
            price=int(row["price"]),
            direction="고가" if row["z_score"] > 0 else "저가",
            z_score=float(row["z_score"]),
        )
        for _, row in z_df.iterrows()
    ] if not z_df.empty else []

    iqr_df = detect_iqr(current_df)
    iqr = [
        IqrAnomaly(
            code=code_for_row(row, code_map_cache),
            category=row["category"],
            product=row["product"],
            price=int(row["price"]),
            direction="고가" if row["price"] > row["upper_bound"] else "저가",
            lower_bound=float(row["lower_bound"]),
            upper_bound=float(row["upper_bound"]),
        )
        for _, row in iqr_df.iterrows()
    ] if not iqr_df.empty else []

    return AnomaliesResponse(category_stats=category_stats, zscore=zscore, iqr=iqr)
