import { useEffect, useMemo, useState } from "react";
import { getPrediction, getPrices } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import type { PredictionResponse } from "../types/api";
import styles from "./PredictionPage.module.css";

const CATEGORIES = ["게이밍 노트북", "DDR5 RAM", "NVMe SSD", "그래픽카드", "CPU"];

export function PredictionPage() {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [code, setCode] = useState("");
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);

  const { data: pricesData, loading: pricesLoading } = useFetch(
    () => getPrices({ category, sort: "price_asc" }),
    [category],
  );

  // 같은 pcode를 공유하는 용량 변형(SSD 1TB/2TB 등)은 내부 코드가 같아서 어차피 같은 예측
  // 결과로 귀결된다 — 드롭다운에서 코드당 하나만 대표로 남겨 <option> key/value 충돌을 막는다.
  const productOptions = useMemo(() => {
    if (!pricesData) return [];
    const seen = new Set<string>();
    return pricesData.items.filter((i) => {
      if (!i.code || seen.has(i.code)) return false;
      seen.add(i.code);
      return true;
    });
  }, [pricesData]);

  useEffect(() => {
    setCode(productOptions[0]?.code ?? "");
  }, [productOptions]);

  useEffect(() => {
    if (!code) {
      setPrediction(null);
      return;
    }
    let cancelled = false;
    setLoadingPrediction(true);
    getPrediction(code)
      .then((res) => {
        if (!cancelled) {
          setPrediction(res);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setPrediction(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingPrediction(false);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  return (
    <section>
      <SectionHeader icon="🔮" title="가격 예측" subtitle="제품을 선택하면 스펙 기반 적정 가격을 예측하고 실제 판매가와 비교해드려요." />

      <div className={styles.selectRow}>
        <select className={styles.select} value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select className={styles.select} value={code} onChange={(e) => setCode(e.target.value)} disabled={pricesLoading}>
          {productOptions.map((i) => (
            <option key={i.code} value={i.code}>
              {i.product}
            </option>
          ))}
        </select>
      </div>

      {loadingPrediction && <p>예측 계산 중...</p>}
      {error && <p role="alert">예측을 만들 수 없어요: {error}</p>}

      {prediction && (
        <>
          <div className={styles.infoRow}>
            <div className={styles.infoCard}>
              <div className={styles.infoLabel}>모델</div>
              <div className={styles.infoValue}>{prediction.model_name}</div>
            </div>
            <div className={styles.infoCard}>
              <div className={styles.infoLabel}>R² 점수</div>
              <div className={styles.infoValue}>{prediction.r2.toFixed(3)}</div>
            </div>
            <div className={styles.infoCard}>
              <div className={styles.infoLabel}>학습 데이터</div>
              <div className={styles.infoValue}>{prediction.data_count}개</div>
            </div>
          </div>

          <div className={styles.resultRow}>
            <div className={styles.resultCard}>
              <div className={styles.infoLabel}>실제 가격</div>
              <div className={styles.resultValue}>{prediction.actual_price.toLocaleString()}원</div>
            </div>
            <div className={styles.resultCard}>
              <div className={styles.infoLabel}>예측 가격</div>
              <div className={styles.resultValue}>{Math.round(prediction.predicted_price).toLocaleString()}원</div>
              <div className={styles.infoLabel}>
                범위(80%) {Math.round(prediction.low).toLocaleString()} ~ {Math.round(prediction.high).toLocaleString()}원
              </div>
            </div>
            <div className={styles.resultCard}>
              <div className={styles.infoLabel}>적정가 점수</div>
              <div className={styles.scoreValue}>
                {prediction.fair_score}점 · {prediction.fair_label}
              </div>
            </div>
          </div>

          <div className={styles.splitRow}>
            <div>
              <SectionHeader icon="📊" title="스펙별 가격 기여도" />
              {prediction.contributions.length === 0 ? (
                <p>뚜렷한 기여 스펙을 찾지 못했어요.</p>
              ) : (
                <div className={styles.contribList}>
                  {prediction.contributions.map((c) => (
                    <div key={c.feature} className={styles.contribRow}>
                      <span className={styles.contribLabel}>{c.label}</span>
                      <div className={styles.barTrack}>
                        <div
                          className={c.contribution > 0 ? styles.barPos : styles.barNeg}
                          style={{ width: `${Math.min(100, (Math.abs(c.contribution) / (Math.abs(prediction.contributions[0].contribution) || 1)) * 100)}%` }}
                        />
                      </div>
                      <span className={styles.contribValue}>{Math.round(c.contribution).toLocaleString()}원</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <SectionHeader icon="🔍" title="비슷한 스펙 제품 비교" />
              {prediction.similar_products.length === 0 ? (
                <p>비교할 제품이 없어요.</p>
              ) : (
                <div className={styles.similarList}>
                  {prediction.similar_products.map((s) => {
                    const diff = s.price - prediction.actual_price;
                    return (
                      <div key={s.product} className={styles.similarItem}>
                        <div className={styles.similarName}>{s.product}</div>
                        <div className={styles.meta}>
                          {s.price.toLocaleString()}원 ·{" "}
                          {diff > 0 ? `🔺 +${diff.toLocaleString()}원` : diff < 0 ? `🔻 ${diff.toLocaleString()}원` : "동일"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
