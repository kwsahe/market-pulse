# api/main.py
# Market Pulse React 프론트엔드용 FastAPI 앱. dashboard/app.py(Streamlit, 8010포트)는 건드리지 않고
# 그 옆에 REST API를 추가한다.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    alerts, anomalies, categories, changes, compare, laptops, news, prediction,
    prices, products, scrapes, spotlights, watchlist,
)

app = FastAPI(title="Market Pulse API", version="0.1.0")

# 로컬 개발 전용: Vite 기본 포트(5173)만 명시적으로 허용한다.
# Vite가 다른 포트로 뜨면(5173 사용 중일 때 자동으로 5174 등으로 증가) 여기도 같이 갱신해야 한다.
# 워치리스트 추적 토글/목표가 저장이 POST/PUT을 쓰기 시작하면서 GET 외 메서드도 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(prices.router)
app.include_router(products.router)
app.include_router(anomalies.router)
app.include_router(prediction.router)
app.include_router(compare.router)
app.include_router(watchlist.router)
app.include_router(scrapes.router)
app.include_router(news.router)
app.include_router(changes.router)
app.include_router(alerts.router)
app.include_router(spotlights.router)
app.include_router(laptops.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
