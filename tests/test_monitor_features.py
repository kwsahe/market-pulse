# tests/test_monitor_features.py
# extract_monitor_features의 정규식 검증. 스펙 문자열은 다나와 "게이밍모니터" 검색 결과에서
# 실제로 관측된 형태를 그대로 가져왔다 (평면/곡면, 측정방식 유무, 명암비 유무 등 변형 포함).

import pytest

from ml.price_prediction import FEATURE_EXTRACTORS, FEATURE_LABELS, extract_monitor_features

FLAT_IPS = (
    "모니터 / 68.47cm(27인치) / QHD(2560 x 1440) / 120Hz / IPS / 와이드(16:9) / "
    "5ms(GTG) / 350nits / 1,000:1 / 피벗(회전) / 엘리베이션(높낮이) / 틸트(상하) / 스위블(좌우)"
)
CURVED_ULTRAWIDE = (
    "모니터 / 100.859cm(40인치) / WUHD(5120 x 2160) / 120Hz / Nano-IPS Black / 울트라와이드(21:9) / "
    "2500R / 5ms(GTG) / 450nits / 2,000:1 / 엘리베이션(높낮이) / 틸트(상하) / 스위블(좌우)"
)
NO_CONTRAST = (
    "모니터 / 68cm(27인치) / QHD(2560 x 1440) / 255Hz / Fast IPS / 와이드(16:9) / "
    "0.3ms(GTG) / 400nits / 피벗(회전) / 엘리베이션(높낮이) / 틸트(상하) / 스위블(좌우)"
)


def features(specs: str, product: str = "테스트 모니터") -> dict:
    return extract_monitor_features({"specs": specs, "product": product})


def test_reads_panel_size_resolution_and_refresh_rate():
    f = features(FLAT_IPS)
    assert f["panel_inch"] == 27
    assert f["pixels_mp"] == pytest.approx(3.69, abs=0.01)  # 2560x1440
    assert f["refresh_hz"] == 120
    assert f["response_ms"] == 5
    assert f["brightness_nits"] == 350


def test_contrast_ratio_does_not_match_aspect_ratio():
    """'와이드(16:9)'가 먼저 나오므로 ':1' 앵커가 없으면 명암비로 16을 잘못 집는다."""
    assert features(FLAT_IPS)["contrast_ratio"] == 1000
    assert features(CURVED_ULTRAWIDE)["contrast_ratio"] == 2000


def test_flat_panel_has_zero_curvature():
    assert features(FLAT_IPS)["curvature_r"] == 0
    assert features(CURVED_ULTRAWIDE)["curvature_r"] == 2500


def test_panel_grade_flags():
    flat = features(FLAT_IPS)
    assert flat["is_fast_ips"] == 0 and flat["is_oled"] == 0

    fast = features(NO_CONTRAST)
    assert fast["is_fast_ips"] == 1

    # 'Nano-IPS Black'도 고속 IPS 등급으로 잡혀야 한다
    assert features(CURVED_ULTRAWIDE)["is_fast_ips"] == 1

    oled = features(FLAT_IPS.replace("IPS", "QD-OLED"))
    assert oled["is_oled"] == 1


def test_ultrawide_and_stand_features():
    assert features(FLAT_IPS)["is_ultrawide"] == 0
    assert features(FLAT_IPS)["stand_features"] == 4

    wide = features(CURVED_ULTRAWIDE)
    assert wide["is_ultrawide"] == 1
    assert wide["stand_features"] == 3


def test_missing_specs_degrade_to_zero_not_none():
    """train_model이 StandardScaler에 그대로 넣으므로 값은 항상 숫자여야 한다."""
    f = features("")
    assert set(f) == set(features(FLAT_IPS)), "모든 행이 같은 키 집합을 반환해야 한다"
    assert all(isinstance(v, (int, float)) for v in f.values())
    assert all(v == 0 for v in f.values())


def test_registered_as_a_prediction_category_with_korean_labels():
    assert FEATURE_EXTRACTORS["게이밍 모니터"] is extract_monitor_features
    for key in features(FLAT_IPS):
        assert key in FEATURE_LABELS, f"{key}의 한글 라벨이 없어 화면에 영문 키가 그대로 노출된다"
