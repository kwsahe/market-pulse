import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import styles from "./Layout.module.css";

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/", label: "개요" },
  { to: "/desk", label: "3D 데스크" },
  { to: "/changes", label: "가격 변동" },
  { to: "/compare", label: "비교" },
  { to: "/prediction", label: "예측" },
  { to: "/anomalies", label: "이상치" },
  { to: "/watchlist", label: "워치리스트" },
  { to: "/scrapes", label: "수집이력" },
  { to: "/news", label: "뉴스" },
];

export function Layout({ children }: { children: ReactNode }) {
  // toISOString()은 UTC라 KST 새벽에 하루 전 날짜가 찍힌다 — 요일(getDay)과도 어긋나므로 로컬 기준으로 만든다
  const today = new Date();
  const weekdayKr = ["일", "월", "화", "수", "목", "금", "토"][today.getDay()];
  const pad = (n: number) => String(n).padStart(2, "0");
  const dateLabel = `${today.getFullYear()}.${pad(today.getMonth() + 1)}.${pad(today.getDate())} (${weekdayKr})`;

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <Link to="/" className={styles.titleRow}>
          <img src="/logo_mark.png" alt="Market Pulse 로고" className={styles.logo} />
          <h1 className={styles.title}>Market Pulse</h1>
        </Link>
        <p className={styles.subtitle}>
          RTX5080 / RTX5090 게이밍 노트북 & PC 부품 가격 추적 · ML 분석 · IT 뉴스 대시보드
        </p>
        <div className={styles.metaRow}>
          <span className={styles.datePill}>📅 {dateLabel}</span>
          <span className={styles.livePill}>
            <span className={styles.liveDot} />
            실시간 수집 중
          </span>
        </div>
      </header>
      <nav className={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className={styles.content}>{children}</main>
    </div>
  );
}
