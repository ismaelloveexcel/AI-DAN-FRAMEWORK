#!/usr/bin/env python3
"""
JeweledTech Agentic Framework API Server

A simple, developer-friendly API server for creating and orchestrating AI agents.
This server demonstrates the core capabilities of the framework.
"""

from fastapi import FastAPI, HTTPException, Security, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple, Callable
import os
import sys
import logging
from datetime import datetime
import hashlib
import json
import threading
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import framework components
from agents.examples import ResearchAgent, WriterAgent
from agents.executive_chat import ExecutiveChatAgent
from core.config import get_settings, reload_settings
from core.policy import ApprovalPolicy
from core.operations import OperationsStore
from core.operator_console_ui import build_operator_console_html

settings = get_settings()


def _load_runtime_settings():
    """Reload settings so runtime auth toggles are reflected immediately."""
    runtime_settings = reload_settings()
    if runtime_settings.api.enable_auth and not runtime_settings.api.api_key:
        raise RuntimeError(
            "Authentication is enabled but no API key is configured. "
            "Set FRAMEWORK_API_KEY (or API_KEY/API__API_KEY) before startup."
        )
    if runtime_settings.environment != "development" and runtime_settings.api.enable_auth:
        key = (runtime_settings.api.api_key or "").strip()
        weak_markers = ["replace", "changeme", "test", "dev", "generate", "sample"]
        if len(key) < 32:
            raise RuntimeError("FRAMEWORK_API_KEY must be at least 32 characters outside development.")
        if any(marker in key.lower() for marker in weak_markers):
            raise RuntimeError("FRAMEWORK_API_KEY appears to be placeholder/weak for non-development.")
    return runtime_settings


settings = _load_runtime_settings()
ops_store = OperationsStore(settings.automation.operations_db_path)
_worker_stop = threading.Event()
_worker_thread: Optional[threading.Thread] = None

# Do not allow wildcard origin with credentials (invalid/unsafe browser combo).
cors_allow_credentials = "*" not in settings.api.cors_origins

# Initialize FastAPI app
app = FastAPI(
    title="JeweledTech Agentic Framework",
    description="Open-source framework for building multi-agent AI systems",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _approval_metadata(action_scope: str) -> Dict[str, Any]:
    """Attach approval policy metadata to action responses."""
    policy = ApprovalPolicy.from_settings()
    return {
        "scope": action_scope,
        "requires_manual_approval": policy.requires_manual_approval(action_scope),
    }

# API Key Security (for n8n integration)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key for protected endpoints"""
    runtime_settings = _load_runtime_settings()
    expected_key = runtime_settings.api.api_key
    enable_auth = runtime_settings.api.enable_auth

    if not enable_auth:
        return "auth_disabled"

    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    return api_key

# Initialize example agents
research_agent = ResearchAgent()
writer_agent = WriterAgent()
executive_chat_agent = ExecutiveChatAgent()

# Request/Response models
class ResearchRequest(BaseModel):
    topic: str
    depth: str = "medium"

class WritingRequest(BaseModel):
    topic: str
    research_data: Optional[str] = None
    tone: str = "professional"
    word_count: int = 800

class CollaborativeRequest(BaseModel):
    topic: str
    output_type: str = "blog_post"  # blog_post, documentation, report

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    agent: str
    task: str
    result: Any
    timestamp: str
    status: str

# n8n Integration Request Models
class N8NWebhookRequest(BaseModel):
    """Request model for n8n webhook calls"""
    workflow_id: str
    trigger_type: str  # "sales", "marketing", "research", "custom"
    payload: Dict[str, Any]
    callback_url: Optional[str] = None

class SalesLeadRequest(BaseModel):
    """Request model for sales lead processing"""
    lead_name: str
    lead_email: str
    lead_company: str
    lead_source: str = "n8n"
    additional_data: Optional[Dict[str, Any]] = None

class SalesQualifyRequest(BaseModel):
    """Request model for lead qualification"""
    lead_id: str
    lead_data: Dict[str, Any]
    icp_criteria: Optional[Dict[str, Any]] = None

class MarketingRequest(BaseModel):
    """Request model for marketing actions"""
    action: str  # "generate_content", "analyze", "distribute"
    campaign_name: Optional[str] = None
    parameters: Dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    approval_id: str
    approve: bool = True
    decision_note: Optional[str] = ""


class DailyBatchRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=200)


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = ""


runtime_settings = _load_runtime_settings()
ops_store = OperationsStore(runtime_settings.automation.operations_db_path)
_worker_stop = threading.Event()
_worker_thread: Optional[threading.Thread] = None


def _now_iso() -> str:
    return datetime.now().isoformat()


