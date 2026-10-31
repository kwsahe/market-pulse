from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT_PATH = Path("screenshots/architecture_flow.png")


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/NanumGothicBold.ttf" if bold else "C:/Windows/Fonts/NanumGothic.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


F_TITLE = font(46, True)
F_SUBTITLE = font(23)
F_SECTION = font(24, True)
F_BOX = font(22, True)
F_SMALL = font(17)
F_TINY = font(15)

BG = "#f6f8fb"
INK = "#182033"
MUTED = "#687287"
BORDER = "#b9c3d4"
WHITE = "#ffffff"
BLUE = "#2563eb"
GREEN = "#059669"
PURPLE = "#7c3aed"
AMBER = "#d97706"
RED = "#dc2626"
CYAN = "#0891b2"
SLATE = "#334155"


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_line(draw, text, fnt, max_width):
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if text_size(draw, trial, fnt)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_centered(draw, box, lines, fnt, fill=INK, line_gap=6):
    x1, y1, x2, y2 = box
    rendered = []
    for line in lines:
        rendered.extend(str(line).split("\n"))
    heights = [text_size(draw, line, fnt)[1] for line in rendered]
    total_h = sum(heights) + line_gap * (len(rendered) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, h in zip(rendered, heights):
        w, _ = text_size(draw, line, fnt)
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=fnt, fill=fill)
        y += h + line_gap


def rounded(draw, box, fill, outline=BORDER, width=2, radius=22):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def shadow(draw, box, radius=22):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 7, y1 + 8, x2 + 7, y2 + 8), radius=radius, fill="#d8deeaaa")


def section(draw, box, title, color):
    shadow(draw, box, 26)
    rounded(draw, box, WHITE, "#d1d9e6", 2, 26)
    x1, y1, x2, _ = box
    draw.rounded_rectangle((x1, y1, x2, y1 + 48), radius=26, fill=color)
    draw.rectangle((x1, y1 + 24, x2, y1 + 48), fill=color)
    draw.text((x1 + 22, y1 + 11), title, font=F_SECTION, fill=WHITE)


def box(draw, xy, label, color, w=260, h=98):
    """label[0]은 제목(F_BOX, 필요하면 문자열에 \\n으로 수동 줄바꿈),
    label[1:]는 본문(F_SMALL, 폭을 넘으면 자동 줄바꿈) — 상자보다 텍스트가 길어 밖으로
    삐져나오는 걸 막기 위해 폰트를 분리하고 자동 줄바꿈을 적용한다."""
    x, y = xy
    shadow(draw, (x, y, x + w, y + h), 18)
    rounded(draw, (x, y, x + w, y + h), "#ffffff", color, 3, 18)
    draw.rectangle((x, y, x + 8, y + h), fill=color)

    avail_w = w - 34
    rendered = [(t, F_BOX) for t in str(label[0]).split("\n")]
    for raw in label[1:]:
        rendered.extend((t, F_SMALL) for t in wrap_line(draw, raw, F_SMALL, avail_w))

    heights = [text_size(draw, t, f)[1] for t, f in rendered]
    total_h = sum(heights) + 6 * (len(rendered) - 1)
    yy = y + max(6, (h - total_h) / 2)
    for (t, f), hh in zip(rendered, heights):
        tw, _ = text_size(draw, t, f)
        draw.text((x + 16 + max(0, avail_w - tw) / 2, yy), t, font=f, fill=INK)
        yy += hh + 6
    return (x, y, x + w, y + h)


def small_box(draw, xy, title, body, color, w=385, h=154):
    x, y = xy
    shadow(draw, (x, y, x + w, y + h), 18)
    rounded(draw, (x, y, x + w, y + h), WHITE, "#d2dbea", 2, 18)
    draw.rounded_rectangle((x + 14, y + 14, x + 56, y + 56), radius=12, fill=color)
    draw.text((x + 70, y + 17), title, font=F_BOX, fill=INK)
    lines = []
    for raw in body:
        lines.extend(wrap_line(draw, raw, F_SMALL, w - 46))
    yy = y + 68
    for line in lines[:3]:
        draw.text((x + 24, yy), line, font=F_SMALL, fill=MUTED)
        yy += 24


