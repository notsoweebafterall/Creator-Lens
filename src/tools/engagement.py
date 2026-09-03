from src.models import Creator


def compute_engagement(creator: Creator) -> float:
    if creator.avg_views <= 0:
        return 0.0

    engagement = (
        (creator.avg_likes + creator.avg_comments)
        / creator.avg_views
    ) * 100

    return round(engagement, 2)