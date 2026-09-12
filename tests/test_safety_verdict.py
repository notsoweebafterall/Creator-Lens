from src.models import Creator, SafetyVerdict
from src.tools.safety import check_brand_safety


def test_check_brand_safety_grounded_in():
    creator = Creator(
        creator_id="C001",
        name="Crypto King",
        platform="Instagram",
        niche="fintech",
        followers=100000,
        avg_views=30000,
        avg_likes=2000,
        avg_comments=100,
        audience_age_18_24=0.4,
        audience_age_25_34=0.4,
        geography="India",
        estimated_price_inr=50000,
        content_summary="Promotes high-yield crypto trading strategies and token pre-sales.",
        previous_brand_categories=["crypto trading", "unregulated loans"],
    )

    verdict = check_brand_safety(creator)

    assert isinstance(verdict, SafetyVerdict)
    assert verdict.creator_id == "C001"
    assert verdict.risk_level in {"low", "medium", "high"}
    assert verdict.reasoning
    
    # Assert grounded_in actually contains non-empty retrieved chunk text!
    assert isinstance(verdict.grounded_in, list)
    assert len(verdict.grounded_in) > 0, "grounded_in list must not be empty"
    for chunk in verdict.grounded_in:
        assert isinstance(chunk, str)
        assert len(chunk.strip()) > 0, "grounded_in text chunk must not be empty string"
