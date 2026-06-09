from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def quote_identifier(identifier: str) -> str:
    escaped = str(identifier).replace('"', '""')
    return f'"{escaped}"'


def load_csv_to_sqlite(
    csv_path: str | Path,
    db_path: str | Path,
    table_name: str = "programme_index",
    if_exists: str = "replace",
) -> int:
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
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    quoted_table = quote_identifier(table_name)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({quoted_table})").fetchall()

    return [row[1] for row in rows]