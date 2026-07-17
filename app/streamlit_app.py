#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NZ Fee Portal public Streamlit app.

Expected repository structure:
    app/streamlit_app.py
    data/output/programme_index.csv
    data/output/fee_source_index.csv
    data/output/fee_snapshot.csv
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "output"

PROGRAMME_FILE = DATA_DIR / "programme_index.csv"
FEE_SOURCE_FILE = DATA_DIR / "fee_source_index.csv"
FEE_SNAPSHOT_FILE = DATA_DIR / "fee_snapshot.csv"


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).replace("\xa0", " ")).strip()


@st.cache_data(show_spinner=False)
def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return pd.read_csv(p)


def normalize_column(df: pd.DataFrame, candidates: list[str], new_name: str, default: str = "") -> pd.DataFrame:
    df = df.copy()
    for c in candidates:
        if c in df.columns:
            df[new_name] = df[c].map(clean_text)
            return df
    df[new_name] = default
    return df


def contains_any(row: pd.Series, cols: list[str], terms: list[str]) -> bool:
    text = " ".join(clean_text(row.get(c, "")) for c in cols).lower()
    return any(t.lower() in text for t in terms if t)


def unique_sorted(df: pd.DataFrame, col: str) -> list[str]:
    if df.empty or col not in df.columns:
        return []
    return sorted(v for v in df[col].dropna().astype(str).unique().tolist() if clean_text(v))


def expanded_terms(query: str) -> list[str]:
    q = clean_text(query)
    if not q:
        return []

    terms = [q]
    ql = q.lower()
    aliases = {
        "computer": ["computing", "computer science", "information technology", "software", "data", "cyber", "ICT", "IT"],
        "computing": ["computer", "computer science", "information technology", "software", "data", "cyber", "ICT", "IT"],
        "it": ["information technology", "ICT", "computer", "computing", "software", "data", "cyber"],
        "business": ["commerce", "management", "accounting", "finance", "marketing", "administration"],
        "engineering": ["construction", "civil", "mechanical", "electrical", "automotive"],
        "health": ["nursing", "midwifery", "medical", "wellbeing"],
        "hospitality": ["tourism", "cookery", "culinary", "food and beverage"],
        "english": ["language", "ESOL", "english language"],
        "计算机": ["computer", "computing", "information technology", "software", "data science", "cyber security", "ICT", "IT"],
        "商科": ["business", "commerce", "management", "accounting", "finance", "marketing"],
        "工程": ["engineering", "construction", "civil", "mechanical", "electrical"],
        "护理": ["nursing", "health", "midwifery"],
    }
    for key, vals in aliases.items():
        if key in ql or key in q:
            terms.extend(vals)

    out = []
    seen = set()
    for t in terms:
        t = clean_text(t)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def standardise_programmes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = normalize_column(df, ["provider_name"], "provider_name")
    df = normalize_column(df, ["provider_type"], "provider_type")
    df = normalize_column(df, ["provider_website"], "provider_website")
    df = normalize_column(df, ["programme_name"], "programme_name")
    df = normalize_column(df, ["programme_link"], "programme_link")
    df = normalize_column(df, ["study_stage"], "study_stage", "Unknown")
    df = normalize_column(df, ["subject_area"], "subject_area", "Unknown")
    df = normalize_column(df, ["matched_keywords"], "matched_keywords")
    return df


