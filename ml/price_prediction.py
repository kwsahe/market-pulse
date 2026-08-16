# ml/price_prediction.py
# 스펙 기반 가격 예측 모델
#
# 원리:
# 1. 스펙 텍스트에서 숫자 특성을 추출 (용량, 클럭, 코어 수 등)
# 2. 카테고리별로 Linear Regression 모델을 학습
# 3. 새 스펙을 넣으면 적정 가격을 예측
#
# 데이터가 쌓일수록 예측 정확도가 올라가요!

import pandas as pd
import numpy as np
import re
import os
import sys
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, cross_val_predict, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import load_prices


# ============================
# 특성 추출 함수들
# ============================
def extract_notebook_features(row):
    """게이밍 노트북 스펙에서 특성 추출
    
    스펙 텍스트 예시:
    "노트북 / 40.6cm(16인치) / 2.2kg / 밝기 : 300nit / 인텔 / 코어i5-13세대 / ..."
    
    여기서 숫자를 뽑아내서 ML이 이해할 수 있는 형태로 변환
    """
    specs = str(row.get("specs", ""))
    product = str(row.get("product", ""))
    features = {}

    # 화면 크기 (인치)
    inch = re.search(r"(\d+\.?\d*)\s*인치", specs)
    features["screen_inch"] = float(inch.group(1)) if inch else 0

    # 무게 (kg)
    weight = re.search(r"(\d+\.?\d*)\s*kg", specs)
    features["weight_kg"] = float(weight.group(1)) if weight else 0

    # 밝기 (nit)
    nit = re.search(r"(\d+)\s*nit", specs)
    features["brightness_nit"] = int(nit.group(1)) if nit else 0

    # CPU 클럭 (GHz)
    ghz = re.search(r"(\d+\.?\d*)\s*GHz", specs)
    features["cpu_ghz"] = float(ghz.group(1)) if ghz else 0

    # SSD 용량 (상품명에서 추출)
    ssd = re.search(r"SSD\s*(\d+)\s*(TB|GB)", product)
    if ssd:
        val = int(ssd.group(1))
        if ssd.group(2) == "TB":
            val *= 1024
        features["ssd_gb"] = val
    else:
        features["ssd_gb"] = 0

    # RAM 용량 (상품명에서)
    ram = re.search(r"(\d+)\s*GB\s*램", product)
    features["ram_gb"] = int(ram.group(1)) if ram else 0

    return features


def extract_ram_features(row):
    """DDR5 RAM 스펙에서 특성 추출"""
    specs = str(row.get("specs", ""))
    product = str(row.get("product", ""))
    features = {}

    # 클럭 (MHz)
    mhz = re.search(r"(\d{4,5})\s*MHz", specs)
    features["clock_mhz"] = int(mhz.group(1)) if mhz else 0

    # CL 타이밍
    cl = re.search(r"CL\s*(\d+)", specs)
    features["cl_timing"] = int(cl.group(1)) if cl else 0

    # 전압 (V)
    volt = re.search(r"(\d+\.?\d*)\s*V", specs)
    features["voltage"] = float(volt.group(1)) if volt else 0

    # 용량 (상품명에서)
    cap = re.search(r"\((\d+)\s*GB", product)
    features["capacity_gb"] = int(cap.group(1)) if cap else 0

    # 팩(여러 개 묶음)인지
    pack = re.search(r"(\d+)x(\d+)", product)
    features["is_pack"] = 1 if pack else 0

    # LED 유무
    features["has_led"] = 1 if "LED" in specs or "RGB" in specs else 0

    return features


