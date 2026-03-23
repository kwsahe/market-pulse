import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

# ============================
# 1단계: 웹페이지 가져오기
# ============================
URL = "https://search.danawa.com/dsearch.php?query=게이밍+노트북"

# 브라우저인 척 하기 (안 하면 차단당할 수 있음)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)
print(f"응답 상태: {response.status_code}")  # 200이면 성공!

# ============================
# 2단계: HTML 파싱 & 데이터 추출
# ============================
soup = BeautifulSoup(response.text, "html.parser")

# 상품명 전부 가져오기
names = soup.find_all("a", class_="click_log_product_standard_title_")

# 가격 전부 가져오기
prices = soup.find_all("a", class_="click_log_product_standard_price_")

# 결과 출력
print(f"\n수집된 상품 수: {len(names)}개\n")
print("-" * 60)

for i, (name, price) in enumerate(zip(names, prices), 1):
    product = name.get_text(strip=True)
    cost = price.get_text(strip=True)
    print(f"{i}. {product}")
    print(f"   가격: {cost}")
    print("-" * 60)

# ============================
# 3단계: CSV 파일로 저장
# ============================
today = datetime.now().strftime("%Y-%m-%d")

with open("database/prices.csv", "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # 파일이 비어있으면 헤더 추가
    f.seek(0, 2)  # 파일 끝으로 이동
    if f.tell() == 0:
        writer.writerow(["날짜", "상품명", "가격"])
    for name, price in zip(names, prices):
        product = name.get_text(strip=True)
        cost = price.get_text(strip=True)
        writer.writerow([today, product, cost])

print(f"\n✅ database/prices.csv에 {len(names)}개 상품 저장 완료!")
