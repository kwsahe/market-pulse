# workflow/report_generator.py
# 리포트 생성 모듈 (Markdown + HTML)

import os
import html as html_lib
from datetime import datetime
from typing import Dict, Any, Tuple

# 대시보드(dashboard/theme.py)와 동일한 다크 테마 색상 토큰 — 리포트와 대시보드의 룩앤필을 통일
_SURFACE = "#171A21"
_SURFACE_RAISED = "#1E222C"
_BORDER = "#2D3340"
_TEXT = "#F3F4F6"
_MUTED = "#8B93A7"
_CYAN = "#22D3EE"
_GREEN = "#0CA30C"
_RED = "#D03B3B"
_AMBER = "#FAB219"


def _esc(value: Any) -> str:
    """상품명 등 외부(스크래핑) 데이터를 HTML에 안전하게 넣기 위한 이스케이프"""
    return html_lib.escape(str(value))


def _stat_card(label: str, value: str, color: str = _TEXT) -> str:
    return (
        f'<div class="stat-card"><div class="stat-label">{_esc(label)}</div>'
        f'<div class="stat-value" style="color:{color}">{_esc(value)}</div></div>'
    )


def _price_item(product: str, category: str, prev_price: float, current_price: float, change_pct: float) -> str:
    is_up = change_pct > 0
    badge_color = _RED if is_up else _GREEN
    arrow = "▲" if is_up else "▼"
    return (
        '<div class="item-card">'
        f'<div class="item-name">{_esc(product[:60])}</div>'
        f'<div class="item-cat">{_esc(category)}</div>'
        f'<div class="item-price">{prev_price:,.0f}원 → <b>{current_price:,.0f}원</b> '
        f'<span style="color:{badge_color}">{arrow} {change_pct:+.2f}%</span></div>'
        '</div>'
    )


def _anomaly_item(product: str, category: str, price: float, method: str, detail: str) -> str:
    return (
        '<div class="item-card">'
        f'<div class="item-name">⚠️ {_esc(product[:60])}</div>'
        f'<div class="item-cat">{_esc(category)}</div>'
        f'<div class="item-price">{price:,.0f}원 <span class="item-cat">· {_esc(method)} ({_esc(detail)})</span></div>'
        '</div>'
    )


def _render_html_report(state: Dict[str, Any], run_id: str, timestamp: str) -> str:
    """state 데이터로 직접 HTML을 구성한다 (md 문자열을 정규식 치환하지 않음 — 태그 깨짐 방지)"""
    sections = []

    summary_html = (
        '<div class="summary-grid">'
        + _stat_card("가격 데이터", f"{state.get('prices_collected', 0)}개 (+{state.get('prices_new', 0)})", _CYAN)
        + _stat_card("뉴스 데이터", f"{state.get('news_collected', 0)}개 (+{state.get('news_new', 0)})", _CYAN)
        + _stat_card("총 상품", f"{state.get('total_products', 0)}개")
        + _stat_card("소요시간", f"{state.get('duration_seconds', 0):.1f}초")
        + '</div>'
    )
    sections.append(f'<h2>📊 요약</h2>{summary_html}')
    categories = state.get("categories", [])
    if categories:
        sections.append(f'<p class="item-cat">카테고리: {_esc(", ".join(categories))}</p>')

    changes = state.get("price_changes", [])
    if changes:
        up = [c for c in changes if c["change"] > 0]
        down = [c for c in changes if c["change"] < 0]
        change_summary = (
            '<div class="summary-grid">'
            + _stat_card("전체 변동", f"{len(changes)}개")
            + _stat_card("인상", f"{len(up)}개", _RED)
            + _stat_card("인하", f"{len(down)}개", _GREEN)
            + '</div>'
        )
        top_up = "".join(
            _price_item(c["product"], c["category"], c["prev_price"], c["current_price"], c["change_pct"])
            for c in sorted(changes, key=lambda x: x["change_pct"], reverse=True)[:5]
        )
        top_down = "".join(
            _price_item(c["product"], c["category"], c["prev_price"], c["current_price"], c["change_pct"])
            for c in sorted(changes, key=lambda x: x["change_pct"])[:5]
        )
        sections.append(
            f'<h2>📈 가격 변동 ({len(changes)}개)</h2>{change_summary}'
            f'<h3>TOP 5 인상</h3>{top_up}<h3>TOP 5 인하</h3>{top_down}'
        )

    anomalies = state.get("anomalies", [])
    if anomalies:
        items = "".join(
            _anomaly_item(a["product"], a["category"], a["price"], a["method"], a["detail"])
            for a in anomalies[:10]
        )
        sections.append(f'<h2>⚠️ 이상치 ({len(anomalies)}개)</h2>{items}')

    trends = state.get("trend_summary", [])
    if trends:
        rows = "".join(
            '<div class="item-card">'
            f'<div class="item-name">{"📈" if t["direction"] == "up" else ("📉" if t["direction"] == "down" else "➡️")} '
            f'{_esc(t["category"])}</div>'
            f'<div class="item-price">{t["first_price"]:,.0f}원 → {t["last_price"]:,.0f}원 '
            f'<span style="color:{_RED if t["direction"] == "up" else _GREEN}">{t["change_pct"]:+.2f}%</span></div>'
            '</div>'
            for t in trends
        )
        sections.append(f'<h2>📈 카테고리 트렌드</h2>{rows}')

    if state.get("error"):
        sections.append(f'<h2>❌ 에러</h2><div class="error-box">{_esc(state["error"])}</div>')

    body = "".join(sections)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Market Pulse Report — {_esc(run_id)}</title>
