# scraper/price_scraper.py
# 다나와 게이밍 노트북 + PC 부품 가격/스펙/이미지 수집 스크래퍼
# 중복 저장 방지 + 저장 결과 리포트

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import (
    init_db, insert_many_prices, load_prices,
    insert_many_laptop_prices, upsert_laptop_product,
    save_laptop_specs, save_laptop_images,
)
from scraper.laptop_detail_scraper import fetch_product_detail

# ============================
# 1단계: DB 초기화
# ============================
init_db()

# ============================
# 2단계: 검색 카테고리 설정
# ============================
# 게이밍 노트북은 RTX5080/5090에 초점을 맞춰 별도 수집 (collect_gaming_laptops 참고)
CATEGORIES = {
    "DDR5 RAM": "DDR5",
    "NVMe SSD": "NVMe+SSD",
    "그래픽카드": "지포스+그래픽카드",
    "CPU": "CPU+프로세서",
}

LAPTOP_CATEGORY = "게이밍 노트북"
LAPTOP_DEFAULT_CATE = "11252476"  # 게이밍 노트북 전체 (fallback)
LAPTOP_QUERIES = [
    ("RTX5080+노트북", "RTX5080"),
    ("RTX5090+노트북", "RTX5090"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

today = datetime.now().strftime("%Y-%m-%d")
total_count = 0
total_new = 0


IMG_URL_PATTERN = re.compile(r"prod_img|catalog-image")


def extract_image(parent):
    """상품 블록에서 이미지 URL 추출 (다나와 구 CDN(prod_img)/신 CDN(catalog-image) 모두 지원)"""
    img_url = ""
    for attr in ("src", "data-src", "data-original"):
        img_tag = parent.find("img", attrs={attr: IMG_URL_PATTERN})
        if img_tag:
            img_url = img_tag.get(attr, "")
            break
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
    """용량별 변형 추출"""
    variants = []
    price_list = parent.find("div", class_="prod_pricelist")
    if not price_list:
        return variants
    items = price_list.find_all("li", id=re.compile(r"productInfoDetail_"))
    for item in items:
        mem_sect = item.find("p", class_="memory_sect")
        if not mem_sect:
            continue
        mem_text_span = mem_sect.find("span", class_="text")
        if not mem_text_span:
            continue
        mem_text = mem_text_span.get_text(strip=True)
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


def extract_pcode(href):
    """상품 상세 링크에서 다나와 상품코드(pcode) 추출"""
    m = re.search(r"pcode=(\d+)", href or "")
    return m.group(1) if m else None


def extract_cate(href):
    """상품 상세 링크에서 카테고리 코드 추출 (상세페이지 스펙 조회에 필요)"""
    m = re.search(r"cate=(\d+)", href or "")
    return m.group(1) if m else LAPTOP_DEFAULT_CATE


def collect_gaming_laptops():
    """RTX5080/5090 게이밍 노트북 수집 — 목록 + 상세페이지(전체 스펙/이미지) 모두 저장"""
    print(f"\n{'='*60}")
    print(f"[+] [{LAPTOP_CATEGORY}] RTX5080/5090 수집 중...")
    print(f"{'='*60}")

    data_list = []
    seen_pcodes = set()

    for query, gpu_hint in LAPTOP_QUERIES:
        url = f"https://search.danawa.com/dsearch.php?query={query}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(f"[!] [{gpu_hint}] 요청 시간 초과 (15초). 건너뜁니다.")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[!] [{gpu_hint}] 네트워크 오류: {e}. 건너뜁니다.")
            continue

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            names = soup.find_all("a", class_="click_log_product_standard_title_")
        except Exception as e:
            print(f"⚠️ [{gpu_hint}] HTML 파싱 오류: {e}. 건너뜁니다.")
            continue

        for i, name_tag in enumerate(names):
            try:
                product = name_tag.get_text(strip=True)
                href = name_tag.get("href", "")
                pcode = extract_pcode(href)
                if not pcode or pcode in seen_pcodes:
                    continue
                seen_pcodes.add(pcode)
                cate = extract_cate(href)

                block = find_product_block(name_tag)
                img_url = extract_image(block)
                specs = extract_specs(block)
                variants = extract_variants(block)

                if variants:
                    for mem_text, var_price in variants:
                        full_name = f"{product} ({mem_text})"
                        print(f"{len(seen_pcodes)}. {full_name}")
                        data_list.append((today, LAPTOP_CATEGORY, full_name, var_price, specs, img_url, pcode))
                else:
                    price_tag = block.find("a", class_="click_log_product_standard_price_")
                    if not price_tag:
                        continue
                    cost_text = price_tag.get_text(strip=True)
                    try:
                        cost_num = int(cost_text.replace(",", "").replace("원", ""))
                    except ValueError:
                        continue
                    print(f"{len(seen_pcodes)}. {product}")
                    data_list.append((today, LAPTOP_CATEGORY, product, cost_num, specs, img_url, pcode))

                # 상세페이지: 전체 스펙 + 상세정보(홍보) 이미지 수집
                try:
                    detail = fetch_product_detail(pcode, cate)
                    gpu_model = detail["spec_dict"].get("GPU 칩셋", gpu_hint)
                    upsert_laptop_product(pcode, product, gpu_model, detail["detail_url"], detail["raw_spec_text"])
                    save_laptop_specs(pcode, detail["spec_dict"])

                    images = []
                    if img_url:
                        images.append((img_url, "main", 0))
                    images += [(u, "detail", idx + 1) for idx, u in enumerate(detail["detail_images"])]
                    save_laptop_images(pcode, images)

                    print(f"   상세: 스펙 {len(detail['spec_dict'])}개 | 이미지 {len(images)}개")
                    time.sleep(0.4)
                except Exception as e:
                    print(f"   [!] 상세정보 수집 실패 (pcode={pcode}): {e}")

            except Exception as e:
                print(f"   [!] 상품 파싱 오류: {e}. 건너뜁니다.")
                continue

    if data_list:
        new_count = insert_many_laptop_prices(data_list)
        print(f"\n[OK] [{LAPTOP_CATEGORY}] 수집: {len(data_list)}개 | 신규 저장: {new_count}개 | 고유 상품: {len(seen_pcodes)}개")
        return len(data_list), new_count
    else:
        print(f"\n[!] [{LAPTOP_CATEGORY}] 수집된 상품이 없어요.")
        return 0, 0


# ============================
# 3단계: 카테고리별 수집
# ============================
for category, query in CATEGORIES.items():
    url = f"https://search.danawa.com/dsearch.php?query={query}"
    print(f"\n{'='*60}")
    print(f"[+] [{category}] 수집 중...")
    print(f"{'='*60}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[!] [{category}] 요청 시간 초과 (15초). 건너뜁니다.")
        continue
    except requests.exceptions.RequestException as e:
        print(f"[!] [{category}] 네트워크 오류: {e}. 건너뜁니다.")
        continue

    print(f"   응답: {response.status_code}")

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        names = soup.find_all("a", class_="click_log_product_standard_title_")
    except Exception as e:
        print(f"⚠️ [{category}] HTML 파싱 오류: {e}. 건너뜁니다.")
        continue

    data_list = []
    for i, name_tag in enumerate(names):
        try:
            product = name_tag.get_text(strip=True)
            block = find_product_block(name_tag)
            img_url = extract_image(block)
            specs = extract_specs(block)
            variants = extract_variants(block)

            if variants:
                for mem_text, var_price in variants:
                    full_name = f"{product} ({mem_text})"
                    print(f"{i+1}. {full_name}")
                    img_status = "OK" if img_url else "NO"
                    print(f"   가격: {var_price:,}원 | 이미지: {img_status}")
                    data_list.append((today, category, full_name, var_price, specs, img_url))
            else:
                price_tag = block.find("a", class_="click_log_product_standard_price_")
                if not price_tag:
                    continue
                cost_text = price_tag.get_text(strip=True)
                try:
                    cost_num = int(cost_text.replace(",", "").replace("원", ""))
                except ValueError:
                    continue
                print(f"{i+1}. {product}")
                img_status = "OK" if img_url else "NO"
                print(f"   가격: {cost_num:,}원 | 이미지: {img_status}")
                data_list.append((today, category, product, cost_num, specs, img_url))

            if specs:
                print(f"   스펙: {specs[:80]}...")
        except Exception as e:
            print(f"   [!] 상품 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
            continue

    # DB 저장 (중복 무시)
    if data_list:
        new_count = insert_many_prices(data_list)
        total_count += len(data_list)
        total_new += new_count
        print(f"\n[OK] [{category}] 수집: {len(data_list)}개 | 신규 저장: {new_count}개 | 중복 건너뜀: {len(data_list) - new_count}개")
    else:
        print(f"\n[!] [{category}] 수집된 상품이 없어요.")

# ============================
# 4단계: 게이밍 노트북(RTX5080/5090) 수집
# ============================
laptop_count, laptop_new = collect_gaming_laptops()
total_count += laptop_count
total_new += laptop_new

print(f"\n{'='*60}")
print(f"[OK] 전체 수집: {total_count}개 | 신규 저장: {total_new}개 | 중복 건너뜀: {total_count - total_new}개")
print(f"{'='*60}")