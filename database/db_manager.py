# database/db_manager.py
# SQLite DB 초기화 및 데이터 관리 모듈

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


@contextmanager
def get_connection():
    """스레드 안전 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """DB 테이블 및 인덱스 초기화"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # prices 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                product TEXT NOT NULL,
                price INTEGER NOT NULL,
                specs TEXT,
                image_url TEXT
            )
        """)

        # 같은 날짜 + 같은 상품은 중복 저장 방지용 인덱스
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_unique
            ON prices (date, product)
        """)

        # 게이밍 노트북(RTX5080/5090) 상세 추적을 위한 다나와 상품코드 컬럼
        cursor.execute("PRAGMA table_info(prices)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "pcode" not in existing_cols:
            cursor.execute("ALTER TABLE prices ADD COLUMN pcode TEXT")

        # news 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collected_at TEXT NOT NULL,
                press TEXT,
                title TEXT NOT NULL,
                published_at TEXT
            )
        """)

        # 같은 제목 + 같은 언론사는 중복 방지
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_news_unique
            ON news (title, press)
        """)

        # 게이밍 노트북(RTX5080/5090) 상품 메타 정보 — pcode가 상품(=상세페이지) 단위 식별자
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laptop_products (
                pcode TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                gpu_model TEXT,
                detail_url TEXT,
                raw_spec_text TEXT,
                updated_at TEXT
            )
        """)

        # 상세페이지 스펙표를 key-value로 펼쳐서 저장 (필터링용)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laptop_specs (
                pcode TEXT NOT NULL,
                spec_key TEXT NOT NULL,
                spec_value TEXT,
                PRIMARY KEY (pcode, spec_key)
            )
        """)

        # 대표 이미지 + 상세정보(홍보) 이미지
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laptop_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pcode TEXT NOT NULL,
                image_url TEXT NOT NULL,
                image_type TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_laptop_images_unique
            ON laptop_images (pcode, image_url)
        """)

        # 집중 추적 대상으로 체크한 모델 (영구 저장)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_laptops (
                pcode TEXT PRIMARY KEY,
                tracked_at TEXT NOT NULL
            )
        """)

        conn.commit()
    print("[OK] DB 초기화 완료! 테이블: prices, news, laptop_products, laptop_specs, laptop_images, tracked_laptops")


def insert_many_prices(data_list: list[tuple]) -> int:
    """가격 데이터 여러 개를 한 번에 저장 (중복 무시)"""
    if not data_list:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO prices (date, category, product, price, specs, image_url) VALUES (?, ?, ?, ?, ?, ?)",
            data_list
        )
        conn.commit()
        return cursor.rowcount


def insert_many_laptop_prices(data_list: list[tuple]) -> int:
    """게이밍 노트북 가격 데이터 저장 (pcode 포함, 중복 무시)"""
    if not data_list:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO prices (date, category, product, price, specs, image_url, pcode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            data_list
        )
        conn.commit()
        return cursor.rowcount


def upsert_laptop_product(pcode: str, name: str, gpu_model: str, detail_url: str, raw_spec_text: str) -> None:
    """노트북 상품 메타 정보 저장/갱신"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO laptop_products (pcode, name, gpu_model, detail_url, raw_spec_text, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(pcode) DO UPDATE SET
                name=excluded.name,
                gpu_model=excluded.gpu_model,
                detail_url=excluded.detail_url,
                raw_spec_text=excluded.raw_spec_text,
                updated_at=excluded.updated_at
            """,
            (pcode, name, gpu_model, detail_url, raw_spec_text)
        )
        conn.commit()


def save_laptop_specs(pcode: str, spec_dict: dict) -> None:
    """상세 스펙 key-value 저장 (기존 값 대체)"""
    if not spec_dict:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO laptop_specs (pcode, spec_key, spec_value) VALUES (?, ?, ?)",
            [(pcode, k, v) for k, v in spec_dict.items()]
        )
        conn.commit()


def save_laptop_images(pcode: str, images: list[tuple]) -> None:
    """대표/상세정보 이미지 URL 저장 (images: [(url, type, sort_order), ...])"""
    if not images:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO laptop_images (pcode, image_url, image_type, sort_order) VALUES (?, ?, ?, ?)",
            [(pcode, url, img_type, order) for url, img_type, order in images]
        )
        conn.commit()


def load_laptop_products() -> pd.DataFrame:
    """노트북 상품 메타 정보 전체 조회"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM laptop_products", conn)
    except Exception as e:
        print(f"⚠️ 노트북 상품 로드 실패: {e}")
        return pd.DataFrame()


def load_laptop_specs() -> pd.DataFrame:
    """노트북 스펙 key-value 전체 조회"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM laptop_specs", conn)
    except Exception as e:
        print(f"⚠️ 노트북 스펙 로드 실패: {e}")
        return pd.DataFrame()


