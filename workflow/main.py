# workflow/main.py
# 워크플로우 실행 진입점

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.graph import run_workflow
from workflow.state import create_initial_state

def main():
    """워크플로우 실행"""
    print("=" * 60)
    print("Market Pulse 자동 리포트 생성 시작")
    print("=" * 60)
    
    result = run_workflow()
    
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    print(f"상태: {result['status']}")
    print(f"실행 ID: {result['run_id']}")
    print(f"가격 데이터: {result['prices_collected']}개 (신규: {result['prices_new']}개)")
    print(f"뉴스 데이터: {result['news_collected']}개 (신규: {result['news_new']}개)")
    print(f"가격 변동: {len(result['price_changes'])}개")
    print(f"이상치: {len(result['anomalies'])}개")
    print(f"소요시간: {result['duration_seconds']:.1f}초")
    
    if result['error']:
        print(f"\n[!] 에러: {result['error']}")
    else:
        print(f"\n[OK] 리포트 저장: {result['report_path']}")
        print(f"   HTML: {result['report_path'].replace('.md', '.html')}")
    
    return result

if __name__ == "__main__":
    main()