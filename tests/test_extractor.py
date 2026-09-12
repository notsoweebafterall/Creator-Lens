from src.extractor import extract_campaign_requirements


def test_extract_campaign_requirements_complete():
    brief = """
    A fintech brand wants an Instagram awareness campaign in India.
    The target audience is 18 to 30 years old.
    The campaign budget is 500000 INR.
    """

    result = extract_campaign_requirements(brief)

    assert result.niche.lower() == "fintech"
    assert result.platform.lower() == "instagram"
    assert result.geography.lower() == "india"
    assert result.target_age_min == 18
    assert result.target_age_max == 30
    assert result.budget_inr == 500000
    assert result.needs_clarification is False


def test_extract_campaign_requirements_incomplete():
    brief = """
    We want a cool creator campaign for young people on Instagram.
    """

    result = extract_campaign_requirements(brief)

    assert result.needs_clarification is True
    assert result.clarification_reason is not None
    assert len(result.clarification_reason) > 0