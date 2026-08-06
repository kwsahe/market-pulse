import { getScrapeRuns } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { SectionHeader } from "../components/SectionHeader";
import { StatCards, type Stat } from "../components/StatCard";
import styles from "./ScrapesPage.module.css";

export function ScrapesPage() {
  const { data, loading, error } = useFetch(() => getScrapeRuns(), []);

  if (loading) return <p>불러오는 중...</p>;
  if (error) return <p role="alert">수집 이력을 불러오지 못했어요: {error}</p>;
  if (!data) return null;

  if (data.runs.length === 0) {
    return <p>아직 수집 실행 기록이 없어요.</p>;
  }

  const summaryStats: Stat[] = [
    { icon: "🛰️", label: "전체 실행", value: `${data.summary.total}회` },
    { icon: "✅", label: "성공", value: `${data.summary.success}회`, color: "var(--mp-green)" },
    { icon: "❌", label: "실패", value: `${data.summary.failed}회`, color: "var(--mp-red)" },
    { icon: "⏳", label: "진행 중", value: `${data.summary.running}회`, color: "var(--mp-amber)" },
  ];

  return (
    <>
      <section>
        <SectionHeader icon="🛰️" title="수집 실행 이력" subtitle="가격/뉴스 스크래퍼가 언제, 얼마나 성공적으로 돌았는지 확인해요." />
        <div className={styles.latestGrid}>
          {data.latest_by_source.map((r) => (
            <div key={r.source} className={styles.latestCard}>
              <div className={styles.latestSource}>최근 {r.source} 수집</div>
              <div className={r.status === "failed" ? styles.statusFailed : styles.statusOk}>{r.status}</div>
              <div className={styles.latestMeta}>
                {r.started_at} · 수집 {r.fetched_count}개 · 신규 {r.inserted_count}개
              </div>
              {r.status === "failed" && r.error_message && (
                <div className={styles.errorMsg}>❌ {r.error_message}</div>
              )}
            </div>
          ))}
        </div>
      </section>

      <StatCards stats={summaryStats} />

      <section>
        <SectionHeader icon="📜" title="최근 실행 목록" />
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>#</th>
                <th>소스</th>
                <th>시작</th>
                <th>종료</th>
                <th>수집</th>
                <th>신규</th>
                <th>상태</th>
                <th>에러</th>
              </tr>
            </thead>
            <tbody>
              {data.runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.source}</td>
                  <td>{r.started_at}</td>
                  <td>{r.finished_at ?? "-"}</td>
                  <td>{r.fetched_count}</td>
                  <td>{r.inserted_count}</td>
                  <td className={r.status === "failed" ? styles.statusFailed : undefined}>{r.status}</td>
                  <td>{r.error_message ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