<style>
  :root {{
    --surface: {_SURFACE}; --surface-raised: {_SURFACE_RAISED}; --border: {_BORDER};
    --text: {_TEXT}; --muted: {_MUTED}; --cyan: {_CYAN};
  }}
  body {{
    background: #0D0F14; color: var(--text);
    font-family: 'Segoe UI', -apple-system, sans-serif;
    max-width: 900px; margin: 0 auto; padding: 32px 24px; line-height: 1.6;
  }}
  h1 {{ font-size: 1.8rem; margin: 0 0 4px 0; }}
  h1 .title-text {{
    background: linear-gradient(90deg, var(--text), var(--cyan));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  }}
  h1 .title-icon {{ display: inline-block; margin-right: 8px; -webkit-text-fill-color: initial; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 8px; }}
  h2 {{ font-size: 1.15rem; margin-top: 32px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  h3 {{ font-size: 0.95rem; color: var(--muted); margin: 18px 0 8px 0; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 14px 0; }}
  .stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }}
  .stat-label {{ color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: .04em; }}
  .stat-value {{ font-size: 1.25rem; font-weight: 800; margin-top: 4px; }}
  .item-card {{ background: var(--surface-raised); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }}
  .item-name {{ font-weight: 600; }}
  .item-cat {{ color: var(--muted); font-size: 0.78rem; }}
  .item-price {{ margin-top: 4px; }}
  .error-box {{ background: rgba(208,59,59,0.12); border: 1px solid {_RED}; border-radius: 10px; padding: 14px; color: {_RED}; }}
</style>
</head>
<body>
  <h1><span class="title-icon">📊</span><span class="title-text">Market Pulse 리포트</span></h1>
  <div class="meta">생성일 {_esc(timestamp)} · 실행 ID {_esc(run_id)}</div>
  {body}
</body>
</html>
"""


def generate_report(state: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    상태 기반 리포트 생성
    반환: (markdown_content, html_content, save_path)
    """
    run_id = state.get("run_id", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # MD 생성
    md_lines = [
        f"# Market Pulse 리포트",
        f"",
        f"**생성일:** {timestamp}",
        f"**실행 ID:** {run_id}",
        f"**소요시간:** {state.get('duration_seconds', 0):.1f}초",
        f"",
        f"## 📊 요약",
        f"- **가격 데이터:** {state.get('prices_collected', 0)}개 (신규: {state.get('prices_new', 0)}개)",
        f"- **뉴스 데이터:** {state.get('news_collected', 0)}개 (신규: {state.get('news_new', 0)}개)",
        f"- **카테고리:** {', '.join(state.get('categories', []))}",
        f"- **총 상품:** {state.get('total_products', 0)}개",
        f"",
    ]
    
    # 가격 변동
    changes = state.get('price_changes', [])
    if changes:
        up_count = len([c for c in changes if c['change'] > 0])
        down_count = len([c for c in changes if c['change'] < 0])
        md_lines.extend([
            f"## 📈 가격 변동 ({len(changes)}개)",
            f"- **인상:** {up_count}개",
            f"- **인하:** {down_count}개",
            f"",
            f"### TOP 5 인상",
        ])
        for item in sorted(changes, key=lambda x: x['change_pct'], reverse=True)[:5]:
            md_lines.append(f"- **{item['product'][:40]}** ({item['category']})")
            md_lines.append(f"  {item['prev_price']:,}원 → {item['current_price']:,}원 (+{item['change_pct']:.2f}%)")
        md_lines.append("")
        
        md_lines.append("### TOP 5 인하")
        for item in sorted(changes, key=lambda x: x['change_pct'])[:5]:
            md_lines.append(f"- **{item['product'][:40]}** ({item['category']})")
            md_lines.append(f"  {item['prev_price']:,}원 → {item['current_price']:,}원 ({item['change_pct']:.2f}%)")
        md_lines.append("")
    
    # 이상치
    anomalies = state.get('anomalies', [])
    if anomalies:
        md_lines.extend([
            f"## ⚠️ 이상치 ({len(anomalies)}개)",
            f"",
        ])
        for item in anomalies[:10]:
            md_lines.append(f"- **{item['product'][:40]}** ({item['category']})")
            md_lines.append(f"  가격: {item['price']:,}원 | 방법: {item['method']} ({item['detail']})")
        md_lines.append("")
    
    # 트렌드
    trends = state.get('trend_summary', [])
    if trends:
        md_lines.extend([
            f"## 📈 카테고리 트렌드",
            f"",
        ])
        for t in trends:
            icon = "📈" if t['direction'] == 'up' else ("📉" if t['direction'] == 'down' else "➡️")
            md_lines.append(f"- {icon} **{t['category']}**: {t['first_price']:,.0f}원 → {t['last_price']:,.0f}원 ({t['change_pct']:+.2f}%)")
        md_lines.append("")
    
    # 에러 발생 시
    if state.get('error'):
        md_lines.extend([
            f"## ❌ 에러",
            f"",
            f"{state['error']}",
            f"",
        ])
    
    md_content = "\n".join(md_lines)

    # HTML 생성 (md 문자열을 정규식으로 변환하지 않고, 대시보드와 같은 상태 데이터로 직접 구성 —
    # 대시보드(dashboard/theme.py)와 동일한 다크 테마 색상 토큰을 재사용해 룩앤필을 통일한다)
    html_content = _render_html_report(state, run_id, timestamp)
    
    # 저장
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"report_{run_id}.md"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    html_path = os.path.join(reports_dir, f"report_{run_id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return md_content, html_content, filepath