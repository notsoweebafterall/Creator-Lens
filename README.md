# 🔎 CreatorLens: Creator Campaign Intelligence

CreatorLens is an AI system for creator campaign intelligence, built around ONE genuine tool-calling agent plus deterministic and structured-LLM components — not a stack of agents for the sake of it. It processes unstructured campaign briefs, investigates synthetic creator profiles, runs RAG-based brand safety checks, and returns ranked, evidence-backed creator shortlists.

---

## 🎯 Architecture Overview

```text
               Unstructured Campaign Brief
                           │
                           ▼
              ┌─────────────────────────┐
              │ Brief Extractor (LLM)   │ ──(Clarification Check)
              └────────────┬────────────┘
                           │ CampaignRequirements
                           ▼
          ┌──────────────────────────────────┐
          │ Investigation Agent (Tool-Loop)  │
          └────────────────┬─────────────────┘
                           │ Emergent Function Calls
          ┌────────────────┼──────────────────┬─────────────────┐
          ▼                ▼                  ▼                 ▼
   search_creators compute_engagement audience_fit_score check_brand_safety
   (SQLite Filter)  (Pandas Calc)      (Demographic)      (RAG / Vector)
          └────────────────┬──────────────────┴─────────────────┘
                           │ CreatorInvestigation[]
                           ▼
              ┌─────────────────────────┐
              │ Recommendation          │
              │ Synthesizer (LLM)       │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Unknown-Risk Guard      │ ──(Deterministic Safety Demotion)
              └────────────┬────────────┘
                           │
                           ▼
               Ranked Final Shortlist
```

### Why standard multi-agent setups fail & why Investigation Agent is a "real" agent
Unlike standard linear pipelines, the **Investigation Agent** operates in an autonomous tool-calling loop:
1. **Deterministic Baseline**: Begins with `search_creators` using a budget ceiling (`budget_inr / min_creators`) to pull candidate matches.
2. **Emergent Tool Selection**: Per candidate, the model dynamically chooses which tools to invoke (`compute_engagement`, `audience_fit_score`, `check_brand_safety`). Tool-calling sequences vary based on creator data, avoiding wasted tokens on low-fit candidates.
3. **Traceability**: Every claim in the final recommendation is explicitly tagged as a **Retrieved Fact**, **Calculated Metric**, or **Model Judgment**.

---

## 🛡️ Safety & Deterministic Guard

- **RAG Safety Evaluation**: `check_brand_safety` queries ChromaDB (using local `all-MiniLM-L6-v2` embeddings with zero API cost) for brand guidelines matching creator content summaries & past brand partnerships, returning a structured `SafetyVerdict`.
- **Unknown Risk Guard**: A deterministic post-processing guard (`enforce_unknown_risk_guard`) demotes any creator with unverified safety status if their score is close to (within 10 points of) a verified-safe creator.

---

## 📊 Instrumentation & Observability

Every LLM call across all components is instrumented and logged to `logs/llm_calls.jsonl` with:
- Purpose (`extractor`, `agent`, `safety`, `synthesizer`)
- Model identifier (e.g. `gemini-3.1-flash-lite`, `groq/llama-3.3-70b-versatile`)
- Status (`success`, `retry_success`, `fallback_groq_success`, `error`)
- Latency (seconds)
- Token counts (`input_tokens`, `output_tokens`, `total_tokens`)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Gemini API Key (and optional Groq API key for fallback)

### Local Installation
```bash
# Clone and enter repo (or navigate to project folder)
git clone https://github.com/notsoweebafterall/Creator-Lens.git
cd Creator-Lens

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
echo "GEMINI_MODEL=gemini-3.1-flash-lite" >> .env
```

### Ingest Brand Safety Guidelines
```bash
python -m src.rag.ingest
```

### Running Tests
```bash
pytest -s
```

### Running Streamlit UI Demo
```bash
streamlit run src/ui.py
```
*Note: `src/ui.py` is provided for interactive web UI demonstration.*

---

## 🐳 Docker Support

Run CreatorLens inside a container using Docker:

```bash
# Build Docker image
docker build -t creator-lens .

# Run test suite in container
docker run --env-file .env creator-lens

# Run UI container (exposing port 8501)
docker run --env-file .env -p 8501:8501 creator-lens streamlit run src/ui.py
```

---

## 🛠️ Technology Stack
- **LLM Provider**: Google Gemini (`google-genai` SDK) as primary provider with exponential backoff retry; Groq (`openai` SDK compatible endpoint) as transparent same-call fallback after retries are exhausted.
- **Model Traceability**: Every output object (`CampaignRequirements`, `SafetyVerdict`, `CreatorRecommendation`) records the exact `model_used` that answered.
- **Vector DB / RAG**: ChromaDB + local sentence-transformers embeddings (`all-MiniLM-L6-v2`, no API cost).
- **Database**: SQLite (150 synthetic creators).
- **Data Validation**: Pydantic v2.
- **UI Framework**: Streamlit.