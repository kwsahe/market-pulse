// frontend/src/types/api.ts
// api/schemas.py의 Pydantic 응답 모델과 1:1 대응하는 타입.

export interface ProductSummary {
  code: string;
  category: string;
  product: string;
  price: number;
  date: string;
  specs?: string | null;
  image_url?: string | null;
  pcode?: string | null;
  is_anomaly: boolean;
  change?: number | null;
  change_pct?: number | null;
}

export interface PriceListResponse {
  items: ProductSummary[];
  total: number;
}

export interface CategoryStat {
  category: string;
  avg_price: number;
  count: number;
}

export interface CategoriesResponse {
  categories: CategoryStat[];
  product_count: number;
  avg_price: number;
  up_count: number;
  down_count: number;
  anomaly_count: number;
}

export interface PricePoint {
  date: string;
  price: number;
}

export interface ProductImage {
  image_url: string;
  image_type: "main" | "detail";
}

export interface ProductDetailResponse {
  code: string;
  category: string;
  product: string;
  price: number;
  date: string;
  specs?: string | null;
  pcode?: string | null;
  images: ProductImage[];
  history: PricePoint[];
  hist_min?: number | null;
  hist_max?: number | null;
}

export type SortOrder = "price_asc" | "price_desc";

// ============================
// 이상치 (anomalies)
// ============================

export interface AnomalyCategoryStat {
  category: string;
  count: number;
  mean: number;
  min: number;
  max: number;
  std: number;
}

export interface ZScoreAnomaly {
  code: string;
  category: string;
  product: string;
  price: number;
  direction: "고가" | "저가";
  z_score: number;
}

export interface IqrAnomaly {
  code: string;
  category: string;
  product: string;
  price: number;
  direction: "고가" | "저가";
  lower_bound: number;
  upper_bound: number;
}

export interface AnomaliesResponse {
  category_stats: AnomalyCategoryStat[];
  zscore: ZScoreAnomaly[];
  iqr: IqrAnomaly[];
}

// ============================
// 가격 예측 (prediction) / 비교 (compare)
// ============================

export interface FeatureContribution {
  feature: string;
  label: string;
  value: number;
  contribution: number;
}

export interface SimilarProduct {
  product: string;
  price: number;
  distance: number;
}

export interface PredictionResponse {
  code: string;
  category: string;
  product: string;
  actual_price: number;
  predicted_price: number;
  low: number;
  high: number;
  fair_score: number;
  fair_label: string;
  model_name: string;
  r2: number;
  data_count: number;
  contributions: FeatureContribution[];
  similar_products: SimilarProduct[];
}

export interface CompareProduct {
  code: string;
  category: string;
  product: string;
  image_url?: string | null;
  price: number;
  predicted_price?: number | null;
  hist_min?: number | null;
  hist_max?: number | null;
  fair_score?: number | null;
  fair_label?: string | null;
}

export interface SpecRow {
  label: string;
  values: number[];
}

export interface CompareResponse {
  products: CompareProduct[];
  spec_table: SpecRow[];
}

// ============================
// 워치리스트 (watchlist)
// ============================

export interface WatchlistItem {
  pcode: string;
  code: string;
  category: string;
  product: string;
  price: number;
  image_url?: string | null;
  tracked_at?: string | null;
  target_price?: number | null;
  memo?: string | null;
  target_reached: boolean;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
}

// ============================
// 수집 이력 (scrape runs)
// ============================

export interface ScrapeRunLatest {
  source: string;
  status: string;
  started_at: string;
  fetched_count: number;
  inserted_count: number;
  error_message?: string | null;
}

export interface ScrapeRunSummary {
  total: number;
  success: number;
  failed: number;
  running: number;
}

export interface ScrapeRun {
  id: number;
  source: string;
  started_at: string;
  finished_at?: string | null;
  fetched_count: number;
  inserted_count: number;
  status: string;
  error_message?: string | null;
}

export interface ScrapeRunsResponse {
  latest_by_source: ScrapeRunLatest[];
  summary: ScrapeRunSummary;
  runs: ScrapeRun[];
}

// ============================
// 뉴스 (news)
// ============================

export interface NewsItem {
  collected_at: string;
  press?: string | null;
  title: string;
  published_at?: string | null;
}

export interface NewsResponse {
  items: NewsItem[];
}

// ============================
// 가격 변동 (changes)
// ============================

export interface ChangeItem {
  code: string;
  category: string;
  product: string;
  image_url?: string | null;
  specs?: string | null;
  prev_price: number;
  current_price: number;
  change: number;
  change_pct: number;
}

export interface ChangesResponse {
  has_changes: boolean;
  prev_date?: string | null;
  latest_date?: string | null;
  up: ChangeItem[];
  down: ChangeItem[];
}

// ============================
// 알림 배너 (alerts)
// ============================

export interface TargetReachedItem {
  code: string;
  category: string;
  product: string;
  image_url?: string | null;
  price: number;
  target_price: number;
}

export interface AlertsResponse {
  tracked_drops: ChangeItem[];
  target_reached: TargetReachedItem[];
}

// ============================
// 오늘의 하이라이트 (spotlights)
// ============================

export interface SpotlightNotableItem {
  code: string;
  category: string;
  product: string;
  image_url?: string | null;
  price: number;
  kind: "anomaly" | "new";
  z_score?: number | null;
}

export interface SpotlightsResponse {
  top_movers: ChangeItem[];
  notable: SpotlightNotableItem[];
}

// ============================
// 노트북 전용 뷰 (laptops)
// ============================

export interface LaptopImage {
  image_url: string;
  image_type: "main" | "detail";
}

export interface LaptopSpec {
  spec_key: string;
  spec_value: string;
}

export interface LaptopBestBuy {
  best_date: string;
  savings: number;
  is_best_now: boolean;
}

export interface LaptopItem {
  pcode: string;
  code: string;
  category: string;
  product: string;
  price: number;
  date: string;
  image_url?: string | null;
  images: LaptopImage[];
  full_specs: LaptopSpec[];
  filter_values: Record<string, string | null>;
  best_buy?: LaptopBestBuy | null;
  change?: number | null;
  change_pct?: number | null;
  tracked: boolean;
  is_new: boolean;
}

export interface LaptopsResponse {
  category: string;
  filter_spec_keys: string[];
  filter_options: Record<string, string[]>;
  new_count: number;
  latest_date?: string | null;
  items: LaptopItem[];
}
