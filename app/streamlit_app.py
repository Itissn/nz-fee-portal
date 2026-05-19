#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Streamlit app for NZFeePortal.

Important design choice
-----------------------
Programme pages usually do NOT have Domestic/International labels. The same
programme page is used for both student types. Therefore, the Student type
filter is applied to:
    1. Official fee sources
    2. Extracted fee snapshots
    3. The fee-source links attached to each programme row

It is NOT used to remove programme rows directly unless a programme table
actually contains a student_type column.

Run:
    cd /d D:\NZFeePortal
    streamlit run app\streamlit_app.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "output"
CONFIG_DIR = ROOT / "config"

PROGRAMME_PATHS = [
    OUTPUT_DIR / "programme_index.csv",
    OUTPUT_DIR / "programme_index_app.csv",
    OUTPUT_DIR / "programme_index_final.csv",
    OUTPUT_DIR / "programme_index_clean.csv",
]

FEE_SOURCE_PATHS = [
    OUTPUT_DIR / "fee_source_index.csv",
    OUTPUT_DIR / "fee_source_index_validated_clean.csv",
]

FEE_SNAPSHOT_PATHS = [
    OUTPUT_DIR / "fee_snapshot.csv",
    OUTPUT_DIR / "programme_level_fees_2026_repaired.csv",
]

ALIASES_PATH = CONFIG_DIR / "keyword_aliases.csv"


def read_first_existing(paths: Iterable[Path]) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            try:
                return pd.read_csv(path, encoding="utf-8-sig")
            except Exception:
                return pd.read_csv(path)
    return pd.DataFrame()


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).replace("\xa0", " ")).strip()


def norm_col(df: pd.DataFrame, candidates: list[str], new_name: str, default: str = "") -> pd.DataFrame:
    df = df.copy()
    for c in candidates:
        if c in df.columns:
            df[new_name] = df[c].map(clean_text)
            return df
    df[new_name] = default
    return df


def contains_any_text(row: pd.Series, cols: list[str], terms: list[str]) -> bool:
    hay = " ".join(clean_text(row.get(c, "")) for c in cols).lower()
    return any(t.lower() in hay for t in terms if t)


def load_alias_terms(query: str) -> list[str]:
    query = clean_text(query)
    if not query:
        return []

    terms = [query]
    q_lower = query.lower()

    # Built-in aliases for common Chinese/English searches.
    builtin = {
        "计算机": [
            "computer", "computer science", "computing", "information technology",
            "information systems", "software", "software engineering", "data science",
            "cyber", "cyber security", "artificial intelligence", "machine learning",
            "ict", "it", "digital technologies",
        ],
        "商科": [
            "business", "commerce", "management", "accounting", "finance",
            "marketing", "economics", "entrepreneurship", "administration",
        ],
        "工程": [
            "engineering", "civil", "mechanical", "electrical", "construction",
            "quantity surveying", "automotive",
        ],
        "护理": ["nursing", "health", "midwifery"],
        "教育": ["education", "teaching", "early childhood"],
        "酒店": ["hospitality", "tourism", "cookery", "culinary"],
    }

    for k, aliases in builtin.items():
        if k in query:
            terms.extend(aliases)

    if ALIASES_PATH.exists():
        try:
            alias_df = pd.read_csv(ALIASES_PATH, encoding="utf-8-sig")
            for _, r in alias_df.iterrows():
                key = clean_text(r.get("query_keyword", "")).lower()
                aliases = clean_text(r.get("aliases", ""))
                if key and (key in q_lower or q_lower in key):
                    terms.extend([a.strip() for a in aliases.split(";") if a.strip()])
        except Exception:
            pass

    # If English query is broad, add common variants.
    if q_lower in {"it", "ict", "computer", "computing"}:
        terms.extend([
            "computer science", "computing", "information technology",
            "software", "data", "cyber", "ict", "it",
        ])
    if q_lower in {"business", "commerce"}:
        terms.extend(["management", "accounting", "finance", "marketing"])

    # Deduplicate, preserving order.
    out = []
    seen = set()
    for t in terms:
        t = clean_text(t)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def standardize_programmes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df = norm_col(df, ["provider_name"], "provider_name")
    df = norm_col(df, ["provider_type"], "provider_type")
    df = norm_col(df, ["programme_name"], "programme_name")
    df = norm_col(df, ["programme_link"], "programme_link")
    df = norm_col(df, ["study_stage"], "study_stage", "Unknown")
    df = norm_col(df, ["subject_area"], "subject_area", "Unknown")
    df = norm_col(df, ["matched_keywords"], "matched_keywords")
    return df


