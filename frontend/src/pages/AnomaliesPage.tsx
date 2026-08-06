import { Link } from "react-router-dom";
import { getAnomalies } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import { CategoryBadge } from "../components/CategoryBadge";
import type { IqrAnomaly, ZScoreAnomaly } from "../types/api";
import styles from "./AnomaliesPage.module.css";

function AnomalyRow({ item }: { item: ZScoreAnomaly | IqrAnomaly }) {
  const inner = (
    <>
      <span className={item.direction === "고가" ? styles.dirHigh : styles.dirLow}>
        {item.direction === "고가" ? "📈" : "📉"} {item.direction}
      </span>
      <CategoryBadge category={item.category} />
      <span className={styles.name}>{item.product}</span>
      <span className={styles.price}>{item.price.toLocaleString()}원</span>
      <span className={styles.detail}>
        {"z_score" in item
          ? `Z: ${item.z_score.toFixed(2)}`
          : `범위: ${item.lower_bound.toLocaleString()}~${item.upper_bound.toLocaleString()}원`}
      </span>
    </>
  );
  return item.code ? (
    <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.row}>
      {inner}
    </Link>
  ) : (
    <div className={styles.row}>{inner}</div>
  );
}

export function AnomaliesPage() {
  const { data, loading, error } = useFetch(() => getAnomalies(), []);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">이상치 데이터를 불러오지 못했어요: {error}</p>;
  if (!data) return null;

  return (
    <>
      <section>
        <SectionHeader icon="📊" title="카테고리별 통계" />
        <div className={styles.statGrid}>
          {data.category_stats.map((s) => (
            <div key={s.category} className={styles.statCard}>
              <div className={styles.statCategory}>{s.category}</div>
              <div className={styles.statLine}>상품 수 {s.count}개</div>
              <div className={styles.statLine}>평균 {Math.round(s.mean).toLocaleString()}원</div>
              <div className={styles.statLine}>최저 {Math.round(s.min).toLocaleString()}원</div>
              <div className={styles.statLine}>최고 {Math.round(s.max).toLocaleString()}원</div>
              <div className={styles.statLine}>표준편차 {Math.round(s.std).toLocaleString()}원</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader icon="🔵" title="Z-score 이상치" subtitle="평균에서 표준편차 2.5배 이상 벗어난 상품" />
        {data.zscore.length === 0 ? (
          <p>✅ 이상치 없음</p>
        ) : (
          <div className={styles.list}>
            {data.zscore.map((item, i) => (
              <AnomalyRow key={`${item.code || item.product}-${i}`} item={item} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader icon="🟠" title="IQR 이상치" subtitle="중간 50% 범위의 1.5배를 벗어난 상품" />
        {data.iqr.length === 0 ? (
          <p>✅ 이상치 없음</p>
        ) : (
          <div className={styles.list}>
            {data.iqr.map((item, i) => (
              <AnomalyRow key={`${item.code || item.product}-${i}`} item={item} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
