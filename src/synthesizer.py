from google import genai
from google.genai import types

from src.config import settings
from src.models import (
    CampaignRequirements,
    CreatorInvestigation,
    CreatorRecommendation,
)
from src.llm import generate_with_fallback


client = genai.Client(api_key=settings.gemini_api_key)


def synthesize_recommendations(
    campaign: CampaignRequirements,
    investigations: list[CreatorInvestigation],
) -> list[CreatorRecommendation]:

    prompt = f"""
You are the final recommendation engine for CreatorLens.

Campaign:
{campaign.model_dump_json(indent=2)}

Creator investigations:
{[item.model_dump() for item in investigations]}

Rank the investigated creators for this campaign.

Rules:
1. Use ONLY the supplied evidence.
2. Never invent creator facts or metrics.
3. Do not change any numerical values.
4. Consider engagement, audience fit, and brand safety.
5. Give each creator a score from 0 to 100.
6. Explain the recommendation concisely.
7. Preserve every evidence item exactly as supplied.
8. The evidence types mean:
   - retrieved_fact = retrieved database information
   - calculated_metric = deterministic Python calculation
   - model_judgment = LLM judgment based on retrieved guidelines

Return the creators ranked from strongest to weakest.
"""

    response_text = generate_with_fallback(
        prompt,
        response_schema=list[CreatorRecommendation],
    )

    print("\n[DEBUG] GROQ SYNTHESIZER RESPONSE:")
    print(repr(response_text))

    import json

    try:
        data = json.loads(response_text)

    except json.JSONDecodeError:
        cleaned = response_text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()

        data = json.loads(cleaned)

    return [
        CreatorRecommendation.model_validate(item)
        for item in data
    ]