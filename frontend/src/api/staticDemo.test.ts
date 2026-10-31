import { afterEach, describe, expect, it, vi } from "vitest";
import { staticGet } from "./staticDemo";

const item = (code: string, category: string, product: string, price: number) => ({
  code, category, product, price, date: "2026-10-31", is_anomaly: false,
});

const FILES: Record<string, unknown> = {
  "prices.json": {
    items: [
      item("RAM-1", "DDR5 RAM", "삼성 DDR5 16GB", 80000),
      item("RAM-2", "DDR5 RAM", "SK하이닉스 DDR5 32GB", 150000),
      item("CPU-1", "CPU", "AMD 라이젠 7", 300000),
    ],
    total: 3,
  },
  "compare/RAM.json": {
    "RAM-1": { product: { code: "RAM-1", category: "DDR5 RAM", product: "a", price: 80000 }, specs: [{ label: "용량", value: 16 }] },
    "RAM-2": { product: { code: "RAM-2", category: "DDR5 RAM", product: "b", price: 150000 }, specs: [{ label: "용량", value: 32 }] },
  },
  "compare/CPU.json": {
    "CPU-1": { product: { code: "CPU-1", category: "CPU", product: "c", price: 300000 }, specs: [] },
  },
};

vi.stubGlobal("fetch", async (url: string) => {
  const file = url.split("demo-data/")[1];
  const body = FILES[file];
  return { ok: body !== undefined, status: body === undefined ? 404 : 200, json: async () => body };
});

afterEach(() => vi.clearAllMocks());

describe("staticGet /api/prices", () => {
  it("filters by category and search text like the API", async () => {
    const res = await staticGet("/api/prices?category=DDR5+RAM&q=ddr5&sort=price_desc&limit=1&offset=0");
    expect(res).toEqual({ items: [expect.objectContaining({ code: "RAM-2" })], total: 2 });
  });

  it("pages with offset and defaults to 100 rows ascending", async () => {
    const res = (await staticGet("/api/prices?offset=1")) as { items: { code: string }[]; total: number };
    expect(res.items.map((i) => i.code)).toEqual(["RAM-2", "CPU-1"]);
    expect(res.total).toBe(3);
  });
});

describe("staticGet /api/compare", () => {
  it("joins per-product entries into one spec table", async () => {
    const res = await staticGet("/api/compare?codes=RAM-1,RAM-2");
    expect(res).toEqual({
      products: [expect.objectContaining({ code: "RAM-1" }), expect.objectContaining({ code: "RAM-2" })],
      spec_table: [{ label: "용량", values: [16, 32] }],
    });
  });

  it("rejects mixed categories and unknown codes", async () => {
    await expect(staticGet("/api/compare?codes=RAM-1,CPU-1")).rejects.toThrow("400");
    await expect(staticGet("/api/compare?codes=RAM-1,RAM-9")).rejects.toThrow("404");
  });
});
