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
    init_db, load_prices,
    insert_many_laptop_prices, upsert_laptop_product,
    save_laptop_specs, save_laptop_images, get_or_create_product_code,
    start_scrape_run, finish_scrape_run,
)
from scraper.laptop_detail_scraper import fetch_product_detail

# ============================
# 검색 카테고리 설정
# ============================
# 게이밍 노트북은 RTX5080/5090에 초점을 맞춰 별도 수집 (collect_gaming_laptops 참고)
CATEGORIES = {
    "DDR5 RAM": "DDR5",
    "NVMe SSD": "NVMe+SSD",
    "그래픽카드": "지포스+그래픽카드",
    "CPU": "CPU+프로세서",
    "게이밍 모니터": "게이밍모니터",
    "게이밍 키보드": "게이밍키보드",
    "게이밍 마우스": "게이밍마우스",
}

# 다나와 검색어에 "게이밍"이 들어가도 필터 효과가 거의 없어서(플레인 "모니터" 검색과 결과가 사실상 동일)
# 60~100Hz 사무용 모니터가 20%가량 섞여 들어온다. 스펙의 주사율로 한 번 더 거른다.
MIN_GAMING_REFRESH_HZ = 120
REFRESH_HZ_PATTERN = re.compile(r"(\d{2,4})\s*Hz")


def _is_gaming_monitor(product: str, specs: str) -> bool:
    """주사율 120Hz 이상만 게이밍 모니터로 인정. 주사율 표기가 없으면 제외한다."""
    match = REFRESH_HZ_PATTERN.search(specs)
    return bool(match) and int(match.group(1)) >= MIN_GAMING_REFRESH_HZ


# 키보드는 "방식"이 스펙에 100% 표기되므로 그걸로 거른다.
# 폴링레이트로 거르면 표기가 없는(11.5%) 로지텍 G512·CORSAIR K100 AIR 같은 진짜 게이밍 제품이 탈락한다.
GAMING_SWITCH_PATTERN = re.compile(r"기계식|무접점\s*\(")
OFFICE_SWITCH_PATTERN = re.compile(r"멤브레인|펜타그래프|플런저")


def _is_gaming_keyboard(product: str, specs: str) -> bool:
    """기계식 / 무접점(자석축·광축·정전용량)만 게이밍 키보드로 인정."""
    return bool(GAMING_SWITCH_PATTERN.search(specs)) and not OFFICE_SWITCH_PATTERN.search(specs)


# 마우스는 폴링레이트가 게이밍 여부를 가장 잘 가른다. 다만 22%가 미표기이고
# 그 안에 로지텍 G309 같은 진짜 게이밍 마우스가 섞여 있어, 미표기일 때만 DPI로 대신 판정한다.
MIN_GAMING_POLLING_HZ = 1000
MIN_GAMING_DPI = 8000
POLLING_HZ_PATTERN = re.compile(r"(\d{3,5})\s*Hz\s*폴링레이트")
DPI_PATTERN = re.compile(r"(\d{3,6})\s*DPI")


def _is_gaming_mouse(product: str, specs: str) -> bool:
    """폴링레이트 1000Hz 이상, 미표기면 DPI 8000 이상."""
    polling = POLLING_HZ_PATTERN.search(specs)
    if polling:
        return int(polling.group(1)) >= MIN_GAMING_POLLING_HZ
    dpi = DPI_PATTERN.search(specs)
    return bool(dpi) and int(dpi.group(1)) >= MIN_GAMING_DPI


# 카테고리별 추가 선별 규칙 — (상품명, 스펙) -> 수집할지 여부. 없으면 전부 수집한다.
CATEGORY_FILTERS = {
    "게이밍 모니터": _is_gaming_monitor,
    "게이밍 키보드": _is_gaming_keyboard,
    "게이밍 마우스": _is_gaming_mouse,
}

LAPTOP_CATEGORY = "게이밍 노트북"
LAPTOP_DEFAULT_CATE = "11252476"  # 게이밍 노트북 전체 (fallback)
LAPTOP_QUERIES = [
    ("RTX5080+노트북", "RTX5080"),
    ("RTX5090+노트북", "RTX5090"),
]