def extract_ssd_features(row):
    """NVMe SSD 스펙에서 특성 추출"""
    specs = str(row.get("specs", ""))
    product = str(row.get("product", ""))
    features = {}

    # PCIe 세대
    pcie = re.search(r"PCIe(\d+)\.0", specs)
    features["pcie_gen"] = int(pcie.group(1)) if pcie else 0

    # 순차 읽기 속도 (MB/s)
    read_speed = re.search(r"순차읽기\s*:\s*([\d,]+)\s*MB", specs)
    features["read_speed"] = int(read_speed.group(1).replace(",", "")) if read_speed else 0

    # 순차 쓰기 속도 (MB/s)
    write_speed = re.search(r"순차쓰기\s*:\s*([\d,]+)\s*MB", specs)
    features["write_speed"] = int(write_speed.group(1).replace(",", "")) if write_speed else 0

    # DRAM 탑재 여부
    features["has_dram"] = 1 if "DRAM 탑재" in specs else 0

    # TLC/QLC
    features["is_tlc"] = 1 if "TLC" in specs else 0

    # 용량 (상품명에서)
    cap = re.search(r"\((\d+)\s*(TB|GB)", product)
    if cap:
        val = int(cap.group(1))
        if cap.group(2) == "TB":
            val *= 1024
        features["capacity_gb"] = val
    else:
        features["capacity_gb"] = 0

    # 외장 SSD 여부
    features["is_external"] = 1 if "외장" in specs or "포터블" in product else 0

    return features


def extract_gpu_features(row):
    """그래픽카드 스펙에서 특성 추출"""
    specs = str(row.get("specs", ""))
    product = str(row.get("product", ""))
    features = {}

    # GPU 등급 (숫자 추출: 5090→5090, 5080→5080)
    gpu_model = re.search(r"RTX\s*(\d{4})", specs + product)
    features["gpu_model"] = int(gpu_model.group(1)) if gpu_model else 0

    # VRAM (GB)
    vram = re.search(r"(\d+)\s*GB", product)
    features["vram_gb"] = int(vram.group(1)) if vram else 0

    # 부스트 클럭 (MHz)
    boost = re.search(r"부스트클럭\s*:\s*(\d+)\s*MHz", specs)
    features["boost_mhz"] = int(boost.group(1)) if boost else 0

    # 카드 길이 (mm)
    length = re.search(r"가로.*?(\d+\.?\d*)\s*mm", specs)
    features["length_mm"] = float(length.group(1)) if length else 0

    # 정격 파워 (W)
    power = re.search(r"정격파워\s*(\d+)\s*W", specs)
    features["power_w"] = int(power.group(1)) if power else 0

    return features


def extract_cpu_features(row):
    """CPU 스펙에서 특성 추출"""
    specs = str(row.get("specs", ""))
    product = str(row.get("product", ""))
    features = {}

    # 코어 수 (P코어 + E코어)
    p_core = re.search(r"P(\d+)", specs)
    e_core = re.search(r"E(\d+)", specs)
    plain_core = re.search(r"^(\d+)코어", specs)
    if p_core and e_core:
        features["total_cores"] = int(p_core.group(1)) + int(e_core.group(1))
    elif plain_core:
        features["total_cores"] = int(plain_core.group(1))
    else:
        features["total_cores"] = 0

    # 최대 클럭 (GHz)
    ghz = re.search(r"최대 클럭\s*:\s*(\d+\.?\d*)\s*GHz", specs)
    features["max_ghz"] = float(ghz.group(1)) if ghz else 0

    # 내장 그래픽 유무
    features["has_igpu"] = 1 if "내장그래픽:탑재" in specs else 0

    # 정품/벌크
    features["is_bulk"] = 1 if "벌크" in product else 0

    # 세대 추출
    gen = re.search(r"(\d+)세대", product)
    features["generation"] = int(gen.group(1)) if gen else 0

    # 시리즈2 여부 (최신)
    features["is_series2"] = 1 if "시리즈2" in product else 0

    return features


