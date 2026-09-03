import json
from pathlib import Path

from src.extractor import extract_campaign_requirements


def run_extraction_eval():
    path = Path("tests/eval_data/extraction_cases.json")

    cases = json.loads(path.read_text(encoding="utf-8"))

    total = 0
    correct = 0

    for case in cases:
        result = extract_campaign_requirements(case["brief"])
        expected = case["expected"]

        for field, expected_value in expected.items():
            total += 1

            actual_value = getattr(result, field)

            if actual_value == expected_value:
                correct += 1

    accuracy = correct / total if total else 0.0

    print(f"Extraction accuracy: {accuracy:.2%}")
    print(f"Correct fields: {correct}/{total}")

    return accuracy


if __name__ == "__main__":
    run_extraction_eval()