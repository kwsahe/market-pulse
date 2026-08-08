// frontend/src/utils/laptopFilter.ts
// LaptopSection의 필터 매칭 로직 — dashboard/laptop_view.py의 _apply_spec_filter()와 동일한 규칙:
// 스펙 정보가 아예 없는 상품은 그 필터 때문에 숨기지 않는다(필터 옵션 목록 자체가 실제 값만
// 담고 있어서 "정보없음"을 선택할 방법이 없기 때문). 순수 함수로 분리해 컴포넌트 없이 테스트한다.

import type { LaptopItem } from "../types/api";

export interface LaptopFilterParams {
  search: string;
  selections: Record<string, Set<string>>;
  filterOptions: Record<string, string[]>;
  filterSpecKeys: string[];
  priceRange: [number, number];
}

export function matchesLaptopFilters(item: LaptopItem, params: LaptopFilterParams): boolean {
  const { search, selections, filterOptions, filterSpecKeys, priceRange } = params;

  if (search && !item.product.toLowerCase().includes(search.toLowerCase())) return false;
  if (item.price < priceRange[0] || item.price > priceRange[1]) return false;

  for (const key of filterSpecKeys) {
    const selected = selections[key];
    const allOptions = filterOptions[key] ?? [];
    if (!selected || selected.size >= allOptions.length) continue; // 전체 선택 = 필터 없음
    const value = item.filter_values[key];
    if (value == null) continue; // 정보 없는 상품은 필터로 숨기지 않음
    if (!selected.has(value)) return false;
  }

  return true;
}

export function filterLaptops(items: LaptopItem[], params: LaptopFilterParams): LaptopItem[] {
  return items.filter((item) => matchesLaptopFilters(item, params));
}
