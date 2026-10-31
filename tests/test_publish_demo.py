# tests/test_publish_demo.py
# 공개 데모 갱신 단계 — 매일 배치 끝에 돈다. 다른 사람이 받은 사본(주인 계정 로그인 없음)에서는
# 아무것도 내보내거나 푸시하지 않고 성공(0)으로 넘어가야 배치가 실패로 잡히지 않는다.

import pytest

import scripts.publish_demo as publish


@pytest.mark.parametrize("url", [
    "https://github.com/kwsahe/market-pulse",
    "https://github.com/kwsahe/market-pulse.git",
    "git@github.com:kwsahe/market-pulse.git",
])
def test_owner_repo_reads_github_remote(url):
    assert publish.owner_repo(url) == ("kwsahe", "market-pulse")


def test_owner_repo_rejects_other_hosts():
    with pytest.raises(ValueError):
        publish.owner_repo("https://gitlab.com/kwsahe/market-pulse")


def test_skips_without_owner_login(monkeypatch, capsys):
    calls = []

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        if cmd[:3] == ["gh", "auth", "token"]:
            raise publish.subprocess.CalledProcessError(1, cmd, stderr="no account")
        return "https://github.com/kwsahe/market-pulse"

    monkeypatch.setattr(publish, "_run", fake_run)
    monkeypatch.setattr("sys.argv", ["publish_demo.py"])
    assert publish.main() == 0
    assert "건너뜀" in capsys.readouterr().out
    assert not any(c[0] == "git" and c[1] in ("push", "init") for c in calls)
