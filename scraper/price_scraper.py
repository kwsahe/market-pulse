# scraper/price_scraper.py
# 다나와 게이밍 노트북 가격 수집 스크래퍼 (DB 저장 버전)

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

# database 폴더의 db_manager를 import하기 위한 경로 설정
# sys.path에 프로젝트 루트를 추가하면 다른 폴더의 모듈을 불러올 수 있어요
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, insert_many_prices

# ============================
# 1단계: DB 초기화 (테이블 없으면 생성)
# ============================
init_db()

# ============================
# 2단계: 웹페이지 가져오기
# ============================
URL = "https://search.danawa.com/dsearch.php?query=게이밍+노트북"

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

names = soup.find_all("a", class_="click_log_product_standard_title_")
prices = soup.find_all("a", class_="click_log_product_standard_price_")

today = datetime.now().strftime("%Y-%m-%d")

# 결과 출력 + DB 저장용 리스트 만들기
data_list = []
print(f"\n수집된 상품 수: {len(names)}개\n")
print("-" * 60)

for i, (name, price) in enumerate(zip(names, prices), 1):
    product = name.get_text(strip=True)
    cost_text = price.get_text(strip=True)

    # "1,947,890원" → 1947890 (숫자만 추출)
    # replace로 쉼표와 "원"을 제거하고 정수로 변환
    cost_num = int(cost_text.replace(",", "").replace("원", ""))

    print(f"{i}. {product}")
    print(f"   가격: {cost_text} → DB 저장: {cost_num}")
    print("-" * 60)

    data_list.append((today, product, cost_num))

# ============================
# 4단계: DB에 한 번에 저장
# ============================
insert_many_prices(data_list)
print(f"\n✅ DB에 {len(data_list)}개 상품 가격 저장 완료!")