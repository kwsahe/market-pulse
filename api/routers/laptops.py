# api/routers/laptops.py
# GET /api/laptops/{category} — dashboard/laptop_view.py 로직 이식.
# 데이터가 그리 크지 않아(카테고리당 수백 개) 필터링에 필요한 모든 정보(스펙 옵션 + 개별 상품의
# 정제된 필터값)를 한 번에 실어보내고, 실제 필터링은 프론트에서 클라이언트 사이드로 처리한다
# (dashboard/tabs/news.py의 언론사 필터와 동일한 패턴).

import re

import pandas as pd
from fastapi import APIRouter

from database.db_manager import (
    get_product_code_map, get_tracked_pcodes, load_laptop_best_buy_stats,
    load_laptop_images, load_laptop_products, load_laptop_specs,
)
from api.deps import data_cache
from api.routers.prices import _load_prices_cached, _price_changes_cached, latest_snapshot
from api.schemas import LaptopBestBuy, LaptopImage, LaptopItem, LaptopSpec, LaptopsResponse

router = APIRouter(prefix="/api/laptops", tags=["laptops"])

DEFAULT_FILTER_SPEC_KEYS = ["GPU 칩셋", "제조회사", "CPU 세분류", "화면 크기", "램", "용량", "무게"]
AI_FILTER_SPEC_KEYS = ["CPU 제조사", "CPU 세분류", "화면 크기", "램", "용량", "무게"]


def _clean_value(value):
    """스펙 값에서 부가 설명(괄호 등) 제거 — 필터 옵션을 깔끔하게 만들기 위함"""
    if not isinstance(value, str):
        return value
    return re.sub(r"\(.*?\)", "", value).strip()


@data_cache
def _laptop_specs_cached() -> pd.DataFrame:
    return load_laptop_specs()


@data_cache
def _laptop_images_cached() -> pd.DataFrame:
    return load_laptop_images()


@data_cache
def _laptop_products_cached() -> pd.DataFrame:
    return load_laptop_products()


@data_cache
def _best_buy_cached(category: str) -> pd.DataFrame:
    return load_laptop_best_buy_stats(category)


@data_cache
def _laptop_code_map_cached(category: str) -> dict:
    return get_product_code_map(category)


@router.get("/{category}", response_model=LaptopsResponse)
def get_laptops(category: str) -> LaptopsResponse:
    filter_spec_keys = AI_FILTER_SPEC_KEYS if category == "AI 노트북" else DEFAULT_FILTER_SPEC_KEYS

    current_df = latest_snapshot(_load_prices_cached())
    laptop_df = current_df[current_df["category"] == category].copy()
    laptop_df = laptop_df[laptop_df["pcode"].notna() & (laptop_df["pcode"] != "")]

    if laptop_df.empty:
        return LaptopsResponse(
            category=category, filter_spec_keys=filter_spec_keys, filter_options={}, new_count=0, items=[],
        )

    # 같은 상품(pcode)의 SSD/RAM 용량 변형 중 최저가만 대표로 표시
    laptop_df = laptop_df.sort_values("price").drop_duplicates(subset="pcode", keep="first")
    category_pcodes = set(laptop_df["pcode"])

    specs_df = _laptop_specs_cached()
    specs_df = specs_df[specs_df["pcode"].isin(category_pcodes)]
    images_df = _laptop_images_cached()
    images_df = images_df[images_df["pcode"].isin(category_pcodes)]
    best_buy_df = _best_buy_cached(category)
    products_df = _laptop_products_cached()
    tracked_pcodes = set(get_tracked_pcodes())
    code_map = _laptop_code_map_cached(category)

    spec_pivot = (
        specs_df.pivot(index="pcode", columns="spec_key", values="spec_value")
        if not specs_df.empty else pd.DataFrame()
    )

    latest_date = laptop_df["date"].max()
    new_pcodes: set = set()
    if not products_df.empty and "first_seen" in products_df.columns:
        first_seen_date = products_df["first_seen"].astype(str).str[:10]
        new_pcodes = set(products_df.loc[first_seen_date == latest_date, "pcode"])
    new_pcodes &= category_pcodes

    filter_options: dict[str, list[str]] = {}
    for key in filter_spec_keys:
        if key in spec_pivot.columns:
            filter_options[key] = sorted({_clean_value(v) for v in spec_pivot[key].dropna()})
        else:
            filter_options[key] = []

    change_result = _price_changes_cached()
    change_map: dict = {}
    if isinstance(change_result, tuple):
        changed_df, _latest_date, _prev_date = change_result
        if not changed_df.empty:
            change_map = {row["product"]: (row["change"], row["change_pct"]) for _, row in changed_df.iterrows()}

    items = []
    for _, row in laptop_df.iterrows():
        pcode = row["pcode"]
        prod_images = images_df[images_df["pcode"] == pcode]
        prod_specs = specs_df[specs_df["pcode"] == pcode]

        filter_values: dict[str, str | None] = {}
        for key in filter_spec_keys:
            raw = spec_pivot.loc[pcode, key] if pcode in spec_pivot.index and key in spec_pivot.columns else None
            filter_values[key] = _clean_value(raw) if pd.notna(raw) else None

        best_buy = None
        if not best_buy_df.empty:
            stat = best_buy_df[best_buy_df["pcode"] == pcode]
            if not stat.empty:
                best_price = int(stat.iloc[0]["best_price"])
                savings = int(row["price"]) - best_price
                best_buy = LaptopBestBuy(best_date=stat.iloc[0]["best_date"], savings=savings, is_best_now=savings <= 0)

        change, change_pct = change_map.get(row["product"], (None, None))

        items.append(LaptopItem(
            pcode=pcode,
            code=code_map.get(pcode, ""),
            category=category,
            product=row["product"],
            price=int(row["price"]),
            date=row["date"],
            image_url=row.get("image_url"),
            images=[
                LaptopImage(image_url=r["image_url"], image_type=r["image_type"])
                for _, r in prod_images.iterrows()
            ],
            full_specs=[
                LaptopSpec(spec_key=r["spec_key"], spec_value=r["spec_value"])
                for _, r in prod_specs.iterrows()
            ],
            filter_values=filter_values,
            best_buy=best_buy,
            change=int(change) if change is not None else None,
            change_pct=float(change_pct) if change_pct is not None else None,
            tracked=pcode in tracked_pcodes,
            is_new=pcode in new_pcodes,
        ))

    return LaptopsResponse(
        category=category,
        filter_spec_keys=filter_spec_keys,
        filter_options=filter_options,
        new_count=len(new_pcodes),
        latest_date=str(latest_date),
        items=items,
    )
