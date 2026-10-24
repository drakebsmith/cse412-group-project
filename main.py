# Imports will likely need modification since we'll need to interface with the PostgreSQL server and Kaggle
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Globally loads the local .env file
load_dotenv()

# Establishes connection with local PostgreSQL server via handshake, returns connection object 
def connect_server():
    try:
        connection = psycopg2.connect(
            dbname = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD"),
            host = os.getenv("DB_HOST"),
            port = os.getenv("DB_PORT")
        )  
        return connection
    
    except Exception as connection_error:
        print(f"Error: connection to PostgreSQL server could not be established due to {connection_error}")
        sys.exit(1) # Only utilize for errors that should terminate the program!

# Commits the dataset's schema to the database
def commit_schema(connection):
    with connection.cursor() as cursor:
        try:
            with open("sql/updated_schema.sql", "r", encoding = "utf-8") as file:
                script = file.read()
            cursor.execute(script)
            connection.commit()

        except Exception as cursor_error:
            print(f"Error: contents of updated_schema.sql could not be read due to {cursor_error}")
            sys.exit(1)

# Initial load only: schema must exist and all eight target tables must be empty.
def insert_data(connection):
    from import_mapping import import_csv_data

    counts = import_csv_data(connection)
    print(f"Imported CSV rows: {counts}")
    return counts

def get_database_schema() -> str:
    
    '''
        Input: list of table names (optional)

        Output: table names, columns, datatypes, primary keys, foreign keys,
        and descriptions of important fields

        Database interactions: PostgreSQL schema metadata and field descriptions
    '''

    connection = connect_server()

    field_descriptions = {
        # Circuits
        "circuits.circuitid": "Id",
        "circuits.circuitref": "Reference name of circuit",
        "circuits.name": "Actual name of circuit",
        "circuits.location": "City",
        "circuits.country": "Country",

        # Drivers
        "drivers.driverid": "Id",
        "drivers.driverref": "Reference name of driver",
        "drivers.number": "Driver number",
        "drivers.code": "3-letter alphabet code of driver",
        "drivers.forename": "First name",
        "drivers.surname": "Last name",
        "drivers.dob": "Date of birth",
        "drivers.nationality": "Country",

        # Constructors
        "constructors.constructorid": "Id",
        "constructors.constructorref": "Reference name of constructor",
        "constructors.name": "Actual name of constructor",
        "constructors.nationality": "Country",

        # Statuses
        "statuses.statusid": "Id",
        "statuses.status": "Name",

        # Races
        "races.raceid": "Id of race",
        "races.year": "Year",
        "races.round": "Race number",
        "races.circuitid": "Id of circuit",
        "races.name": "Name of race",
        "races.date": "Date",
        "races.time": "Time",

        # Results
        "results.resultid": "Id",
        "results.raceid": "Id of race",
        "results.driverid": "Id of driver",
        "results.constructorid": "Id of constructor",
        "results.statusid": "Id of result status",
        "results.number": "Car number",
        "results.grid": "Position in starting grid",
        "results.positionorder": "Final rank",
        "results.points": "Points",
        "results.laps": "Number of laps completed",
        "results.time": "Total elapsed race time",
        "results.fastestlaptime": "Fastest lap time recorded by the driver",
        "results.fastestlapspeed": "Speed recorded during the driver's fastest lap",

        # Pit Stops
        "pit_stops.resultid": "Id of the corresponding race result",
        "pit_stops.stop": "Stop number",
        "pit_stops.lap": "Lap number",
        "pit_stops.time": "Time of pit stop",
        "pit_stops.duration": "Duration of pit stop",

        # Lap Times
        "lap_times.resultid": "Id of the corresponding race result",
        "lap_times.lap": "Lap number",
        "lap_times.position": "Driver position on that lap",
        "lap_times.time": "Time"
    }

    try:
        connection.set_session(readonly=True)

        with connection.cursor() as cursor:

            # Get columns and datatypes
            cursor.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            columns = cursor.fetchall()

            # Get primary keys
            cursor.execute("""
                SELECT
                    c.relname,
                    a.attname
                FROM pg_constraint p
                JOIN pg_class c
                    ON c.oid = p.conrelid
                JOIN pg_namespace n
                    ON n.oid = c.relnamespace
                JOIN unnest(p.conkey) AS k(attnum)
                    ON TRUE
                JOIN pg_attribute a
                    ON a.attrelid = c.oid
                    AND a.attnum = k.attnum
                WHERE p.contype = 'p'
                    AND n.nspname = 'public';
            """)
            primary_keys = set(cursor.fetchall())

            # Get foreign keys
            cursor.execute("""
                SELECT
                    source.relname,
                    source_col.attname,
                    target.relname,
                    target_col.attname
                FROM pg_constraint p
                JOIN pg_class source
                    ON source.oid = p.conrelid
                JOIN pg_class target
                    ON target.oid = p.confrelid
                JOIN pg_namespace n
                    ON n.oid = source.relnamespace
                JOIN unnest(p.conkey) WITH ORDINALITY
                    AS source_key(attnum, pos)
                    ON TRUE
                JOIN unnest(p.confkey) WITH ORDINALITY
                    AS target_key(attnum, pos)
                    ON source_key.pos = target_key.pos
                JOIN pg_attribute source_col
                    ON source_col.attrelid = source.oid
                    AND source_col.attnum = source_key.attnum
                JOIN pg_attribute target_col
                    ON target_col.attrelid = target.oid
                    AND target_col.attnum = target_key.attnum
                WHERE p.contype = 'f'
                    AND n.nspname = 'public';
            """)
            foreign_keys = {
                (table, column): (foreign_table, foreign_column)
                for table, column, foreign_table, foreign_column
                in cursor.fetchall()
            }

       
            if not columns:
                return "No matching tables were found"

            schema_info = []
            current_table = None

            for table_name, column_name, data_type in columns:
                if table_name != current_table:
                    schema_info.append(f"\nTable: {table_name}")
                    current_table = table_name

                column_info = f"  - {column_name} ({data_type})"

                if (table_name, column_name) in primary_keys:
                    column_info += " [PRIMARY KEY]"

                if (table_name, column_name) in foreign_keys:
                    foreign_table, foreign_column = foreign_keys[
                        (table_name, column_name)
                    ]

                    column_info += (
                        f" [FOREIGN KEY -> "
                        f"{foreign_table}({foreign_column})]"
                    )

                description = field_descriptions.get(
                    f"{table_name}.{column_name}"
                )

                if description:
                    column_info += f" | Description: {description}"

                schema_info.append(column_info)

            return "\n".join(schema_info)

    except Exception as schema_error:
        return f"Error reading schema: {str(schema_error)}"

    finally:
        connection.close()

