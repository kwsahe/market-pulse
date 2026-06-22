# workflow/report_generator.py
# 리포트 생성 모듈 (Markdown + HTML)

import os
from datetime import datetime
from typing import Dict, Any, Tuple

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
    
    # HTML 변환 (간단)
    html_content = md_content.replace("\n", "<br>\n").replace("# ", "<h1>").replace("## ", "<h2>").replace("### ", "<h3>").replace("**", "<b>").replace("</b>", "</b>").replace("- ", "<li>").replace("<h1>", "<h1 style='color:#333;'>").replace("<h2>", "<h2 style='color:#666;'>")
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Market Pulse Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; }} h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
        .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .up {{ color: #e74c3c; }} .down {{ color: #27ae60; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
    
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