import pytest
from src.agent import compute_engagement_tool, investigate_campaign
from src.llm import call_llm_with_fallback, log_llm_event
from src.models import CampaignRequirements, CreatorInvestigation, Evidence, SafetyVerdict
from src.extractor import extract_campaign_requirements
from src.tools.safety import check_brand_safety


def test_tool_sequence_populated():
    """Verify tool_sequence is populated as a proper Field on CreatorInvestigation."""
    inv = CreatorInvestigation(creator_id="C001", creator_name="Test Creator")
    inv.tool_sequence = ["search_creators", "compute_engagement"]
    assert inv.tool_sequence == ["search_creators", "compute_engagement"]
    dumped = inv.model_dump()
    assert "tool_sequence" in dumped
    assert dumped["tool_sequence"] == ["search_creators", "compute_engagement"]


def test_malformed_creator_dict_fallback():
    """Verify malformed creator_dict produces flagged fallback and logs warning."""
    malformed_dict = {"creator_id": "C999", "avg_likes": 100, "followers": 1000}
    res = compute_engagement_tool(malformed_dict)
    assert res["is_fallback"] is True
    assert isinstance(res["rate"], float)


def test_groq_fallback_on_forced_gemini_failure():
    """Verify forced Gemini failure triggers Groq fallback and records model_used."""
    def forced_failing_gemini():
        raise RuntimeError("Simulated Gemini total outage")

    def mock_groq_fn():
        class DummyRes:
            text = '{"creator_id": "C001", "risk_level": "low", "reasoning": "Groq fallback evaluation ok", "grounded_in": ["safe"]}'
        return DummyRes()

    res, model_used = call_llm_with_fallback(
        forced_failing_gemini,
        groq_fn=mock_groq_fn,
        purpose="test_forced_fallback",
        max_retries=1,
    )

    assert "groq" in model_used.lower()
    verdict = SafetyVerdict.model_validate_json(res.text)
    verdict.model_used = model_used
    assert "groq" in verdict.model_used.lower()
