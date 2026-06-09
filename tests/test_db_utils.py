from pathlib import Path

import pandas as pd
import pytest

from src.db_utils import (
    get_table_columns,
    load_csv_to_sqlite,
    search_programmes_sqlite,
)


def test_load_csv_to_sqlite_creates_database(tmp_path):
    csv_path = tmp_path / "sample.csv"
    db_path = tmp_path / "sample.sqlite"

    df = pd.DataFrame(
        {
            "provider": ["Victoria University of Wellington"],
            "programme_name": ["Master of Data Science"],
            "fee": [45000],
        }
    )
    df.to_csv(csv_path, index=False)

    row_count = load_csv_to_sqlite(
        csv_path=csv_path,
        db_path=db_path,
        table_name="programme_index",
    )

    assert row_count == 1
    assert db_path.exists()


def test_get_table_columns_returns_expected_columns(tmp_path):
    csv_path = tmp_path / "sample.csv"
    db_path = tmp_path / "sample.sqlite"

    df = pd.DataFrame(
        {
            "provider": ["University of Auckland"],
            "programme_name": ["Bachelor of Commerce"],
        }
    )
    df.to_csv(csv_path, index=False)

    load_csv_to_sqlite(csv_path, db_path)

    columns = get_table_columns(db_path)

    assert "provider" in columns
    assert "programme_name" in columns


def test_search_programmes_sqlite_finds_matching_record(tmp_path):
    csv_path = tmp_path / "sample.csv"
    db_path = tmp_path / "sample.sqlite"

    df = pd.DataFrame(
        {
            "provider": [
                "Victoria University of Wellington",
                "University of Auckland",
            ],
            "programme_name": [
                "Master of Computer Science",
                "Bachelor of Commerce",
            ],
            "fee": [46000, 39000],
        }
    )
    df.to_csv(csv_path, index=False)

    load_csv_to_sqlite(csv_path, db_path)

    results = search_programmes_sqlite(
        db_path=db_path,
        query="computer",
        search_columns=["programme_name"],
    )

    assert len(results) == 1
    assert results[0]["programme_name"] == "Master of Computer Science"


def test_search_programmes_sqlite_is_case_insensitive(tmp_path):
    csv_path = tmp_path / "sample.csv"
    db_path = tmp_path / "sample.sqlite"

    df = pd.DataFrame(
        {
            "provider": ["Victoria University of Wellington"],
            "programme_name": ["Master of Artificial Intelligence"],
        }
    )
    df.to_csv(csv_path, index=False)

    load_csv_to_sqlite(csv_path, db_path)

    results = search_programmes_sqlite(
        db_path=db_path,
        query="ARTIFICIAL",
        search_columns=["programme_name"],
    )

    assert len(results) == 1


def test_search_programmes_sqlite_returns_limited_rows_for_empty_query(tmp_path):
    csv_path = tmp_path / "sample.csv"
    db_path = tmp_path / "sample.sqlite"

    df = pd.DataFrame(
        {
            "provider": ["A", "B", "C"],
            "programme_name": ["P1", "P2", "P3"],
        }
    )
    df.to_csv(csv_path, index=False)

    load_csv_to_sqlite(csv_path, db_path)

    results = search_programmes_sqlite(
        db_path=db_path,
        query="",
        limit=2,
    )

    assert len(results) == 2


def test_load_csv_to_sqlite_raises_for_missing_csv(tmp_path):
    missing_csv = tmp_path / "missing.csv"
    db_path = tmp_path / "sample.sqlite"

    with pytest.raises(FileNotFoundError):
        load_csv_to_sqlite(missing_csv, db_path)