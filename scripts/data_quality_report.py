"""Write a reproducible Markdown audit of the same release the web portal uses."""

import argparse
from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.catalogue import DB, FIELDS, open_reader


def markdown_report(db):
    lines = [
        "# Snapshot quality report",
        "",
        "The three input files are identified by SHA-256. Dates are recorded provider checks.",
        "",
        "| Dataset | Rows | Providers | First check | Last check |",
        "|---|---:|---:|---|---|",
    ]
    for table in FIELDS:
        summary = db.execute(
            f"""SELECT COUNT(*), COUNT(DISTINCT provider_id),
                               MIN(last_checked), MAX(last_checked) FROM {table}"""
        ).fetchone()
        lines.append(f"| {table} | " + " | ".join(map(str, summary)) + " |")
    matched = db.execute(
        """SELECT COUNT(*) FROM programme_index p WHERE EXISTS (
        SELECT 1 FROM fee_snapshot f WHERE p.provider_id=f.provider_id
        AND fold(p.programme_name)=fold(f.programme_name) AND instr(f.quality_flags,'numeric_programme_name')=0)"""
    ).fetchone()[0]
    lines += [
        "",
        f"{matched:,} programme records have an exact provider-and-name fee match before cohort filters.",
        "A name match can cover multiple fee bases, majors or student groups.",
        "",
        "| Dataset | Quality finding | Affected rows |",
        "|---|---|---:|",
    ]
    for table, issue, count in db.execute(
        """SELECT dataset, issue, COUNT(*) FROM catalogue_issues
                                            GROUP BY dataset, issue ORDER BY dataset, issue"""
    ):
        lines.append(f"| {table} | {issue} | {count:,} |")
    lines += [
        "",
        "A record can have several findings. The Data quality tab lists individual CSV line numbers.",
        "",
        "| Source CSV | SHA-256 |",
        "|---|---|",
    ]
    for table, sha in db.execute(
        "SELECT dataset, sha256 FROM catalogue_sources ORDER BY dataset"
    ):
        lines.append(f"| {table}.csv | `{sha}` |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DB)
    parser.add_argument(
        "--report-path", type=Path, default=ROOT / "reports" / "data_quality_report.md"
    )
    args = parser.parse_args()
    with closing(open_reader(args.db_path)) as db:
        db.execute("BEGIN")
        report = markdown_report(db)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print("Wrote the snapshot quality report.")


if __name__ == "__main__":
    main()
