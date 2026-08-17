# tests/test_price_scraper.py
# 네트워크 없이 순수 파싱/선별 로직만 검증한다 (다나와 HTML 조각을 직접 만들어 넣는다).

from bs4 import BeautifulSoup

from scraper.price_scraper import (
    _is_gaming_keyboard, _is_gaming_monitor, _is_gaming_mouse, _is_new_product,
    clean_name, extract_variants,
)


def block(html: str):
    return BeautifulSoup(html, "html.parser")


VARIANT_HTML = """
<div class="prod_pricelist"><ul>
  <li id="productInfoDetail_1">
    <p class="memory_sect"><span class="text">1TB</span></p>
    <a class="click_log_product_standard_price_">129,000원</a>
  </li>
  <li id="productInfoDetail_2">
    <p class="memory_sect"><span class="text">2TB</span></p>
    <a class="click_log_product_standard_price_">228,000원</a>
  </li>
</ul></div>
"""

# 모니터처럼 옵션이 하나뿐인 상품군 — memory_sect는 있는데 라벨이 공백이다
EMPTY_LABEL_HTML = """
<div class="prod_pricelist"><ul>
  <li id="productInfoDetail_1">
    <p class="memory_sect"><span class="text">
    </span></p>
    <a class="click_log_product_standard_price_">178,000원</a>
  </li>
</ul></div>
"""


def test_extract_variants_reads_labelled_options():
    assert extract_variants(block(VARIANT_HTML)) == [("1TB", 129000), ("2TB", 228000)]


def test_extract_variants_drops_blank_labels():
    """빈 라벨을 변형으로 치면 상품명이 "LG전자 24U411B ()" 꼴로 저장된다.
    빈 목록을 돌려줘야 호출부가 일반 가격 경로로 폴백한다."""
    assert extract_variants(block(EMPTY_LABEL_HTML)) == []


def test_extract_variants_without_pricelist():
    assert extract_variants(block("<div class='item'></div>")) == []


GAMING_SPEC = "모니터 / 68.6cm(27인치) / QHD(2560 x 1440) / 240Hz / Fast IPS / 와이드(16:9) / 0.3ms(MPRT)"
OFFICE_SPEC = "모니터 / 80cm(32인치) / 4K UHD(3840 x 2160) / 60Hz / VA / 와이드(16:9) / 4ms(GTG)"
BORDERLINE_SPEC = "모니터 / 68.47cm(27인치) / QHD(2560 x 1440) / 120Hz / IPS / 와이드(16:9) / 5ms(GTG)"


def test_gaming_monitor_filter_keeps_high_refresh():
    assert _is_gaming_monitor("ASUS ROG STRIX", GAMING_SPEC)
    assert _is_gaming_monitor("크로스오버 27QD166CM", BORDERLINE_SPEC)  # 120Hz는 경계 포함


def test_gaming_monitor_filter_drops_office_panels():
    """다나와 '게이밍모니터' 검색에는 60Hz 사무용 모니터가 20%가량 섞여 나온다."""
    assert not _is_gaming_monitor("알파스캔 AOC U32V11", OFFICE_SPEC)


def test_gaming_monitor_filter_drops_missing_refresh_rate():
    assert not _is_gaming_monitor("스펙 미상 모니터", "모니터 / 68.6cm(27인치) / QHD(2560 x 1440)")


# ============================
# 상품명 하이라이트 공백 복원
# ============================

def test_clean_name_restores_spaces_eaten_by_search_highlight():
    """다나와가 검색어를 <b>로 감싸면 get_text(strip=True)가 앞뒤 공백을 먹어
    '축교환 게이밍 기계식'이 '축교환게이밍기계식'으로 붙어버린다."""
    html = "<a>앱코 HACKER K640 축교환 <b>게이밍</b> <b>기계식</b> 블랙</a>"
    tag = BeautifulSoup(html, "html.parser").find("a")

    # 기존 동작(버그): 하이라이트 앞뒤 공백이 전부 사라진다
    assert tag.get_text(strip=True) == "앱코 HACKER K640 축교환게이밍기계식블랙"
    assert clean_name(tag) == "앱코 HACKER K640 축교환 게이밍 기계식 블랙"


def test_clean_name_collapses_repeated_whitespace():
    tag = BeautifulSoup("<a>  LG전자   24U411B\n </a>", "html.parser").find("a")
    assert clean_name(tag) == "LG전자 24U411B"


# ============================
# 중고 변형 제외
# ============================

USED_VARIANT_HTML = """
<div class="prod_pricelist"><ul>
  <li id="productInfoDetail_1">
    <p class="memory_sect"><span class="text">적축</span></p>
    <a class="click_log_product_standard_price_">29,900원</a>
  </li>
  <li id="productInfoDetail_2">
    <p class="memory_sect"><span class="text">중고</span></p>
    <a class="click_log_product_standard_price_">20,330원</a>
  </li>
</ul></div>
"""


def test_extract_variants_drops_used_options():
    """중고가는 신품 최저가보다 평균 16.8%, 최대 32% 싸서 같은 시계열에 섞으면
    카테고리 최저가·평균가와 가격 하락 알림이 전부 왜곡된다."""
    assert extract_variants(block(USED_VARIANT_HTML)) == [("적축", 29900)]


