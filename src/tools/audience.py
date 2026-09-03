from src.models import Creator


def audience_fit_score(
    creator: Creator,
    target_age_min: int,
    target_age_max: int,
) -> float:
    if target_age_min >= 25 and target_age_max <= 34:
        score = creator.audience_age_25_34

    elif target_age_min >= 18 and target_age_max <= 24:
        score = creator.audience_age_18_24

    elif target_age_min < 25 and target_age_max > 24:
        score = (
            creator.audience_age_18_24
            + creator.audience_age_25_34
        )

    else:
        score = 0.0

    return round(score, 3)