from src.tools.search import search_creators


def test_budget_filter():
    ceiling = 100000
    creators = search_creators(
        niche="fintech",
        platform="Instagram",
        geography="India",
        max_price_inr=ceiling,
        limit=10,
    )

    assert len(creators) > 0
    for creator in creators:
        assert creator.estimated_price_inr <= ceiling
