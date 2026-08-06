# api/routers/scrapes.py
# GET /api/scrape-runs — dashboard/tabs/scrapes.py 로직 이식.

from fastapi import APIRouter, Query

from database.db_manager import load_scrape_runs
from api.deps import data_cache
from api.schemas import ScrapeRun, ScrapeRunLatest, ScrapeRunsResponse, ScrapeRunSummary

router = APIRouter(prefix="/api/scrape-runs", tags=["scrapes"])


@data_cache
def _load_scrape_runs_cached(limit: int):
    return load_scrape_runs(limit=limit)


@router.get("", response_model=ScrapeRunsResponse)
def get_scrape_runs(limit: int = Query(50, ge=1, le=200)) -> ScrapeRunsResponse:
    runs_df = _load_scrape_runs_cached(limit)
    if runs_df.empty:
        return ScrapeRunsResponse(
            latest_by_source=[], summary=ScrapeRunSummary(total=0, success=0, failed=0, running=0), runs=[],
        )

    latest_by_source_df = runs_df.sort_values("id").groupby("source").tail(1)
    latest_by_source = [
        ScrapeRunLatest(
            source=row["source"], status=row["status"], started_at=row["started_at"],
            fetched_count=int(row["fetched_count"]), inserted_count=int(row["inserted_count"]),
            error_message=row.get("error_message"),
        )
        for _, row in latest_by_source_df.iterrows()
    ]

    summary = ScrapeRunSummary(
        total=len(runs_df),
        success=int((runs_df["status"] == "success").sum()),
        failed=int((runs_df["status"] == "failed").sum()),
        running=int((runs_df["status"] == "running").sum()),
    )

    runs = [
        ScrapeRun(
            id=int(row["id"]), source=row["source"], started_at=row["started_at"],
            finished_at=row.get("finished_at"), fetched_count=int(row["fetched_count"]),
            inserted_count=int(row["inserted_count"]), status=row["status"],
            error_message=row.get("error_message"),
        )
        for _, row in runs_df.iterrows()
    ]

    return ScrapeRunsResponse(latest_by_source=latest_by_source, summary=summary, runs=runs)
