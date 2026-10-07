"""SQLite 存储层：实时快照与 K 线缓存。

Streamlit 每次 rerun 都会重新执行脚本，这里统一使用「短连接」：
每个函数建立连接、用完即提交并关闭，简单且线程安全。数据量小，性能足够。
"""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def _conn():
    """连接上下文管理器：开启 WAL 与超时，正常提交，结束时关闭。"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """建表（幂等）。"""
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kline_daily (
                symbol TEXT NOT NULL,
                date   TEXT NOT NULL,
                open   REAL,
                high   REAL,
                low    REAL,
                close  REAL,
                volume REAL,
                PRIMARY KEY (symbol, date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS realtime_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol     TEXT NOT NULL,
                name       TEXT,
                price      REAL,
                open       REAL,
                high       REAL,
                low        REAL,
                prev_close REAL,
                change     REAL,
                change_pct REAL,
                ts         TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rt_symbol_ts ON realtime_history(symbol, ts)"
        )


def upsert_kline(rows):
    """写入/更新日K。rows: list[dict]，键含 symbol,date,open,high,low,close,volume。"""
    if not rows:
        return
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO kline_daily(symbol, date, open, high, low, close, volume)
            VALUES (:symbol, :date, :open, :high, :low, :close, :volume)
            ON CONFLICT(symbol, date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """,
            rows,
        )


def append_realtime(rows):
    """追加实时快照。rows: list[dict]，键含 symbol,name,price,open,high,low,
    prev_close,change,change_pct,ts。"""
    if not rows:
        return
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO realtime_history
                (symbol, name, price, open, high, low, prev_close, change, change_pct, ts)
            VALUES
                (:symbol, :name, :price, :open, :high, :low, :prev_close, :change, :change_pct, :ts)
            """,
            rows,
        )


def get_latest_kline_date(symbol):
    """返回某品种已缓存的最新日期，无数据返回 None。"""
    with _conn() as conn:
        row = conn.execute(
            "SELECT MAX(date) AS d FROM kline_daily WHERE symbol = ?", (symbol,)
        ).fetchone()
        return row["d"] if row else None


def get_kline(symbol, start=None, end=None, limit=None):
    """查询日K，按日期升序返回 list[dict]。"""
    sql = "SELECT date, open, high, low, close, volume FROM kline_daily WHERE symbol = ?"
    params = [symbol]
    if start:
        sql += " AND date >= ?"
        params.append(start)
    if end:
        sql += " AND date <= ?"
        params.append(end)
    sql += " ORDER BY date ASC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_realtime_history(symbol, n=200):
    """返回某品种最近 n 条实时快照（按时间升序），list[{price, ts}]。"""
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT price, ts FROM (
                SELECT id, price, ts FROM realtime_history
                WHERE symbol = ? ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
            """,
            (symbol, n),
        ).fetchall()
    return [dict(r) for r in rows]
