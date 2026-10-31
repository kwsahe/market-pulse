"""공개 데모(GitHub Pages)를 오늘 수집분으로 갱신한다 — run_scrapers.bat 의 마지막 단계.

1. export_static_demo.export() 로 실제 API 응답을 임시 폴더에 뜬다
2. demo-data 브랜치에 커밋 하나로 강제 푸시한다
   (main 에 매일 데이터 커밋이 붙으면 코드 이력이 묻히고 저장소가 날마다 몇 MB씩 커진다.
    커밋 하나를 덮어쓰면 이전 데이터는 GitHub 이 알아서 정리한다)
3. Pages 배포 워크플로(.github/workflows/pages.yml)를 실행한다 — 그 워크플로가 demo-data 브랜치를 읽어 빌드한다

푸시는 저장소 주인(origin 의 owner) 계정의 gh 로그인으로 한다. 이 PC 의 gh 기본 계정이 달라도 되고,
그 계정 로그인이 없는 PC(다른 사람이 받은 사본)에서는 아무것도 하지 않고 넘어간다.
토큰은 하위 프로세스 환경변수로만 넘기고 출력하지 않는다.

사용법:
    python scripts/publish_demo.py            # 내보내기 + 푸시 + 배포 실행
    python scripts/publish_demo.py --dry-run  # 내보내기와 임시 폴더 커밋까지만 (푸시·배포 안 함)
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANCH = "demo-data"
WORKFLOW = "pages.yml"


def _run(cmd, cwd=PROJECT_ROOT, env=None) -> str:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def owner_repo(remote_url: str) -> tuple[str, str]:
    """'https://github.com/kwsahe/market-pulse(.git)' 또는 'git@github.com:kwsahe/market-pulse.git' → (owner, repo)"""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", remote_url)
    if not m:
        raise ValueError(f"GitHub 저장소 주소가 아니에요: {remote_url}")
    return m.group(1), m.group(2)


def owner_token(owner: str):
    """gh 에 owner 계정으로 로그인돼 있으면 그 토큰, 아니면 None."""
    try:
        return _run(["gh", "auth", "token", "--user", owner]) or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="푸시·배포 없이 내보내기와 커밋만 해 본다")
    args = parser.parse_args()

    remote = _run(["git", "remote", "get-url", "origin"])
    owner, repo = owner_repo(remote)
    token = owner_token(owner)
    if token is None and not args.dry_run:
        print(f"[건너뜀] gh 에 {owner} 계정 로그인이 없어 공개 데모를 갱신하지 않아요.")
        return 0
    name = _run(["git", "config", "user.name"])
    email = _run(["git", "config", "user.email"])

    from scripts.export_static_demo import export

    # ignore_cleanup_errors: Windows 에서 .git 안의 읽기 전용 파일이 남아도 단계 자체는 실패로 치지 않는다
    with tempfile.TemporaryDirectory(prefix="market-pulse-demo-", ignore_cleanup_errors=True) as tmp:
        summary = export(os.path.join(tmp, "data"))
        _run(["git", "init", "-q", "-b", BRANCH], cwd=tmp)
        _run(["git", "add", "-A"], cwd=tmp)
        _run(["git", "-c", f"user.name={name}", "-c", f"user.email={email}",
              "commit", "-q", "-m", f"demo data: {summary['snapshot']} 수집분"], cwd=tmp)
        print(f"{summary['snapshot']} 수집분 · 상품 {summary['products']}행 · 상세 {summary['details']}개 · "
              f"{summary['bytes'] / 1024 / 1024:.1f}MB")
        if args.dry_run:
            print("[dry-run] 푸시와 배포는 건너뜀")
            return 0

        env = {**os.environ, "GH_TOKEN": token}
        _run(["git", "push", "-q", "--force", remote, f"HEAD:{BRANCH}"], cwd=tmp, env=env)
        _run(["gh", "workflow", "run", WORKFLOW, "-R", f"{owner}/{repo}", "--ref", "main"], env=env)
    print(f"[OK] {BRANCH} 브랜치 갱신 + Pages 배포 시작 → https://{owner}.github.io/{repo}/")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        # git/gh 오류 메시지만 보여 준다 (명령줄·환경변수에는 토큰이 없지만, 넘기는 것도 최소로)
        print(f"[!] {e.cmd[0]} {e.cmd[1]} 실패: {(e.stderr or '').strip()[:300]}")
        sys.exit(1)
