from google import genai
from google.genai import types

from src.config import settings
from src.models import (
    CampaignRequirements,
    CreatorInvestigation,
    Evidence,
)
from src.tools.search import search_creators
from src.tools.engagement import compute_engagement
from src.tools.audience import audience_fit_score
from src.tools.safety import check_brand_safety

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

client = genai.Client(api_key=settings.gemini_api_key)

MAX_CANDIDATES = 3


def search_creators_tool(
    niche: str,
    platform: str,
    geography: str,
    limit: int = 10,
) -> list[dict]:
    """
    Search the creator database using exact campaign filters.
    """
    creators = search_creators(
        niche=niche,
        platform=platform,
        geography=geography,
        limit=limit,
    )

    creators = creators[:MAX_CANDIDATES]

    print(f"[Tool] search_creators -> {len(creators)} candidates")

    return [creator.model_dump() for creator in creators]


TOOLS = [search_creators_tool]


def investigate_campaign(
    campaign: CampaignRequirements,
    max_steps: int = 2,
) -> list[CreatorInvestigation]:

    system_instruction = f"""
You are CreatorLens, an AI creator campaign investigation agent.

Campaign:
{campaign.model_dump_json(indent=2)}

Your ONLY task is to search the creator database.

You MUST call search_creators_tool exactly once using:

niche = "{campaign.niche}"
platform = "{campaign.platform}"
geography = "{campaign.geography}"

NEVER broaden or modify these filters.

After receiving the search results:
- Do not call any other tools.
- Do not invent information.
- Return a concise summary of the creators found.
"""

    print("\n[Agent] Starting investigation...")

    chat = client.chats.create(
        model=settings.gemini_model,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=TOOLS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=max_steps,
            ),
        ),
    )

    try:
        response = chat.send_message(
            "Begin the investigation."
        )

    except Exception as exc:
        print(f"[Agent] Gemini failed: {exc}")
        print("[Agent] Falling back to Groq...")

        groq_response = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": "Begin the investigation.",
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "search_creators_tool",
                        "description": "Search the creator database using exact campaign filters.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "niche": {"type": "string"},
                                "platform": {"type": "string"},
                                "geography": {"type": "string"},
                                "limit": {"type": "integer"},
                            },
                            "required": ["niche", "platform", "geography"],
                        },
                    },
                }
            ],
            tool_choice="required",
        )

        tool_call = groq_response.choices[0].message.tool_calls[0]

        import json

        arguments = json.loads(tool_call.function.arguments)

        tool_result = search_creators_tool(**arguments)

        groq_response = groq_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {
                    "role": "user",
                    "content": "Begin the investigation.",
                },
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                },
            ],
        )

        class GroqResponse:
            text = groq_response.choices[0].message.content

        response = GroqResponse()

        print("[Agent] Groq fallback succeeded.")

    print("\n[Agent] Search complete.")

    if response.text:
        print("\n--- AGENT SUMMARY ---")
        print(response.text)

    # ---------------------------------------------------------
    # Deterministic investigation
    # ---------------------------------------------------------

    candidates = search_creators(
        niche=campaign.niche,
        platform=campaign.platform,
        geography=campaign.geography,
        limit=MAX_CANDIDATES,
    )

    investigations = []

    for creator in candidates:

        evidence = []

        # Retrieved fact
        evidence.append(
            Evidence(
                type="retrieved_fact",
                claim=(
                    f"{creator.name} is a {creator.niche} creator "
                    f"on {creator.platform} in {creator.geography}."
                ),
                source="search_creators",
            )
        )

        # Calculated engagement
        engagement = compute_engagement(creator)

        evidence.append(
            Evidence(
                type="calculated_metric",
                claim=f"Engagement rate: {engagement}%.",
                source="compute_engagement",
            )
        )

        # Calculated audience fit
        if (
            campaign.target_age_min is not None
            and campaign.target_age_max is not None
        ):
            audience_score = audience_fit_score(
                creator,
                campaign.target_age_min,
                campaign.target_age_max,
            )

            evidence.append(
                Evidence(
                    type="calculated_metric",
                    claim=f"Audience fit score: {audience_score}.",
                    source="audience_fit_score",
                )
            )

        # Brand safety
        safety = check_brand_safety(creator)

        evidence.append(
            Evidence(
                type="model_judgment",
                claim=f"Brand safety: {safety}",
                source="check_brand_safety",
            )
        )

        investigations.append(
            CreatorInvestigation(
                creator_id=creator.creator_id,
                creator_name=creator.name,
                evidence=evidence,
            )
        )

    return investigations