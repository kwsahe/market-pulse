import type { SortOrder } from "../types/api";
import styles from "./SearchBar.module.css";

export function SearchBar({
  q,
  onQChange,
  sort,
  onSortChange,
}: {
  q: string;
  onQChange: (value: string) => void;
  sort: SortOrder;
  onSortChange: (value: SortOrder) => void;
}) {
  return (
    <div className={styles.bar}>
      <input
        className={styles.input}
        type="text"
        placeholder="🔍 상품명 검색..."
        value={q}
        onChange={(e) => onQChange(e.target.value)}
      />
      <select
        className={styles.select}
        value={sort}
        onChange={(e) => onSortChange(e.target.value as SortOrder)}
      >
        <option value="price_asc">가격 낮은 순</option>
        <option value="price_desc">가격 높은 순</option>
      </select>
    </div>
  );
}
