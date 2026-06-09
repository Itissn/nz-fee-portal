from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def find_csv_files():
    """Return all CSV files under the data directory."""
    if not DATA_DIR.exists():
        return []

    return list(DATA_DIR.rglob("*.csv"))


def test_data_directory_exists():
    assert DATA_DIR.exists(), "The data directory does not exist."


def test_at_least_one_csv_file_exists():
    csv_files = find_csv_files()
    assert csv_files, "No CSV files found under the data directory."


def test_csv_files_can_be_read_and_are_not_empty():
    csv_files = find_csv_files()

    for csv_path in csv_files:
        df = pd.read_csv(csv_path)

        assert not df.empty, f"{csv_path} is empty."
        assert len(df.columns) > 0, f"{csv_path} has no columns."


def test_csv_files_do_not_have_empty_column_names():
    csv_files = find_csv_files()

    for csv_path in csv_files:
        df = pd.read_csv(csv_path)

        empty_columns = [
            column for column in df.columns
            if str(column).strip() == ""
        ]

        assert not empty_columns, (
            f"{csv_path} has empty column names: {empty_columns}"
        )


def test_programme_index_has_expected_columns_if_present():
    possible_paths = [
        DATA_DIR / "programme_index.csv",
        DATA_DIR / "output" / "programme_index.csv",
    ]

    existing_paths = [path for path in possible_paths if path.exists()]

    if not existing_paths:
        return

    programme_index_path = existing_paths[0]
    df = pd.read_csv(programme_index_path)

    expected_columns = {
        "provider",
        "programme_name",
    }

    missing_columns = expected_columns.difference(set(df.columns))

    assert not missing_columns, (
        f"{programme_index_path} is missing expected columns: "
        f"{sorted(missing_columns)}"
    )