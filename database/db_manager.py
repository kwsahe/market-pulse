# database/db_manager.py
# SQLite DB 초기화 및 데이터 관리 모듈

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # prices 테이블 — specs 열 추가
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

    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료! 테이블: prices, news")


def insert_many_prices(data_list):
    """data_list: [(날짜, 카테고리, 상품명, 가격, 스펙, 이미지URL), ...]"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO prices (date, category, product, price, specs, image_url) VALUES (?, ?, ?, ?, ?, ?)",
        data_list
    )
    conn.commit()
    conn.close()


def insert_many_news(data_list):
    """data_list: [(수집시간, 언론사, 제목, 발행시간), ...]"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO news (collected_at, press, title, published_at) VALUES (?, ?, ?, ?)",
        data_list
    )
    conn.commit()
    conn.close()


def get_all_prices():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prices ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_news():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY published_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_db()
    print(f"\n현재 가격 데이터: {len(get_all_prices())}개")
    print(f"현재 뉴스 데이터: {len(get_all_news())}개")