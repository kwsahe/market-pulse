# tests/test_peripheral_features.py
# 게이밍 키보드/마우스 특성 추출기 검증.
# 스펙 문자열은 다나와 검색 결과에서 실제로 관측된 형태를 그대로 가져왔다.

from ml.price_prediction import (
    FEATURE_EXTRACTORS, FEATURE_LABELS, extract_keyboard_features, extract_mouse_features,
)

MAGNETIC_TKL = (
    "키보드 / 텐키리스 / 유선 / 무접점(자석축) / 84키 / 8000Hz / 0.125ms 응답속도 / "
    "숫자키없음 / RGB 백라이트 / C타입 포트 / 금속하우징 / PBT / 이중사출 키캡 / 한/영 정각"
)
MECHANICAL_FULL = (
    "키보드 / 풀배열 / 유선 / 기계식 / 104키 / 스위치 : GTMX / 1000Hz / 1ms 응답속도 / "
    "비키스타일 / 스위치 교체형 / 레인보우 백라이트 / ABS / 이중사출 키캡 / 한/영 정각"
)
WIRELESS_OPTICAL = (
    "키보드 / 컴팩트 풀배열 / 유선+무선 / 무접점(광축) / 블루투스 / 전용동글(리시버) / "
    "8000Hz / 0.125ms 응답속도 / 매크로키 / RGB 백라이트 / 로우프로파일(LP)"
)


def kb(specs: str) -> dict:
    return extract_keyboard_features({"specs": specs, "product": "테스트 키보드"})


def test_keyboard_switch_type_is_mutually_exclusive():
    magnetic = kb(MAGNETIC_TKL)
    assert (magnetic["is_magnetic"], magnetic["is_optical"], magnetic["is_mechanical"]) == (1, 0, 0)

    mechanical = kb(MECHANICAL_FULL)
    assert (mechanical["is_magnetic"], mechanical["is_optical"], mechanical["is_mechanical"]) == (0, 0, 1)

    optical = kb(WIRELESS_OPTICAL)
    assert (optical["is_magnetic"], optical["is_optical"], optical["is_mechanical"]) == (0, 1, 0)


def test_keyboard_layout_and_key_count():
    assert kb(MAGNETIC_TKL)["is_tenkeyless"] == 1
    assert kb(MAGNETIC_TKL)["key_count"] == 84
    assert kb(MECHANICAL_FULL)["is_tenkeyless"] == 0
    assert kb(MECHANICAL_FULL)["key_count"] == 104


def test_keyboard_connection_and_polling():
    assert kb(MAGNETIC_TKL)["is_wireless"] == 0
    assert kb(MAGNETIC_TKL)["polling_hz"] == 8000
    assert kb(MECHANICAL_FULL)["polling_hz"] == 1000

    wireless = kb(WIRELESS_OPTICAL)
    assert wireless["is_wireless"] == 1
    assert wireless["has_bluetooth"] == 1


def test_keyboard_hotswap_uses_actual_spec_wording():
    """다나와 스펙에는 '핫스왑'이라는 단어가 없고 '스위치 교체형'으로 적힌다."""
    assert kb(MECHANICAL_FULL)["is_hotswap"] == 1
    assert kb(MAGNETIC_TKL)["is_hotswap"] == 0


def test_keyboard_keycap_and_backlight():
    assert kb(MAGNETIC_TKL)["is_pbt"] == 1
    assert kb(MAGNETIC_TKL)["has_rgb"] == 1
    # 레인보우 백라이트는 RGB 등급이 아니다
    assert kb(MECHANICAL_FULL)["is_pbt"] == 0
    assert kb(MECHANICAL_FULL)["has_rgb"] == 0


PREMIUM_WIRELESS_MOUSE = (
    "마우스 / 유선+무선 / DPI+5버튼 / 26000DPI / 광 / 전용동글(리시버) / 블루투스 / USB / "
    "센서 : PAW-3395 / 8000Hz 폴링레이트 / 오른손 / RGB라이트 / 소프트웨어 지원 / 매크로"
)
WIRED_BASIC_MOUSE = "마우스 / 유선 / 6버튼 / 12000DPI / 광 / USB / 1000Hz 폴링레이트 / 오른손"


def ms(specs: str) -> dict:
    return extract_mouse_features({"specs": specs, "product": "테스트 마우스"})


def test_mouse_core_numbers():
    f = ms(PREMIUM_WIRELESS_MOUSE)
    assert f["dpi"] == 26000
    assert f["polling_hz"] == 8000
    assert f["button_count"] == 5
    assert f["has_dpi_button"] == 1

    basic = ms(WIRED_BASIC_MOUSE)
    assert basic["button_count"] == 6
    assert basic["has_dpi_button"] == 0


def test_mouse_connection_flags():
    f = ms(PREMIUM_WIRELESS_MOUSE)
    assert (f["is_wireless"], f["has_bluetooth"], f["has_dongle"]) == (1, 1, 1)

    wired = ms(WIRED_BASIC_MOUSE)
    assert (wired["is_wireless"], wired["has_bluetooth"], wired["has_dongle"]) == (0, 0, 0)


def test_mouse_premium_sensor_and_extras():
    f = ms(PREMIUM_WIRELESS_MOUSE)
    assert f["has_premium_sensor"] == 1
    assert f["has_rgb"] == 1
    assert f["has_software"] == 1
    assert f["has_macro"] == 1

    basic = ms(WIRED_BASIC_MOUSE)
    assert basic["has_premium_sensor"] == 0
    assert basic["has_rgb"] == 0


def test_missing_specs_degrade_to_zero_not_none():
    """train_model이 StandardScaler에 그대로 넣으므로 값은 항상 숫자여야 하고,
    모든 행이 같은 키 집합을 반환해야 한다."""
    for extract, sample in ((kb, MAGNETIC_TKL), (ms, PREMIUM_WIRELESS_MOUSE)):
        empty = extract("")
        assert set(empty) == set(extract(sample))
        assert all(isinstance(v, (int, float)) for v in empty.values())
        assert all(v == 0 for v in empty.values())


def test_registered_with_korean_labels():
    assert FEATURE_EXTRACTORS["게이밍 키보드"] is extract_keyboard_features
    assert FEATURE_EXTRACTORS["게이밍 마우스"] is extract_mouse_features
    for key in list(kb(MAGNETIC_TKL)) + list(ms(PREMIUM_WIRELESS_MOUSE)):
        assert key in FEATURE_LABELS, f"{key}의 한글 라벨이 없어 화면에 영문 키가 그대로 노출된다"
