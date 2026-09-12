import json
from google.genai import types

from src.config import settings
from src.llm import call_llm_with_fallback, gemini_client, groq_client, GROQ_MODEL
from src.models import (
    CampaignRequirements,
    CreatorInvestigation,
    CreatorRecommendation,
)


def enforce_unknown_risk_guard(
    recommendations: list[CreatorRecommendation],
) -> list[CreatorRecommendation]:
    """
    Deterministic post-processing guard:
    Verifies no creator without brand safety evidence ranks above a verified-safe creator
    if their scores are within 10 points.
    """
    def has_safety(rec: CreatorRecommendation) -> bool:
        return any(
            "safety" in ev.source.lower() or "safety" in ev.claim.lower()
            for ev in rec.evidence
        )

    # Note: A plain sorted key cannot cleanly express the conditional 10-point score tolerance gap window, so we use a single forward pass to demote unverified creators outranking safe creators within 10 pts.
    recs = sorted(recommendations, key=lambda r: r.score, reverse=True)
    for i in range(len(recs) - 1):
        if not has_safety(recs[i]) and has_safety(recs[i + 1]):
            if recs[i].score - recs[i + 1].score <= 10.0:
                recs[i], recs[i + 1] = recs[i + 1], recs[i]

    return recs


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
5. If no brand_safety evidence is present for a creator, treat their risk as UNKNOWN — do not rank them as if they were vetted. Prefer candidates with verified safety evidence when scores are close.
6. Give each creator a score from 0 to 100.
7. Explain the recommendation concisely.
8. Preserve every evidence item exactly as supplied.
9. The evidence types mean:
   - retrieved_fact = retrieved database information
   - calculated_metric = deterministic Python calculation
   - model_judgment = LLM judgment based on retrieved guidelines

Return the creators ranked from strongest to weakest.
"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[CreatorRecommendation],
    )

    def _groq_synthesizer():
        if not groq_client:
            raise RuntimeError("Groq client not initialized")
        system_msg = (
            "You are the final recommendation engine. Output JSON containing an array of recommendations under key 'recommendations' or direct array. "
            "Each object must have: creator_id, creator_name, score (float 0-100), evidence (list of objects with type, claim, source), recommendation (string)."
        )
        res = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = res.choices[0].message.content
        class DummyTextResponse:
            def __init__(self, text):
                self.text = text
        return DummyTextResponse(content)

    response, model_used = call_llm_with_fallback(
        lambda: gemini_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        ),
        groq_fn=_groq_synthesizer,
        purpose="synthesizer",
        model=settings.gemini_model,
    )

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError:
        cleaned = response.text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()
        data = json.loads(cleaned)

    if isinstance(data, dict):
        data = data.get("recommendations", data.get("creators", list(data.values())[0]))

    raw_recs = [
        CreatorRecommendation.model_validate(item)
        for item in data
    ]

    for r in raw_recs:
        r.model_used = model_used

    return enforce_unknown_risk_guard(raw_recs)