import json
from pathlib import Path

from src.rag.retrieve import retrieve_guidelines


def run_retrieval_eval():
    path = Path("tests/eval_data/retrieval_cases.json")

    cases = json.loads(path.read_text(encoding="utf-8"))

    total = 0
    correct = 0

    for case in cases:
        results = retrieve_guidelines(
            case["query"],
            top_k=3,
        )

        expected_source = case["expected_source"]

        sources = [
            result["source"]
            for result in results
        ]

        total += 1

        if expected_source in sources:
            correct += 1

    precision_at_3 = correct / total if total else 0.0

    print(f"Retrieval Precision@3: {precision_at_3:.2%}")
    print(f"Queries with correct source in top 3: {correct}/{total}")

    return precision_at_3


if __name__ == "__main__":
    run_retrieval_eval()