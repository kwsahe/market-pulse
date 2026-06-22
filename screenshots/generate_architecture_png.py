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
    x, y = xy
    shadow(draw, (x, y, x + w, y + h), 18)
    rounded(draw, (x, y, x + w, y + h), "#ffffff", color, 3, 18)
    draw.rectangle((x, y, x + 8, y + h), fill=color)
    draw_centered(draw, (x + 16, y + 8, x + w - 12, y + h - 8), label, F_BOX)
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
    img = Image.new("RGB", (1800, 1260), BG)
    draw = ImageDraw.Draw(img)

    draw.text((70, 44), "Market Pulse 구성도 및 데이터 흐름", font=F_TITLE, fill=INK)
    draw.text(
        (74, 104),
        "Danawa 가격 수집, Naver 뉴스 수집, SQLite 저장, Streamlit 대시보드, ML 가격 예측/이상치 분석",
        font=F_SUBTITLE,
        fill=MUTED,
    )

    section(draw, (70, 165, 340, 620), "외부 데이터", BLUE)
    section(draw, (410, 165, 720, 620), "수집 계층", GREEN)
    section(draw, (790, 165, 1095, 620), "저장 계층", AMBER)
    section(draw, (1165, 165, 1500, 620), "분석 / ML", PURPLE)
    section(draw, (1545, 165, 1730, 620), "표현", CYAN)

    b_danawa = box(draw, (105, 255), ["Danawa", "제품/가격/스펙"], BLUE, 200, 92)
    b_naver = box(draw, (105, 410), ["Naver News", "IT/과학 뉴스"], BLUE, 200, 92)

    b_price = box(draw, (445, 230), ["price_scraper.py", "가격/스펙/이미지"], GREEN, 240, 92)
    b_news = box(draw, (445, 385), ["news_scraper.py", "뉴스 제목/언론사"], GREEN, 240, 92)
    b_batch = box(draw, (445, 515), ["run_scrapers.bat", "수집 자동 실행"], GREEN, 240, 72)

    b_dbm = box(draw, (825, 235), ["db_manager.py", "init / insert"], AMBER, 230, 92)
    b_sql = box(draw, (825, 390), ["SQLite", "database/data.db"], AMBER, 230, 92)
    b_tables = box(draw, (825, 515), ["prices / news", "unique index"], AMBER, 230, 72)

    b_anom = box(draw, (1200, 220), ["이상치 탐지", "Z-score / IQR"], PURPLE, 260, 82)
    b_change = box(draw, (1200, 325), ["가격 변동", "전일 대비 비교"], PURPLE, 260, 82)
    b_trend = box(draw, (1200, 430), ["가격 추이", "카테고리 평균"], PURPLE, 260, 82)
    b_pred = box(draw, (1200, 535), ["가격 예측", "LR / RandomForest"], PURPLE, 260, 82)

    b_ui = box(draw, (1575, 342), ["Streamlit", "Dashboard"], CYAN, 135, 110)

    arrow(draw, (b_danawa[2], 301), (b_price[0], 276), BLUE)
    arrow(draw, (b_naver[2], 456), (b_news[0], 431), BLUE)
    arrow(draw, (565, b_batch[1]), (565, b_news[3] + 8), GREEN)
    arrow(draw, (685, 276), (b_dbm[0], 281), GREEN)
    arrow(draw, (685, 431), (b_dbm[0], 281), GREEN)
    arrow(draw, (940, b_dbm[3]), (940, b_sql[1]), AMBER)
    arrow(draw, (940, b_sql[3]), (940, b_tables[1]), AMBER)

    for target_y in [261, 366, 471, 576]:
        arrow(draw, (b_tables[2], 551), (b_anom[0], target_y), PURPLE, 3)
    for source_y in [261, 366, 471, 576]:
        arrow(draw, (b_anom[2], source_y), (b_ui[0], 397), CYAN, 3)

    draw.text((70, 685), "ML 활용 상세", font=F_TITLE, fill=INK)
    small_box(
        draw,
        (70, 755),
        "1. 이상치 탐지",
        ["카테고리별 최신 가격 분포에서 비정상 가격 감지", "Z-score threshold 2.5, IQR 1.5배 기준"],
        RED,
    )
    small_box(
        draw,
        (510, 755),
        "2. 가격 예측",
        ["제품명/스펙 텍스트에서 feature 추출", "Linear Regression과 Random Forest를 R2로 비교"],
        PURPLE,
    )
    small_box(
        draw,
        (950, 755),
        "3. 변동/추이 분석",
        ["최신일과 직전일 가격 비교", "날짜/카테고리별 평균 가격 추이 집계"],
        GREEN,
    )
    small_box(
        draw,
        (1390, 755),
        "4. 대시보드 반영",
        ["ML 결과를 Streamlit 탭에 즉시 표시", "가격 예측 모델은 카테고리별 캐싱"],
        CYAN,
    )

    section(draw, (70, 990, 1730, 1160), "DB 구조 요약", SLATE)
    draw.text((115, 1063), "prices", font=F_BOX, fill=INK)
    draw.text((115, 1102), "id, date, category, product, price, specs, image_url", font=F_SMALL, fill=MUTED)
    draw.text((820, 1063), "news", font=F_BOX, fill=INK)
    draw.text((820, 1102), "id, collected_at, press, title, published_at", font=F_SMALL, fill=MUTED)
    draw.text((1300, 1063), "중복 방지", font=F_BOX, fill=INK)
    draw.text((1300, 1102), "prices(date, product), news(title, press)", font=F_SMALL, fill=MUTED)

    img.save(OUT_PATH)
    print(f"saved: {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
