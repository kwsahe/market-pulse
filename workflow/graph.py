# workflow/graph.py
# LangGraph 워크플로우 정의 (StateGraph 기반)

from langgraph.graph import StateGraph, END
from workflow.state import ReportState
from workflow.nodes import (
    node_init_db,
    node_collect_prices,
    node_collect_news,
    node_analyze_changes,
    node_detect_anomalies,
    node_analyze_trends,
    node_generate_report,
    node_finalize,
)
from workflow.checkpoint import save_checkpoint

def should_continue(state: ReportState) -> str:
    """상태 확인 후 다음 단계 결정"""
    if state.get("status") == "failed":
        return "error"
    return "continue"


def build_workflow() -> StateGraph:
    """워크플로우 그래프 구성"""
    workflow = StateGraph(ReportState)

    # 노드 추가
    workflow.add_node("init_db", node_init_db)
    workflow.add_node("collect_prices", node_collect_prices)
    workflow.add_node("collect_news", node_collect_news)
    workflow.add_node("analyze_changes", node_analyze_changes)
    workflow.add_node("detect_anomalies", node_detect_anomalies)
    workflow.add_node("analyze_trends", node_analyze_trends)
    workflow.add_node("generate_report", node_generate_report)
    workflow.add_node("finalize", node_finalize)

    # 진입점
    workflow.set_entry_point("init_db")

    # 순차 실행 연결
    workflow.add_edge("init_db", "collect_prices")
    workflow.add_edge("collect_prices", "collect_news")
    workflow.add_edge("collect_news", "analyze_changes")
    workflow.add_edge("analyze_changes", "detect_anomalies")
    workflow.add_edge("detect_anomalies", "analyze_trends")
    workflow.add_edge("analyze_trends", "generate_report")
    workflow.add_edge("generate_report", "finalize")
    workflow.add_edge("finalize", END)

    # 조건부 에러 처리 (각 단계 후 체크포인트 저장)
    workflow.add_conditional_edges(
        "init_db",
        should_continue,
        {"continue": "collect_prices", "error": END}
    )
    workflow.add_conditional_edges(
        "collect_prices",
        should_continue,
        {"continue": "collect_news", "error": END}
    )
    workflow.add_conditional_edges(
        "collect_news",
        should_continue,
        {"continue": "analyze_changes", "error": END}
    )
    workflow.add_conditional_edges(
        "analyze_changes",
        should_continue,
        {"continue": "detect_anomalies", "error": END}
    )
    workflow.add_conditional_edges(
        "detect_anomalies",
        should_continue,
        {"continue": "analyze_trends", "error": END}
    )
    workflow.add_conditional_edges(
        "analyze_trends",
        should_continue,
        {"continue": "generate_report", "error": END}
    )
    workflow.add_conditional_edges(
        "generate_report",
        should_continue,
        {"continue": "finalize", "error": END}
    )

    return workflow


def run_workflow() -> ReportState:
    """워크플로우 실행 (체크포인트 자동 저장)"""
    workflow = build_workflow()
    app = workflow.compile()
    
    from workflow.state import create_initial_state
    initial_state = create_initial_state()
    
    print(f"=== 워크플로우 시작: {initial_state['run_id']} ===")
    
    # 상태 저장 콜백 (각 단계 후)
    def save_state_callback(state):
        if isinstance(state, dict):
            save_checkpoint(state, state.get("run_id", "unknown"))
    
    # 실행
    result = app.invoke(initial_state)
    
    # 최종 상태 저장
    save_checkpoint(result, result.get("run_id", "unknown"))
    
    print(f"=== 워크플로우 완료: {result['status']} ===")
    
    return result


if __name__ == "__main__":
    run_workflow()