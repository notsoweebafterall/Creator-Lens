from google import genai
from google.genai import errors
import os
from openai import OpenAI

from dotenv import load_dotenv

from src.config import settings
from src.models import Creator
from src.rag.retrieve import retrieve_guidelines

load_dotenv()


client = genai.Client(api_key=settings.gemini_api_key)
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)


def check_brand_safety(creator: Creator) -> str:
    query = (
        f"Brand safety assessment for a {creator.niche} creator "
        f"on {creator.platform}. "
        f"Known status: {creator.brand_safety_status}"
    )

    guidelines = retrieve_guidelines(query, top_k=3)

    guideline_text = "\n\n".join(
        f"Source: {item['source']}\n{item['document']}"
        for item in guidelines
    )

    prompt = f"""
Assess this creator for brand safety using ONLY the supplied
creator information and retrieved guidelines.

Creator:
{creator.model_dump_json(indent=2)}

Retrieved guidelines:
{guideline_text}

Return a concise judgment:
SAFE, REVIEW, or UNSAFE

Then give one short reason.
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )

        print("RAW SAFETY RESPONSE:", repr(response.text))

        return response.text.strip()

    except (errors.ServerError, errors.ClientError) as exc:
        print(f"[Safety] Gemini failed: {exc}")
        print("[Safety] Falling back to Groq...")

        groq_response = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        result = groq_response.choices[0].message.content.strip()

        print("RAW SAFETY RESPONSE (Groq):", repr(result))

        return result