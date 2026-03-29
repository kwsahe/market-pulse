# database/db_manager.py
# SQLite DB 초기화 및 데이터 관리 모듈
 
import sqlite3
import os
 
DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
 
 
def get_connection():
    """DB 연결을 반환하는 함수"""
    conn = sqlite3.connect(DB_PATH)
    return conn
 
 
def init_db():
    """테이블이 없으면 생성하는 함수"""
    conn = get_connection()
    cursor = conn.cursor()
 
    # prices 테이블 (가격 데이터)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    """)
 
    # news 테이블 (뉴스 데이터) — published_at으로 변경
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
    """가격 데이터 여러 개를 한 번에 저장
    data_list 형식: [(날짜, 상품명, 가격), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO prices (date, product, price) VALUES (?, ?, ?)",
        data_list
    )
    conn.commit()
    conn.close()
 
 
def insert_many_news(data_list):
    """뉴스 데이터 여러 개를 한 번에 저장
    data_list 형식: [(수집시간, 언론사, 제목, 발행시간), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO news (collected_at, press, title, published_at) VALUES (?, ?, ?, ?)",
        data_list
    )
    conn.commit()
    conn.close()
 
 
def get_all_prices():
    """저장된 가격 데이터 전부 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prices ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
 
 
def get_all_news():
    """저장된 뉴스 데이터 전부 조회"""
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