# api/routers/spotlights.py
# GET /api/spotlights — dashboard/tabs/spotlights.py 로직 이식 (오늘의 변동폭 TOP + 주목할 만한 상품).

import pandas as pd
from fastapi import APIRouter

from database.db_manager import load_laptop_products
from ml.anomaly_detection import detect_zscore
from api.routers.changes import _build_change_item
from api.routers.prices import _load_prices_cached, _price_changes_cached, code_for_row, latest_snapshot
from api.schemas import SpotlightNotableItem, SpotlightsResponse

router = APIRouter(prefix="/api/spotlights", tags=["spotlights"])

LAPTOP_CATEGORIES = ["게이밍 노트북", "AI 노트북"]


@router.get("", response_model=SpotlightsResponse)
def get_spotlights() -> SpotlightsResponse:
    current_df = latest_snapshot(_load_prices_cached())
    code_map_cache: dict = {}

    top_movers = []
    change_result = _price_changes_cached()
    if isinstance(change_result, tuple):
        changed_df, _latest_date, _prev_date = change_result
        if not changed_df.empty:
            top = changed_df.reindex(changed_df["change_pct"].abs().sort_values(ascending=False).index).head(8)
            top_movers = [_build_change_item(row, current_df, code_map_cache) for _, row in top.iterrows()]

    notable: list[SpotlightNotableItem] = []
    z_df = detect_zscore(current_df) if not current_df.empty else pd.DataFrame()
    if not z_df.empty:
        top_anomalies = z_df.reindex(z_df["z_score"].abs().sort_values(ascending=False).index).head(5)
        for _, row in top_anomalies.iterrows():
            notable.append(SpotlightNotableItem(
                code=code_for_row(row, code_map_cache),
                category=row["category"],
                product=row["product"],
                image_url=row.get("image_url"),
                price=int(row["price"]),
                kind="anomaly",
                z_score=float(row["z_score"]),
            ))

    if not current_df.empty:
        products_df = load_laptop_products()
        laptop_current = current_df[current_df["category"].isin(LAPTOP_CATEGORIES) & current_df["pcode"].notna()]
        if not products_df.empty and "first_seen" in products_df.columns and not laptop_current.empty:
            latest_laptop_date = laptop_current["date"].max()
            first_seen_date = products_df["first_seen"].astype(str).str[:10]
            new_pcodes_today = set(products_df.loc[first_seen_date == latest_laptop_date, "pcode"])
            new_rows = laptop_current[laptop_current["pcode"].isin(new_pcodes_today)].drop_duplicates(subset="pcode")
            for _, row in new_rows.head(5).iterrows():
                notable.append(SpotlightNotableItem(
                    code=code_for_row(row, code_map_cache),
                    category=row["category"],
                    product=row["product"],
                    image_url=row.get("image_url"),
                    price=int(row["price"]),
                    kind="new",
                ))

    return SpotlightsResponse(top_movers=top_movers, notable=notable)