def extract_monitor_features(row):
    """게이밍 모니터 스펙에서 특성 추출

    스펙 텍스트 예시:
    "모니터 / 68.47cm(27인치) / QHD(2560 x 1440) / 120Hz / IPS / 와이드(16:9) /
     5ms(GTG) / 350nits / 1,000:1 / 피벗(회전) / 엘리베이션(높낮이) / 틸트(상하)"

    정규식은 다나와 '게이밍모니터' 검색 결과 40건을 실측해서 맞췄다.
    곡률(1500R)은 15%에만 있어 없으면 0(평면)으로 둔다.
    """
    specs = str(row.get("specs", ""))
    features = {}

    # 화면 크기 (인치)
    inch = re.search(r"(\d+(?:\.\d+)?)\s*인치", specs)
    features["panel_inch"] = float(inch.group(1)) if inch else 0

    # 해상도 — 총 픽셀 수로 환산해야 FHD/QHD/4K가 하나의 연속 변수가 된다
    res = re.search(r"\((\d{3,4})\s*x\s*(\d{3,4})\)", specs)
    features["pixels_mp"] = round(int(res.group(1)) * int(res.group(2)) / 1_000_000, 2) if res else 0

    # 주사율 (Hz) — 가격을 가장 크게 가르는 축
    hz = re.search(r"(\d{2,4})\s*Hz", specs)
    features["refresh_hz"] = int(hz.group(1)) if hz else 0

    # 응답속도 (ms) — 측정방식 괄호(GTG/MPRT/OD/MBR)는 없을 수도 있다
    ms = re.search(r"(\d+(?:\.\d+)?)\s*ms", specs)
    features["response_ms"] = float(ms.group(1)) if ms else 0

    # 밝기 (nits)
    nits = re.search(r"(\d+)\s*nits", specs)
    features["brightness_nits"] = int(nits.group(1)) if nits else 0

    # 명암비 — ':1' 앵커가 없으면 화면비(16:9)를 잘못 집는다
    contrast = re.search(r"([\d,]+):1", specs)
    features["contrast_ratio"] = int(contrast.group(1).replace(",", "")) if contrast else 0

    # 곡률 (R) — 평면은 0
    curve = re.search(r"(\d{3,4})\s*R", specs)
    features["curvature_r"] = int(curve.group(1)) if curve else 0

    # 패널 등급 — 긴 이름부터 매칭해야 'Fast IPS'가 'IPS'로 먼저 잡히지 않는다
    features["is_oled"] = 1 if re.search(r"QD-OLED|OLED", specs) else 0
    features["is_fast_ips"] = 1 if re.search(r"Nano-IPS Black|IPS Black|Fast IPS", specs) else 0

    # 울트라와이드 여부
    features["is_ultrawide"] = 1 if "울트라와이드" in specs else 0

    # 스탠드 조절 기능 개수 (틸트/엘리베이션/스위블/피벗)
    features["stand_features"] = sum(
        1 for kw in ("틸트", "엘리베이션", "스위블", "피벗") if kw in specs
    )

    return features


# ============================
# 카테고리별 특성 추출 매핑
# ============================
FEATURE_EXTRACTORS = {
    "게이밍 노트북": extract_notebook_features,
    "DDR5 RAM": extract_ram_features,
    "NVMe SSD": extract_ssd_features,
    "그래픽카드": extract_gpu_features,
    "CPU": extract_cpu_features,
    "게이밍 모니터": extract_monitor_features,
}


# ============================
# 특성명 한글 라벨 (대시보드 표시용)
# ============================
FEATURE_LABELS = {
    "screen_inch": "화면 크기(인치)",
    "weight_kg": "무게(kg)",
    "brightness_nit": "밝기(nit)",
    "cpu_ghz": "CPU 클럭(GHz)",
    "ssd_gb": "SSD 용량(GB)",
    "ram_gb": "RAM 용량(GB)",
    "clock_mhz": "클럭(MHz)",
    "cl_timing": "CL 타이밍",
    "voltage": "전압(V)",
    "capacity_gb": "용량(GB)",
    "is_pack": "2개입 묶음",
    "has_led": "RGB/LED",
    "pcie_gen": "PCIe 세대",
    "read_speed": "순차읽기(MB/s)",
    "write_speed": "순차쓰기(MB/s)",
    "has_dram": "DRAM 탑재",
    "is_tlc": "TLC 낸드",
    "is_external": "외장형",
    "gpu_model": "GPU 모델번호",
    "vram_gb": "VRAM(GB)",
    "boost_mhz": "부스트 클럭(MHz)",
    "length_mm": "카드 길이(mm)",
    "power_w": "정격 파워(W)",
    "total_cores": "총 코어 수",
    "max_ghz": "최대 클럭(GHz)",
    "has_igpu": "내장그래픽",
    "is_bulk": "벌크 제품",
    "generation": "세대",
    "is_series2": "시리즈2(최신)",
    "panel_inch": "화면 크기(인치)",
    "pixels_mp": "해상도(백만 픽셀)",
    "refresh_hz": "주사율(Hz)",
    "response_ms": "응답속도(ms)",
    "brightness_nits": "밝기(nits)",
    "contrast_ratio": "명암비",
    "curvature_r": "곡률(R)",
    "is_oled": "OLED 패널",
    "is_fast_ips": "고속 IPS 패널",
    "is_ultrawide": "울트라와이드",
    "stand_features": "스탠드 조절 기능 수",
}


