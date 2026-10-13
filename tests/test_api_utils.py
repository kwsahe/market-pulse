# tests/test_api_utils.py
# sqlite NULL -> pandas NaN -> pydantic Optional[str] 경로에서 나던 500을 막는 헬퍼 검증.

import numpy as np
import pandas as pd
import pytest

from api.utils import optional_str


def test_optional_str_passes_through_real_strings():
    assert optional_str("69869543") == "69869543"
    assert optional_str("http://img/a.jpg") == "http://img/a.jpg"


@pytest.mark.parametrize("missing", [None, float("nan"), np.nan, pd.NA, pd.NaT])
def test_optional_str_normalizes_every_missing_marker(missing):
    """pandas는 결측치를 NaN/NaT/pd.NA 등 여러 형태로 돌려준다. 전부 None이어야 한다."""
    assert optional_str(missing) is None


def test_optional_str_keeps_empty_string():
    """스크래퍼는 '이미지를 못 찾았다'는 뜻으로 ''를 저장한다 — None과 구분돼야 한다."""
    assert optional_str("") == ""


def test_optional_str_reads_null_column_from_dataframe():
    """실제로 터졌던 경로: nullable TEXT 컬럼을 DataFrame으로 읽으면 None이 아니라 NaN이 온다."""
    df = pd.DataFrame({"pcode": [None, "69869543"]})
    row = df.iloc[0]
    assert row["pcode"] is not None  # pandas가 NaN으로 바꿔놓은 상태
    assert optional_str(row["pcode"]) is None
    assert optional_str(df.iloc[1]["pcode"]) == "69869543"


def test_optional_str_stringifies_non_strings():
    """pcode가 정수로 들어오는 경로도 있어서 문자열로 눕힌다."""
    assert optional_str(69869543) == "69869543"


def test_optional_str_leaves_non_scalars_alone():
    """pd.isna는 리스트를 넣으면 스칼라를 안 돌려준다 — 예외로 죽지 않아야 한다."""
    assert optional_str(["a", "b"]) == "['a', 'b']"
