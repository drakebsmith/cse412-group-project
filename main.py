# Imports will likely need modification since we'll need to interface with the PostgreSQL server and Kaggle
import os
import psycopg2
from dotenv import load_dotenv

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
    # TODO: Function that initiates Gemini and takes user input; should handle errors and security issues
    print("Hello world!") # This is just here to prevent an error from being thrown for having an empty main()

if __name__ == "__main__":
    main()