# workflow/nodes.py
# LangGraph 노드 함수들

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_db, load_prices, load_news
from ml.anomaly_detection import detect_zscore, detect_iqr
from ml.price_change import detect_price_changes
from ml.trend_analysis import get_price_trend, summarize_trends
from workflow.state import ReportState, create_initial_state


def node_init_db(state: ReportState) -> ReportState:
    """DB 초기화"""
    print("[Node] DB 초기화 중...")
    try:
        init_db()
        state["status"] = "db_ready"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"DB 초기화 실패: {e}"
    return state


def node_collect_prices(state: ReportState) -> ReportState:
    """가격 데이터 수집 (스크래퍼 직접 호출)"""
    print("[Node] 가격 데이터 수집 중...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-u", "scraper/price_scraper.py"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            df = load_prices()
            state["prices_collected"] = len(df)
            # 중복 제외 신규 저장 수 계산 (최신 날짜 기준)
            if not df.empty:
                latest = df[df["date"] == df["date"].max()]
                state["prices_new"] = len(latest)
            state["status"] = "prices_collected"
        else:
            state["status"] = "failed"
            state["error"] = f"가격 수집 실패: {result.stderr}"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"가격 수집 예외: {e}"
    return state


def node_collect_news(state: ReportState) -> ReportState:
    """뉴스 데이터 수집"""
    print("[Node] 뉴스 데이터 수집 중...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-u", "scraper/news_scraper.py"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            df = load_news()
            state["news_collected"] = len(df)
            if not df.empty:
                latest = df[df["collected_at"] == df["collected_at"].max()]
                state["news_new"] = len(latest)
            state["status"] = "news_collected"
        else:
            state["status"] = "failed"
            state["error"] = f"뉴스 수집 실패: {result.stderr}"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"뉴스 수집 예외: {e}"
    return state


def node_analyze_changes(state: ReportState) -> ReportState:
    """가격 변동 분석"""
    print("[Node] 가격 변동 분석 중...")
    try:
        result = detect_price_changes()
        if isinstance(result, tuple):
            changed, latest_date, prev_date = result
            if not changed.empty:
                changes = []
                for _, row in changed.iterrows():
                    changes.append({
                        "product": row["product"],
                        "category": row["category"],
                        "prev_price": int(row["prev_price"]),
                        "current_price": int(row["current_price"]),
                        "change": int(row["change"]),
                        "change_pct": float(row["change_pct"])
                    })
                state["price_changes"] = changes
        state["status"] = "changes_analyzed"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"변동 분석 실패: {e}"
    return state


def node_detect_anomalies(state: ReportState) -> ReportState:
    """이상치 탐지"""
    print("[Node] 이상치 탐지 중...")
    try:
        df = load_prices()
        if not df.empty:
            latest_date = df["date"].max()
            current = df[df["date"] == latest_date]
            
            anomalies = []
            z_anom = detect_zscore(current)
            if not z_anom.empty:
                for _, row in z_anom.iterrows():
                    anomalies.append({
                        "product": row["product"],
                        "category": row["category"],
                        "price": int(row["price"]),
                        "method": "Z-score",
                        "detail": f"Z={row['z_score']:.2f}"
                    })
            
            iqr_anom = detect_iqr(current)
            if not iqr_anom.empty:
                for _, row in iqr_anom.iterrows():
                    anomalies.append({
                        "product": row["product"],
                        "category": row["category"],
                        "price": int(row["price"]),
                        "method": "IQR",
                        "detail": f"범위 {row['lower_bound']:,.0f}~{row['upper_bound']:,.0f}"
                    })
            state["anomalies"] = anomalies
        state["status"] = "anomalies_detected"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"이상치 탐지 실패: {e}"
    return state


def node_analyze_trends(state: ReportState) -> ReportState:
    """트렌드 분석"""
    print("[Node] 트렌드 분석 중...")
    try:
        df = load_prices()
        if not df.empty and df["date"].nunique() >= 2:
            state["trend_summary"] = summarize_trends(df)
            # 카테고리 목록 저장
            state["categories"] = df["category"].unique().tolist()
            state["total_products"] = len(df)
        state["status"] = "trends_analyzed"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"트렌드 분석 실패: {e}"
    return state


def node_generate_report(state: ReportState) -> ReportState:
    """리포트 생성 (Markdown + HTML)"""
    print("[Node] 리포트 생성 중...")
    try:
        from workflow.report_generator import generate_report
        report_md, report_html, report_path = generate_report(state)
        state["report_markdown"] = report_md
        state["report_html"] = report_html
        state["report_path"] = report_path
        state["status"] = "report_generated"
    except Exception as e:
        state["status"] = "failed"
        state["error"] = f"리포트 생성 실패: {e}"
    return state


def node_finalize(state: ReportState) -> ReportState:
    """최종화"""
    state["duration_seconds"] = (
        datetime.fromisoformat(datetime.now().isoformat()) - 
        datetime.fromisoformat(state["started_at"])
    ).total_seconds()
    state["status"] = "completed"
    print(f"[Node] 완료! 소요시간: {state['duration_seconds']:.1f}초")
    return state