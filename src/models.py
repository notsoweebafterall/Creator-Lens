from typing import Literal

from pydantic import BaseModel, Field


class CampaignRequirements(BaseModel):
    niche: str
    budget: float | None = None
    target_age_min: int | None = None
    target_age_max: int | None = None
    geography: str | None = None
    platform: str | None = None
    campaign_goal: str | None = None


class Creator(BaseModel):
    creator_id: str
    name: str
    platform: str
    niche: str
    followers: int
    avg_views: int
    avg_likes: int
    avg_comments: int
    audience_age_18_24: float
    audience_age_25_34: float
    geography: str
    brand_safety_status: str


class Evidence(BaseModel):
    type: Literal["retrieved_fact", "calculated_metric", "model_judgment"]
    claim: str
    source: str


class CreatorInvestigation(BaseModel):
    creator_id: str
    creator_name: str
    evidence: list[Evidence] = Field(default_factory=list)


class CreatorRecommendation(BaseModel):
    creator_id: str
    creator_name: str
    score: float
    evidence: list[Evidence] = Field(default_factory=list)
    recommendation: str


class CampaignResult(BaseModel):
    campaign: CampaignRequirements
    recommendations: list[CreatorRecommendation]