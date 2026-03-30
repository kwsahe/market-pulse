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
import sqlite3
import re
import os
import sys
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "data.db")


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, category, product, price, specs FROM prices",
        conn
    )
    conn.close()
    return df


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


# ============================
# 카테고리별 특성 추출 매핑
# ============================
FEATURE_EXTRACTORS = {
    "게이밍 노트북": extract_notebook_features,
    "DDR5 RAM": extract_ram_features,
    "NVMe SSD": extract_ssd_features,
    "그래픽카드": extract_gpu_features,
    "CPU": extract_cpu_features,
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
        print(f"⚠️ [{category}] 데이터가 {len(cat_df)}개로 부족해요. (최소 5개 필요)")
        return None

    extractor = FEATURE_EXTRACTORS.get(category)
    if not extractor:
        print(f"⚠️ [{category}] 특성 추출기가 없어요.")
        return None

    # 특성 추출
    features_list = []
    for _, row in cat_df.iterrows():
        features_list.append(extractor(row))

    features_df = pd.DataFrame(features_list)

    # 0이 아닌 값이 있는 컬럼만 사용 (전부 0인 특성은 의미 없음)
    useful_cols = [col for col in features_df.columns if features_df[col].sum() != 0]
    if not useful_cols:
        print(f"⚠️ [{category}] 유용한 특성을 추출하지 못했어요.")
        return None

    X = features_df[useful_cols].values
    y = cat_df["price"].values

    # 스케일링 (특성 값 범위 통일)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 모델 1: Linear Regression
    lr = LinearRegression()
    lr_scores = cross_val_score(lr, X_scaled, y, cv=min(5, len(X)), scoring="r2")

    # 모델 2: Random Forest (더 복잡한 패턴 학습 가능)
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_scores = cross_val_score(rf, X_scaled, y, cv=min(5, len(X)), scoring="r2")

    # 더 나은 모델 선택
    if rf_scores.mean() > lr_scores.mean():
        best_model = rf
        best_name = "Random Forest"
        best_score = rf_scores.mean()
    else:
        best_model = lr
        best_name = "Linear Regression"
        best_score = lr_scores.mean()

    # 전체 데이터로 최종 학습
    best_model.fit(X_scaled, y)

    return {
        "model": best_model,
        "model_name": best_name,
        "features": useful_cols,
        "scaler": scaler,
        "lr_r2": lr_scores.mean(),
        "rf_r2": rf_scores.mean(),
        "best_r2": best_score,
        "data_count": len(cat_df),
        "category": category,
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