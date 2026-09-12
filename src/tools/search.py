import sqlite3

from src.config import settings
from src.models import Creator


def search_creators(
    niche: str | None = None,
    platform: str | None = None,
    geography: str | None = None,
    max_price_inr: int | None = None,
    limit: int = 10,
) -> list[Creator]:
    connection = sqlite3.connect(settings.db_file)
    connection.row_factory = sqlite3.Row

    if isinstance(niche, dict):
        niche = niche.get("exact") or niche.get("value") or niche.get("eq") or (list(niche.values())[0] if niche else None)
    if isinstance(platform, dict):
        platform = platform.get("exact") or platform.get("value") or platform.get("eq") or (list(platform.values())[0] if platform else None)
    if isinstance(geography, dict):
        geography = geography.get("exact") or geography.get("value") or geography.get("eq") or (list(geography.values())[0] if geography else None)
    if isinstance(max_price_inr, dict):
        max_price_inr = max_price_inr.get("lte") or max_price_inr.get("max") or max_price_inr.get("value") or (list(max_price_inr.values())[0] if max_price_inr else None)
    if max_price_inr is not None:
        try:
            max_price_inr = int(max_price_inr)
        except (ValueError, TypeError):
            max_price_inr = None

    query = "SELECT * FROM creators WHERE 1=1"
    params = []

    if niche:
        query += " AND LOWER(niche) = LOWER(?)"
        params.append(niche)

    if platform:
        query += " AND LOWER(platform) = LOWER(?)"
        params.append(platform)

    if geography:
        query += " AND LOWER(geography) = LOWER(?)"
        params.append(geography)

    # Budget ceiling heuristic: max_price_inr = budget_inr / min_creators
    if max_price_inr is not None:
        query += " AND estimated_price_inr <= ?"
        params.append(max_price_inr)

    query += " LIMIT ?"
    params.append(limit)

    rows = connection.execute(query, params).fetchall()
    connection.close()

    return [Creator(**dict(row)) for row in rows]