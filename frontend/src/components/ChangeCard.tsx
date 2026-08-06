import { Link } from "react-router-dom";
import type { ChangeItem } from "../types/api";
import { CategoryBadge } from "./CategoryBadge";
import styles from "./ChangeCard.module.css";

export function ChangeCard({ item }: { item: ChangeItem }) {
  const isUp = item.change > 0;
  return (
    <div className={styles.card}>
      <div className={styles.imageWrap}>
        {item.image_url ? (
          <img src={item.image_url} alt={item.product} className={styles.image} />
        ) : (
          <div className={styles.noImage}>이미지 없음</div>
        )}
      </div>
      <div className={styles.body}>
        <CategoryBadge category={item.category} />
        <div className={styles.name}>{item.product}</div>
        <div className={styles.priceRow}>
          {item.prev_price.toLocaleString()}원 → <strong>{item.current_price.toLocaleString()}원</strong>
        </div>
        <div className={isUp ? styles.changeUp : styles.changeDown}>
          {isUp ? "📈" : "📉"} {isUp ? "+" : ""}
          {item.change.toLocaleString()}원 ({isUp ? "+" : ""}
          {item.change_pct}%)
        </div>
        {item.specs && (
          <details className={styles.specs}>
            <summary>상세 스펙</summary>
            <p>{item.specs}</p>
          </details>
        )}
        {item.code && (
          <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.detailLink}>
            🔍 상세보기
          </Link>
        )}
      </div>
    </div>
  );
}
