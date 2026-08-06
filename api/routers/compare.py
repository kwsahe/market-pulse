# api/routers/compare.py
# GET /api/compare?codes=A,B,C — dashboard/tabs/compare.py 로직 이식 (같은 카테고리 2~5개 비교).

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ml.anomaly_detection import detect_zscore
from ml.price_prediction import FEATURE_EXTRACTORS, FEATURE_LABELS, compute_fair_price_score, predict_price_range
from api.routers.prediction import _get_model_cached
from api.routers.prices import _load_prices_cached, latest_snapshot
from api.routers.products import _match_key_for_row, _price_history_cached, _resolve_code
from api.schemas import CompareProduct, CompareResponse, SpecRow

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("", response_model=CompareResponse)
def compare_products(
    codes: str = Query(..., description="쉼표로 구분된 상품코드, 2~5개, 예: RAM-1,RAM-2"),
) -> CompareResponse:
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not 2 <= len(code_list) <= 5:
        raise HTTPException(status_code=400, detail="비교할 상품은 2~5개 선택해주세요.")

    prices_df = _load_prices_cached()
    resolved: list[tuple[str, pd.Series]] = []
    category: str | None = None
    for code in code_list:
        cat, row = _resolve_code(code, prices_df)
        if row is None:
            raise HTTPException(status_code=404, detail=f"상품번호 '{code}'를 찾을 수 없어요.")
        if category is None:
            category = cat
        elif cat != category:
            raise HTTPException(status_code=400, detail="같은 카테고리 상품만 비교할 수 있어요.")
        resolved.append((code, row))

    extractor = FEATURE_EXTRACTORS.get(category)
    model_info = _get_model_cached(category) if extractor else None

    current_df = latest_snapshot(prices_df)
    cat_current_df = current_df[current_df["category"] == category]
    z_df = detect_zscore(cat_current_df) if not cat_current_df.empty else pd.DataFrame()
    anomaly_products = set(z_df["product"]) if not z_df.empty else set()

    products: list[CompareProduct] = []
    spec_rows_per_product: list[dict] = []

    for code, row in resolved:
        price = int(row["price"])
        features = extractor(row) if extractor else {}
        predicted = None
        if extractor and model_info:
            predicted, _low, _high = predict_price_range(model_info, features)

        match_key = _match_key_for_row(row)
        pcode = row.get("pcode")
        by_pcode = bool(pcode) and str(pcode).strip() != ""
        history_df = _price_history_cached(category, match_key, by_pcode)
        hist_min = int(history_df["price"].min()) if not history_df.empty else None
        hist_max = int(history_df["price"].max()) if not history_df.empty else None

        fair_score = fair_label = None
        if predicted is not None:
            is_anomaly = row["product"] in anomaly_products and price >= predicted
            fair_score, fair_label = compute_fair_price_score(price, predicted, hist_min, hist_max, is_anomaly)

        products.append(CompareProduct(
            code=code, category=category, product=row["product"], image_url=row.get("image_url"),
            price=price, predicted_price=predicted, hist_min=hist_min, hist_max=hist_max,
            fair_score=fair_score, fair_label=fair_label,
        ))
        spec_rows_per_product.append(features)

    spec_table = []
    if spec_rows_per_product and spec_rows_per_product[0]:
        for fkey in spec_rows_per_product[0].keys():
            spec_table.append(SpecRow(
                label=FEATURE_LABELS.get(fkey, fkey),
                values=[float(feats.get(fkey, 0)) for feats in spec_rows_per_product],
            ))

    return CompareResponse(products=products, spec_table=spec_table)
