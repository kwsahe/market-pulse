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
        "Danawa/Naver 수집 -> SQLite 저장 -> ML 분석 -> Streamlit / FastAPI+React(병행), LangGraph 자동화 + pytest/CI",
        font=F_SUBTITLE,
        fill=MUTED,
    )

    # ---------- 1행: 데이터 흐름 5단 ----------
    section(draw, (70, 165, 340, 700), "외부 데이터", BLUE)
    section(draw, (410, 165, 720, 700), "수집 계층", GREEN)
    section(draw, (790, 165, 1095, 700), "저장 계층", AMBER)
    section(draw, (1165, 165, 1500, 700), "분석 / ML", PURPLE)
    section(draw, (1545, 165, 1930, 700), "표현 (병행 운영)", CYAN)

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

    b_danawa, b_naver = stack(105, 255, 200, 18, [
        (["Danawa", "제품/가격/스펙"], BLUE, 92),
        (["Naver News", "IT/과학 뉴스"], BLUE, 92),
    ])

    b_price, b_detail, b_news, b_batch = stack(445, 220, 240, 16, [
        (["price_scraper.py", "부품4종+노트북 목록"], GREEN, 70),
        (["laptop_detail_\nscraper.py", "노트북 상세스펙/이미지"], GREEN, 92),
        (["news_scraper.py", "뉴스 제목/언론사"], GREEN, 70),
        (["run_scrapers.bat", "수집 자동화 + 실행이력 기록"], GREEN, 70),
    ])

    b_dbm, b_sql, b_tables = stack(825, 220, 230, 22, [
        (["db_manager.py", "init/insert/migration"], AMBER, 92),
        (["SQLite", "database/data.db"], AMBER, 92),
        (["9개 테이블", "상품번호·수집이력 포함"], AMBER, 92),
    ])

    b_anom, b_change, b_trend, b_pred, b_score = stack(1200, 205, 260, 16, [
        (["이상치 탐지", "Z-score / IQR"], PURPLE, 70),
        (["가격 변동", "pcode 우선 매칭"], PURPLE, 70),
        (["가격 추이", "카테고리 평균(캐싱)"], PURPLE, 70),
        (["가격 예측", "LR/RF + GroupKFold"], PURPLE, 70),
        (["적정가 점수", "예측가+최저가 근접도"], PURPLE, 70),
    ])

    b_streamlit, b_api, b_react = stack(1580, 205, 300, 20, [
        (["Streamlit", "app.py + tabs 12개 · 8010"], CYAN, 115),
        (["FastAPI API", "라우터 13개, DB/ML 로직 재사용 · 8000"], CYAN, 100),
        (["React SPA", "Vite+TS, 9개 페이지 · 5173"], CYAN, 100),
    ])

    arrow(draw, (b_danawa[2], mid_y(b_danawa)), (b_price[0], mid_y(b_price)), BLUE)
    arrow(draw, (b_naver[2], mid_y(b_naver)), (b_news[0], mid_y(b_news)), BLUE)
    arrow(draw, (565, b_batch[1]), (565, b_news[3] + 6), GREEN)
    arrow(draw, (b_price[2], mid_y(b_price)), (b_dbm[0], mid_y(b_dbm) - 12), GREEN)
    arrow(draw, (b_detail[2], mid_y(b_detail)), (b_dbm[0], mid_y(b_dbm)), GREEN)
    arrow(draw, (b_news[2], mid_y(b_news)), (b_dbm[0], mid_y(b_dbm) + 12), GREEN)
    arrow(draw, (940, b_dbm[3]), (940, b_sql[1]), AMBER)
    arrow(draw, (940, b_sql[3]), (940, b_tables[1]), AMBER)
    arrow(draw, (b_tables[2], mid_y(b_tables)), (b_anom[0], (b_anom[1] + b_score[3]) / 2), PURPLE, 3)
    arrow(draw, (b_anom[2], mid_y(b_anom)), (b_streamlit[0], b_streamlit[1] + 25), CYAN, 3)
    arrow(draw, (b_pred[2], mid_y(b_pred)), (b_streamlit[0], mid_y(b_streamlit)), CYAN, 3)
    arrow(draw, (b_score[2], mid_y(b_score)), (b_streamlit[0], b_streamlit[3] - 25), CYAN, 3)
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
        ["제품명/스펙에서 feature 추출, LR vs RandomForest R2 비교", "GroupKFold로 동일 상품 train/test 누수 방지"],
        PURPLE,
    )
    small_box(
        draw, (row_x[2], 800), "3. 적정가 점수 (0~100)",
        ["예측가 대비 저렴함 + 과거 최저가 근접도", "고가 이상치면 감점 (규칙 기반 조합)"],
        AMBER,
    )
    small_box(
        draw, (row_x[3], 800), "4. 변동/추이 분석",
        ["pcode 우선 매칭으로 상품명 변경에도 강건", "SSD 1TB/RAM 16GB 기준으로 용량 왜곡 제거"],
        GREEN,
    )

    # ---------- 3행: 자동화 & 품질 ----------
    draw.text((70, 960), "자동화 & 품질", font=F_TITLE, fill=INK)
    small_box(
        draw, (row_x[0], 1030), "LangGraph 워크플로우",
        ["수집→분석→리포트 생성 자동화 파이프라인", "단계별 체크포인트 저장, 실패 시 재시작 가능"],
        BLUE,
    )
    small_box(
        draw, (row_x[1], 1030), "수집 실행 이력",
        ["scrape_runs 테이블에 성공/실패·소요시간 기록", "대시보드 '수집 이력' 탭에서 바로 확인"],
        GREEN,
    )
    small_box(
        draw, (row_x[2], 1030), "테스트 & CI",
        ["pytest 63개(API 포함) + vitest 12개", "GitHub Actions로 push마다 두 스위트 자동 실행"],
        SLATE,
    )
    small_box(
        draw, (row_x[3], 1030), "성능 캐싱",
        ["Streamlit st.cache_data + FastAPI cachetools(TTL)", "같은 30초/3600초 캐싱 전략을 양쪽에 재사용"],
        CYAN,
    )

    # ---------- 4행: DB 구조 요약 (3x3) ----------
    section(draw, (70, 1190, 1930, 1500), "DB 구조 요약 (9개 테이블)", SLATE)
    db_tables = [
        ("prices", "date, category, product, price, pcode, specs, image_url"),
        ("news", "collected_at, press, title, published_at"),
        ("product_registry", "internal_code(RAM-1 등), category, match_key"),
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
