import { describe, expect, it } from "vitest";
import { buildCsvString, escapeCsvCell } from "./csv";

describe("escapeCsvCell", () => {
  it("passes plain values through untouched", () => {
    expect(escapeCsvCell("삼성전자 DDR5 16GB")).toBe("삼성전자 DDR5 16GB");
    expect(escapeCsvCell(80000)).toBe("80000");
  });

  it("returns an empty string for null/undefined", () => {
    expect(escapeCsvCell(null)).toBe("");
    expect(escapeCsvCell(undefined)).toBe("");
  });

  it("quotes and escapes values containing commas, quotes, or newlines", () => {
    expect(escapeCsvCell("삼성, 32GB")).toBe('"삼성, 32GB"');
    expect(escapeCsvCell('상품 "특가"')).toBe('"상품 ""특가"""');
    expect(escapeCsvCell("줄바꿈\n포함")).toBe('"줄바꿈\n포함"');
  });
});

describe("buildCsvString", () => {
  const columns = [
    { label: "상품명", get: (r: { name: string; price: number }) => r.name },
    { label: "가격", get: (r: { name: string; price: number }) => r.price },
  ];

  it("builds a header row followed by one row per item", () => {
    const csv = buildCsvString(
      [
        { name: "RAM A", price: 80000 },
        { name: "RAM B", price: 95000 },
      ],
      columns,
    );
    expect(csv).toBe("상품명,가격\nRAM A,80000\nRAM B,95000");
  });

  it("still emits a header when rows is empty", () => {
    expect(buildCsvString([], columns)).toBe("상품명,가격\n");
  });
});
