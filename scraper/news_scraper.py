# scraper/news_scraper.py
# 네이버 IT/과학 뉴스 수집 스크래퍼 (DB 저장 버전)

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

# database 폴더의 db_manager를 import하기 위한 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, insert_many_news

# ============================
# 1단계: DB 초기화
# ============================
init_db()

# ============================
# 2단계: 웹페이지 가져오기
# ============================
URL = "https://news.naver.com/section/105"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)
print(f"응답 상태: {response.status_code}")

# ============================
# 3단계: HTML 파싱 & 데이터 추출
# ============================
soup = BeautifulSoup(response.text, "html.parser")

titles = soup.find_all("strong", class_="sa_text_strong")
times = soup.find_all("b", string=lambda t: t and ("분전" in t or "시간전" in t or "일전" in t))
press_list = soup.find_all("div", class_="sa_text_press")

now = datetime.now().strftime("%Y-%m-%d %H:%M")

# 결과 출력 + DB 저장용 리스트 만들기
data_list = []
print(f"\n수집된 뉴스 수: {len(titles)}개\n")
print("=" * 70)

for i, title in enumerate(titles):
    headline = title.get_text(strip=True)
    time_text = times[i].get_text(strip=True) if i < len(times) else "시간 없음"
    press = press_list[i].get_text(strip=True) if i < len(press_list) else "언론사 없음"

    print(f"{i+1}. [{press}] {headline}")
    print(f"   {time_text}")
    print("-" * 70)

    data_list.append((now, press, headline, time_text))

# ============================
# 4단계: DB에 한 번에 저장
# ============================
insert_many_news(data_list)
print(f"\n✅ DB에 {len(data_list)}개 뉴스 저장 완료!")