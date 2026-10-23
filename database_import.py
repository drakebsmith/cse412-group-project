"""Transactional Kaggle CSV import usable from the app or as a standalone CLI."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
COLUMNS = json.loads((ROOT / 'csv_columns.json').read_text())
TARGETS = {name: 'statuses' if name == 'status' else name for name in COLUMNS}


def connect_database():
    """Use the project's existing DB_* environment variables; no Gemini key needed."""
    load_dotenv(ROOT / '.env')
    return psycopg2.connect(**{
        key: value for key, value in {
            'dbname': os.getenv('DB_NAME'), 'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'), 'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', '5432'),
        }.items() if value
    })


def _inspect_files(directory):
    inspected = {}
    for name, expected in COLUMNS.items():
        path = directory / (('statuses' if name == 'status' else name) + '.csv')
        with path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.reader(stream)
            if next(reader, None) != expected:
                raise ValueError(f'{path.name}: CSV header/order does not match csv_columns.json')
            count = 0
            for line, row in enumerate(reader, 2):
                if len(row) != len(expected):
                    raise ValueError(f'{path.name}:{line}: wrong number of fields')
                count += 1
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        inspected[name] = (path, count, digest)
    return inspected


def _execute_schema(cursor):
    schema = (ROOT / 'sql' / 'schema.sql').read_text()
    schema = '\n'.join(line for line in schema.splitlines()
                       if line.strip().upper() not in ('BEGIN;', 'COMMIT;'))
    cursor.execute(schema)


def initialize_schema(connection):
    """Compatibility entry point for commit_schema(connection)."""
    if connection.autocommit or connection.get_transaction_status() != 0:
        raise ValueError('Use an idle connection with autocommit disabled')
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(412, 43)')
            cursor.execute('SET LOCAL search_path TO public')
            _execute_schema(cursor)


def import_dataset(connection, data_dir=None):
    """Initialize schema and import all eight CSVs atomically.

    Pass a dedicated, idle psycopg2 connection with autocommit disabled. On success
    the transaction commits; on failure schema/data changes roll back. Repeated
    startup with identical CSVs skips COPY after checking saved counts/digests.
    A populated database not created by this importer is rejected, never erased.
    """
    if connection.autocommit or connection.get_transaction_status() != 0:
        raise ValueError('Use an idle connection with autocommit disabled')
    directory = Path(data_dir) if data_dir is not None else ROOT / 'f1_data'
    inspected = _inspect_files(directory.resolve())
    with connection:
        with connection.cursor() as cur:
            cur.execute('SELECT pg_advisory_xact_lock(412, 43)')
            cur.execute('SET LOCAL search_path TO public')
            _execute_schema(cur)
            # Reject incompatible existing tables or the old UNIQUE constraint.
            cur.execute("SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name='results'")
            columns = {row[0] for row in cur.fetchall()}
            if not {'result_id', 'race_id', 'driver_id', 'fastest_lap_time'} <= columns:
                raise ValueError('Existing schema is incompatible; use a fresh database with schema.sql')
            cur.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE conrelid='public.results'::regclass AND contype='u'")
            if any(definition.replace(' ', '').lower() in
                   ('unique(race_id,driver_id)', 'unique(driver_id,race_id)')
                   for (definition,) in cur.fetchall()):
                raise ValueError('Remove the old results race_id/driver_id UNIQUE constraint before importing')
            cur.execute('''CREATE TABLE IF NOT EXISTS f1_import_metadata (
                source_name TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
                row_count BIGINT NOT NULL, imported_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
            cur.execute('SELECT source_name, sha256, row_count FROM f1_import_metadata')
            saved = {name: (digest, count) for name, digest, count in cur.fetchall()}
            counts = {}
            for source, target in TARGETS.items():
                cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(target)))
                counts[source] = cur.fetchone()[0]
            if saved:
                if set(saved) != set(inspected) or any(
                    saved[name] != (digest, count) or counts[name] != count
                    for name, (_, count, digest) in inspected.items()
                ):
                    raise ValueError('CSV files or imported row counts changed; use a fresh database to reload')
                return {'skipped': True, 'counts': {TARGETS[n]: c for n, c in counts.items()}}
            if any(counts.values()):
                raise ValueError('Target tables already contain data without import metadata; use a fresh database')
            for name, expected in COLUMNS.items():
                cur.execute(sql.SQL('CREATE TEMP TABLE {} ({}) ON COMMIT DROP').format(
                    sql.Identifier('stage_' + name),
                    sql.SQL(', ').join(sql.SQL('{} TEXT').format(sql.Identifier(c.lower()))
                                      for c in expected)))
                copy = sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '\\N')").format(
                    sql.Identifier('stage_' + name))
                with inspected[name][0].open(encoding='utf-8-sig', newline='') as stream:
                    cur.copy_expert(copy.as_string(cur), stream)
            cur.execute((ROOT / 'sql' / 'import_transform.sql').read_text())
            for name, (_, count, digest) in inspected.items():
                cur.execute('INSERT INTO f1_import_metadata (source_name, sha256, row_count) VALUES (%s,%s,%s)',
                            (name, digest, count))
    return {'skipped': False, 'counts': {TARGETS[n]: item[1] for n, item in inspected.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'f1_data')
    args = parser.parse_args()
    connection = connect_database()
    try:
        print(json.dumps(import_dataset(connection, args.data_dir), indent=2))
    finally:
        connection.close()


if __name__ == '__main__':
    main()
