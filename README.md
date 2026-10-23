# Formula 1 group project

## Database setup and import

This branch uses the snake_case schema in `sql/schema.sql`. CSV headers remain unchanged; the importer explicitly maps them into that schema. Do not also run the camelCase `updated_schema.sql` from a different branch against the same database.

1. Install Python and PostgreSQL. Create a new, empty PostgreSQL database for this project.
2. Create a virtual environment and install the project dependencies:

```sh
python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows Command Prompt, instead:
# venv\Scripts\activate.bat
pip install -r dependencies.txt
```

3. Copy `.env.template` to `.env` and set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT to your PostgreSQL connection details. PostgreSQL commonly uses port 5432; use your actual port. Keep `.env` private. A Gemini key is not needed for database import.
4. The eight required CSVs are already in `f1_data/`. The status file is named `statuses.csv` on this branch, rather than Kaggle's original `status.csv`.
5. Run:

```sh
python main.py
```

Startup creates the schema, imports the eight tables, prints their counts, then calls the existing `main(connection)` function. Gemini and the three tool functions are still placeholders on the published branch. This change completes the database/import portion, not those application features.

To run only the importer:

```sh
python database_import.py
# Optional: another folder with the same eight filenames and headers:
python database_import.py --data-dir /path/to/f1_data
```

Paths for bundled data, SQL and `.env` are resolved relative to the Python files, so launching from a different working directory works.

## Calling from other project code

The existing entry points remain available:

```python
from main import connect_server, commit_schema, insert_data

connection = connect_server()
try:
    # insert_data also initializes the schema in the same transaction.
    # commit_schema(connection) remains available if needed separately.
    report = insert_data(connection)
    # Continue with the Gemini/tool loop using connection.
finally:
    connection.close()
```

Use an idle connection with autocommit disabled. If tool queries leave a transaction open, commit or roll it back before invoking the importer again.

## How import works

- Verifies original CSV header names/order and row widths before changing the database.
- COPY loads the complete source rows into temporary text tables. Unused CSV columns are omitted by explicit INSERT mappings in `sql/import_transform.sql`.
- Converts `\N` to SQL NULL. Elapsed race, pit-stop and lap durations come from milliseconds; fastest-lap minutes:seconds strings are converted explicitly. Clock times remain TIME values.
- Looks up each pit-stop/lap result_id using raceId and driverId. An absent or ambiguous match aborts the transaction.
- Removes the invalid UNIQUE (race_id, driver_id) definition: historical results contain multiple records for some driver/race pairs. Primary key result_id is retained.
- Uses a transaction and an import lock: a failure rolls back the entire import, and concurrent initializations are serialized.
- Stores source hashes/counts in a small `f1_import_metadata` bookkeeping table. Repeated startup skips duplicate imports after comparing the files and counts. This is additional to the eight application tables. It checks counts/hashes, not every existing database value.

An old schema or partially populated database is not silently deleted or migrated. Use a fresh project database. IF NOT EXISTS does not alter an existing definition. If existing tables still have the invalid unique constraint, remove that constraint explicitly or use the new database. Missing files, changed headers/data, invalid values, and unmatched result lookups fail with an error.

The other six CSVs in f1_data are not imported: they have no tables in the agreed eight-entity ER diagram. In particular, championship standings are not modeled. Agree on an ER extension if those tables are needed.

## Verification

Tests use real PostgreSQL and create/drop dedicated, randomly named databases; the admin connection needs CREATE DATABASE privilege. They do not use DB_NAME or change the project's database.

```sh
# macOS/Linux example:
F1_TEST_ADMIN_DSN='dbname=postgres user=YOUR_USER host=localhost' \
F1_TEST_DATA_DIR=f1_data \
python -m unittest discover -s tests -v
```

Tests verify the full source import, repeat startup, result lookups, millisecond conversions, representative win/lap queries, INSERT/UPDATE/DELETE, and rollback on an unmatched pit-stop row. The supplied dataset was tested on PostgreSQL 15.19. Gemini calls are not tested or implemented here.
