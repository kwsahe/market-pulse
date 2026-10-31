import { useEffect, useMemo, useState } from "react";
import { getNews } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import styles from "./NewsPage.module.css";

export function NewsPage() {
  const { data, loading, error } = useFetch(() => getNews(), []);
  const [selectedPress, setSelectedPress] = useState<Set<string>>(new Set());

  const allPress = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set(data.items.map((n) => n.press).filter((p): p is string => !!p))).sort();
  }, [data]);

  useEffect(() => {
    if (allPress.length > 0) setSelectedPress(new Set(allPress));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">뉴스를 불러오지 못했어요: {error}</p>;
  if (!data) return null;
  if (data.items.length === 0) return <p>아직 뉴스 데이터가 없어요.</p>;

  const togglePress = (press: string) => {
    setSelectedPress((prev) => {
      const next = new Set(prev);
      if (next.has(press)) next.delete(press);
      else next.add(press);
      return next;
    });
  };

  const filtered = data.items.filter((n) => !n.press || selectedPress.has(n.press));
  // 'YYYY-MM-DD HH:MM' 문자열이라 사전순 최대가 가장 최근 수집 시각이다
  const lastCollected = data.items.reduce((max, n) => (n.collected_at > max ? n.collected_at : max), "");

  return (
    <section>
      <SectionHeader title="IT/과학 뉴스" />
      {/* 새 기사가 안 들어오는 이유를 밝혀 둔다 — 설명이 없으면 멈춘 데이터가 고장처럼 보인다 */}
      <p className={styles.notice}>
        뉴스 수집은 {lastCollected.slice(0, 10)} 이후 멈춰 있어요. 네이버 뉴스가 robots.txt로 자동 수집을
        금지해서 껐고, 네이버 검색 API로 바꾼 뒤 다시 시작할 예정이에요. 아래는 그때까지 모은 기사예요.
      </p>
      <div className={styles.pressFilter}>
        {allPress.map((press) => (
          <label key={press} className={styles.pressChip}>
            <input
              type="checkbox"
              checked={selectedPress.has(press)}
              onChange={() => togglePress(press)}
            />
            {press}
          </label>
        ))}
      </div>
      <div className={styles.list}>
        {filtered.map((item, i) => (
          <div key={`${item.title}-${i}`} className={styles.item}>
            <div className={styles.title}>{item.title}</div>
            <div className={styles.meta}>
              {item.press} · {item.published_at}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
