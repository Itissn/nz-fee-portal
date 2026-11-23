from contextlib import closing

from scripts.data_quality_report import markdown_report
from src.catalogue import open_reader, rebuild


def test_report_agrees_with_the_saved_release(tmp_path):
    target = tmp_path / "catalogue.db"
    rebuild(db_path=target)
    with closing(open_reader(target)) as db:
        report = markdown_report(db)
        for table, count, digest in db.execute("SELECT * FROM catalogue_sources"):
            assert f"| {table} | {count} |" in report
            assert digest in report
        assert "| programme_index | unknown_subject |" in report
