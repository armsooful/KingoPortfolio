#!/usr/bin/env python
"""
SQLite migration for Phase 7 result_hash.

- Adds result_hash column to phase7_evaluation_run if missing
- Backfills result_hash = sha256(result_json)
"""

import argparse
import hashlib
import os
import sqlite3


def ensure_column(conn: sqlite3.Connection) -> None:
    cursor = conn.execute("PRAGMA table_info(phase7_evaluation_run)")
    columns = {row[1] for row in cursor.fetchall()}
    if "result_hash" not in columns:
        conn.execute("ALTER TABLE phase7_evaluation_run ADD COLUMN result_hash TEXT")


def backfill_hashes(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        "SELECT evaluation_id, result_json FROM phase7_evaluation_run "
        "WHERE result_hash IS NULL OR result_hash = ''"
    ).fetchall()
    updated = 0
    for evaluation_id, result_json in rows:
        if result_json is None:
            continue
        result_hash = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
        conn.execute(
            "UPDATE phase7_evaluation_run SET result_hash = ? WHERE evaluation_id = ?",
            (result_hash, evaluation_id),
        )
        updated += 1
    return updated


def resolve_db_path(db_path: str | None) -> str:
    if db_path:
        return db_path
    default_path = os.path.join(os.path.dirname(__file__), "..", "kingo.db")
    return os.path.abspath(default_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Phase 7 result_hash in SQLite.")
    parser.add_argument("--db", dest="db_path", help="SQLite DB file path")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db_path)
    conn = sqlite3.connect(db_path)
    try:
        ensure_column(conn)
        updated = backfill_hashes(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"result_hash updated: {updated}")


if __name__ == "__main__":
    main()