# ============================
# 모델 학습 & 평가
# ============================
def train_model(category):
    """카테고리별 가격 예측 모델 학습
    
    1. 해당 카테고리 데이터 필터링
    2. 스펙에서 특성 추출
    3. LinearRegression + RandomForest 학습
    4. 교차 검증으로 정확도 평가
    
    반환: (모델, 특성명 리스트, 스케일러, 평가 결과)
    """
    df = load_prices()
    cat_df = df[df["category"] == category].copy()

    if len(cat_df) < 5:
        print(f"[!] [{category}] 데이터가 {len(cat_df)}개로 부족해요. (최소 5개 필요)")
        return None

    extractor = FEATURE_EXTRACTORS.get(category)
    if not extractor:
        print(f"[!] [{category}] 특성 추출기가 없어요.")
        return None

    # 특성 추출
    features_list = []
    for _, row in cat_df.iterrows():
        features_list.append(extractor(row))

    features_df = pd.DataFrame(features_list)

    # 0이 아닌 값이 있는 컬럼만 사용 (전부 0인 특성은 의미 없음)
    useful_cols = [col for col in features_df.columns if features_df[col].sum() != 0]
    if not useful_cols:
        print(f"[!] [{category}] 유용한 특성을 추출하지 못했어요.")
        return None

    X = features_df[useful_cols].values
    y = cat_df["price"].values

    # 같은 상품(pcode, 없으면 상품명)이 여러 수집일에 걸쳐 거의 동일한 스펙/가격으로
    # 중복 등장하기 때문에, 일반 KFold로 섞으면 같은 상품이 train/test에 동시에 들어가
    # R2가 과대평가된다(사실상 정답을 외워서 맞히는 셈). GroupKFold로 같은 상품은
    # 항상 같은 fold에만 속하게 해서 "본 적 없는 상품"에 대한 일반화 성능을 측정한다.
    groups = cat_df.apply(
        lambda r: r["pcode"] if pd.notna(r.get("pcode")) and str(r.get("pcode")).strip() else r["product"],
        axis=1,
    ).values
    n_groups = len(set(groups))
    cv_n = min(5, n_groups)
    cv = GroupKFold(n_splits=cv_n) if cv_n >= 2 else None

    # 모델 1: Linear Regression (Pipeline으로 스케일링 포함)
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression())
    ])

    # 모델 2: Random Forest (트리 기반이라 스케일링 불필요하지만 일관성을 위해 Pipeline 사용)
    rf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    if cv is not None:
        lr_scores = cross_val_score(lr_pipeline, X, y, groups=groups, cv=cv, scoring="r2")
        rf_scores = cross_val_score(rf_pipeline, X, y, groups=groups, cv=cv, scoring="r2")
    else:
        # 상품 종류가 2개 미만이면 그룹 분할 자체가 불가능 — 교차검증 없이 학습만 진행
        lr_scores = rf_scores = np.array([0.0])

    # 더 나은 모델 선택
    if rf_scores.mean() > lr_scores.mean():
        best_pipeline = rf_pipeline
        best_name = "Random Forest"
        best_score = rf_scores.mean()
    else:
        best_pipeline = lr_pipeline
        best_name = "Linear Regression"
        best_score = lr_scores.mean()

    # out-of-fold 예측으로 잔차 분포 계산 → 예측 신뢰구간(80% 구간)에 사용
    try:
        if cv is not None:
            oof_pred = cross_val_predict(best_pipeline, X, y, groups=groups, cv=cv)
        else:
            oof_pred = best_pipeline.fit(X, y).predict(X)
        residuals = y - oof_pred
        residual_p10 = float(np.percentile(residuals, 10))
        residual_p90 = float(np.percentile(residuals, 90))
    except ValueError:
        residual_p10 = residual_p90 = 0.0

    # 전체 데이터로 최종 학습
    best_pipeline.fit(X, y)

    # 스케일러 추출 (예측 시 사용)
    scaler = best_pipeline.named_steps["scaler"]
    model = best_pipeline.named_steps["model"]

    return {
        "model": model,
        "model_name": best_name,
        "features": useful_cols,
        "scaler": scaler,
        "lr_r2": lr_scores.mean(),
        "rf_r2": rf_scores.mean(),
        "best_r2": best_score,
        "data_count": len(cat_df),
        "category": category,
        "residual_p10": residual_p10,
        "residual_p90": residual_p90,
    }