def execute_query(sql_query: str):
    # Function that Gemini will call to execute a user's natural language query as a SQL query
    
    '''
        Input: SQL query crafted by Gemini
    
        Output: column names, result rows, the number of returned rows, and any errors with the query
    
        Database interactions: read-only SQL queries against the PostgreSQL database; should support filtering, joins, grouping and aggregate functions like COUNT(), SUM(), and AVG()
    '''
    print(f"[TOOL] execute_query called with: {sql_query}")
    # Opens a connection to the local PostgreSQL database 
    connection = connect_server()
    try:
        query = sql_query.strip().lower()
        # Prevents Gemini from executing any queries that modify the database
        if not (query.startswith("select") or query.startswith("with")):
            return {
                "columns" : [],
                "rows" : [],
                "row_count" : 0,
                "error" : "Only read-only SELECT queries are allowed."
            }

        connection.set_session(readonly = True)

        with connection.cursor() as cursor:
            cursor.execute(sql_query)

            if cursor.description is None:
                return {
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "error": None
                }

            columns = [column[0] for column in cursor.description]
            results = cursor.fetchmany(50)
            return {
                "columns": columns,
                "rows": results,
                "row_count": len(results),
                "error": None
            }

    except Exception as query_error:
        # Returns an error message if the SQL query fails to execute
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": str(query_error)
        }

    finally:
        connection.close()

def get_data_coverage():
    # TODO: Function that Gemini will call to check whether the given tables contains the records needed for the user's natural language query

    '''
        Input: relevant table names and, optionally, a season year
    
        Output: available year ranges, record counts for the requested season, and missing-value counts for relevant fields
    
        Database interactions: predefined summary SQL queries against the PostgreSQL database, joining specific tables to determine season coverage.
    '''

def main():
    personal_key = os.getenv("GEMINI_API_KEY")

    # This if statement might be redundant given the try-except in connect_server()
    if not personal_key:
        print("Error: invalid or unset API key")
        sys.exit(1)

    client = genai.Client(api_key = personal_key)

    # Context for Gemini
    instructions = (
        "You are experienced in SQL and are assisting with the interfacing of a local PostgreSQL database containing Formula 1 World Championships data from 1950 to 2024."
        "When the user asks a question, retrieve the database's schema from get_database_schema(), "
        "call get_data_coverage() to verify which tables will have the information pertaining to the query, "
        "translate the question into a SQL query, and execute the query using execute_query(). "
        "Return the results in natural language to the user."
    )

    # Gemini object that the user engages with
    agent = client.chats.create(
        # model = "gemini-3.8-flash", # This model seems to always be in high demand, we'll need to pick a fitting model for this project
        model = "gemini-3.5-flash-lite",
        config = types.GenerateContentConfig(
            system_instruction = instructions, # Provides Gemini with the instructions above
            tools = [get_database_schema, execute_query, get_data_coverage], # Informs Gemini that these functions are tools it can use
            temperature = 0.0 # Ensures that Gemini doesn't diverge from the user's prompt. The lower the value, the less divergence.
        )
    )

    print("\nWelcome to the Gemini-assisted Formula 1 World Championships (1950-2024) database server! Ask away!")
    print("\nNote: enter \"exit\" to quit the program")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                print("Error: empty input, please try again")
            if user_input == "exit":
                break
            response = agent.send_message(user_input)
            print(f"\nGemini: {response.text}")

        except Exception as user_input_error:
            print(f"Error: {user_input_error}")
            sys.exit(1)

# This section should be used for initializing the database server.
# Some of these functions might be moved to a separate Python file
# since some only need to be run once
if __name__ == "__main__":
    connection = connect_server()
    # commit_schema(connection) # Uncomment once schema.sql is updated accordingly. This is to prevent duplicate table creation!
    # insert_data(connection)
    main()