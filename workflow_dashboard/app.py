# workflow_dashboard/app.py
# LangGraph 워크플로우 제어 및 리포트 뷰어 대시보드

import streamlit as st
import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.main import main as run_workflow
from workflow.state import create_initial_state

# 설정
st.set_page_config(page_title="Market Pulse Workflow", page_icon="🔄", layout="wide")
st.title("🔄 Market Pulse Workflow Dashboard")
st.caption("LangGraph 기반 자동 리포트 생성 및 모니터링")

# reports 폴더 경로
reports_dir = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports"))
reports_dir.mkdir(exist_ok=True)

# 사이드바
st.sidebar.header("🎮 제어")

run_now = st.sidebar.button("🚀 워크플로우 실행", type="primary")
clear_reports = st.sidebar.button("🗑️ 리포트 삭제")

# 리포트 목록
st.sidebar.subheader("📁 이전 리포트")
report_files = sorted(reports_dir.glob("report_*.md"), reverse=True)

if report_files:
    selected_report = st.sidebar.selectbox(
        "리포트 선택",
        options=[f for f in report_files],
        format_func=lambda x: x.stem.replace("report_", "")
    )
else:
    selected_report = None
    st.sidebar.info("리포트가 없습니다.")

# 메인 콘텐츠
if run_now:
    st.info("⏳ 워크플로우 실행 중...")
    with st.spinner("단계별 진행 상황을 확인하세요..."):
        try:
            result = run_workflow()
            st.success("✅ 워크플로우 완료!")
            
            # 결과 요약
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("가격 데이터", f"{result['prices_collected']}개", f"+{result['prices_new']}")
            with col2:
                st.metric("뉴스 데이터", f"{result['news_collected']}개", f"+{result['news_new']}")
            with col3:
                st.metric("가격 변동", f"{len(result['price_changes'])}개")
            with col4:
                st.metric("이상치", f"{len(result['anomalies'])}개")
            
            # 리포트 내용 표시
            if result['report_markdown']:
                st.divider()
                st.subheader("📄 리포트 미리보기")
                st.markdown(result['report_markdown'])
            
            # 파일 링크
            if result['report_path'] and os.path.exists(result['report_path']):
                html_path = result['report_path'].replace('.md', '.html')
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"[📥 Markdown 다운로드]({result['report_path']})")
                with col2:
                    if os.path.exists(html_path):
                        st.markdown(f"[🌐 HTML 뷰어]({html_path})")
                        
        except Exception as e:
            st.error(f"❌ 실행 실패: {e}")
            st.exception(e)

elif selected_report:
    # 리포트 표시
    run_id = selected_report.stem.replace("report_", "")
    st.subheader(f"📄 리포트: {run_id}")
    
    with open(selected_report, "r", encoding="utf-8") as f:
        content = f.read()
    
    st.markdown(content)
    
    # HTML 버전이 있으면 링크
    html_path = str(selected_report).replace('.md', '.html')
    if os.path.exists(html_path):
        st.markdown(f"[🌐 HTML 버전 보기]({html_path})")

else:
    # 기본 화면
    st.info("👈 사이드바에서 워크플로우를 실행하거나 리포트를 선택하세요.")
    
    # 최근 리포트 미리보기
    if report_files:
        st.subheader("📊 최근 리포트")
        latest = report_files[0]
        with open(latest, "r", encoding="utf-8") as f:
            preview = f.read().split("\n")[:30]
        st.code("\n".join(preview))

# 리포트 삭제
if clear_reports and st.sidebar.checkbox("확인 후 삭제"):
    for f in report_files:
        f.unlink()
    st.success("리포트가 삭제되었습니다.")
    st.rerun()