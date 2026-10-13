// frontend/src/api/client.ts
// FastAPI(api/main.py, 기본 8000번 포트) 호출 헬퍼.
// 8000번이 다른 프로젝트에 점유된 환경도 있어서, VITE_API_BASE_URL로 덮어쓸 수 있게 뒀다.
// (frontend/.env 에 VITE_API_BASE_URL=http://localhost:8001 식으로 적으면 된다)

import type {
  AlertsResponse,
  AnomaliesResponse,
  CategoriesResponse,
  CategoryPulseResponse,
  ChangesResponse,
  CompareResponse,
  HealthResponse,
  LaptopsResponse,
  NewsResponse,
  PredictionResponse,
  PriceListResponse,
  ProductDetailResponse,
  ScrapeRunsResponse,
  SortOrder,
  SpotlightsResponse,
  WatchlistResponse,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`요청 실패 (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
}

async function sendJson<T>(method: "POST" | "PUT", path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // 읽기전용으로 배포된 서버는 쓰기 라우트를 아예 등록하지 않아서 405가 온다.
    // "요청 실패 (405)"만 보면 원인을 알 수 없으므로 사람이 읽을 수 있는 말로 바꾼다.
    if (res.status === 405) {
      throw new Error("읽기전용으로 공개된 서버라 편집할 수 없어요. 편집은 집 PC에서 해주세요.");
    }
    throw new Error(`요청 실패 (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health");
}

export function getCategories(): Promise<CategoriesResponse> {
  return getJson<CategoriesResponse>("/api/categories");
}

export function getCategoryPulse(category: string): Promise<CategoryPulseResponse> {
  return getJson<CategoryPulseResponse>(`/api/categories/${encodeURIComponent(category)}/pulse`);
}

export function getPrices(params: {
  category?: string;
  q?: string;
  sort?: SortOrder;
  limit?: number;
  offset?: number;
}): Promise<PriceListResponse> {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.q) qs.set("q", params.q);
  if (params.sort) qs.set("sort", params.sort);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  return getJson<PriceListResponse>(`/api/prices?${qs.toString()}`);
}

export function getProductDetail(code: string): Promise<ProductDetailResponse> {
  return getJson<ProductDetailResponse>(`/api/products/${encodeURIComponent(code)}`);
}

export function getAnomalies(): Promise<AnomaliesResponse> {
  return getJson<AnomaliesResponse>("/api/anomalies");
}

export function getPrediction(code: string): Promise<PredictionResponse> {
  return getJson<PredictionResponse>(`/api/prediction/${encodeURIComponent(code)}`);
}

export function getCompare(codes: string[]): Promise<CompareResponse> {
  return getJson<CompareResponse>(`/api/compare?codes=${codes.map(encodeURIComponent).join(",")}`);
}

export function getWatchlist(): Promise<WatchlistResponse> {
  return getJson<WatchlistResponse>("/api/watchlist");
}

export function trackProduct(pcode: string, tracked: boolean): Promise<{ status: string }> {
  return sendJson("POST", `/api/watchlist/${encodeURIComponent(pcode)}`, { tracked });
}

export function saveTarget(
  pcode: string,
  targetPrice: number | null,
  memo: string,
): Promise<{ status: string }> {
  return sendJson("PUT", `/api/watchlist/${encodeURIComponent(pcode)}/target`, {
    target_price: targetPrice,
    memo,
  });
}

export function getScrapeRuns(): Promise<ScrapeRunsResponse> {
  return getJson<ScrapeRunsResponse>("/api/scrape-runs");
}

export function getNews(): Promise<NewsResponse> {
  return getJson<NewsResponse>("/api/news");
}

export function getChanges(): Promise<ChangesResponse> {
  return getJson<ChangesResponse>("/api/changes");
}

export function getAlerts(): Promise<AlertsResponse> {
  return getJson<AlertsResponse>("/api/alerts");
}

export function getSpotlights(): Promise<SpotlightsResponse> {
  return getJson<SpotlightsResponse>("/api/spotlights");
}

export function getLaptops(category: string): Promise<LaptopsResponse> {
  return getJson<LaptopsResponse>(`/api/laptops/${encodeURIComponent(category)}`);
}
