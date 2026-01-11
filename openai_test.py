import os
import truststore
from openai import OpenAI
from dotenv import load_dotenv

truststore.inject_into_ssl()
load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(
    api_key=openai_api_key,
    timeout=30.0 
)

stream = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": "Say 'double bubble bath' ten times fast.",
        },
    ],
    stream=True,
)

for event in stream:
    print(event)