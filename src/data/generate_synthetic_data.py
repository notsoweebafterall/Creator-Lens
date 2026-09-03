import random
import sqlite3
from pathlib import Path

import pandas as pd


random.seed(42)

OUTPUT_CSV = Path("data/creators.csv")
OUTPUT_DB = Path("data/creators.db")


NICHES = [
    "fintech",
    "finance",
    "technology",
    "fitness",
    "beauty",
    "gaming",
    "fashion",
    "food",
    "travel",
    "education",
]

PLATFORMS = ["Instagram", "YouTube"]

GEOGRAPHIES = [
    "India",
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Hyderabad",
    "Pune",
]

SAFETY_STATUSES = [
    "clean",
    "clean",
    "clean",
    "clean",
    "review",
    "unsafe",
]


def make_creator(
    creator_id: int,
    niche: str | None = None,
    platform: str | None = None,
    geography: str | None = None,
) -> dict:

    niche = niche or random.choice(NICHES)
    platform = platform or random.choice(PLATFORMS)
    geography = geography or random.choice(GEOGRAPHIES)

    followers = random.randint(
        10_000,
        2_000_000,
    )

    avg_views = int(
        followers * random.uniform(0.15, 0.75)
    )

    avg_likes = int(
        avg_views * random.uniform(0.02, 0.09)
    )

    avg_comments = int(
        avg_views * random.uniform(0.002, 0.02)
    )

    age_18_24 = round(
        random.uniform(0.15, 0.70),
        2,
    )

    age_25_34 = round(
        random.uniform(
            0.15,
            min(0.70, 0.95 - age_18_24),
        ),
        2,
    )

    return {
        "creator_id": f"C{creator_id:03d}",
        "name": f"Creator {creator_id:03d}",
        "platform": platform,
        "niche": niche,
        "followers": followers,
        "avg_views": avg_views,
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "audience_age_18_24": age_18_24,
        "audience_age_25_34": age_25_34,
        "geography": geography,
        "brand_safety_status": random.choice(
            SAFETY_STATUSES
        ),
    }


def main():

    creators = []

    creator_id = 1

    # -----------------------------------------
    # Guaranteed fintech demo candidates
    # -----------------------------------------
    for _ in range(10):
        creators.append(
            make_creator(
                creator_id,
                niche="fintech",
                platform="Instagram",
                geography="India",
            )
        )
        creator_id += 1

    # -----------------------------------------
    # Guaranteed finance candidates
    # -----------------------------------------
    for _ in range(10):
        creators.append(
            make_creator(
                creator_id,
                niche="finance",
                platform="Instagram",
                geography="India",
            )
        )
        creator_id += 1

    # -----------------------------------------
    # Remaining diverse creators
    # -----------------------------------------
    while creator_id <= 150:
        creators.append(
            make_creator(creator_id)
        )
        creator_id += 1

    df = pd.DataFrame(creators)

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    connection = sqlite3.connect(
        OUTPUT_DB
    )

    df.to_sql(
        "creators",
        connection,
        if_exists="replace",
        index=False,
    )

    connection.close()

    print(
        f"Saved {len(df)} creators."
    )

    print(
        "Guaranteed fintech/Instagram/India:",
        len(
            df[
                (df["niche"] == "fintech")
                & (df["platform"] == "Instagram")
                & (df["geography"] == "India")
            ]
        ),
    )

    print(
        f"CSV: {OUTPUT_CSV}"
    )

    print(
        f"SQLite: {OUTPUT_DB}"
    )


if __name__ == "__main__":
    main()