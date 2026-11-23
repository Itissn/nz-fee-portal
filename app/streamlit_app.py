"""Search historical NZ study options, then inspect traceable fee evidence."""

import csv
import os
import sqlite3
from datetime import date
import sys
from contextlib import closing
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.catalogue import DB, ensure_database, open_reader
from src.search import Filters, query


def choices(db, sql):
    return ["", *(row[0] for row in db.execute(sql) if row[0])]


def table(frame, key):
    if frame.empty:
        st.info("No matching records.")
        return
    if "last_checked" in frame.columns:
        frame = frame.copy()
        today = date.today()
        frame["days_since_check"] = frame.last_checked.map(
            lambda day: (today - date.fromisoformat(day)).days
        )
    links = {
        c: st.column_config.LinkColumn(
            c.replace("_", " ").title(), display_text="Open provider page"
        )
        for c in frame
        if c.endswith("_link")
    }
    st.dataframe(frame, hide_index=True, column_config=links, width="stretch")
    st.download_button(
        "Download these results",
        frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{key}.csv",
        mime="text/csv",
        key=key,
    )


def show_catalogue(db):
    st.caption(
        "Search a saved New Zealand tertiary catalogue, then check the provider, source date and fee basis."
    )
    input_counts = dict(db.execute("SELECT dataset, row_count FROM catalogue_sources"))
    for col, (label, name) in zip(
        st.columns(3),
        [
            ("Programmes", "programme_index"),
            ("Fee sources", "fee_source_index"),
            ("Fee records", "fee_snapshot"),
        ],
    ):
        col.metric(label, f"{input_counts[name]:,}")
    with st.sidebar:
        st.header("Search")
        keyword = st.text_input("Programme or subject", placeholder="e.g. nursing")
        provider = st.selectbox(
            "Provider",
            choices(
                db,
                """SELECT provider_name FROM programme_index UNION
            SELECT provider_name FROM fee_source_index UNION SELECT provider_name FROM fee_snapshot ORDER BY 1""",
            ),
            format_func=any_label,
        )
        institution = st.selectbox(
            "Provider type",
            choices(
                db, "SELECT DISTINCT provider_type FROM programme_index ORDER BY 1"
            ),
            format_func=any_label,
        )
        stage_values = sorted(
            {
                v.strip()
                for (s,) in db.execute(
                    "SELECT DISTINCT study_stage FROM programme_index"
                )
                for v in s.split(";")
                if v.strip()
            }
        )
        stage = st.selectbox("Study stage", ["", *stage_values], format_func=any_label)
        st.subheader("Fee evidence")
        st.caption(
            "These filters apply to fee records and sources. Programme pages cover both student groups."
        )
        student = st.selectbox(
            "Student type", ["", "Domestic", "International"], format_func=any_label
        )
        year = st.text_input("Fee year", placeholder="All years")
        quality = st.selectbox(
            "Source quality",
            choices(
                db, "SELECT DISTINCT source_quality FROM fee_source_index ORDER BY 1"
            ),
            format_func=any_label,
        )
        unknown = st.checkbox(
            "Include records with an unspecified year or student group"
        )
    filters = Filters(
        keyword, provider, institution, stage, student, year.strip(), quality, unknown
    )
    programmes = query(db, "programmes", filters)
    browse, sources, fees, audit = st.tabs(
        ["Find a programme", "Provider sources", "Fee snapshots", "Data quality"]
    )
    with browse:
        st.subheader(f"{len(programmes):,} programme matches")
        st.caption(
            "Coverage columns count evidence at the provider level across the saved catalogue."
        )
        table(programmes.drop(columns="provider_id"), "programmes")
        if not programmes.empty:
            labels = (
                programmes.provider_name + " — " + programmes.programme_name
            ).tolist()
            index = st.selectbox(
                "Inspect one programme",
                list(range(len(labels))),
                format_func=lambda i: labels[i],
            )
            row = programmes.iloc[index]
            selected = (row.provider_id, row.programme_name)
            st.markdown("**Historical fee evidence for this programme**")
            matched = query(db, "fees", filters, selected)
            if matched.empty:
                st.info(
                    "No exact provider-and-programme-name match under these fee filters. Use the provider links below."
                )
            else:
                st.caption(
                    "Name match only. Check the major, fee basis, student type and year with the provider."
                )
                table(matched, "programme_fees")
            st.markdown("**Provider reference links**")
            st.caption(
                "These links refer to the provider. They may cover several programmes."
            )
            table(query(db, "sources", filters, selected), "programme_sources")
            st.link_button("Open this programme's provider page", row.programme_link)
    with sources:
        st.caption(
            "Includes direct and supporting links. Use the source quality filter to distinguish them."
        )
        table(query(db, "sources", filters), "sources")
    with fees:
        st.caption(
            "Historical NZD amounts. Compare only after confirming the fee basis and year on the linked page."
        )
        table(query(db, "fees", filters), "fees")
    with audit:
        st.caption(
            "Last checked is the date recorded in the source CSV. A new import does not recheck provider pages."
        )
        table(
            pd.read_sql_query(
                """SELECT dataset, row_count, sha256 FROM catalogue_sources ORDER BY dataset""",
                db,
            ),
            "manifest",
        )
        summary = pd.read_sql_query(
            """SELECT dataset, issue, COUNT(*) AS affected_rows FROM catalogue_issues
                                       GROUP BY dataset, issue ORDER BY dataset, issue""",
            db,
        )
        st.markdown("**Quality findings**")
        table(summary, "quality_summary")
        with st.expander("Locate flagged CSV records"):
            table(
                pd.read_sql_query(
                    "SELECT * FROM catalogue_issues ORDER BY dataset, source_line, issue",
                    db,
                ),
                "flagged_records",
            )


def any_label(value):
    return value or "All"


def main():
    db_path = Path(os.environ.get("NZ_FEE_DB") or DB)
    st.set_page_config(page_title="NZ Fee Portal", layout="wide")
    st.title("NZ Fee Portal")
    try:
        ensure_database(db_path)
        with closing(open_reader(db_path)) as db:
            db.execute(
                "BEGIN"
            )  # Every tab in a rerun reads the same published release.
            show_catalogue(db)
    except (OSError, ValueError, csv.Error, sqlite3.Error) as error:
        st.error(f"Catalogue unavailable: {error}")


if __name__ == "__main__":
    main()