# ============================
# 상품명 기준 중고 제외
# ============================

def test_is_new_product_drops_used_and_refurbished():
    """다나와는 중고 표시를 변형 라벨뿐 아니라 상품명 자체에도 넣는다."""
    assert not _is_new_product("삼성전자 PM981a M.2 NVMe 중고 (256GB)")
    assert not _is_new_product("GIGABYTE AORUS Gen4 M.2 NVMe 중고 (2TB)")
    assert not _is_new_product("ASUS TUF Gaming A14 FA401UM-RG007 (리퍼비시)")
    assert not _is_new_product("삼성전자 PM9A1 M.2 NVMe 병행수입 (2TB)")
    assert not _is_new_product("삼성전자 990 PRO M.2 NVMe 해외구매 (4TB)")


def test_is_new_product_keeps_bulk():
    """벌크는 무포장 정품(새 제품)이라 걸러내면 안 된다 —
    ml/price_prediction.py의 extract_cpu_features가 is_bulk를 가격 특성으로 쓴다."""
    assert _is_new_product("삼성전자 PM9A1 M.2 NVMe 벌크 (1TB)")
    assert _is_new_product("인텔 코어i5-14세대 14400 (랩터레이크 리프레시) (벌크 + 쿨러)")


def test_is_new_product_keeps_normal_products():
    assert _is_new_product("CORSAIR K100 AIR WIRELESS RGB 게이밍 기계식")
    assert _is_new_product("LG전자 울트라기어 evo AI 올레드 39GX950B")
    assert _is_new_product("")


def test_is_new_product_does_not_match_partial_words():
    """'리퍼'만 잡으면 '그리퍼' 같은 무관한 단어에 걸린다 — 전체 형태로만 매칭한다."""
    assert _is_new_product("로보틱스 그리퍼 마우스")


# ============================
# 게이밍 키보드 / 마우스 선별
# ============================

MECHANICAL_KB = "키보드 / 풀배열 / 유선 / 기계식 / 104키 / 스위치 : GTMX / 1000Hz / 1ms 응답속도"
MAGNETIC_KB = "키보드 / 텐키리스 / 유선 / 무접점(자석축) / 84키 / 8000Hz / 0.125ms 응답속도"
MEMBRANE_KB = "키보드 / 컴팩트 풀배열 / 유선+무선 / 멤브레인 / 블루투스 / 98키 / 1000Hz"
PANTOGRAPH_KB = "키보드 / 미니 / 무선 / 펜타그래프 / 블루투스 / 79키"


def test_gaming_keyboard_filter_keeps_mechanical_and_magnetic():
    assert _is_gaming_keyboard("앱코 HACKER K640", MECHANICAL_KB)
    assert _is_gaming_keyboard("CORSAIR K70 PRO TKL", MAGNETIC_KB)


def test_gaming_keyboard_filter_drops_office_switches():
    assert not _is_gaming_keyboard("MSI FORGE GK100", MEMBRANE_KB)
    assert not _is_gaming_keyboard("로지텍 K380", PANTOGRAPH_KB)


def test_gaming_keyboard_filter_does_not_use_polling_rate():
    """폴링레이트로 거르면 표기가 없는 진짜 게이밍 키보드가 탈락한다
    (실측: 로지텍 G512, CORSAIR K100 AIR 등 11.5%가 Hz 미표기)."""
    no_hz = "키보드 / 풀배열 / 유선 / 기계식 / 104키 / RGB 백라이트"
    assert _is_gaming_keyboard("로지텍 G512", no_hz)


HIGH_POLLING_MOUSE = "마우스 / 유선+무선 / 5버튼 / 33000DPI / 8000Hz 폴링레이트 / 오른손"
OFFICE_MOUSE = "마우스 / 유선 / 3버튼 / 3600DPI / 125Hz 폴링레이트"
NO_POLLING_HIGH_DPI = "마우스 / 무선 / DPI+5버튼 / 25600DPI / 광 / 전용동글(리시버)"
NO_POLLING_LOW_DPI = "마우스 / 유선 / 3버튼 / 6400DPI / 광"


def test_gaming_mouse_filter_uses_polling_rate_when_present():
    assert _is_gaming_mouse("CORSAIR 세이버 v2 PRO", HIGH_POLLING_MOUSE)
    assert not _is_gaming_mouse("COX CM1000", OFFICE_MOUSE)


def test_gaming_mouse_filter_falls_back_to_dpi_when_polling_missing():
    """폴링레이트 미표기가 22%나 되고 그 안에 진짜 게이밍 마우스가 섞여 있어,
    미표기일 때만 DPI로 대신 판정한다."""
    assert _is_gaming_mouse("로지텍 G309", NO_POLLING_HIGH_DPI)
    assert not _is_gaming_mouse("MSI FORGE GM100", NO_POLLING_LOW_DPI)


def test_gaming_mouse_filter_drops_specless_product():
    assert not _is_gaming_mouse("스펙 미상 마우스", "마우스 / 유선 / 3버튼")
