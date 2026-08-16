import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getCategories, getPrices } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { StatCards, type Stat } from "../components/StatCard";
import { SectionHeader } from "../components/SectionHeader";
import { CategoryBarChart } from "../components/CategoryBarChart";
import { CategoryTabs } from "../components/CategoryTabs";
import { SearchBar } from "../components/SearchBar";
import { ProductCard } from "../components/ProductCard";
import { AlertBanner } from "../components/AlertBanner";
import { SpotlightSection } from "../components/SpotlightSection";
import { LaptopSection } from "../components/LaptopSection";
import { downloadCsv } from "../utils/csv";
import type { ProductSummary, SortOrder } from "../types/api";

const PAGE_SIZE = 60;
const EXPORT_PAGE_SIZE = 500; // api/routers/prices.py의 limit 상한과 동일하게 유지할 것
const LAPTOP_CATEGORIES = ["게이밍 노트북", "AI 노트북"];

export function OverviewPage() {
  // 카테고리는 URL로 들고 다닌다 — 3D 데스크의 "전체 상품 보기" 링크가 이 파라미터로 들어온다
  const [searchParams, setSearchParams] = useSearchParams();
  const category = searchParams.get("category") ?? "";
  const setCategory = (next: string) =>
    setSearchParams(next ? { category: next } : {}, { replace: true });

  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortOrder>("price_asc");

  const [items, setItems] = useState<ProductSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: categoriesData, loading: categoriesLoading, error: categoriesError } = useFetch(
    () => getCategories(),
    [],
  );

  useEffect(() => {
    if (LAPTOP_CATEGORIES.includes(category)) return; // 노트북 카테고리는 LaptopSection이 별도로 로드한다
    let cancelled = false;
    setLoading(true);
    getPrices({ category: category || undefined, q: q || undefined, sort, limit: PAGE_SIZE, offset: 0 })
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setTotal(res.total);
        setError(null);
      })
      .catch((err: Error) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [category, q, sort]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const res = await getPrices({
        category: category || undefined,
        q: q || undefined,
        sort,
        limit: PAGE_SIZE,
        offset: items.length,
      });
      setItems((prev) => [...prev, ...res.items]);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleExportCsv = async () => {
    // API가 한 번에 500개까지만 내주므로 전체를 받으려면 나눠서 이어붙인다
    const all: ProductSummary[] = [];
    while (all.length < total) {
      const res = await getPrices({
        category: category || undefined,
        q: q || undefined,
        sort,
        limit: EXPORT_PAGE_SIZE,
        offset: all.length,
      });
      if (res.items.length === 0) break;
      all.push(...res.items);
    }
    downloadCsv(
      all,
      [
        { label: "상품명", get: (r) => r.product },
        { label: "카테고리", get: (r) => r.category },
        { label: "가격", get: (r) => r.price },
        { label: "수집일", get: (r) => r.date },
      ],
      `market_pulse_products${category ? `_${category}` : ""}.csv`,
    );
  };

  const stats: Stat[] = useMemo(() => {
    if (!categoriesData) return [];
    return [
      { icon: "📦", label: "상품", value: `${categoriesData.product_count}개` },
      { icon: "📂", label: "카테고리", value: `${categoriesData.categories.length}개` },
      {
        icon: "💰",
        label: "평균가",
        value: `${Math.round(categoriesData.avg_price).toLocaleString()}원`,
        color: "var(--mp-cyan)",
      },
      { icon: "📈", label: "인상", value: `${categoriesData.up_count}개`, color: "var(--mp-red)" },
      { icon: "📉", label: "인하", value: `${categoriesData.down_count}개`, color: "var(--mp-green)" },
      {
        icon: "⚠️",
        label: "이상치",
        value: `${categoriesData.anomaly_count}개`,
        color: "var(--mp-amber)",
        accent: categoriesData.anomaly_count > 0,
      },
    ];
  }, [categoriesData]);

  return (
    <>
      <AlertBanner />

      {categoriesError && <p role="alert">데이터를 불러오지 못했어요: {categoriesError}</p>}
      {!categoriesLoading && categoriesData && <StatCards stats={stats} />}

      {categoriesData && categoriesData.categories.length > 0 && (
        <section>
          <SectionHeader icon="📊" title="카테고리별 평균 가격" />
          <CategoryBarChart
            data={categoriesData.categories}
            valueKey="avg_price"
            valueLabel="평균가"
            formatValue={(v) => `${Math.round(v / 10000)}만원`}
          />
        </section>
      )}

      <SpotlightSection />

      <section>
        <SectionHeader icon="🔍" title="전체 상품" subtitle="카테고리·검색·정렬로 찾아보세요" />
        <CategoryTabs
          categories={categoriesData?.categories.map((c) => c.category) ?? []}
          active={category}
          onChange={setCategory}
        />
        {LAPTOP_CATEGORIES.includes(category) ? (
          <LaptopSection category={category} />
        ) : (
          <>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <SearchBar q={q} onQChange={setQ} sort={sort} onSortChange={setSort} />
              </div>
              {total > 0 && (
                <button
                  onClick={handleExportCsv}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 10,
                    border: "1px solid var(--mp-border)",
                    background: "var(--mp-surface)",
                    color: "var(--mp-text)",
                    fontSize: "0.85rem",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  ⬇️ CSV 내보내기 ({total}개)
                </button>
              )}
            </div>

            {error && <p role="alert">상품 목록을 불러오지 못했어요: {error}</p>}
            {loading && <p>불러오는 중...</p>}
            {!loading && items.length === 0 && <p>조건에 맞는 상품이 없어요.</p>}
            {items.length > 0 && (
              <>
                <p style={{ color: "var(--mp-muted)", fontSize: "0.82rem", marginTop: 12 }}>
                  {items.length} / {total}개 표시 중
                </p>
                <div
                  style={{
                    marginTop: 8,
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                    gap: 16,
                  }}
                >
                  {items.map((item) => (
                    <ProductCard key={`${item.code || "none"}-${item.product}-${item.date}`} product={item} />
                  ))}
                </div>
                {items.length < total && (
                  <div style={{ textAlign: "center", marginTop: 20 }}>
                    <button
                      onClick={loadMore}
                      disabled={loadingMore}
                      style={{
                        padding: "10px 24px",
                        borderRadius: 999,
                        border: "1px solid var(--mp-border)",
                        background: "var(--mp-surface)",
                        color: "var(--mp-text)",
                        fontSize: "0.85rem",
                        cursor: "pointer",
                      }}
                    >
                      {loadingMore ? "불러오는 중..." : `더보기 (${total - items.length}개 더)`}
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </section>
    </>
  );
}
