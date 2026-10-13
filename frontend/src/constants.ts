// frontend/src/constants.ts
// dashboard/theme.py의 CATEGORY_COLORS와 동일한 매핑.

export const CATEGORY_COLORS: Record<string, string> = {
  "게이밍 노트북": "#3987e5",
  "DDR5 RAM": "#d95926",
  "NVMe SSD": "#199e70",
  "그래픽카드": "#c98500",
  CPU: "#d55181",
  "AI 노트북": "#9085e9",
  "게이밍 모니터": "#8749a4",
  "게이밍 키보드": "#454fdb",
  "게이밍 마우스": "#a34145",
};

export function categoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? "#8b93a7";
}

// 움직임 줄이기 설정. 페이지를 연 시점 값만 본다 — 설정을 바꾸면 새로고침해야 반영된다.
// (vitest 는 node 환경이라 window 가 없다)
export const REDUCED_MOTION =
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
