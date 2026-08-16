# tests/test_category_registry.py
# 카테고리를 하나 추가할 때 같이 고쳐야 하는 레지스트리 3종이 서로 어긋나지 않는지 지킨다.
#
# 이 정합성이 깨져도 예외는 안 나고 조용히 잘못 동작한다:
#   - CATEGORY_PREFIX 누락 → 상품번호가 fallback "ITEM-1"로 발급되고 PK로 DB에 굳는다
#   - CATEGORY_COLORS 누락 → 차트에서 회색 폴백이 되거나 다른 카테고리와 같은 색이 재사용된다
# 프론트엔드 쪽 같은 성격의 가드는 frontend/src/three/parts.test.ts 에 있다.

from database.db_manager import CATEGORY_PREFIX
from dashboard.theme import CATEGORY_COLORS
from ml.price_prediction import FEATURE_EXTRACTORS
from scraper.price_scraper import (
    AI_LAPTOP_CATEGORY, CATEGORIES, CATEGORY_FILTERS, LAPTOP_CATEGORY,
)


def collected_categories() -> set[str]:
    """스크래퍼가 실제로 수집하는 카테고리 전체 — 부품류 + 노트북 2종(별도 경로)."""
    return set(CATEGORIES) | {LAPTOP_CATEGORY, AI_LAPTOP_CATEGORY}


def test_every_collected_category_has_a_product_code_prefix():
    missing = collected_categories() - set(CATEGORY_PREFIX)
    assert not missing, f"CATEGORY_PREFIX 누락: {missing} (상품번호가 ITEM-n으로 발급된다)"


def test_every_collected_category_has_a_color():
    missing = collected_categories() - set(CATEGORY_COLORS)
    assert not missing, f"CATEGORY_COLORS 누락: {missing}"


def test_registries_have_no_stale_entries():
    collected = collected_categories()
    assert set(CATEGORY_PREFIX) == collected
    assert set(CATEGORY_COLORS) == collected


def test_product_code_prefixes_are_unique():
    prefixes = list(CATEGORY_PREFIX.values())
    assert len(set(prefixes)) == len(prefixes), f"상품번호 접두사 중복: {prefixes}"


def test_feature_extractors_only_cover_collected_categories():
    unknown = set(FEATURE_EXTRACTORS) - collected_categories()
    assert not unknown, f"수집하지 않는 카테고리에 예측 모델이 붙어 있다: {unknown}"


def test_category_filters_only_target_collected_categories():
    unknown = set(CATEGORY_FILTERS) - set(CATEGORIES)
    assert not unknown, f"부품 수집 대상이 아닌 카테고리에 선별 규칙이 걸려 있다: {unknown}"
