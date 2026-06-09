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


def get_distinct_values_sqlite(
    db_path: str | Path,
    column_name: str,
    table_name: str = "programme_index",
    limit: int = 500,
) -> list[str]:
    """
    Return distinct non-empty values from one SQLite column.
    """
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    columns = get_table_columns(db_path, table_name)

    if column_name not in columns:
        return []

    quoted_table = quote_identifier(table_name)
    quoted_column = quote_identifier(column_name)

    sql = (
        f"SELECT DISTINCT {quoted_column} "
        f"FROM {quoted_table} "
        f"WHERE {quoted_column} IS NOT NULL "
        f"AND TRIM(CAST({quoted_column} AS TEXT)) != '' "
        f"ORDER BY {quoted_column} "
        f"LIMIT ?"
    )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(sql, (limit,)).fetchall()

    return [str(row[0]) for row in rows]


def query_programmes_sqlite(
    db_path: str | Path,
    query: str = "",
    provider_type: str | None = None,
    study_stage: str | None = None,
    table_name: str = "programme_index",
    limit: int = 100,
) -> list[dict]:
    """
    Query programme records from SQLite with optional keyword and filters.
    """
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    columns = get_table_columns(db_path, table_name)

    if not columns:
        raise ValueError(f"Table has no columns: {table_name}")

    quoted_table = quote_identifier(table_name)
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)

    where_parts = []
    params: list[object] = []

    query_text = str(query).strip().lower()

    searchable_columns = [
        column for column in [
            "provider_name",
            "programme_name",
            "study_stage",
            "subject_area",
            "matched_keywords",
        ]
        if column in columns
    ]

    if query_text and searchable_columns:
        keyword_conditions = [
            f"LOWER(CAST({quote_identifier(column)} AS TEXT)) LIKE ?"
            for column in searchable_columns
        ]

        where_parts.append("(" + " OR ".join(keyword_conditions) + ")")
        params.extend([f"%{query_text}%"] * len(searchable_columns))

    if provider_type and provider_type != "All" and "provider_type" in columns:
        where_parts.append(f"{quote_identifier('provider_type')} = ?")
        params.append(provider_type)

    if study_stage and study_stage != "All" and "study_stage" in columns:
        where_parts.append(f"{quote_identifier('study_stage')} = ?")
        params.append(study_stage)

    where_sql = ""

    if where_parts:
        where_sql = "WHERE " + " AND ".join(where_parts)

    order_columns = [
        column for column in ["provider_name", "programme_name"]
        if column in columns
    ]

    if order_columns:
        order_sql = "ORDER BY " + ", ".join(
            quote_identifier(column) for column in order_columns
        )
    else:
        order_sql = ""

    sql = (
        f"SELECT {quoted_columns} "
        f"FROM {quoted_table} "
        f"{where_sql} "
        f"{order_sql} "
        f"LIMIT ?"
    )

    params.append(limit)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]