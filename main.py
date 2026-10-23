# Imports will likely need modification since we'll need to interface with the PostgreSQL server and Kaggle
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Establishes connection with local PostgreSQL server via handshake, returns connection object 
def connect_server():
    load_dotenv()

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
            with open("sql/schema.sql", "r", encoding = "utf-8") as file:
                script = file.read()
            cursor.execute(script)
            connection.commit()

        except Exception as cursor_error:
            print(f"Error: contents of schema.sql could not be read due to {cursor_error}")
            sys.exit(1)

# Inserts the data from Kaggle into the database
def insert_data(connection):
    tables = [
        "circuits", "drivers",
        "constructors", "statuses",
        "races", "results",
        "pit_stops", "lap_times"
    ]

    table_columns = {
        "circuits" : "circuit_id, circuit_ref, name, location, country",
        "drivers" : "driver_id, driver_ref, number, code, forename, surname, dob, nationality",
        "constructors" : "constructor_id, constructor_ref, name, nationality",
        "statuses" : "status_id, status",
        "races" : "race_id, year, round, name, race_date, start_time, circuit_id",
        "results" : "result_id, race_id, driver_id, constructor_id, status_id, number, grid, ",
        "pit_stops" : "",
        "lap_times" : "raceId, driverId"
    }

    try:
        cursor = connection.cursor()
        #cursor.execute("""
        #    SELECT table_name FROM information_schema.tables
        #    WHERE table_schema = 'public';
        #""")
        # tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"""SELECT COUNT(*) FROM {table};""")
            contents = cursor.fetchone()[0]
            if contents > 0:
                print(f"{table} is empty!")
                return
            else:
                with open(f"f1_data/{table}.csv", "r", encoding = "utf-8") as file:
                    cursor.copy_expert(
                        f"""COPY {table} () FROM STDIN WITH CSV HEADER""",
                        file
                    )
                connection.commit()
                # print(f"{table_name} is filled!")

    except Exception as insert_error:
        print(f"Error: data could not be inserted due to {insert_error}")

def get_database_schema():
    # TODO: Function that Gemini will call to retrieve the tables, columns, and relationships of the database

    '''
        Input: list of table names (optional)

        Output: table names, columns, datatypes, primary keys, foreign keys, and descriptions of important fields

        Database interactions: PostgreSQL schema metadata and field descriptions
    '''

def execute_query():
    # TODO: Function that Gemini will call to execute a user's natural language query as a SQL query

    '''
        Input: SQL query crafted by Gemini
    
        Output: column names, result rows, the number of returned rows, and any errors with the query
    
        Database interactions: read-only SQL queries against the PostgreSQL database; should support filtering, joins, grouping and aggregate functions like COUNT(), SUM(), and AVG()
    '''

def get_data_coverage():
    # TODO: Function that Gemini will call to check whether the given tables contains the records needed for the user's natural language query

    '''
        Input: relevant table names and, optionally, a season year
    
        Output: available year ranges, record counts for the requested season, and missing-value counts for relevant fields
    
        Database interactions: predefined summary SQL queries against the PostgreSQL database, joining specific tables to determine season coverage.
    '''

def main(connection):
    # TODO: Function that initiates Gemini and takes user input; should handle errors and security issues
    print("Temp")

if __name__ == "__main__":
    connection = connect_server()
    commit_schema(connection)
    insert_data(connection)
    main(connection)