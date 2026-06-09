from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = ROOT_DIR / "local_db" / "nz_fee_portal.sqlite"
DEFAULT_REPORT_PATH = ROOT_DIR / "reports" / "data_quality_report.md"
DEFAULT_TABLE_NAME = "programme_index"

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def read_table(db_path: Path, table_name: str) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn,
        )

    if df.empty:
        raise ValueError(f"Table is empty: {table_name}")

    return df


def make_missing_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for column in df.columns:
        missing_count = df[column].isna().sum()
        empty_string_count = df[column].astype(str).str.strip().eq("").sum()
        total_missing = int(missing_count + empty_string_count)

        rows.append(
            {
                "column": column,
                "missing_or_empty_count": total_missing,
                "missing_or_empty_rate": round(total_missing / len(df), 4),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by="missing_or_empty_rate",
        ascending=False,
    )


def value_counts_table(
    df: pd.DataFrame,
    column: str,
    top_n: int = 20,
) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])

    result = (
        df[column]
        .fillna("Missing")
        .astype(str)
        .str.strip()
        .replace("", "Missing")
        .value_counts()
        .head(top_n)
        .reset_index()
    )

    result.columns = [column, "count"]
    return result


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data available._"

    return df.to_markdown(index=False)


def build_report(df: pd.DataFrame) -> str:
    total_rows = len(df)
    total_columns = len(df.columns)

    provider_count = (
        df["provider_name"].nunique()
        if "provider_name" in df.columns
        else "N/A"
    )

    programme_count = (
        df["programme_name"].nunique()
        if "programme_name" in df.columns
        else "N/A"
    )

    unknown_subject_count = (
        int((df["subject_area"].fillna("").astype(str).str.strip() == "Unknown").sum())
        if "subject_area" in df.columns
        else "N/A"
    )

    average_refined_score = (
        round(float(pd.to_numeric(df["refined_score"], errors="coerce").mean()), 2)
        if "refined_score" in df.columns
        else "N/A"
    )

    missing_summary = make_missing_value_summary(df).head(20)

    provider_type_summary = value_counts_table(df, "provider_type")
    study_stage_summary = value_counts_table(df, "study_stage")
    subject_area_summary = value_counts_table(df, "subject_area")
    refined_bucket_summary = value_counts_table(df, "refined_bucket")

    report = f"""# NZ Fee Portal Data Quality Report

## Overview

| Metric | Value |
|---|---:|
| Total rows | {total_rows} |
| Total columns | {total_columns} |
| Unique providers | {provider_count} |
| Unique programme names | {programme_count} |
| Unknown subject_area count | {unknown_subject_count} |
| Average refined_score | {average_refined_score} |

## Missing Value Summary

{dataframe_to_markdown(missing_summary)}

## Provider Type Distribution

{dataframe_to_markdown(provider_type_summary)}

## Study Stage Distribution

{dataframe_to_markdown(study_stage_summary)}

## Subject Area Distribution

{dataframe_to_markdown(subject_area_summary)}

## Refined Bucket Distribution

{dataframe_to_markdown(refined_bucket_summary)}
"""

    return report


def write_report(report: str, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown data quality report from SQLite."
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database.",
    )

    parser.add_argument(
        "--table-name",
        type=str,
        default=DEFAULT_TABLE_NAME,
        help="SQLite table name.",
    )

    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Output Markdown report path.",
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

    logger.info("Reading table from SQLite")
    logger.info("Database path: %s", args.db_path)
    logger.info("Table name: %s", args.table_name)

    df = read_table(
        db_path=args.db_path,
        table_name=args.table_name,
    )

    logger.info("Rows loaded: %s", len(df))

    report = build_report(df)

    write_report(
        report=report,
        report_path=args.report_path,
    )

    logger.info("Report written to: %s", args.report_path)


if __name__ == "__main__":
    main()