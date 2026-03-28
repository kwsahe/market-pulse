
# SQLite DB 초기화 및 데이터 관리 모듈

import sqlite3
import os

# DB 파일 경로
DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_connection():
    """DB 연결을 반환하는 함수
    
    왜 함수로 만들까?
    → 여러 파일(price_scraper, news_scraper, dashboard)에서
      같은 DB에 접근해야 하니까, 연결 방법을 한 곳에서 관리하는 거예요.
    """
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    """테이블이 없으면 생성하는 함수
    
    IF NOT EXISTS를 쓰면 이미 테이블이 있어도 에러 없이 넘어가요.
    → 프로그램을 여러 번 실행해도 안전해요.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ============================
    # prices 테이블 (가격 데이터)
    # ============================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            product TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    """)

    # ============================
    # news 테이블 (뉴스 데이터)
    # ============================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_at TEXT NOT NULL,
            press TEXT,
            title TEXT NOT NULL,
            time_ago TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료! 테이블: prices, news")


def insert_price(date, product, price):
    """가격 데이터 1개를 DB에 저장
    
    ?를 쓰는 이유 (플레이스홀더):
    → SQL 인젝션 방지. 직접 문자열을 넣으면 보안 위험이 있어요.
    → cursor.execute("INSERT ... VALUES ('" + product + "')")  ← 위험!
    → cursor.execute("INSERT ... VALUES (?)", (product,))      ← 안전!
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO prices (date, product, price) VALUES (?, ?, ?)",
        (date, product, price)
    )
    conn.commit()
    conn.close()


def insert_many_prices(data_list):
    """가격 데이터 여러 개를 한 번에 저장
    
    executemany()는 반복문 없이 한 번에 여러 행을 넣어요.
    → 40개 상품을 하나씩 넣으면 DB를 40번 열고 닫지만,
      이 함수는 1번만 열고 닫아서 훨씬 빨라요.
    
    data_list 형식: [(날짜, 상품명, 가격), (날짜, 상품명, 가격), ...]
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
    
    data_list 형식: [(수집시간, 언론사, 제목, 게시시간), ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO news (collected_at, press, title, time_ago) VALUES (?, ?, ?, ?)",
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
    cursor.execute("SELECT * FROM news ORDER BY collected_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


# 직접 실행하면 DB 초기화
if __name__ == "__main__":
    init_db()

    # 테스트: 데이터 확인
    print(f"\n현재 가격 데이터: {len(get_all_prices())}개")
    print(f"현재 뉴스 데이터: {len(get_all_news())}개")