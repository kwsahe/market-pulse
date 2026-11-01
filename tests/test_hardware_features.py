# tests/test_hardware_features.py
# 노트북·RAM·그래픽카드·CPU 특성 추출 회귀 테스트.
# 2026-11 점검 때 정규식이 실제 다나와 스펙 표기와 어긋나 값이 통째로 0이던 특성들
# (AMD 코어 수, 내장그래픽, 그래픽카드 파워, RAM 2개입)과 새로 넣은 특성을 실제 문구로 확인한다.

from ml.price_prediction import (
    extract_cpu_features,
    extract_gpu_features,
    extract_keyboard_features,
    extract_notebook_features,
    extract_ram_features,
)

NOTEBOOK_SPECS = (
    "노트북 / 40.6cm(16인치) / 2.7kg / 윈도우11(설치) / [화면] / 2560x1600(WQXGA) / DCI-P3: 100% / "
    "240Hz / 500nit / [CPU] / AMD / 라이젠9(Zen4) / 8945HX (5.4GHz) / [그래픽] / 외장그래픽 / RTX5080 / "
    "VRAM: 16GB / TGP: 175W / [구성] / 16GB / 램 교체: 가능 / 용량: 1TB / USB-PD(+DC) / 90Wh"
)

AMD_CPU_SPECS = (
    "AMD(소켓AM5) / 16코어 / 32스레드 / 메모리 규격: DDR5 / 탑재 / 6세대(Zen5) / TSMC 4nm / "
    "기본 클럭: 4.3GHz / 최대 클럭: 5.7GHz / L2 캐시: 16MB / L3 캐시: 128MB / TDP: 170W"
)

INTEL_CPU_SPECS = (
    "인텔(소켓1851) / P6+E12코어 / 18스레드 / 메모리 규격: DDR5 / 미탑재 / TSMC 3nm / "
    "기본 클럭: 4.2GHz / 최대 클럭: 5.3GHz / L2 캐시: 30MB / L3 캐시: 30MB"
)

GPU_SPECS = (
    "RTX 5060 Ti / PCIe5.0x16(at x8) / 550W 이상 / 전원 포트: 8핀 x1 / 가로(길이): 229mm / "
    "베이스클럭: 2407 / 부스트클럭: 2602MHz / 스트림 프로세서: 4608 / GDDR7"
)


def test_notebook_reads_gpu_screen_and_cpu_tier_from_specs():
    f = extract_notebook_features({"specs": NOTEBOOK_SPECS, "product": "MSI 벡터 A16 HX A8WIG-R9 QHD+ (SSD 1TB)"})
    assert f["gpu_model"] == 5080
    assert f["vram_gb"] == 16
    assert f["tgp_w"] == 175
    assert f["refresh_hz"] == 240
    assert f["pixels_mp"] == 4.1
    assert f["cpu_tier"] == 9
    assert f["ssd_gb"] == 1024


def test_notebook_ram_prefers_product_option_then_falls_back_to_specs():
    base = extract_notebook_features({"specs": NOTEBOOK_SPECS, "product": "MSI 벡터 A16 (SSD 1TB)"})
    upgraded = extract_notebook_features({"specs": NOTEBOOK_SPECS, "product": "MSI 벡터 A16 64GB램 (SSD 1TB)"})
    assert base["ram_gb"] == 16
    assert upgraded["ram_gb"] == 64


def test_amd_cpu_core_count_is_not_zero():
    f = extract_cpu_features({"specs": AMD_CPU_SPECS, "product": "AMD 라이젠9-6세대 9950X3D (그래니트 릿지) (정품)"})
    assert f["total_cores"] == 16
    assert f["threads"] == 32
    assert f["l3_mb"] == 128
    assert f["cpu_tier"] == 9
    assert f["has_igpu"] == 1
    assert f["generation"] == 6


def test_intel_cpu_sums_p_and_e_cores_and_reads_missing_igpu():
    f = extract_cpu_features({"specs": INTEL_CPU_SPECS, "product": "인텔 코어 울트라5 시리즈2 250KF Plus (정품)"})
    assert f["total_cores"] == 18
    assert f["cpu_tier"] == 5
    assert f["has_igpu"] == 0
    assert f["is_series2"] == 1


