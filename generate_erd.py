import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("#1e1e2e")
ax.set_facecolor("#1e1e2e")

C_HEADER_PRICES = "#4c9be8"
C_HEADER_NEWS   = "#56b6a0"
C_ROW_DARK      = "#2a2a3e"
C_ROW_LIGHT     = "#313145"
C_PK            = "#f0c060"
C_IDX           = "#c084fc"
C_TEXT          = "#e0e0f0"
C_BORDER        = "#555577"
C_NOTE          = "#888899"
C_LABEL         = "#aaaacc"
C_ARROW         = "#6666aa"

ROW_H    = 0.50
HEADER_H = 0.65
TABLE_TOP = 8.05
PW = 6.3
PX, NX = 0.7, 9.0


def draw_table(ax, x, y, w, title, header_color, columns):
    total_h = HEADER_H + len(columns) * ROW_H + 0.08
    bot = y - total_h

    ax.add_patch(FancyBboxPatch(
        (x, bot), w, total_h,
        boxstyle="round,pad=0.05", lw=1.8,
        edgecolor=C_BORDER, facecolor=C_ROW_DARK, zorder=2))

    ax.add_patch(FancyBboxPatch(
        (x, y - HEADER_H), w, HEADER_H,
        boxstyle="round,pad=0.05", lw=0,
        edgecolor="none", facecolor=header_color, zorder=3))
    ax.text(x + w / 2, y - HEADER_H / 2, title,
            ha="center", va="center", fontsize=14, fontweight="bold",
            color="white", zorder=4)

    for i, (col_name, col_type, tag) in enumerate(columns):
        ry = y - HEADER_H - (i + 1) * ROW_H
        bg = C_ROW_DARK if i % 2 == 0 else C_ROW_LIGHT
        ax.add_patch(FancyBboxPatch(
            (x + 0.06, ry + 0.04), w - 0.12, ROW_H - 0.06,
            boxstyle="round,pad=0.02", lw=0,
            edgecolor="none", facecolor=bg, zorder=3))

        if tag:
            tc = C_PK if tag == "PK" else (C_IDX if tag in ("UQ",) else C_LABEL)
            if tag == "NOT NULL":
                tc = "#70a8e0"
            ax.add_patch(FancyBboxPatch(
                (x + 0.14, ry + 0.10), 0.74, 0.28,
                boxstyle="round,pad=0.04", lw=0,
                edgecolor="none", facecolor=tc + "44", zorder=4))
            ax.text(x + 0.51, ry + ROW_H / 2, tag,
                    ha="center", va="center", fontsize=7, fontweight="bold",
                    color=tc, zorder=5)

        ax.text(x + 0.98, ry + ROW_H / 2, col_name,
                ha="left", va="center", fontsize=10.5,
                color=C_TEXT, fontweight="bold" if tag == "PK" else "normal", zorder=5)
        ax.text(x + w - 0.16, ry + ROW_H / 2, col_type,
                ha="right", va="center", fontsize=8.5,
                color=C_LABEL, style="italic", zorder=5)

    return bot


def note_box(ax, x, y, lines, color, width=3.6):
    bh = 0.31 * len(lines) + 0.20
    ax.add_patch(FancyBboxPatch(
        (x, y - bh), width, bh,
        boxstyle="round,pad=0.08", lw=1.1,
        edgecolor=color + "99", facecolor=color + "22", zorder=4))
    for j, line in enumerate(lines):
        ax.text(x + 0.17, y - 0.17 - j * 0.31, line,
                ha="left", va="top", fontsize=8.5, color=color, zorder=5)
    return bh


# ── 타이틀 ─────────────────────────────────────────────────
ax.text(8.0, 8.77, "Market Pulse  —  Database ERD",
        ha="center", va="center", fontsize=18, fontweight="bold", color="white")
ax.text(8.0, 8.44, "SQLite  ·  prices (4,336 rows)  ·  news (341 rows)  ·  database/data.db",
        ha="center", va="center", fontsize=9, color=C_NOTE)