def load_laptop_images() -> pd.DataFrame:
    """노트북 이미지 전체 조회"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM laptop_images ORDER BY pcode, image_type, sort_order", conn
            )
    except Exception as e:
        print(f"⚠️ 노트북 이미지 로드 실패: {e}")
        return pd.DataFrame()


def load_laptop_price_history(pcode: str) -> pd.DataFrame:
    """특정 노트북(pcode)의 날짜별 최저가 추이"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query(
                "SELECT date, MIN(price) AS price FROM prices WHERE pcode = ? GROUP BY date ORDER BY date",
                conn, params=(pcode,)
            )
    except Exception as e:
        print(f"⚠️ 노트북 가격 이력 로드 실패: {e}")
        return pd.DataFrame()


def load_laptop_best_buy_stats() -> pd.DataFrame:
    """노트북별 역대 최저가 + 그 날짜 (pcode 단위, 날짜별 최저가 기준으로 계산)
    반환 컬럼: pcode, best_date, best_price"""
    try:
        with get_connection() as conn:
            daily = pd.read_sql_query(
                """
                SELECT pcode, date, MIN(price) AS price
                FROM prices
                WHERE category = '게이밍 노트북' AND pcode IS NOT NULL AND pcode != ''
                GROUP BY pcode, date
                """,
                conn
            )
        if daily.empty:
            return pd.DataFrame(columns=["pcode", "best_date", "best_price"])
        best_idx = daily.groupby("pcode")["price"].idxmin()
        best = daily.loc[best_idx, ["pcode", "date", "price"]].rename(
            columns={"date": "best_date", "price": "best_price"}
        )
        return best.reset_index(drop=True)
    except Exception as e:
        print(f"⚠️ 노트북 최저가 통계 로드 실패: {e}")
        return pd.DataFrame(columns=["pcode", "best_date", "best_price"])


def get_tracked_pcodes() -> list:
    """집중 추적 중인 노트북 pcode 목록"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pcode FROM tracked_laptops")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"⚠️ 추적 목록 로드 실패: {e}")
        return []


def set_laptop_tracked(pcode: str, tracked: bool) -> None:
    """노트북 추적 상태 설정 (체크박스 온/오프)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if tracked:
            cursor.execute(
                "INSERT OR IGNORE INTO tracked_laptops (pcode, tracked_at) VALUES (?, datetime('now', 'localtime'))",
                (pcode,)
            )
        else:
            cursor.execute("DELETE FROM tracked_laptops WHERE pcode = ?", (pcode,))
        conn.commit()


def insert_many_news(data_list: list[tuple]) -> int:
    """뉴스 데이터 여러 개를 한 번에 저장 (중복 무시)"""
    if not data_list:
        return 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO news (collected_at, press, title, published_at) VALUES (?, ?, ?, ?)",
            data_list
        )
        conn.commit()
        return cursor.rowcount


def load_prices() -> pd.DataFrame:
    """가격 데이터를 DataFrame으로 불러오기 (ML/대시보드 공통)"""
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT date, category, product, price, specs, image_url, pcode FROM prices ORDER BY date",
                conn
            )
        return df
    except Exception as e:
        print(f"⚠️ 가격 데이터 로드 실패: {e}")
        return pd.DataFrame()


def load_news() -> pd.DataFrame:
    """뉴스 데이터를 DataFrame으로 불러오기 (대시보드 공통)"""
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT collected_at, press, title, published_at FROM news ORDER BY published_at DESC",
                conn
            )
        return df
    except Exception as e:
        print(f"⚠️ 뉴스 데이터 로드 실패: {e}")
        return pd.DataFrame()


def get_all_prices() -> list:
    """가격 데이터 전체 조회 (레거시 호환용)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM prices ORDER BY date DESC")
            return cursor.fetchall()
    except Exception as e:
        print(f"⚠️ 가격 데이터 조회 실패: {e}")
        return []


def get_all_news() -> list:
    """뉴스 데이터 전체 조회 (레거시 호환용)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM news ORDER BY published_at DESC")
            return cursor.fetchall()
    except Exception as e:
        print(f"⚠️ 뉴스 데이터 조회 실패: {e}")
        return []


if __name__ == "__main__":
    init_db()
    prices_df = load_prices()
    news_df = load_news()
    print(f"\n현재 가격 데이터: {len(prices_df)}개")
    print(f"현재 뉴스 데이터: {len(news_df)}개")