def test_gpu_reads_recommended_power_stream_processors_and_ti():
    f = extract_gpu_features({"specs": GPU_SPECS, "product": "ASUS DUAL 지포스 RTX 5060 TI OC D7 8GB"})
    assert f["gpu_model"] == 5060
    assert f["power_w"] == 550
    assert f["stream_processors"] == 4608
    assert f["is_ti"] == 1
    assert f["vram_gb"] == 8


def test_gpu_without_ti_is_not_flagged():
    specs = GPU_SPECS.replace("RTX 5060 Ti", "RTX 5060")
    assert extract_gpu_features({"specs": specs, "product": "MSI 지포스 RTX 5060 D7 8GB"})["is_ti"] == 0


def test_cpu_packaging_separates_single_box_from_multipack_bulk_and_parallel_import():
    """같은 칩도 포장에 따라 값이 크게 다르다 (10-31: 9700X 정품 68.6만 / 멀티팩 39.3만 / 벌크 병행 33.3만)."""
    def pack(product):
        f = extract_cpu_features({"specs": AMD_CPU_SPECS, "product": product})
        return f["is_bulk"], f["is_multipack"], f["is_parallel_import"], f["has_cooler"]

    assert pack("AMD 라이젠7-6세대 9700X (그래니트 릿지) (정품)") == (0, 0, 0, 0)
    assert pack("AMD 라이젠7-6세대 9700X (그래니트 릿지) (멀티팩 정품)") == (0, 1, 0, 0)
    assert pack("AMD 라이젠7-6세대 9700X (그래니트 릿지) (벌크 병행)") == (1, 0, 1, 0)
    assert pack("인텔 코어i5-14세대 14600KF (랩터레이크 리프레시) (밸류팩 정품)") == (0, 1, 0, 0)
    assert pack("인텔 코어i5-12세대 12400F (엘더레이크) (벌크 + 쿨러)") == (1, 0, 0, 1)


# 새 검색 UI 스펙에는 스위치 방식이 빠진다 — 수집 필터와 같은 기준으로 상품명·래피드 트리거도 본다.
NEW_UI_KB_SPECS = "키보드 / 풀배열 / 유선 / 104키 / H/W매크로 / 8000Hz / 0.125ms 응답속도 / RGB 백라이트"


def test_keyboard_switch_type_falls_back_to_product_name():
    magnetic = extract_keyboard_features({"specs": NEW_UI_KB_SPECS, "product": "CORSAIR K70 MAX RGB MGX 게이밍 기계식 (마그네틱축)"})
    optical = extract_keyboard_features({"specs": NEW_UI_KB_SPECS, "product": "COX CY104K V2 카일 광축 V2 게이밍 블랙 (갈축)"})
    mechanical = extract_keyboard_features({"specs": NEW_UI_KB_SPECS, "product": "앱코 K580 교체축 게이밍 스카이 (적축)"})
    assert magnetic["is_magnetic"] == 1
    assert optical["is_optical"] == 1
    assert mechanical["is_mechanical"] == 1 and mechanical["is_magnetic"] == 0


def test_keyboard_rapid_trigger_counts_as_magnetic():
    specs = "키보드 / 미니 / 유선 / 61키 / 8000Hz / 래피드 트리거"
    assert extract_keyboard_features({"specs": specs, "product": "CORSAIR 클리퍼 PRO 미니 60"})["is_magnetic"] == 1


def test_keyboard_old_ui_spec_still_reads_switch_type():
    old = "키보드 / 텐키리스 / 유선 / 무접점(자석축) / 84키 / 8000Hz"
    f = extract_keyboard_features({"specs": old, "product": "CORSAIR K70 PRO TKL"})
    assert f["is_magnetic"] == 1 and f["is_optical"] == 0


def test_ram_two_stick_pack_is_detected():
    pack = extract_ram_features({"specs": "DDR5 / 6000MHz / CL30", "product": "KingBank DDR5-6000 CL30 패키지 (32GB(16Gx2))"})
    single = extract_ram_features({"specs": "DDR5 / 5600MHz / CL46", "product": "타무즈 DDR5-5600 CL46 (32GB)"})
    assert pack["is_pack"] == 1
    assert pack["capacity_gb"] == 32
    assert single["is_pack"] == 0
