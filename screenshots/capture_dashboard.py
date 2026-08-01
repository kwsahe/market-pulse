"""dashboard/app.py를 로컬에서 실행 중일 때(기본 localhost:8010) Playwright로 캡처해서
README용 screenshots/dashboard_overview.png를 갱신한다.

사용법:
    streamlit run dashboard/app.py --server.port 8010   # 다른 터미널에서 먼저 실행
    python screenshots/capture_dashboard.py
"""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("MARKET_PULSE_URL", "http://localhost:8010")
OUTPUT = os.path.join(os.path.dirname(__file__), "dashboard_overview.png")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
        await page.goto(URL, wait_until="networkidle", timeout=30000)
        # Streamlit이 차트/위젯을 그릴 시간을 준다
        await page.wait_for_timeout(3000)
        await page.screenshot(path=OUTPUT, full_page=False)
        print(f"Saved: {OUTPUT}")
        await browser.close()

asyncio.run(main())
