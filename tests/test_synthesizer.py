from src.agent import investigate_campaign
from src.models import CampaignRequirements, CreatorRecommendation
from src.synthesizer import synthesize_recommendations


def test_synthesize_recommendations():
    campaign = CampaignRequirements(
        niche="fintech",
        target_age_min=18,
        target_age_max=30,
        geography="India",
        platform="Instagram",
        campaign_goal="awareness",
    )

    investigations = investigate_campaign(campaign)

    recommendations = synthesize_recommendations(
        campaign,
        investigations,
    )

    assert len(recommendations) > 0

    for recommendation in recommendations:
        assert isinstance(recommendation, CreatorRecommendation)
        assert 0 <= recommendation.score <= 100
        assert recommendation.creator_id
        assert recommendation.creator_name
        assert recommendation.recommendation
        assert recommendation.evidence