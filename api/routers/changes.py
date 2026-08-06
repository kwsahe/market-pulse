# api/routers/changes.py
# GET /api/changes — dashboard/tabs/changes.py 로직 이식 (전일 대비 인상/인하 목록).

import pandas as pd
from fastapi import APIRouter

from api.routers.prices import _load_prices_cached, _price_changes_cached, code_for_row, latest_snapshot
from api.schemas import ChangeItem, ChangesResponse

router = APIRouter(prefix="/api/changes", tags=["changes"])


def _build_change_item(row: pd.Series, current_df: pd.DataFrame, code_map_cache: dict) -> ChangeItem:
    detail = current_df[current_df["product"] == row["product"]]
    image_url = specs = None
    code = ""
    if not detail.empty:
        drow = detail.iloc[0]
        image_url = drow.get("image_url")
        specs = drow.get("specs")
        code = code_for_row(drow, code_map_cache)
    return ChangeItem(
        code=code,
        category=row["category"],
        product=row["product"],
        image_url=image_url,
        specs=specs,
        prev_price=int(row["prev_price"]),
        current_price=int(row["current_price"]),
        change=int(row["change"]),
        change_pct=float(row["change_pct"]),
    )


@router.get("", response_model=ChangesResponse)
def get_changes() -> ChangesResponse:
    change_result = _price_changes_cached()
    if not isinstance(change_result, tuple):
        return ChangesResponse(has_changes=False, up=[], down=[])

    changed_df, latest_date, prev_date = change_result
    current_df = latest_snapshot(_load_prices_cached())
    code_map_cache: dict = {}

    up_df = changed_df[changed_df["change"] > 0]
    down_df = changed_df[changed_df["change"] < 0]

    return ChangesResponse(
        has_changes=True,
        prev_date=str(prev_date),
        latest_date=str(latest_date),
        up=[_build_change_item(row, current_df, code_map_cache) for _, row in up_df.iterrows()],
        down=[_build_change_item(row, current_df, code_map_cache) for _, row in down_df.iterrows()],
    )
