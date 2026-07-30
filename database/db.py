import os
import time
from pathlib import Path

import pymysql
from flask import g

# keep DATE as "YYYY-MM-DD" strings and DECIMAL as floats so jsonify output
# matches what the frontend already expects
_conv = pymysql.converters.conversions.copy()
_conv[pymysql.FIELD_TYPE.DATE] = str
_conv[pymysql.FIELD_TYPE.NEWDECIMAL] = float


class DB:
    """Thin wrapper so callers keep the sqlite-style db.execute(...) API."""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def _connect():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "hotel"),
        password=os.environ.get("DB_PASSWORD", "hotel"),
        database=os.environ.get("DB_NAME", "hotel"),
        cursorclass=pymysql.cursors.DictCursor,
        conv=_conv,
    )


def get_db():
    if "db" not in g:
        g.db = DB(_connect())
    return g.db


def init_db(retries=30, delay=2):
    """Create tables if missing. Retries while MySQL is still booting."""
    for attempt in range(retries):
        try:
            conn = _connect()
            break
        except pymysql.err.OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
    with conn:
        cur = conn.cursor()
        for stmt in (Path(__file__).parent / "schema.sql").read_text().split(";"):
            if stmt.strip():
                cur.execute(stmt)
        conn.commit()


def close_db(exc=None):
    db = g.pop("db", None)
    if db:
        db.close()
