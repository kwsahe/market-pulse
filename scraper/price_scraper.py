# scraper/price_scraper.py
# 다나와 게이밍 노트북 + PC 부품 가격/스펙/이미지 수집 스크래퍼
# 용량별 변형(8GB, 16GB, 32GB 등)도 각각 저장

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import init_db, insert_many_prices

# ============================
# 1단계: DB 초기화
# ============================
init_db()

# ============================
# 2단계: 검색 카테고리 설정
# ============================
CATEGORIES = {
    "게이밍 노트북": "게이밍+노트북",
    "DDR5 RAM": "DDR5+램",
    "NVMe SSD": "NVMe+SSD",
    "그래픽카드": "지포스+그래픽카드",
    "CPU": "CPU+프로세서",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

today = datetime.now().strftime("%Y-%m-%d")
total_count = 0


def extract_image(parent):
    """상품 블록에서 이미지 URL 추출"""
    img_url = ""

    # 1) src에 prod_img가 포함된 img 태그
    img_tag = parent.find("img", src=re.compile(r"prod_img"))
    if img_tag:
        img_url = img_tag.get("src", "")
    else:
        # 2) data-src 속성 확인 (지연 로딩)
        img_tag = parent.find("img", attrs={"data-src": re.compile(r"prod_img")})
        if img_tag:
            img_url = img_tag.get("data-src", "")
        else:
            # 3) data-original 속성 확인
            img_tag = parent.find("img", attrs={"data-original": re.compile(r"prod_img")})
            if img_tag:
                img_url = img_tag.get("data-original", "")

    if img_url and img_url.startswith("//"):
        img_url = "https:" + img_url

    return img_url


def extract_specs(parent):
    """상품 블록에서 스펙 텍스트 추출"""
    spec_div = parent.find("div", class_="spec_list")
    if spec_div:
        raw = spec_div.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", raw).strip()
    return ""


def find_product_block(tag):
    """태그의 상위 요소를 올라가며 상품 블록 찾기"""
    parent = tag
    for _ in range(10):
        if parent.parent:
            parent = parent.parent
        parent_class = " ".join(parent.get("class", []))
        if "product" in parent_class or "item" in parent_class or "main_prodlist" in parent_class:
            return parent
    return parent


def extract_variants(parent):
    """용량별 변형 추출 (RAM, SSD 등)
    
    prod_pricelist 안에 li 태그들이 용량별 변형이에요.
    각 li 안에 memory_sect(용량)과 price_sect(가격)이 있어요.
    
    반환: [(용량텍스트, 가격숫자), ...] 또는 빈 리스트
    """
    variants = []
    price_list = parent.find("div", class_="prod_pricelist")

    if not price_list:
        return variants

    items = price_list.find_all("li", id=re.compile(r"productInfoDetail_"))
    for item in items:
        # 용량 추출
        mem_sect = item.find("p", class_="memory_sect")
        if not mem_sect:
            continue
        mem_text_span = mem_sect.find("span", class_="text")
        if not mem_text_span:
            continue
        mem_text = mem_text_span.get_text(strip=True)

        # 가격 추출
        price_tag = item.find("a", class_="click_log_product_standard_price_")
        if not price_tag:
            continue
        price_text = price_tag.get_text(strip=True)
        try:
            price_num = int(price_text.replace(",", "").replace("원", ""))
        except ValueError:
            continue

        variants.append((mem_text, price_num))

    return variants


# ============================
# 3단계: 카테고리별 수집
# ============================
for category, query in CATEGORIES.items():
    url = f"https://search.danawa.com/dsearch.php?query={query}"
    response = requests.get(url, headers=headers)
    print(f"\n{'='*60}")
    print(f"📦 [{category}] 수집 중... (응답: {response.status_code})")
    print(f"{'='*60}")

    soup = BeautifulSoup(response.text, "html.parser")

    names = soup.find_all("a", class_="click_log_product_standard_title_")

    data_list = []
    for i, name_tag in enumerate(names):
        product = name_tag.get_text(strip=True)

        # 상품 블록 찾기
        block = find_product_block(name_tag)

        # 이미지 & 스펙 추출
        img_url = extract_image(block)
        specs = extract_specs(block)

        # 용량별 변형 확인
        variants = extract_variants(block)

        if variants:
            # 변형이 있으면 각 용량별로 따로 저장
            for mem_text, var_price in variants:
                full_name = f"{product} ({mem_text})"
                print(f"{i+1}. {full_name}")
                print(f"   가격: {var_price:,}원 | 이미지: {'✅' if img_url else '❌'}")
                data_list.append((today, category, full_name, var_price, specs, img_url))
        else:
            # 변형 없으면 기본 가격으로 저장
            price_tag = block.find("a", class_="click_log_product_standard_price_")
            if not price_tag:
                continue
            cost_text = price_tag.get_text(strip=True)
            try:
                cost_num = int(cost_text.replace(",", "").replace("원", ""))
            except ValueError:
                continue

            print(f"{i+1}. {product}")
            print(f"   가격: {cost_num:,}원 | 이미지: {'✅' if img_url else '❌'}")
            data_list.append((today, category, product, cost_num, specs, img_url))

        if specs:
            print(f"   스펙: {specs[:80]}...")

    # DB 저장
    if data_list:
        insert_many_prices(data_list)
        total_count += len(data_list)
        print(f"\n✅ [{category}] {len(data_list)}개 저장 완료!")
    else:
        print(f"\n⚠️ [{category}] 수집된 상품이 없어요.")

print(f"\n{'='*60}")
print(f"🎉 전체 {total_count}개 상품 수집 & 저장 완료!")
print(f"{'='*60}")