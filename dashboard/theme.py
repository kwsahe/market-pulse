# dashboard/theme.py
# 다크 모드 "실제 웹사이트" 느낌의 공통 스타일/컴포넌트 헬퍼
# (커스텀 폰트, 배경 그라디언트 글로우, 커스텀 통계 카드, 배지, 탭/버튼/스크롤바 폴리시)

import base64 as _base64
import html as _html
import os as _os
import streamlit as st

# UI 크롬(탭/헤더/보더 등 장식용) — 데이터 인코딩에는 쓰지 않음
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"

# 로고(screenshots/generate_logo.py로 생성) — data URI로 인라인 삽입해서 Streamlit
# 정적 파일 서빙 설정 없이도 항상 뜨게 한다. 프로세스당 1회만 읽는다.
_LOGO_PATH = _os.path.join(_os.path.dirname(__file__), "..", "screenshots", "logo_mark.png")


def _load_logo_data_uri() -> str:
    try:
        with open(_LOGO_PATH, "rb") as f:
            b64 = _base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except FileNotFoundError:
        return ""


LOGO_DATA_URI = _load_logo_data_uri()

# 상태 색상(dataviz 스킬의 validate_palette.js로 배경 #0D0F14 기준 검증 완료).
# 기존 파스텔톤(#34D399/#F87171/#FBBF24)은 명도 밴드·CVD 분리 기준을 통과하지 못해 교체함.
# red-green 조합은 적록색맹에서 근본적으로 구분이 어려워(ΔE 4.1) 배지에 이모지+수치를 항상 병기해 보완.
GREEN = "#0CA30C"   # 가격 인하 / 이득 (good)
RED = "#D03B3B"     # 가격 인상 (critical)
AMBER = "#FAB219"   # 이상치 경고 (warning)

# 카테고리 고정 색상(다른 차트에서도 항상 같은 카테고리는 항상 같은 색) — validate_palette.js 통과
# 게이밍 모니터(#8749A4)는 7번째 색이라 남은 색상환 틈(OKLCh 색상각 314°)에서 골랐다.
# 기존 6색 전부와 정상시각 ΔE ≥ 16.6, 색각이상 ΔE ≥ 11.0, 배경(#0D0F14) 대비 3.21:1로 전 항목 통과.
CATEGORY_COLORS = {
    "게이밍 노트북": "#3987E5",
    "DDR5 RAM": "#D95926",
    "NVMe SSD": "#199E70",
    "그래픽카드": "#C98500",
    "CPU": "#D55181",
    "AI 노트북": "#9085E9",
    "게이밍 모니터": "#8749A4",
}
DEFAULT_CATEGORY_COLOR = "#8B93A7"

SURFACE = "#171A21"
SURFACE_RAISED = "#1E222C"
BORDER = "#2D3340"
TEXT = "#F3F4F6"
MUTED = "#8B93A7"


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)


