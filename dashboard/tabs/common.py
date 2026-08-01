# dashboard/tabs/common.py
# 여러 탭 모듈이 공유하는 순수 헬퍼 + 캐시된 데이터 접근 함수
#
# 성능 메모: Streamlit은 위젯 하나만 바뀌어도 스크립트 전체(모든 탭의 본문 포함,
# 화면에 안 보이는 탭도 전부)를 처음부터 다시 실행한다. DB 조회/ML 계산 함수에
# 캐시가 없으면 클릭 한 번마다 그 무거운 연산이 전부 다시 도는 셈이라 체감 렉이
# 커진다. 여기 있는 함수들은 전부 @st.cache_data로 감싸서, 실제 데이터가 바뀌지
# 않는 한(스크래퍼가 새로 돌기 전까지는) 반복 호출이 캐시에서 즉시 반환되게 한다.

import pandas as pd
import streamlit as st

from database.db_manager import (
    load_prices, load_news, get_product_code_map, load_product_registry,
    load_laptop_products, load_laptop_specs, load_laptop_images, load_scrape_runs,
    load_price_history_by_match_key, load_laptop_price_history, load_laptop_best_buy_stats,
)
from ml.anomaly_detection import detect_zscore, detect_iqr
from ml.price_change import detect_price_changes
from ml.price_prediction import train_model

# 스크래퍼가 데이터를 새로 채워 넣을 때까지의 신선도 허용치.
# 너무 짧으면 캐시 효과가 없고, 너무 길면 방금 수집한 데이터가 화면에 안 보일 수 있다.
_DATA_TTL = 30


def match_key_for_row(row: pd.Series) -> str:
    """상품번호 조회용 식별키 — pcode가 있으면 pcode, 없으면(부품 과거 데이터) 상품명"""
    pcode = row.get("pcode")
    return pcode if pcode and str(pcode).strip() else row["product"]


def open_product_detail(code: str) -> None:
    """상품 코드로 상세보기를 연다 — URL 쿼리파라미터에 반영되므로 그대로 복사하면 링크가 된다"""
    st.query_params["code"] = code
    st.rerun()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """엑셀에서 한글이 깨지지 않도록 utf-8-sig로 인코딩한 CSV 바이트"""
    return df.to_csv(index=False).encode("utf-8-sig")


def format_capacity_label(capacity_gb: int) -> str:
    """128, 256, 512, 1024(=1TB) 같은 용량 값을 다나와 스타일 라벨로 변환"""
    if not capacity_gb or capacity_gb <= 0:
        return "정보없음"
    if capacity_gb >= 1024 and capacity_gb % 1024 == 0:
        return f"{capacity_gb // 1024}TB"
    return f"{capacity_gb}GB"


def score_badge_bg(hex_color: str, alpha: float = 0.15) -> str:
    """적정가 점수 배지 배경색 — 점수 색상(hex)의 옅은 rgba 톤"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ============================
# 캐시된 데이터 접근 (DB 조회 / ML 계산)
# ============================

@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_prices_cached() -> pd.DataFrame:
    return load_prices()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_news_cached() -> pd.DataFrame:
    return load_news()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def get_product_code_map_cached(category: str) -> dict:
    return get_product_code_map(category)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_product_registry_cached() -> pd.DataFrame:
    return load_product_registry()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_laptop_products_cached() -> pd.DataFrame:
    return load_laptop_products()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_laptop_specs_cached() -> pd.DataFrame:
    return load_laptop_specs()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_laptop_images_cached() -> pd.DataFrame:
    return load_laptop_images()


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_scrape_runs_cached(limit: int = 50) -> pd.DataFrame:
    return load_scrape_runs(limit=limit)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_price_history_by_match_key_cached(category: str, match_key: str, by_pcode: bool = False) -> pd.DataFrame:
    return load_price_history_by_match_key(category, match_key, by_pcode=by_pcode)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_laptop_price_history_cached(pcode: str) -> pd.DataFrame:
    return load_laptop_price_history(pcode)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def load_laptop_best_buy_stats_cached(category: str) -> pd.DataFrame:
    return load_laptop_best_buy_stats(category)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def detect_zscore_cached(current_df: pd.DataFrame) -> pd.DataFrame:
    return detect_zscore(current_df)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def detect_iqr_cached(current_df: pd.DataFrame) -> pd.DataFrame:
    return detect_iqr(current_df)


@st.cache_data(ttl=_DATA_TTL, show_spinner=False)
def detect_price_changes_cached():
    return detect_price_changes()


def code_for_row(row: pd.Series, category: str, code_map_cache: dict) -> str:
    """카테고리별 code_map을 캐시하며 상품번호를 조회하는 공통 패턴"""
    if category not in code_map_cache:
        code_map_cache[category] = get_product_code_map_cached(category)
    return code_map_cache[category].get(match_key_for_row(row), "")


@st.cache_data(show_spinner="모델 학습 중...", ttl=3600)
def get_trained_model(category):
    """카테고리별 가격 예측 모델 학습 (캐시됨) — 가격예측/상품비교 탭이 공유"""
    try:
        return train_model(category)
    except Exception as e:
        st.error(f"모델 학습 실패 ({category}): {e}")
        return None
