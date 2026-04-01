"""AIDAN-OS — Lean FastAPI Server

6 endpoints only. No fluff.
"""

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AIDAN-OS API",
    description="Solo operator business OS — lean API for AIDAN interactions",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    expected_key = os.getenv("FRAMEWORK_API_KEY")
    enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    if not enable_auth:
        return "auth_disabled"
    if not api_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class DailyRequest(BaseModel):
    current_product: Optional[str] = "CareerScore MU"
    current_stage: Optional[str] = "Building"


class EvaluateRequest(BaseModel):
    idea: str
    target_market: Optional[str] = "Mauritius"


class BuildPromptRequest(BaseModel):
    idea: str
    core_feature: str
    tech_stack: Optional[str] = "Static HTML + Python FastAPI"


class WeeklyReviewRequest(BaseModel):
    week_number: int
    mrr: float = 0.0
    users: int = 0
    what_happened: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    mode: str


# --- LLM Helper ---

def call_openai(system_prompt: str, user_message: str) -> str:
    """Call OpenAI API. Falls back to mock if API key not set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-key-here":
        return _mock_response(user_message)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.warning("OpenAI call failed: %s — using mock response", e)
        return _mock_response(user_message)


def _mock_response(message: str) -> str:
    return (
        f"[MOCK MODE — set OPENAI_API_KEY to enable live responses]\n\n"
        f"Received: {message[:100]}...\n\n"
        "AIDAN would respond here with focused, direct guidance."
    )


AIDAN_SYSTEM_PROMPT = (
    # Abbreviated system prompt for API use.
    # Canonical full version: aidan/system_prompt.md
    # Dashboard version: dashboard/index.html (must be kept in sync manually)
    "You are AIDAN — AI Daily Autonomous Navigator. "
    "You are a solo-operator business OS. Your user is building toward $500 MRR. "
    "Be direct. Slightly sarcastic. No fluff. One priority at a time. "
    "Everything before $500 MRR is a distraction. "
    "Never approve spending, publishing, or launching without explicit user confirmation."
)


# --- Endpoints ---

@app.get("/health")
async def health():
    """Health check — always returns 200 if server is up."""
    return {
        "status": "ok",
        "service": "AIDAN-OS",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/aidan/chat", response_model=ChatResponse)
async def aidan_chat(
    req: ChatRequest,
    _key: str = Depends(verify_api_key),
):
    """Send a message to AIDAN, get a focused response."""
    system = AIDAN_SYSTEM_PROMPT
    if req.context:
        system += f"\n\nContext: {req.context}"

    response_text = call_openai(system, req.message)
    mode = "live" if os.getenv("OPENAI_API_KEY", "").startswith("sk-") else "mock"

    return ChatResponse(
        response=response_text,
        timestamp=datetime.now(timezone.utc).isoformat(),
        mode=mode,
    )


@app.post("/aidan/daily")
async def aidan_daily(
    req: DailyRequest,
    _key: str = Depends(verify_api_key),
):
    """Get today's ONE focus task from AIDAN."""
    prompt = (
        f"Current product: {req.current_product}\n"
        f"Current stage: {req.current_stage}\n\n"
        "Give me today's ONE priority task in this exact format:\n"
        "TODAY'S FOCUS: [one task]\n"
        "EXPECTED OUTCOME: [measurable result]\n"
        "TIME ESTIMATE: [hours]\n"
        "DO NOT: [1-3 distractions to avoid]"
    )
    response_text = call_openai(AIDAN_SYSTEM_PROMPT, prompt)
    return {
        "daily_focus": response_text,
        "product": req.current_product,
        "stage": req.current_stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/aidan/evaluate")
async def aidan_evaluate(
    req: EvaluateRequest,
    _key: str = Depends(verify_api_key),
):
    """Evaluate a product idea against AIDAN's 5 Kill Criteria."""
    prompt = (
        f"Evaluate this product idea for the {req.target_market} market:\n\n"
        f"IDEA: {req.idea}\n\n"
        "Score it against these 5 Kill Criteria (YES/NO for each):\n"
        "1. Search demand — are people searching for this?\n"
        "2. Willingness to pay — are people paying for something similar?\n"
        "3. Build speed — can it be built in 3 days with Cursor?\n"
        "4. Market fit — does it work for the target market?\n"
        "5. Recurring potential — can it generate MRR, not just one-off sales?\n\n"
        "End with: VERDICT: PROCEED or KILL, and one sentence why."
    )
    response_text = call_openai(AIDAN_SYSTEM_PROMPT, prompt)
    return {
        "idea": req.idea,
        "evaluation": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/aidan/build-prompt")
async def aidan_build_prompt(
    req: BuildPromptRequest,
    _key: str = Depends(verify_api_key),
):
    """Generate a Cursor-ready build prompt for a validated idea."""
    prompt = (
        f"Generate a Cursor-ready build prompt for this validated idea:\n\n"
        f"IDEA: {req.idea}\n"
        f"CORE FEATURE: {req.core_feature}\n"
        f"TECH STACK: {req.tech_stack}\n\n"
        "The prompt should be clear, scoped for a 3-day MVP, "
        "and include: UI style (glassmorphism dark), mobile-friendly requirement, "
        "and Stripe payment placeholder. Keep it under 200 words."
    )
    response_text = call_openai(AIDAN_SYSTEM_PROMPT, prompt)
    return {
        "idea": req.idea,
        "cursor_prompt": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/aidan/weekly-review")
async def aidan_weekly_review(
    req: WeeklyReviewRequest,
    _key: str = Depends(verify_api_key),
):
    """Generate a weekly review: what worked, what failed, one fix."""
    mrr_gap = max(0, 500 - req.mrr)
    prompt = (
        f"Week {req.week_number} review:\n"
        f"MRR: ${req.mrr:.2f} (gap to $500: ${mrr_gap:.2f})\n"
        f"Users: {req.users}\n"
        f"What happened: {req.what_happened or 'Not provided'}\n\n"
        "Generate a weekly review in this EXACT format:\n"
        "WEEK [N] REVIEW\n"
        "✅ What worked: [specific, honest]\n"
        "❌ What failed: [specific, no excuses]\n"
        "🔧 One fix for next week: [actionable, not a list — ONE thing]\n"
        "📊 MRR this week: $[number]\n"
        "🎯 Distance from $500: $[number]"
    )
    response_text = call_openai(AIDAN_SYSTEM_PROMPT, prompt)
    return {
        "week": req.week_number,
        "mrr": req.mrr,
        "mrr_gap": mrr_gap,
        "review": response_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
