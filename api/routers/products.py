# api/routers/products.py
# GET /api/products/{code} — dashboard/tabs/product_detail.py의 _resolve_code() 조합 로직을 그대로 이식.
# (스펙/이미지/가격이력/역대최저가까지 한 번에 응답)

import pandas as pd
from fastapi import APIRouter, HTTPException

from database.db_manager import load_product_registry, load_laptop_images, load_price_history_by_match_key
from api.deps import data_cache
from api.routers.prices import _load_prices_cached
from api.schemas import ProductDetailResponse, ProductImage, PricePoint

router = APIRouter(prefix="/api/products", tags=["products"])


@data_cache
def _product_registry_cached() -> pd.DataFrame:
    return load_product_registry()


@data_cache
def _laptop_images_cached() -> pd.DataFrame:
    return load_laptop_images()


@data_cache
def _price_history_cached(category: str, match_key: str, by_pcode: bool) -> pd.DataFrame:
    return load_price_history_by_match_key(category, match_key, by_pcode=by_pcode)


def _match_key_for_row(row: pd.Series) -> str:
    pcode = row.get("pcode")
    return pcode if pcode and str(pcode).strip() else row["product"]


def _resolve_code(code: str, prices_df: pd.DataFrame):
    """상품번호 -> (category, 최신 데이터 행) 조회. 없으면 (None, None)"""
    reg = _product_registry_cached()
    match = reg[reg["internal_code"] == code]
    if match.empty:
        return None, None
    category = match.iloc[0]["category"]
    match_key = match.iloc[0]["match_key"]
    latest_date = prices_df["date"].max()
    cat_latest = prices_df[(prices_df["date"] == latest_date) & (prices_df["category"] == category)]
    row = cat_latest[(cat_latest["pcode"] == match_key) | (cat_latest["product"] == match_key)]
    if row.empty:
        hist = prices_df[(prices_df["category"] == category) & ((prices_df["pcode"] == match_key) | (prices_df["product"] == match_key))]
        if hist.empty:
            return category, None
        row = hist.sort_values("date").tail(1)
    return category, row.iloc[0]


@router.get("/{code}", response_model=ProductDetailResponse)
def get_product_detail(code: str) -> ProductDetailResponse:
    prices_df = _load_prices_cached()
    category, row = _resolve_code(code, prices_df)
    if row is None:
        raise HTTPException(status_code=404, detail=f"상품번호 '{code}'를 찾을 수 없어요.")

    match_key = _match_key_for_row(row)
    pcode = row.get("pcode")
    by_pcode = bool(pcode) and str(pcode).strip() != ""

    images: list[ProductImage] = []
    if by_pcode:
        all_images_df = _laptop_images_cached()
        prod_imgs = all_images_df[all_images_df["pcode"] == pcode]
        images = [
            ProductImage(image_url=img["image_url"], image_type=img["image_type"])
            for _, img in prod_imgs.iterrows()
        ]

    history_df = _price_history_cached(category, match_key, by_pcode)
    history = [PricePoint(date=r["date"], price=int(r["price"])) for _, r in history_df.iterrows()]
    hist_min = int(history_df["price"].min()) if not history_df.empty else None
    hist_max = int(history_df["price"].max()) if not history_df.empty else None

    return ProductDetailResponse(
        code=code,
        category=category,
        product=row["product"],
        price=int(row["price"]),
        date=row["date"],
        specs=row.get("specs"),
        pcode=pcode,
        images=images,
        history=history,
        hist_min=hist_min,
        hist_max=hist_max,
    )
