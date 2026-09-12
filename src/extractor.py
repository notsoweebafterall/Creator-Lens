from google.genai import types

from src.config import settings
from src.llm import call_llm_with_fallback, gemini_client, groq_client, GROQ_MODEL
from src.models import CampaignRequirements


def extract_campaign_requirements(brief: str) -> CampaignRequirements:
    prompt = f"""
Extract the campaign requirements from the following brand brief.

Return only information explicitly stated or strongly implied by the brief.
Do not invent missing values.

CRITICAL INSTRUCTION:
If the brief is missing key requirements such as budget (budget_inr), niche, or geography, you MUST set needs_clarification=True and explain what is missing or ambiguous in clarification_reason rather than guessing.

Brand brief:
{brief}
"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CampaignRequirements,
    )

    def _groq_extractor():
        if not groq_client:
            raise RuntimeError("Groq client not initialized")
        system_msg = (
            "Extract campaign requirements from the brand brief into JSON matching schema keys: "
            "niche, budget_inr, target_age_min, target_age_max, geography, platform, campaign_goal, "
            "needs_clarification (bool), clarification_reason (string or null), min_creators (default 3). "
            "If budget_inr, niche, or geography is missing, set needs_clarification=true and clarify in clarification_reason."
        )
        res = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": brief},
            ],
            response_format={"type": "json_object"},
        )
        class DummyTextResponse:
            def __init__(self, text):
                self.text = text
        return DummyTextResponse(res.choices[0].message.content)

    response, model_used = call_llm_with_fallback(
        lambda: gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        ),
        groq_fn=_groq_extractor,
        purpose="extractor",
        model=settings.gemini_model,
    )

    reqs = CampaignRequirements.model_validate_json(response.text)
    reqs.model_used = model_used
    return reqs