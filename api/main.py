# api/main.py
# Market Pulse React 프론트엔드용 FastAPI 앱. dashboard/app.py(Streamlit, 8010포트)는 건드리지 않고
# 그 옆에 REST API를 추가한다.
#
# 배포 시에는 이 앱이 프론트 빌드 산출물(frontend/dist)까지 같은 오리진에서 서빙한다.
# 오리진이 하나면 CORS가 "설정할 것"이 아니라 "존재하지 않는 것"이 되고,
# 도메인·배포 산출물·인증 지점이 각각 하나로 줄어든다.

import os
import sqlite3
from datetime import date

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database.db_manager import DB_PATH
from api.routers import (
    alerts, anomalies, categories, changes, compare, laptops, news, prediction,
    prices, products, scrapes, spotlights, watchlist,
)

# 공개 배포용 읽기전용 모드.
# 워치리스트 쓰기 라우트(POST /api/watchlist/{pcode}, PUT .../target)는 인증이 전혀 없어서,
# 공개 URL에 그대로 노출하면 누구나 추적 목록과 목표가를 바꿀 수 있다.
# 인증을 새로 만드는 대신 그 라우트를 **등록하지 않는다** — 인증 코드 0줄로 노출면이 사라진다.
# (조회는 무해하므로 남긴다. 아래 include_router 부분 참고)
# 워치리스트 편집이 필요하면 같은 PC의 localhost 에서 READONLY 없이 띄우면 된다.
READONLY = os.getenv("MARKET_PULSE_READONLY", "0") == "1"

# 프론트 빌드 산출물 위치. 있으면 같은 오리진에서 서빙한다.
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

app = FastAPI(title="Market Pulse API", version="0.1.0")

# CORS는 개발용(Vite 5173에서 8000을 호출하는 경우)으로만 남긴다.
# 단일 오리진 배포에서는 프론트와 API가 같은 출처라 이 미들웨어를 타지 않는다.
# 추가 오리진이 필요하면 MARKET_PULSE_CORS_ORIGINS 에 콤마로 구분해 넣는다.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [o.strip() for o in os.getenv("MARKET_PULSE_CORS_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"] if READONLY else ["GET", "POST", "PUT"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(prices.router)
app.include_router(products.router)
app.include_router(anomalies.router)
app.include_router(prediction.router)
app.include_router(compare.router)
app.include_router(scrapes.router)
app.include_router(news.router)
app.include_router(changes.router)
app.include_router(alerts.router)
app.include_router(spotlights.router)
app.include_router(laptops.router)

# 워치리스트 **조회**는 무해하다 — 위험한 건 인증 없는 쓰기다.
# 라우터를 통째로 빼면 GET /api/watchlist 가 SPA 폴백에 걸려 HTML을 돌려주고
# 프론트가 JSON 파싱 에러로 죽으므로, 비-GET 라우트만 뺀 사본을 만들어 등록한다.
#
# 원본 watchlist.router 는 건드리지 않는다. 공유 라우터 객체를 직접 잘라내면 그 변경이
# 모듈에 남아서, 같은 프로세스에서 나중에 쓰기 모드로 앱을 만들어도 쓰기 라우트가 사라진 채로 뜬다.
# (app.routes 를 거르는 방법은 못 쓴다 — FastAPI 0.141부터 include_router 가 개별 라우트를
#  펼치지 않고 _IncludedRouter 참조 하나만 넣기 때문에 경로로 걸러낼 수가 없다.)
if READONLY:
    _readonly_watchlist = APIRouter()
    # 라우트 객체는 선언 시점에 이미 prefix가 반영된 전체 경로를 갖고 있어서,
    # prefix 없는 라우터에 그대로 옮겨 담으면 경로가 유지된다.
    _readonly_watchlist.routes = [
        route for route in watchlist.router.routes
        if set(getattr(route, "methods", set())) <= {"GET", "HEAD"}
    ]
    app.include_router(_readonly_watchlist)
else:
    app.include_router(watchlist.router)


@app.get("/api/health")
def health():
    """서비스 상태 + **데이터 신선도**.

    예전에는 {"status": "ok"} 고정이라 DB가 비어 있어도 ok를 반환해서 배포 검증에 쓸 수 없었다.
    이 프로젝트의 가장 그럴듯한 실패는 서버가 죽는 게 아니라 수집이 조용히 멈추는 것이므로,
    "언제 수집된 데이터인지"를 1급 정보로 돌려준다. 프론트 헤더가 이 값을 배지로 띄운다."""
    info = {
        "status": "ok",
        "readonly": READONLY,
        "last_scrape_date": None,
        "days_stale": None,
        "rows": 0,
        "categories": 0,
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            latest, rows = conn.execute("SELECT MAX(date), COUNT(*) FROM prices").fetchone()
            info["last_scrape_date"] = latest
            info["rows"] = rows or 0
            if latest:
                info["days_stale"] = (date.today() - date.fromisoformat(latest)).days
                info["categories"] = conn.execute(
                    "SELECT COUNT(DISTINCT category) FROM prices WHERE date = ?", (latest,)
                ).fetchone()[0]
        finally:
            conn.close()
    except Exception as e:
        info["status"] = "error"
        info["detail"] = f"{type(e).__name__}: {e}"
        return info

    if not info["rows"]:
        info["status"] = "empty"
    elif info["days_stale"] is not None and info["days_stale"] >= 2:
        # 하루 1회 수집이라 1일 지연은 아직 정상 범위(오늘 배치 전). 2일부터 이상으로 본다.
        info["status"] = "stale"
    return info


# 정적 파일 마운트는 **모든 API 라우트 뒤에** 와야 한다 — 루트("/")에 먼저 붙이면
# 그 아래 모든 경로를 가로채서 /api/* 가 404가 된다.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """React Router 용 SPA 폴백.

        /desk, /products/GN-1 같은 경로는 서버에 실제 파일이 없고 브라우저에서 라우팅된다.
        따라서 정적 파일이 있으면 그걸 주고, 없으면 index.html 을 줘서 프론트가 처리하게 한다.
        (/api/* 는 위에서 이미 등록된 라우터가 먼저 잡으므로 여기까지 오지 않는다)"""
        # 등록되지 않은 /api/* 는 index.html 이 아니라 404 여야 한다.
        # 안 그러면 오타나 라우터 누락이 "HTML을 받아서 JSON 파싱 실패"라는
        # 엉뚱한 증상으로 나타나서 원인을 찾기 어려워진다.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"알 수 없는 API 경로입니다: /{full_path}")

        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        # 경로 탈출 방지 — full_path 는 외부 입력이다
        if candidate.startswith(FRONTEND_DIST) and os.path.isfile(candidate):
            return FileResponse(candidate)
        # index.html 은 매번 재검증시킨다. Cache-Control 이 없으면 브라우저가 Last-Modified 기준
        # 추정 캐시로 옛 화면을 며칠씩 보여준다(재빌드 직후 실측). 해시가 붙은 /assets 는 무관.
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"), headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
