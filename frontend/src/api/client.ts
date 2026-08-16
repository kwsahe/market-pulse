// frontend/src/api/client.ts
// FastAPI(api/main.py, 기본 8000번 포트) 호출 헬퍼.

import type {
  AlertsResponse,
  AnomaliesResponse,
  CategoriesResponse,
  CategoryPulseResponse,
  ChangesResponse,
  CompareResponse,
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

const API_BASE_URL = "http://localhost:8000";

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
    throw new Error(`요청 실패 (${res.status}): ${path}`);
  }
  return res.json() as Promise<T>;
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
