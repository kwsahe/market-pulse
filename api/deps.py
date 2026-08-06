# api/deps.py
# dashboard/tabs/common.py의 @st.cache_data(ttl=30) 패턴을 FastAPI 쪽에서 재현한다.
# DB 읽기 함수(문자열/카테고리 등 원시타입 인자만 받는 것들)만 감싼다 — DataFrame을
# 인자로 받는 함수(detect_zscore 등)는 str(args) 캐시 키가 느리고 불안정해서 대상에서 뺀다.

import functools
import hashlib
import json

from cachetools import TTLCache

DATA_TTL_SECONDS = 30
MODEL_TTL_SECONDS = 3600  # 예측 모델 캐싱은 다음 단계(예측 탭 이식) 몫 — 상수만 미리 정의

_data_cache: TTLCache = TTLCache(maxsize=256, ttl=DATA_TTL_SECONDS)
_model_cache: TTLCache = TTLCache(maxsize=16, ttl=MODEL_TTL_SECONDS)


def _make_key(func_name: str, args: tuple, kwargs: dict) -> str:
    raw = f"{func_name}:{args}:{json.dumps(kwargs, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _ttl_cache(cache: TTLCache):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(func.__name__, args, kwargs)
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator


def data_cache(func):
    return _ttl_cache(_data_cache)(func)


def model_cache(func):
    return _ttl_cache(_model_cache)(func)


def reset_cache() -> None:
    """테스트에서 DB_PATH를 바꿔치기한 뒤 캐시 오염을 막기 위해 호출한다."""
    _data_cache.clear()
    _model_cache.clear()
