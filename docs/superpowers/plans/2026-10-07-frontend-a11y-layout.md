# 프론트 접근성(3번) · 화면 구성(4번) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hallmark 감사(2026-10-07)의 3번(접근성)·4번(화면 구성) 묶음을 반영한다.

**Architecture:** 전역 규칙(포커스 링·움직임 줄이기·빨강 토큰)은 `theme.css` 한 곳에 둔다. 개요 화면의 자동 슬라이드 2개는 카드 그리드로, 평균가 막대 차트는 기존 `/api/categories/{c}/pulse`를 쓰는 카테고리 변동 표로 바꾼다. 메뉴는 줄바꿈 대신 가로 스크롤 한 줄로 만든다. 백엔드 변경 없음.

**Tech Stack:** React 19 + CSS Modules + recharts + @react-three/fiber, vitest(node 환경, DOM 없음).

**Spec:** 이 세션의 hallmark 감사 결과표(심각 6 · 중요 14 · 사소 3) 중 3·4번 묶음 항목.

## Global Constraints

- 새 의존성 추가 금지 (테스트 라이브러리 포함 — 컴포넌트 테스트 대신 순수 함수만 vitest로 검증)
- 색은 토큰으로: `--mp-red`는 `#ef5f5f` (surface `#171a21` 대비 5.37:1), `dashboard/theme.py`의 `RED`도 같은 값으로 (theme.css 상단 주석의 동기화 규칙)
- 포커스 링: 2px, `var(--mp-cyan)` (배경 대비 10.6:1), `outline-offset: 2px`
- 같은 우선순위 CSS는 뒤에 오는 규칙이 이긴다 — 미디어쿼리 오버라이드는 기본 규칙보다 뒤에 둘 것
- 커밋은 사용자가 요청할 때만

## Review Focus

1. 카테고리 9개 중 하나의 pulse 요청만 실패 → 표 전체가 사라지지 않고 그 줄만 "—" (Task 4 테스트로 고정)
2. 인상·인하가 0인 카테고리 → "0"을 흐리게 표시, 빈칸이나 NaN 금지 (Task 4 테스트로 고정)
3. 320px 화면 → 메뉴는 자기 영역 안에서만 가로 스크롤, 페이지 가로 스크롤 없음 (Task 5 브라우저 확인)
4. 모바일에서 마지막 메뉴(뉴스)에 있을 때 → 현재 항목이 보이는 위치로 메뉴가 옮겨지고, 페이지는 세로로 튀지 않음 (Task 5 브라우저 확인)
5. 키보드 사용자 → 검색창을 포함한 모든 링크·버튼에 2px 링 (Task 1 브라우저 확인)

---

### Task 1: 전역 접근성 규칙 + 배지 대비

**Files:**
- Modify: `frontend/src/theme.css` (`--mp-red`, `:focus-visible`, 움직임 줄이기 미디어쿼리)
- Modify: `dashboard/theme.py:34` (`RED`)
- Modify: `frontend/src/components/SearchBar.module.css:29` (`outline: none` 삭제)
- Modify: `frontend/src/components/CategoryBadge.tsx` (글씨색)

- [ ] **Step 1: theme.css**

```css
  --mp-red: #ef5f5f; /* #d03b3b 은 작은 글씨에서 3.6:1 이라 미달 → 5.4:1 */
```

