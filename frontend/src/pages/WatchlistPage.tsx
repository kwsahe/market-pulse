import { useState } from "react";
import { Link } from "react-router-dom";
import { getWatchlist, saveTarget, trackProduct } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import { CategoryBadge } from "../components/CategoryBadge";
import type { WatchlistItem } from "../types/api";
import styles from "./WatchlistPage.module.css";

function WatchlistCard({ item, onChanged }: { item: WatchlistItem; onChanged: () => void }) {
  const [targetInput, setTargetInput] = useState(item.target_price ? String(item.target_price) : "");
  const [memoInput, setMemoInput] = useState(item.memo ?? "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const parsed = Number(targetInput);
      await saveTarget(item.pcode, targetInput && parsed > 0 ? parsed : null, memoInput);
      onChanged();
    } finally {
      setSaving(false);
    }
  };

  const handleUntrack = async () => {
    await trackProduct(item.pcode, false);
    onChanged();
  };

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
        <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.name}>
          {item.product}
        </Link>
        <div className={styles.price}>현재가 {item.price.toLocaleString()}원</div>
        {item.target_reached && (
          <div className={styles.reached}>🎯 목표가 도달! 지금이 구매 타이밍이에요.</div>
        )}
        <div className={styles.targetRow}>
          <input
            type="number"
            className={styles.targetInput}
            placeholder="목표가(원, 비우면 해제)"
            value={targetInput}
            onChange={(e) => setTargetInput(e.target.value)}
          />
          <input
            type="text"
            className={styles.memoInput}
            placeholder="메모"
            value={memoInput}
            onChange={(e) => setMemoInput(e.target.value)}
          />
          <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
            저장
          </button>
        </div>
        <button className={styles.untrackBtn} onClick={handleUntrack}>
          추적 해제
        </button>
      </div>
    </div>
  );
}

export function WatchlistPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, loading, error } = useFetch(() => getWatchlist(), [refreshKey]);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">워치리스트를 불러오지 못했어요: {error}</p>;
  if (!data) return null;

  return (
    <section>
      <SectionHeader icon="🎯" title="워치리스트" subtitle="집중 추적 중인 노트북과 목표가 도달 여부를 확인해요." />
      {data.items.length === 0 ? (
        <p>추적 중인 상품이 없어요. 노트북 상세 페이지에서 🎯 집중 추적을 눌러보세요!</p>
      ) : (
        <div className={styles.grid}>
          {data.items.map((item) => (
            <WatchlistCard key={item.pcode} item={item} onChanged={() => setRefreshKey((k) => k + 1)} />
          ))}
        </div>
      )}
    </section>
  );
}
