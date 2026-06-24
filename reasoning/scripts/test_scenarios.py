import json
import requests
from pathlib import Path

REASONING_API = "http://localhost:8000/analyze"
MOCK_DIR = Path(__file__).parent.parent.parent / "shared" / "mock"

scenarios = [
    MOCK_DIR / "scenario1_aligned.json",
    MOCK_DIR / "scenario2_scope_creep.json",
    MOCK_DIR / "scenario3_policy_violation.json",
]

for path in scenarios:
    data = json.loads(path.read_text())
    print(f"\n{'─' * 60}")
    print(f"▶  {data['label']}")
    print("─" * 60)

    try:
        response = requests.post(REASONING_API, json={
            "intent": data["intent"],
            "execution": data["execution"],
        })
        result = response.json()
        if response.ok:
            print(f"Drift detected : {result['drift_detected']}")
            print(f"Severity       : {result['severity']}")
            print(f"Reasoning      : {result['reasoning']}")
        else:
            print(f"ERROR          : {result}")
    except Exception as e:
        print(f"ERROR          : {e}")
