# database/db_manager.py
# SQLite DB 초기화 및 데이터 관리 모듈

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

# 카테고리별 내부 상품번호 접두사 (RAM-1, SSD-1, GC-1, CPU-1, GN-1, AN-1 ...)
CATEGORY_PREFIX = {
    "DDR5 RAM": "RAM",
    "NVMe SSD": "SSD",
    "그래픽카드": "GC",
    "CPU": "CPU",
    "게이밍 노트북": "GN",
    "AI 노트북": "AN",
}


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
                first_seen TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("PRAGMA table_info(laptop_products)")
        laptop_cols = [row[1] for row in cursor.fetchall()]
        if "first_seen" not in laptop_cols:
            cursor.execute("ALTER TABLE laptop_products ADD COLUMN first_seen TEXT")
            # 기존 행은 처음 관찰된 시점을 알 수 없으므로 updated_at으로 백필 (신제품 오탐 방지)
            cursor.execute("UPDATE laptop_products SET first_seen = updated_at WHERE first_seen IS NULL")

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
                tracked_at TEXT NOT NULL,
                target_price INTEGER,
                memo TEXT
            )
        """)
        cursor.execute("PRAGMA table_info(tracked_laptops)")
        tracked_cols = [row[1] for row in cursor.fetchall()]
        if "target_price" not in tracked_cols:
            cursor.execute("ALTER TABLE tracked_laptops ADD COLUMN target_price INTEGER")
        if "memo" not in tracked_cols:
            cursor.execute("ALTER TABLE tracked_laptops ADD COLUMN memo TEXT")

        # 카테고리 공통 상품번호 레지스트리 (RAM-1, SSD-1, GC-1, CPU-1, GN-1, AN-1 ...)
        # match_key: 노트북류는 danawa pcode, 부품류(RAM/SSD/GC/CPU)는 상품명 텍스트 자체가 SKU 단위라 그대로 사용
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_registry (
                internal_code TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                match_key TEXT NOT NULL,
                display_name TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                UNIQUE(category, match_key)
            )
        """)

        # 스크래퍼 실행 이력 (성공/실패, 수집·신규 저장 건수, 소요 시간 추적용)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                fetched_count INTEGER DEFAULT 0,
                inserted_count INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'running',
                error_message TEXT
            )
        """)

        # 스키마 변경 이력 (언제 어떤 마이그레이션이 이 DB에 적용됐는지 추적)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        for migration_name in (
            "001_initial_prices_news",
            "002_prices_pcode",
            "003_laptop_tables",
            "004_laptop_products_first_seen",
            "005_tracked_laptops",
            "006_product_registry",
            "007_scrape_runs",
            "008_tracked_laptops_target_price",
        ):
            cursor.execute(
                "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, datetime('now', 'localtime'))",
                (migration_name,)
            )

        conn.commit()
    print("[OK] DB 초기화 완료! 테이블: prices, news, laptop_products, laptop_specs, laptop_images, tracked_laptops, product_registry, scrape_runs, schema_migrations")


def start_scrape_run(source: str) -> int:
    """수집 실행 시작 기록. finish_scrape_run에 넘길 run_id를 반환한다."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scrape_runs (source, started_at, status) VALUES (?, datetime('now', 'localtime'), 'running')",
            (source,)
        )
        conn.commit()
        return cursor.lastrowid


def finish_scrape_run(
    run_id: int, fetched_count: int = 0, inserted_count: int = 0,
    status: str = "success", error_message: Optional[str] = None,
) -> None:
    """수집 실행 종료 기록 (성공/실패, 수집·신규 저장 건수)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE scrape_runs
               SET finished_at = datetime('now', 'localtime'), fetched_count = ?, inserted_count = ?,
                   status = ?, error_message = ?
               WHERE id = ?""",
            (fetched_count, inserted_count, status, error_message, run_id)
        )
        conn.commit()


