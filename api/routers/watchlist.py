# api/routers/watchlist.py
# 워치리스트 — dashboard/laptop_view.py의 "추적 중" 탭 로직 이식.
# 읽기(GET)는 캐싱하지 않는다: 추적 토글/목표가 저장 직후 즉시 반영돼야 하는 mutation UX라서
# 30초 TTL 캐시를 걸면 저장 직후 재조회에서 옛날 값이 보일 수 있다.

import pandas as pd
from fastapi import APIRouter, HTTPException

from database.db_manager import get_tracked_pcodes, load_tracked_targets, set_laptop_tracked, set_target_price
from api.routers.prices import _load_prices_cached, code_for_row, latest_snapshot
from api.schemas import TargetRequest, TrackRequest, WatchlistItem, WatchlistResponse

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def get_watchlist() -> WatchlistResponse:
    targets_df = load_tracked_targets()
    if targets_df.empty:
        return WatchlistResponse(items=[])

    prices_df = _load_prices_cached()
    current_df = latest_snapshot(prices_df)
    tracked_df = current_df[current_df["pcode"].isin(set(targets_df["pcode"]))]
    if tracked_df.empty:
        return WatchlistResponse(items=[])

    # 같은 pcode(SSD/RAM 용량 변형)가 여러 행으로 나오므로 dashboard/laptop_view.py와 동일하게
    # 최저가 1건만 대표로 남긴다.
    tracked_df = tracked_df.sort_values("price").drop_duplicates(subset="pcode", keep="first")

    target_map = {
        row["pcode"]: (
            int(row["target_price"]) if pd.notna(row["target_price"]) else None,
            row["memo"] if pd.notna(row["memo"]) else None,
            row["tracked_at"] if pd.notna(row["tracked_at"]) else None,
        )
        for _, row in targets_df.iterrows()
    }

    code_map_cache: dict = {}
    items = []
    for _, row in tracked_df.iterrows():
        pcode = row["pcode"]
        target_price, memo, tracked_at = target_map.get(pcode, (None, None, None))
        items.append(WatchlistItem(
            pcode=pcode,
            code=code_for_row(row, code_map_cache),
            category=row["category"],
            product=row["product"],
            price=int(row["price"]),
            image_url=row.get("image_url"),
            tracked_at=tracked_at,
            target_price=target_price,
            memo=memo,
            target_reached=target_price is not None and row["price"] <= target_price,
        ))
    return WatchlistResponse(items=items)


@router.post("/{pcode}")
def track_product(pcode: str, body: TrackRequest) -> dict:
    set_laptop_tracked(pcode, body.tracked)
    return {"status": "ok"}


@router.put("/{pcode}/target")
def save_target(pcode: str, body: TargetRequest) -> dict:
    if pcode not in set(get_tracked_pcodes()):
        raise HTTPException(status_code=404, detail=f"'{pcode}'는 추적 중인 상품이 아니에요.")
    set_target_price(pcode, body.target_price, body.memo)
    return {"status": "ok"}
