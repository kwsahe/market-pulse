"""단일 오리진 프로덕션 실행 진입점.

FastAPI 하나가 API와 프론트 빌드(frontend/dist)를 **같은 출처**에서 서빙한다.
오리진이 하나면 CORS가 설정 대상이 아니라 아예 없는 것이 되고, 배포 산출물·도메인·
인증 지점이 각각 하나로 줄어든다.

기본이 읽기전용이다 — 워치리스트 쓰기 라우트에는 인증이 없어서, 공개 URL에 노출되면
누구나 추적 목록과 목표가를 바꿀 수 있다. 인증을 만드는 대신 그 라우트를 등록하지 않는다.
편집이 필요하면 --writable 로 띄우되 외부에 노출하지 말 것.

사용법:
    python scripts/serve_prod.py                  # 읽기전용, 127.0.0.1:8002
    python scripts/serve_prod.py --port 8000
    python scripts/serve_prod.py --writable       # 워치리스트 편집 허용 (로컬 전용)
    python scripts/serve_prod.py --host 0.0.0.0   # LAN 노출 (Tailscale Funnel은 불필요)

프론트 빌드를 먼저 해야 한다:
    npm run build --prefix frontend
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8002)
    # 기본은 루프백. Tailscale Funnel 은 127.0.0.1 로 프록시하므로 0.0.0.0 이 필요 없고,
    # 실수로 공유기 밖에 열리는 사고를 막는다.
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--writable", action="store_true",
                        help="워치리스트 쓰기 허용 (인증이 없으므로 공개 노출 금지)")
    args = parser.parse_args()

    if not os.path.isdir(DIST):
        print("[!] 프론트 빌드가 없습니다:", DIST)
        print("    먼저 실행하세요:  npm run build --prefix frontend")
        raise SystemExit(1)

    # api.main 이 import 시점에 이 값을 읽으므로 import 전에 설정해야 한다.
    os.environ["MARKET_PULSE_READONLY"] = "0" if args.writable else "1"

    import uvicorn

    mode = "쓰기 허용 (공개 노출 금지)" if args.writable else "읽기전용"
    print(f"Market Pulse 단일 오리진 서버 — {mode}")
    print(f"  http://{args.host}:{args.port}")
    print(f"  프론트: {DIST}")
    uvicorn.run("api.main:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