def load_scrape_runs(limit: int = 50) -> pd.DataFrame:
    """최근 수집 실행 이력 조회 (최신순)"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM scrape_runs ORDER BY id DESC LIMIT ?", conn, params=(limit,)
            )
    except Exception as e:
        print(f"⚠️ 수집 이력 로드 실패: {e}")
        return pd.DataFrame()


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


def upsert_laptop_product(pcode: str, name: str, gpu_model: str, detail_url: str, raw_spec_text: str) -> bool:
    """노트북 상품 메타 정보 저장/갱신. first_seen은 최초 1회만 기록(신제품 판별용).
    반환값: 이번 호출로 처음 추가된 신제품이면 True"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM laptop_products WHERE pcode = ?", (pcode,))
        is_new = cursor.fetchone() is None
        cursor.execute(
            """
            INSERT INTO laptop_products (pcode, name, gpu_model, detail_url, raw_spec_text, first_seen, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
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
        return is_new


def get_or_create_product_code(category: str, match_key: str, display_name: str) -> str:
    """카테고리+식별키(pcode 또는 상품명)에 대응하는 내부 상품번호를 찾거나 새로 발급.
    이미 등록돼 있으면 코드만 반환(표시명 갱신), 없으면 해당 카테고리의 다음 순번으로 새로 발급."""
    prefix = CATEGORY_PREFIX.get(category, "ITEM")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT internal_code FROM product_registry WHERE category = ? AND match_key = ?",
            (category, match_key)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE product_registry SET display_name = ? WHERE internal_code = ?",
                (display_name, row["internal_code"])
            )
            conn.commit()
            return row["internal_code"]

        cursor.execute("SELECT COUNT(*) AS c FROM product_registry WHERE category = ?", (category,))
        next_n = cursor.fetchone()["c"] + 1
        internal_code = f"{prefix}-{next_n}"
        cursor.execute(
            """
            INSERT INTO product_registry (internal_code, category, match_key, display_name, first_seen)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
            """,
            (internal_code, category, match_key, display_name)
        )
        conn.commit()
        return internal_code


def backfill_product_registry() -> int:
    """기존에 수집된 prices 데이터 전체에 상품번호를 발급 (없는 것만). pcode가 있으면 pcode,
    없으면(과거 부품 데이터) 상품명을 식별키로 사용. 스키마 도입 후 1회 실행용."""
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT category, product, pcode FROM prices").fetchall()
    registered = 0
    for r in rows:
        match_key = r["pcode"] if r["pcode"] else r["product"]
        get_or_create_product_code(r["category"], match_key, r["product"])
        registered += 1
    return registered


def load_product_registry(category: str = None) -> pd.DataFrame:
    """상품번호 레지스트리 전체(또는 특정 카테고리) 조회"""
    try:
        with get_connection() as conn:
            if category:
                return pd.read_sql_query(
                    "SELECT * FROM product_registry WHERE category = ?", conn, params=(category,)
                )
            return pd.read_sql_query("SELECT * FROM product_registry", conn)
    except Exception as e:
        print(f"⚠️ 상품 레지스트리 로드 실패: {e}")
        return pd.DataFrame()


def get_product_code_map(category: str) -> dict:
    """{match_key: internal_code} 매핑 (부품 카테고리는 match_key=상품명, 노트북류는 match_key=pcode)"""
    reg = load_product_registry(category)
    if reg.empty:
        return {}
    return dict(zip(reg["match_key"], reg["internal_code"]))


def load_price_history_by_match_key(category: str, match_key: str, by_pcode: bool = False) -> pd.DataFrame:
    """상품 하나의 날짜별 가격 추이. by_pcode=True면 pcode 기준(노트북, 같은 pcode의 용량 변형 중 최저가),
    False면 상품명 그대로 매칭(부품류)."""
    try:
        with get_connection() as conn:
            if by_pcode:
                return pd.read_sql_query(
                    "SELECT date, MIN(price) AS price FROM prices WHERE pcode = ? GROUP BY date ORDER BY date",
                    conn, params=(match_key,)
                )
            return pd.read_sql_query(
                "SELECT date, price FROM prices WHERE category = ? AND product = ? ORDER BY date",
                conn, params=(category, match_key)
            )
    except Exception as e:
        print(f"⚠️ 상품 가격 이력 로드 실패: {e}")
        return pd.DataFrame()


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


def load_laptop_best_buy_stats(category: str = "게이밍 노트북") -> pd.DataFrame:
    """노트북별 역대 최저가 + 그 날짜 (pcode 단위, 날짜별 최저가 기준으로 계산)
    반환 컬럼: pcode, best_date, best_price"""
    try:
        with get_connection() as conn:
            daily = pd.read_sql_query(
                """
                SELECT pcode, date, MIN(price) AS price
                FROM prices
                WHERE category = ? AND pcode IS NOT NULL AND pcode != ''
                GROUP BY pcode, date
                """,
                conn, params=(category,)
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


def set_target_price(pcode: str, target_price: Optional[int], memo: str = "") -> None:
    """추적 중인 상품의 목표가/메모 설정 (target_price=None이면 목표가 해제)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tracked_laptops SET target_price = ?, memo = ? WHERE pcode = ?",
            (target_price, memo, pcode)
        )
        conn.commit()


def load_tracked_targets() -> pd.DataFrame:
    """추적 중인 상품의 목표가/메모 전체 조회"""
    try:
        with get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM tracked_laptops", conn)
    except Exception as e:
        print(f"⚠️ 추적 목표가 로드 실패: {e}")
        return pd.DataFrame(columns=["pcode", "tracked_at", "target_price", "memo"])


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