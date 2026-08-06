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

  return (
    <section>
      <SectionHeader icon="📰" title="IT/과학 뉴스" />
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
              📡 {item.press} · 🕐 {item.published_at}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
