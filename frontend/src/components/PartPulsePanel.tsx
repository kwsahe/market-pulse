// frontend/src/components/PartPulsePanel.tsx
// 3D 데스크에서 선택한 부품(=카테고리) 하나의 가격 요약 패널.
// GET /api/categories/{category}/pulse 한 번으로 스냅샷 통계·추이·최저가/변동 TOP3를 모두 채운다.

import { Link } from "react-router-dom";
import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import { getCategoryPulse } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import type { PartDef } from "../three/parts";
import { partColor } from "../three/parts";
import type { CategoryPulseItem } from "../types/api";
import styles from "./PartPulsePanel.module.css";

function manwon(value: number): string {
  return `${(value / 10000).toLocaleString(undefined, { maximumFractionDigits: 1 })}만원`;
}

function ItemRow({ item, accent }: { item: CategoryPulseItem; accent: string }) {
  const body = (
    <>
      <span className={styles.itemName} title={item.product}>
        {item.product}
      </span>
      <span className={styles.itemPrice}>
        {item.price.toLocaleString()}원
        {item.change != null && item.change !== 0 && (
          <em className={item.change > 0 ? styles.up : styles.down}>
            {item.change > 0 ? "▲" : "▼"} {Math.abs(item.change_pct ?? 0).toFixed(1)}%
          </em>
        )}
      </span>
    </>
  );

  if (!item.code) return <li className={styles.item}>{body}</li>;
  return (
    <li className={styles.item} style={{ borderLeftColor: accent }}>
      <Link to={`/products/${encodeURIComponent(item.code)}`} className={styles.itemLink}>
        {body}
      </Link>
    </li>
  );
}

export function PartPulsePanel({
  part,
  collected,
}: {
  part: PartDef;
  /** 이 카테고리가 수집된 적 있는지. undefined면 아직 확인 전이라 요청을 보류한다. */
  collected?: boolean;
}) {
  const accent = partColor(part);
  // 한 번도 수집되지 않은 카테고리는 pulse가 404라, 수집 여부를 알기 전에는 요청하지 않는다
  // (섣불리 보내면 첫 로딩에 404 에러가 번쩍였다가 안내 문구로 바뀐다)
  const { data, loading, error } = useFetch(
    () => (collected ? getCategoryPulse(part.category) : Promise.resolve(null)),
    [part.category, collected],
  );

  return (
    <aside className={styles.panel} style={{ borderColor: `${accent}55` }}>
      <header className={styles.header}>
        <span className={styles.icon} style={{ background: `${accent}22`, color: accent }}>
          {part.icon}
        </span>
        <div>
          <h2 className={styles.title}>{part.label}</h2>
          <p className={styles.hint}>{part.hint}</p>
        </div>
      </header>

      {collected === undefined && <p className={styles.state}>불러오는 중...</p>}
      {collected === false && (
        <p className={styles.state}>
          아직 수집된 {part.label} 데이터가 없어요. <code>run_scrapers.bat</code>을 한 번 돌리면 이
          자리에 시세가 채워집니다.
        </p>
      )}
      {collected === true && loading && <p className={styles.state}>불러오는 중...</p>}
      {collected === true && error && (
        <p className={styles.state} role="alert">
          이 부품의 데이터를 불러오지 못했어요: {error}
        </p>
      )}

      {data && (
        <>
          <p className={styles.meta}>기준일 {data.latest_date}</p>

          <div className={styles.statGrid}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>상품</span>
              <strong className={styles.statValue}>{data.count.toLocaleString()}개</strong>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>평균가</span>
              <strong className={styles.statValue} style={{ color: accent }}>
                {manwon(data.avg_price)}
              </strong>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>최저가</span>
              <strong className={styles.statValue}>{manwon(data.min_price)}</strong>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>최고가</span>
              <strong className={styles.statValue}>{manwon(data.max_price)}</strong>
            </div>
          </div>

          <div className={styles.chips}>
            <span className={`${styles.chip} ${styles.up}`}>📈 인상 {data.up_count}</span>
            <span className={`${styles.chip} ${styles.down}`}>📉 인하 {data.down_count}</span>
            <span className={`${styles.chip} ${styles.warn}`}>⚠️ 이상치 {data.anomaly_count}</span>
          </div>

          {data.trend.length >= 2 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>
                평균가 추이
                {data.trend_pct != null && (
                  <em className={data.trend_pct >= 0 ? styles.up : styles.down}>
                    {data.trend_pct >= 0 ? "+" : ""}
                    {data.trend_pct.toFixed(1)}%
                  </em>
                )}
              </h3>
              <ResponsiveContainer width="100%" height={92}>
                <AreaChart data={data.trend} margin={{ top: 4, right: 2, left: 2, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`pulse-${part.id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={accent} stopOpacity={0.55} />
                      <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <YAxis hide domain={["dataMin", "dataMax"]} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--mp-surface-raised)",
                      border: "1px solid var(--mp-border)",
                      borderRadius: 10,
                      color: "var(--mp-text)",
                      fontSize: "0.78rem",
                    }}
                    labelFormatter={(label) => `${label}`}
                    formatter={(value) => [manwon(Number(value)), "평균가"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="avg_price"
                    stroke={accent}
                    strokeWidth={2}
                    fill={`url(#pulse-${part.id})`}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </section>
          )}

          {data.cheapest.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>최저가 TOP {data.cheapest.length}</h3>
              <ul className={styles.list}>
                {data.cheapest.map((item) => (
                  <ItemRow key={`cheap-${item.product}`} item={item} accent={accent} />
                ))}
              </ul>
            </section>
          )}

          {data.movers.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>변동 TOP {data.movers.length}</h3>
              <ul className={styles.list}>
                {data.movers.map((item) => (
                  <ItemRow key={`mover-${item.product}`} item={item} accent={accent} />
                ))}
              </ul>
            </section>
          )}

          <Link
            to={`/?category=${encodeURIComponent(part.category)}`}
            className={styles.cta}
            style={{ borderColor: `${accent}66`, color: accent }}
          >
            {part.label} 전체 상품 보기 →
          </Link>
        </>
      )}
    </aside>
  );
}
