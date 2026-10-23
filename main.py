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