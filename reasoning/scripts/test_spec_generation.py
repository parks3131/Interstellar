"""
Test spec generation using scenario2 (scope creep) mock data.
No server or live credentials required — only OPENROUTER_API_KEY.
"""

import json
import os
import sys
from pathlib import Path

# Run from the reasoning/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from openai import OpenAI
from models import IntentObject, ExecutionObject, DriftAnalysis, RemediationSpec

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")

DRIFT_PROMPT = (Path(__file__).parent.parent / "prompts/drift_detection.txt").read_text()
SPEC_PROMPT  = (Path(__file__).parent.parent / "prompts/spec_generation.txt").read_text()

MOCK = Path(__file__).parent.parent.parent / "shared/mock/scenario2_scope_creep.json"
data = json.loads(MOCK.read_text())

intent    = IntentObject(**data["intent"])
execution = ExecutionObject(**data["execution"])

print("=== Step 1: Drift Detection ===")
resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=512,
    messages=[
        {"role": "system", "content": DRIFT_PROMPT},
        {"role": "user", "content": f"IntentObject:\n{intent.model_dump_json(indent=2)}\n\nExecutionObject:\n{execution.model_dump_json(indent=2)}"},
    ],
)
drift = DriftAnalysis(**json.loads(resp.choices[0].message.content.strip()))
print(f"drift_detected : {drift.drift_detected}")
print(f"severity       : {drift.severity}")
print(f"reasoning      : {drift.reasoning}")

if not drift.drift_detected:
    print("\nNo drift — spec generation skipped.")
    sys.exit(0)

print("\n=== Step 2: Spec Generation ===")
resp2 = client.chat.completions.create(
    model=MODEL,
    max_tokens=1024,
    messages=[
        {"role": "system", "content": SPEC_PROMPT},
        {"role": "user", "content": (
            f"IntentObject:\n{intent.model_dump_json(indent=2)}\n\n"
            f"ExecutionObject:\n{execution.model_dump_json(indent=2)}\n\n"
            f"DriftAnalysis:\n{drift.model_dump_json(indent=2)}"
        )},
    ],
)
llm_output = json.loads(resp2.choices[0].message.content.strip())
spec = RemediationSpec(
    pr_number=int(execution.source_id),
    jira_key=intent.source_id,
    severity=drift.severity,
    owner=execution.author.display_name,
    **llm_output,
)
print(json.dumps(spec.model_dump(), indent=2))
