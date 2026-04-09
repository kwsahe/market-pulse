# scraper/news_scraper.py
# 네이버 IT/과학 뉴스 수집 스크래퍼 (중복 방지)

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, insert_many_news

init_db()


def parse_relative_time(time_text):
    now = datetime.now()
    match = re.search(r"(\d+)", time_text)
    if not match:
        return now.strftime("%Y-%m-%d %H:%M")
    num = int(match.group(1))
    if "분전" in time_text:
        result = now - timedelta(minutes=num)
    elif "시간전" in time_text:
        result = now - timedelta(hours=num)
    elif "일전" in time_text:
        result = now - timedelta(days=num)
    else:
        result = now
    return result.strftime("%Y-%m-%d %H:%M")


URL = "https://news.naver.com/section/105"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(URL, headers=headers, timeout=15)
    response.raise_for_status()
    print(f"응답 상태: {response.status_code}")
except requests.exceptions.Timeout:
    print("⚠️ 요청 시간 초과 (15초). 뉴스 수집을 건너뜁니다.")
    exit(1)
except requests.exceptions.RequestException as e:
    print(f"⚠️ 네트워크 오류: {e}. 뉴스 수집을 건너뜁니다.")
    exit(1)

try:
    soup = BeautifulSoup(response.text, "html.parser")
    titles = soup.find_all("strong", class_="sa_text_strong")
    times = soup.find_all("b", string=lambda t: t and ("분전" in t or "시간전" in t or "일전" in t))
    press_list = soup.find_all("div", class_="sa_text_press")
except Exception as e:
    print(f"⚠️ HTML 파싱 오류: {e}. 뉴스 수집을 건너뜁니다.")
    exit(1)

now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

data_list = []
print(f"\n수집된 뉴스 수: {len(titles)}개\n")
print("=" * 70)

for i, title in enumerate(titles):
    try:
        headline = title.get_text(strip=True)
        time_text = times[i].get_text(strip=True) if i < len(times) else ""
        press = press_list[i].get_text(strip=True) if i < len(press_list) else "언론사 없음"
        published = parse_relative_time(time_text)

        print(f"{i+1}. [{press}] {headline}")
        print(f"   {time_text} → {published}")
        print("-" * 70)

        data_list.append((now_str, press, headline, published))
    except Exception as e:
        print(f"   ⚠️ 뉴스 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
        continue

new_count = insert_many_news(data_list)
print(f"\n✅ 수집: {len(data_list)}개 | 신규 저장: {new_count}개 | 중복 건너뜀: {len(data_list) - new_count}개")