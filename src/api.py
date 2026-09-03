from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.extractor import extract_campaign_requirements
from src.agent import investigate_campaign
from src.synthesizer import synthesize_recommendations
from src.models import CampaignResult


app = FastAPI(title="CreatorLens")


class CampaignRequest(BaseModel):
    brief: str


@app.post("/campaign", response_model=CampaignResult)
def create_campaign(request: CampaignRequest):
    try:
        campaign = extract_campaign_requirements(request.brief)

        investigations = investigate_campaign(campaign)

        recommendations = synthesize_recommendations(
            campaign,
            investigations,
        )

        return CampaignResult(
            campaign=campaign,
            recommendations=recommendations,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Campaign analysis failed.",
        ) from exc