"""sqlite3 connection management and generic CRUD helpers for the memory
store. All schema knowledge (which columns are JSON, which column is the
primary key) lives in models.py's registries so this file stays generic.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from .models import ID_COLUMNS, JSON_COLUMNS

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Memory is an optional subsystem for the captain runtime.  A contended
    # writer must fail open through the runtime's existing exception handling
    # instead of holding the decision loop for sqlite3's multi-second default.
    # WAL keeps ordinary readers concurrent with telemetry writes; 10 ms is a
    # deliberately small upper bound for the remaining writer contention.
    conn = sqlite3.connect(str(path), timeout=0.01)
    conn.execute("PRAGMA busy_timeout = 10")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def _encode_row(table: str, fields: dict[str, Any]) -> dict[str, Any]:
    json_columns = JSON_COLUMNS.get(table, ())
    encoded = {}
    for key, value in fields.items():
        if key in json_columns and not isinstance(value, str):
            encoded[key] = json.dumps(value if value is not None else None)
        else:
            encoded[key] = value
    return encoded


def _decode_row(table: str, row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    result = dict(row)
    for column in JSON_COLUMNS.get(table, ()):
        raw = result.get(column)
        if raw is not None:
            try:
                result[column] = json.loads(raw)
            except (TypeError, ValueError):
                pass
    return result


def insert(conn: sqlite3.Connection, table: str, fields: dict[str, Any]) -> dict[str, Any]:
    encoded = _encode_row(table, fields)
    columns = list(encoded.keys())
    placeholders = ", ".join(["?"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.execute(sql, [encoded[column] for column in columns])
    conn.commit()
    return fields


def update(conn: sqlite3.Connection, table: str, row_id: Any, fields: dict[str, Any]) -> None:
    id_column = ID_COLUMNS[table]
    encoded = _encode_row(table, fields)
    assignments = ", ".join(f"{column} = ?" for column in encoded)
    sql = f"UPDATE {table} SET {assignments} WHERE {id_column} = ?"
    conn.execute(sql, [*encoded.values(), row_id])
    conn.commit()


def fetch_one(conn: sqlite3.Connection, table: str, row_id: Any) -> Optional[dict[str, Any]]:
    id_column = ID_COLUMNS[table]
    cursor = conn.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", [row_id])
    return _decode_row(table, cursor.fetchone())


def fetch_by(conn: sqlite3.Connection, table: str, **filters: Any) -> list[dict[str, Any]]:
    where = " AND ".join(f"{key} = ?" for key in filters)
    sql = f"SELECT * FROM {table}"
    params: Iterable[Any] = []
    if where:
        sql += f" WHERE {where}"
        params = list(filters.values())
    cursor = conn.execute(sql, params)
    return [_decode_row(table, row) for row in cursor.fetchall()]


def fetch_sql(conn: sqlite3.Connection, table: str, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params)
    return [_decode_row(table, row) for row in cursor.fetchall()]