def standardize_fee_sources(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df = norm_col(df, ["provider_name"], "provider_name")
    df = norm_col(df, ["provider_type"], "provider_type")
    df = norm_col(df, ["display_title", "validated_title", "source_title"], "source_title")
    df = norm_col(df, ["source_link"], "source_link")
    df = norm_col(df, ["source_type"], "source_type")
    df = norm_col(df, ["display_student_type", "validated_student_type", "student_type"], "student_type", "Unknown")
    df = norm_col(df, ["display_fee_year", "validated_fee_year", "fee_year"], "fee_year", "Unknown")
    df = norm_col(df, ["refined_score", "validation_score", "source_score"], "source_score", "0")
    df = norm_col(df, ["refined_reason", "validation_reason", "notes"], "notes")
    return df


def standardize_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df = norm_col(df, ["provider_name"], "provider_name")
    df = norm_col(df, ["provider_type"], "provider_type")
    df = norm_col(df, ["programme_name"], "programme_name")
    df = norm_col(df, ["study_stage"], "study_stage", "Unknown")
    df = norm_col(df, ["student_type"], "student_type", "Unknown")
    df = norm_col(df, ["fee_year"], "fee_year", "Unknown")
    df = norm_col(df, ["tuition_fee_nzd"], "tuition_fee_nzd")
    df = norm_col(df, ["fee_basis"], "fee_basis")
    df = norm_col(df, ["source_link", "official_fee_link"], "source_link")
    df = norm_col(df, ["notes"], "notes")
    return df


def filter_student_type(df: pd.DataFrame, selected: str, col: str = "student_type") -> pd.DataFrame:
    if df.empty or selected == "All" or col not in df.columns:
        return df

    s = df[col].astype(str).str.strip()
    # Both and Unknown are kept because they may be general fee pages useful to both groups.
    return df[s.isin([selected, "Both", "Unknown", ""]) | s.str.lower().eq("nan")]


def filter_study_stage(df: pd.DataFrame, selected: str) -> pd.DataFrame:
    if df.empty or selected == "All" or "study_stage" not in df.columns:
        return df
    return df[df["study_stage"].astype(str).str.contains(re.escape(selected), case=False, na=False)]


def filter_year(df: pd.DataFrame, selected_year: str) -> pd.DataFrame:
    if df.empty or not selected_year or selected_year == "All":
        return df
    if "fee_year" not in df.columns:
        return df
    s = df["fee_year"].astype(str)
    return df[s.str.contains(re.escape(selected_year), case=False, na=False) | s.isin(["Unknown", "", "nan"])]


def attach_fee_links(programmes: pd.DataFrame, fee_sources: pd.DataFrame, student_type: str) -> pd.DataFrame:
    if programmes.empty:
        return programmes
    if fee_sources.empty:
        programmes = programmes.copy()
        programmes["relevant_fee_sources"] = ""
        return programmes

    fs = filter_student_type(fee_sources, student_type)
    fs = fs.copy()
    fs["source_label"] = fs.apply(
        lambda r: f"{clean_text(r.get('student_type', 'Unknown'))}: {clean_text(r.get('source_title', 'fee source'))} | {clean_text(r.get('source_link', ''))}",
        axis=1,
    )

    grouped = (
        fs.groupby("provider_name")["source_label"]
        .apply(lambda x: "\n".join(list(dict.fromkeys([v for v in x if v]))[:5]))
        .to_dict()
    )

    out = programmes.copy()
    out["relevant_fee_sources"] = out["provider_name"].map(grouped).fillna("")
    return out


def dataframe_with_links(df: pd.DataFrame, link_cols: list[str], height: int = 520) -> None:
    if df.empty:
        st.info("No matching rows.")
        return

    column_config = {}
    for c in link_cols:
        if c in df.columns:
            column_config[c] = st.column_config.LinkColumn(c, display_text="Open link")

    st.dataframe(
        df,
        hide_index=True,
        column_config=column_config,
        height=height,
        width="stretch",
    )


def main() -> None:
    st.set_page_config(page_title="NZ Fee Portal", layout="wide")

    st.title("NZ Fee Portal")
    st.caption(
        "Programme-aware fee reference portal. Programme pages usually do not have Domestic/International labels, "
        "so Student type filters fee sources and fee snapshots, and attaches matching fee links to programme results."
    )

    programmes = standardize_programmes(read_first_existing(PROGRAMME_PATHS))
    fee_sources = standardize_fee_sources(read_first_existing(FEE_SOURCE_PATHS))
    snapshots = standardize_snapshots(read_first_existing(FEE_SNAPSHOT_PATHS))

    with st.sidebar:
        st.header("Search filters")

        keyword = st.text_input("Programme / subject keyword", value="")
        query_terms = load_alias_terms(keyword)

        provider_options = ["All"]
        if not programmes.empty and "provider_name" in programmes.columns:
            provider_options += sorted(programmes["provider_name"].dropna().astype(str).unique().tolist())
        provider = st.selectbox("Provider", provider_options)

        type_options = ["All"]
        if not programmes.empty and "provider_type" in programmes.columns:
            type_options += sorted(programmes["provider_type"].dropna().astype(str).unique().tolist())
        provider_type = st.selectbox("Provider type", type_options)

        student_type = st.selectbox("Student type", ["All", "Domestic", "International"])

        stage_options = ["All", "Certificate", "Diploma", "Bachelor", "Graduate", "Postgraduate", "Master", "Doctoral", "English Language", "Pathway / Foundation"]
        study_stage = st.selectbox("Study stage", stage_options)

        fee_year = st.text_input("Fee year", value="2026")

        only_fee_snapshots = st.checkbox("Only show extracted fee snapshots", value=False)

        if query_terms:
            st.caption("Expanded search terms: " + "; ".join(query_terms[:12]))

    # Programme filtering
    prog = programmes.copy()
    if not prog.empty:
        if provider != "All":
            prog = prog[prog["provider_name"].eq(provider)]
        if provider_type != "All":
            prog = prog[prog["provider_type"].eq(provider_type)]
        prog = filter_study_stage(prog, study_stage)

        if query_terms:
            cols = ["programme_name", "subject_area", "matched_keywords", "study_stage"]
            mask = prog.apply(lambda r: contains_any_text(r, cols, query_terms), axis=1)
            prog = prog[mask]

        # Only if a future programme table has student_type, apply it. Usually it does not.
        if "student_type" in prog.columns:
            prog = filter_student_type(prog, student_type)

    # Fee source filtering
    fs = fee_sources.copy()
    if not fs.empty:
        if provider != "All":
            fs = fs[fs["provider_name"].eq(provider)]
        if provider_type != "All":
            fs = fs[fs["provider_type"].eq(provider_type)]
        fs = filter_student_type(fs, student_type)
        fs = filter_year(fs, fee_year)
        if query_terms:
            cols = ["provider_name", "source_title", "source_type", "student_type", "notes", "source_link"]
            mask = fs.apply(lambda r: contains_any_text(r, cols, query_terms), axis=1)
            # If keyword is programme-specific, fee source pages may not mention it.
            # Keep provider-linked fee sources if programme matches exist.
            providers_from_prog = set(prog["provider_name"].unique()) if not prog.empty and "provider_name" in prog.columns else set()
            mask_provider = fs["provider_name"].isin(providers_from_prog) if "provider_name" in fs.columns else False
            fs = fs[mask | mask_provider]

    # Snapshot filtering
    snap = snapshots.copy()
    if not snap.empty:
        if provider != "All":
            snap = snap[snap["provider_name"].eq(provider)]
        if provider_type != "All" and "provider_type" in snap.columns:
            snap = snap[snap["provider_type"].eq(provider_type)]
        snap = filter_student_type(snap, student_type)
        snap = filter_study_stage(snap, study_stage)
        snap = filter_year(snap, fee_year)
        if query_terms:
            cols = ["programme_name", "study_stage", "notes"]
            mask = snap.apply(lambda r: contains_any_text(r, cols, query_terms), axis=1)
            snap = snap[mask]

    prog_with_links = attach_fee_links(prog, fs, student_type)

    if only_fee_snapshots:
        default_tab = "Extracted fee snapshots"
    else:
        default_tab = "Programme matches"

    tab1, tab2, tab3 = st.tabs(["Programme matches", "Official fee sources", "Extracted fee snapshots"])

    with tab1:
        st.subheader(f"Programme matches ({len(prog_with_links)})")
        st.caption(
            "Student type does not normally remove programme rows because official programme pages are usually shared by Domestic and International students. "
            "The selected student type is used to attach relevant fee-source links in the last column."
        )

        display_cols = [
            c for c in [
                "provider_name",
                "provider_type",
                "programme_name",
                "study_stage",
                "subject_area",
                "programme_link",
                "relevant_fee_sources",
            ]
            if c in prog_with_links.columns
        ]
        dataframe_with_links(prog_with_links[display_cols], ["programme_link"], height=520)

        st.download_button(
            "Download programme matches",
            data=prog_with_links.to_csv(index=False).encode("utf-8-sig"),
            file_name="programme_matches.csv",
            mime="text/csv",
        )

    with tab2:
        st.subheader(f"Official fee sources ({len(fs)})")
        st.caption("This table is filtered by Student type. Rows labelled Unknown or Both are kept as general sources.")

        display_cols = [
            c for c in [
                "provider_name",
                "provider_type",
                "source_title",
                "source_type",
                "student_type",
                "fee_year",
                "source_score",
                "source_link",
                "notes",
            ]
            if c in fs.columns
        ]
        dataframe_with_links(fs[display_cols], ["source_link"], height=520)

        st.download_button(
            "Download fee sources",
            data=fs.to_csv(index=False).encode("utf-8-sig"),
            file_name="official_fee_sources.csv",
            mime="text/csv",
        )

    with tab3:
        st.subheader(f"Extracted fee snapshots ({len(snap)})")
        st.caption("This table is filtered by Student type and Fee year when those columns are available.")

        display_cols = [
            c for c in [
                "provider_name",
                "provider_type",
                "programme_name",
                "study_stage",
                "student_type",
                "fee_year",
                "tuition_fee_nzd",
                "fee_basis",
                "source_link",
                "notes",
            ]
            if c in snap.columns
        ]
        dataframe_with_links(snap[display_cols], ["source_link"], height=520)

        st.download_button(
            "Download fee snapshots",
            data=snap.to_csv(index=False).encode("utf-8-sig"),
            file_name="fee_snapshots.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
