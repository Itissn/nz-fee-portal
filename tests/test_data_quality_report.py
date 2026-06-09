from pathlib import Path

import pandas as pd

from scripts.data_quality_report import (
    build_report,
    make_missing_value_summary,
    value_counts_table,
)


def test_make_missing_value_summary_counts_missing_and_empty_values():
    df = pd.DataFrame(
        {
            "provider_name": ["A", "", None],
            "programme_name": ["P1", "P2", "P3"],
        }
    )

    summary = make_missing_value_summary(df)

    provider_row = summary[
        summary["column"] == "provider_name"
    ].iloc[0]

    assert provider_row["missing_or_empty_count"] == 2


def test_value_counts_table_returns_expected_counts():
    df = pd.DataFrame(
        {
            "study_stage": ["Bachelor", "Bachelor", "Master"],
        }
    )

    result = value_counts_table(df, "study_stage")

    bachelor_count = result[
        result["study_stage"] == "Bachelor"
    ]["count"].iloc[0]

    assert bachelor_count == 2


def test_build_report_contains_expected_sections():
    df = pd.DataFrame(
        {
            "provider_name": ["Provider A", "Provider B"],
            "provider_type": ["University", "PTE"],
            "programme_name": ["Programme A", "Programme B"],
            "study_stage": ["Bachelor", "Master"],
            "subject_area": ["Computer Science", "Unknown"],
            "refined_bucket": ["clean", "clean"],
            "refined_score": [100, 80],
        }
    )

    report = build_report(df)

    assert "# NZ Fee Portal Data Quality Report" in report
    assert "## Overview" in report
    assert "## Missing Value Summary" in report
    assert "## Study Stage Distribution" in report