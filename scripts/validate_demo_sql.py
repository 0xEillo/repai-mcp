"""Spin up an ephemeral Postgres, apply demo-schema + seed, assert results.

Run: uv run --with pgserver --with psycopg[binary] python scripts/validate_demo_sql.py
Not part of the package; a developer validation aid for the demo SQL files.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pgserver
import psycopg

ROOT = Path(__file__).resolve().parent.parent
# pgserver's bundled Postgres ships without the pgcrypto contrib module.
# gen_random_uuid() is core since PG13, so the extension line is only defensive
# for Supabase; drop it for this local validation run.
SCHEMA = (ROOT / "supabase" / "demo-schema.sql").read_text().replace(
    "create extension if not exists pgcrypto;", ""
)
SEED = (ROOT / "supabase" / "seed-demo.sql").read_text()


def apply_seed_and_count(conn: psycopg.Connection) -> dict[str, int]:
    conn.execute(SCHEMA)
    conn.execute(SEED)
    # Idempotency: run seed twice, expect identical counts.
    conn.execute(SEED)
    checks = {
        "profiles": "select count(*) from profiles",
        "workout_sessions": "select count(*) from workout_sessions",
        "sets": "select count(*) from sets",
        "stuck": "select count(*) from workout_sessions where is_processing",
        "coach_msgs": "select count(*) from proactive_coach_messages",
        "coach_consumed": "select count(*) from proactive_coach_messages where consumed_at is not null",
        "ai_chat": "select count(*) from ai_chat_usage",
        "emails": "select count(*) from email_automation_events",
        "trial_users": "select count(*) from profiles where trial_start_date is not null",
    }
    return {name: conn.execute(sql).fetchone()[0] for name, sql in checks.items()}


def create_partial_existing_schema(conn: psycopg.Connection) -> None:
    """Simulate a Supabase project where some demo tables already existed."""
    conn.execute("create table profiles (id uuid primary key);")
    conn.execute("create table exercises (id uuid primary key);")
    conn.execute("create table workout_sessions (id uuid primary key);")


def main() -> int:
    with tempfile.TemporaryDirectory() as pgdata:
        db = pgserver.get_server(Path(pgdata))
        try:
            db.psql("CREATE DATABASE demo;")
            uri = db.get_uri(database="demo")
            with psycopg.connect(uri, autocommit=True) as conn:
                results = apply_seed_and_count(conn)

            db.psql("CREATE DATABASE partial_demo;")
            partial_uri = db.get_uri(database="partial_demo")
            with psycopg.connect(partial_uri, autocommit=True) as conn:
                create_partial_existing_schema(conn)
                partial_results = apply_seed_and_count(conn)
        finally:
            db.cleanup()

    print("Demo SQL validation results:")
    for name, value in results.items():
        print(f"  {name:16} = {value}")
    print("Partial-schema validation results:")
    for name, value in partial_results.items():
        print(f"  {name:16} = {value}")

    expectations = {
        "profiles": 25,
        "stuck": 2,
        "trial_users": 3,
    }
    ok = True
    for name, expected in expectations.items():
        if results[name] != expected:
            print(f"FAIL: {name} expected {expected}, got {results[name]}")
            ok = False
        if partial_results[name] != expected:
            print(
                f"FAIL: partial {name} expected {expected}, "
                f"got {partial_results[name]}"
            )
            ok = False
    if results["coach_consumed"] == 0 or results["coach_msgs"] == 0:
        print("FAIL: expected some coach messages, consumed and unconsumed")
        ok = False
    if results["sets"] == 0 or results["workout_sessions"] == 0:
        print("FAIL: expected workouts and sets")
        ok = False

    print("OK" if ok else "VALIDATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
