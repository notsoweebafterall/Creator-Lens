from src.extractor import extract_campaign_requirements


def test_extract_campaign_requirements():
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
    assert result.budget == 500000
    assert result.campaign_goal.lower() == "awareness"