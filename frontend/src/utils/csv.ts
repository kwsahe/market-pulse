// frontend/src/utils/csv.ts
// dashboard/tabs/common.py의 to_csv_bytes()와 동일한 목적 — 엑셀에서 한글이 깨지지 않도록
// UTF-8 BOM을 붙여서 클라이언트에서 바로 CSV 파일을 내려받게 한다(서버 왕복 불필요).

function escapeCsvCell(value: unknown): string {
  const str = value == null ? "" : String(value);
  if (/[",\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function downloadCsv<T>(
  rows: T[],
  columns: { label: string; get: (row: T) => unknown }[],
  filename: string,
): void {
  const header = columns.map((c) => escapeCsvCell(c.label)).join(",");
  const body = rows.map((row) => columns.map((c) => escapeCsvCell(c.get(row))).join(",")).join("\n");
  const csv = `${header}\n${body}`;

  const blob = new Blob(["﻿", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
