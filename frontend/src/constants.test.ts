import { describe, expect, it } from "vitest";
import { categoryColor } from "./constants";

describe("categoryColor", () => {
  it("returns the mapped color for a known category", () => {
    expect(categoryColor("DDR5 RAM")).toBe("#d95926");
  });

  it("falls back to the muted gray for an unknown category", () => {
    expect(categoryColor("존재하지않는카테고리")).toBe("#8b93a7");
  });
});
