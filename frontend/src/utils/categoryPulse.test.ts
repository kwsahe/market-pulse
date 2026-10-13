import { describe, expect, it } from "vitest";
import { toPulseRows } from "./categoryPulse";
import type { CategoryPulseResponse } from "../types/api";

const pulse = (category: string, median: number, up: number, down: number) =>
  ({ category, median_price: median, up_count: up, down_count: down }) as CategoryPulseResponse;

describe("toPulseRows", () => {
  it("keeps request order and maps median/up/down", () => {
    const rows = toPulseRows(
      ["CPU", "그래픽카드"],
      [
        { status: "fulfilled", value: pulse("CPU", 349730, 5, 36) },
        { status: "fulfilled", value: pulse("그래픽카드", 1500000, 0, 0) },
      ],
    );
    expect(rows).toEqual([
      { category: "CPU", median: 349730, up: 5, down: 36 },
      { category: "그래픽카드", median: 1500000, up: 0, down: 0 },
    ]);
  });

  it("blanks only the row whose request failed", () => {
    const rows = toPulseRows(
      ["CPU", "게이밍 마우스"],
      [
        { status: "rejected", reason: new Error("500") },
        { status: "fulfilled", value: pulse("게이밍 마우스", 45000, 2, 1) },
      ],
    );
    expect(rows[0]).toEqual({ category: "CPU", median: null, up: null, down: null });
    expect(rows[1].median).toBe(45000);
  });
});
