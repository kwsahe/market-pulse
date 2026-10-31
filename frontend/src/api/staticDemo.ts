// frontend/src/api/staticDemo.ts
// GitHub Pages 정적 데모용 — 서버 대신 미리 떠 둔 JSON(scripts/export_static_demo.py)을 읽는다.
// client.ts 의 getJson 이 VITE_STATIC_DEMO=1 빌드에서만 이 함수로 길을 바꾼다.
// 파일은 API 응답 그대로라, 여기서는 서버가 쿼리로 하던 일(카테고리·검색·정렬·페이지, 비교 조합)만 한다.

import type { CompareProduct, CompareResponse, PriceListResponse, ProductSummary } from "../types/api";

const DATA_URL = `${import.meta.env.BASE_URL}demo-data/`;

const cache = new Map<string, Promise<unknown>>();

function load<T>(file: string): Promise<T> {
  if (!cache.has(file)) {
    const p = fetch(DATA_URL + file).then((res) => {
      if (!res.ok) throw new Error(`요청 실패 (${res.status}): ${file}`);
      return res.json();
    });
    p.catch(() => cache.delete(file)); // 실패는 기억하지 않는다 — 다시 누르면 다시 받는다
    cache.set(file, p);
  }
  return cache.get(file) as Promise<T>;
}

function notFound(path: string): Error {
  return new Error(`요청 실패 (404): ${path}`);
}

// 상품번호 'RAM-12' → products/RAM.json 처럼 접두어별로 묶어 뒀다.
async function byCode<T>(dir: string, code: string, path: string): Promise<T> {
  const bundle = await load<Record<string, T>>(`${dir}/${code.split("-")[0]}.json`).catch(() => ({}) as Record<string, T>);
  const hit = bundle[code];
  if (!hit) throw notFound(path);
  return hit;
}

async function prices(qs: URLSearchParams): Promise<PriceListResponse> {
  const { items } = await load<{ items: ProductSummary[] }>("prices.json");
  const category = qs.get("category");
  const q = qs.get("q")?.toLowerCase();
  const desc = qs.get("sort") === "price_desc";
  const limit = Number(qs.get("limit") ?? 100);
  const offset = Number(qs.get("offset") ?? 0);

  const rows = items
    .filter((it) => (!category || it.category === category) && (!q || it.product.toLowerCase().includes(q)))
    .sort((a, b) => (desc ? b.price - a.price : a.price - b.price));
  return { items: rows.slice(offset, offset + limit), total: rows.length };
}

type CompareEntry = { product: CompareProduct; specs: { label: string; value: number }[] };

async function compare(codes: string[], path: string): Promise<CompareResponse> {
  if (codes.length < 2 || codes.length > 5) throw new Error(`요청 실패 (400): ${path}`);
  const entries = await Promise.all(codes.map((c) => byCode<CompareEntry>("compare", c, path)));
  if (new Set(entries.map((e) => e.product.category)).size > 1) throw new Error(`요청 실패 (400): ${path}`);
  return {
    products: entries.map((e) => e.product),
    spec_table: entries[0].specs.map((row, i) => ({
      label: row.label,
      values: entries.map((e) => e.specs[i]?.value ?? 0),
    })),
  };
}

export async function staticGet(path: string): Promise<unknown> {
  const [route, query = ""] = path.split("?");
  const qs = new URLSearchParams(query);
  const parts = route.replace(/^\/api\//, "").split("/").map(decodeURIComponent);

  switch (parts[0]) {
    case "prices":
      return prices(qs);
    case "compare":
      return compare((qs.get("codes") ?? "").split(",").filter(Boolean), path);
    case "products":
      return byCode("products", parts[1], path);
    case "prediction":
      return byCode("prediction", parts[1], path);
    case "laptops": {
      const hit = (await load<Record<string, unknown>>("laptops.json"))[parts[1]];
      if (!hit) throw notFound(path);
      return hit;
    }
    case "categories":
      if (parts[2] === "pulse") {
        const hit = (await load<Record<string, unknown>>("pulse.json"))[parts[1]];
        if (!hit) throw notFound(path);
        return hit;
      }
      return load("categories.json");
    default:
      return load(`${parts[0]}.json`);
  }
}
