import sqlite3
import sys

from pathlib import Path
from datetime import datetime

from psycopg import sql

# Add the AEGIS project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.memory.postgres_backend import get_connection


SQLITE_PATH = Path("data/aegis.db").resolve()

TABLES = [
    "conversations",
    "conversation_messages",
    "feedback",
    "benchmark_results",
    "research_experiments",
    "research_case_results",
    "research_trial_results",
]

EXPECTED_COUNTS = {
    "benchmark_results": 3,
    "conversation_messages": 53,
    "conversations": 13,
    "feedback": 18,
    "research_case_results": 10,
    "research_experiments": 1,
    "research_trial_results": 90,
}

BOOLEAN_COLUMNS = {
    "benchmark_results": ["correct"],
    "research_trial_results": [
        "is_warmup",
        "execution_success",
        "is_correct",
    ],
}


def convert_value(table, column, value, pg_types):
    if value is None:
        return None

    if column in BOOLEAN_COLUMNS.get(table, []):
        if value not in (0, 1):
            raise ValueError(
                f"Unexpected boolean value: {table}.{column}={value}"
            )
        return bool(value)

    if pg_types.get(column) == "timestamp without time zone":
        if isinstance(value, str):
            return datetime.fromisoformat(value)

    return value


def load_sqlite_data():
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(SQLITE_PATH)

    uri = f"file:{SQLITE_PATH.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row

    data = {}
    columns = {}

    try:
        print("Reading original SQLite database (READ ONLY)...")

        for table in TABLES:
            rows = connection.execute(
                f'SELECT * FROM "{table}"'
            ).fetchall()

            expected = EXPECTED_COUNTS[table]

            if len(rows) != expected:
                raise RuntimeError(
                    f"{table}: expected {expected}, "
                    f"found {len(rows)}. Migration stopped."
                )

            data[table] = rows

            columns[table] = [
                column[1]
                for column in connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            ]

            print(f"  {table}: {len(rows)} records loaded")

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                "SQLite foreign-key violations detected."
            )

        return data, columns

    finally:
        connection.close()


def main():
    data, source_columns = load_sqlite_data()

    print("\nChecking PostgreSQL target...")

    with get_connection() as connection:

        pg_types = {}

        for table in TABLES:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            if count != 0:
                raise RuntimeError(
                    f"PostgreSQL table {table} is not empty. "
                    "Migration stopped."
                )

            columns = connection.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                """,
                (table,),
            ).fetchall()

            pg_types[table] = {
                column[0]: column[1]
                for column in columns
            }

            if set(source_columns[table]) != set(pg_types[table]):
                raise RuntimeError(
                    f"Column mismatch in {table}."
                )

        print("All seven PostgreSQL tables are empty.")

        print("\nStarting migration transaction...")

        # Any exception inside this block causes rollback.
        with connection.transaction():

            with connection.cursor() as cursor:

                # Insert records in foreign-key dependency order.
                for table in TABLES:
                    columns = source_columns[table]

                    query = sql.SQL(
                        "INSERT INTO {} ({}) VALUES ({})"
                    ).format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(
                            sql.Identifier(column)
                            for column in columns
                        ),
                        sql.SQL(", ").join(
                            sql.Placeholder()
                            for _ in columns
                        ),
                    )

                    records = []

                    for row in data[table]:
                        records.append(
                            tuple(
                                convert_value(
                                    table,
                                    column,
                                    row[column],
                                    pg_types[table],
                                )
                                for column in columns
                            )
                        )

                    if records:
                        cursor.executemany(query, records)

                    print(
                        f"  Migrated {table}: {len(records)} records"
                    )

                # Reset only genuine PostgreSQL identity sequences.
                print("\nResetting identity sequences...")

                for table in TABLES:
                    identity = cursor.execute(
                        """
                        SELECT is_identity
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = %s
                          AND column_name = 'id'
                        """,
                        (table,),
                    ).fetchone()

                    if not identity or identity[0] != "YES":
                        print(f"  Skipped: {table}")
                        continue

                    max_id = max(
                        (row["id"] for row in data[table]),
                        default=0,
                    )

                    if max_id:
                        cursor.execute(
                            """
                            SELECT setval(
                                pg_get_serial_sequence(
                                    %s, 'id'
                                )::regclass,
                                %s,
                                true
                            )
                            """,
                            (f"public.{table}", max_id),
                        )

                        print(
                            f"  {table}: sequence set to {max_id}"
                        )

                # Verify every count before committing.
                print("\nVerifying migrated record counts...")

                for table in TABLES:
                    actual = cursor.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(
                            sql.Identifier(table)
                        )
                    ).fetchone()[0]

                    expected = EXPECTED_COUNTS[table]

                    if actual != expected:
                        raise RuntimeError(
                            f"{table}: expected {expected}, "
                            f"found {actual}"
                        )

                    print(f"  {table}: {actual}/{expected} verified")

        print("\nPostgreSQL transaction committed.")

    print("\n========== MIGRATION SUMMARY ==========")
    print("SQLite source records: 188")
    print("PostgreSQL migrated records: 188")
    print("Tables migrated: 7")
    print("Original SQLite database modified: NO")
    print("Transaction: COMMITTED")
    print("MIGRATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
