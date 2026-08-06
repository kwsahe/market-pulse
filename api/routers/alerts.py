# api/routers/alerts.py
# GET /api/alerts — dashboard/tabs/alerts.py 로직 이식 (추적 상품 하락 알림 + 목표가 도달 알림).

from fastapi import APIRouter

from database.db_manager import get_tracked_pcodes, load_tracked_targets
from api.routers.changes import _build_change_item
from api.routers.prices import _load_prices_cached, _price_changes_cached, code_for_row, latest_snapshot
from api.schemas import AlertsResponse, TargetReachedItem

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertsResponse)
def get_alerts() -> AlertsResponse:
    current_df = latest_snapshot(_load_prices_cached())
    code_map_cache: dict = {}

    tracked_drops = []
    tracked_pcodes = get_tracked_pcodes()
    change_result = _price_changes_cached()
    if tracked_pcodes and isinstance(change_result, tuple) and not current_df.empty:
        changed_df, _latest_date, _prev_date = change_result
        if not changed_df.empty:
            tracked_names = current_df[current_df["pcode"].isin(tracked_pcodes)]["product"].unique().tolist()
            drops_df = changed_df[changed_df["product"].isin(tracked_names) & (changed_df["change"] < 0)]
            tracked_drops = [_build_change_item(row, current_df, code_map_cache) for _, row in drops_df.iterrows()]

    target_reached = []
    targets_df = load_tracked_targets()
    if not targets_df.empty:
        targets_df = targets_df[targets_df["target_price"].notna()]
    if not targets_df.empty and not current_df.empty:
        target_map = dict(zip(targets_df["pcode"], targets_df["target_price"]))
        tracked_current = current_df[current_df["pcode"].isin(target_map.keys())].copy()
        tracked_current["_target"] = tracked_current["pcode"].map(target_map)
        reached_df = tracked_current[tracked_current["price"] <= tracked_current["_target"]]
        for _, row in reached_df.iterrows():
            target_reached.append(TargetReachedItem(
                code=code_for_row(row, code_map_cache),
                category=row["category"],
                product=row["product"],
                image_url=row.get("image_url"),
                price=int(row["price"]),
                target_price=int(row["_target"]),
            ))

    return AlertsResponse(tracked_drops=tracked_drops, target_reached=target_reached)
