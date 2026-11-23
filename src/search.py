"""SQL shared by Streamlit and integration tests. Filter values are bound parameters."""

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class Filters:
    keyword: str = ""
    provider: str = ""
    provider_type: str = ""
    stage: str = ""
    student: str = ""
    year: str = ""
    source_quality: str = ""
    include_unknown: bool = False


SUBJECTS = {
    "computer": (
        "computing",
        "computer",
        "information technology",
        "software",
        "data science",
    ),
    "business": (
        "business",
        "commerce",
        "management",
        "accounting",
        "finance",
        "marketing",
    ),
    "engineering": ("engineering", "construction", "civil", "mechanical", "electrical"),
    "health": ("nursing", "midwifery", "medical", "health"),
    "hospitality": ("hospitality", "tourism", "cookery", "culinary"),
    "english": ("english", "language", "esol"),
}
ALIASES = {
    "computing": "computer",
    "it": "computer",
    "计算机": "computer",
    "商科": "business",
    "工程": "engineering",
    "护理": "health",
}


def terms(keyword):
    term = " ".join(keyword.casefold().split())
    return (
        list(dict.fromkeys([term, *SUBJECTS.get(ALIASES.get(term, term), ())]))
        if term
        else []
    )


def _keyword(columns, words, params):
    haystack = " || ' ' || ".join(columns)
    params.extend(words)
    return "(" + " OR ".join(f"instr(fold({haystack}), ?) > 0" for _ in words) + ")"


def _fee_filters(filters, alias, params):
    clauses = []
    for field, value in (("fee_year", filters.year), ("student_type", filters.student)):
        if value:
            checked = f"instr(';' || replace({alias}.{field}, ' ', '') || ';', ';' || ? || ';') > 0"
            params.append(value)
            if field == "student_type":
                checked += f" OR {alias}.{field} = 'Both'"
            if filters.include_unknown:
                checked += f" OR lower({alias}.{field}) IN ('', 'unknown')"
            clauses.append(f"({checked})")
    return clauses


def query(db, dataset, filters, selected=None):
    """selected is (provider ID, programme name). Sources remain provider-level references."""
    params, clauses = [], []
    words = terms(filters.keyword)
    if dataset == "programmes":
        source = "programme_index p"
        cols = """p.provider_id, p.provider_name, p.programme_name, p.study_stage, p.subject_area,
                  p.last_checked, p.programme_link,
                  EXISTS (SELECT 1 FROM fee_source_index f WHERE f.provider_id=p.provider_id) AS provider_has_source,
                  EXISTS (SELECT 1 FROM fee_snapshot s WHERE s.provider_id=p.provider_id) AS provider_has_snapshots"""
        alias = "p"
        search_cols = [
            "p.programme_name",
            "p.subject_area",
            "p.matched_keywords",
            "p.provider_name",
        ]
    elif dataset == "sources":
        source, alias = "fee_source_index f", "f"
        cols = "f.provider_name, f.source_title, f.student_type, f.fee_year, f.source_quality, f.last_checked, f.source_link, f.notes"
        search_cols = ["f.source_title", "f.provider_name", "f.notes"]
        if filters.source_quality:
            clauses.append("f.source_quality=?")
            params.append(filters.source_quality)
    elif dataset == "fees":
        source, alias = "fee_snapshot s", "s"
        cols = """s.provider_name, s.programme_name, s.major_name, s.specialisation_name,
                  s.student_type, s.fee_year, s.tuition_fee_nzd, s.fee_basis, s.last_checked,
                  s.source_link, s.quality_flags, s.calculation_method"""
        search_cols = [
            "s.programme_name",
            "s.provider_name",
            "s.major_name",
            "s.specialisation_name",
            "s.notes",
        ]
    else:
        raise ValueError("Unknown dataset")
    if filters.provider:
        clauses.append(f"{alias}.provider_name=?")
        params.append(filters.provider)
    if filters.provider_type:
        if dataset == "fees":
            clauses.append(
                "EXISTS (SELECT 1 FROM programme_index pt WHERE pt.provider_id=s.provider_id AND pt.provider_type=?)"
            )
        else:
            clauses.append(f"{alias}.provider_type=?")
        params.append(filters.provider_type)
    if dataset != "programmes":
        clauses.extend(_fee_filters(filters, alias, params))
    if selected is not None:
        clauses.append(f"{alias}.provider_id=?")
        params.append(selected[0])
        if dataset == "fees":
            clauses.append(
                "fold(s.programme_name)=fold(?) AND instr(s.quality_flags,'numeric_programme_name')=0"
            )
            params.append(selected[1])
    else:
        if filters.stage and dataset != "sources":
            level = (
                "s.study_stage || ';' || s.qualification_level"
                if dataset == "fees"
                else "p.study_stage"
            )
            clauses.append(
                f"instr(';' || replace(fold({level}), '; ', ';') || ';', ';' || fold(?) || ';')>0"
            )
            params.append(filters.stage)
        if words:
            match = _keyword(search_cols, words, params)
            if dataset == "sources":
                provider_match = _keyword(
                    ["p.programme_name", "p.subject_area", "p.matched_keywords"],
                    words,
                    params,
                )
                match = f"({match} OR EXISTS (SELECT 1 FROM programme_index p WHERE p.provider_id=f.provider_id AND {provider_match}))"
            clauses.append(match)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    order = (
        "provider_name, source_title"
        if dataset == "sources"
        else "provider_name, programme_name"
    )
    return pd.read_sql_query(
        f"SELECT {cols} FROM {source}{where} ORDER BY {order}, {alias}.source_line",
        db,
        params=params,
    )
