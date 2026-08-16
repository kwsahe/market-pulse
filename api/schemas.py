# api/schemas.py
# 개요/상품리스트/상품상세 + 비교/예측/이상치/워치리스트/수집이력/뉴스 응답 모델.

from typing import Optional

from pydantic import BaseModel


class ProductSummary(BaseModel):
    code: str  # 상품 레지스트리에 없으면 빈 문자열
    category: str
    product: str
    price: int
    date: str
    specs: Optional[str] = None
    image_url: Optional[str] = None
    pcode: Optional[str] = None
    is_anomaly: bool = False
    change: Optional[int] = None  # 전일 대비 변동값(원). 비교 대상 없으면 None
    change_pct: Optional[float] = None


class PriceListResponse(BaseModel):
    items: list[ProductSummary]
    total: int


class CategoryStat(BaseModel):
    category: str
    avg_price: float
    count: int


class CategoriesResponse(BaseModel):
    categories: list[CategoryStat]
    product_count: int
    avg_price: float
    up_count: int
    down_count: int
    anomaly_count: int


# ============================
# 카테고리 단건 요약 (3D 데스크 부품 패널)
# ============================

class CategoryTrendPoint(BaseModel):
    date: str
    avg_price: float
    count: int


class CategoryPulseItem(BaseModel):
    code: str  # 상품 레지스트리에 없으면 빈 문자열
    product: str
    price: int
    image_url: Optional[str] = None
    change: Optional[int] = None
    change_pct: Optional[float] = None


class CategoryPulseResponse(BaseModel):
    category: str
    latest_date: str
    count: int
    avg_price: float
    min_price: int
    max_price: int
    median_price: float
    up_count: int
    down_count: int
    anomaly_count: int
    trend: list[CategoryTrendPoint] = []
    trend_pct: Optional[float] = None  # trend 첫 지점 대비 마지막 지점 변화율(%)
    cheapest: list[CategoryPulseItem] = []
    movers: list[CategoryPulseItem] = []  # 변동률 절대값 상위


class PricePoint(BaseModel):
    date: str
    price: int


class ProductImage(BaseModel):
    image_url: str
    image_type: str  # "main" | "detail"


class ProductDetailResponse(BaseModel):
    code: str
    category: str
    product: str
    price: int
    date: str
    specs: Optional[str] = None
    pcode: Optional[str] = None
    images: list[ProductImage] = []
    history: list[PricePoint] = []
    hist_min: Optional[int] = None
    hist_max: Optional[int] = None


# ============================
# 가격 변동 (changes)
# ============================

class ChangeItem(BaseModel):
    code: str
    category: str
    product: str
    image_url: Optional[str] = None
    specs: Optional[str] = None
    prev_price: int
    current_price: int
    change: int
    change_pct: float


class ChangesResponse(BaseModel):
    has_changes: bool
    prev_date: Optional[str] = None
    latest_date: Optional[str] = None
    up: list[ChangeItem]
    down: list[ChangeItem]


# ============================
# 알림 배너 (alerts)
# ============================

class TargetReachedItem(BaseModel):
    code: str
    category: str
    product: str
    image_url: Optional[str] = None
    price: int
    target_price: int


class AlertsResponse(BaseModel):
    tracked_drops: list[ChangeItem]
    target_reached: list[TargetReachedItem]


# ============================
# 오늘의 하이라이트 (spotlights)
# ============================

class SpotlightNotableItem(BaseModel):
    code: str
    category: str
    product: str
    image_url: Optional[str] = None
    price: int
    kind: str  # "anomaly" | "new"
    z_score: Optional[float] = None


class SpotlightsResponse(BaseModel):
    top_movers: list[ChangeItem]
    notable: list[SpotlightNotableItem]


# ============================
# 노트북 전용 뷰 (laptops) — dashboard/laptop_view.py
# ============================

class LaptopImage(BaseModel):
    image_url: str
    image_type: str


class LaptopSpec(BaseModel):
    spec_key: str
    spec_value: str


class LaptopBestBuy(BaseModel):
    best_date: str
    savings: int  # 현재가 - 역대최저가. 0 이하면 지금이 역대 최저가
    is_best_now: bool


