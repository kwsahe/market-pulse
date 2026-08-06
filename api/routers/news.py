# api/routers/news.py
# GET /api/news — dashboard/tabs/news.py 로직 이식. 데이터셋이 작아(수백 건) 언론사 필터는
# 서버 왕복 없이 프론트에서 클라이언트 필터링한다(원본도 전체 news_df를 한 번만 넘겨받음).

from fastapi import APIRouter

from database.db_manager import load_news
from api.deps import data_cache
from api.schemas import NewsItem, NewsResponse

router = APIRouter(prefix="/api/news", tags=["news"])


@data_cache
def _load_news_cached():
    return load_news()


@router.get("", response_model=NewsResponse)
def get_news() -> NewsResponse:
    news_df = _load_news_cached()
    items = [
        NewsItem(
            collected_at=row["collected_at"], press=row.get("press"),
            title=row["title"], published_at=row.get("published_at"),
        )
        for _, row in news_df.iterrows()
    ]
    return NewsResponse(items=items)
