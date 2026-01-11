import json
import pandas
import os
import sqlite3
import re
from typing import List, Dict, Any

def GetDatabaseConnection():
    DatabaseExists = os.path.exists("demo.db")
    Connection = sqlite3.connect("demo.db")

    if not DatabaseExists:
        PopulateDatabase(Connection)
    else:
        Cursor = Connection.cursor()
        Cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        Tables = Cursor.fetchall()
        if not Tables:
            PopulateDatabase(Connection)

    return Connection

def PopulateDatabase(Connection):
    DataFrame = pandas.read_excel('Data Dump - Accrual Accounts.xlsx')
    DataFrame.to_sql("accounts", con=Connection, if_exists='replace', index=False)

    Cursor = Connection.cursor()
    Cursor.execute("PRAGMA table_info(accounts)")
    ColumnsInformation = Cursor.fetchall()

    TableSchema = {
        "accounts": {
            "description": "Accrual accounts data",
            "columns": []
        }
    }

    for Col in ColumnsInformation:
        ColumnInformation = {
            "name": Col[1],
            "type": Col[2],
            "nullable": not Col[3],
            "default": Col[4],
            "primary_key": Col[5] == 1
        }
        TableSchema["accounts"]["columns"].append(ColumnInformation)

    with open('db_schema.json', 'w') as File:
        json.dump(TableSchema, File, indent=2)

def SanitizeInput(InputString: str) -> str:
    DangerousPatterns = [
        ';', '--', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute', 'drop', 'delete',
        'update', 'insert', 'alter', 'truncate', 'merge', 'grant', 'revoke'
    ]

    InputLower = InputString.lower()
    for Pattern in DangerousPatterns:
        if Pattern in InputLower:
            raise ValueError("Dangerous SQL detected: " + Pattern)

    Sanitized = InputString.replace("'", "''")
    return Sanitized


def QuoteColumnInWhere(WhereClause: str, Connection) -> str:
    if not WhereClause:
        return WhereClause

    Cursor = Connection.cursor()
    Cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    Tables = Cursor.fetchall()

    AllColumns = []
    for Table in Tables:
        TableName = Table[0]
        Cursor.execute(f"PRAGMA table_info('{TableName}')")
        ColumnsInformation = Cursor.fetchall()
        for ColumnInformation in ColumnsInformation:
            AllColumns.append(ColumnInformation[1])

    ProcessedWhere = WhereClause
    for ColumnName in AllColumns:
        ProcessedWhere = re.sub(r'\b' + re.escape(ColumnName) + r'\b', f'"{ColumnName}"', ProcessedWhere)

    return ProcessedWhere


def BuildSelectQuery(TableName: str, Columns: List[str] = None, WhereClause: str = None,
                     OrderBy: str = None) -> str:

    TableName = SanitizeInput(TableName)
    QuotedTableName = f'"{TableName}"'

    if Columns:
        QuotedColumns = []
        for Col in Columns:
            SanitizedColumn = SanitizeInput(Col.strip())
            QuotedColumns.append(f'"{SanitizedColumn}"')
        ColumnsString = ", ".join(QuotedColumns)
    else:
        ColumnsString = "*"

    Query = f"SELECT {ColumnsString} FROM {QuotedTableName}"

    if WhereClause:
        DatabaseConnection = GetDatabaseConnection()
        try:
            WhereClause = SanitizeInput(WhereClause)
            WhereClause = QuoteColumnInWhere(WhereClause, DatabaseConnection)
            Query += f" WHERE {WhereClause}"
        finally:
            DatabaseConnection.close()

    if OrderBy:
        if OrderBy:
            DatabaseConnection = GetDatabaseConnection()
            try:
                OrderBy = SanitizeInput(OrderBy)
                OrderBy = QuoteColumnInWhere(OrderBy, DatabaseConnection)
                Query += f" ORDER BY {OrderBy}"
            finally:
                DatabaseConnection.close()

    Query += " LIMIT 5;"
    return Query


def ExecuteSQL(TableName: str, Columns: List[str] = None, WhereClause: str = None,
               OrderBy: str = None) -> List[Dict[str, Any]]:

    DatabaseConnection = GetDatabaseConnection()
    try:
        Cursor = DatabaseConnection.cursor()
        Cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        AvailableTables = [Row[0] for Row in Cursor.fetchall()]

        if TableName not in AvailableTables:
            raise ValueError(f"Table '{TableName}' does not exist in the database. Available tables: {AvailableTables}")

        Query = BuildSelectQuery(TableName, Columns, WhereClause, OrderBy)

        Cursor.execute(Query)

        ColumnsInformation = [Column[0] for Column in Cursor.description]

        Rows = Cursor.fetchall()

        Results = []
        for Row in Rows:
            RowDictionary = {}
            for Index, Col in enumerate(ColumnsInformation):
                RowDictionary[Col] = Row[Index]
            Results.append(RowDictionary)

        return Results

    finally:
        DatabaseConnection.close()


def GetToolSchema() -> Dict[str, Any]:

    return {
        "type": "function",
        "function": {
            "name": "selectSQL",
            "description": "Execute a SELECT query on the database to retrieve data. This tool can only read data and cannot modify the database. Each response is limited to 5 rows of responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "TableName": {
                        "type": "string",
                        "description": "Name of the table to query",
                    },
                    "Columns": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of specific columns to retrieve (optional, defaults to all columns)",
                        "default": ["*"]
                    },
                    "WhereClause": {
                        "type": "string",
                        "description": "WHERE clause conditions to filter results (optional)"
                    },
                    "OrderBy": {
                        "type": "string",
                        "description": "ORDER BY clause to sort results (optional)"
                    }
                },
                "required": ["TableName"],
                "additionalProperties": False
            }
        }
    }


def GetTablesSchema() -> Dict[str, Any]:
    try:
        with open('db_schema.json', 'r') as File:
            return json.load(File)
    except FileNotFoundError:
        return {
            "description": "Database schema information",
            "tables": {}
        }