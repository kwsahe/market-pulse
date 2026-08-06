import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getCompare, getPrices } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import { CategoryBadge } from "../components/CategoryBadge";
import type { CompareResponse } from "../types/api";
import styles from "./ComparePage.module.css";

// ml/price_prediction.py의 FEATURE_EXTRACTORS 키와 동일 — 예측 모델이 있는 카테고리만 비교 가능.
const CATEGORIES = ["게이밍 노트북", "DDR5 RAM", "NVMe SSD", "그래픽카드", "CPU"];

export function ComparePage() {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: pricesData, loading: pricesLoading } = useFetch(
    () => getPrices({ category, sort: "price_asc" }),
    [category],
  );

  // 같은 pcode를 공유하는 용량 변형은 내부 코드가 같아 어차피 같은 비교 결과로 귀결된다 —
  // 코드당 하나만 대표로 남겨 체크리스트 key 충돌과 "다른 항목인데 같이 체크됨" 혼란을 막는다.
  const pickOptions = useMemo(() => {
    if (!pricesData) return [];
    const seen = new Set<string>();
    return pricesData.items.filter((i) => {
      if (!i.code || seen.has(i.code)) return false;
      seen.add(i.code);
      return true;
    });
  }, [pricesData]);

  useEffect(() => {
    setSelected([]);
    setResult(null);
  }, [category]);

  useEffect(() => {
    if (selected.length < 2) {
      setResult(null);
      return;
    }
    let cancelled = false;
    getCompare(selected)
      .then((res) => {
        if (!cancelled) {
          setResult(res);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const toggle = (code: string) => {
    setSelected((prev) => {
      if (prev.includes(code)) return prev.filter((c) => c !== code);
      if (prev.length >= 5) return prev;
      return [...prev, code];
    });
  };

  return (
    <section>
      <SectionHeader icon="🔀" title="상품 비교" subtitle="같은 카테고리에서 2~5개 상품을 선택해 나란히 비교해보세요." />

      <select className={styles.select} value={category} onChange={(e) => setCategory(e.target.value)}>
        {CATEGORIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {pricesLoading && <p>상품 목록 불러오는 중...</p>}
      {pricesData && (
        <div className={styles.pickList}>
          {pickOptions.map((item) => (
            <label key={item.code} className={styles.pickItem}>
              <input
                type="checkbox"
                checked={selected.includes(item.code)}
                disabled={!selected.includes(item.code) && selected.length >= 5}
                onChange={() => toggle(item.code)}
              />
              {item.product} · {item.price.toLocaleString()}원
            </label>
          ))}
        </div>
      )}

      {selected.length > 0 && selected.length < 2 && <p>비교하려면 2개 이상 선택해주세요.</p>}
      {error && <p role="alert">비교 데이터를 불러오지 못했어요: {error}</p>}

      {result && (
        <>
          <div className={styles.cards}>
            {result.products.map((p) => (
              <div key={p.code} className={styles.card}>
                {p.image_url ? (
                  <img src={p.image_url} alt={p.product} className={styles.image} />
                ) : (
                  <div className={styles.noImage}>이미지 없음</div>
                )}
                <CategoryBadge category={p.category} />
                <Link to={`/products/${encodeURIComponent(p.code)}`} className={styles.name}>
                  {p.product}
                </Link>
                <div className={styles.price}>{p.price.toLocaleString()}원</div>
                {p.hist_min != null && (
                  <div className={styles.meta}>
                    과거 최저 {p.hist_min.toLocaleString()}원 · 최고 {p.hist_max?.toLocaleString()}원
                  </div>
                )}
                {p.predicted_price != null && (
                  <div className={styles.meta}>예측가 {Math.round(p.predicted_price).toLocaleString()}원</div>
                )}
                {p.fair_score != null && (
                  <div className={styles.scoreBadge}>
                    {p.fair_score}점 · {p.fair_label}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>스펙</th>
                  {result.products.map((p) => (
                    <th key={p.code}>{p.product.slice(0, 20)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.spec_table.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    {row.values.map((v, i) => (
                      <td key={i}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