```css
/* 키보드 이동 위치 표시. 브라우저 기본 링은 어두운 배경에서 약하고 페이지마다 달랐다. */
:focus-visible {
  outline: 2px solid var(--mp-cyan);
  outline-offset: 2px;
}

/* 움직임 줄이기 설정을 켠 사용자: 깜빡이는 상태 점 같은 반복 애니메이션까지 멈춘다 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Step 2: theme.py** — `RED = "#EF5F5F"`
- [ ] **Step 3: SearchBar** — `.input:focus, .select:focus`에서 `outline: none;` 줄만 삭제 (테두리 색 변화는 유지, 전역 링이 함께 보임)
- [ ] **Step 4: CategoryBadge** — `color` 를 `"var(--mp-text)"`로. 배경 틴트·테두리는 카테고리 색 유지 (키보드·모니터·마우스 색은 글씨로 2.8:1)
- [ ] **Step 5: 확인** — `npx tsc -b` exit 0, 브라우저에서 Tab 키로 이동 시 검색창·링크에 링, 배지 글씨 계산색 `rgb(243, 244, 246)`

### Task 2: 자바스크립트 애니메이션의 움직임 줄이기

**Files:**
- Modify: `frontend/src/constants.ts` (상수 추가)
- Modify: `frontend/src/components/PriceHistoryChart.tsx:34` (`<Line>`)
- Modify: `frontend/src/components/PartPulsePanel.tsx:149` (`<Area>`)
- Modify: `frontend/src/three/DeskScene.tsx:108` (카메라 보간)

**Interfaces:**
- Produces: `export const REDUCED_MOTION: boolean` (constants.ts)

- [ ] **Step 1: constants.ts**

```ts
// 움직임 줄이기 설정. 페이지를 연 시점 값만 본다 — 설정을 바꾸면 새로고침해야 반영된다.
// (vitest 는 node 환경이라 window 가 없다)
export const REDUCED_MOTION =
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
```

- [ ] **Step 2: 차트 2곳** — `<Line ... isAnimationActive={!REDUCED_MOTION} />`, `<Area ... isAnimationActive={!REDUCED_MOTION} ...>`
- [ ] **Step 3: DeskScene** — `const t = REDUCED_MOTION ? 1 : 1 - Math.pow(0.0015, delta);` (켜져 있으면 한 프레임에 목표 위치로)
- [ ] **Step 4: 확인** — `npx tsc -b`, `npm test` (constants 테스트 통과 = node 환경에서 상수가 false)

### Task 3: 자동 슬라이드 → 카드 그리드

**Files:**
- Modify: `frontend/src/components/SpotlightSection.tsx`
- Modify: `frontend/src/components/SpotlightCard.module.css` (`.grid` 추가)
- Delete: `frontend/src/components/Carousel.tsx`, `frontend/src/components/Carousel.module.css`

- [ ] **Step 1: SpotlightCard.module.css 끝에**

```css
/* 자동 슬라이드 대신 한 번에 다 보여준다 — 순위 비교가 목적이라 한 장씩 넘기면 안 된다 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr));
  gap: 14px;
}
```

- [ ] **Step 2: SpotlightSection** — `<Carousel slides={x} />` 두 곳을 `<div className={cardStyles.grid}>{x}</div>`로, `Carousel` import 삭제, 변수명 `moverCards`/`notableCards`, 부제 "가격이 가장 많이 움직인 순서예요" / "이상치·신제품이에요"
- [ ] **Step 3: Carousel 파일 2개 삭제** (사용처가 SpotlightSection 뿐임을 grep으로 확인한 뒤)
- [ ] **Step 4: 확인** — `npx tsc -b`, 개요에서 변동 TOP 8장·주목 5장이 동시에 보임, `setInterval` 0건

### Task 4: 평균가 막대 차트 → 카테고리 변동 표

**Files:**
- Create: `frontend/src/utils/categoryPulse.ts`
- Create: `frontend/src/utils/categoryPulse.test.ts`
- Create: `frontend/src/components/CategoryPulseTable.tsx`
- Create: `frontend/src/components/CategoryPulseTable.module.css`
- Modify: `frontend/src/pages/OverviewPage.tsx:132-142` (섹션 교체)
- Delete: `frontend/src/components/CategoryBarChart.tsx`

**Interfaces:**
- Consumes: `getCategoryPulse(category: string): Promise<CategoryPulseResponse>` (기존 client.ts)
- Produces: `toPulseRows(categories: string[], results: PromiseSettledResult<CategoryPulseResponse>[]): PulseRow[]`,
  `interface PulseRow { category: string; median: number | null; up: number | null; down: number | null }`,
  `CategoryPulseTable({ categories }: { categories: string[] })`

- [ ] **Step 1: 실패하는 테스트**

```ts
import { describe, expect, it } from "vitest";
import { toPulseRows } from "./categoryPulse";
import type { CategoryPulseResponse } from "../types/api";

const pulse = (category: string, median: number, up: number, down: number) =>
  ({ category, median_price: median, up_count: up, down_count: down }) as CategoryPulseResponse;

describe("toPulseRows", () => {
  it("keeps request order and maps median/up/down", () => {
    const rows = toPulseRows(["CPU", "그래픽카드"], [
      { status: "fulfilled", value: pulse("CPU", 349730, 5, 36) },
      { status: "fulfilled", value: pulse("그래픽카드", 1500000, 0, 0) },
    ]);
    expect(rows).toEqual([
      { category: "CPU", median: 349730, up: 5, down: 36 },
      { category: "그래픽카드", median: 1500000, up: 0, down: 0 },
    ]);
  });

  it("blanks only the row whose request failed", () => {
    const rows = toPulseRows(["CPU", "게이밍 마우스"], [
      { status: "rejected", reason: new Error("500") },
      { status: "fulfilled", value: pulse("게이밍 마우스", 45000, 2, 1) },
    ]);
    expect(rows[0]).toEqual({ category: "CPU", median: null, up: null, down: null });
    expect(rows[1].median).toBe(45000);
  });
});
```

- [ ] **Step 2: 실행해서 실패 확인** — `npm test -- categoryPulse` → FAIL (모듈 없음)
- [ ] **Step 3: 최소 구현**

```ts
import type { CategoryPulseResponse } from "../types/api";

export interface PulseRow {
  category: string;
  median: number | null;
  up: number | null;
  down: number | null;
}

/** 카테고리별 pulse 응답을 표 한 줄씩으로 만든다.
 *  요청 하나가 실패해도 표 전체를 비우지 않고 그 줄만 비운다(null → 화면에선 "—"). */
