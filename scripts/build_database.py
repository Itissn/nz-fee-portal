"""Refresh the three snapshots as one version of the reference catalogue."""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.catalogue import DATA, DB, rebuild


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA,
        help="Directory containing all three named CSV files",
    )
    parser.add_argument("--db-path", type=Path, default=DB)
    args = parser.parse_args()
    try:
        counts = rebuild(args.data_dir, args.db_path)
    except (ValueError, OSError, sqlite3.Error, csv.Error) as error:
        parser.exit(1, f"Import failed: {error}\n")
    print("Imported snapshots: " + ", ".join(f"{k}: {v:,}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
