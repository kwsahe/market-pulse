import { useState } from "react";
import { getChanges } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import { StatCards, type Stat } from "../components/StatCard";
import { ChangeCard } from "../components/ChangeCard";
import styles from "./ChangesPage.module.css";

export function ChangesPage() {
  const [tab, setTab] = useState<"up" | "down">("up");
  const { data, loading, error } = useFetch(() => getChanges(), []);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">가격 변동 데이터를 불러오지 못했어요: {error}</p>;
  if (!data) return null;

  if (!data.has_changes) {
    return (
      <section>
        <SectionHeader icon="📊" title="가격 변동 리포트" />
        <p>📊 가격 변동은 2일 이상 데이터가 쌓이면 표시돼요. 내일 다시 스크래퍼를 실행해보세요!</p>
      </section>
    );
  }

  const stats: Stat[] = [
    { icon: "📈", label: "인상 상품", value: `${data.up.length}개`, color: "var(--mp-red)" },
    { icon: "📉", label: "인하 상품", value: `${data.down.length}개`, color: "var(--mp-green)" },
    { icon: "🔀", label: "총 변동", value: `${data.up.length + data.down.length}개` },
  ];

  const items = tab === "up" ? data.up : data.down;

  return (
    <section>
      <SectionHeader icon="📊" title="가격 변동 리포트" subtitle={`비교 기간: ${data.prev_date} → ${data.latest_date}`} />
      <StatCards stats={stats} />

      <div className={styles.tabs}>
        <button className={tab === "up" ? styles.tabActive : styles.tab} onClick={() => setTab("up")}>
          📈 가격 인상 ({data.up.length})
        </button>
        <button className={tab === "down" ? styles.tabActive : styles.tab} onClick={() => setTab("down")}>
          📉 가격 인하 ({data.down.length})
        </button>
      </div>

      {items.length === 0 ? (
        <p>{tab === "up" ? "가격 인상 상품 없음!" : "가격 인하 상품 없음!"}</p>
      ) : (
        <div className={styles.list}>
          {items.map((item, i) => (
            <ChangeCard key={`${item.code || item.product}-${i}`} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
