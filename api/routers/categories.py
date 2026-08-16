# api/routers/categories.py
# GET /api/categories — 카테고리별 평균가/상품수(오늘자 스냅샷 기준) + 개요 스탯 카드 요약
# dashboard/app.py의 stat_cards 6종(상품/카테고리/평균가/인상/인하/이상치) 계산 로직과 동일하게 맞춘다.
# GET /api/categories/{category}/pulse — 3D 데스크에서 부품 하나를 클릭했을 때 보여줄 단일 카테고리 요약

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ml.anomaly_detection import detect_zscore
from api.routers.prices import (
    _load_prices_cached, _price_changes_cached, code_for_row, latest_snapshot,
)
from api.schemas import (
    CategoriesResponse, CategoryPulseItem, CategoryPulseResponse, CategoryStat, CategoryTrendPoint,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])

TOP_N = 3  # 부품 패널에 노출할 최저가/변동 상품 개수


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


def _category_changes(category: str) -> pd.DataFrame:
    """detect_price_changes() 결과에서 해당 카테고리 행만 추린다. 비교 대상 날짜가 없으면 빈 DataFrame."""
    change_result = _price_changes_cached()
    if not isinstance(change_result, tuple):
        return pd.DataFrame()
    changed_df, _latest_date, _prev_date = change_result
    if changed_df.empty:
        return changed_df
    return changed_df[changed_df["category"] == category]


def _pulse_item(row: pd.Series, code_map_cache: dict, change_map: dict) -> CategoryPulseItem:
    change, change_pct = change_map.get(row["product"], (None, None))
    return CategoryPulseItem(
        code=code_for_row(row, code_map_cache),
        product=row["product"],
        price=int(row["price"]),
        image_url=row.get("image_url"),
        change=int(change) if change is not None else None,
        change_pct=float(change_pct) if change_pct is not None else None,
    )


@router.get("/{category}/pulse", response_model=CategoryPulseResponse)
def get_category_pulse(
    category: str,
    trend_days: int = Query(14, ge=2, le=90, description="추이 그래프에 포함할 최근 수집일 수"),
) -> CategoryPulseResponse:
    """3D 데스크에서 부품 하나(=카테고리)를 방문했을 때 띄우는 요약.

    개요 화면의 카드 6종을 한 카테고리로 좁힌 것 + 날짜별 평균가 추이 + 최저가/변동 TOP N.
    """
    prices_df = _load_prices_cached()
    cat_all = prices_df[prices_df["category"] == category] if not prices_df.empty else pd.DataFrame()
    if cat_all.empty:
        raise HTTPException(status_code=404, detail=f"'{category}' 카테고리 데이터가 없습니다")

    # 기준일은 전체 최신 수집일에 맞추되(다른 화면과 숫자가 어긋나지 않도록),
    # 그날 이 카테고리가 수집되지 않았으면 이 카테고리의 마지막 수집일로 내려온다.
    global_latest = prices_df["date"].max()
    current = cat_all[cat_all["date"] == global_latest]
    if current.empty:
        latest_date = cat_all["date"].max()
        current = cat_all[cat_all["date"] == latest_date]
    else:
        latest_date = global_latest

    trend_df = (
        cat_all.groupby("date")["price"].agg(["mean", "count"]).sort_index().tail(trend_days)
    )
    trend = [
        CategoryTrendPoint(date=str(date), avg_price=float(row["mean"]), count=int(row["count"]))
        for date, row in trend_df.iterrows()
    ]
    trend_pct = None
    if len(trend) >= 2 and trend[0].avg_price > 0:
        trend_pct = round((trend[-1].avg_price - trend[0].avg_price) / trend[0].avg_price * 100, 2)

    changed_df = _category_changes(category)
    change_map: dict = {}
    if not changed_df.empty:
        change_map = {
            row["product"]: (row["change"], row["change_pct"]) for _, row in changed_df.iterrows()
        }

    z_anomalies = detect_zscore(current)
    anomaly_count = len(z_anomalies) if not z_anomalies.empty else 0

    code_map_cache: dict = {}
    cheapest = [
        _pulse_item(row, code_map_cache, change_map)
        for _, row in current.nsmallest(TOP_N, "price").iterrows()
    ]

    movers: list[CategoryPulseItem] = []
    if not changed_df.empty:
        # 변동 정보는 changed_df에, 이미지/코드는 최신 스냅샷에 있어 상품명으로 이어붙인다.
        current_by_product = {row["product"]: row for _, row in current.iterrows()}
        top_moved = changed_df.reindex(
            changed_df["change_pct"].abs().sort_values(ascending=False).index
        )
        for _, changed_row in top_moved.iterrows():
            snapshot_row = current_by_product.get(changed_row["product"])
            if snapshot_row is None:
                continue
            movers.append(_pulse_item(snapshot_row, code_map_cache, change_map))
            if len(movers) == TOP_N:
                break

    return CategoryPulseResponse(
        category=category,
        latest_date=str(latest_date),
        count=len(current),
        avg_price=float(current["price"].mean()),
        min_price=int(current["price"].min()),
        max_price=int(current["price"].max()),
        median_price=float(current["price"].median()),
        up_count=int((changed_df["change"] > 0).sum()) if not changed_df.empty else 0,
        down_count=int((changed_df["change"] < 0).sum()) if not changed_df.empty else 0,
        anomaly_count=anomaly_count,
        trend=trend,
        trend_pct=trend_pct,
        cheapest=cheapest,
        movers=movers,
    )
