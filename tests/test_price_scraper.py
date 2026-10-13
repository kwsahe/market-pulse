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
# 무작위 리다이렉트한다. 새 UI에는 옛 마크업이 없어 상품 0개로 파싱되고, 예외가 아니라서
# 조용히 '성공' 처리됐다(그날 11개 검색 중 4개 누락). 요청마다 배정이 무작위라 재요청하면 복구된다.
class _FakeResp:
    def __init__(self, text, url):
        self.text, self.url, self.status_code = text, url, 200


def _patch_search(monkeypatch, pages):
    import scraper.price_scraper as ps
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return pages[min(len(calls), len(pages)) - 1]

    monkeypatch.setattr(ps.requests, "get", fake_get)
    monkeypatch.setattr(ps.time, "sleep", lambda s: None)  # 크롤 딜레이는 테스트에서 건너뛴다
    return ps, calls


OLD_UI = _FakeResp('<a class="click_log_product_standard_title_">x</a>', "https://search.danawa.com/dsearch.php?query=x")
NEW_UI = _FakeResp('<div class="flex hover:underline">x</div>', "https://search.danawa.com/?query=x")


def test_search_get_retries_when_bucketed_into_new_ui(monkeypatch):
    ps, calls = _patch_search(monkeypatch, [NEW_UI, NEW_UI, OLD_UI])
    resp = ps._search_get("https://search.danawa.com/dsearch.php?query=x")
    assert resp is OLD_UI
    assert len(calls) == 3


def test_search_get_gives_up_after_retries(monkeypatch):
    """끝까지 새 UI면 무한히 돌지 않고 마지막 응답을 돌려준다 —
    그 검색어는 0개로 파싱되고, 카테고리 급감/소멸은 verify_last_scrape 가드가 잡는다."""
    ps, calls = _patch_search(monkeypatch, [NEW_UI])
    resp = ps._search_get("https://search.danawa.com/dsearch.php?query=x")
    assert resp is NEW_UI
    assert len(calls) == ps.SEARCH_RETRIES + 1


def test_search_get_does_not_retry_old_ui(monkeypatch):
    ps, calls = _patch_search(monkeypatch, [OLD_UI])
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
