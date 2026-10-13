# tests/test_verify_last_scrape.py
# 수집 형상 가드. scrape_runs.status 가 22회 전부 success 였기 때문에 만든 장치라,
# "무엇을 잡고 무엇을 못 잡는지"를 테스트로 못박아 둔다.

import sqlite3

import pytest

from scripts.verify_last_scrape import check


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE prices (id INTEGER PRIMARY KEY, date TEXT, category TEXT)")
    return c


def seed(conn, date, counts):
    conn.executemany(
        "INSERT INTO prices (date, category) VALUES (?, ?)",
        [(date, cat) for cat, n in counts.items() for _ in range(n)],
    )
    conn.commit()


def test_normal_day_passes(conn):
    seed(conn, "2026-09-09", {"CPU": 100, "그래픽카드": 40})
    seed(conn, "2026-09-10", {"CPU": 104, "그래픽카드": 40})
    problems, warnings = check(conn, "2026-09-10")
    assert problems == []
    assert warnings == []


def test_catches_category_collapse(conn):
    """실제 사고 형태 — 검색어가 깨져 진짜 상품이 거의 안 잡히는 경우."""
    seed(conn, "2026-09-09", {"CPU": 104, "그래픽카드": 40})
    seed(conn, "2026-09-10", {"CPU": 2, "그래픽카드": 40})
    problems, _ = check(conn, "2026-09-10")
    assert len(problems) == 1
    assert "CPU" in problems[0] and "급감" in problems[0]


def test_catches_category_disappearing(conn):
    seed(conn, "2026-09-09", {"CPU": 104, "그래픽카드": 40})
    seed(conn, "2026-09-10", {"그래픽카드": 40})
    problems, _ = check(conn, "2026-09-10")
    assert len(problems) == 1
    assert "통째로 사라졌습니다" in problems[0]


def test_catches_stale_date(conn):
    """배치가 아예 안 돈 날 — 오늘 날짜 데이터가 없다."""
    seed(conn, "2026-09-09", {"CPU": 104})
    problems, _ = check(conn, "2026-09-10")
    assert len(problems) == 1
    assert "배치가 돌지 않았거나" in problems[0]


def test_surge_is_warning_not_failure(conn):
    """급증은 사고 복구·신제품 대량 등록으로도 생긴다.
    실패로 처리하면 오탐이 되고, 오탐이 반복되면 알림을 안 보게 된다."""
    seed(conn, "2026-09-09", {"CPU": 2})
    seed(conn, "2026-09-10", {"CPU": 104})
    problems, warnings = check(conn, "2026-09-10")
    assert problems == []
    assert len(warnings) == 1 and "급증" in warnings[0]


def test_normal_variation_within_threshold_passes(conn):
    """실측상 정상 변화율 최대가 28.7% 였다. 그 정도는 통과해야 한다."""
    seed(conn, "2026-09-09", {"게이밍 노트북": 171})
    seed(conn, "2026-09-10", {"게이밍 노트북": 220})  # +28.7%
    problems, warnings = check(conn, "2026-09-10")
    assert problems == []
    assert warnings == []


def test_known_blind_spot_contamination_that_refills(conn):
    """알려진 사각지대를 명시적으로 고정해 둔다.

    2026-09-03 CPU 사고 당시 실제 행수는 104 -> 86(-17.3%)이었다. 진짜 CPU가 2행으로
    줄었지만 스마트폰·태블릿 84행이 그 자리를 채워서 행수만으로는 정상으로 보였다.
    지금은 _is_cpu 필터가 그 84행을 거부하므로 붕괴가 드러나 잡힌다 — 즉 이 가드의
    실효성은 카테고리에 필터가 있느냐에 달려 있다. 필터 없는 카테고리는 여전히 못 잡는다."""
    seed(conn, "2026-08-19", {"CPU": 104})
    seed(conn, "2026-09-03", {"CPU": 86})
    problems, _ = check(conn, "2026-09-03")
    assert problems == [], "행수만 보는 가드는 이 형태를 못 잡는다 (의도된 한계)"


def test_first_collection_has_nothing_to_compare(conn):
    seed(conn, "2026-09-10", {"CPU": 104})
    problems, warnings = check(conn, "2026-09-10")
    assert problems == []
    assert warnings == []