def standardise_fee_sources(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = normalize_column(df, ["provider_name"], "provider_name")
    df = normalize_column(df, ["provider_type"], "provider_type")
    df = normalize_column(df, ["display_title", "source_title", "validated_title"], "source_title")
    df = normalize_column(df, ["source_link"], "source_link")
    df = normalize_column(df, ["source_type"], "source_type", "Unknown")
    df = normalize_column(df, ["display_student_type", "student_type", "validated_student_type"], "student_type", "Unknown")
    df = normalize_column(df, ["display_fee_year", "fee_year", "validated_fee_year"], "fee_year", "Unknown")
    df = normalize_column(df, ["source_quality"], "source_quality", "clean")
    df = normalize_column(df, ["notes", "refined_reason", "validation_reason"], "notes")
    if "refined_score" in df.columns:
        df["refined_score"] = pd.to_numeric(df["refined_score"], errors="coerce").fillna(0)
    elif "validation_score" in df.columns:
        df["refined_score"] = pd.to_numeric(df["validation_score"], errors="coerce").fillna(0)
    else:
        df["refined_score"] = 0
    return df


def standardise_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = normalize_column(df, ["provider_name"], "provider_name")
    df = normalize_column(df, ["provider_type"], "provider_type")
    df = normalize_column(df, ["programme_name"], "programme_name")
    df = normalize_column(df, ["study_stage"], "study_stage", "Unknown")
    df = normalize_column(df, ["student_type"], "student_type", "Unknown")
    df = normalize_column(df, ["fee_year"], "fee_year", "Unknown")
    df = normalize_column(df, ["tuition_fee_nzd"], "tuition_fee_nzd")
    df = normalize_column(df, ["fee_basis"], "fee_basis")
    df = normalize_column(df, ["source_link"], "source_link")
    df = normalize_column(df, ["notes"], "notes")
    df["tuition_fee_nzd_num"] = pd.to_numeric(df["tuition_fee_nzd"], errors="coerce")
    return df


def filter_provider(df: pd.DataFrame, provider: str) -> pd.DataFrame:
    if df.empty or provider == "All" or "provider_name" not in df.columns:
        return df
    return df[df["provider_name"].eq(provider)]


def filter_provider_type(df: pd.DataFrame, provider_type: str) -> pd.DataFrame:
    if df.empty or provider_type == "All" or "provider_type" not in df.columns:
        return df
    return df[df["provider_type"].eq(provider_type)]


def filter_stage(df: pd.DataFrame, stage: str) -> pd.DataFrame:
    if df.empty or stage == "All" or "study_stage" not in df.columns:
        return df
    return df[df["study_stage"].astype(str).str.contains(re.escape(stage), case=False, na=False)]


def filter_student_type(df: pd.DataFrame, student_type: str) -> pd.DataFrame:
    if df.empty or student_type == "All" or "student_type" not in df.columns:
        return df
    s = df["student_type"].astype(str).str.strip()
    return df[s.isin([student_type, "Both", "Unknown", ""]) | s.str.lower().eq("nan")]


def filter_year(df: pd.DataFrame, year: str) -> pd.DataFrame:
    if df.empty or not clean_text(year) or "fee_year" not in df.columns:
        return df
    y = clean_text(year)
    s = df["fee_year"].astype(str)
    return df[s.str.contains(re.escape(y), case=False, na=False) | s.isin(["Unknown", "", "nan"])]


def filter_keyword(df: pd.DataFrame, terms: list[str], cols: list[str]) -> pd.DataFrame:
    if df.empty or not terms:
        return df
    mask = df.apply(lambda r: contains_any(r, cols, terms), axis=1)
    return df[mask]


def add_programme_coverage_flags(programmes: pd.DataFrame, fee_sources: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    if programmes.empty:
        return programmes

    out = programmes.copy()
    fee_provider_set = set(fee_sources["provider_name"].dropna().astype(str)) if not fee_sources.empty and "provider_name" in fee_sources.columns else set()
    snapshot_provider_set = set(snapshots["provider_name"].dropna().astype(str)) if not snapshots.empty and "provider_name" in snapshots.columns else set()

    out["has_official_fee_source"] = out["provider_name"].isin(fee_provider_set).map({True: "Yes", False: "No"})
    out["has_extracted_fee_snapshot"] = out["provider_name"].isin(snapshot_provider_set).map({True: "Yes", False: "No"})
    return out


def dataframe(df: pd.DataFrame, link_cols: Iterable[str], height: int = 520) -> None:
    if df.empty:
        st.info("No matching rows.")
        return

    column_config = {}
    for col in link_cols:
        if col in df.columns:
            column_config[col] = st.column_config.LinkColumn(col, display_text="Open link")

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=height,
        column_config=column_config,
    )


def main() -> None:
    st.set_page_config(page_title="NZ Fee Portal", layout="wide")

    programmes = standardise_programmes(read_csv(str(PROGRAMME_FILE)))
    fee_sources = standardise_fee_sources(read_csv(str(FEE_SOURCE_FILE)))
    snapshots = standardise_snapshots(read_csv(str(FEE_SNAPSHOT_FILE)))

    st.title("NZ Fee Portal")
    st.caption(
        "Prototype reference portal for New Zealand tertiary programme pages, official fee-source links, "
        "and extracted fee snapshots. Always verify fees through the official provider links."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Programme entries", f"{len(programmes):,}")
    c2.metric("Official fee sources", f"{len(fee_sources):,}")
    c3.metric("Fee snapshots", f"{len(snapshots):,}")
    parsed_providers = snapshots["provider_name"].nunique() if not snapshots.empty and "provider_name" in snapshots.columns else 0
    c4.metric("Parsed-fee providers", f"{parsed_providers:,}")

    with st.sidebar:
        st.header("Search filters")
        keyword = st.text_input("Programme / subject keyword", value="", placeholder="e.g., computer, business, nursing")
        terms = expanded_terms(keyword)

        provider = st.selectbox("Provider", ["All"] + unique_sorted(programmes, "provider_name"))
        provider_type = st.selectbox("Provider type", ["All"] + unique_sorted(programmes, "provider_type"))
        student_type = st.selectbox("Student type", ["All", "Domestic", "International"])

        stage_options = [
            "All", "Certificate", "Diploma", "Bachelor", "Graduate",
            "Postgraduate", "Master", "Doctoral", "English Language",
            "Pathway / Foundation",
        ]
        study_stage = st.selectbox("Study stage", stage_options)
        fee_year = st.text_input("Fee year", value="2026")

        if not fee_sources.empty and "source_quality" in fee_sources.columns:
            source_quality = st.selectbox("Fee source quality", ["All"] + unique_sorted(fee_sources, "source_quality"))
        else:
            source_quality = "All"

        if terms:
            st.caption("Expanded terms: " + "; ".join(terms[:12]))

    prog = programmes.copy()
    prog = filter_provider(prog, provider)
    prog = filter_provider_type(prog, provider_type)
    prog = filter_stage(prog, study_stage)
    prog = filter_keyword(prog, terms, ["programme_name", "subject_area", "matched_keywords", "study_stage", "provider_name"])
    prog = add_programme_coverage_flags(prog, fee_sources, snapshots)

    fs = fee_sources.copy()
    fs = filter_provider(fs, provider)
    fs = filter_provider_type(fs, provider_type)
    fs = filter_student_type(fs, student_type)
    fs = filter_year(fs, fee_year)
    if source_quality != "All" and "source_quality" in fs.columns:
        fs = fs[fs["source_quality"].eq(source_quality)]

    if terms:
        fs_text = filter_keyword(fs, terms, ["provider_name", "source_title", "source_link", "notes", "student_type"])
        provider_set = set(prog["provider_name"].dropna().astype(str)) if not prog.empty and "provider_name" in prog.columns else set()
        fs_provider = fs[fs["provider_name"].isin(provider_set)] if "provider_name" in fs.columns else fs.iloc[0:0]
        fs = pd.concat([fs_text, fs_provider], ignore_index=True).drop_duplicates()

    snap = snapshots.copy()
    snap = filter_provider(snap, provider)
    snap = filter_provider_type(snap, provider_type)
    snap = filter_student_type(snap, student_type)
    snap = filter_stage(snap, study_stage)
    snap = filter_year(snap, fee_year)
    snap = filter_keyword(snap, terms, ["programme_name", "study_stage", "provider_name", "notes"])

    tab1, tab2, tab3 = st.tabs([
        "Programme matches",
        "Official fee sources",
        "Extracted fee snapshots (partial coverage)",
    ])

    with tab1:
        st.subheader(f"Programme matches ({len(prog):,})")
        st.write(
            "Programme pages are usually shared by Domestic and International students. "
            "Use the coverage columns to see whether a provider has an official fee source or parsed fee snapshot."
        )

        cols = [
            "provider_name", "provider_type", "programme_name", "study_stage", "subject_area",
            "has_official_fee_source", "has_extracted_fee_snapshot", "programme_link",
        ]
        cols = [c for c in cols if c in prog.columns]
        dataframe(prog[cols], ["programme_link"])

        st.download_button(
            "Download programme matches",
            data=prog.to_csv(index=False).encode("utf-8-sig"),
            file_name="programme_matches.csv",
            mime="text/csv",
        )

    with tab2:
        st.subheader(f"Official fee sources ({len(fs):,})")
        st.write(
            "This table contains official or useful fee-source links. "
            "Rows marked supporting may be less direct than clean fee pages."
        )

        cols = [
            "provider_name", "provider_type", "source_title", "source_type", "student_type",
            "fee_year", "source_quality", "refined_score", "source_link", "notes",
        ]
        cols = [c for c in cols if c in fs.columns]
        dataframe(fs[cols], ["source_link"])

        st.download_button(
            "Download official fee sources",
            data=fs.to_csv(index=False).encode("utf-8-sig"),
            file_name="official_fee_sources.csv",
            mime="text/csv",
        )

    with tab3:
        st.subheader(f"Extracted fee snapshots (partial coverage) ({len(snap):,})")
        st.warning(
            "Parsed fee amounts are available only for providers where reliable structured fee data could be extracted. "
            "If no amount is shown, use the programme page or official fee source link."
        )

        cols = [
            "provider_name", "provider_type", "programme_name", "study_stage", "student_type",
            "fee_year", "tuition_fee_nzd", "fee_basis", "source_link", "notes",
        ]
        cols = [c for c in cols if c in snap.columns]
        dataframe(snap[cols], ["source_link"])

        st.download_button(
            "Download extracted fee snapshots",
            data=snap.to_csv(index=False).encode("utf-8-sig"),
            file_name="extracted_fee_snapshots.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
