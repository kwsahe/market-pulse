import { describe, expect, it } from "vitest";
import type { LaptopItem } from "../types/api";
import { filterLaptops, type LaptopFilterParams } from "./laptopFilter";

function makeItem(overrides: Partial<LaptopItem> = {}): LaptopItem {
  return {
    pcode: "P1",
    code: "GN-1",
    category: "게이밍 노트북",
    product: "ASUS ROG STRIX G18",
    price: 3000000,
    date: "2026-08-06",
    image_url: null,
    images: [],
    full_specs: [],
    filter_values: { "GPU 칩셋": "RTX5080" },
    best_buy: null,
    change: null,
    change_pct: null,
    tracked: false,
    is_new: false,
    ...overrides,
  };
}

const baseParams: LaptopFilterParams = {
  search: "",
  selections: { "GPU 칩셋": new Set(["RTX5080", "RTX5090"]) },
  filterOptions: { "GPU 칩셋": ["RTX5080", "RTX5090"] },
  filterSpecKeys: ["GPU 칩셋"],
  priceRange: [0, 10_000_000],
};

describe("filterLaptops", () => {
  it("keeps every item when all filter options are selected (no-op filter)", () => {
    const items = [makeItem(), makeItem({ pcode: "P2", filter_values: { "GPU 칩셋": "RTX5090" } })];
    expect(filterLaptops(items, baseParams)).toHaveLength(2);
  });

  it("excludes items whose spec value isn't in the selected set", () => {
    const items = [makeItem({ filter_values: { "GPU 칩셋": "RTX5080" } })];
    const params = { ...baseParams, selections: { "GPU 칩셋": new Set(["RTX5090"]) } };
    expect(filterLaptops(items, params)).toHaveLength(0);
  });

  it("never hides an item just because it's missing that spec entirely", () => {
    // dashboard/laptop_view.py의 _apply_spec_filter와 동일한 규칙: 정보 없음(null)은 필터 대상 제외
    const items = [makeItem({ filter_values: { "GPU 칩셋": null } })];
    const params = { ...baseParams, selections: { "GPU 칩셋": new Set(["RTX5090"]) } };
    expect(filterLaptops(items, params)).toHaveLength(1);
  });

  it("filters by price range inclusively", () => {
    const items = [makeItem({ price: 1_000_000 }), makeItem({ pcode: "P2", price: 5_000_000 })];
    const params = { ...baseParams, priceRange: [1_000_000, 1_000_000] as [number, number] };
    const result = filterLaptops(items, params);
    expect(result).toHaveLength(1);
    expect(result[0].price).toBe(1_000_000);
  });

  it("filters by case-insensitive product name search", () => {
    const items = [makeItem({ product: "ASUS ROG Strix G18" })];
    expect(filterLaptops(items, { ...baseParams, search: "strix" })).toHaveLength(1);
    expect(filterLaptops(items, { ...baseParams, search: "레노버" })).toHaveLength(0);
  });
});
