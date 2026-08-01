# dashboard/tabs/scrapes.py
# 수집 실행 이력 탭 — scrape_runs 테이블 조회

from database.db_manager import load_scrape_runs
from dashboard.theme import section_header, GREEN, RED, AMBER
import streamlit as st


def render() -> None:
    section_header("🛰️", "수집 실행 이력", "가격/뉴스 스크래퍼가 언제, 얼마나 성공적으로 돌았는지 확인해요.")

    runs_df = load_scrape_runs(limit=50)
    if runs_df.empty:
        st.info("아직 수집 실행 기록이 없어요.")
        return

    latest_by_source = runs_df.sort_values("id").groupby("source").tail(1)
    run_cols = st.columns(len(latest_by_source))
    for col, (_, rrow) in zip(run_cols, latest_by_source.iterrows()):
        with col:
            st.metric(f"최근 {rrow['source']} 수집", rrow["status"], delta=None)
            st.caption(f"{rrow['started_at']} · 수집 {rrow['fetched_count']}개 · 신규 {rrow['inserted_count']}개")
            if rrow["status"] == "failed" and rrow.get("error_message"):
                st.caption(f"❌ {rrow['error_message']}")

    st.divider()

    total_runs = len(runs_df)
    success_runs = len(runs_df[runs_df["status"] == "success"])
    fail_runs = len(runs_df[runs_df["status"] == "failed"])
    running_runs = len(runs_df[runs_df["status"] == "running"])
    sum_cols = st.columns(4)
    with sum_cols[0]:
        st.metric("전체 실행", f"{total_runs}회")
    with sum_cols[1]:
        st.metric("성공", f"{success_runs}회")
    with sum_cols[2]:
        st.metric("실패", f"{fail_runs}회")
    with sum_cols[3]:
        st.metric("진행 중", f"{running_runs}회")

    st.divider()
    st.markdown("**📜 최근 실행 목록**")
    display_df = runs_df[["id", "source", "started_at", "finished_at", "fetched_count", "inserted_count", "status", "error_message"]].copy()
    display_df.columns = ["#", "소스", "시작", "종료", "수집", "신규", "상태", "에러"]
    st.dataframe(display_df, hide_index=True, width="stretch")
