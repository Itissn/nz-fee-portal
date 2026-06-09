from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def quote_identifier(identifier: str) -> str:
    """
    Safely quote a SQLite table or column identifier.
    """
    escaped = str(identifier).replace('"', '""')
    return f'"{escaped}"'


def load_csv_to_sqlite(
    csv_path: str | Path,
    db_path: str | Path,
    table_name: str = "programme_index",
    if_exists: str = "replace",
) -> int:
    """
    Load a CSV file into a SQLite database table.

    Returns the number of loaded rows.
    """
    csv_path = Path(csv_path)
    db_path = Path(db_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError(f"CSV file is empty: {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists=if_exists,
            index=False,
        )

    return len(df)


def get_table_columns(
    db_path: str | Path,
    table_name: str = "programme_index",
) -> list[str]:
    """
    Return column names for a SQLite table.
    """
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    quoted_table = quote_identifier(table_name)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f"PRAGMA table_info({quoted_table})")
        rows = cursor.fetchall()

    return [row[1] for row in rows]


def search_programmes_sqlite(
    db_path: str | Path,
    query: str,
    table_name: str = "programme_index",
    search_columns: list[str] | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search programme records in a SQLite table.

    If search_columns is not provided, all columns are searched as text.
    """
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    columns = get_table_columns(db_path, table_name)

    if not columns:
        raise ValueError(f"Table has no columns: {table_name}")

    if search_columns is None:
        selected_columns = columns
    else:
        selected_columns = [
            column for column in search_columns
            if column in columns
        ]

    if not selected_columns:
        return []

    quoted_table = quote_identifier(table_name)
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)

    query_text = str(query).strip().lower()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        if query_text == "":
            sql = (
                f"SELECT {quoted_columns} "
                f"FROM {quoted_table} "
                f"LIMIT ?"
            )
            rows = conn.execute(sql, (limit,)).fetchall()
        else:
            where_clause = " OR ".join(
                f"LOWER(CAST({quote_identifier(column)} AS TEXT)) LIKE ?"
                for column in selected_columns
            )
            params = [f"%{query_text}%"] * len(selected_columns)
            params.append(limit)

            sql = (
                f"SELECT {quoted_columns} "
                f"FROM {quoted_table} "
                f"WHERE {where_clause} "
                f"LIMIT ?"
            )
            rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]