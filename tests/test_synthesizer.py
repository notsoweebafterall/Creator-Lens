from src.agent import investigate_campaign
from src.models import (
    CampaignRequirements,
    CreatorRecommendation,
    Evidence,
)
from src.synthesizer import enforce_unknown_risk_guard, synthesize_recommendations


def test_synthesize_recommendations():
    campaign = CampaignRequirements(
        niche="fintech",
        budget_inr=500000,
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


def test_enforce_unknown_risk_guard():
    # Rec A has higher LLM score (95) but NO brand safety evidence
    rec_a = CreatorRecommendation(
        creator_id="C001",
        creator_name="Unvetted Creator",
        score=95.0,
        evidence=[
            Evidence(type="retrieved_fact", claim="Fintech creator", source="search_creators"),
            Evidence(type="calculated_metric", claim="Engagement: 5%", source="compute_engagement"),
        ],
        recommendation="Unvetted candidate",
    )

    # Rec B has slightly lower score (90) but HAS verified safety evidence
    rec_b = CreatorRecommendation(
        creator_id="C002",
        creator_name="Vetted Safe Creator",
        score=90.0,
        evidence=[
            Evidence(type="retrieved_fact", claim="Fintech creator", source="search_creators"),
            Evidence(type="model_judgment", claim="Brand safety risk: low", source="check_brand_safety"),
        ],
        recommendation="Vetted safe candidate",
    )

    # Guard should demote Rec A below Rec B because score diff is <= 10 and A lacks safety evidence
    guarded = enforce_unknown_risk_guard([rec_a, rec_b])

    assert guarded[0].creator_id == "C002"
    assert guarded[1].creator_id == "C001"