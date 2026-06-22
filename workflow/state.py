# workflow/state.py
# LangGraph 상태 정의

from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class PriceChangeItem:
    product: str
    category: str
    prev_price: int
    current_price: int
    change: int
    change_pct: float


@dataclass
class AnomalyItem:
    product: str
    category: str
    price: int
    method: str
    detail: str


@dataclass
class NewsItem:
    title: str
    press: str
    published_at: str
    collected_at: str


class ReportState(TypedDict):
    # 실행 메타데이터
    run_id: str
    started_at: str
    status: str  # running, completed, failed
    error: Optional[str]
    
    # 수집 결과
    prices_collected: int
    prices_new: int
    news_collected: int
    news_new: int
    
    # 분석 결과
    price_changes: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    trend_summary: List[Dict[str, Any]]
    
    # 리포트
    report_markdown: str
    report_html: str
    report_path: str
    
    # 통계
    duration_seconds: float
    categories: List[str]
    total_products: int


def create_initial_state() -> ReportState:
    """초기 상태 생성"""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ReportState(
        run_id=run_id,
        started_at=datetime.now().isoformat(),
        status="running",
        error=None,
        prices_collected=0,
        prices_new=0,
        news_collected=0,
        news_new=0,
        price_changes=[],
        anomalies=[],
        trend_summary=[],
        report_markdown="",
        report_html="",
        report_path="",
        duration_seconds=0.0,
        categories=[],
        total_products=0,
    )