def inject_css() -> None:
    """폰트 · 배경 글로우 · 탭/메트릭/버튼/스크롤바 · 카드 호버 등 전역 스타일 주입"""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
            font-family: 'Inter', -apple-system, sans-serif;
        }}
        h1, h2, h3, [data-testid="stHeading"] p {{
            font-family: 'Manrope', sans-serif !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }}

        /* ---------- 배경 앰비언트 글로우 ---------- */
        [data-testid="stApp"] {{
            background-color: #0D0F14;
            background-image:
                radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.14), transparent 40%),
                radial-gradient(circle at 100% 100%, rgba(139, 92, 246, 0.12), transparent 40%);
            background-attachment: fixed;
        }}

        /* ---------- 히어로 헤더 ---------- */
        .mp-hero {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .mp-hero-title {{
            font-family: 'Manrope', sans-serif;
            font-weight: 800;
            font-size: 2.3rem;
            margin: 0;
            color: {TEXT};
        }}
        .mp-hero-title .mp-hero-title-text {{
            background: linear-gradient(90deg, {TEXT} 0%, {CYAN} 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        @supports not (-webkit-background-clip: text) {{
            .mp-hero-title .mp-hero-title-text {{ -webkit-text-fill-color: initial; }}
        }}
        .mp-hero-icon {{
            display: inline-block;
            margin-right: 10px;
            -webkit-text-fill-color: initial;
        }}
        .mp-hero-logo {{
            display: inline-block;
            width: 52px;
            height: 52px;
            border-radius: 14px;
            margin-right: 14px;
            vertical-align: middle;
            box-shadow: 0 4px 14px rgba(34,211,238,0.25);
        }}
        .mp-hero-title-link {{
            text-decoration: none !important;
            cursor: pointer;
            transition: opacity .15s ease;
        }}
        .mp-hero-title-link:hover {{
            opacity: 0.85;
        }}
        .mp-hero-sub {{
            color: {MUTED};
            font-size: 0.95rem;
            margin-top: 6px;
        }}
        .mp-live-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            background: rgba(52, 211, 153, 0.12);
            color: {GREEN};
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid rgba(52, 211, 153, 0.25);
            white-space: nowrap;
        }}
        .mp-live-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: {GREEN};
            animation: mp-pulse 1.6s infinite;
        }}
        @keyframes mp-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(52,211,153,0.55); }}
            70% {{ box-shadow: 0 0 0 8px rgba(52,211,153,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(52,211,153,0); }}
        }}
        .mp-date-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: {SURFACE};
            color: {MUTED};
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            border: 1px solid {BORDER};
            white-space: nowrap;
        }}
        .mp-new-badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 800;
            background: {VIOLET};
            color: #fff;
            letter-spacing: .02em;
            margin-left: 6px;
            vertical-align: middle;
        }}
        .mp-code-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            font-family: 'Manrope', monospace;
            background: {SURFACE_RAISED};
            color: {CYAN};
            border: 1px solid {BORDER};
            letter-spacing: .02em;
            margin-right: 6px;
            vertical-align: middle;
        }}

        /* ---------- 커스텀 통계 카드 ---------- */
        .mp-stat-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 14px;
            margin: 18px 0 10px 0;
        }}
        @media (max-width: 1200px) {{ .mp-stat-grid {{ grid-template-columns: repeat(3, 1fr); }} }}
        @media (max-width: 640px) {{ .mp-stat-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        .mp-stat-card {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 16px 18px;
            transition: all .2s ease;
        }}
        .mp-stat-card:hover {{
            transform: translateY(-3px);
            border-color: {CYAN};
            box-shadow: 0 10px 26px rgba(34,211,238,0.15);
        }}
        .mp-stat-card-accent {{
            background: linear-gradient(180deg, rgba(250,178,25,0.10), {SURFACE} 55%);
            border-color: rgba(250,178,25,0.35);
        }}
        .mp-stat-card-accent:hover {{
            border-color: {AMBER};
            box-shadow: 0 10px 26px rgba(250,178,25,0.18);
        }}
        .mp-stat-icon {{
            width: 34px;
            height: 34px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            margin-bottom: 10px;
            background: rgba(255,255,255,0.06);
        }}
        .mp-stat-label {{
            color: {MUTED};
            font-size: 0.74rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .04em;
        }}
        .mp-stat-value {{
            font-family: 'Manrope', sans-serif;
            font-size: 1.5rem;
            font-weight: 800;
            margin-top: 3px;
        }}

        /* ---------- 섹션 헤더 ---------- */
        .mp-section-header {{
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin: 8px 0 14px 0;
        }}
        .mp-section-header .mp-bar {{
            width: 4px;
            height: 20px;
            border-radius: 2px;
            background: linear-gradient(180deg, {CYAN}, {VIOLET});
            align-self: center;
        }}
        .mp-section-header .mp-title {{
            font-family: 'Manrope', sans-serif;
            font-weight: 800;
            font-size: 1.2rem;
            color: {TEXT};
        }}
        .mp-section-header .mp-sub {{
            color: {MUTED};
            font-size: 0.85rem;
        }}

        /* ---------- 탭 ---------- */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {{
            gap: 6px;
            border-bottom: none !important;
        }}
        [data-testid="stTab"] {{
            border-radius: 999px !important;
            padding: 8px 18px !important;
            background: {SURFACE};
            border: 1px solid {BORDER};
            transition: all .18s ease;
        }}
        [data-testid="stTab"]:hover {{
            border-color: {CYAN};
        }}
        [data-testid="stTab"][aria-selected="true"] {{
            background: linear-gradient(90deg, {CYAN}, #67e8f9);
            border-color: transparent;
            box-shadow: 0 4px 16px rgba(34,211,238,.3);
        }}
        [data-testid="stTab"][aria-selected="true"] p {{
            color: #04121a !important;
            font-weight: 700 !important;
        }}
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
            display: none;
        }}

        /* ---------- 메트릭 위젯 ---------- */
        div[data-testid="stMetric"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 14px 16px 10px 16px;
            transition: all .2s ease;
        }}
        div[data-testid="stMetric"]:hover {{
            border-color: {CYAN};
            transform: translateY(-2px);
        }}
        [data-testid="stMetricLabel"] p {{
            color: {MUTED} !important;
            font-size: 0.76rem !important;
            text-transform: uppercase;
            letter-spacing: .03em;
            font-weight: 700 !important;
        }}
        [data-testid="stMetricValue"] {{
            font-family: 'Manrope', sans-serif !important;
            font-weight: 800 !important;
        }}

        /* ---------- 카드(마커 기반 호버 하이라이트) ---------- */
        .mp-card-marker {{ display: none; }}
        div[data-testid="stVerticalBlock"]:has(
            > div[data-testid="stElementContainer"]:first-child > div[data-testid="stMarkdown"] div.mp-card-marker
        ) {{
            background: {SURFACE};
            border-radius: 18px !important;
            transition: all .2s ease;
        }}
        div[data-testid="stVerticalBlock"]:has(
            > div[data-testid="stElementContainer"]:first-child > div[data-testid="stMarkdown"] div.mp-card-marker
        ):hover {{
            transform: translateY(-3px);
            border-color: {CYAN} !important;
            box-shadow: 0 12px 28px rgba(34,211,238,0.12);
        }}

        /* ---------- 버튼 / 구분선 / 익스팬더 ---------- */
        [data-testid="stBaseButton-primary"] {{
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}
        [data-testid="stBaseButton-secondary"] {{
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}
        hr {{
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, transparent, {BORDER}, transparent) !important;
            margin: 18px 0 !important;
        }}
        div[data-testid="stExpander"] {{
            background: {SURFACE_RAISED};
            border: 1px solid {BORDER} !important;
            border-radius: 12px !important;
        }}

        /* ---------- 스크롤바 ---------- */
        ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 8px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: {CYAN}; }}

        /* ---------- 회전 카드(캐러셀) — 순수 CSS로 자동 순환, Streamlit 재실행 불필요 ---------- */
        .mp-carousel {{
            position: relative;
            border-radius: 16px;
        }}
        .mp-carousel-slide {{
            position: absolute;
            inset: 0;
            opacity: 0;
            pointer-events: none;
        }}
        .mp-spotlight-card {{
            display: flex;
            gap: 16px;
            align-items: center;
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 16px 20px;
            height: 100%;
            box-sizing: border-box;
        }}
        .mp-spotlight-img {{
            width: 96px;
            height: 96px;
            border-radius: 10px;
            object-fit: contain;
            background: {SURFACE_RAISED};
            flex-shrink: 0;
        }}
        .mp-spotlight-img-empty {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: {MUTED};
            font-size: 0.7rem;
            text-align: center;
        }}
        .mp-spotlight-info {{
            min-width: 0;
        }}
        .mp-spotlight-name {{
            font-weight: 700;
            font-size: 1rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 60vw;
            display: inline-block;
            vertical-align: middle;
        }}
        .mp-spotlight-cat {{
            color: {MUTED};
            font-size: 0.78rem;
            margin-top: 2px;
        }}
        .mp-spotlight-price {{
            margin-top: 8px;
            font-size: 0.95rem;
        }}
        .mp-spotlight-actions {{
            margin-top: 10px;
        }}
        .mp-spotlight-btn {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 5px 14px;
            border-radius: 999px;
            background: rgba(34, 211, 238, 0.12);
            color: {CYAN};
            border: 1px solid rgba(34, 211, 238, 0.3);
            font-size: 0.78rem;
            font-weight: 700;
            text-decoration: none !important;
            white-space: nowrap;
            transition: all .15s ease;
        }}
        .mp-spotlight-btn:hover {{
            background: rgba(34, 211, 238, 0.22);
            border-color: {CYAN};
        }}

        /* ---------- 배지 ---------- */
        .mp-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .mp-badge-up {{ background: rgba(248, 113, 113, 0.15); color: {RED}; }}
        .mp-badge-down {{ background: rgba(52, 211, 153, 0.15); color: {GREEN}; }}
        .mp-badge-best {{ background: rgba(34, 211, 238, 0.15); color: {CYAN}; }}
        .mp-muted {{ color: {MUTED}; font-size: 0.85rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def card_marker() -> None:
    """카드 호버 스타일을 적용받기 위한 마커 — st.container(border=True) 블록의 맨 첫 줄에서 호출"""
    st.markdown('<div class="mp-card-marker"></div>', unsafe_allow_html=True)


def hero_header(title: str, subtitle: str, live_label: str = "실시간 수집 중", date_label: str = "", icon: str = "📊") -> None:
    """그라디언트 타이틀 + 오늘 날짜 + LIVE 펄스 배지가 있는 히어로 헤더
    로고 이미지(screenshots/logo_mark.png)가 있으면 그걸 쓰고, 없으면 이모지로 대체한다.
    icon(이모지)은 별도 span으로 분리해 그라디언트 text-clip을 적용하지 않는다.
    (h1 전체에 -webkit-text-fill-color:transparent를 걸면 이모지 컬러 글리프가
    투명 처리되어 빈 사각형(tofu box)으로 보이는 렌더링 버그가 있었음)
    """
    # 참고: Streamlit의 markdown 렌더러는 CommonMark 규칙상 HTML 블록 중간에
    # 빈 줄(또는 공백만 있는 줄)이 있으면 거기서 끊고 이후를 코드블록으로 취급한다.
    # 여러 div를 이어붙일 때는 반드시 줄바꿈/들여쓰기 없는 한 줄 HTML로 만들어야 한다.
    date_html = f'<div class="mp-date-pill">📅 {date_label}</div>' if date_label else ""
    if LOGO_DATA_URI:
        icon_html = f'<img class="mp-hero-logo" src="{LOGO_DATA_URI}" alt="Market Pulse 로고">'
    else:
        icon_html = f'<span class="mp-hero-icon">{icon}</span>' if icon else ""
    html = (
        f'<div class="mp-hero"><div><h1 class="mp-hero-title">'
        f'<a href="/" target="_self" class="mp-hero-title-link">{icon_html}<span class="mp-hero-title-text">{title}</span></a></h1>'
        f'<div class="mp-hero-sub">{subtitle}</div></div>'
        f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">'
        f'{date_html}<div class="mp-live-pill"><span class="mp-live-dot"></span>{live_label}</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def section_header(icon: str, title: str, subtitle: str = "") -> None:
    """아이콘 + 그라디언트 바가 있는 섹션 타이틀"""
    sub_html = f'<span class="mp-sub">{subtitle}</span>' if subtitle else ""
    html = (
        f'<div class="mp-section-header"><span class="mp-bar"></span>'
        f'<span class="mp-title">{icon} {title}</span>{sub_html}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def stat_cards(stats: list[dict]) -> None:
    """커스텀 HTML 통계 카드 그리드
    stats: [{"icon": "📦", "label": "상품", "value": "80개", "color": "#F3F4F6", "accent": False}, ...]
    color가 TEXT/MUTED가 아니면(=시맨틱 강조색) 아이콘 배지 배경에도 같은 색을 옅게 반영한다.
    accent=True인 카드는 카드 전체에 경고 톤(앰버) 배경/보더를 준다(이상치 등 주의가 필요한 지표용).
    """
    cards_html = ""
    for s in stats:
        color = s.get("color", TEXT)
        icon_bg = _hex_to_rgba(color, 0.16) if color not in (TEXT, MUTED) else "rgba(255,255,255,0.06)"
        card_class = "mp-stat-card mp-stat-card-accent" if s.get("accent") else "mp-stat-card"
        cards_html += (
            f'<div class="{card_class}"><div class="mp-stat-icon" style="background:{icon_bg}">{s["icon"]}</div>'
            f'<div class="mp-stat-label">{s["label"]}</div>'
            f'<div class="mp-stat-value" style="color:{color}">{s["value"]}</div></div>'
        )
    st.markdown(f'<div class="mp-stat-grid">{cards_html}</div>', unsafe_allow_html=True)


def price_change_badge(change: float, change_pct: float) -> str:
    """가격 변동 배지 HTML (인상=빨강, 인하=초록)"""
    if change > 0:
        return f'<span class="mp-badge mp-badge-up">📈 +{change:,.0f}원 (+{change_pct}%)</span>'
    return f'<span class="mp-badge mp-badge-down">📉 {change:,.0f}원 ({change_pct}%)</span>'


def best_buy_badge(text: str, is_best_now: bool) -> str:
    """'언제 샀으면 얼마 이득' 뱃지 HTML"""
    if is_best_now:
        return f'<span class="mp-badge mp-badge-best">{text}</span>'
    return f'<span class="mp-muted">{text}</span>'


def new_badge() -> str:
    """신제품 표시 뱃지 HTML"""
    return '<span class="mp-new-badge">🆕 NEW</span>'


def code_badge(code: str) -> str:
    """상품번호(RAM-1, GN-3 ...) 표시 뱃지 HTML"""
    if not code:
        return ""
    return f'<span class="mp-code-badge">{code}</span>'


def spotlight_card(code: str, product: str, category: str, image_url: str, price_line: str, badge_html: str = "") -> str:
    """회전 카드(rotating_cards) 한 장의 내부 HTML — 이미지+상품번호+이름+카테고리+가격/배지+바로가기 버튼
    code가 있으면 '?code=XXX' 상세 페이지로 가는 링크 버튼을 붙인다(같은 탭에서 이동, 대시보드 전역
    라우팅 규칙과 동일 — app.py의 _open_product_detail/_render_product_detail_section 참고)."""
    product_esc = _html.escape(str(product))[:60]
    category_esc = _html.escape(str(category))
    if image_url and str(image_url).startswith("http"):
        img_html = f'<img class="mp-spotlight-img" src="{_html.escape(str(image_url), quote=True)}">'
    else:
        img_html = '<div class="mp-spotlight-img mp-spotlight-img-empty">이미지 없음</div>'
    goto_html = ""
    if code:
        code_q = _html.escape(str(code), quote=True)
        goto_html = f'<a class="mp-spotlight-btn" href="?code={code_q}" target="_self">🔗 상품 바로가기</a>'
    return (
        '<div class="mp-spotlight-card">'
        f'{img_html}'
        '<div class="mp-spotlight-info">'
        f'{code_badge(code)}<span class="mp-spotlight-name">{product_esc}</span>'
        f'<div class="mp-spotlight-cat">{category_esc}</div>'
        f'<div class="mp-spotlight-price">{price_line} {badge_html}</div>'
        f'<div class="mp-spotlight-actions">{goto_html}</div>'
        '</div></div>'
    )


def rotating_cards(cards_html: list[str], seconds_per_card: float = 4.0, height_px: int = 172) -> None:
    """카드 여러 장을 순서대로 자동 크로스페이드 순환시키는 CSS 전용 캐러셀.
    Streamlit 재실행 없이 브라우저에서만 애니메이션이 돌아간다(각 슬라이드가 고유한
    @keyframes로 전체 주기 중 자기 차례에만 보이도록 opacity를 움직인다)."""
    n = len(cards_html)
    if n == 0:
        return
    if n == 1:
        st.markdown(f'<div class="mp-carousel" style="height:{height_px}px">{cards_html[0]}</div>', unsafe_allow_html=True)
        return

    period = n * seconds_per_card
    fade_pct = min(6.0, (0.5 / period) * 100)  # 0.5초 페이드, 세그먼트 폭의 절반을 넘지 않게 상한

    style_parts = []
    slide_parts = []
    for i, card_html in enumerate(cards_html):
        start = i / n * 100
        end = (i + 1) / n * 100
        stops = []
        if i > 0:
            stops.append((0.0, 0))
        stops.append((start, 0))
        stops.append((min(start + fade_pct, end), 1))
        stops.append((max(end - fade_pct, start), 1))
        stops.append((end, 0))
        if i < n - 1:
            stops.append((100.0, 0))
        stops.sort(key=lambda s: s[0])
        # opacity와 함께 pointer-events도 같이 움직여서, 화면에 실제로 보이는 카드의 버튼만
        # 클릭되게 한다(안 그러면 모든 슬라이드가 같은 자리에 겹쳐 있어 보이지 않는 카드의
        # 링크가 클릭을 가로챌 수 있음)
        kf_body = "".join(
            f"{pct:.3f}%{{opacity:{op};pointer-events:{'auto' if op == 1 else 'none'}}}"
            for pct, op in stops
        )
        anim_name = f"mp-carousel-fade-{i}"
        style_parts.append(f"@keyframes {anim_name}{{{kf_body}}}")
        slide_parts.append(
            f'<div class="mp-carousel-slide" style="animation:{anim_name} {period:.2f}s infinite;">{card_html}</div>'
        )

    html = (
        f'<style>{"".join(style_parts)}</style>'
        f'<div class="mp-carousel" style="height:{height_px}px">{"".join(slide_parts)}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