def _hash_payload(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resolve_scope(endpoint: str) -> str:
    if endpoint.startswith("/sales") or endpoint.startswith("/n8n/webhook"):
        return "money"
    if endpoint.startswith("/marketing"):
        return "brand"
    return "operations"


def _kill_switch_state() -> Dict[str, Any]:
    state = ops_store.get_state("kill_switch", {"active": False, "reason": "", "updated_at": _now_iso()})
    if isinstance(state, bool):
        return {"active": state, "reason": "", "updated_at": _now_iso()}
    return state


def _set_kill_switch(active: bool, reason: str = "") -> None:
    ops_store.set_state(
        "kill_switch",
        {
            "active": bool(active),
            "reason": reason,
            "updated_at": _now_iso(),
        },
    )


def _route_pause_key(endpoint: str) -> str:
    return f"paused:{endpoint}"


def _is_route_paused(endpoint: str) -> bool:
    state = ops_store.get_state(_route_pause_key(endpoint), {"paused": False})
    return bool(state.get("paused", False)) if isinstance(state, dict) else False


def _set_route_paused(endpoint: str, paused: bool, reason: str = "") -> None:
    ops_store.set_state(
        _route_pause_key(endpoint),
        {
            "paused": bool(paused),
            "reason": reason,
            "updated_at": _now_iso(),
        },
    )


def _list_route_pauses() -> List[Dict[str, Any]]:
    rows = ops_store.list_states(prefix="paused:")
    pauses = []
    for row in rows:
        value = row.get("value") or {}
        if isinstance(value, dict) and value.get("paused"):
            pauses.append(
                {
                    "endpoint": row["key"].replace("paused:", "", 1),
                    "reason": value.get("reason", ""),
                    "updated_at": value.get("updated_at", row.get("updated_at")),
                }
            )
    return pauses


def _safe_float(value: Optional[str]) -> float:
    if value in (None, ""):
        return 0.0
    try:
        parsed = float(value)
        return parsed if parsed >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def _check_guardrails(endpoint: str, request_cost_usd: float) -> None:
    runtime = _load_runtime_settings().automation

    if _kill_switch_state().get("active"):
        raise HTTPException(status_code=423, detail="Kill switch is active. Resume from /operator/kill-switch.")

    if _is_route_paused(endpoint):
        raise HTTPException(status_code=423, detail=f"Route is paused by guardrail: {endpoint}")

    if request_cost_usd > runtime.per_request_cost_cap_usd:
        raise HTTPException(
            status_code=429,
            detail=f"Request cost exceeds per-request cap ({request_cost_usd:.2f} > {runtime.per_request_cost_cap_usd:.2f}).",
        )

    daily_spend = ops_store.get_daily_spend()
    if daily_spend + request_cost_usd > runtime.max_daily_spend_usd:
        if runtime.auto_pause_on_guardrail_breach:
            _set_kill_switch(True, "Daily spend cap breached")
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily spend cap reached ({daily_spend:.2f} + {request_cost_usd:.2f} > "
                f"{runtime.max_daily_spend_usd:.2f})."
            ),
        )


def _post_guardrail_check(endpoint: str) -> None:
    runtime = _load_runtime_settings().automation
    stats = ops_store.get_route_stats_today(endpoint)
    if stats["total"] < runtime.min_requests_for_guardrail:
        return

    if stats["error_rate"] > runtime.route_error_rate_threshold:
        reason = f"Error rate breach ({stats['error_rate']:.2f} > {runtime.route_error_rate_threshold:.2f})"
        _set_route_paused(endpoint, True, reason)
        if runtime.auto_pause_on_guardrail_breach:
            _set_kill_switch(True, f"Guardrail breach on {endpoint}: error rate")
        return

    tracked_conversion = endpoint.startswith("/sales") or endpoint.startswith("/marketing")
    if tracked_conversion and stats["conversion_rate"] < runtime.conversion_rate_floor:
        reason = f"Conversion floor breach ({stats['conversion_rate']:.2f} < {runtime.conversion_rate_floor:.2f})"
        _set_route_paused(endpoint, True, reason)
        if runtime.auto_pause_on_guardrail_breach:
            _set_kill_switch(True, f"Guardrail breach on {endpoint}: conversion")


