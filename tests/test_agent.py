from src.agent import investigate_campaign
from src.models import CampaignRequirements, CreatorInvestigation


def test_investigate_campaign():
    campaign = CampaignRequirements(
        niche="fintech",
        target_age_min=18,
        target_age_max=30,
        geography="India",
        platform="Instagram",
        campaign_goal="awareness",
    )

    results = investigate_campaign(campaign)

    assert len(results) > 0

    for creator in results:
        assert isinstance(creator, CreatorInvestigation)
        assert creator.creator_id
        assert creator.creator_name
        assert creator.evidence

        for evidence in creator.evidence:
            assert evidence.type in {
                "retrieved_fact",
                "calculated_metric",
                "model_judgment",
            }
            assert evidence.claim
            assert evidence.source