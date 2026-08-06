import { Link } from "react-router-dom";
import type { ProductSummary } from "../types/api";
import { CategoryBadge } from "./CategoryBadge";
import styles from "./ProductCard.module.css";

export function ProductCard({ product }: { product: ProductSummary }) {
  const inner = (
    <>
      <div className={styles.imageWrap}>
        {product.image_url ? (
          <img src={product.image_url} alt={product.product} className={styles.image} />
        ) : (
          <div className={styles.noImage}>이미지 없음</div>
        )}
        {product.is_anomaly && <span className={styles.anomalyBadge}>⚠️ 이상치</span>}
      </div>
      <div className={styles.body}>
        <CategoryBadge category={product.category} />
        <div className={styles.name} title={product.product}>
          {product.product}
        </div>
        <div className={styles.price}>{product.price.toLocaleString()}원</div>
        {product.change != null && product.change !== 0 && (
          <div className={product.change > 0 ? styles.changeUp : styles.changeDown}>
            {product.change > 0 ? "📈" : "📉"} {product.change > 0 ? "+" : ""}
            {product.change.toLocaleString()}원 ({product.change_pct?.toFixed(1)}%)
          </div>
        )}
      </div>
    </>
  );

  if (!product.code) {
    return <div className={styles.card}>{inner}</div>;
  }

  return (
    <Link to={`/products/${encodeURIComponent(product.code)}`} className={styles.card}>
      {inner}
    </Link>
  );
}
