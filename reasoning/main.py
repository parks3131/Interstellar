import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from models import AnalyzeRequest, DriftAnalysis

load_dotenv()

app = FastAPI(title="Interstellar Reasoning Engine")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.getenv("REASONING_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = Path("prompts/drift_detection.txt").read_text()


@app.post("/analyze", response_model=DriftAnalysis)
async def analyze(request: AnalyzeRequest) -> DriftAnalysis:
    user_message = f"""
IntentObject:
{request.intent.model_dump_json(indent=2)}

ExecutionObject:
{request.execution.model_dump_json(indent=2)}
"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
        return DriftAnalysis(**parsed)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to parse reasoning output: {raw}")


@app.get("/health")
async def health():
    return {"status": "ok"}
