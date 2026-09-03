import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.extractor import extract_campaign_requirements
from src.agent import investigate_campaign
from src.synthesizer import synthesize_recommendations


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="CreatorLens",
    page_icon="🔎",
    layout="wide",
)


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        .hero-title {
            font-size: 3.2rem;
            font-weight: 750;
            margin-bottom: 0.2rem;
        }

        .hero-subtitle {
            color: #9ca3af;
            font-size: 1.05rem;
            margin-bottom: 2rem;
        }

        .creator-card {
            border: 1px solid #30333b;
            border-radius: 14px;
            padding: 1.4rem;
            margin-bottom: 1rem;
            background: #101116;
        }

        .creator-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .creator-name {
            font-size: 1.45rem;
            font-weight: 650;
        }

        .creator-score {
            font-size: 1.7rem;
            font-weight: 700;
        }

        .metric-label {
            color: #9ca3af;
            font-size: 0.85rem;
            margin-bottom: 0.15rem;
        }

        .metric-value {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .safe {
            color: #4ade80;
            font-weight: 700;
        }

        .review {
            color: #facc15;
            font-weight: 700;
        }

        .unsafe {
            color: #f87171;
            font-weight: 700;
        }

        .evidence-source {
            color: #8b949e;
            font-size: 0.8rem;
        }

        div[data-testid="stMetric"] {
            padding: 0.2rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    '<div class="hero-title">🔎 CreatorLens</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-subtitle">'
    "AI-powered creator campaign intelligence"
    "</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Campaign input
# ---------------------------------------------------------

st.subheader("Campaign Brief")

brief = st.text_area(
    "Describe the campaign you want to build.",
    placeholder=(
        "Example: A fintech brand wants an Instagram awareness "
        "campaign in India targeting users aged 18 to 30 "
        "with a budget of 500000 INR."
    ),
    height=150,
    label_visibility="collapsed",
)


analyze = st.button(
    "Analyze Campaign",
    type="primary",
    use_container_width=False,
)


# ---------------------------------------------------------
# Pipeline
# ---------------------------------------------------------

if analyze:

    if not brief.strip():
        st.warning("Please enter a campaign brief.")
        st.stop()

    with st.spinner("Analyzing campaign and evaluating creators..."):

        campaign = extract_campaign_requirements(brief)

        investigations = investigate_campaign(campaign)

        recommendations = synthesize_recommendations(
            campaign,
            investigations,
        )


    # -----------------------------------------------------
    # Campaign requirements
    # -----------------------------------------------------

    st.divider()

    st.subheader("Campaign Requirements")

    requirement_cols = st.columns(6)

    requirement_cols[0].metric(
        "Niche",
        campaign.niche or "—",
    )

    requirement_cols[1].metric(
        "Platform",
        campaign.platform or "—",
    )

    requirement_cols[2].metric(
        "Geography",
        campaign.geography or "—",
    )

    if (
        campaign.target_age_min is not None
        and campaign.target_age_max is not None
    ):
        target_age = (
            f"{campaign.target_age_min}–"
            f"{campaign.target_age_max}"
        )
    else:
        target_age = "—"

    requirement_cols[3].metric(
        "Target Age",
        target_age,
    )

    if campaign.budget is not None:
        budget = f"₹{campaign.budget:,.0f}"
    else:
        budget = "—"

    requirement_cols[4].metric(
        "Budget",
        budget,
    )

    requirement_cols[5].metric(
        "Goal",
        campaign.campaign_goal or "—",
    )


    # -----------------------------------------------------
    # Recommendations
    # -----------------------------------------------------

    st.divider()

    st.subheader("Creator Recommendations")

    for rank, recommendation in enumerate(
        recommendations,
        start=1,
    ):

        # ---------------------------------------------
        # Extract evidence for compact card display
        # ---------------------------------------------

        engagement = "—"
        audience_fit = "—"
        brand_safety = "—"

        for evidence in recommendation.evidence:

            if evidence.source == "compute_engagement":
                engagement = evidence.claim.replace(
                    "Engagement rate: ",
                    "",
                )

            elif evidence.source == "audience_fit_score":
                raw_score = evidence.claim.replace(
                    "Audience fit score: ",
                    "",
                ).strip()

                try:
                    if raw_score.endswith("%"):
                        audience_fit = raw_score
                    else:
                        audience_fit = f"{float(raw_score) * 100:.0f}%"
                except ValueError:
                    audience_fit = raw_score

            elif evidence.source == "check_brand_safety":

                claim = evidence.claim.upper()

                if "UNSAFE" in claim:
                    brand_safety = "UNSAFE"

                elif "REVIEW" in claim:
                    brand_safety = "REVIEW"

                elif "SAFE" in claim:
                    brand_safety = "SAFE"


        # ---------------------------------------------
        # Brand safety styling
        # ---------------------------------------------

        if brand_safety == "SAFE":
            safety_display = (
                '<span class="safe">🟢 SAFE</span>'
            )

        elif brand_safety == "REVIEW":
            safety_display = (
                '<span class="review">🟡 REVIEW</span>'
            )

        elif brand_safety == "UNSAFE":
            safety_display = (
                '<span class="unsafe">🔴 UNSAFE</span>'
            )

        else:
            safety_display = "—"


        # ---------------------------------------------
        # Creator card
        # ---------------------------------------------

        with st.container(border=True):

            header_col, score_col = st.columns(
                [5, 1],
            )

            with header_col:

                st.markdown(
                    f"""
                    <div class="creator-name">
                        #{rank} &nbsp; {recommendation.creator_name}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with score_col:

                st.markdown(
                    f"""
                    <div class="metric-label">Score</div>
                    <div class="creator-score">
                        {recommendation.score:.0f}/100
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


            st.write(
                recommendation.recommendation
            )


            # -----------------------------------------
            # Key metrics
            # -----------------------------------------

            metric_cols = st.columns(3)

            with metric_cols[0]:
                st.markdown(
                    f"""
                    <div class="metric-label">
                        Engagement
                    </div>
                    <div class="metric-value">
                        📈 {engagement}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with metric_cols[1]:
                st.markdown(
                    f"""
                    <div class="metric-label">
                        Audience Fit
                    </div>
                    <div class="metric-value">
                        🎯 {audience_fit}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with metric_cols[2]:
                st.markdown(
                    f"""
                    <div class="metric-label">
                        Brand Safety
                    </div>
                    <div class="metric-value">
                        {safety_display}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


            # -----------------------------------------
            # Evidence
            # -----------------------------------------

            with st.expander("View Evidence"):

                for evidence in recommendation.evidence:

                    if evidence.type == "retrieved_fact":
                        label = "📘 Retrieved fact"

                    elif evidence.type == "calculated_metric":
                        label = "📊 Calculated metric"

                    else:
                        label = "🤖 Model judgment"

                    st.markdown(
                        f"**{label}**"
                    )

                    st.write(
                        evidence.claim
                    )

                    st.markdown(
                        f"""
                        <div class="evidence-source">
                            Source: {evidence.source}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.divider()