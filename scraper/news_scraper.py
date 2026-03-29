# scraper/news_scraper.py
# 네이버 IT/과학 뉴스 수집 스크래퍼 (DB 저장 버전)
 
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import sys
import os
 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, insert_many_news
 
# ============================
# 1단계: DB 초기화
# ============================
init_db()
 
 
# ============================
# 헬퍼 함수: "48분전" → "2026-03-29 14:12"
# ============================
def parse_relative_time(time_text):
    """상대 시간을 실제 날짜/시간으로 변환
    
    "48분전" → 현재 시간에서 48분 빼기
    "3시간전" → 현재 시간에서 3시간 빼기
    "1일전" → 현재 시간에서 1일 빼기
    
    re.search(r"(\d+)", text)는 텍스트에서 숫자만 뽑아내요.
    "48분전" → 48, "3시간전" → 3
    """
    now = datetime.now()
 
    # 숫자 추출
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
 
now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
 
# 결과 출력 + DB 저장용 리스트
data_list = []
print(f"\n수집된 뉴스 수: {len(titles)}개\n")
print("=" * 70)
 
for i, title in enumerate(titles):
    headline = title.get_text(strip=True)
    time_text = times[i].get_text(strip=True) if i < len(times) else ""
    press = press_list[i].get_text(strip=True) if i < len(press_list) else "언론사 없음"
 
    # 상대 시간 → 실제 시간 변환
    published = parse_relative_time(time_text)
 
    print(f"{i+1}. [{press}] {headline}")
    print(f"   {time_text} → {published}")
    print("-" * 70)
 
    data_list.append((now_str, press, headline, published))
 
# ============================
# 4단계: DB에 저장
# ============================
insert_many_news(data_list)
print(f"\n✅ DB에 {len(data_list)}개 뉴스 저장 완료!")