# AI 노트북(로컬 RAM으로 AI 구동 가능한 노트북) — 맥북 M5 시리즈 + 라이젠 AI Max(대용량 통합메모리)
AI_LAPTOP_CATEGORY = "AI 노트북"
AI_LAPTOP_DEFAULT_CATE = "11354187"  # 다나와 "AI 노트북" 카테고리 (fallback)
AI_LAPTOP_QUERIES = [
    ("M5+맥북", "Apple M5"),
    ("라이젠+AI+Max+노트북", "Ryzen AI Max"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

today = datetime.now().strftime("%Y-%m-%d")

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


def clean_name(tag) -> str:
    """상품명 추출 — 다나와가 검색어 토큰을 <b>로 감싸는 걸 감안한다.

    get_text(strip=True)는 텍스트 노드마다 공백을 없앤 뒤 이어붙여서
    '앱코 HACKER K640 축교환 <b>게이밍</b> <b>기계식</b> 블랙'을
    '앱코 HACKER K640 축교환게이밍기계식 블랙'으로 만든다. 상품명에 검색어가
    자주 들어가는 키보드/마우스에서 특히 심하고, 같은 상품이 검색어마다 다른
    이름으로 저장돼 상품명 기반 매칭이 깨진다. 구분자를 주고 공백을 정리한다."""
    return re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()


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


# 중고/병행수입 상품은 신품과 가격대가 달라서 같은 시계열에 섞으면 안 된다.
# 실측(키보드 200건): 23%가 '중고' 옵션을 갖고, 중고가는 신품 최저가보다 평균 16.8%,
# 최대 32% 싸다. 그대로 넣으면 카테고리 최저가·평균가와 가격 하락 알림이 전부 왜곡된다.
#
# 다나와는 이걸 두 군데에 흘려 놓는다 — prod_pricelist의 변형 라벨(예: '중고')과
# 상품명 자체(예: '삼성전자 PM981a M.2 NVMe 중고'). 두 경로가 다른 기준을 쓰면
# 한쪽만 새는 함정이라 같은 패턴을 공유한다.
#
# '벌크'는 절대 넣지 말 것 — 무포장 정품(새 제품)이고, 오히려 ml/price_prediction.py의
# extract_cpu_features가 is_bulk를 가격 특성으로 쓰고 있다.
# '리퍼'는 실제 표기가 '리퍼비시'라, '그리퍼' 같은 단어에 걸리지 않게 전체 형태로 적는다.
USED_PRODUCT_PATTERN = re.compile(r"중고|병행수입|해외구매|리퍼비시|리퍼브")


def _is_new_product(product: str) -> bool:
    """상품명에 중고/리퍼비시 표시가 없는(=신품 시세로 볼 수 있는) 상품인지."""
    return not USED_PRODUCT_PATTERN.search(product or "")


def extract_variants(parent):
    """용량별 변형 추출

    변형 라벨(memory_sect)이 비어 있는 상품은 변형으로 치지 않는다 — 모니터처럼
    옵션이 하나뿐인 상품군은 memory_sect 엘리먼트는 있는데 안이 공백이라,
    라벨을 그대로 붙이면 상품명이 "LG전자 24U411B ()" 꼴로 저장된다.
    중고/병행수입 라벨도 같이 걸러낸다.
    여기서 걸러내면 호출부의 `if variants:`가 False가 되어 일반 가격 경로로 폴백한다."""
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
        if not mem_text:
            continue
        if USED_PRODUCT_PATTERN.search(mem_text):
            continue
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


def extract_cate(href, default_cate=LAPTOP_DEFAULT_CATE):
    """상품 상세 링크에서 카테고리 코드 추출 (상세페이지 스펙 조회에 필요)"""
    m = re.search(r"cate=(\d+)", href or "")
    return m.group(1) if m else default_cate


def _has_unified_memory(spec_dict):
    """CPU/GPU/NPU가 하나의 메모리 풀을 공유하는 '통합메모리' 노트북인지 판별.
    애플 실리콘은 구조적으로 항상 통합메모리. AMD는 라이젠AI Max/Max+ 칩 + LPDDR5x 온보드
    조합일 때만 해당 — 이름에 'AI'가 들어간 일반 라이젠AI 7/9(DDR5, 일반 CPU+VRAM 분리 구조)는 제외.
    (다나와 검색이 "라이젠 AI Max"로 HP 오멘 MAX 시리즈 같은 무관한 상품명도 함께 잡아오기 때문에 필요)"""
    maker = spec_dict.get("CPU 제조사", "")
    cpu_detail = spec_dict.get("CPU 세분류", "")
    ram_type = spec_dict.get("램 타입", "")
    if "애플" in maker or "Apple" in maker:
        return True
    if "AI Max" in cpu_detail and ("LPDDR5x" in ram_type or "온보드" in ram_type):
        return True
    return False


def _collect_laptops(category, queries, default_cate, chip_spec_key="GPU 칩셋", validate_fn=None):
    """상세 스펙/이미지까지 수집하는 노트북 카테고리 공용 수집기
    (게이밍 노트북 RTX5080/5090, AI 노트북 등 pcode 기반 노트북 수집에 재사용)
    validate_fn(spec_dict)이 주어지면 상세 스펙을 먼저 확인해서 False면 통째로 건너뛴다."""
    print(f"\n{'='*60}")
    print(f"[+] [{category}] 수집 중...")
    print(f"{'='*60}")

    data_list = []
    seen_pcodes = set()
    new_products = []

    for query, chip_hint in queries:
        url = f"https://search.danawa.com/dsearch.php?query={query}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(f"[!] [{chip_hint}] 요청 시간 초과 (15초). 건너뜁니다.")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[!] [{chip_hint}] 네트워크 오류: {e}. 건너뜁니다.")
            continue

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            names = soup.find_all("a", class_="click_log_product_standard_title_")
        except Exception as e:
            print(f"⚠️ [{chip_hint}] HTML 파싱 오류: {e}. 건너뜁니다.")
            continue

        for i, name_tag in enumerate(names):
            try:
                product = clean_name(name_tag)
                href = name_tag.get("href", "")
                pcode = extract_pcode(href)
                if not pcode or pcode in seen_pcodes:
                    continue
                # 노트북은 리퍼비시가 특히 많이 섞여 들어온다(실측 34종) — 신품 시세만 남긴다
                if not _is_new_product(product):
                    print(f"   [SKIP] 중고/리퍼: {product[:50]}")
                    continue
                cate = extract_cate(href, default_cate=default_cate)

                block = find_product_block(name_tag)
                img_url = extract_image(block)
                specs = extract_specs(block)
                variants = extract_variants(block)

                # validate_fn이 있으면 상세 스펙부터 확인해서 조건에 안 맞으면 통째로 건너뛴다
                # (예: "라이젠 AI Max 노트북" 검색이 HP 오멘 MAX 시리즈처럼 이름만 비슷한 무관한 상품도 같이 잡아옴)
                detail = None
                if validate_fn:
                    try:
                        detail = fetch_product_detail(pcode, cate)
                    except Exception as e:
                        print(f"   [!] 상세정보 조회 실패 (pcode={pcode}): {e}. 건너뜁니다.")
                        continue
                    if not validate_fn(detail["spec_dict"]):
                        print(f"   [SKIP] 조건에 맞지 않아 제외: {product[:50]}")
                        continue

                seen_pcodes.add(pcode)

                if variants:
                    for mem_text, var_price in variants:
                        full_name = f"{product} ({mem_text})"
                        print(f"{len(seen_pcodes)}. {full_name}")
                        data_list.append((today, category, full_name, var_price, specs, img_url, pcode))
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
                    data_list.append((today, category, product, cost_num, specs, img_url, pcode))

                get_or_create_product_code(category, pcode, product)

                # 상세페이지: 전체 스펙 + 상세정보(홍보) 이미지 수집
                try:
                    if detail is None:
                        detail = fetch_product_detail(pcode, cate)
                    chip_model = detail["spec_dict"].get(chip_spec_key, chip_hint)
                    is_new = upsert_laptop_product(pcode, product, chip_model, detail["detail_url"], detail["raw_spec_text"])
                    if is_new:
                        new_products.append(product)
                        print(f"   [NEW] 신제품 발견!")
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
        print(f"\n[OK] [{category}] 수집: {len(data_list)}개 | 신규 저장: {new_count}개 | 고유 상품: {len(seen_pcodes)}개")
        if new_products:
            print(f"[NEW] 신제품 {len(new_products)}종 발견: {', '.join(new_products)}")
        return len(data_list), new_count
    else:
        print(f"\n[!] [{category}] 수집된 상품이 없어요.")
        return 0, 0


def collect_gaming_laptops():
    """RTX5080/5090 게이밍 노트북 수집 — 목록 + 상세페이지(전체 스펙/이미지) 모두 저장"""
    return _collect_laptops(LAPTOP_CATEGORY, LAPTOP_QUERIES, LAPTOP_DEFAULT_CATE, chip_spec_key="GPU 칩셋")


def collect_ai_laptops():
    """AI 노트북(통합메모리로 로컬 AI 구동 가능한 노트북만) 수집 — 애플 실리콘 / 라이젠AI Max·Max+(LPDDR5x 온보드)만 통과"""
    return _collect_laptops(
        AI_LAPTOP_CATEGORY, AI_LAPTOP_QUERIES, AI_LAPTOP_DEFAULT_CATE,
        chip_spec_key="CPU 세분류", validate_fn=_has_unified_memory,
    )


def _collect_parts_category(category: str, query: str) -> tuple[int, int]:
    """PC 부품(RAM/SSD/그래픽카드/CPU) 한 카테고리 수집"""
    url = f"https://search.danawa.com/dsearch.php?query={query}"
    print(f"\n{'='*60}")
    print(f"[+] [{category}] 수집 중...")
    print(f"{'='*60}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[!] [{category}] 요청 시간 초과 (15초). 건너뜁니다.")
        return 0, 0
    except requests.exceptions.RequestException as e:
        print(f"[!] [{category}] 네트워크 오류: {e}. 건너뜁니다.")
        return 0, 0

    print(f"   응답: {response.status_code}")

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        names = soup.find_all("a", class_="click_log_product_standard_title_")
    except Exception as e:
        print(f"⚠️ [{category}] HTML 파싱 오류: {e}. 건너뜁니다.")
        return 0, 0

    keep = CATEGORY_FILTERS.get(category)
    data_list = []
    registered = 0
    skipped = 0
    used_skipped = 0
    for i, name_tag in enumerate(names):
        try:
            product = clean_name(name_tag)
            href = name_tag.get("href", "")
            pcode = extract_pcode(href)
            block = find_product_block(name_tag)
            img_url = extract_image(block)
            specs = extract_specs(block)
            variants = extract_variants(block)

            # 선별 규칙은 상품번호 발급보다 먼저 — 걸러낸 상품에 번호가 나가면 안 된다
            if not _is_new_product(product):
                used_skipped += 1
                print(f"{i+1}. [SKIP] 중고/리퍼: {product[:50]}")
                continue
            if keep and not keep(product, specs):
                skipped += 1
                print(f"{i+1}. [SKIP] 카테고리 조건 미달: {product[:50]}")
                continue

            # 상품번호(RAM-1, SSD-1 ...)는 상세페이지(=pcode) 단위로 1개만 발급 —
            # 용량별 variant는 같은 pcode 상세페이지 안의 가격 옵션일 뿐, 별개 상품이 아님
            if pcode:
                get_or_create_product_code(category, pcode, product)
                registered += 1

            if variants:
                for mem_text, var_price in variants:
                    full_name = f"{product} ({mem_text})"
                    print(f"{i+1}. {full_name}")
                    img_status = "OK" if img_url else "NO"
                    print(f"   가격: {var_price:,}원 | 이미지: {img_status}")
                    data_list.append((today, category, full_name, var_price, specs, img_url, pcode))
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
                data_list.append((today, category, product, cost_num, specs, img_url, pcode))

            if specs:
                print(f"   스펙: {specs[:80]}...")
        except Exception as e:
            print(f"   [!] 상품 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
            continue

    # DB 저장 (중복 무시)
    skip_note = f" | 조건 미달 제외: {skipped}개" if skipped else ""
    skip_note += f" | 중고/리퍼 제외: {used_skipped}개" if used_skipped else ""
    if data_list:
        new_count = insert_many_laptop_prices(data_list)
        print(f"\n[OK] [{category}] 수집: {len(data_list)}개 | 신규 저장: {new_count}개 | 상품번호 등록: {registered}개 | 중복 건너뜀: {len(data_list) - new_count}개{skip_note}")
        return len(data_list), new_count
    else:
        print(f"\n[!] [{category}] 수집된 상품이 없어요.{skip_note}")
        return 0, 0


def main() -> None:
    init_db()
    run_id = start_scrape_run("price")

    total_count = 0
    total_new = 0

    try:
        # ============================
        # 1단계: 카테고리별(RAM/SSD/그래픽카드/CPU) 수집
        # ============================
        for category, query in CATEGORIES.items():
            count, new_count = _collect_parts_category(category, query)
            total_count += count
            total_new += new_count

        # ============================
        # 2단계: 게이밍 노트북(RTX5080/5090) 수집
        # ============================
        laptop_count, laptop_new = collect_gaming_laptops()
        total_count += laptop_count
        total_new += laptop_new

        # ============================
        # 3단계: AI 노트북(맥북 M5 / 라이젠 AI Max) 수집
        # ============================
        ai_laptop_count, ai_laptop_new = collect_ai_laptops()
        total_count += ai_laptop_count
        total_new += ai_laptop_new
    except Exception as e:
        finish_scrape_run(run_id, total_count, total_new, status="failed", error_message=str(e))
        raise

    finish_scrape_run(run_id, total_count, total_new, status="success")

    print(f"\n{'='*60}")
    print(f"[OK] 전체 수집: {total_count}개 | 신규 저장: {total_new}개 | 중복 건너뜀: {total_count - total_new}개")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()