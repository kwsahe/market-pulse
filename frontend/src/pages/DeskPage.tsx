// frontend/src/pages/DeskPage.tsx
// 3D 데스크 화면. 왼쪽은 조작 가능한 3D 씬, 오른쪽은 선택한 부품의 가격 요약 패널.
// three.js 번들이 초기 로딩에 끼지 않도록 씬은 lazy import 한다.
// 3D를 못 쓰는 상황(WebGL 미지원/모바일)에서도 부품 칩만으로 같은 데이터를 볼 수 있게 했다.

import { Suspense, lazy, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { getCategories } from "../api/client";
import { useFetch } from "../hooks/useFetch";
import { PartPulsePanel } from "../components/PartPulsePanel";
import { SectionHeader } from "../components/SectionHeader";
import { PARTS, findPart, partColor } from "../three/parts";
import styles from "./DeskPage.module.css";

const DeskScene = lazy(() => import("../three/DeskScene"));

export function DeskPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("part");
  const selectedPart = findPart(selectedId);

  const { data: categoriesData } = useFetch(() => getCategories(), []);

  const availableCategories = useMemo(
    () => new Set((categoriesData?.categories ?? []).map((c) => c.category)),
    [categoriesData],
  );

  const summaries = useMemo(() => {
    const byCategory = new Map((categoriesData?.categories ?? []).map((c) => [c.category, c]));
    return Object.fromEntries(
      PARTS.map((part) => {
        const stat = byCategory.get(part.category);
        if (!stat) return [part.id, "데이터 없음"];
        return [
          part.id,
          `평균 ${(stat.avg_price / 10000).toFixed(1)}만원 · ${stat.count}개`,
        ];
      }),
    );
  }, [categoriesData]);

  const select = (id: string | null) => {
    // 히스토리를 더럽히지 않도록 부품 이동은 replace로 — 뒤로가기는 대시보드로 나가는 용도로 남긴다
    setSearchParams(id ? { part: id } : {}, { replace: true });
  };

  return (
    <>
      <SectionHeader
        icon="🖥️"
        title="3D 데스크"
        subtitle="부품을 클릭하면 카메라가 이동하고 해당 카테고리 시세가 열려요"
      />

      <div className={styles.chipRow}>
        <button
          type="button"
          onClick={() => select(null)}
          className={`${styles.chip} ${!selectedPart ? styles.chipActive : ""}`}
        >
          🏠 전체 보기
        </button>
        {PARTS.map((part) => {
          const active = selectedId === part.id;
          const accent = partColor(part);
          return (
            <button
              key={part.id}
              type="button"
              onClick={() => select(part.id)}
              className={`${styles.chip} ${active ? styles.chipActive : ""}`}
              style={active ? { borderColor: accent, color: accent } : undefined}
              aria-pressed={active}
            >
              {part.icon} {part.label}
              {!availableCategories.has(part.category) && categoriesData && (
                <span className={styles.chipEmpty}>·수집 전</span>
              )}
            </button>
          );
        })}
      </div>

      <div className={styles.layout}>
        <div className={styles.stage}>
          <Suspense fallback={<div className={styles.sceneFallback}>3D 씬 불러오는 중...</div>}>
            <DeskScene
              selectedId={selectedId}
              onSelect={select}
              summaries={summaries}
              availableCategories={availableCategories}
            />
          </Suspense>
          <p className={styles.controlsHint}>드래그: 회전 · 휠: 확대/축소 · 부품 클릭: 방문</p>
        </div>

        {selectedPart ? (
          <PartPulsePanel
            part={selectedPart}
            // 카테고리 목록을 받기 전에는 undefined — 패널이 요청을 보류하고 로딩만 띄운다
            collected={categoriesData ? availableCategories.has(selectedPart.category) : undefined}
          />
        ) : (
          <aside className={styles.empty}>
            <h2 className={styles.emptyTitle}>부품을 골라보세요</h2>
            <p className={styles.emptyText}>
              케이스 안의 CPU·그래픽카드·RAM·SSD, 그리고 책상 위 노트북 2종과 게이밍 모니터가 각각
              하나의 가격 카테고리예요. 부품을 클릭하면 그 카테고리의 오늘 시세와 최근 추이가 여기에
              열립니다.
            </p>
            <ul className={styles.emptyList}>
              {PARTS.map((part) => (
                <li key={part.id}>
                  <button type="button" onClick={() => select(part.id)} className={styles.emptyItem}>
                    <span style={{ color: partColor(part) }}>{part.icon}</span>
                    <span className={styles.emptyItemLabel}>{part.label}</span>
                    <span className={styles.emptyItemHint}>{summaries[part.id]}</span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        )}
      </div>
    </>
  );
}

export default DeskPage;
