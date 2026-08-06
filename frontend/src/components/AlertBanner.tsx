import { Link } from "react-router-dom";
import { getAlerts } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { ChangeCard } from "./ChangeCard";
import styles from "./AlertBanner.module.css";

export function AlertBanner() {
  const { data } = useFetch(() => getAlerts(), []);
  if (!data) return null;
  if (data.tracked_drops.length === 0 && data.target_reached.length === 0) return null;

  return (
    <div className={styles.wrap}>
      {data.tracked_drops.length > 0 && (
        <details className={styles.banner} open>
          <summary>🔔 집중 추적 중인 상품 {data.tracked_drops.length}개의 가격이 내렸어요!</summary>
          <div className={styles.grid}>
            {data.tracked_drops.map((item, i) => (
              <ChangeCard key={`${item.code || item.product}-${i}`} item={item} />
            ))}
          </div>
        </details>
      )}
      {data.target_reached.length > 0 && (
        <details className={styles.banner} open>
          <summary>🎯 목표가에 도달한 추적 상품 {data.target_reached.length}개가 있어요!</summary>
          <div className={styles.grid}>
            {data.target_reached.map((item, i) => (
              <div key={`${item.code || item.product}-${i}`} className={styles.targetCard}>
                {item.image_url ? (
                  <img src={item.image_url} alt={item.product} className={styles.targetImage} />
                ) : (
                  <div className={styles.noImage}>이미지 없음</div>
                )}
                <div>
                  <div className={styles.targetName}>{item.product}</div>
                  <div className={styles.targetPrice}>
                    현재가 {item.price.toLocaleString()}원 · 목표가 {item.target_price.toLocaleString()}원
                  </div>
                  {item.code && (
                    <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.link}>
                      🔍 상세보기
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
