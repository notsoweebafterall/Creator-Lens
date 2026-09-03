import json
from datetime import datetime, timezone
from pathlib import Path


LOG_FILE = Path("logs/llm.jsonl")


def log_llm_event(
    provider: str,
    status: str,
    latency_seconds: float,
):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "status": status,
        "latency_seconds": round(latency_seconds, 3),
    }

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")