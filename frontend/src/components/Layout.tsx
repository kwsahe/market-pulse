import { useEffect, useRef, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { getHealth } from "../api/client";
import { useFetch } from "../hooks/useFetch";
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

/** 데이터 신선도 배지.
 *
 * 예전에는 "실시간 수집 중"이 하드코딩돼 있어서, 수집이 며칠 멈춰도 화면은 똑같이 정상으로 보였다.
 * 이 프로젝트의 가장 그럴듯한 실패는 서버가 죽는 게 아니라 수집이 조용히 멈추는 것이고,
 * 알림을 놓쳤거나 PC가 꺼져 있었어도 화면을 여는 순간 눈에 들어오게 하는 게 가장 싸고 확실하다.
 */
function FreshnessPill() {
  const { data } = useFetch(() => getHealth(), []);

  if (!data) {
    return <span className={styles.livePill}>수집 상태 확인 중…</span>;
  }
  if (data.status === "error" || data.status === "empty") {
    return <span className={`${styles.livePill} ${styles.pillBad}`}>⚠️ 데이터를 읽을 수 없어요</span>;
  }

  const stale = data.days_stale ?? 0;
  const label = data.last_scrape_date ?? "-";
  if (data.status === "stale") {
    return (
      <span className={`${styles.livePill} ${styles.pillBad}`} title="수집 배치가 멈췄을 수 있어요">
        ⚠️ {label} 이후 수집 없음 ({stale}일째)
      </span>
    );
  }
  return (
    <span className={styles.livePill} title={`상품 ${data.rows.toLocaleString()}행 · 카테고리 ${data.categories}개`}>
      <span className={styles.liveDot} />
      {stale === 0 ? "오늘 수집됨" : `${label} 수집`}
    </span>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  // 모바일에선 메뉴가 가로로 스크롤된다 — 현재 페이지 항목이 화면 밖이면 가운데로 옮긴다.
  // scrollIntoView 는 뒤로가기 때 페이지까지 세로로 끌어올려서, 메뉴 영역의 가로 스크롤만 직접 조정한다.
  const navRef = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  useEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!nav || !active) return;
    const offset = active.getBoundingClientRect().left - nav.getBoundingClientRect().left;
    nav.scrollLeft += offset - (nav.clientWidth - active.offsetWidth) / 2;
  }, [pathname]);

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
          <FreshnessPill />
        </div>
      </header>
      <nav ref={navRef} className={styles.nav}>
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
