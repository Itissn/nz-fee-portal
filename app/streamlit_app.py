from pathlib import Path
import sys

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.portal_search import load_csv_data, search_programmes_smart


PROGRAMME_INDEX_PATH = ROOT_DIR / "data" / "output" / "programme_index.csv"


@st.cache_data
def load_programme_index():
    return load_csv_data(PROGRAMME_INDEX_PATH)


def main():
    st.set_page_config(
        page_title="NZ Fee Reference Portal",
        layout="wide",
    )

    st.title("NZ Fee Reference Portal")
    st.write(
        "Search New Zealand programme fee information collected from public sources."
    )

    try:
        df = load_programme_index()
    except Exception as error:
        st.error(f"Failed to load programme index: {error}")
        return

    st.caption(f"Loaded {len(df):,} programme records.")

    query = st.text_input(
        "Search programme or provider",
        placeholder="Example: computer science, data science, Victoria",
    )

    filtered_df = search_programmes_smart(df, query)

    st.write(f"Showing {len(filtered_df):,} result(s).")
    st.dataframe(filtered_df, use_container_width=True)


if __name__ == "__main__":
    main()