def _audit(
    *,
    event_type: str,
    endpoint: str,
    scope: str,
    success: bool,
    converted: bool,
    cost_usd: float,
    correlation_id: Optional[str],
    payload: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    ops_store.append_audit(
        event_type=event_type,
        endpoint=endpoint,
        scope=scope,
        success=success,
        converted=converted,
        cost_usd=cost_usd,
        correlation_id=correlation_id,
        payload=payload,
        result=result,
    )


def _register_or_replay(
    *,
    endpoint: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
) -> Tuple[Optional[str], Optional[Tuple[int, Dict[str, Any]]]]:
    effective_key = idempotency_key or f"auto:{_hash_payload({**payload, '__endpoint': endpoint})}"
    claim = ops_store.register_idempotency(
        idempotency_key=effective_key,
        endpoint=endpoint,
        request_hash=_hash_payload(payload),
        ttl_hours=_load_runtime_settings().automation.idempotency_ttl_hours,
    )

    if claim["status"] == "conflict":
        return effective_key, (409, {"status": "error", "detail": "Idempotency conflict"})
    if claim["status"] == "in_progress":
        return effective_key, (409, {"status": "error", "detail": "Request already processing for this key"})
    if claim["status"] == "replay":
        body = claim["response_body"]
        if isinstance(body, dict):
            body.setdefault("idempotency", {"key": effective_key, "replayed": True})
        return effective_key, (int(claim.get("status_code", 200)), body)
    return effective_key, None


def _require_approval_or_create(
    *,
    scope: str,
    endpoint: str,
    method: str,
    action_type: str,
    payload: Dict[str, Any],
    approval_token: Optional[str],
    correlation_id: Optional[str],
    estimated_cost_usd: float,
) -> Optional[Dict[str, Any]]:
    policy = ApprovalPolicy.from_settings()
    if not policy.requires_manual_approval(scope):
        return None

    if approval_token:
        token = ops_store.consume_approval_token(approval_token)
        if token.get("ok"):
            return None
        raise HTTPException(status_code=403, detail=f"Invalid approval token: {token.get('reason')}")

    approval = ops_store.create_approval(
        scope=scope,
        endpoint=endpoint,
        method=method,
        action_type=action_type,
        request_hash=_hash_payload(payload),
        payload={
            "action_payload": payload,
            "endpoint": endpoint,
            "scope": scope,
            "estimated_cost_usd": estimated_cost_usd,
            "correlation_id": correlation_id,
        },
    )
    return {
        "status": "approval_required",
        "message": "Founder approval required before execution.",
        "approval": approval,
        "next_step": "Use /operator/approve-and-run for one-click execution.",
    }


def _run_action(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if action_type == "n8n.webhook":
        trigger_type = payload.get("trigger_type")
        source_payload = payload.get("payload", {})
        if trigger_type == "sales":
            action = source_payload.get("action", "process")
            result = {
                "processed": True,
                "action": action,
                "message": f"Sales action '{action}' processed successfully",
            }
        elif trigger_type == "marketing":
            action = source_payload.get("action", "analyze")
            if action == "generate_content":
                topic = source_payload.get("topic", "")
                content = writer_agent.write_blog_post(topic=topic, tone="professional", word_count=500)
                result = {"content": content, "topic": topic}
            else:
                result = {
                    "processed": True,
                    "action": action,
                    "message": f"Marketing action '{action}' processed successfully",
                }
        elif trigger_type == "research":
            result = research_agent.research_topic(
                topic=source_payload.get("topic", ""),
                depth=source_payload.get("depth", "medium"),
            )
        else:
            result = executive_chat_agent.chat(
                message=str(source_payload),
                context={"workflow_id": payload.get("workflow_id"), "source": "n8n"},
            )
        return {
            "workflow_id": payload.get("workflow_id"),
            "trigger_type": trigger_type,
            "result": result,
        }

    if action_type == "sales.process_lead":
        analysis_prompt = f"""
        Analyze this sales lead and provide qualification recommendations:
        - Name: {payload.get('lead_name')}
        - Email: {payload.get('lead_email')}
        - Company: {payload.get('lead_company')}
        - Source: {payload.get('lead_source')}
        - Additional Data: {payload.get('additional_data') or 'None'}

        Provide: qualification score (1-100), priority level, recommended next steps.
        """
        response = executive_chat_agent.chat(
            message=analysis_prompt,
            context={"lead_source": payload.get("lead_source"), "type": "lead_analysis"},
        )
        return {
            "lead": {
                "name": payload.get("lead_name"),
                "email": payload.get("lead_email"),
                "company": payload.get("lead_company"),
            },
            "analysis": response.get("message", "Analysis complete"),
        }

    if action_type == "sales.qualify_lead":
        default_icp = {
            "company_size": "50-500 employees",
            "industry": ["technology", "finance", "healthcare"],
            "budget_range": "$10k-$100k",
            "decision_timeline": "1-3 months",
        }
        icp = payload.get("icp_criteria") or default_icp
        qualification_prompt = f"""
        Qualify this lead against our ICP criteria:

        Lead Data: {payload.get('lead_data', {})}

        ICP Criteria: {icp}

        Provide a qualification score (0-100), match reasons, and gaps.
        """
        response = executive_chat_agent.chat(
            message=qualification_prompt,
            context={"type": "icp_qualification"},
        )
        return {
            "lead_id": payload.get("lead_id"),
            "qualification": response.get("message", "Qualification complete"),
            "icp_criteria_used": icp,
        }

    if action_type == "marketing.generate_content":
        if payload.get("action") != "generate_content":
            raise HTTPException(status_code=400, detail=f"Invalid action: {payload.get('action')}. Use 'generate_content'.")
        params = payload.get("parameters", {})
        content_type = params.get("content_type", "blog_post")
        topic = params.get("topic", "")
        tone = params.get("tone", "professional")
        word_count = params.get("word_count", 800)

        if content_type == "blog_post":
            content = writer_agent.write_blog_post(topic=topic, tone=tone, word_count=word_count)
        elif content_type == "social_media":
            content = writer_agent.write_email(
                subject=topic,
                tone="engaging",
                key_points=params.get("key_points", [topic]),
            )
        else:
            content = writer_agent.summarize_content(content=topic, max_words=word_count)

        return {
            "campaign_name": payload.get("campaign_name"),
            "content_type": content_type,
            "content": content,
        }

    if action_type == "marketing.analyze_campaign":
        if payload.get("action") != "analyze":
            raise HTTPException(status_code=400, detail=f"Invalid action: {payload.get('action')}. Use 'analyze'.")
        campaign_data = payload.get("parameters", {}).get("campaign_data", {})
        analysis_prompt = f"""
        Analyze this marketing campaign and provide insights:

        Campaign: {payload.get('campaign_name') or 'Unnamed Campaign'}
        Data: {campaign_data}

        Provide: performance summary, key insights, recommendations for improvement.
        """
        response = executive_chat_agent.chat(
            message=analysis_prompt,
            context={"type": "campaign_analysis"},
        )
        return {
            "campaign_name": payload.get("campaign_name"),
            "analysis": response.get("message", "Analysis complete"),
        }

    raise ValueError(f"Unsupported action_type: {action_type}")


def _execute_job_with_retry(
    *,
    endpoint: str,
    scope: str,
    action_type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    estimated_cost_usd: float,
    correlation_id: Optional[str],
    converted: bool,
) -> Tuple[str, Dict[str, Any]]:
    runtime = _load_runtime_settings().automation
    max_attempts = max(1, runtime.auto_retry_max_attempts)
    backoff_ms = max(0, runtime.auto_retry_backoff_ms)

    job = ops_store.enqueue_job(
        action_type=action_type,
        payload=payload,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
    )
    job_id = job["id"]

    while True:
        try:
            result = _run_action(action_type, payload)
            ops_store.mark_job_success(job_id, result)
            _audit(
                event_type=action_type,
                endpoint=endpoint,
                scope=scope,
                success=True,
                converted=converted,
                cost_usd=estimated_cost_usd,
                correlation_id=correlation_id,
                payload=payload,
                result=result,
            )
            _post_guardrail_check(endpoint)
            return job_id, result
        except HTTPException:
            raise
        except Exception as exc:
            state = ops_store.mark_job_failure(job_id, str(exc), backoff_ms)
            _audit(
                event_type=f"{action_type}.failure",
                endpoint=endpoint,
                scope=scope,
                success=False,
                converted=False,
                cost_usd=estimated_cost_usd,
                correlation_id=correlation_id,
                payload=payload,
                result={"error": str(exc)},
            )
            _post_guardrail_check(endpoint)
            if state.get("status") == "dead_letter":
                raise HTTPException(
                    status_code=500,
                    detail=f"Action failed after retries and moved to dead-letter queue: {action_type}",
                )
            if backoff_ms > 0:
                time.sleep(backoff_ms / 1000.0)


def _process_due_jobs(limit: int = 20) -> Dict[str, int]:
    claimed = ops_store.claim_due_jobs(limit=limit)
    summary = {"claimed": len(claimed), "succeeded": 0, "retried": 0, "dead_letter": 0}
    backoff_ms = max(0, _load_runtime_settings().automation.auto_retry_backoff_ms)

    for job in claimed:
        payload = job["payload"]
        action_payload = payload.get("action_payload", payload)
        endpoint = payload.get("endpoint", "/operator/background")
        scope = payload.get("scope", _resolve_scope(endpoint))
        estimated_cost = float(payload.get("estimated_cost_usd", 0.0))
        correlation_id = payload.get("correlation_id")

        try:
            result = _run_action(job["action_type"], action_payload)
            ops_store.mark_job_success(job["id"], result)
            _audit(
                event_type=job["action_type"],
                endpoint=endpoint,
                scope=scope,
                success=True,
                converted=False,
                cost_usd=estimated_cost,
                correlation_id=correlation_id,
                payload=action_payload,
                result=result,
            )
            _post_guardrail_check(endpoint)
            summary["succeeded"] += 1
        except Exception as exc:
            state = ops_store.mark_job_failure(job["id"], str(exc), backoff_ms)
            _audit(
                event_type=f"{job['action_type']}.failure",
                endpoint=endpoint,
                scope=scope,
                success=False,
                converted=False,
                cost_usd=estimated_cost,
                correlation_id=correlation_id,
                payload=action_payload,
                result={"error": str(exc)},
            )
            _post_guardrail_check(endpoint)
            if state.get("status") == "dead_letter":
                summary["dead_letter"] += 1
            else:
                summary["retried"] += 1

    return summary

def _execute_sensitive_action(
    *,
    raw_request: Request,
    endpoint: str,
    action_type: str,
    payload: Dict[str, Any],
    idempotency_key: Optional[str],
    approval_token: Optional[str],
    estimated_cost_usd: float,
    correlation_id: Optional[str],
    converted: bool,
    response_builder: Callable[[Dict[str, Any], str], Dict[str, Any]],
) -> JSONResponse:
    scope = _resolve_scope(endpoint)
    key, replay = _register_or_replay(endpoint=endpoint, payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)

    try:
        _check_guardrails(endpoint, estimated_cost_usd)
        approval_response = _require_approval_or_create(
            scope=scope,
            endpoint=endpoint,
            method=raw_request.method,
            action_type=action_type,
            payload=payload,
            approval_token=approval_token,
            correlation_id=correlation_id,
            estimated_cost_usd=estimated_cost_usd,
        )
        if approval_response is not None:
            _audit(
                event_type=f"{action_type}.approval_required",
                endpoint=endpoint,
                scope=scope,
                success=False,
                converted=False,
                cost_usd=0.0,
                correlation_id=correlation_id,
                payload=payload,
                result=approval_response,
            )
            if key:
                ops_store.complete_idempotency(key, 202, approval_response)
            return JSONResponse(status_code=202, content=approval_response)

        job_id, result = _execute_job_with_retry(
            endpoint=endpoint,
            scope=scope,
            action_type=action_type,
            payload=payload,
            idempotency_key=key,
            estimated_cost_usd=estimated_cost_usd,
            correlation_id=correlation_id,
            converted=converted,
        )
        body = response_builder(result, job_id)
        body["approval"] = _approval_metadata(scope)
        body.setdefault("timestamp", _now_iso())
        body["idempotency"] = {"key": key, "replayed": False}
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except HTTPException as exc:
        if key:
            ops_store.fail_idempotency(key, exc.status_code, {"detail": exc.detail})
        raise
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise


def _worker_loop() -> None:
    logger.info("Background operations worker started")
    while not _worker_stop.is_set():
        try:
            _process_due_jobs(limit=20)
        except Exception as exc:  # pragma: no cover
            logger.error("Worker loop error: %s", exc)
        poll_seconds = max(1, _load_runtime_settings().automation.queue_poll_interval_seconds)
        _worker_stop.wait(timeout=poll_seconds)
    logger.info("Background operations worker stopped")


@app.on_event("startup")
def _on_startup() -> None:
    global _worker_thread
    if _load_runtime_settings().automation.enable_background_worker:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_stop.clear()
        _worker_thread = threading.Thread(target=_worker_loop, name="ops-worker", daemon=True)
        _worker_thread.start()


@app.on_event("shutdown")
def _on_shutdown() -> None:
    _worker_stop.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=2)


# API Routes
@app.get("/")
def read_root():
    return {
        "framework": "JeweledTech Agentic Framework",
        "version": "1.0.0",
        "description": "Open-source framework for building multi-agent AI systems",
        "endpoints": {
            "/": "Welcome",
            "/health": "Health and safety status",
            "/agents": "List available agents",
            "/operator/console": "Single-screen operator console",
            "/docs": "Interactive API documentation",
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "framework": "JeweledTech Agentic Framework",
        "agents_loaded": 3,
        "kill_switch": _kill_switch_state(),
        "features": ["research", "writing", "executive_chat", "ops_guardrails"],
        "timestamp": _now_iso(),
    }


@app.get("/agents")
def list_agents():
    return {
        "agents": [
            {
                "id": "research_agent",
                "name": "Research Specialist",
                "description": "Researches topics and compiles comprehensive reports",
                "capabilities": ["research_topic", "compare_topics", "fact_check"],
            },
            {
                "id": "writer_agent",
                "name": "Content Writer",
                "description": "Creates various types of written content",
                "capabilities": [
                    "write_blog_post",
                    "create_technical_documentation",
                    "write_email",
                    "summarize_content",
                ],
            },
        ]
    }


@app.post("/research", response_model=AgentResponse)
async def research_topic(
    request: ResearchRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(endpoint="/research", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        result = research_agent.research_topic(topic=request.topic, depth=request.depth)
        body = AgentResponse(
            agent="research_agent",
            task=f"Research '{request.topic}'",
            result=result,
            timestamp=_now_iso(),
            status="completed",
        ).model_dump()
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/write", response_model=AgentResponse)
async def write_content(
    request: WritingRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(endpoint="/write", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        result = writer_agent.write_blog_post(
            topic=request.topic,
            research_data=request.research_data,
            tone=request.tone,
            word_count=request.word_count,
        )
        body = AgentResponse(
            agent="writer_agent",
            task=f"Write about '{request.topic}'",
            result=result,
            timestamp=_now_iso(),
            status="completed",
        ).model_dump()
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/collaborate")
async def collaborate_agents(
    request: CollaborativeRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(endpoint="/collaborate", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        research_result = research_agent.research_topic(topic=request.topic, depth="comprehensive")
        if request.output_type == "blog_post":
            writing_result = writer_agent.write_blog_post(
                topic=request.topic,
                research_data=research_result["findings"],
                tone="professional",
                word_count=1000,
            )
        elif request.output_type == "documentation":
            writing_result = writer_agent.create_technical_documentation(
                subject=request.topic,
                specifications={"based_on": "research_findings"},
            )
        else:
            writing_result = writer_agent.summarize_content(content=research_result["findings"], max_words=200)
        body = {
            "collaboration": "research_and_write",
            "topic": request.topic,
            "output_type": request.output_type,
            "agents_involved": ["research_agent", "writer_agent"],
            "research_phase": research_result,
            "writing_phase": writing_result,
            "timestamp": _now_iso(),
            "status": "completed",
        }
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/crew/create")
async def create_crew(
    agent_ids: List[str],
    crew_name: str = "Custom Crew",
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = {"agent_ids": agent_ids, "crew_name": crew_name}
    key, replay = _register_or_replay(endpoint="/crew/create", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        agent_map = {"research_agent": research_agent, "writer_agent": writer_agent}
        agents = [agent_map.get(aid) for aid in agent_ids if aid in agent_map]
        if not agents:
            raise HTTPException(status_code=400, detail="No valid agents specified")
        body = {
            "crew_name": crew_name,
            "agents": agent_ids,
            "status": "created",
            "capabilities": "Ready to execute multi-step tasks",
        }
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except HTTPException as exc:
        if key:
            ops_store.fail_idempotency(key, exc.status_code, {"detail": exc.detail})
        raise


@app.post("/chat")
async def executive_chat(
    request: ChatRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(endpoint="/chat", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        response = executive_chat_agent.chat(
            message=request.message,
            context={"conversation_id": request.conversation_id, **(request.context or {})},
        )
        body = {
            "status": "success",
            "response": response["message"],
            "metadata": response.get("metadata", {}),
            "timestamp": response["timestamp"],
            "conversation_id": request.conversation_id,
        }
        if key:
            ops_store.complete_idempotency(key, 200, body)
        return JSONResponse(status_code=200, content=body)
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat/analyze")
async def analyze_business_request(
    request: Dict[str, Any],
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    key, replay = _register_or_replay(endpoint="/chat/analyze", payload=request, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    try:
        analysis = executive_chat_agent.analyze_business_request(request.get("request", ""))
        if key:
            ops_store.complete_idempotency(key, 200, analysis)
        return JSONResponse(status_code=200, content=analysis)
    except Exception as exc:
        if key:
            ops_store.fail_idempotency(key, 500, {"detail": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat/reset")
async def reset_chat(idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    key, replay = _register_or_replay(endpoint="/chat/reset", payload={}, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)
    executive_chat_agent.reset_conversation()
    body = {"status": "success", "message": "Conversation history reset"}
    if key:
        ops_store.complete_idempotency(key, 200, body)
    return JSONResponse(status_code=200, content=body)


@app.post("/n8n/webhook")
async def n8n_webhook(
    request: N8NWebhookRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    approval_token: Optional[str] = Header(default=None, alias="X-Approval-Token"),
    estimated_cost_usd: Optional[str] = Header(default=None, alias="X-Cost-Estimate-Usd"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    payload = request.model_dump()
    return _execute_sensitive_action(
        raw_request=raw_request,
        endpoint="/n8n/webhook",
        action_type="n8n.webhook",
        payload=payload,
        idempotency_key=idempotency_key,
        approval_token=approval_token,
        estimated_cost_usd=_safe_float(estimated_cost_usd),
        correlation_id=correlation_id,
        converted=False,
        response_builder=lambda result, job_id: {
            "status": "success",
            "workflow_id": result["workflow_id"],
            "trigger_type": result["trigger_type"],
            "result": result["result"],
            "job_id": job_id,
        },
    )


@app.post("/sales/process-lead")
async def process_lead(
    request: SalesLeadRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    approval_token: Optional[str] = Header(default=None, alias="X-Approval-Token"),
    estimated_cost_usd: Optional[str] = Header(default=None, alias="X-Cost-Estimate-Usd"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    payload = request.model_dump()
    return _execute_sensitive_action(
        raw_request=raw_request,
        endpoint="/sales/process-lead",
        action_type="sales.process_lead",
        payload=payload,
        idempotency_key=idempotency_key,
        approval_token=approval_token,
        estimated_cost_usd=_safe_float(estimated_cost_usd),
        correlation_id=correlation_id,
        converted=False,
        response_builder=lambda result, job_id: {
            "status": "success",
            "lead": result["lead"],
            "analysis": result["analysis"],
            "job_id": job_id,
        },
    )


@app.post("/sales/qualify-lead")
async def qualify_lead(
    request: SalesQualifyRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    approval_token: Optional[str] = Header(default=None, alias="X-Approval-Token"),
    estimated_cost_usd: Optional[str] = Header(default=None, alias="X-Cost-Estimate-Usd"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    payload = request.model_dump()
    return _execute_sensitive_action(
        raw_request=raw_request,
        endpoint="/sales/qualify-lead",
        action_type="sales.qualify_lead",
        payload=payload,
        idempotency_key=idempotency_key,
        approval_token=approval_token,
        estimated_cost_usd=_safe_float(estimated_cost_usd),
        correlation_id=correlation_id,
        converted=False,
        response_builder=lambda result, job_id: {
            "status": "success",
            "lead_id": result["lead_id"],
            "qualification": result["qualification"],
            "icp_criteria_used": result["icp_criteria_used"],
            "job_id": job_id,
        },
    )


@app.post("/marketing/generate-content")
async def generate_marketing_content(
    request: MarketingRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    approval_token: Optional[str] = Header(default=None, alias="X-Approval-Token"),
    estimated_cost_usd: Optional[str] = Header(default=None, alias="X-Cost-Estimate-Usd"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    payload = request.model_dump()
    return _execute_sensitive_action(
        raw_request=raw_request,
        endpoint="/marketing/generate-content",
        action_type="marketing.generate_content",
        payload=payload,
        idempotency_key=idempotency_key,
        approval_token=approval_token,
        estimated_cost_usd=_safe_float(estimated_cost_usd),
        correlation_id=correlation_id,
        converted=False,
        response_builder=lambda result, job_id: {
            "status": "success",
            "campaign_name": result["campaign_name"],
            "content_type": result["content_type"],
            "content": result["content"],
            "job_id": job_id,
        },
    )


@app.post("/marketing/analyze-campaign")
async def analyze_campaign(
    request: MarketingRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    approval_token: Optional[str] = Header(default=None, alias="X-Approval-Token"),
    estimated_cost_usd: Optional[str] = Header(default=None, alias="X-Cost-Estimate-Usd"),
    correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-Id"),
):
    payload = request.model_dump()
    return _execute_sensitive_action(
        raw_request=raw_request,
        endpoint="/marketing/analyze-campaign",
        action_type="marketing.analyze_campaign",
        payload=payload,
        idempotency_key=idempotency_key,
        approval_token=approval_token,
        estimated_cost_usd=_safe_float(estimated_cost_usd),
        correlation_id=correlation_id,
        converted=False,
        response_builder=lambda result, job_id: {
            "status": "success",
            "campaign_name": result["campaign_name"],
            "analysis": result["analysis"],
            "job_id": job_id,
        },
    )


@app.get("/operator/console")
def operator_console(api_key: str = Depends(verify_api_key)):
    pending_approvals = len(ops_store.list_approvals(status="pending", limit=500))
    pending_jobs = len(ops_store.list_jobs(status="pending", limit=500))
    running_jobs = len(ops_store.list_jobs(status="running", limit=500))
    dead_letter_jobs = len(ops_store.list_jobs(status="dead_letter", limit=500))
    daily_spend = ops_store.get_daily_spend()
    kill = _kill_switch_state()

    primary_action = {
        "type": "review_approvals",
        "label": "Review pending approvals",
        "endpoint": "/operator/approvals",
    }
    if pending_approvals == 0:
        primary_action = {
            "type": "run_daily_batch",
            "label": "Run daily batch",
            "endpoint": "/operator/run-daily-batch",
        }

    return {
        "headline": "Operator Console",
        "primary_action": primary_action,
        "kpis": {
            "pending_approvals": pending_approvals,
            "pending_jobs": pending_jobs,
            "running_jobs": running_jobs,
            "dead_letter_jobs": dead_letter_jobs,
            "daily_spend_usd": round(daily_spend, 2),
            "kill_switch_active": bool(kill.get("active")),
        },
        "route_pauses": _list_route_pauses(),
        "kill_switch": kill,
        "timestamp": _now_iso(),
    }


@app.get("/operator/console/ui", response_class=HTMLResponse)
def operator_console_ui(api_key: str = Depends(verify_api_key)):
    return HTMLResponse(content=build_operator_console_html(), status_code=200)


@app.get("/operator/approvals")
def operator_list_approvals(status: str = "pending", api_key: str = Depends(verify_api_key)):
    rows = ops_store.list_approvals(status=status, limit=200)
    return {"status": "success", "count": len(rows), "approvals": rows}


@app.post("/operator/approve")
def operator_approve(
    request: ApprovalDecisionRequest,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(endpoint="/operator/approve", payload=payload, idempotency_key=idempotency_key)
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)

    decision = ops_store.decide_approval(request.approval_id, request.approve, request.decision_note or "")
    if not decision:
        body = {"status": "error", "detail": "Approval not found"}
        if key:
            ops_store.complete_idempotency(key, 404, body)
        return JSONResponse(status_code=404, content=body)

    body = {"status": "success", "decision": decision}
    if key:
        ops_store.complete_idempotency(key, 200, body)
    return JSONResponse(status_code=200, content=body)


@app.post("/operator/approve-and-run")
def operator_approve_and_run(
    request: ApprovalDecisionRequest,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(
        endpoint="/operator/approve-and-run", payload=payload, idempotency_key=idempotency_key
    )
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)

    decision = ops_store.decide_approval(request.approval_id, True, request.decision_note or "Approved and queued")
    if not decision:
        body = {"status": "error", "detail": "Approval not found"}
        if key:
            ops_store.complete_idempotency(key, 404, body)
        return JSONResponse(status_code=404, content=body)

    approval = ops_store.get_approval_by_token(decision["resume_token"])
    if not approval:
        body = {"status": "error", "detail": "Approval payload missing"}
        if key:
            ops_store.complete_idempotency(key, 404, body)
        return JSONResponse(status_code=404, content=body)

    job = ops_store.enqueue_job(
        action_type=approval["action_type"],
        payload=approval["payload"],
        idempotency_key=key,
        max_attempts=max(1, _load_runtime_settings().automation.auto_retry_max_attempts),
    )
    body = {
        "status": "queued",
        "approval_id": approval["id"],
        "job": job,
        "message": "Approved action queued. Run /operator/run-daily-batch or wait for worker.",
    }
    if key:
        ops_store.complete_idempotency(key, 202, body)
    return JSONResponse(status_code=202, content=body)


@app.post("/operator/run-daily-batch")
def operator_run_daily_batch(
    request: DailyBatchRequest,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(
        endpoint="/operator/run-daily-batch", payload=payload, idempotency_key=idempotency_key
    )
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)

    summary = _process_due_jobs(limit=request.limit)
    body = {
        "status": "success",
        "message": "Daily batch executed",
        "summary": summary,
        "timestamp": _now_iso(),
    }
    if key:
        ops_store.complete_idempotency(key, 200, body)
    return JSONResponse(status_code=200, content=body)


@app.get("/operator/jobs")
def operator_list_jobs(status: Optional[str] = None, api_key: str = Depends(verify_api_key)):
    jobs = ops_store.list_jobs(status=status, limit=300)
    return {"status": "success", "count": len(jobs), "jobs": jobs}


@app.get("/operator/jobs/{job_id}")
def operator_get_job(job_id: str, api_key: str = Depends(verify_api_key)):
    job = ops_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "job": job}


@app.post("/operator/kill-switch")
def operator_kill_switch(
    request: KillSwitchRequest,
    api_key: str = Depends(verify_api_key),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    payload = request.model_dump()
    key, replay = _register_or_replay(
        endpoint="/operator/kill-switch", payload=payload, idempotency_key=idempotency_key
    )
    if replay is not None:
        status_code, body = replay
        return JSONResponse(status_code=status_code, content=body)

    _set_kill_switch(request.active, request.reason)
    body = {"status": "success", "kill_switch": _kill_switch_state()}
    if key:
        ops_store.complete_idempotency(key, 200, body)
    return JSONResponse(status_code=200, content=body)


@app.get("/operator/audit/recent")
def operator_recent_audit(limit: int = 50, api_key: str = Depends(verify_api_key)):
    events = ops_store.list_audit_events(limit=max(1, min(limit, 200)))
    return {"status": "success", "count": len(events), "events": events}


# Run the server
if __name__ == "__main__":
    import uvicorn

    print("\\n" + "=" * 60)
    print("[*] JeweledTech Agentic Framework")
    print("=" * 60)
    print("\\nStarting API server...")
    print("Documentation available at: http://localhost:8000/docs")
    print("Operator console: http://localhost:8000/operator/console")
    print("=" * 60 + "\\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)