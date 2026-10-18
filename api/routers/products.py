# api/routers/products.py
# GET /api/products/{code} — dashboard/tabs/product_detail.py의 _resolve_code() 조합 로직을 그대로 이식.
# (스펙/이미지/가격이력/역대최저가까지 한 번에 응답)

import pandas as pd
from fastapi import APIRouter, HTTPException

from database.db_manager import (
    load_product_registry, load_laptop_images, load_price_history_by_match_key, match_key_for, match_keys,
)
from api.deps import data_cache
from api.routers.prices import _load_prices_cached
from api.schemas import ProductDetailResponse, ProductImage, PricePoint
from api.utils import optional_str

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
    return match_key_for(row["category"], row.get("pcode"), row["product"])


def _resolve_code(code: str, prices_df: pd.DataFrame):
    """상품번호 -> (category, 최신 데이터 행) 조회. 없으면 (None, None)"""
    reg = _product_registry_cached()
    match = reg[reg["internal_code"] == code]
    if match.empty:
        return None, None
    category = match.iloc[0]["category"]
    match_key = match.iloc[0]["match_key"]
    # pcode/상품명 직접 비교는 식별키 규칙이 바뀌기 전에 발급된 번호(옛 링크)도 계속 열리게 남겨둔다
    hist = prices_df[(prices_df["category"] == category)
                     & ((prices_df["pcode"] == match_key.split(" ", 1)[0]) | (prices_df["product"] == match_key))]
    hist = hist[(match_keys(hist, category) == match_key) | (hist["pcode"] == match_key) | (hist["product"] == match_key)]
    if hist.empty:
        return category, None
    # 가장 최근 수집일(오늘 목록에 없으면 마지막으로 보인 날)의 행. 한 번호에 행이 여럿이면(노트북 옵션,
    # 옛 pcode 단위 번호) 최저가 — 가격 이력이 날짜별 최저가라, 아무 행이나 고르면 헤드라인과 이력이 어긋난다.
    last = hist[hist["date"] == hist["date"].max()]
    return category, last.loc[last["price"].idxmin()]


@router.get("/{code}", response_model=ProductDetailResponse)
def get_product_detail(code: str) -> ProductDetailResponse:
    prices_df = _load_prices_cached()
    category, row = _resolve_code(code, prices_df)
    if row is None:
        raise HTTPException(status_code=404, detail=f"상품번호 '{code}'를 찾을 수 없어요.")

    match_key = _match_key_for_row(row)
    # NaN을 그대로 두면 bool(nan)이 True라 pcode가 없는 행도 pcode 경로를 타버린다.
    pcode = optional_str(row.get("pcode"))
    by_pcode = bool(pcode and pcode.strip())

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
        specs=optional_str(row.get("specs")),
        pcode=pcode,
        images=images,
        history=history,
        hist_min=hist_min,
        hist_max=hist_max,
    )
