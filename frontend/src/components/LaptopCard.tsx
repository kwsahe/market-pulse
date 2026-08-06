import { useState } from "react";
import { Link } from "react-router-dom";
import { trackProduct } from "../api/client";
import type { LaptopItem } from "../types/api";
import { ImageGalleryModal } from "./ImageGalleryModal";
import styles from "./LaptopCard.module.css";

export function LaptopCard({ item, onTrackChange }: { item: LaptopItem; onTrackChange: () => void }) {
  const [showGallery, setShowGallery] = useState(false);
  const [showSpecs, setShowSpecs] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleToggleTrack = async () => {
    setBusy(true);
    try {
      await trackProduct(item.pcode, !item.tracked);
      onTrackChange();
    } finally {
      setBusy(false);
    }
  };

  const isUp = item.change != null && item.change > 0;

  return (
    <div className={styles.card}>
      <div className={styles.imageWrap} onClick={() => setShowGallery(true)} role="button" tabIndex={0}>
        {item.image_url ? (
          <img src={item.image_url} alt={item.product} className={styles.image} />
        ) : (
          <div className={styles.noImage}>이미지 없음</div>
        )}
        <span className={styles.imageCount}>🖼️ {item.images.length}</span>
      </div>

      <div className={styles.body}>
        <div className={styles.badgeRow}>
          {item.code && <span className={styles.codeBadge}>{item.code}</span>}
          {item.is_new && <span className={styles.newBadge}>🆕 NEW</span>}
        </div>
        <div className={styles.name}>{item.product}</div>
        <div className={styles.price}>{item.price.toLocaleString()}원</div>

        {item.change != null && item.change !== 0 && (
          <div className={isUp ? styles.changeUp : styles.changeDown}>
            {isUp ? "📈" : "📉"} {isUp ? "+" : ""}
            {item.change.toLocaleString()}원 ({item.change_pct}%)
          </div>
        )}

        {item.best_buy &&
          (item.best_buy.is_best_now ? (
            <div className={styles.bestNow}>🏆 지금이 역대 최저가예요!</div>
          ) : (
            <div className={styles.bestPast}>
              🕒 {item.best_buy.best_date}에 샀으면 {item.best_buy.savings.toLocaleString()}원 이득이었어요
            </div>
          ))}

        <label className={styles.trackLabel}>
          <input type="checkbox" checked={item.tracked} disabled={busy} onChange={handleToggleTrack} />
          🎯 집중 추적
        </label>

        <div className={styles.actions}>
          <button className={styles.specToggle} onClick={() => setShowSpecs((s) => !s)}>
            📋 전체 스펙 {showSpecs ? "▲" : "▼"}
          </button>
          {item.code && (
            <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.detailLink}>
              📈 상세보기
            </Link>
          )}
        </div>

        {showSpecs && (
          <table className={styles.specTable}>
            <tbody>
              {item.full_specs.map((s) => (
                <tr key={s.spec_key}>
                  <td>{s.spec_key}</td>
                  <td>{s.spec_value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className={styles.date}>수집일: {item.date}</div>
      </div>

      {showGallery && (
        <ImageGalleryModal product={item.product} images={item.images} onClose={() => setShowGallery(false)} />
      )}
    </div>
  );
}
