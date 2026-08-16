# tests/test_price_scraper.py
# 네트워크 없이 순수 파싱/선별 로직만 검증한다 (다나와 HTML 조각을 직접 만들어 넣는다).

from bs4 import BeautifulSoup

from scraper.price_scraper import _is_gaming_monitor, extract_variants


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
