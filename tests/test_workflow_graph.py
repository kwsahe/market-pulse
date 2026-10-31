# tests/test_workflow_graph.py
# 회귀: LangGraph 워크플로에 뉴스 수집 단계가 남아 있으면 robots.txt 가 전면 금지(Disallow: /)한
# news.naver.com 을 긁는다. 매일 수집(run_scrapers.bat)에서는 껐는데 이 워크플로에만 남아 있었다.

import pytest

pytest.importorskip("langgraph")  # requirements.txt 에는 있다 — CI는 설치하고 돌린다


def test_workflow_has_no_news_collection_step():
    from workflow.graph import build_workflow
    graph = build_workflow()
    assert "collect_news" not in graph.nodes
    assert {"collect_prices", "analyze_changes", "generate_report"} <= set(graph.nodes)
    graph.compile()  # 뉴스 단계를 빼며 끊긴 연결이 있으면 여기서 실패한다
