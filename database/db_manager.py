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
    conn.close()
    print("✅ DB 초기화 완료! 테이블: prices, news")


def insert_many_prices(data_list):
    """가격 데이터 여러 개를 한 번에 저장 (중복 무시)
    
    INSERT OR IGNORE: 이미 같은 (date, product) 조합이 있으면
    에러 없이 건너뛰어요. 하루에 여러 번 실행해도 안전!
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT OR IGNORE INTO prices (date, category, product, price, specs, image_url) VALUES (?, ?, ?, ?, ?, ?)",
        data_list
    )
    inserted = cursor.rowcount
    conn.commit()
    conn.close()
    return inserted


def insert_many_news(data_list):
    """뉴스 데이터 여러 개를 한 번에 저장 (중복 무시)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT OR IGNORE INTO news (collected_at, press, title, published_at) VALUES (?, ?, ?, ?)",
        data_list
    )
    inserted = cursor.rowcount
    conn.commit()
    conn.close()
    return inserted


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