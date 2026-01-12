import os
import json
from dotenv import load_dotenv
import pandas
from openai import OpenAI
from fastapi import FastAPI, Body
import tools

App = FastAPI()
LoadDotEnv = load_dotenv()

OpenAIApiKey = os.environ.get("OPENAI_API_KEY")
if not OpenAIApiKey:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

OpenAIClient = OpenAI(
    api_key=OpenAIApiKey,
    timeout=30.0
)

@App.get("/")
def ReadRoot():
    return {"Hello": "World"}

@App.get("/test_db_query")
def ReadTestDbQuery():
    return tools.ExecuteSQL("accounts", None, "Transaction Value > 1000")


@App.post("/chat")
def HandleChat(Body: dict = Body()):
    try:
        Messages = Body["conversationHistory"]

        DbSchema = tools.GetTablesSchema()

        schema_description = "DATABASE SCHEMA INFORMATION:\n\n"

        for table_name, table_info in DbSchema.items():
            if isinstance(table_info, dict) and "columns" in table_info:
                schema_description += f"TABLE: {table_name}\n"
                schema_description += f"Description: {table_info.get('description', 'No description')}\n"
                schema_description += "COLUMNS:\n"

                for col_info in table_info["columns"]:
                    col_name = col_info["name"]
                    col_type = col_info["type"]
                    schema_description += f"  - {col_name} ({col_type})\n"

                schema_description += "\n"

        SystemMessage = {
            "role": "system",
            "content": f"You are a SQL Data Science Assistant. You can help users query databases using SQL. When appropriate, use the selectSQL tool to retrieve data from the database. Always follow safe practices and never attempt to modify the database.\n\n{schema_description}\n\nIMPORTANT: BEFORE FORMING ANY SQL QUERY, you MUST verify that every column name you intend to use exists in the schema above. The tool will reject any queries that reference non-existent columns.\n\nCRITICAL RULES FOR QUERYING:\n1. ONLY use the exact column names listed in the schema above - NO EXCEPTIONS\n2. Do not invent, guess, or hallucinate any column names that are not explicitly listed\n3. When using WHERE or ORDER BY clauses, use only the valid column names provided\n4. If uncertain, query without WHERE clause first to see sample data and confirm column names\n5. IMPORTANT: Some column names contain spaces (like \"Clearing Date\", \"Transaction Value\"). Use them exactly as shown, including spaces.\n\nFAILURE TO FOLLOW THESE RULES WILL RESULT IN QUERY ERRORS."
        }

        if not Messages or Messages[0]["role"] != "system":
            Messages = [SystemMessage] + Messages

        Completion = OpenAIClient.chat.completions.create(
            model="gpt-4o-mini",
            messages=Messages,
            tools=[tools.GetToolSchema()]
        )

        while Completion.choices[0].finish_reason == "tool_calls":
            AssistantMessage = Completion.choices[0].message
            Messages.append(AssistantMessage.model_dump())

            for ToolCall in AssistantMessage.tool_calls:
                FunctionName = ToolCall.function.name
                Arguments = json.loads(ToolCall.function.arguments)

                if FunctionName == "selectSQL":
                    try:
                        TableName = Arguments.get("TableName")
                        Columns = Arguments.get("Columns")
                        WhereClause = Arguments.get("WhereClause")
                        OrderBy = Arguments.get("OrderBy")

                        ToolResult = tools.ExecuteSQL(
                            TableName=TableName,
                            Columns=Columns,
                            WhereClause=WhereClause,
                            OrderBy=OrderBy
                        )
                    except ValueError as e:
                        # Return the error to the agent so it can correct itself
                        ToolResult = {"error": f"Validation Error: {str(e)}. Please check your column names and make sure they exactly match the available columns in the database schema."}
                    except Exception as e:
                        # Return general error to the agent
                        ToolResult = {"error": f"Error executing query: {str(e)}. Please verify your SQL syntax and make sure you're using valid column names from the schema."}
                else:
                    ToolResult = {"error": f"Unknown tool: {FunctionName}"}

                ToolResponse = {
                    "tool_call_id": ToolCall.id,
                    "role": "tool",
                    "name": FunctionName,
                    "content": json.dumps(ToolResult)
                }
                Messages.append(ToolResponse)

            Completion = OpenAIClient.chat.completions.create(
                model="gpt-4o-mini",
                messages=Messages,
                tools=[tools.GetToolSchema()]
            )

        Result = Completion.choices[0].message.content
        return Result

    except Exception as E:
        raise E