# ── 테이블 ─────────────────────────────────────────────────
prices_cols = [
    ("id",        "INTEGER", "PK"),
    ("date",      "TEXT",    "NOT NULL"),
    ("category",  "TEXT",    "NOT NULL"),
    ("product",   "TEXT",    "NOT NULL"),
    ("price",     "INTEGER", "NOT NULL"),
    ("specs",     "TEXT",    "nullable"),
    ("image_url", "TEXT",    "nullable"),
]
news_cols = [
    ("id",           "INTEGER", "PK"),
    ("collected_at", "TEXT",    "NOT NULL"),
    ("press",        "TEXT",    "nullable"),
    ("title",        "TEXT",    "NOT NULL"),
    ("published_at", "TEXT",    "nullable"),
]

p_bot = draw_table(ax, PX, TABLE_TOP, PW, "prices", C_HEADER_PRICES, prices_cols)
n_bot = draw_table(ax, NX, TABLE_TOP, PW, "news",   C_HEADER_NEWS,   news_cols)

# ── 테이블 간 연관 — 두 테이블 하단 아래에 elbow 커넥터 ───
# prices 오른쪽 아래 모서리 → 수평 연결선 → news 왼쪽 아래 모서리
conn_y = min(p_bot, n_bot) - 0.35   # 두 테이블 모두 아래
p_right = PX + PW
n_left  = NX
mid_x   = (p_right + n_left) / 2

# prices 쪽 수직 + 수평 절반
ax.plot([p_right - 0.04, p_right - 0.04, mid_x],
        [p_bot, conn_y, conn_y],
        color=C_ARROW, lw=1.5, linestyle="--", zorder=3)
# news 쪽 수직 + 수평 절반
ax.plot([n_left + 0.04, n_left + 0.04, mid_x],
        [n_bot, conn_y, conn_y],
        color=C_ARROW, lw=1.5, linestyle="--", zorder=3)
# 화살표 머리 표시 (양쪽 꺾인 부분)
for bx, by in [(p_right - 0.04, p_bot), (n_left + 0.04, n_bot)]:
    ax.plot(bx, by, "o", color=C_ARROW, ms=5, zorder=4)

# 연결 설명 텍스트
ax.text(mid_x, conn_y - 0.10,
        "논리적 연관: date 기준 조회  (FK 없음)",
        ha="center", va="top", fontsize=8.5, color=C_NOTE, style="italic")

# ── UNIQUE INDEX 주석 ─────────────────────────────────────
note_box(ax, PX + 0.3, p_bot - 0.60,
         ["UNIQUE INDEX: (date, product)",
          "→ 하루 1회, 상품 중복 방지"],
         C_IDX)

note_box(ax, NX + 0.3, n_bot - 0.60,
         ["UNIQUE INDEX: (title, press)",
          "→ 동일 기사 중복 방지"],
         C_IDX)

# ── 범례 ─────────────────────────────────────────────────
LX, LY = 0.5, 2.10
ax.text(LX, LY + 0.12, "Legend",
        fontsize=9.5, fontweight="bold", color=C_TEXT)
for i, (col, label) in enumerate([
    (C_PK,       "PK  —  Primary Key (AUTOINCREMENT)"),
    (C_IDX,      "UQ  —  Unique Index"),
    ("#70a8e0",  "NOT NULL  —  필수 컬럼"),
    (C_LABEL,    "nullable  —  선택 컬럼"),
]):
    iy = LY - 0.38 - i * 0.40
    ax.add_patch(FancyBboxPatch(
        (LX, iy), 0.38, 0.26,
        boxstyle="round,pad=0.04", lw=0,
        edgecolor="none", facecolor=col + "66", zorder=4))
    ax.text(LX + 0.52, iy + 0.13, label,
            ha="left", va="center", fontsize=8.5, color=C_LABEL)

plt.tight_layout(pad=0.3)
plt.savefig("erd.png", dpi=180, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("saved: erd.png")
