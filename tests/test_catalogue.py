import csv
import shutil
import sqlite3
from contextlib import closing

import pytest
from src.catalogue import DATA, ensure_database, open_reader, rebuild
from src.search import Filters, query


@pytest.fixture
def release(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA, data)
    path = tmp_path / "test.sqlite"
    rebuild(data, path)
    return data, path


def edit_csv(path, modify):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames
    modify(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, headers)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize(
    ("dataset", "change", "cause"),
    [
        ("fee_snapshot", lambda rows: rows[0].update(tuition_fee_nzd="NaN"), "finite"),
        ("fee_source_index", lambda rows: rows.append(rows[0]), "duplicate"),
        (
            "programme_index",
            lambda rows: rows[0].update(last_checked="2026-02-31"),
            "day",
        ),
        (
            "programme_index",
            lambda rows: rows[0].update(programme_link=""),
            "invalid programme_link",
        ),
    ],
)
def test_bad_snapshot_preserves_old_release(release, dataset, change, cause):
    data, path = release
    with closing(open_reader(path)) as db:
        before = [tuple(r) for r in db.execute("SELECT * FROM catalogue_sources")]
    edit_csv(data / (dataset + ".csv"), change)
    with pytest.raises(ValueError, match=cause):
        rebuild(data, path)
    with closing(open_reader(path)) as db:
        assert before == [
            tuple(r) for r in db.execute("SELECT * FROM catalogue_sources")
        ]
        assert (
            db.execute("SELECT COUNT(*) FROM fee_snapshot").fetchone()[0]
            == before[2][1]
        )


def test_database_error_rolls_back_all_ddl(release):
    _, path = release
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("ALTER TABLE catalogue_release RENAME TO held")
        db.execute("CREATE VIEW catalogue_release AS SELECT * FROM held")
        db.execute(
            "UPDATE programme_index SET subject_area='last published value' WHERE source_line=2"
        )
    with pytest.raises(sqlite3.OperationalError):
        rebuild(db_path=path)
    with closing(open_reader(path)) as db:
        assert (
            db.execute(
                "SELECT subject_area FROM programme_index WHERE source_line=2"
            ).fetchone()[0]
            == "last published value"
        )


def test_refresh_replaces_old_values_without_destroying_other_tables(release):
    data, path = release
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE analyst_notes (note)")

    def change(rows):
        rows[0]["programme_name"] = "New fieldwork course"
        rows[0]["subject_area"] = "Unknown"

    edit_csv(data / "programme_index.csv", change)
    counts = rebuild(data, path)
    rebuild(data, path)
    with closing(open_reader(path)) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM programme_index").fetchone()[0]
            == counts["programme_index"]
        )
        assert (
            len(query(db, "programmes", Filters(keyword="New fieldwork course"))) == 1
        )
        assert db.execute("SELECT COUNT(*) FROM analyst_notes").fetchone()[0] == 0
        assert (
            db.execute(
                "SELECT COUNT(*) FROM catalogue_issues WHERE dataset='programme_index' AND source_line=2 AND issue='unknown_subject'"
            ).fetchone()[0]
            == 1
        )


def test_legacy_programme_only_db_migrates_on_launch(tmp_path):
    path = tmp_path / "old.sqlite"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE programme_index (programme_name)")
    ensure_database(path)
    with closing(open_reader(path)) as db:
        assert db.execute("SELECT COUNT(*) FROM catalogue_sources").fetchone()[0] == 3


def test_trace_from_query_to_fee_and_source_fallback(release):
    _, path = release
    with closing(open_reader(path)) as db:
        filters = Filters(
            keyword="agriculture",
            provider="Lincoln University",
            student="Domestic",
            year="2026",
        )
        result = query(db, "programmes", filters)
        selected = result[result.programme_name == "Bachelor of Agriculture"].iloc[0]
        fees = query(
            db, "fees", filters, (selected.provider_id, selected.programme_name)
        )
        assert fees[
            ["tuition_fee_nzd", "fee_basis", "last_checked"]
        ].values.tolist() == [[8690, "per 120 points", "2026-05-14"]]
        assert fees.source_link.iloc[0].startswith("https://www.lincoln.ac.nz/")
        unmatched = (selected.provider_id, "An unlisted programme")
        assert query(db, "fees", Filters(), unmatched).empty
        assert not query(db, "sources", Filters(), unmatched).empty
        assert query(db, "programmes", Filters(keyword="%' OR 1=1 --")).empty


def test_cohort_filters_and_quality_report(release):
    _, path = release
    with closing(open_reader(path)) as db:
        known = query(db, "sources", Filters(year="2026", student="Domestic"))
        broad = query(
            db,
            "sources",
            Filters(year="2026", student="Domestic", include_unknown=True),
        )
        assert set(known.fee_year) <= {"2026", "2025;2026"}
        assert set(known.student_type) <= {"Domestic", "Both"}
        assert len(known) < len(broad)
        flagged = db.execute(
            "SELECT source_line FROM catalogue_issues WHERE issue='numeric_programme_name' LIMIT 1"
        ).fetchone()
        row = db.execute(
            "SELECT provider_id, programme_name FROM fee_snapshot WHERE source_line=?",
            tuple(flagged),
        ).fetchone()
        assert query(db, "fees", Filters(), row).empty
