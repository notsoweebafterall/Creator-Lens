from google import genai
from google.genai import types

from src.config import settings
from src.models import CampaignRequirements
from src.llm import generate_with_fallback

client = genai.Client(api_key=settings.gemini_api_key)


def extract_campaign_requirements(brief: str) -> CampaignRequirements:
    prompt = f"""
Extract the campaign requirements from the following brand brief.

Return only information explicitly stated or strongly implied by the brief.
Do not invent missing values.

Brand brief:
{brief}
"""

    response_text = generate_with_fallback(
        prompt,
        response_schema=CampaignRequirements,
    )

    return CampaignRequirements.model_validate_json(response_text)