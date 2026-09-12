from google.genai import types

from src.config import settings
from src.llm import call_llm_with_fallback, gemini_client, groq_client, GROQ_MODEL
from src.models import Creator, SafetyVerdict
from src.rag.retrieve import retrieve_guidelines


def check_brand_safety(creator: Creator) -> SafetyVerdict:
    brand_cats_str = ", ".join(creator.previous_brand_categories)
    query = (
        f"Brand safety assessment for {creator.niche} creator. "
        f"Content summary: {creator.content_summary}. "
        f"Past sponsored categories: {brand_cats_str}."
    )

    guidelines = retrieve_guidelines(query, top_k=3)
    retrieved_chunks = [item["document"] for item in guidelines if item.get("document")]

    guideline_text = "\n\n".join(
        f"Source: {item['source']}\n{item['document']}"
        for item in guidelines
    )

    prompt = f"""
Assess this creator for brand safety using ONLY the supplied creator information and retrieved guidelines.

Creator ID: {creator.creator_id}
Niche: {creator.niche}
Content Summary: {creator.content_summary}
Previous Brand Categories: {brand_cats_str}

Retrieved guidelines:
{guideline_text}

Provide a structured verdict:
- creator_id: {creator.creator_id}
- risk_level: "low", "medium", or "high"
- reasoning: brief evidence-based explanation
- grounded_in: exact relevant quote(s) or excerpt(s) from the retrieved guidelines
"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SafetyVerdict,
    )

    def _groq_safety():
        if not groq_client:
            raise RuntimeError("Groq client not initialized")
        system_msg = (
            "You are a brand safety evaluation agent. Output JSON with keys: "
            "creator_id (string), risk_level ('low', 'medium', or 'high'), reasoning (string), grounded_in (list of strings)."
        )
        res = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
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
        groq_fn=_groq_safety,
        purpose="safety",
        model=settings.gemini_model,
    )

    verdict = SafetyVerdict.model_validate_json(response.text)
    
    # Ensure grounded_in contains retrieved chunk texts if model returned empty
    if not verdict.grounded_in:
        verdict.grounded_in = retrieved_chunks

    verdict.model_used = model_used
    return verdict