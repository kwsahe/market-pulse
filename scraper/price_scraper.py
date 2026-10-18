# scraper/price_scraper.py
# 다나와 게이밍 노트북 + PC 부품 가격/스펙/이미지 수집 스크래퍼
# 중복 저장 방지 + 저장 결과 리포트

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import statistics
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import (
    init_db, load_prices,
    insert_many_laptop_prices, upsert_laptop_product,
    save_laptop_specs, save_laptop_images, get_or_create_product_code, match_key_for,
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
    # 검색어에 "프로세서"를 넣으면 안 된다 — 다나와가 그걸 스마트폰·태블릿의 AP(엑시노스·
    # 디멘시티 등) 스펙에 매칭시켜서, 2026-08-19까지 104~138행이던 CPU 수집이 09-03에
    # 진짜 CPU 2행 + 폰/태블릿 84행으로 뒤집혔다. 실측: "CPU+프로세서"는 40개 중 1개만
    # 진짜 CPU고, "CPU"는 40개 전부 진짜 CPU다(인텔·AMD 섞여서 나온다).
    "CPU": "CPU",
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


# 다나와 "CPU 프로세서" 검색에는 스마트폰·태블릿이 섞여 들어온다. 검색어에 CPU가 들어가도
# 소용없는 게, 다나와가 기기의 AP(엑시노스·디멘시티·Helio 등)를 CPU로 쳐서 같이 물어온다.
# 실측(누적 373종): 84종(22.5%)이 스마트폰·태블릿이었고, 갤럭시 퀀텀7 단말할인가 154,900원이
# CPU 카테고리 최저가로 잡혀 평균가와 최저가 통계를 흔들었다.
#
# 데스크탑 CPU는 소켓 규격이 스펙에 100% 표기된다(인텔(소켓1700)·AMD(소켓AM5) 꼴).
# 반대로 스마트폰·태블릿은 소켓이라는 개념 자체가 없다. 실측상 이 한 조건으로 완전히 갈렸다 —
# 소켓 표기 289종은 전부 데스크탑 CPU, 미표기 84종은 전부 스마트폰(40)·태블릿(44)이었다.
CPU_SOCKET_PATTERN = re.compile(r"소켓")


def _is_cpu(product: str, specs: str) -> bool:
    """소켓 규격이 표기된 데스크탑 CPU만 인정. 표기가 없으면 제외한다."""
    return bool(CPU_SOCKET_PATTERN.search(specs or ""))


# 카테고리별 추가 선별 규칙 — (상품명, 스펙) -> 수집할지 여부. 없으면 전부 수집한다.
CATEGORY_FILTERS = {
    "CPU": _is_cpu,
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

# ── robots.txt 준수 플래그 ────────────────────────────────────────
# prod.danawa.com/robots.txt 는 /info/ajax/ 를 명시적으로 금지한다(Disallow: /info/ajax/).
# laptop_detail_scraper.fetch_product_detail 이 정확히 그 경로를 POST 하는데,
# 사람이 가끔 손으로 돌리는 것과 매일 무인으로 도는 배치가 치는 것은 성격이 다르므로
# 스케줄러 등록에 맞춰 기본값을 끔으로 둔다.
#
# 끄면 잃는 것 (대체 경로가 없다 — 스펙표·상세이미지가 전부 그 ajax 응답에만 있고,
# 허용된 /info/?pcode= 페이지는 ajax 호출 파라미터만 제공한다):
#   - AI 노트북 카테고리 전체: 수집 여부 판정이 상세 스펙에 의존해서, 검증 없이 담으면
#     이름만 비슷한 무관한 상품이 섞인다(CPU가 폰·태블릿으로 오염된 것과 같은 실패다).
#   - 신규 노트북의 상세 스펙/상세 이미지. 이미 모아둔 176종분은 그대로 보존된다.
#
# 다시 켜려면: 환경변수 MARKET_PULSE_FETCH_LAPTOP_DETAIL=1
FETCH_LAPTOP_DETAIL = os.getenv("MARKET_PULSE_FETCH_LAPTOP_DETAIL", "0") == "1"

# search.danawa.com/robots.txt 의 Crawl-delay: 10 을 지킨다.
# 지금까지 카테고리 검색 9건이 간격 없이 연속 발사됐다(국내 가정용 IP라 넘어갔을 뿐이다).
SEARCH_CRAWL_DELAY_SEC = 10
DETAIL_CRAWL_DELAY_SEC = 1.5


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

today = datetime.now().strftime("%Y-%m-%d")

IMG_URL_PATTERN = re.compile(r"prod_img|catalog-image")


_last_search_ts = 0.0


def _search_get(url):
    """search.danawa.com 검색 요청. robots.txt의 Crawl-delay: 10 을 강제한다."""
    global _last_search_ts
    wait = SEARCH_CRAWL_DELAY_SEC - (time.monotonic() - _last_search_ts)
    if wait > 0:
        print(f"   (crawl-delay 대기 {wait:.0f}초)")
        time.sleep(wait)
    response = requests.get(url, headers=headers, timeout=15)
    _last_search_ts = time.monotonic()
    return response


# 다나와가 2026-10-07부터 검색 요청 일부를 개편된 새 검색 UI(search.danawa.com/?query=)로 무작위
# 리다이렉트한다(서버 307, 쿠키 없음, 검색어 무관). 옛 UI가 올 때까지 재요청하던 우회는 비율이
# 20~35%에서 25~67%(2026-10-18)로 오르자 10-16 NVMe SSD, 10-18 그래픽카드를 통째로 놓쳤다.
# 그래서 두 UI를 모두 읽는다. 새 UI도 서버 렌더링이라 상품 목록이 HTML 안 self.__next_f
# 페이로드에 JSON으로 실려 온다(금지 경로인 /api_ui/ 는 부르지 않는다).
#
# 같은 시각 두 UI로 받은 11개 검색어 전체에서 저장될 행(상품명+옵션 라벨, 가격, pcode)이 전부 같았다.
# 가격은 minPrice(배송비 제외)가 옛 UI와 일치한다 — totalPrice는 배송비 포함이라 다르다.
# 스펙 문구는 표기가 조금 다르지만('램타이밍 : ' → '램타이밍: ', 항목 몇 개 추가) 카테고리 필터와
# 가격 예측 특성은 같은 값이 나왔다. 그래서 어느 UI가 와도 같은 행이 저장되고 이력이 이어진다.
OLD_SEARCH_UI_MARKER = "click_log_product_standard_title_"
_NEXT_F_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


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


# 다나와에는 실판매가가 아닌 미끼/옵션 가격이 드물게 섞여 들어온다.
# 실측(2026-09-03): 삼성전자 990 EVO Plus 4TB가 10,000원으로 내려왔다. 다나와가 같은 줄에
# 찍어주는 단가가 3원/1GB인데, 같은 상품의 2TB는 258원/1GB, 1TB는 328원/1GB다.
# 이 한 행이 가격 변동 리포트에서 -99.06%로 1위를 차지해 진짜 변동을 전부 가렸다.
#
# 카테고리 전체 분포로는 못 잡는다 — 8TB SSD(393만원)나 128GB SSD(5.7만원)처럼
# 정상 상품의 가격대가 워낙 넓어서, 카테고리 기준 하한선은 정상 상품부터 자른다.
# 대신 "같은 상품(pcode)의 다른 변형"과 비교하면 깨끗하게 갈린다.
#
# 임계값 5%는 기존 수집분 전체(비교 가능한 변형 10,699행)로 맞췄다. 이 값을 넘겨 걸리는 건
# 위 미끼가 1건(0.85%)뿐이고, 가장 낮은 정상 행은 인텔 14900K 벌크(9.63%)라 여유가 있다.
# 10%까지 올리면 그 벌크 상품이 같이 잘린다 — 벌크는 무포장 정품이라 남겨야 한다.
BOGUS_PRICE_RATIO = 0.05

_CAPACITY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(TB|GB)", re.I)


def _capacity_gb(label: str):
    """변형 라벨에서 용량을 GB로 환산. 용량 토큰이 정확히 하나일 때만 신뢰한다.

    노트북 라벨('램64GB, SSD 2TB')처럼 둘 이상이면 어느 쪽으로 정규화할지 알 수 없고,
    '벌크'·'적축'처럼 아예 없으면 애초에 용량 상품이 아니다. 둘 다 None으로 돌려서
    호출부가 단가 대신 원가격으로 비교하게 만든다."""
    found = _CAPACITY_PATTERN.findall(label or "")
    if len(found) != 1:
        return None
    number, unit = found[0]
    return float(number) * (1024 if unit.upper() == "TB" else 1)


def _drop_bogus_variant_prices(variants):
    """같은 상품의 다른 변형에 비해 터무니없이 싼 변형(미끼가)을 걸러낸다.

    모든 라벨에서 용량이 하나씩 잡히면 1GB당 단가로 비교한다. 원가격끼리 비교하면
    1TB와 8TB처럼 용량 차가 큰 정상 변형이 걸릴 수 있어서다. 하나라도 용량을 못 읽으면
    (키보드 축, CPU 벌크 등) 원가격으로 비교한다 — 그런 라벨은 용량 상품이 아니라
    변형 간 가격 차이가 애초에 크지 않다.

    비교 기준은 '자기를 뺀 나머지의 중앙값'이다. 평균을 쓰면 미끼가 자신이 기준을
    끌어내려서 정작 본인이 안 걸린다."""
    if len(variants) < 2:
        return variants  # 비교할 형제가 없으면 판단 근거도 없다

    capacities = [_capacity_gb(label) for label, _ in variants]
    by_unit_price = all(capacity for capacity in capacities)
    metrics = [
        price / capacities[i] if by_unit_price else float(price)
        for i, (_, price) in enumerate(variants)
    ]

    kept = []
    for i, (label, price) in enumerate(variants):
        others = [m for j, m in enumerate(metrics) if j != i]
        baseline = statistics.median(others)
        if baseline > 0 and metrics[i] < baseline * BOGUS_PRICE_RATIO:
            print(f"   [SKIP] 미끼가 의심 제외: {label} {price:,}원")
            continue
        kept.append((label, price))
    return kept


# 카테고리 기준으로 말이 안 되는 가격. 위의 미끼가 필터는 같은 상품의 다른 옵션과 비교하므로
# 옵션이 하나뿐인 상품은 못 본다. 실측(2026-09-29~): '앱코 HACKER A660 마우스 (화이트)'가
# 판매처 1곳("1몰")의 잘못된 가격 439,824,000원으로 5번 연속 수집돼 마우스 평균가를 708만원으로 만들었다.
#
# 같은 상품의 직전 가격과 비교하지 않는 이유: 다나와 최저가는 판매처가 바뀌면 2.5~5배씩 실제로
# 움직이고 그 수준이 유지되기도 해서(삼성 T7 500GB 40만↔192만), 직전 가격 기준으로 거르면
# 정상적인 큰 변동이 매일 거부되어 그 상품이 영영 갱신되지 않는다. 그래서 '자릿수가 다른' 수준만 거른다.
#
# 100배는 누적 데이터로 맞췄다: 정상 상품 중 가장 비싼 스레드리퍼 PRO 9995WX(1,836만원)가 CPU 중앙값의
# 약 55배, 문제의 마우스는 7,094~7,236배였다. 싼 쪽으로 1/100 미만은 중고 펜티엄(3,720원)뿐이었다.
ABSURD_PRICE_RATIO = 100


def _is_absurd_price(price: int, median: float) -> bool:
    return median > 0 and (price > median * ABSURD_PRICE_RATIO or price * ABSURD_PRICE_RATIO < median)


def _drop_absurd_prices(data_list: list) -> list:
    """저장 직전 카테고리 한 묶음에서, 묶음 중앙값의 100배 넘게 비싸거나 1/100 미만으로 싼 행을 뺀다.
    행 형식은 insert_many_laptop_prices 와 같다: (date, category, name, price, specs, img, pcode)."""
    if not data_list:
        return data_list
    median = statistics.median(row[3] for row in data_list)
    kept = []
    for row in data_list:
        if _is_absurd_price(row[3], median):
            print(f"   [SKIP] 비정상 가격 제외: {row[2][:50]} {row[3]:,}원 (카테고리 중앙값 {median:,.0f}원)")
            continue
        kept.append(row)
    return kept


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
    return _drop_bogus_variant_prices(variants)


def extract_pcode(href):
    """상품 상세 링크에서 다나와 상품코드(pcode) 추출"""
    m = re.search(r"pcode=(\d+)", href or "")
    return m.group(1) if m else None


def extract_cate(href, default_cate=LAPTOP_DEFAULT_CATE):
    """상품 상세 링크에서 카테고리 코드 추출 (상세페이지 스펙 조회에 필요)"""
    m = re.search(r"cate=(\d+)", href or "")
    return m.group(1) if m else default_cate


def _price_number(tag):
    """'129,000원' 가격 태그 → 129000. 태그가 없거나 숫자가 아니면 None."""
    if not tag:
        return None
    try:
        return int(tag.get_text(strip=True).replace(",", "").replace("원", ""))
    except ValueError:
        return None


# 검색 결과 상품 하나: product(상품명) / href(상세 링크, pcode·cate를 품음) / img_url / specs /
# variants([(옵션 라벨, 가격)], 중고·미끼가 제외) / price(옵션이 없을 때의 가격, 없으면 None)
def _old_ui_items(html):
    items = []
    for i, tag in enumerate(BeautifulSoup(html, "html.parser").find_all("a", class_=OLD_SEARCH_UI_MARKER)):
        try:
            block = find_product_block(tag)
            variants = extract_variants(block)
            items.append({
                "product": clean_name(tag), "href": tag.get("href", ""),
                "img_url": extract_image(block), "specs": extract_specs(block), "variants": variants,
                "price": None if variants else _price_number(block.find("a", class_="click_log_product_standard_price_")),
            })
        except Exception as e:
            print(f"   [!] 상품 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
    return items


def _html_text(fragment):
    """새 UI가 HTML 조각으로 주는 값(검색어 <b> 강조 등)을 옛 UI와 같은 규칙(clean_name)으로 글자만 남긴다.
    규칙이 다르면 '<b>DDR5</b>-6000'이 'DDR5-6000'/'DDR5 -6000'으로 갈려 같은 상품이 다른 이름이 된다."""
    return clean_name(BeautifulSoup(fragment or "", "html.parser"))


def _new_ui_items(html):
    payload = "".join(json.loads(chunk) for chunk in _NEXT_F_CHUNK.findall(html))
    m = re.search(r'"products"\s*:\s*\[', payload)
    if not m:
        return []  # 구조가 또 바뀐 것 — 0개로 끝나고 verify_last_scrape 가드가 카테고리 소멸로 잡는다
    items = []
    for i, p in enumerate(json.JSONDecoder().raw_decode(payload, m.end() - 1)[0]):
        # prodType 1 = 다나와 가격비교 상품(옛 UI 목록과 정확히 같은 집합). 3은 오픈마켓 중개 링크라
        # pcode가 없고 맥북 케이스 같은 무관한 상품이 섞인다 — 옛 UI에는 아예 안 나오던 것들이다.
        if p.get("prodType") != 1:
            continue
        try:
            summary = p.get("summary") or {}
            desc, bridge = summary.get("desc") or [], summary.get("descBridge") or []
            spec_html = "".join(d + (bridge[j] if j < len(bridge) else "") for j, d in enumerate(desc))
            bundles = [(b.get("bundleName") or "", b.get("minPrice")) for b in p.get("bundleList") or []]
            if not bundles and p.get("bundleName"):
                # 옵션이 하나뿐인 상품도 옛 UI는 라벨을 붙였다 — "PATRIOT ... 블랙 (16GB)"
                bundles = [(p["bundleName"], p.get("minPrice"))]
            variants = _drop_bogus_variant_prices(
                [(label, price) for label, price in bundles
                 if label and price and not USED_PRODUCT_PATTERN.search(label)])
            items.append({
                "product": _html_text(p.get("productName")), "href": p.get("linkUrl", ""),
                # 새 UI는 '?v=수정시각'을 붙인다 — 그대로 두면 laptop_images(pcode, image_url)에 매일 새 행이 쌓인다
                "img_url": (p.get("imageUrl") or "").split("?")[0], "specs": _html_text(spec_html),
                "variants": variants, "price": None if variants else p.get("minPrice"),
            })
        except Exception as e:
            print(f"   [!] 상품 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
    return items


def _search_items(html):
    """검색 결과 HTML → 상품 목록. 옛 UI/새 UI 어느 쪽이 와도 같은 형식으로 돌려준다."""
    if OLD_SEARCH_UI_MARKER in html:
        return _old_ui_items(html)
    items = _new_ui_items(html)
    print(f"   (새 검색 UI로 응답 — {len(items)}개 읽음)")
    return items


# 통합메모리 판정 — 검색 결과 페이지의 스펙 문자열만 쓴다.
#
# 예전에는 상세페이지 ajax 응답의 spec_dict(CPU 제조사 / CPU 세분류 / 램 타입)를 봤는데,
# 그 경로가 robots 금지(/info/ajax/)라 상세 수집을 끄면 AI 노트북을 통째로 못 모았다.
# 검색 페이지 스펙에도 같은 정보가 그대로 실려 있어서 허용 경로만으로 판정이 된다.
#
# 실측 검증: 검색 결과 70건 중 정답이 확정된 69건(통과 50 / 탈락 19)에 대해
# 아래 판정기가 ajax 기반 판정과 100% 일치했다 (오탐 0, 누락 0).
#   통과 예) "... / 애플(ARM) / M5 / ... / Apple Intelligence"
#           "... / AMD / 라이젠 AI Max + / 395 / 50TOPS / Radeon 8060S / ..."
#   탈락 예) "... / AMD / 라이젠 AI 9 / HX 375 / 55TOPS / RTX5070 Ti / VRAM: 12GB / ..."
# 핵심 구분점은 "라이젠 AI Max"(통합메모리)와 "라이젠 AI 7/9"(외장 VRAM 분리 구조)다.
UNIFIED_APPLE_PATTERN = re.compile(r"애플\(ARM\)|애플 실리콘")
UNIFIED_AMD_PATTERN = re.compile(r"라이젠\s*AI\s*Max")


def _has_unified_memory(product: str, specs: str) -> bool:
    """CPU/GPU/NPU가 하나의 메모리 풀을 공유하는 '통합메모리' 노트북인지 판별.

    애플 실리콘은 구조적으로 항상 통합메모리. AMD는 라이젠AI Max/Max+ 칩일 때만 해당 —
    이름에 'AI'가 들어간 일반 라이젠AI 7/9는 외장 VRAM 분리 구조라 제외한다.
    (다나와 "라이젠 AI Max" 검색이 HP 오멘 MAX 시리즈 같은 무관한 상품도 함께 잡아온다)"""
    text = specs or ""
    return bool(UNIFIED_APPLE_PATTERN.search(text) or UNIFIED_AMD_PATTERN.search(text))


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
            response = _search_get(url)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(f"[!] [{chip_hint}] 요청 시간 초과 (15초). 건너뜁니다.")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[!] [{chip_hint}] 네트워크 오류: {e}. 건너뜁니다.")
            continue

        try:
            items = _search_items(response.text)
        except Exception as e:
            print(f"⚠️ [{chip_hint}] HTML 파싱 오류: {e}. 건너뜁니다.")
            continue

        for item in items:
            try:
                product = item["product"]
                href = item["href"]
                pcode = extract_pcode(href)
                if not pcode or pcode in seen_pcodes:
                    continue
                # 노트북은 리퍼비시가 특히 많이 섞여 들어온다(실측 34종) — 신품 시세만 남긴다
                if not _is_new_product(product):
                    print(f"   [SKIP] 중고/리퍼: {product[:50]}")
                    continue
                cate = extract_cate(href, default_cate=default_cate)

                img_url = item["img_url"]
                specs = item["specs"]
                variants = item["variants"]

                # 판정은 검색 페이지 스펙만으로 한다 — 상세 요청보다 먼저 걸러서
                # 탈락할 상품에 요청을 낭비하지 않고, robots 금지 경로에도 의존하지 않는다.
                # (예: "라이젠 AI Max 노트북" 검색이 HP 오멘 MAX 시리즈처럼 이름만 비슷한 무관한 상품도 같이 잡아옴)
                detail = None
                if validate_fn and not validate_fn(product, specs):
                    print(f"   [SKIP] 조건에 맞지 않아 제외: {product[:50]}")
                    continue

                seen_pcodes.add(pcode)

                if variants:
                    for mem_text, var_price in variants:
                        full_name = f"{product} ({mem_text})"
                        print(f"{len(seen_pcodes)}. {full_name}")
                        data_list.append((today, category, full_name, var_price, specs, img_url, pcode))
                else:
                    cost_num = item["price"]
                    if cost_num is None:
                        continue
                    print(f"{len(seen_pcodes)}. {product}")
                    data_list.append((today, category, product, cost_num, specs, img_url, pcode))

                get_or_create_product_code(category, pcode, product)

                # 상세페이지: 전체 스펙 + 상세정보(홍보) 이미지 수집
                # robots 금지 경로(/info/ajax/)를 쓰므로 플래그가 꺼져 있으면 통째로 건너뛴다.
                # 이때도 laptop_products 에는 등록해서 [NEW] 신제품 판별은 계속 동작하게 한다.
                # (빈 raw_spec_text 로 기존 값을 덮지 않도록 upsert 쪽에 보존 패치가 들어가 있다)
                if not FETCH_LAPTOP_DETAIL:
                    detail_url = f"https://prod.danawa.com/info/?pcode={pcode}&cate={cate}"
                    is_new = upsert_laptop_product(pcode, product, chip_hint, detail_url, "")
                    if is_new:
                        new_products.append(product)
                        print(f"   [NEW] 신제품 발견! (상세 스펙은 수집하지 않음)")
                    if img_url:
                        save_laptop_images(pcode, [(img_url, "main", 0)])
                    continue

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
                    time.sleep(DETAIL_CRAWL_DELAY_SEC)
                except Exception as e:
                    print(f"   [!] 상세정보 수집 실패 (pcode={pcode}): {e}")

            except Exception as e:
                print(f"   [!] 상품 파싱 오류: {e}. 건너뜁니다.")
                continue

    data_list = _drop_absurd_prices(data_list)
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
        response = _search_get(url)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"[!] [{category}] 요청 시간 초과 (15초). 건너뜁니다.")
        return 0, 0
    except requests.exceptions.RequestException as e:
        print(f"[!] [{category}] 네트워크 오류: {e}. 건너뜁니다.")
        return 0, 0

    print(f"   응답: {response.status_code}")

    try:
        items = _search_items(response.text)
    except Exception as e:
        print(f"⚠️ [{category}] HTML 파싱 오류: {e}. 건너뜁니다.")
        return 0, 0

    keep = CATEGORY_FILTERS.get(category)
    data_list = []
    registered = 0
    skipped = 0
    used_skipped = 0
    for i, item in enumerate(items):
        try:
            product = item["product"]
            pcode = extract_pcode(item["href"])
            img_url = item["img_url"]
            specs = item["specs"]
            variants = item["variants"]

            # 선별 규칙은 상품번호 발급보다 먼저 — 걸러낸 상품에 번호가 나가면 안 된다
            if not _is_new_product(product):
                used_skipped += 1
                print(f"{i+1}. [SKIP] 중고/리퍼: {product[:50]}")
                continue
            if keep and not keep(product, specs):
                skipped += 1
                print(f"{i+1}. [SKIP] 카테고리 조건 미달: {product[:50]}")
                continue

            first_row = len(data_list)
            if variants:
                for mem_text, var_price in variants:
                    full_name = f"{product} ({mem_text})"
                    print(f"{i+1}. {full_name}")
                    img_status = "OK" if img_url else "NO"
                    print(f"   가격: {var_price:,}원 | 이미지: {img_status}")
                    data_list.append((today, category, full_name, var_price, specs, img_url, pcode))
            else:
                cost_num = item["price"]
                if cost_num is None:
                    continue
                print(f"{i+1}. {product}")
                img_status = "OK" if img_url else "NO"
                print(f"   가격: {cost_num:,}원 | 이미지: {img_status}")
                data_list.append((today, category, product, cost_num, specs, img_url, pcode))

            # 상품번호(RAM-1, SSD-1 ...)는 가격 행(용량 변형) 단위로 발급 — 1TB/4TB는 가격이 따로 움직이는
            # 별개 SKU라, pcode 하나로 묶으면 변동 TOP의 4TB가 상세페이지에선 1TB로 열린다
            if pcode:
                for row in data_list[first_row:]:
                    get_or_create_product_code(category, match_key_for(category, pcode, row[2]), row[2])
                    registered += 1

            if specs:
                print(f"   스펙: {specs[:80]}...")
        except Exception as e:
            print(f"   [!] 상품 #{i+1} 파싱 오류: {e}. 건너뜁니다.")
            continue

    # DB 저장 (중복 무시)
    skip_note = f" | 조건 미달 제외: {skipped}개" if skipped else ""
    skip_note += f" | 중고/리퍼 제외: {used_skipped}개" if used_skipped else ""
    data_list = _drop_absurd_prices(data_list)
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