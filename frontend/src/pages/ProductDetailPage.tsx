import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProductDetail, getWatchlist, trackProduct } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { CategoryBadge } from "../components/CategoryBadge";
import { PriceHistoryChart } from "../components/PriceHistoryChart";
import { categoryColor } from "../constants";
import styles from "./ProductDetailPage.module.css";

function TrackToggle({ pcode }: { pcode: string }) {
  const [tracked, setTracked] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getWatchlist().then((res) => {
      if (!cancelled) setTracked(res.items.some((item) => item.pcode === pcode));
    });
    return () => {
      cancelled = true;
    };
  }, [pcode]);

  if (tracked === null) return null;

  const toggle = async () => {
    setBusy(true);
    try {
      await trackProduct(pcode, !tracked);
      setTracked(!tracked);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button className={tracked ? styles.trackBtnActive : styles.trackBtn} onClick={toggle} disabled={busy}>
      {tracked ? "🎯 추적 중 (해제하기)" : "🎯 집중 추적"}
    </button>
  );
}

export function ProductDetailPage() {
  const { code = "" } = useParams<{ code: string }>();
  const { data, loading, error } = useFetch(() => getProductDetail(code), [code]);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">상품을 찾을 수 없어요: {error}</p>;
  if (!data) return null;

  const mainImage = data.images.find((img) => img.image_type === "main");
  const detailImages = data.images.filter((img) => img.image_type === "detail");
  const diffFromMinPct =
    data.hist_min && data.hist_min > 0 ? ((data.price - data.hist_min) / data.hist_min) * 100 : 0;

  return (
    <div className={styles.wrap}>
      <Link to="/" className={styles.back}>
        ← 목록으로
      </Link>

      <div className={styles.header}>
        <div className={styles.imageWrap}>
          {mainImage ? (
            <img src={mainImage.image_url} alt={data.product} className={styles.image} />
          ) : (
            <div className={styles.noImage}>이미지 없음</div>
          )}
        </div>
        <div className={styles.info}>
          <CategoryBadge category={data.category} />
          <h1 className={styles.name}>{data.product}</h1>
          <div className={styles.price}>{data.price.toLocaleString()}원</div>
          <p className={styles.meta}>
            상품번호 {data.code} · 최근 수집일 {data.date}
          </p>
          {data.pcode && <TrackToggle pcode={data.pcode} />}
          {data.specs && (
            <details className={styles.specs}>
              <summary>상세 스펙</summary>
              <p>{data.specs}</p>
            </details>
          )}
        </div>
      </div>

      {detailImages.length > 0 && (
        <section>
          <h2 className={styles.sectionTitle}>🖼️ 상세정보 이미지</h2>
          <div className={styles.detailImages}>
            {detailImages.map((img) => (
              <img key={img.image_url} src={img.image_url} alt="" />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className={styles.sectionTitle}>📈 가격 추이</h2>
        {data.history.length >= 2 ? (
          <>
            <div className={styles.historyStats}>
              <div>
                <span className={styles.statLabel}>전체 최저가</span>
                <span className={styles.statValue}>{data.hist_min?.toLocaleString()}원</span>
              </div>
              <div>
                <span className={styles.statLabel}>전체 최고가</span>
                <span className={styles.statValue}>{data.hist_max?.toLocaleString()}원</span>
              </div>
            </div>
            <p className={styles.meta}>
              {diffFromMinPct > 0.5
                ? `현재가가 역대 최저가보다 ${diffFromMinPct.toFixed(1)}% 높아요.`
                : "🏆 지금이 역대 최저가예요!"}
            </p>
            <PriceHistoryChart history={data.history} color={categoryColor(data.category)} />
          </>
        ) : (
          <p className={styles.meta}>가격 추이는 2일 이상 데이터가 쌓이면 표시돼요.</p>
        )}
      </section>
    </div>
  );
}
