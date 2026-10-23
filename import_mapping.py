"""CSV-to-updated_schema.sql mapping, called by main.insert_data()."""
import csv
from pathlib import Path

from psycopg2 import sql

ROOT = Path(__file__).resolve().parent
# Exact source CSV headers/order, including columns omitted by the ER model.
COLUMNS = {'circuits': ['circuitId',
              'circuitRef',
              'name',
              'location',
              'country',
              'lat',
              'lng',
              'alt',
              'url'],
 'drivers': ['driverId',
             'driverRef',
             'number',
             'code',
             'forename',
             'surname',
             'dob',
             'nationality',
             'url'],
 'constructors': ['constructorId', 'constructorRef', 'name', 'nationality', 'url'],
 'statuses': ['statusId', 'status'],
 'races': ['raceId',
           'year',
           'round',
           'circuitId',
           'name',
           'date',
           'time',
           'url',
           'fp1_date',
           'fp1_time',
           'fp2_date',
           'fp2_time',
           'fp3_date',
           'fp3_time',
           'quali_date',
           'quali_time',
           'sprint_date',
           'sprint_time'],
 'results': ['resultId',
             'raceId',
             'driverId',
             'constructorId',
             'number',
             'grid',
             'position',
             'positionText',
             'positionOrder',
             'points',
             'laps',
             'time',
             'milliseconds',
             'fastestLap',
             'rank',
             'fastestLapTime',
             'fastestLapSpeed',
             'statusId'],
 'pit_stops': ['raceId', 'driverId', 'stop', 'lap', 'time', 'duration', 'milliseconds'],
 'lap_times': ['raceId', 'driverId', 'lap', 'position', 'time', 'milliseconds']}


def import_csv_data(connection, data_dir=None):
    """Import all eight tables atomically after commit_schema(connection).

    Requires an idle connection, autocommit disabled, and empty target tables.
    Already populated/partially populated tables are rejected without changing
    them. This is an initial-load function, not a general data synchronization.
    """
    if connection.autocommit or connection.get_transaction_status() != 0:
        raise ValueError("Use an idle connection with autocommit disabled")
    directory = Path(data_dir) if data_dir is not None else ROOT / "f1_data"
    source_counts = {}
    for table, header in COLUMNS.items():
        with (directory / (table + ".csv")).open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            if next(reader, None) != header:
                raise ValueError(f"{table}.csv: unexpected CSV headers or column order")
            count = 0
            for line, row in enumerate(reader, 2):
                if len(row) != len(header):
                    raise ValueError(f"{table}.csv line {line}: unexpected number of columns")
                count += 1
            source_counts[table] = count

    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(412, 43)")
            cursor.execute("SET LOCAL search_path TO public")
            for table in COLUMNS:
                cursor.execute(sql.SQL("SELECT EXISTS (SELECT 1 FROM {})").format(sql.Identifier(table)))
                if cursor.fetchone()[0]:
                    raise ValueError("Target tables already contain data. Skip this initial import or use a fresh database; no rows were changed.")
            for table, header in COLUMNS.items():
                cursor.execute(sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(
                    sql.Identifier("stage_" + table),
                    sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(column.lower()))
                                      for column in header)))
                statement = sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '\\N')").format(
                    sql.Identifier("stage_" + table))
                with (directory / (table + ".csv")).open(newline="", encoding="utf-8-sig") as stream:
                    cursor.copy_expert(statement.as_string(cursor), stream)
            cursor.execute((ROOT / "sql" / "import_mapping.sql").read_text(encoding="utf-8"))
            for table, expected in source_counts.items():
                cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                if cursor.fetchone()[0] != expected:
                    raise ValueError(f"{table}: imported count differs from CSV; import rolled back")
    return source_counts
