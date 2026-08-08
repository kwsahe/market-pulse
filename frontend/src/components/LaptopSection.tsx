import { useEffect, useMemo, useState } from "react";
import { getLaptops } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { downloadCsv } from "../utils/csv";
import { filterLaptops } from "../utils/laptopFilter";
import { LaptopCard } from "./LaptopCard";
import styles from "./LaptopSection.module.css";

export function LaptopSection({ category }: { category: string }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, loading, error } = useFetch(() => getLaptops(category), [category, refreshKey]);

  const [search, setSearch] = useState("");
  const [selections, setSelections] = useState<Record<string, Set<string>>>({});
  const [priceRange, setPriceRange] = useState<[number, number] | null>(null);
  const [showNew, setShowNew] = useState(false);

  // 카테고리가 바뀌거나 새 데이터가 오면 필터를 "전체 선택" 상태로 리셋한다
  useEffect(() => {
    if (!data) return;
    const next: Record<string, Set<string>> = {};
    for (const key of data.filter_spec_keys) {
      next[key] = new Set(data.filter_options[key] ?? []);
    }
    setSelections(next);
    if (data.items.length > 0) {
      const prices = data.items.map((i) => i.price);
      setPriceRange([Math.min(...prices), Math.max(...prices)]);
    } else {
      setPriceRange(null);
    }
    setSearch("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const filtered = useMemo(() => {
    if (!data || !priceRange) return [];
    return filterLaptops(data.items, {
      search,
      selections,
      filterOptions: data.filter_options,
      filterSpecKeys: data.filter_spec_keys,
      priceRange,
    });
  }, [data, search, selections, priceRange]);

  const toggleFilterValue = (key: string, value: string) => {
    setSelections((prev) => {
      const next = new Set(prev[key] ?? []);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return { ...prev, [key]: next };
    });
  };

  const handleExportCsv = () => {
    downloadCsv(
      filtered,
      [
        { label: "상품명", get: (r) => r.product },
        { label: "카테고리", get: () => category },
        { label: "가격", get: (r) => r.price },
        { label: "수집일", get: (r) => r.date },
      ],
      `market_pulse_${category}.csv`,
    );
  };

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">노트북 데이터를 불러오지 못했어요: {error}</p>;
  if (!data || data.items.length === 0) {
    return <p>{category} 상세 데이터가 아직 없어요.</p>;
  }

  const newItems = data.items.filter((i) => i.is_new);

  return (
    <div className={styles.wrap}>
      {newItems.length > 0 && (
        <div className={styles.newBanner}>
          <button className={styles.newBannerToggle} onClick={() => setShowNew((s) => !s)}>
            🆕 오늘({data.latest_date}) 새로 발견된 노트북 {newItems.length}종이 있어요! {showNew ? "▲" : "▼"}
          </button>
          {showNew && (
            <ul className={styles.newList}>
              {newItems.map((item) => (
                <li key={item.pcode}>
                  {item.product} · {item.price.toLocaleString()}원
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <input
        className={styles.search}
        type="text"
        placeholder="🔎 상품명으로 검색..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className={styles.filters}>
        {data.filter_spec_keys.map((key) => {
          const options = data.filter_options[key] ?? [];
          if (options.length === 0) return null;
          const selected = selections[key] ?? new Set<string>();
          return (
            <div key={key} className={styles.filterGroup}>
              <div className={styles.filterLabel}>{key}</div>
              <div className={styles.filterOptions}>
                {options.map((opt) => (
                  <label key={opt} className={styles.filterChip}>
                    <input
                      type="checkbox"
                      checked={selected.has(opt)}
                      onChange={() => toggleFilterValue(key, opt)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            </div>
          );
        })}

        {priceRange && (
          <div className={styles.priceFilter}>
            <div className={styles.filterLabel}>가격대(원)</div>
            <div className={styles.priceInputs}>
              <input
                type="number"
                value={priceRange[0]}
                onChange={(e) => setPriceRange([Number(e.target.value), priceRange[1]])}
              />
              <span>~</span>
              <input
                type="number"
                value={priceRange[1]}
                onChange={(e) => setPriceRange([priceRange[0], Number(e.target.value)])}
              />
            </div>
          </div>
        )}
      </div>

      <div className={styles.toolbar}>
        <span className={styles.count}>{filtered.length}개 상품 표시 중</span>
        {filtered.length > 0 && (
          <button className={styles.csvBtn} onClick={handleExportCsv}>
            ⬇️ {category} 목록 CSV ({filtered.length}개)
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <p>조건에 맞는 노트북이 없어요. 필터를 조정해보세요.</p>
      ) : (
        <div className={styles.grid}>
          {filtered.map((item) => (
            <LaptopCard key={item.pcode} item={item} onTrackChange={() => setRefreshKey((k) => k + 1)} />
          ))}
        </div>
      )}
    </div>
  );
}
