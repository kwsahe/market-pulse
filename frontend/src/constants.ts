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
