# dashboard/theme.py
# 다크 모드 "실제 웹사이트" 느낌의 공통 스타일/컴포넌트 헬퍼
# (커스텀 폰트, 배경 그라디언트 글로우, 커스텀 통계 카드, 배지, 탭/버튼/스크롤바 폴리시)

import streamlit as st

# UI 크롬(탭/헤더/보더 등 장식용) — 데이터 인코딩에는 쓰지 않음
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"

# 상태 색상(dataviz 스킬의 validate_palette.js로 배경 #0D0F14 기준 검증 완료).
# 기존 파스텔톤(#34D399/#F87171/#FBBF24)은 명도 밴드·CVD 분리 기준을 통과하지 못해 교체함.
# red-green 조합은 적록색맹에서 근본적으로 구분이 어려워(ΔE 4.1) 배지에 이모지+수치를 항상 병기해 보완.
GREEN = "#0CA30C"   # 가격 인하 / 이득 (good)
RED = "#D03B3B"     # 가격 인상 (critical)
AMBER = "#FAB219"   # 이상치 경고 (warning)

# 카테고리 고정 색상(다른 차트에서도 항상 같은 카테고리는 같은 색) — validate_palette.js 통과
CATEGORY_COLORS = {
    "게이밍 노트북": "#3987E5",
    "DDR5 RAM": "#D95926",
    "NVMe SSD": "#199E70",
    "그래픽카드": "#C98500",
    "CPU": "#D55181",
    "AI 노트북": "#9085E9",
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
            background: linear-gradient(90deg, {TEXT} 0%, {CYAN} 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        @supports not (-webkit-background-clip: text) {{
            .mp-hero-title {{ -webkit-text-fill-color: initial; }}
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


def hero_header(title: str, subtitle: str, live_label: str = "실시간 수집 중", date_label: str = "") -> None:
    """그라디언트 타이틀 + 오늘 날짜 + LIVE 펄스 배지가 있는 히어로 헤더"""
    # 참고: Streamlit의 markdown 렌더러는 CommonMark 규칙상 HTML 블록 중간에
    # 빈 줄(또는 공백만 있는 줄)이 있으면 거기서 끊고 이후를 코드블록으로 취급한다.
    # 여러 div를 이어붙일 때는 반드시 줄바꿈/들여쓰기 없는 한 줄 HTML로 만들어야 한다.
    date_html = f'<div class="mp-date-pill">📅 {date_label}</div>' if date_label else ""
    html = (
        f'<div class="mp-hero"><div><h1 class="mp-hero-title">{title}</h1>'
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


def stat_cards(stats: list[dict]) -> None:
    """커스텀 HTML 통계 카드 그리드
    stats: [{"icon": "📦", "label": "상품", "value": "80개", "color": "#F3F4F6"}, ...]
    """
    cards_html = "".join(
        f'<div class="mp-stat-card"><div class="mp-stat-icon">{s["icon"]}</div>'
        f'<div class="mp-stat-label">{s["label"]}</div>'
        f'<div class="mp-stat-value" style="color:{s.get("color", TEXT)}">{s["value"]}</div></div>'
        for s in stats
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