def arrow(draw, start, end, color=SLATE, width=4):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    dx = x2 - x1
    dy = y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 13
    p1 = (x2, y2)
    p2 = (x2 - ux * size + px * size * 0.55, y2 - uy * size + py * size * 0.55)
    p3 = (x2 - ux * size - px * size * 0.55, y2 - uy * size - py * size * 0.55)
    draw.polygon([p1, p2, p3], fill=color)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (2000, 1560), BG)
    draw = ImageDraw.Draw(img)

    draw.text((70, 44), "Market Pulse 구성도 및 데이터 흐름", font=F_TITLE, fill=INK)
    draw.text(
        (74, 104),
        "다나와 검색(옛/새 화면) -> 품질 필터 -> SQLite(WAL) -> 분석/ML -> FastAPI + React(한 주소) · 매일 무인 수집·백업·검증",
        font=F_SUBTITLE,
        fill=MUTED,
    )

    # ---------- 1행: 데이터 흐름 5단 ----------
    section(draw, (70, 165, 340, 700), "외부 데이터", BLUE)
    section(draw, (410, 165, 720, 700), "수집 계층", GREEN)
    section(draw, (790, 165, 1095, 700), "저장 계층", AMBER)
    section(draw, (1165, 165, 1500, 700), "분석 / ML", PURPLE)
    section(draw, (1545, 165, 1930, 700), "표현", CYAN)

    def stack(x, y0, w, gap, items):
        """(라벨, 색상, 높이) 목록을 세로로 겹치지 않게 쌓아서 bbox 리스트를 반환"""
        boxes = []
        y = y0
        for label, color, h in items:
            bb = box(draw, (x, y), label, color, w, h)
            boxes.append(bb)
            y = bb[3] + gap
        return boxes

    def mid_y(bb):
        return (bb[1] + bb[3]) / 2

    b_old_ui, b_new_ui, b_sched = stack(105, 235, 200, 18, [
        (["다나와 검색", "옛 화면 (HTML)"], BLUE, 92),
        (["다나와 검색", "새 화면 (JSON)"], BLUE, 92),
        (["작업 스케줄러", "매일 09:10 · 창 없이"], BLUE, 92),
    ])

    b_price, b_filter, b_batch = stack(445, 220, 240, 18, [
        (["price_scraper.py", "두 화면 → 같은 상품 목록 (10초 간격)"], GREEN, 100),
        (["품질 필터", "미끼가 · 비정상가 · 카테고리 오염 · 중고"], GREEN, 100),
        (["run_scrapers.bat", "수집 → 변동 → 백업 → 검증, 실패 알림"], GREEN, 100),
    ])

    b_dbm, b_sql, b_backup = stack(825, 220, 230, 22, [
        (["db_manager.py", "상품번호 규칙 match_key_for"], AMBER, 100),
        (["SQLite (WAL)", "9개 테이블 · 5.3만 행"], AMBER, 92),
        (["백업", "VACUUM INTO → OneDrive 7세대"], AMBER, 100),
    ])

    b_change, b_anom, b_pred, b_score, b_verify = stack(1200, 205, 260, 16, [
        (["가격 변동", "직전 수집일 대비 인상/인하"], PURPLE, 70),
        (["이상치 탐지", "Z-score / IQR"], PURPLE, 70),
        (["가격 예측", "LR/RF + GroupKFold"], PURPLE, 70),
        (["적정가 점수", "예측가 + 역대 최저가 근접도"], PURPLE, 70),
        (["수집 결과 검증", "40% 급감·소실 시 실패"], PURPLE, 70),
    ])

    b_api, b_react, b_extra = stack(1580, 205, 300, 20, [
        (["FastAPI", "REST API 17개 · 한 주소(8002) · 읽기 전용"], CYAN, 110),
        (["React SPA", "10개 화면 + Three.js 3D 데스크"], CYAN, 110),
        (["보조", "Streamlit 대시보드 · LangGraph 리포트"], CYAN, 92),
    ])

    arrow(draw, (b_old_ui[2], mid_y(b_old_ui)), (b_price[0], mid_y(b_price) - 12), BLUE)
    arrow(draw, (b_new_ui[2], mid_y(b_new_ui)), (b_price[0], mid_y(b_price) + 12), BLUE)
    arrow(draw, (b_sched[2], mid_y(b_sched)), (b_batch[0], mid_y(b_batch)), BLUE)
    arrow(draw, (565, b_price[3]), (565, b_filter[1]), GREEN)
    arrow(draw, (b_filter[2], mid_y(b_filter)), (b_dbm[0], mid_y(b_dbm)), GREEN)
    arrow(draw, (940, b_dbm[3]), (940, b_sql[1]), AMBER)
    arrow(draw, (940, b_sql[3]), (940, b_backup[1]), AMBER)
    arrow(draw, (b_sql[2], mid_y(b_sql)), (b_change[0], (b_change[1] + b_verify[3]) / 2), PURPLE, 3)
    arrow(draw, (b_change[2], mid_y(b_change)), (b_api[0], mid_y(b_api) - 20), CYAN, 3)
    arrow(draw, (b_pred[2], mid_y(b_pred)), (b_api[0], mid_y(b_api) + 20), CYAN, 3)
    arrow(draw, ((b_api[0] + b_api[2]) / 2, b_api[3]), ((b_react[0] + b_react[2]) / 2, b_react[1]), CYAN, 3)

    # ---------- 2행: ML 활용 상세 ----------
    row_x = [70, 562, 1054, 1546]
    draw.text((70, 730), "ML 활용 상세", font=F_TITLE, fill=INK)
    small_box(
        draw, (row_x[0], 800), "1. 이상치 탐지",
        ["카테고리별 최신 가격 분포에서 비정상 가격 감지", "Z-score threshold 2.5, IQR 1.5배 기준"],
        RED,
    )
    small_box(
        draw, (row_x[1], 800), "2. 가격 예측",
        ["상품명·스펙에서 특성 추출, LR vs RF 비교", "GroupKFold로 같은 상품 학습/검증 분리"],
        PURPLE,
    )
    small_box(
        draw, (row_x[2], 800), "3. 적정가 점수 (0~100)",
        ["예측가 대비 저렴함 + 과거 최저가 근접도", "고가 이상치면 감점 (규칙 기반 조합)"],
        AMBER,
    )
    small_box(
        draw, (row_x[3], 800), "4. 가격 변동",
        ["상품번호 기준 매칭이라 상품명 표기가 바뀌어도 이어짐", "카테고리 비교는 평균 대신 중앙값 (이상가에 덜 흔들림)"],
        GREEN,
    )

    # ---------- 3행: 운영 & 품질 ----------
    draw.text((70, 960), "운영 & 품질", font=F_TITLE, fill=INK)
    small_box(
        draw, (row_x[0], 1030), "무인 수집",
        ["매일 09:10 (꺼져 있었으면 켜질 때)", "수집률 17.1% → 82.7%"],
        BLUE,
    )
    small_box(
        draw, (row_x[1], 1030), "데이터 품질 필터",
        ["미끼가: 다른 용량 단가의 5% 미만", "비정상가: 중앙값 100배·1/100 밖"],
        GREEN,
    )
    small_box(
        draw, (row_x[2], 1030), "테스트 & CI",
        ["pytest 167개 + vitest 22개", "GitHub Actions로 push마다 두 스위트 자동 실행"],
        SLATE,
    )
    small_box(
        draw, (row_x[3], 1030), "robots.txt 준수",
        ["검색 10초 간격, 금지 경로는 꺼둠", "뉴스(전면 금지)는 수집 중단"],
        CYAN,
    )

    # ---------- 4행: DB 구조 요약 (3x3) ----------
    section(draw, (70, 1190, 1930, 1500), "DB 구조 요약 (9개 테이블)", SLATE)
    db_tables = [
        ("prices", "date, category, product, price, pcode, specs, image_url"),
        ("news", "collected_at, press, title (2026-09-10 이후 수집 중단)"),
        ("product_registry", "internal_code(RAM-1 등), match_key(노트북=pcode, 부품=pcode+옵션)"),
        ("laptop_products", "pcode, name, gpu_model, first_seen"),
        ("laptop_specs", "pcode, spec_key, spec_value"),
        ("laptop_images", "pcode, image_url, image_type(main/detail)"),
        ("tracked_laptops", "pcode, target_price, memo"),
        ("scrape_runs", "source, status, fetched/inserted_count"),
        ("schema_migrations", "적용된 마이그레이션 이력"),
    ]
    col_w = (1930 - 70) / 3
    row_h = 90
    for i, (name, desc) in enumerate(db_tables):
        col, row = i % 3, i // 3
        x = 70 + 40 + col * col_w
        y = 1190 + 58 + row * row_h
        draw.text((x, y), name, font=F_BOX, fill=INK)
        for j, line in enumerate(wrap_line(draw, desc, F_TINY, col_w - 70)):
            draw.text((x, y + 30 + j * 20), line, font=F_TINY, fill=MUTED)

    img.save(OUT_PATH)
    print(f"saved: {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
