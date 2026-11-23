import sqlite3
from pathlib import Path


DB_PATH = Path("local_db") / "nz_fee_portal.sqlite"


SQL = """
SELECT provider_name, programme_name, study_stage, subject_area
FROM programme_index
LIMIT 10;
"""


def main():
    if not DB_PATH.exists():
        print(f"Database file does not exist: {DB_PATH}")
        print("Please run: python scripts\\build_database.py")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(SQL).fetchall()

    print("SQL:")
    print(SQL.strip())
    print()
    print(f"Returned rows: {len(rows)}")
    print()

    for row in rows:
        print(dict(row))

    conn.close()


if __name__ == "__main__":
    main()