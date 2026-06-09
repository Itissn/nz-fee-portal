from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


COMMON_PROGRAMME_COLUMNS = [
    "programme_name",
    "program_name",
    "programme",
    "program",
    "qualification",
    "title",
    "name",
]

COMMON_PROVIDER_COLUMNS = [
    "provider",
    "institution",
    "university",
    "organisation",
    "organization",
]


def load_csv_data(csv_path: str | Path) -> pd.DataFrame:
    """
    Load a CSV file into a pandas DataFrame.

    Parameters
    ----------
    csv_path:
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded DataFrame.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    ValueError
        If the CSV file is empty.
    """
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"CSV file is empty: {path}")

    return df


def normalize_text(value: object) -> str:
    """
    Convert a value to a lowercase searchable string.
    """
    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def find_first_existing_column(
    columns: Iterable[str],
    candidates: Iterable[str],
) -> str | None:
    """
    Find the first candidate column that exists in a DataFrame.
    Matching is case-insensitive.
    """
    column_lookup = {str(column).lower(): str(column) for column in columns}

    for candidate in candidates:
        candidate_lower = candidate.lower()
        if candidate_lower in column_lookup:
            return column_lookup[candidate_lower]

    return None


def search_programmes(
    df: pd.DataFrame,
    query: str,
    search_columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Search programme records by keyword.

    If search_columns is not provided, the function searches across all columns.

    Parameters
    ----------
    df:
        Programme DataFrame.
    query:
        User search keyword.
    search_columns:
        Optional list of columns to search.

    Returns
    -------
    pd.DataFrame
        Rows that contain the query in at least one selected column.
    """
    if df.empty:
        return df.copy()

    query_normalized = normalize_text(query)

    if query_normalized == "":
        return df.copy()

    if search_columns is None:
        selected_columns = list(df.columns)
    else:
        selected_columns = [column for column in search_columns if column in df.columns]

    if not selected_columns:
        return df.iloc[0:0].copy()

    mask = pd.Series(False, index=df.index)

    for column in selected_columns:
        column_values = df[column].map(normalize_text)
        mask = mask | column_values.str.contains(query_normalized, na=False)

    return df[mask].copy()


def search_programmes_smart(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Search programme data using likely programme/provider columns when possible.

    If no common columns are found, it falls back to searching all columns.
    """
    programme_column = find_first_existing_column(
        df.columns,
        COMMON_PROGRAMME_COLUMNS,
    )
    provider_column = find_first_existing_column(
        df.columns,
        COMMON_PROVIDER_COLUMNS,
    )

    search_columns = [
        column for column in [programme_column, provider_column]
        if column is not None
    ]

    if not search_columns:
        search_columns = None

    return search_programmes(
        df=df,
        query=query,
        search_columns=search_columns,
    )