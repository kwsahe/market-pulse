# api/utils.py
# DataFrame에서 꺼낸 값을 pydantic 스키마에 넣기 전에 정규화한다.

from typing import Any, Optional

import pandas as pd


def optional_str(value: Any) -> Optional[str]:
    """nullable 문자열 컬럼을 Optional[str]로 정규화한다.

    sqlite의 NULL은 pandas를 거치면 None이 아니라 float('nan')이 된다. 그대로
    pydantic의 Optional[str] 필드에 넣으면 float라서
    "Input should be a valid string [input_value=nan]"으로 500이 난다.
    실제로 pcode가 빈 prices 행(GET /api/products/{code})과 error_message가 빈
    scrape_runs 행(GET /api/scrapes)에서 터졌다.

    row.get("컬럼")은 컬럼이 아예 없을 때만 None을 주고, 값이 NULL이면 NaN을 준다.
    둘 다 "값 없음"으로 봐야 하므로 여기서 함께 None으로 눕힌다.

    빈 문자열은 그대로 둔다 — 스크래퍼가 "이미지를 못 찾았다"는 뜻으로 ""를 저장하는
    컬럼(image_url)이 있어서, 여기서 None으로 바꾸면 두 상태가 구분되지 않는다.
    """
    if _is_missing(value):
        return None
    return value if isinstance(value, str) else str(value)


def _is_missing(value: Any) -> bool:
    """None / NaN / NaT / pd.NA 를 결측치로 본다.

    pd.isna는 리스트·배열을 넣으면 스칼라가 아닌 결과를 돌려주거나 예외를 던진다.
    그런 값은 애초에 결측치 판정 대상이 아니므로 아니라고 답한다."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
