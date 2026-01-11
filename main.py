import os
from dotenv import load_dotenv
import pandas
from openai import OpenAI
from fastapi import FastAPI, Body
import tools

app = FastAPI()
load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

openAIClient = OpenAI(
    api_key=openai_api_key,
    timeout=30.0
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/test_db_query")
def read_test_db_query():
    return tools.ExecuteSQL("accounts", None, "Transaction Value > 1000")


@app.post("/chat")
def handle_chat(body=Body()):
    try:
        completion = openAIClient.chat.completions.create(
            model="gpt-4o-mini",
            messages=body["conversationHistory"],
            tools=[tools.GetToolSchema()]
        )

        result = completion.choices[0].message.content
        return result

    except Exception as e:
        raise e