export function toPulseRows(
  categories: string[],
  results: PromiseSettledResult<CategoryPulseResponse>[],
): PulseRow[] {
  return categories.map((category, i) => {
    const r = results[i];
    if (r?.status !== "fulfilled") return { category, median: null, up: null, down: null };
    return { category, median: r.value.median_price, up: r.value.up_count, down: r.value.down_count };
  });
}
```

- [ ] **Step 4: 테스트 통과 확인** — `npm test -- categoryPulse` → PASS
- [ ] **Step 5: 컴포넌트** — `Promise.allSettled`로 9개를 병렬 조회해 `toPulseRows`에 넘기고 `<table>`(머리글 `scope="col"`, 카테고리 칸 `scope="row"`)로 그린다. 중앙값을 쓰는 이유: 평균은 4.4억짜리 이상 가격 한 건에 마우스 평균이 708만원으로 왜곡된다. 0은 흐리게, null 은 "—". 표는 `max-width: 720px`, 바깥 `overflow-x: auto`.
- [ ] **Step 6: OverviewPage** — 막대 차트 섹션을 `<SectionHeader icon="📊" title="카테고리별 가격 변동" subtitle="중앙값과, 직전 수집일보다 오른·내린 상품 수예요" />` + `<CategoryPulseTable categories={...map((c) => c.category)} />`로 교체, `CategoryBarChart` import 삭제 후 파일 삭제
- [ ] **Step 7: 확인** — `npx tsc -b`, `npm test`, 브라우저에서 표 9줄·중앙값·▲▼ 표시

### Task 5: 모바일 메뉴 한 줄 + 머리글 축소

**Files:**
- Modify: `frontend/src/components/Layout.module.css` (`.nav`, `.navLink`, 파일 끝에 미디어쿼리)
- Modify: `frontend/src/components/Layout.tsx` (현재 항목 가로 위치 맞춤)

- [ ] **Step 1: CSS** — `.nav`: `flex-wrap: nowrap; overflow-x: auto; scrollbar-width: thin;` / `.navLink`: `white-space: nowrap;` (줄이 좁아지면 "가격 변동"이 알약 안에서 두 줄로 꺾이는 것 방지) / 파일 끝:

```css
/* 기본 규칙보다 뒤에 있어야 이긴다 */
@media (max-width: 560px) {
  .hero { margin-bottom: 20px; }
  .logo { width: 40px; height: 40px; border-radius: 11px; }
  .title { font-size: 1.5rem; }
  .subtitle { display: none; } /* 소개 문구는 부가 정보 — 좁은 화면에선 데이터를 먼저 */
}
```

- [ ] **Step 2: Layout.tsx** — 경로가 바뀔 때 메뉴 영역의 가로 스크롤만 조정 (`scrollIntoView`는 뒤로가기 때 페이지를 세로로 끌어올려서 쓰지 않는다)

```tsx
const navRef = useRef<HTMLElement>(null);
const { pathname } = useLocation();
useEffect(() => {
  const nav = navRef.current;
  const active = nav?.querySelector<HTMLElement>('[aria-current="page"]');
  if (!nav || !active) return;
  const offset = active.getBoundingClientRect().left - nav.getBoundingClientRect().left;
  nav.scrollLeft += offset - (nav.clientWidth - active.offsetWidth) / 2;
}, [pathname]);
```

- [ ] **Step 3: 확인** — 320·375·1440에서 페이지 가로 스크롤 없음, 메뉴 1줄, `/news`에서 "뉴스" 항목이 메뉴 영역 안에 보임, 1440에선 메뉴가 스크롤되지 않음

### 마무리 검증

- [ ] `npx tsc -b` exit 0 · `npm test` 전부 통과 · `npm run build` exit 0 · `pytest` 전부 통과 (theme.py 변경)
- [ ] 브라우저: 콘솔 에러 0, 위 Review Focus 1~5
- [ ] hallmark 재감사: 변경 범위에서 새 안티패턴 없음
