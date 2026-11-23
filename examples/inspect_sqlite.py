import sqlite3
from pathlib import Path


DB_PATH = Path("local_db") / "nz_fee_portal.sqlite"


def main():
    if not DB_PATH.exists():
        print(f"Database file does not exist: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    print("Database:", DB_PATH)
    print()

    print("Tables:")
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    for table in tables:
        print("  ", table[0])

    print()

    table_name = "programme_index"

    print(f"Columns in {table_name}:")
    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    for column in columns:
        print(column)

    print()

    print(f"First 5 rows from {table_name}:")
    rows = conn.execute(
        f"SELECT * FROM {table_name} LIMIT 5"
    ).fetchall()

    for row in rows:
        print(row)

    conn.close()


if __name__ == "__main__":
    main()