def predict_price(model_info, features_dict):
    """학습된 모델로 가격 예측
    
    features_dict: {"capacity_gb": 32, "clock_mhz": 6000, ...}
    """
    model = model_info["model"]
    scaler = model_info["scaler"]
    feature_names = model_info["features"]

    # 입력 특성을 모델이 기대하는 순서로 정렬
    X = np.array([[features_dict.get(f, 0) for f in feature_names]])
    X_scaled = scaler.transform(X)

    predicted = model.predict(X_scaled)[0]
    return max(0, predicted)  # 음수 방지


def predict_price_range(model_info, features_dict):
    """예측가 + 신뢰구간(80%). out-of-fold 잔차의 10~90 퍼센타일을 예측값에 더해 범위를 만든다."""
    predicted = predict_price(model_info, features_dict)
    low = max(0, predicted + model_info.get("residual_p10", 0))
    high = max(0, predicted + model_info.get("residual_p90", 0))
    return predicted, low, high


def compute_fair_price_score(actual_price, predicted_price, hist_min=None, hist_max=None, is_anomaly_high=False):
    """0~100점 적정가 점수 (회귀 모델이 아니라 순수 규칙 기반 조합). 50점이 "중립" 기준.

    - 예측가(ML) 대비 저렴할수록 가점, 비쌀수록 감점 (1%당 1점)
    - 과거 최저가~최고가 구간에서 중앙값 대비 최저가 쪽이면 가점, 최고가 쪽이면 감점(최대 ±30점)
    - 고가 이상치로 탐지되면 15점 감점

    반환: (score: int 0~100, label: str)
    """
    score = 50.0

    if predicted_price and predicted_price > 0:
        diff_pct = (actual_price - predicted_price) / predicted_price * 100
        score -= diff_pct

    if hist_min is not None and hist_max is not None and hist_max > hist_min:
        position = (actual_price - hist_min) / (hist_max - hist_min)
        position = min(max(position, 0.0), 1.0)
        score += (0.5 - position) * 60  # 최저가=+30, 중앙=0, 최고가=-30

    if is_anomaly_high:
        score -= 15

    score = int(round(min(max(score, 0.0), 100.0)))

    if score >= 80:
        label = "훌륭한 가격"
    elif score >= 60:
        label = "괜찮은 가격"
    elif score >= 40:
        label = "보통"
    else:
        label = "비싼 편"

    return score, label


def compute_feature_contributions(model_info, features_dict):
    """스펙별 가격 기여도.

    모든 특성을 '학습 데이터 평균'(스케일 기준 0)으로 고정한 기준선(baseline) 예측가에서,
    특성 하나씩만 실제 값으로 바꿨을 때 예측가가 얼마나 움직이는지를 그 특성의 기여도로 본다.
    모델 종류(선형/트리 기반)에 관계없이 동일하게 적용 가능한 단순 marginal contribution 방식.
    """
    model = model_info["model"]
    scaler = model_info["scaler"]
    feature_names = model_info["features"]

    X_scaled = scaler.transform([[features_dict.get(f, 0) for f in feature_names]])
    baseline_scaled = np.zeros((1, len(feature_names)))
    baseline_pred = model.predict(baseline_scaled)[0]

    contributions = []
    for i, fname in enumerate(feature_names):
        X_partial = baseline_scaled.copy()
        X_partial[0, i] = X_scaled[0, i]
        partial_pred = model.predict(X_partial)[0]
        contributions.append({
            "feature": fname,
            "label": FEATURE_LABELS.get(fname, fname),
            "value": features_dict.get(fname, 0),
            "contribution": partial_pred - baseline_pred,
        })
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions, baseline_pred


