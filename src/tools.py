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

    # Sort columns by length in descending order to match longer column names first
    # This helps prevent partial matches (e.g., matching "Date" in "Clearing Date")
    AllColumns = sorted(AllColumns, key=len, reverse=True)

    ProcessedWhere = WhereClause
    for ColumnName in AllColumns:
        # Use word boundaries with special handling for column names that contain spaces
        # For column names with spaces, we can't use \b, so we'll use a more general approach
        escaped_name = re.escape(ColumnName)
        # Match the column name as a whole word/unit, handling cases with/without spaces
        if ' ' in ColumnName:
            # For names with spaces, look for the full name surrounded by word boundaries or operators
            ProcessedWhere = re.sub(r'(?<!\w)(' + escaped_name + r')(?!\w)', f'"{ColumnName}"', ProcessedWhere)
        else:
            # For names without spaces, use word boundaries
            ProcessedWhere = re.sub(r'\b' + escaped_name + r'\b', f'"{ColumnName}"', ProcessedWhere)

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


def ValidateWhereClause(WhereClause: str, TableName: str) -> bool:
    """
    Validates the WHERE clause by checking if it contains potentially non-existent column names.
    This is a heuristic check that looks for column references that might not exist in the table.
    """
    if not WhereClause:
        return True

    DatabaseConnection = GetDatabaseConnection()
    try:
        Cursor = DatabaseConnection.cursor()
        # Get all columns for the table
        Cursor.execute(f"PRAGMA table_info('{TableName}')")
        ValidColumns = [row[1] for row in Cursor.fetchall()]

        # Clean up the WhereClause to handle quoted identifiers properly
        # Remove single and double quotes portions which are usually literals, not columns
        cleaned_clause = WhereClause

        # Extract potential column names from the where clause by looking for identifiers
        # This regex finds words that could be column names (ignoring operators, values, etc.)
        # We'll use a more sophisticated method that considers SQL structure
        import re

        # This captures potential column names in common SQL patterns like:
        # column = value, column > value, column BETWEEN value AND value, etc.
        # Split the clause by SQL operators and look for identifiers
        # First, remove quoted string literals
        clause_no_strings = re.sub(r"'[^']*'", '', WhereClause)  # Remove single-quoted strings
        clause_no_strings = re.sub(r'"[^"]*"', '', clause_no_strings)  # Remove double-quoted strings (but preserve quoted column names)

        # Find potential column names (word-like tokens that could be column names)
        # We'll look for unquoted identifiers only
        potential_columns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_\.]*)\b', clause_no_strings)

        # Filter out SQL keywords and operators that aren't column names
        sql_keywords = {
            'select', 'from', 'where', 'order', 'by', 'group', 'having', 'distinct', 'limit',
            'and', 'or', 'not', 'in', 'like', 'between', 'is', 'null', 'true', 'false',
            'as', 'on', 'inner', 'outer', 'left', 'right', 'join', 'union', 'intersect', 'except',
            'avg', 'count', 'max', 'min', 'sum', 'abs', 'round', 'length', 'upper', 'lower',
            'datetime', 'date', 'timestamp', 'integer', 'text', 'real', 'numeric', 'varchar',
            'int', 'bool', 'float', 'double', 'char'
        }

        potential_columns = [col for col in potential_columns if col.lower() not in sql_keywords]

        for col in potential_columns:
            if '.' in col:
                parts = col.split('.', 1)
                if len(parts) == 2:
                    # Assuming first part is table alias (could be checked more rigorously)
                    col_name = parts[1]
                else:
                    col_name = parts[0]
            else:
                col_name = col

            # For column names with spaces, the AI might provide parts of the name
            # We need strict matching for full column names
            if col_name.lower() not in [vc.lower() for vc in ValidColumns]:
                if len([vc for vc in ValidColumns if col_name.lower() in vc.lower()]) > 0:
                    similar_cols = [vc for vc in ValidColumns if col_name.lower() in vc.lower()]
                    raise ValueError(f"Column '{col_name}' not found in table '{TableName}'. Did you mean one of these: {similar_cols}? Valid columns are: {ValidColumns}")
                else:
                    raise ValueError(f"Column '{col_name}' not found in table '{TableName}'. Valid columns are: {ValidColumns}")

        return True
    finally:
        DatabaseConnection.close()


def ExecuteSQL(TableName: str, Columns: List[str] = None, WhereClause: str = None,
               OrderBy: str = None) -> List[Dict[str, Any]]:

    DatabaseConnection = GetDatabaseConnection()
    try:
        Cursor = DatabaseConnection.cursor()
        Cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        AvailableTables = [Row[0] for Row in Cursor.fetchall()]

        if TableName not in AvailableTables:
            raise ValueError(f"Table '{TableName}' does not exist in the database. Available tables: {AvailableTables}")

        if WhereClause:
            ValidateWhereClause(WhereClause, TableName)

        if OrderBy:
            ValidateWhereClause(OrderBy, TableName)  # Reusing the same validator since logic is similar

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
    db_schema = GetTablesSchema()

    table_columns = {}
    for table_name, table_info in db_schema.items():
        if isinstance(table_info, dict) and "columns" in table_info:
            table_columns[table_name] = [col["name"] for col in table_info["columns"]]

    schema = {
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
                        "enum": list(table_columns.keys()) if table_columns else ["accounts"]  # fallback to "accounts"
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

    return schema


def GetTablesSchema() -> Dict[str, Any]:
    try:
        with open('db_schema.json', 'r') as File:
            return json.load(File)
    except FileNotFoundError:
        return {
            "description": "Database schema information",
            "tables": {}
        }