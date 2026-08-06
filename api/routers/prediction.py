# api/routers/prediction.py
# GET /api/prediction/{code} — dashboard/tabs/prediction.py 로직 이식.
# 모델 학습(ml/price_prediction.train_model)은 무거우니 api/deps.py의 model_cache(ttl=3600)로 감싼다
# (dashboard/tabs/common.py의 get_trained_model이 @st.cache_data(ttl=3600)로 하던 것과 동일 목적).

import pandas as pd
from fastapi import APIRouter, HTTPException

from ml.anomaly_detection import detect_zscore
from ml.price_prediction import (
    FEATURE_EXTRACTORS,
    compute_fair_price_score,
    compute_feature_contributions,
    find_similar_products,
    predict_price_range,
    train_model,
)
from api.deps import model_cache
from api.routers.prices import _load_prices_cached, latest_snapshot
from api.routers.products import _resolve_code, _match_key_for_row, _price_history_cached
from api.schemas import FeatureContribution, PredictionResponse, SimilarProduct

router = APIRouter(prefix="/api/prediction", tags=["prediction"])


@model_cache
def _get_model_cached(category: str):
    return train_model(category)


@router.get("/{code}", response_model=PredictionResponse)
def get_prediction(code: str) -> PredictionResponse:
    prices_df = _load_prices_cached()
    category, row = _resolve_code(code, prices_df)
    if row is None:
        raise HTTPException(status_code=404, detail=f"상품번호 '{code}'를 찾을 수 없어요.")

    extractor = FEATURE_EXTRACTORS.get(category)
    if extractor is None:
        raise HTTPException(status_code=404, detail=f"'{category}' 카테고리는 가격 예측을 지원하지 않아요.")

    model_info = _get_model_cached(category)
    if model_info is None:
        raise HTTPException(status_code=404, detail="예측 모델을 만들기엔 데이터가 부족해요. (카테고리당 최소 5개 필요)")

    features = extractor(row)
    predicted, low, high = predict_price_range(model_info, features)
    actual = int(row["price"])

    match_key = _match_key_for_row(row)
    pcode = row.get("pcode")
    by_pcode = bool(pcode) and str(pcode).strip() != ""
    history_df = _price_history_cached(category, match_key, by_pcode)
    hist_min = int(history_df["price"].min()) if not history_df.empty else None
    hist_max = int(history_df["price"].max()) if not history_df.empty else None

    current_df = latest_snapshot(prices_df)
    cat_current_df = current_df[current_df["category"] == category]
    z_df = detect_zscore(cat_current_df) if not cat_current_df.empty else pd.DataFrame()
    is_anomaly_high = (
        not z_df.empty and row["product"] in set(z_df["product"]) and actual >= predicted
    )

    fair_score, fair_label = compute_fair_price_score(actual, predicted, hist_min, hist_max, is_anomaly_high)

    contributions, _baseline = compute_feature_contributions(model_info, features)
    contributions = [c for c in contributions if abs(c["contribution"]) > 1]

    similar_df = find_similar_products(
        cat_current_df, features, extractor, model_info,
        exclude_product=row["product"], top_n=5,
    )

    return PredictionResponse(
        code=code,
        category=category,
        product=row["product"],
        actual_price=actual,
        predicted_price=predicted,
        low=low,
        high=high,
        fair_score=fair_score,
        fair_label=fair_label,
        model_name=model_info["model_name"],
        r2=model_info["best_r2"],
        data_count=model_info["data_count"],
        contributions=[FeatureContribution(**c) for c in contributions],
        similar_products=[
            SimilarProduct(product=r["product"], price=int(r["price"]), distance=r["distance"])
            for _, r in similar_df.iterrows()
        ],
    )