def find_similar_products(cat_df, target_features, extractor, model_info, exclude_product=None, top_n=5):
    """스펙(스케일된 특성 공간에서의 거리)이 가장 비슷한 다른 제품들을 찾는다."""
    scaler = model_info["scaler"]
    feature_names = model_info["features"]

    target_vec = scaler.transform([[target_features.get(f, 0) for f in feature_names]])[0]

    rows = []
    for _, row in cat_df.iterrows():
        if exclude_product is not None and row["product"] == exclude_product:
            continue
        feats = extractor(row)
        vec = scaler.transform([[feats.get(f, 0) for f in feature_names]])[0]
        distance = float(np.linalg.norm(vec - target_vec))
        rows.append({"product": row["product"], "price": row["price"], "distance": distance})

    if not rows:
        return pd.DataFrame(columns=["product", "price", "distance"])

    similar_df = pd.DataFrame(rows).sort_values("distance").head(top_n).reset_index(drop=True)
    return similar_df


# ============================
# 전체 분석 리포트
# ============================
def run_analysis():
    """모든 카테고리 모델 학습 & 리포트"""
    df = load_prices()
    print(f"📊 전체 데이터: {len(df)}개 상품\n")

    results = {}

    for category in FEATURE_EXTRACTORS:
        print(f"{'='*60}")
        print(f"🤖 [{category}] 모델 학습 중...")
        print(f"{'='*60}")

        result = train_model(category)
        if result is None:
            continue

        results[category] = result

        print(f"   데이터: {result['data_count']}개")
        print(f"   사용 특성: {', '.join(result['features'])}")
        print(f"   Linear Regression R²: {result['lr_r2']:.4f}")
        print(f"   Random Forest R²: {result['rf_r2']:.4f}")
        print(f"   ✅ 선택된 모델: {result['model_name']} (R²: {result['best_r2']:.4f})")

        # R² 해석
        r2 = result["best_r2"]
        if r2 > 0.8:
            quality = "🟢 우수 — 스펙으로 가격의 80% 이상 설명 가능"
        elif r2 > 0.5:
            quality = "🟡 보통 — 스펙 외 다른 요인(브랜드, 시장)도 영향"
        elif r2 > 0:
            quality = "🟠 낮음 — 데이터가 더 쌓이면 개선될 수 있어요"
        else:
            quality = "🔴 부족 — 현재 특성으로는 예측이 어려워요"
        print(f"   모델 품질: {quality}")

    # 예측 예시
    if results:
        print(f"\n{'='*60}")
        print("🔮 예측 예시")
        print(f"{'='*60}")

        if "DDR5 RAM" in results:
            pred = predict_price(results["DDR5 RAM"], {
                "clock_mhz": 6000, "cl_timing": 30,
                "voltage": 1.35, "capacity_gb": 32,
                "is_pack": 1, "has_led": 1
            })
            print(f"\n   DDR5 6000MHz CL30 32GB(16Gx2) RGB")
            print(f"   → 예측 가격: {pred:,.0f}원")

        if "그래픽카드" in results:
            pred = predict_price(results["그래픽카드"], {
                "gpu_model": 5070, "vram_gb": 12,
                "boost_mhz": 2500, "length_mm": 300,
                "power_w": 650
            })
            print(f"\n   RTX 5070 12GB, 2500MHz 부스트")
            print(f"   → 예측 가격: {pred:,.0f}원")

        if "CPU" in results:
            pred = predict_price(results["CPU"], {
                "total_cores": 14, "max_ghz": 5.2,
                "has_igpu": 1, "is_bulk": 0,
                "generation": 14, "is_series2": 0
            })
            print(f"\n   인텔 14세대 14코어, 5.2GHz, 내장그래픽, 정품")
            print(f"   → 예측 가격: {pred:,.0f}원")

    return results


if __name__ == "__main__":
    run_analysis()