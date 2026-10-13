// frontend/src/components/CategoryPulseTable.tsx
// 카테고리별 중앙값과, 직전 수집일 대비 인상·인하 상품 수.
// 평균가 막대 차트를 대체한다 — 카테고리 간 가격대가 약 70배 차이라 막대 대부분이 몇 px였고,
// 평균은 이상 가격 한 건(4.4억 마우스)에 크게 흔들려서 중앙값을 쓴다.

import type { ReactNode } from "react";
import { getCategoryPulse } from "../api/client";
import { categoryColor } from "../constants";
import { useFetch } from "../hooks/useFetch";
import { toPulseRows } from "../utils/categoryPulse";
import styles from "./CategoryPulseTable.module.css";

function count(value: number | null, mark: string, className: string): ReactNode {
  if (value == null) return "—";
  // 0 은 흐리게 — 움직인 카테고리만 눈에 띄도록
  return <span className={value > 0 ? className : styles.zero}>{mark} {value}</span>;
}

export function CategoryPulseTable({ categories }: { categories: string[] }) {
  const { data: rows, error } = useFetch(
    async () => toPulseRows(categories, await Promise.allSettled(categories.map((c) => getCategoryPulse(c)))),
    [categories.join("|")],
  );

  if (error) return <p role="alert" className={styles.note}>카테고리 변동을 불러오지 못했어요: {error}</p>;
  if (!rows) return <p className={styles.note}>불러오는 중…</p>;

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">카테고리</th>
            <th scope="col">중앙값</th>
            <th scope="col">인상</th>
            <th scope="col">인하</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.category}>
              <th scope="row">
                <span className={styles.dot} style={{ background: categoryColor(r.category) }} aria-hidden="true" />
                {r.category}
              </th>
              <td>{r.median == null ? "—" : `${Math.round(r.median).toLocaleString()}원`}</td>
              <td>{count(r.up, "▲", styles.up)}</td>
              <td>{count(r.down, "▼", styles.down)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
