"""Import one complete set of snapshots and its quality findings into SQLite."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DB = ROOT / "local_db" / "nz_fee_portal.sqlite"
VERSION = 1
PROGRAMMES = "programme_index"
SOURCES = "fee_source_index"
FEES = "fee_snapshot"
FIELDS = {
    PROGRAMMES: (
        "provider_id provider_name provider_type programme_name programme_link "
        "study_stage subject_area matched_keywords last_checked refined_score refined_bucket"
    ).split(),
    SOURCES: (
        "provider_id provider_name provider_type source_title source_link source_type "
        "student_type fee_year source_quality notes last_checked"
    ).split(),
    FEES: (
        "provider_id provider_name programme_name qualification_level study_stage "
        "major_name specialisation_name student_type fee_year tuition_fee_nzd fee_basis "
        "source_link last_checked calculation_method notes"
    ).split(),
}
OPTIONAL = {
    "matched_keywords",
    "refined_score",
    "refined_bucket",
    "major_name",
    "specialisation_name",
    "notes",
    "source_type",
    "qualification_level",
    "calculation_method",
}
TRUSTED_LINK = {
    PROGRAMMES: "programme_link",
    SOURCES: "source_link",
    FEES: "source_link",
}


def normalized(value):
    return " ".join(value.casefold().split())


def warn_if_needed(table, row):
    """Flag usable historical records for review without guessing a replacement."""
    if table == PROGRAMMES and row["subject_area"].casefold() in ("", "unknown"):
        yield "unknown_subject"
    if table == SOURCES and row["fee_year"].casefold() in ("", "unknown"):
        yield "unknown_source_year"
    if table == FEES:
        if row["programme_name"].isdecimal():
            yield "numeric_programme_name"
        if not row["fee_basis"]:
            yield "missing_fee_basis"
        elif "$" in row["fee_basis"]:
            yield "currency_in_fee_basis"


def parse_file(table, content):
    reader = csv.DictReader(
        io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True
    )
    header = reader.fieldnames or []
    missing = set(FIELDS[table]) - OPTIONAL - set(header)
    if missing or not all(header) or len(set(header)) != len(header):
        raise ValueError(
            f"{table}: missing or invalid column headers {sorted(missing)}"
        )
    records, warnings, seen = [], [], set()
    for raw in reader:
        n = reader.line_num
        try:
            if None in raw or None in raw.values():
                raise ValueError("row has a different number of cells than the header")
            row = {key: raw.get(key, "").strip() for key in FIELDS[table]}
            if table == SOURCES:
                for field in ("source_title", "student_type", "fee_year"):
                    preferred = (
                        "display_title"
                        if field == "source_title"
                        else f"display_{field}"
                    )
                    row[field] = raw.get(preferred, "").strip() or row[field]
            for key in (
                "provider_id",
                "provider_name",
                "source_title" if table == SOURCES else "programme_name",
            ):
                if not row[key]:
                    raise ValueError(f"empty {key}")
            url = urlsplit(row[TRUSTED_LINK[table]])
            if url.scheme.lower() not in ("http", "https") or not url.hostname:
                raise ValueError(f"invalid {TRUSTED_LINK[table]}")
            checked = date.fromisoformat(row["last_checked"])
            if checked.isoformat() != row["last_checked"]:
                raise ValueError("last_checked must use YYYY-MM-DD")
            identity = (
                tuple(raw.values())
                if table == FEES
                else (row["provider_id"], row[TRUSTED_LINK[table]])
            )
            if identity in seen:
                raise ValueError("duplicate source record")
            seen.add(identity)
            if table == FEES:
                amount = float(row["tuition_fee_nzd"])
                if not math.isfinite(amount) or amount < 0:
                    raise ValueError("tuition_fee_nzd must be finite and non-negative")
                row["tuition_fee_nzd"] = amount
                if not re.fullmatch(r"[0-9]{4}", row["fee_year"]):
                    raise ValueError("fee_year must use YYYY")
            flags = list(warn_if_needed(table, row))
            warnings.extend((table, n, flag) for flag in flags)
            records.append((n, *row.values(), ", ".join(flags)))
        except ValueError as exc:
            raise ValueError(f"{table}.csv, line {n}: {exc}") from exc
    if not records:
        raise ValueError(f"{table}.csv has no data rows")
    return records, warnings


def rebuild(data_dir=DATA, db_path=DB):
    """Validate bytes before taking a write lock. Replace only owned tables in one commit."""
    tables, findings, inputs = {}, [], []
    provider_names = {}
    for table in FIELDS:
        contents = (Path(data_dir) / f"{table}.csv").read_bytes()
        rows, flags = parse_file(table, contents)
        for line, provider_id, provider_name, *_ in rows:
            if provider_names.setdefault(provider_id, provider_name) != provider_name:
                raise ValueError(
                    f"{table}.csv, line {line}: inconsistent name for provider {provider_id}"
                )
        tables[table] = rows
        findings.extend(flags)
        inputs.append((table, len(rows), hashlib.sha256(contents).hexdigest()))
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path, timeout=30)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for table, fields in FIELDS.items():
            db.execute(f'DROP TABLE IF EXISTS "{table}"')
            columns = [
                f'"{f}" {"REAL" if f == "tuition_fee_nzd" else "TEXT"} NOT NULL'
                for f in fields
            ]
            definition = ", ".join(
                [
                    "source_line INTEGER PRIMARY KEY",
                    *columns,
                    "quality_flags TEXT NOT NULL",
                ]
            )
            db.execute(f'CREATE TABLE "{table}" ({definition})')
            placeholders = ", ".join("?" for _ in range(len(fields) + 2))
            db.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})', tables[table]
            )
            db.execute(f"CREATE INDEX {table}_provider ON {table}(provider_id)")
        for table in ("catalogue_sources", "catalogue_issues", "catalogue_release"):
            db.execute(f'DROP TABLE IF EXISTS "{table}"')
        db.execute(
            "CREATE TABLE catalogue_sources (dataset TEXT PRIMARY KEY, row_count INTEGER, sha256 TEXT)"
        )
        db.executemany("INSERT INTO catalogue_sources VALUES (?, ?, ?)", inputs)
        db.execute(
            "CREATE TABLE catalogue_issues (dataset TEXT, source_line INTEGER, issue TEXT)"
        )
        db.executemany("INSERT INTO catalogue_issues VALUES (?, ?, ?)", findings)
        db.execute("CREATE TABLE catalogue_release (version INTEGER, loaded_at TEXT)")
        db.execute(
            "INSERT INTO catalogue_release VALUES (?, ?)",
            (VERSION, datetime.now(timezone.utc).isoformat()),
        )
    return dict((name, count) for name, count, _ in inputs)


def open_reader(path=DB):
    db = sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=30
    )
    db.row_factory = sqlite3.Row
    db.create_function("fold", 1, normalized, deterministic=True)
    return db


def ensure_database(path=DB, data_dir=DATA):
    """First launch also migrates the earlier, programme-only generated DB."""
    if Path(path).exists():
        with closing(open_reader(path)) as db:
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='catalogue_release'"
            ).fetchone():
                version = db.execute(
                    "SELECT version FROM catalogue_release"
                ).fetchone()[0]
                if version == VERSION:
                    return
                raise ValueError(
                    f"Unsupported database version {version}. Run the snapshot import command."
                )
    rebuild(data_dir, path)