class LaptopItem(BaseModel):
    pcode: str
    code: str
    category: str
    product: str
    price: int
    date: str
    image_url: Optional[str] = None
    images: list[LaptopImage] = []
    full_specs: list[LaptopSpec] = []
    filter_values: dict[str, Optional[str]] = {}
    best_buy: Optional[LaptopBestBuy] = None
    change: Optional[int] = None
    change_pct: Optional[float] = None
    tracked: bool = False
    is_new: bool = False


class LaptopsResponse(BaseModel):
    category: str
    filter_spec_keys: list[str]
    filter_options: dict[str, list[str]]
    new_count: int
    latest_date: Optional[str] = None
    items: list[LaptopItem]


# ============================
# 이상치 (anomalies)
# ============================

class AnomalyCategoryStat(BaseModel):
    category: str
    count: int
    mean: float
    min: float
    max: float
    std: float


class ZScoreAnomaly(BaseModel):
    code: str
    category: str
    product: str
    price: int
    direction: str  # "고가" | "저가"
    z_score: float


class IqrAnomaly(BaseModel):
    code: str
    category: str
    product: str
    price: int
    direction: str
    lower_bound: float
    upper_bound: float


class AnomaliesResponse(BaseModel):
    category_stats: list[AnomalyCategoryStat]
    zscore: list[ZScoreAnomaly]
    iqr: list[IqrAnomaly]


# ============================
# 가격 예측 (prediction) / 비교 (compare)
# ============================

class FeatureContribution(BaseModel):
    feature: str
    label: str
    value: float
    contribution: float


class SimilarProduct(BaseModel):
    product: str
    price: int
    distance: float


class PredictionResponse(BaseModel):
    code: str
    category: str
    product: str
    actual_price: int
    predicted_price: float
    low: float
    high: float
    fair_score: int
    fair_label: str
    model_name: str
    r2: float
    data_count: int
    contributions: list[FeatureContribution]
    similar_products: list[SimilarProduct]


class CompareProduct(BaseModel):
    code: str
    category: str
    product: str
    image_url: Optional[str] = None
    price: int
    predicted_price: Optional[float] = None
    hist_min: Optional[int] = None
    hist_max: Optional[int] = None
    fair_score: Optional[int] = None
    fair_label: Optional[str] = None


class SpecRow(BaseModel):
    label: str
    values: list[float]  # products 순서와 동일


class CompareResponse(BaseModel):
    products: list[CompareProduct]
    spec_table: list[SpecRow]


# ============================
# 워치리스트 (watchlist)
# ============================

class WatchlistItem(BaseModel):
    pcode: str
    code: str
    category: str
    product: str
    price: int
    image_url: Optional[str] = None
    tracked_at: Optional[str] = None
    target_price: Optional[int] = None
    memo: Optional[str] = None
    target_reached: bool = False


class WatchlistResponse(BaseModel):
    items: list[WatchlistItem]


class TrackRequest(BaseModel):
    tracked: bool


class TargetRequest(BaseModel):
    target_price: Optional[int] = None
    memo: str = ""


# ============================
# 수집 이력 (scrape runs)
# ============================

class ScrapeRunLatest(BaseModel):
    source: str
    status: str
    started_at: str
    fetched_count: int
    inserted_count: int
    error_message: Optional[str] = None


class ScrapeRunSummary(BaseModel):
    total: int
    success: int
    failed: int
    running: int


class ScrapeRun(BaseModel):
    id: int
    source: str
    started_at: str
    finished_at: Optional[str] = None
    fetched_count: int
    inserted_count: int
    status: str
    error_message: Optional[str] = None


class ScrapeRunsResponse(BaseModel):
    latest_by_source: list[ScrapeRunLatest]
    summary: ScrapeRunSummary
    runs: list[ScrapeRun]


# ============================
# 뉴스 (news)
# ============================

class NewsItem(BaseModel):
    collected_at: str
    press: Optional[str] = None
    title: str
    published_at: Optional[str] = None


class NewsResponse(BaseModel):
    items: list[NewsItem]
