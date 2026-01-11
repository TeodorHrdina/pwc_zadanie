import os
import logging
from dotenv import load_dotenv
import pandas
from openai import OpenAI
from openai._exceptions import APIConnectionError, AuthenticationError, RateLimitError
from fastapi import FastAPI, Body, HTTPException
import pyodbc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.post("/chat")
def handle_chat(body=Body()):
    try:
        logger.info(f"Received conversation history: {body.get('conversationHistory', [])[:2]}...")  # Log first 2 items
        completion = openAIClient.chat.completions.create(
            model="gpt-4o-mini",
            messages=body["conversationHistory"]
        )

        result = completion.choices[0].message.content
        logger.info("Successfully got response from OpenAI API")
        return result

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise e