"""GitHub Pages 정적 데모용 데이터 내보내기.

서버 없이 화면만 돌아가게, 실제 FastAPI 앱을 읽기전용으로 띄워 각 엔드포인트 응답을
JSON 파일로 떠 둔다. 응답을 다시 만들지 않고 API가 돌려준 그대로 저장하므로
데모 화면은 실제 서버와 같은 숫자를 보여 준다(가공은 frontend/src/api/staticDemo.ts 몫).

나가는 파일 (기본 demo/data/):
    health.json, categories.json, anomalies.json, changes.json, alerts.json,
    spotlights.json, scrape-runs.json, watchlist.json, news.json
    prices.json                 최신 수집일 전체 상품 (화면에서 카테고리·검색·정렬·페이지 처리)
    pulse.json, laptops.json    {카테고리: 응답}
    products/<접두어>.json       {상품번호: 상세}      접두어 = 상품번호의 '-' 앞 (예: RAM-12 → RAM)
    prediction/<접두어>.json     {상품번호: 예측}      모델이 없는 카테고리는 빠진다
    compare/<접두어>.json        {상품번호: {product, specs}}  비교 화면이 2~5개를 골라 조합한다

뉴스는 내보내지 않는다(빈 목록). 원문 수집을 robots.txt 때문에 중단했으니 재배포도 하지 않는다.
공개 데모 갱신은 매일 배치의 scripts/publish_demo.py 가 이 export() 를 불러 demo-data 브랜치로 올린다.

사용법 (로컬 확인용 — demo/ 는 git 이 무시한다):
    python scripts/export_static_demo.py            # demo/data/ 를 새로 만든다
    python scripts/export_static_demo.py --out D:/tmp/demo-data
"""

import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "demo", "data")

# 프론트(staticDemo.ts)가 code.split("-")[0] 으로 묶음 파일을 찾는다 — 형식이 다르면 여기서 멈춘다.
CODE_PATTERN = re.compile(r"^[A-Z]+-\d+$")
# 공개 파일에 PC 경로가 섞이면 안 된다(수집 실패 메시지 등).
LOCAL_PATH = re.compile(r"[A-Za-z]:\\|\\Users\\|/home/|/Users/")

FIXED = ["health", "categories", "anomalies", "changes", "alerts", "spotlights", "scrape-runs", "watchlist"]


def _get(client, path: str, **params):
    res = client.get(path, params=params or None)
    if res.status_code != 200:
        raise RuntimeError(f"{path} → {res.status_code}: {res.text[:200]}")
    return res.json()


def _codes_in(obj, found: set) -> None:
    """응답 어디에든 들어 있는 상품번호를 모은다 — 화면이 링크할 수 있는 상세 페이지 전부."""
    if isinstance(obj, dict):
        code = obj.get("code")
        if isinstance(code, str):
            found.add(code)
        for v in obj.values():
            _codes_in(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _codes_in(v, found)


def _check_no_local_paths(name: str, obj) -> None:
    text = json.dumps(obj, ensure_ascii=False)
    m = LOCAL_PATH.search(text)
    if m:
        raise RuntimeError(f"{name} 에 PC 경로가 들어 있어요: …{text[max(0, m.start() - 40): m.end() + 40]}…")


def export(out_dir: str) -> dict:
    os.environ["MARKET_PULSE_READONLY"] = "1"
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    files: dict[str, object] = {}

    for name in FIXED:
        files[f"{name}.json"] = _get(client, f"/api/{name}")
    files["news.json"] = {"items": []}

    items: list = []
    while True:
        page = _get(client, "/api/prices", limit=500, offset=len(items), sort="price_asc")
        items += page["items"]
        if not page["items"] or len(items) >= page["total"]:
            break
    files["prices.json"] = {"items": items, "total": len(items)}

    categories = [c["category"] for c in files["categories.json"]["categories"]]
    files["pulse.json"] = {c: _get(client, f"/api/categories/{c}/pulse") for c in categories}
    files["laptops.json"] = {c: _get(client, f"/api/laptops/{c}") for c in categories if c.endswith("노트북")}

    codes: set = set()
    for obj in files.values():
        _codes_in(obj, codes)
    bad = sorted(c for c in codes if not CODE_PATTERN.match(c))
    if bad:
        raise RuntimeError(f"상품번호 형식이 예상과 달라요: {bad[:10]}")

    bundles: dict[str, dict] = defaultdict(dict)
    for code in sorted(codes):
        prefix = code.split("-")[0]
        detail = client.get(f"/api/products/{code}")
        if detail.status_code != 200:
            continue  # 예전 목록에만 남은 상품 — 데모에서도 '찾을 수 없어요'로 보인다
        bundles[f"products/{prefix}.json"][code] = detail.json()

        pred = client.get(f"/api/prediction/{code}")
        if pred.status_code == 200:
            bundles[f"prediction/{prefix}.json"][code] = pred.json()

        # 비교는 상품마다 따로 계산된다(compare.py) — 같은 상품 둘로 불러 한 개 몫을 떼어 둔다.
        cmp = client.get("/api/compare", params={"codes": f"{code},{code}"})
        if cmp.status_code == 200:
            body = cmp.json()
            bundles[f"compare/{prefix}.json"][code] = {
                "product": body["products"][0],
                "specs": [{"label": row["label"], "value": row["values"][0]} for row in body["spec_table"]],
            }
    files.update(bundles)

    for name, obj in files.items():
        _check_no_local_paths(name, obj)

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for name, obj in files.items():
        path = os.path.join(out_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))

    return {
        "snapshot": files["health.json"].get("last_scrape_date"),
        "products": len(items),
        "details": sum(len(v) for k, v in bundles.items() if k.startswith("products/")),
        "files": len(files),
        "bytes": sum(os.path.getsize(os.path.join(out_dir, n)) for n in files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()
    summary = export(args.out)
    print(f"{summary['snapshot']} 수집분 · 상품 {summary['products']}개 · 상세 {summary['details']}개 · "
          f"파일 {summary['files']}개 · {summary['bytes'] / 1024 / 1024:.1f}MB → {args.out}")


if __name__ == "__main__":
    main()
