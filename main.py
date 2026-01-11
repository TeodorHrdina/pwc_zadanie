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

        SystemMessage = {
            "role": "system",
            "content": f"You are a SQL Data Science Assistant. You can help users query databases using SQL. When appropriate, use the selectSQL tool to retrieve data from the database. Always follow safe practices and never attempt to modify the database.\n\nDatabase Schema:\n{json.dumps(DbSchema, indent=2)}"
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