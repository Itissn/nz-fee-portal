from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.db_utils import (
    get_distinct_values_sqlite,
    load_csv_to_sqlite,
    query_programmes_sqlite,
)


CSV_PATH = ROOT_DIR / "data" / "output" / "programme_index.csv"
DB_PATH = ROOT_DIR / "local_db" / "nz_fee_portal.sqlite"
TABLE_NAME = "programme_index"


def get_app_environment() -> str:
    try:
        return st.secrets.get("APP_ENV", "local")
    except Exception:
        return "local"


@st.cache_resource
def prepare_database() -> str:
    """
    Prepare the local SQLite database for the Streamlit app.

    If the database is missing or older than the source CSV, rebuild it.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file does not exist: {CSV_PATH}")

    should_rebuild = not DB_PATH.exists()

    if DB_PATH.exists():
        should_rebuild = DB_PATH.stat().st_mtime < CSV_PATH.stat().st_mtime

    if should_rebuild:
        load_csv_to_sqlite(
            csv_path=CSV_PATH,
            db_path=DB_PATH,
            table_name=TABLE_NAME,
            if_exists="replace",
        )

    return str(DB_PATH)


@st.cache_data
def load_filter_values(db_path: str):
    provider_types = get_distinct_values_sqlite(
        db_path=db_path,
        column_name="provider_type",
        table_name=TABLE_NAME,
    )

    study_stages = get_distinct_values_sqlite(
        db_path=db_path,
        column_name="study_stage",
        table_name=TABLE_NAME,
    )

    return provider_types, study_stages


@st.cache_data
def run_search(
    db_path: str,
    query: str,
    provider_type: str,
    study_stage: str,
    limit: int,
) -> pd.DataFrame:
    records = query_programmes_sqlite(
        db_path=db_path,
        query=query,
        provider_type=provider_type,
        study_stage=study_stage,
        table_name=TABLE_NAME,
        limit=limit,
    )

    return pd.DataFrame(records)


def main():
    st.set_page_config(
        page_title="NZ Fee Reference Portal",
        layout="wide",
    )

    st.title("NZ Fee Reference Portal")
    st.caption(f"Environment: {get_app_environment()}")

    st.write(
        "Search New Zealand programme information using a local SQLite database "
        "generated from the public programme index CSV."
    )

    try:
        db_path = prepare_database()
    except Exception as error:
        st.error(f"Failed to prepare SQLite database: {error}")
        return

    provider_types, study_stages = load_filter_values(db_path)

    with st.sidebar:
        st.header("Search filters")

        query = st.text_input(
            "Keyword",
            placeholder="Example: computer, data science, business",
        )

        provider_type = st.selectbox(
            "Provider type",
            ["All"] + provider_types,
        )

        study_stage = st.selectbox(
            "Study stage",
            ["All"] + study_stages,
        )

        limit = st.slider(
            "Maximum results",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
        )

    results_df = run_search(
        db_path=db_path,
        query=query,
        provider_type=provider_type,
        study_stage=study_stage,
        limit=limit,
    )

    st.subheader("Search results")
    st.write(f"Showing {len(results_df):,} result(s).")

    if results_df.empty:
        st.info("No matching programmes found.")
        return

    preferred_columns = [
        "provider_name",
        "provider_type",
        "programme_name",
        "study_stage",
        "subject_area",
        "programme_link",
        "refined_score",
        "last_checked",
    ]

    display_columns = [
        column for column in preferred_columns
        if column in results_df.columns
    ]

    st.dataframe(
        results_df[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Show raw result data"):
        st.dataframe(results_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()