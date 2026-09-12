from collections import defaultdict
from google.genai import types

from src.config import settings
from src.llm import call_gemini_with_retry, gemini_client
from src.logging_utils import log_llm_event
from src.models import (
    CampaignRequirements,
    Creator,
    CreatorInvestigation,
    Evidence,
)
from src.tools.audience import audience_fit_score
from src.tools.engagement import compute_engagement
from src.tools.safety import check_brand_safety
from src.tools.search import search_creators

MAX_CANDIDATES = 5


def search_creators_tool(
    niche: str | None = None,
    platform: str | None = None,
    geography: str | None = None,
    max_price_inr: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search the creator database using campaign filters and optional budget ceiling in INR (integer number, e.g. 100000).
    """
    creators = search_creators(
        niche=niche,
        platform=platform,
        geography=geography,
        max_price_inr=max_price_inr,
        limit=limit,
    )
    creators = creators[:MAX_CANDIDATES]
    return [creator.model_dump() for creator in creators]


def compute_engagement_tool(creator_dict: dict) -> dict:
    """
    Compute engagement rate percentage for a creator.
    Returns dict with 'rate' and 'is_fallback'.
    """
    cid = creator_dict.get("creator_id", "UNKNOWN") if isinstance(creator_dict, dict) else "UNKNOWN"
    try:
        creator = Creator.model_validate(creator_dict)
        return {"rate": compute_engagement(creator), "is_fallback": False}
    except Exception:
        log_llm_event(
            purpose=f"fallback_placeholder_data:compute_engagement_tool:{cid}",
            model="none",
            status="warning",
            latency_seconds=0.0,
        )
        followers = creator_dict.get("followers", 1) if isinstance(creator_dict, dict) else 1
        likes = creator_dict.get("avg_likes", 0) if isinstance(creator_dict, dict) else 0
        comments = creator_dict.get("avg_comments", 0) if isinstance(creator_dict, dict) else 0
        views = creator_dict.get("avg_views", 0) if isinstance(creator_dict, dict) else 0
        rate = 0.0 if followers <= 0 else round(((likes + comments + (views * 0.1)) / followers) * 100, 2)
        return {"rate": rate, "is_fallback": True}


def audience_fit_score_tool(
    creator_dict: dict,
    target_age_min: int,
    target_age_max: int,
) -> dict:
    """
    Compute audience age demographic fit score (0.0 to 1.0) for a creator.
    Returns dict with 'score' and 'is_fallback'.
    """
    cid = creator_dict.get("creator_id", "UNKNOWN") if isinstance(creator_dict, dict) else "UNKNOWN"
    try:
        creator = Creator.model_validate(creator_dict)
        return {"score": audience_fit_score(creator, target_age_min, target_age_max), "is_fallback": False}
    except Exception:
        log_llm_event(
            purpose=f"fallback_placeholder_data:audience_fit_score_tool:{cid}",
            model="none",
            status="warning",
            latency_seconds=0.0,
        )
        a18 = creator_dict.get("audience_age_18_24", 0.5) if isinstance(creator_dict, dict) else 0.5
        a25 = creator_dict.get("audience_age_25_34", 0.5) if isinstance(creator_dict, dict) else 0.5
        return {"score": round(float(a18 + a25), 2), "is_fallback": True}


def check_brand_safety_tool(creator_dict: dict) -> dict:
    """
    Check brand safety for a creator using RAG retrieval against brand safety guidelines.
    Returns a SafetyVerdict dictionary with 'is_fallback' flag.
    """
    cid = creator_dict.get("creator_id", "C000") if isinstance(creator_dict, dict) else "C000"
    is_fallback = False
    try:
        creator = Creator.model_validate(creator_dict)
    except Exception:
        log_llm_event(
            purpose=f"fallback_placeholder_data:check_brand_safety_tool:{cid}",
            model="none",
            status="warning",
            latency_seconds=0.0,
        )
        is_fallback = True
        creator = Creator(
            creator_id=cid,
            name=creator_dict.get("name", "Unknown Creator") if isinstance(creator_dict, dict) else "Unknown Creator",
            platform=creator_dict.get("platform", "Instagram") if isinstance(creator_dict, dict) else "Instagram",
            niche=creator_dict.get("niche", "general") if isinstance(creator_dict, dict) else "general",
            followers=creator_dict.get("followers", 10000) if isinstance(creator_dict, dict) else 10000,
            avg_likes=creator_dict.get("avg_likes", 100) if isinstance(creator_dict, dict) else 100,
            avg_comments=creator_dict.get("avg_comments", 10) if isinstance(creator_dict, dict) else 10,
            avg_views=creator_dict.get("avg_views", 1000) if isinstance(creator_dict, dict) else 1000,
            audience_age_18_24=creator_dict.get("audience_age_18_24", 0.5) if isinstance(creator_dict, dict) else 0.5,
            audience_age_25_34=creator_dict.get("audience_age_25_34", 0.5) if isinstance(creator_dict, dict) else 0.5,
            geography=creator_dict.get("geography", "India") if isinstance(creator_dict, dict) else "India",
            estimated_price_inr=creator_dict.get("estimated_price_inr", 10000) if isinstance(creator_dict, dict) else 10000,
            content_summary=creator_dict.get("content_summary", "") if isinstance(creator_dict, dict) else "",
            previous_brand_categories=creator_dict.get("previous_brand_categories", []) if isinstance(creator_dict, dict) else [],
        )
    verdict = check_brand_safety(creator)
    v_dict = verdict.model_dump()
    v_dict["is_fallback"] = is_fallback
    return v_dict


TOOLS = [
    search_creators_tool,
    compute_engagement_tool,
    audience_fit_score_tool,
    check_brand_safety_tool,
]


def investigate_campaign(
    campaign: CampaignRequirements,
    max_turns: int = 8,
) -> list[CreatorInvestigation]:

    budget_ceiling = (
        int(campaign.budget_inr / campaign.min_creators)
        if campaign.budget_inr
        else None
    )

    system_instruction = f"""
You are CreatorLens, an intelligent AI creator campaign investigation agent.

Campaign Requirements:
{campaign.model_dump_json(indent=2)}

Budget Ceiling per creator (if applicable): {budget_ceiling}

Your goal:
1. ALWAYS call search_creators_tool first to find candidates matching the campaign filters (niche="{campaign.niche}", platform="{campaign.platform}", geography="{campaign.geography}", max_price_inr={budget_ceiling}).
2. For each candidate returned, evaluate them using the analysis tools:
   - compute_engagement_tool: to measure creator engagement rate.
   - audience_fit_score_tool: to assess target audience demographic fit (if age bounds are requested).
   - check_brand_safety_tool: to analyze brand safety risk against safety guidelines.
3. Dynamically decide which tools to call per candidate based on their specific profile and missing evidence (e.g. skip demographic check if no age target specified, or prioritize safety check for creators in financial/crypto categories).
4. Once you have gathered sufficient evidence for candidate creators, conclude your investigation and summarize your findings.
"""

    contents = ["Begin campaign investigation."]

    investigations_map: dict[str, CreatorInvestigation] = {}
    candidate_tool_calls: dict[str, list[str]] = defaultdict(list)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    turn = 0
    while turn < max_turns:
        turn += 1

        response, model_used = call_gemini_with_retry(
            lambda: gemini_client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=config,
            ),
            purpose=f"agent_turn_{turn}",
            model=settings.gemini_model,
        )

        if not response.function_calls:
            break

        contents.append(response.candidates[0].content)

        tool_response_parts = []
        for call in response.function_calls:
            tool_name = call.name
            args = call.args or {}

            if tool_name == "search_creators_tool":
                results = search_creators_tool(**args)
                for c_dict in results:
                    cid = c_dict["creator_id"]
                    if cid not in investigations_map:
                        investigations_map[cid] = CreatorInvestigation(
                            creator_id=cid,
                            creator_name=c_dict["name"],
                            evidence=[
                                Evidence(
                                    type="retrieved_fact",
                                    claim=f"{c_dict['name']} is a {c_dict['niche']} creator on {c_dict['platform']} in {c_dict['geography']} (price ₹{c_dict.get('estimated_price_inr', 0)}).",
                                    source="search_creators",
                                )
                            ],
                        )
                        candidate_tool_calls[cid].append("search_creators")
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name, response={"result": results}
                    )
                )

            elif tool_name == "compute_engagement_tool":
                c_dict = args.get("creator_dict", args)
                cid = c_dict.get("creator_id") if isinstance(c_dict, dict) else None
                eng_res = compute_engagement_tool(c_dict)
                rate = eng_res["rate"]
                is_fb = eng_res["is_fallback"]
                claim_text = f"Engagement rate: {rate}%."
                if is_fb:
                    claim_text = f"[ESTIMATED - validation fallback] {claim_text}"
                if cid and cid in investigations_map:
                    investigations_map[cid].evidence.append(
                        Evidence(
                            type="calculated_metric",
                            claim=claim_text,
                            source="compute_engagement",
                        )
                    )
                    candidate_tool_calls[cid].append("compute_engagement")
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name, response={"result": rate}
                    )
                )

            elif tool_name == "audience_fit_score_tool":
                c_dict = args.get("creator_dict", {})
                cid = c_dict.get("creator_id") if isinstance(c_dict, dict) else None
                t_min = args.get("target_age_min", campaign.target_age_min or 18)
                t_max = args.get("target_age_max", campaign.target_age_max or 34)
                fit_res = audience_fit_score_tool(c_dict, t_min, t_max)
                score = fit_res["score"]
                is_fb = fit_res["is_fallback"]
                claim_text = f"Audience fit score: {score}."
                if is_fb:
                    claim_text = f"[ESTIMATED - validation fallback] {claim_text}"
                if cid and cid in investigations_map:
                    investigations_map[cid].evidence.append(
                        Evidence(
                            type="calculated_metric",
                            claim=claim_text,
                            source="audience_fit_score",
                        )
                    )
                    candidate_tool_calls[cid].append("audience_fit_score")
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name, response={"result": score}
                    )
                )

            elif tool_name == "check_brand_safety_tool":
                c_dict = args.get("creator_dict", {})
                cid = c_dict.get("creator_id") if isinstance(c_dict, dict) else None
                verdict_dict = check_brand_safety_tool(c_dict)
                is_fb = verdict_dict.get("is_fallback", False)
                claim_text = f"Brand safety risk: {verdict_dict['risk_level']}. Reasoning: {verdict_dict['reasoning']}"
                if is_fb:
                    claim_text = f"[ESTIMATED - validation fallback] {claim_text}"
                if cid and cid in investigations_map:
                    investigations_map[cid].evidence.append(
                        Evidence(
                            type="model_judgment",
                            claim=claim_text,
                            source="check_brand_safety",
                        )
                    )
                    candidate_tool_calls[cid].append("check_brand_safety")
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name, response={"result": verdict_dict}
                    )
                )

        contents.append(types.Content(role="user", parts=tool_response_parts))

    print("\n--- AGENT INVESTIGATION TOOL SUMMARY ---")
    for cid, tools in candidate_tool_calls.items():
        print(f"Candidate {cid}: {tools}")

    results = list(investigations_map.values())
    for inv in results:
        inv.tool_sequence = candidate_tool_calls.get(inv.creator_id, [])

    return results