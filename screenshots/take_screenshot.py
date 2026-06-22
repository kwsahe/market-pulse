"""
Take a screenshot of product cards with images using data from 2026-04-06.
Builds a standalone HTML page and screenshots it with Playwright.
"""
import asyncio
import sqlite3
import os
from playwright.async_api import async_playwright

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "data.db")
OUTPUT = os.path.join(os.path.dirname(__file__), "screenshot_products.png")
HTML_PATH = os.path.join(os.path.dirname(__file__), "_screenshot_tmp.html")

DATE = "2026-04-06"


def load_products():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT category, product, price, image_url, specs
        FROM prices
        WHERE date = ? AND image_url IS NOT NULL AND image_url != ''
        ORDER BY category, price ASC
    """, (DATE,))
    rows = cur.fetchall()
    conn.close()
    return rows


def build_html(rows):
    # Group by category
    cats = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r)

    cards_html = ""
    for cat, products in cats.items():
        cards_html += f'<h2 class="cat-title">{cat}</h2><div class="grid">'
        for p in products[:6]:  # show up to 6 per category
            name = p["product"][:55]
            price = f'{p["price"]:,}원'
            img = p["image_url"]
            cards_html += f"""
            <div class="card">
              <img src="{img}" alt="{name}" onerror="this.style.display='none'">
              <div class="info">
                <div class="name">{name}</div>
                <div class="price">{price}</div>
              </div>
            </div>"""
        cards_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Market Pulse — 제품 목록</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f6; margin: 0; padding: 20px; }}
  header {{ background: white; border-radius: 12px; padding: 20px 28px; margin-bottom: 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,.08); display: flex; align-items: center; gap: 12px; }}
  header h1 {{ font-size: 28px; margin: 0; color: #1a1a2e; }}
  header p {{ font-size: 13px; color: #666; margin: 0; }}
  .cat-title {{ color: #1a1a2e; margin: 24px 0 10px; font-size: 18px; border-left: 4px solid #4A90D9;
                padding-left: 10px; }}
  .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  .card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
           display: flex; gap: 14px; align-items: center; }}
  .card img {{ width: 100px; height: 100px; object-fit: contain; border-radius: 6px;
               background: #f8f8f8; flex-shrink: 0; }}
  .info {{ min-width: 0; }}
  .name {{ font-size: 13px; color: #333; line-height: 1.4; margin-bottom: 8px; }}
  .price {{ font-size: 16px; font-weight: 700; color: #e63946; }}
  .badge {{ display: inline-block; font-size: 11px; background: #4A90D9; color: white;
            border-radius: 4px; padding: 2px 6px; margin-bottom: 6px; }}
</style>
</head>
<body>
  <header>
    <div style="font-size:40px">📊</div>
    <div>
      <h1>Market Pulse</h1>
      <p>게이밍 노트북 &amp; PC 부품 가격 추적 · ML 분석 · IT 뉴스 대시보드</p>
    </div>
  </header>
  {cards_html}
</body>
</html>"""


async def main():
    rows = load_products()
    if not rows:
        print("No products with images found!")
        return

    html = build_html(rows)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built HTML with {len(rows)} products")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 860})
        await page.goto(f"file:///{HTML_PATH.replace(chr(92), '/')}", wait_until="networkidle", timeout=30000)
        # Wait for images to load
        await page.wait_for_timeout(4000)
        await page.screenshot(path=OUTPUT, full_page=False)
        print(f"Screenshot saved: {OUTPUT}")
        await browser.close()

    os.remove(HTML_PATH)

asyncio.run(main())
