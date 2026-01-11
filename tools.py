import json
import pandas
import os
import sqlite3
from dotenv import load_dotenv

def getDBConnection(): # Temporary implementation. In deployment to be replaced with real SQL connection.
    dataFrame = pandas.read_excel('Data Dump - Accrual Accounts.xlsx')
    connection = sqlite3.connect("demo.db")
    dataFrame.to_sql("accounts", con=connection)
    return connection


# SQL injection through hidden prompts is no bueno
def sanitizeInput(inputString: str) -> str:
    
    dangerous_patterns = [
        ';', '--', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute', 'drop', 'delete',
        'update', 'insert', 'create', 'alter', 'truncate', 'merge', 'grant', 'revoke'
    ]
    
    inputLower = inputString.lower()
    for pattern in dangerous_patterns:
        if pattern in input_lower:
            raise ValueError("Dangerous SQL detected: " + pattern)
    
    sanitized = input_str.replace("'", "''")
    return sanitized


def buildSelectQuery(table_name: str, columns: List[str] = None, where_clause: str = None, 
                      order_by: str = None) -> str:
    
    table_name = sanitize_input(table_name)
    
    query = f"SELECT {columns_str} FROM {table_name}"
    
    if where_clause:
        where_clause = sanitize_input(where_clause)
        query += f" WHERE {where_clause}"
    
    if order_by:
        order_by = sanitize_input(order_by)
        query += f" ORDER BY {order_by}"
    
    
    query += " LIMIT 5;" # To prevent overwhelming the AI with information every response is limited to 5 entries
    
    return query


def executeSQL(table_name: str, columns: List[str] = None, where_clause: str = None, 
                        order_by: str = None) -> List[Dict[str, Any]]:

    
    query = buildSelectQuery(table_name, columns, where_clause, order_by)
    
    
    dbConnection = getDBConnection()
    try:
        cursor = dbConnection.cursor()
        cursor.execute(query)
        
        columns_info = [column[0] for column in cursor.description]
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns_info):
                row_dict[col] = row[i]
            results.append(row_dict)
        
        return results
    
    finally:
        conn.close()


def get_tool_schema() -> Dict[str, Any]:

    return {
        "name": "select_sql",
        "description": "Execute a SELECT query on the database to retrieve data. This tool can only read data and cannot modify the database. Each response is limited to 5 rows of responses.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to query",
                },
                "columns": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of specific columns to retrieve (optional, defaults to all columns)",
                    "default": ["*"]
                },
                "where_clause": {
                    "type": "string",
                    "description": "WHERE clause conditions to filter results (optional)"
                },
                "order_by": {
                    "type": "string",
                    "description": "ORDER BY clause to sort results (optional)"
                }
            },
            "required": ["table_name"],
            "additionalProperties": False
        }
    }