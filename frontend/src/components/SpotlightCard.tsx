import { Link } from "react-router-dom";
import { CategoryBadge } from "./CategoryBadge";
import styles from "./SpotlightCard.module.css";

export function SpotlightCard({
  code,
  product,
  category,
  imageUrl,
  priceLine,
  badge,
  badgeClassName,
}: {
  code: string;
  product: string;
  category: string;
  imageUrl?: string | null;
  priceLine: string;
  badge?: string;
  badgeClassName?: string;
}) {
  return (
    <div className={styles.card}>
      <div className={styles.imageWrap}>
        {imageUrl ? (
          <img src={imageUrl} alt={product} className={styles.image} />
        ) : (
          <div className={styles.noImage}>이미지 없음</div>
        )}
      </div>
      <div className={styles.info}>
        <CategoryBadge category={category} />
        <div className={styles.name}>{product}</div>
        <div className={styles.priceLine}>
          {priceLine} {badge && <span className={badgeClassName ?? styles.badge}>{badge}</span>}
        </div>
        {code && (
          <Link to={`/products/${encodeURIComponent(code)}`} className={styles.link}>
            🔗 상품 바로가기
          </Link>
        )}
      </div>
    </div>
  );
}
