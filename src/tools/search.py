import sqlite3

from src.config import settings
from src.models import Creator


def search_creators(
    niche: str | None = None,
    platform: str | None = None,
    geography: str | None = None,
    limit: int = 10,
) -> list[Creator]:
    connection = sqlite3.connect(settings.db_file)
    connection.row_factory = sqlite3.Row

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

    query += " LIMIT ?"
    params.append(limit)

    rows = connection.execute(query, params).fetchall()
    connection.close()

    return [Creator(**dict(row)) for row in rows]