# api/routers/prices.py
# GET /api/prices — 최신 스냅샷 목록 (검색/카테고리 필터/정렬/페이지네이션 + 이상치 여부/전일 대비 변동값)

import pandas as pd
from fastapi import APIRouter, Query

from database.db_manager import load_prices, get_product_code_map
from ml.anomaly_detection import detect_zscore
from ml.price_change import detect_price_changes
from api.deps import data_cache
from api.schemas import PriceListResponse, ProductSummary

router = APIRouter(prefix="/api/prices", tags=["prices"])


@data_cache
def _load_prices_cached() -> pd.DataFrame:
    return load_prices()


@data_cache
def _code_map_cached(category: str) -> dict:
    return get_product_code_map(category)


@data_cache
def _price_changes_cached():
    return detect_price_changes()


def latest_snapshot(prices_df: pd.DataFrame) -> pd.DataFrame:
    """전체 가격 이력에서 최신 수집일자 데이터만 추려낸다 (dashboard/app.py의 current_df와 동일 로직)."""
    if prices_df.empty:
        return prices_df
    latest_date = prices_df["date"].max()
    return prices_df[prices_df["date"] == latest_date].copy()


def code_for_row(row: pd.Series, code_map_cache: dict) -> str:
    category = row["category"]
    if category not in code_map_cache:
        code_map_cache[category] = _code_map_cached(category)
    match_key = row["pcode"] if row.get("pcode") else row["product"]
    return code_map_cache[category].get(match_key, "")


@router.get("", response_model=PriceListResponse)
def list_prices(
    category: str | None = Query(None, description="카테고리 필터, 예: 'DDR5 RAM'"),
    q: str | None = Query(None, description="상품명 검색어"),
    sort: str = Query("price_asc", pattern="^(price_asc|price_desc)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> PriceListResponse:
    prices_df = _load_prices_cached()
    current_df = latest_snapshot(prices_df)
    if current_df.empty:
        return PriceListResponse(items=[], total=0)

    if category:
        current_df = current_df[current_df["category"] == category]
    if q:
        current_df = current_df[current_df["product"].str.contains(q, case=False, na=False, regex=False)]

    z_anomalies = detect_zscore(current_df) if not current_df.empty else pd.DataFrame()
    anomaly_products = set(z_anomalies["product"].tolist()) if not z_anomalies.empty else set()

    change_result = _price_changes_cached()
    change_map: dict = {}
    if isinstance(change_result, tuple):
        changed_df, _latest_date, _prev_date = change_result
        if not changed_df.empty:
            change_map = {
                row["product"]: (row["change"], row["change_pct"])
                for _, row in changed_df.iterrows()
            }

    current_df = current_df.sort_values("price", ascending=(sort == "price_asc"))
    total = len(current_df)
    page_df = current_df.iloc[offset: offset + limit]

    code_map_cache: dict = {}
    items = []
    for _, row in page_df.iterrows():
        change, change_pct = change_map.get(row["product"], (None, None))
        items.append(ProductSummary(
            code=code_for_row(row, code_map_cache),
            category=row["category"],
            product=row["product"],
            price=int(row["price"]),
            date=row["date"],
            specs=row.get("specs"),
            image_url=row.get("image_url"),
            pcode=row.get("pcode"),
            is_anomaly=row["product"] in anomaly_products,
            change=int(change) if change is not None else None,
            change_pct=float(change_pct) if change_pct is not None else None,
        ))
    return PriceListResponse(items=items, total=total)
