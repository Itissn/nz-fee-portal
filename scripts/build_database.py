from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.db_utils import get_table_columns, load_csv_to_sqlite


DEFAULT_CSV_PATH = ROOT_DIR / "data" / "output" / "programme_index.csv"
DEFAULT_DB_PATH = ROOT_DIR / "local_db" / "nz_fee_portal.sqlite"
DEFAULT_TABLE_NAME = "programme_index"


logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure console logging for the ETL script.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_database(
    csv_path: Path = DEFAULT_CSV_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    table_name: str = DEFAULT_TABLE_NAME,
) -> int:
    """
    Build a SQLite database from the programme index CSV file.
    """
    logger.info("Starting SQLite database build")
    logger.info("Root directory: %s", ROOT_DIR)
    logger.info("CSV path: %s", csv_path)
    logger.info("Database path: %s", db_path)
    logger.info("Table name: %s", table_name)

    row_count = load_csv_to_sqlite(
        csv_path=csv_path,
        db_path=db_path,
        table_name=table_name,
        if_exists="replace",
    )

    columns = get_table_columns(
        db_path=db_path,
        table_name=table_name,
    )

    logger.info("Loaded rows: %s", row_count)
    logger.info("Columns: %s", columns)
    logger.info("SQLite database build completed")

    return row_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a SQLite database from programme_index.csv."
    )

    parser.add_argument(
        "--csv-path",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to the input programme index CSV file.",
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the output SQLite database file.",
    )

    parser.add_argument(
        "--table-name",
        type=str,
        default=DEFAULT_TABLE_NAME,
        help="SQLite table name.",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    try:
        build_database(
            csv_path=args.csv_path,
            db_path=args.db_path,
            table_name=args.table_name,
        )
    except Exception:
        logger.exception("Failed to build SQLite database")
        raise


if __name__ == "__main__":
    main()