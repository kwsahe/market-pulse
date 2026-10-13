// frontend/src/utils/categoryPulse.ts
// 개요 화면의 "카테고리별 가격 변동" 표에 들어갈 줄을 만든다.

import type { CategoryPulseResponse } from "../types/api";

export interface PulseRow {
  category: string;
  median: number | null;
  up: number | null;
  down: number | null;
}

/** 카테고리별 pulse 응답을 표 한 줄씩으로 만든다.
 *  요청 하나가 실패해도 표 전체를 비우지 않고 그 줄만 비운다(null → 화면에선 "—"). */
export function toPulseRows(
  categories: string[],
  results: PromiseSettledResult<CategoryPulseResponse>[],
): PulseRow[] {
  return categories.map((category, i) => {
    const r = results[i];
    if (r?.status !== "fulfilled") return { category, median: null, up: null, down: null };
    return { category, median: r.value.median_price, up: r.value.up_count, down: r.value.down_count };
  });
}
