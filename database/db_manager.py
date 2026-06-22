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

        conn.commit()
    print("[OK] DB 초기화 완료! 테이블: prices, news")


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
                "SELECT date, category, product, price, specs, image_url FROM prices ORDER BY date",
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