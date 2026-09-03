import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from openai import OpenAI
from pydantic import TypeAdapter

load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)


def generate_with_fallback(
    prompt: str,
    response_schema=None,
) -> str:

    try:
        config = None

        if response_schema is not None:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )

        response = gemini_client.models.generate_content(
            model=os.getenv("GEMINI_MODEL"),
            contents=prompt,
            config=config,
        )

        print("[LLM] Gemini succeeded.")
        return response.text

    except (errors.ServerError, errors.ClientError) as exc:
        print(f"[LLM] Gemini failed: {exc}")
        print("[LLM] Falling back to Groq...")

    groq_kwargs = {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    if response_schema is not None:
        schema = TypeAdapter(response_schema).json_schema()

        groq_kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_response",
                "schema": schema,
                "strict": False,
            },
        }

    response = groq_client.chat.completions.create(**groq_kwargs)

    print("[LLM] Groq fallback succeeded.")
    return response.choices[0].message.content