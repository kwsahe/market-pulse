# tests/test_price_scraper.py
# 네트워크 없이 순수 파싱/선별 로직만 검증한다 (다나와 HTML 조각을 직접 만들어 넣는다).

from bs4 import BeautifulSoup

from scraper.price_scraper import (
    _capacity_gb, _drop_bogus_variant_prices, _has_unified_memory, _is_cpu,
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


# 미끼가 필터 — 실제로 걸렸던 케이스는 삼성 990 EVO Plus 4TB가 10,000원으로 내려온 건이다
# (같은 상품 2TB 516,480원 / 1TB 327,720원).
BOGUS_VARIANT_HTML = """
<div class="prod_pricelist"><ul>
  <li id="productInfoDetail_1">
    <p class="memory_sect"><span class="text">4TB</span></p>
    <a class="click_log_product_standard_price_">10,000원</a>
  </li>
  <li id="productInfoDetail_2">
    <p class="memory_sect"><span class="text">2TB</span></p>
    <a class="click_log_product_standard_price_">516,480원</a>
  </li>
  <li id="productInfoDetail_3">
    <p class="memory_sect"><span class="text">1TB</span></p>
    <a class="click_log_product_standard_price_">327,720원</a>
  </li>
</ul></div>
"""


def test_extract_variants_drops_bogus_bait_price():
    """4TB가 1TB보다 32배 싼 건 실판매가가 아니다. 남은 변형은 그대로 살아야 한다."""
    assert extract_variants(block(BOGUS_VARIANT_HTML)) == [("2TB", 516480), ("1TB", 327720)]


def test_capacity_gb_only_trusts_single_token():
    """용량 토큰이 하나일 때만 단가 정규화 기준으로 쓴다."""
    assert _capacity_gb("4TB") == 4096
    assert _capacity_gb("512GB") == 512
    assert _capacity_gb("SSD 1TB") == 1024
    assert _capacity_gb("램64GB, SSD 2TB") is None  # 어느 쪽으로 나눌지 알 수 없다
    assert _capacity_gb("벌크") is None


def test_bogus_filter_keeps_wide_capacity_spread():
    """1TB와 8TB는 원가격만 보면 3%까지 벌어지지만 1GB당 단가로는 정상 범위다.
    단가로 정규화하지 않으면 이 정상 상품이 잘린다."""
    variants = [("1TB", 120_000), ("8TB", 3_900_000)]
    assert _drop_bogus_variant_prices(variants) == variants


def test_bogus_filter_keeps_bulk_cpu():
    """벌크는 무포장 정품(새 제품)이라 남겨야 한다 — 실측 최저 정상 비율이 9.63%다."""
    variants = [("벌크", 72_230), ("정품", 750_000)]
    assert _drop_bogus_variant_prices(variants) == variants


def test_bogus_filter_needs_siblings():
    """변형이 하나뿐이면 비교 기준이 없으므로 판단하지 않고 그대로 둔다."""
    assert _drop_bogus_variant_prices([("4TB", 10_000)]) == [("4TB", 10_000)]


# 다나와 "CPU 프로세서" 검색은 기기의 AP(엑시노스·디멘시티 등)를 CPU로 쳐서
# 스마트폰·태블릿을 같이 물어온다. 누적 373종 중 84종이 그랬다.
CPU_SPEC = "인텔(소켓1700) / P2코어 / 메모리 규격 : DDR5, DDR4 / 내장그래픽:탑재 / PBP-MTP : 46W"
AMD_CPU_SPEC = "AMD(소켓AM5) / 8코어 / 16스레드 / 기본클럭: 4.7GHz / 내장그래픽:탑재"
PHONE_SPEC = "스마트폰(바형) / 화면:17cm(6.7인치) / 램 : 8GB / 엑시노스1680 / 5,000mAh / 무게 : 179g"
TABLET_SPEC = "태블릿PC / LTE / 8.4인치 / 90Hz / 램 : 8GB / 용량 : 128GB / Helio G99 / 6,030mAh"


def test_cpu_filter_keeps_desktop_cpu():
    """데스크탑 CPU는 소켓 규격이 스펙에 100% 표기된다."""
    assert _is_cpu("인텔 프로세서 300 (랩터레이크 리프레시)", CPU_SPEC)
    assert _is_cpu("AMD 라이젠7 9800X3D", AMD_CPU_SPEC)


def test_cpu_filter_drops_phones_and_tablets():
    """갤럭시 퀀텀7 단말할인가 154,900원이 CPU 카테고리 최저가로 잡히던 케이스."""
    assert not _is_cpu("삼성전자 갤럭시 퀀텀7 128GB, SKT 기기변경 완납", PHONE_SPEC)
    assert not _is_cpu("포유디지탈 아이뮤즈 뮤패드 K8 LTE", TABLET_SPEC)


def test_cpu_filter_drops_when_spec_missing():
    """소켓 표기가 없으면 데스크탑 CPU로 볼 근거가 없다."""
    assert not _is_cpu("정체불명 상품", "")
    assert not _is_cpu("정체불명 상품", None)


# AI 노트북(통합메모리) 판정 — 검색 결과 페이지 스펙만 쓴다.
# 예전에는 robots 금지 경로(/info/ajax/)의 spec_dict 를 봤는데, 그 경로를 끄면
# 카테고리를 통째로 못 모으는 문제가 있었다. 실측 69건(통과 50/탈락 19)에서
# ajax 판정과 100% 일치함을 확인하고 교체했다.
APPLE_SPEC = ("AI노트북 / 34.5cm(13.6인치) / 1.23kg / 최대 18시간 / DCI-P3 : 지원 / 500nit / "
              "애플(ARM) / M5 / 16GB / 램 교체 : 불가능 / 용량 : 1TB / Apple Intelligence")
AI_MAX_SPEC = ("AI 태블릿PC / 34.03cm(13.4인치) / 1.2kg / DCI-P3 : 100% / 500nit / AMD / "
               "라이젠 AI Max + / 395 (5.1GHz) / 50TOPS / Radeon 8060S / 32GB")
DISCRETE_GPU_SPEC = ("AI 노트북 / 40.6cm(16인치) / 2.48kg / sRGB : 100% / 500nit / AMD / "
                     "라이젠 AI 7 / 350 (5.0GHz) / 50TOPS / RTX5070 Ti / VRAM: 12GB / TGP : 140W")


def test_unified_memory_accepts_apple_silicon():
    assert _has_unified_memory("APPLE 맥북 에어13 M5", APPLE_SPEC)


def test_unified_memory_accepts_ryzen_ai_max():
    assert _has_unified_memory("ASUS ROG Flow Z13 GZ302EA", AI_MAX_SPEC)


def test_unified_memory_rejects_plain_ryzen_ai():
    """핵심 구분점 — '라이젠 AI 7/9'는 외장 VRAM 분리 구조라 통합메모리가 아니다.
    다나와 '라이젠 AI Max' 검색이 HP 오멘 MAX 시리즈를 함께 잡아오기 때문에 필요하다."""
    assert not _has_unified_memory("HP 오멘 MAX 16-ak0017AX", DISCRETE_GPU_SPEC)


def test_unified_memory_rejects_when_specs_missing():
    assert not _has_unified_memory("정체불명 노트북", "")
    assert not _has_unified_memory("정체불명 노트북", None)


def test_unified_memory_takes_product_and_specs():
    """판정 시그니처가 (상품명, 스펙) 이어야 한다 — CATEGORY_FILTERS 의 다른 판정기들과 같은 모양.
    예전 시그니처(spec_dict 하나)로 되돌아가면 _collect_laptops 호출부가 조용히 깨진다."""
    import inspect
    assert list(inspect.signature(_has_unified_memory).parameters) == ["product", "specs"]


# 다나와가 2026-10-07부터 검색 요청 일부를 개편된 새 검색 UI(search.danawa.com/?query=)로
# 무작위 리다이렉트한다. 옛 UI가 올 때까지 재요청하던 우회는 비율이 최대 67%까지 오르자
# 카테고리를 통째로 놓쳤다(10-16 NVMe SSD, 10-18 그래픽카드). 이제 두 UI를 모두 읽는다.
# 같은 상품이면 어느 UI든 같은 행(상품명+옵션, 가격, pcode, 이미지)이 나와야 이력이 이어진다.
# 실데이터 11개 검색어(894행)로 확인한 모양을 줄여서 옮겼다.
OLD_UI_HTML = """
<div class="prod_item">
  <a class="click_log_product_standard_title_" href="https://prod.danawa.com/info/?pcode=111&cate=112752">ESSENCORE KLEVV <b>DDR5</b>-6000 CL30</a>
  <img src="https://img.danuri.io/catalog-image/111.jpg">
  <div class="spec_list">데스크탑용 / <b>DDR5</b> / 램타이밍 : CL30</div>
  <div class="prod_pricelist"><ul>
    <li id="productInfoDetail_111"><p class="memory_sect"><span class="text">64GB(32Gx2)</span></p>
      <a class="click_log_product_standard_price_">1,850,000원</a></li>
    <li id="productInfoDetail_112"><p class="memory_sect"><span class="text">32GB(16Gx2)</span></p>
      <a class="click_log_product_standard_price_">889,000원</a></li>
    <li id="productInfoDetail_113"><p class="memory_sect"><span class="text">32GB(16Gx2) 중고</span></p>
      <a class="click_log_product_standard_price_">700,000원</a></li>
  </ul></div>
</div>
<div class="prod_item">
  <a class="click_log_product_standard_title_" href="https://prod.danawa.com/info/?pcode=222&cate=112752">삼성전자 <b>DDR5</b>-5600</a>
  <div class="prod_pricelist"><ul>
    <li id="productInfoDetail_222"><p class="memory_sect"><span class="text">16GB</span></p>
      <a class="click_log_product_standard_price_">349,690원</a></li>
  </ul></div>
</div>
<div class="prod_item">
  <a class="click_log_product_standard_title_" href="https://prod.danawa.com/info/?pcode=333&cate=112757">LG전자 24U411B</a>
  <a class="click_log_product_standard_price_">142,590원</a>
</div>
"""

NEW_UI_PRODUCTS = [
    {"prodType": 1, "productSeq": "111", "productName": "ESSENCORE KLEVV <b>DDR5</b>-6000 CL30",
     "linkUrl": "https://prod.danawa.com/info/?pcode=111&keyword=DDR5&cate=112752",
     "imageUrl": "https://img.danuri.io/catalog-image/111.jpg?v=20261018080440",
     "summary": {"desc": ["데스크탑용", "<b>DDR5</b>", "램타이밍", "CL30"], "descBridge": ["<em>/</em>", "<em>/</em>", ": "]},
     "minPrice": 1850000, "totalPrice": 1852500, "bundleName": "64GB(32Gx2)",
     "bundleList": [{"bundleName": "64GB(32Gx2)", "minPrice": 1850000, "totalPrice": 1852500},
                    {"bundleName": "32GB(16Gx2)", "minPrice": 889000, "totalPrice": 891500},
                    {"bundleName": "32GB(16Gx2) 중고", "minPrice": 700000, "totalPrice": 702500}]},
    # 옵션이 하나뿐이면 bundleList가 비고 라벨은 bundleName에만 있다 — 옛 UI는 이것도 "(16GB)"로 붙였다
    {"prodType": 1, "productSeq": "222", "productName": "삼성전자 <b>DDR5</b>-5600",
     "linkUrl": "https://prod.danawa.com/info/?pcode=222&keyword=DDR5&cate=112752",
     "minPrice": 349690, "totalPrice": 352800, "bundleName": "16GB", "bundleList": []},
    {"prodType": 1, "productSeq": "333", "productName": "LG전자 24U411B",
     "linkUrl": "https://prod.danawa.com/info/?pcode=333&keyword=x&cate=112757",
     "minPrice": 142590, "totalPrice": 145090, "bundleName": "", "bundleList": []},
    # 오픈마켓 중개 링크 — pcode가 없고 옛 UI에는 나오지 않는다
    {"prodType": 3, "productSeq": "TH201_1", "productName": "맥북 호환 가죽 케이스",
     "linkUrl": "https://prod.danawa.com/bridge/go_link_goods.php?x=1", "minPrice": 30000},
]


def _new_ui_html(products):
    """Next.js가 실어 보내는 모양 그대로: 페이로드 문자열을 self.__next_f.push 여러 조각으로 나눠 담는다."""
    import json
    payload = "17:" + json.dumps({"state": {"data": {"products": products}}}, ensure_ascii=False, separators=(",", ":"))
    half = len(payload) // 2
    return "".join(f"<script>self.__next_f.push([1,{json.dumps(part)}])</script>"
                   for part in (payload[:half], payload[half:]))


def _rows(items):
    from scraper.price_scraper import extract_cate, extract_pcode
    return [(it["product"], extract_pcode(it["href"]), extract_cate(it["href"]), it["img_url"],
             it["variants"], it["price"]) for it in items]


def test_new_ui_reads_the_same_rows_as_old_ui():
    from scraper.price_scraper import _search_items
    old = _rows(_search_items(OLD_UI_HTML))
    new = _rows(_search_items(_new_ui_html(NEW_UI_PRODUCTS)))
    assert new == old
    assert old[0][0] == "ESSENCORE KLEVV DDR5 -6000 CL30"  # 검색어 <b> 강조를 두 UI가 같은 규칙으로 푼다
    assert old[0][4] == [("64GB(32Gx2)", 1850000), ("32GB(16Gx2)", 889000)]  # 중고 옵션 제외, 가격은 배송비 제외
    assert old[1][4] == [("16GB", 349690)]
    assert old[2][4:] == ([], 142590)


def test_new_ui_strips_image_version_query():
    """'?v=수정시각'이 남으면 laptop_images(pcode, image_url)에 같은 이미지가 매일 새 행으로 쌓인다."""
    from scraper.price_scraper import _search_items
    assert _search_items(_new_ui_html(NEW_UI_PRODUCTS))[0]["img_url"] == "https://img.danuri.io/catalog-image/111.jpg"


def test_new_ui_unknown_structure_reads_nothing():
    """구조가 또 바뀌면 조용히 엉뚱한 값을 만들지 않고 0개 — verify_last_scrape 가드가 카테고리 소멸로 잡는다."""
    from scraper.price_scraper import _search_items
    assert _search_items("<html><body>점검 중</body></html>") == []


def test_search_get_requests_once_even_for_new_ui(monkeypatch):
    """새 UI도 읽을 수 있으니 재요청하지 않는다 — 다나와에 보내는 요청이 검색어당 1번으로 준다."""
    import scraper.price_scraper as ps
    calls = []
    monkeypatch.setattr(ps.requests, "get", lambda url, headers=None, timeout=None: calls.append(url))
    monkeypatch.setattr(ps.time, "sleep", lambda s: None)  # 크롤 딜레이는 테스트에서 건너뛴다
    ps._search_get("https://search.danawa.com/dsearch.php?query=x")
    assert len(calls) == 1


# 비정상 가격(카테고리 오늘치 중앙값의 100배 초과 / 1/100 미만) — 2026-09-29부터
# '앱코 HACKER A660 마우스 (화이트)'가 439,824,000원으로 수집됐다(판매처 1곳의 잘못된 가격).
# 옵션이 하나뿐이라 형제 옵션과 비교하는 미끼가 필터로는 못 잡았다.
def _row(name, price, category="게이밍 마우스"):
    return ("2026-10-07", category, name, price, "", "", "1")


def test_absurd_price_drops_mouse_listed_at_440m():
    from scraper.price_scraper import _drop_absurd_prices
    rows = [_row(f"마우스{i}", 60000 + i * 1000) for i in range(20)]
    rows.append(_row("앱코 HACKER A660 (화이트)", 439_824_000))
    kept = _drop_absurd_prices(rows)
    assert len(kept) == 20
    assert all(r[3] < 1_000_000 for r in kept)


def test_absurd_price_keeps_real_flagship_cpu():
    """스레드리퍼 PRO 9995WX(1,836만원)는 CPU 중앙값의 약 55배지만 실제 가격이다."""
    from scraper.price_scraper import _drop_absurd_prices
    rows = [_row(f"CPU{i}", 330_000, "CPU") for i in range(30)]
    rows.append(_row("AMD 라이젠 스레드리퍼 PRO 9995WX", 18_359_980, "CPU"))
    assert len(_drop_absurd_prices(rows)) == 31


def test_absurd_price_drops_absurdly_cheap_too():
    from scraper.price_scraper import _drop_absurd_prices
    rows = [_row(f"CPU{i}", 400_000, "CPU") for i in range(30)]
    rows.append(_row("미끼 CPU", 3_000, "CPU"))  # 중앙값의 1/133
    assert len(_drop_absurd_prices(rows)) == 30


def test_absurd_price_handles_empty_batch():
    from scraper.price_scraper import _drop_absurd_prices
    assert _drop_absurd_prices([]) == []
