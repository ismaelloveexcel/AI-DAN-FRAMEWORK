"""
Operational persistence layer for autonomous runtime controls.

Stores idempotency keys, approvals, jobs, audit records, and guardrail state.
Uses sqlite for durability with a very small operational footprint.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def _from_json(value: Optional[str], fallback: Any) -> Any:
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


class OperationsStore:
    """Durable store for runtime operations and controls."""

    def __init__(self, db_path: str = "data/ops_runtime.db"):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_code INTEGER,
                    response_body TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    resume_token TEXT UNIQUE NOT NULL,
                    decision_note TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT,
                    consumed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    next_attempt_at REAL NOT NULL,
                    last_error TEXT,
                    result TEXT,
                    idempotency_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    scope TEXT,
                    success INTEGER NOT NULL,
                    converted INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0,
                    correlation_id TEXT,
                    payload TEXT,
                    result TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS guardrail_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    # ---------------------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------------------
    def register_idempotency(
        self,
        idempotency_key: str,
        endpoint: str,
        request_hash: str,
        ttl_hours: int = 24,
    ) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            cutoff = datetime.fromtimestamp(time.time() - (ttl_hours * 3600), tz=timezone.utc).isoformat()
            conn.execute("DELETE FROM idempotency_records WHERE updated_at < ?", (cutoff,))

            existing = conn.execute(
                """
                SELECT * FROM idempotency_records
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

            if existing:
                if existing["endpoint"] != endpoint or existing["request_hash"] != request_hash:
                    return {"status": "conflict"}
                if existing["status"] == "completed":
                    return {
                        "status": "replay",
                        "status_code": existing["status_code"] or 200,
                        "response_body": _from_json(existing["response_body"], {}),
                    }
                return {"status": "in_progress"}

            now = _utc_now_iso()
            conn.execute(
                """
                INSERT INTO idempotency_records (
                    idempotency_key, endpoint, request_hash, status, created_at, updated_at
                ) VALUES (?, ?, ?, 'processing', ?, ?)
                """,
                (idempotency_key, endpoint, request_hash, now, now),
            )
            return {"status": "new"}

    def complete_idempotency(
        self,
        idempotency_key: str,
        status_code: int,
        response_body: Any,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE idempotency_records
                SET status = 'completed',
                    status_code = ?,
                    response_body = ?,
                    updated_at = ?
                WHERE idempotency_key = ?
                """,
                (status_code, _to_json(response_body), _utc_now_iso(), idempotency_key),
            )

    def fail_idempotency(self, idempotency_key: str, status_code: int, error_body: Any) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE idempotency_records
                SET status = 'failed',
                    status_code = ?,
                    response_body = ?,
                    updated_at = ?
                WHERE idempotency_key = ?
                """,
                (status_code, _to_json(error_body), _utc_now_iso(), idempotency_key),
            )

    # ---------------------------------------------------------------------
    # Approvals
    # ---------------------------------------------------------------------
    def create_approval(
        self,
        *,
        scope: str,
        endpoint: str,
        method: str,
        action_type: str,
        request_hash: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        approval_id = str(uuid.uuid4())
        resume_token = str(uuid.uuid4())
        now = _utc_now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals (
                    id, scope, endpoint, method, action_type, request_hash, payload,
                    status, resume_token, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    approval_id,
                    scope,
                    endpoint,
                    method,
                    action_type,
                    request_hash,
                    _to_json(payload),
                    resume_token,
                    now,
                ),
            )
        return {
            "approval_id": approval_id,
            "resume_token": resume_token,
            "scope": scope,
            "endpoint": endpoint,
            "status": "pending",
        }

    def list_approvals(self, status: str = "pending", limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM approvals
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "scope": row["scope"],
                "endpoint": row["endpoint"],
                "method": row["method"],
                "action_type": row["action_type"],
                "status": row["status"],
                "resume_token": row["resume_token"],
                "decision_note": row["decision_note"],
                "created_at": row["created_at"],
                "decided_at": row["decided_at"],
                "consumed_at": row["consumed_at"],
                "payload": _from_json(row["payload"], {}),
            }
            for row in rows
        ]

    def count_approvals(self, status: Optional[str] = None) -> int:
        with self._connect() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM approvals WHERE status = ?",
                    (status,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM approvals",
                ).fetchone()
        return int(row["count"] if row else 0)

    def decide_approval(self, approval_id: str, approve: bool, decision_note: str = "") -> Optional[Dict[str, Any]]:
        status = "approved" if approve else "rejected"
        now = _utc_now_iso()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id = ?",
                (approval_id,),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE approvals
                SET status = ?, decision_note = ?, decided_at = ?
                WHERE id = ?
                """,
                (status, decision_note, now, approval_id),
            )
        return {
            "approval_id": approval_id,
            "status": status,
            "decision_note": decision_note,
            "resume_token": row["resume_token"],
        }

    def get_approval_by_token(self, resume_token: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE resume_token = ?",
                (resume_token,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "scope": row["scope"],
            "endpoint": row["endpoint"],
            "method": row["method"],
            "action_type": row["action_type"],
            "request_hash": row["request_hash"],
            "payload": _from_json(row["payload"], {}),
            "status": row["status"],
            "resume_token": row["resume_token"],
            "consumed_at": row["consumed_at"],
        }

    def consume_approval_token(self, resume_token: str) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE resume_token = ?",
                (resume_token,),
            ).fetchone()
            if not row:
                return {"ok": False, "reason": "not_found"}
            if row["status"] != "approved":
                return {"ok": False, "reason": "not_approved"}
            if row["consumed_at"]:
                return {"ok": False, "reason": "already_used"}

            conn.execute(
                "UPDATE approvals SET consumed_at = ? WHERE id = ?",
                (_utc_now_iso(), row["id"]),
            )
        return {"ok": True, "approval_id": row["id"]}

    # ---------------------------------------------------------------------
    # Jobs / Durable queue
    # ---------------------------------------------------------------------
    def enqueue_job(
        self,
        *,
        action_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str],
        max_attempts: int,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now_iso = _utc_now_iso()
        now_epoch = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, action_type, payload, status, attempts, max_attempts,
                    next_attempt_at, idempotency_key, created_at, updated_at
                )
                VALUES (?, ?, ?, 'pending', 0, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    action_type,
                    _to_json(payload),
                    max_attempts,
                    now_epoch,
                    idempotency_key,
                    now_iso,
                    now_iso,
                ),
            )
        return {
            "id": job_id,
            "action_type": action_type,
            "status": "pending",
            "max_attempts": max_attempts,
            "idempotency_key": idempotency_key,
        }

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "action_type": row["action_type"],
            "payload": _from_json(row["payload"], {}),
            "status": row["status"],
            "attempts": row["attempts"],
            "max_attempts": row["max_attempts"],
            "next_attempt_at": row["next_attempt_at"],
            "last_error": row["last_error"],
            "result": _from_json(row["result"], None),
            "idempotency_key": row["idempotency_key"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_jobs(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM jobs
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "id": row["id"],
                "action_type": row["action_type"],
                "status": row["status"],
                "attempts": row["attempts"],
                "max_attempts": row["max_attempts"],
                "last_error": row["last_error"],
                "result": _from_json(row["result"], None),
                "idempotency_key": row["idempotency_key"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def count_jobs(self, status: Optional[str] = None) -> int:
        with self._connect() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM jobs WHERE status = ?",
                    (status,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM jobs",
                ).fetchone()
        return int(row["count"] if row else 0)

    def retry_dead_letter_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        now = _utc_now_iso()
        now_epoch = time.time()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                return None
            if row["status"] != "dead_letter":
                return {
                    "id": row["id"],
                    "status": row["status"],
                    "retry_scheduled": False,
                }

            conn.execute(
                """
                UPDATE jobs
                SET status = 'pending',
                    attempts = 0,
                    next_attempt_at = ?,
                    last_error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now_epoch, now, job_id),
            )
        return {
            "id": job_id,
            "status": "pending",
            "retry_scheduled": True,
        }

    def claim_due_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        now_epoch = time.time()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'pending'
                  AND next_attempt_at <= ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (now_epoch, limit),
            ).fetchall()
            job_ids = [row["id"] for row in rows]
            if job_ids:
                conn.executemany(
                    "UPDATE jobs SET status = 'running', updated_at = ? WHERE id = ?",
                    [(_utc_now_iso(), job_id) for job_id in job_ids],
                )

        claimed = []
        for row in rows:
            claimed.append(
                {
                    "id": row["id"],
                    "action_type": row["action_type"],
                    "payload": _from_json(row["payload"], {}),
                    "status": "running",
                    "attempts": row["attempts"],
                    "max_attempts": row["max_attempts"],
                    "idempotency_key": row["idempotency_key"],
                }
            )
        return claimed

    def mark_job_success(self, job_id: str, result: Any) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'succeeded',
                    result = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (_to_json(result), _utc_now_iso(), job_id),
            )

    def mark_job_failure(self, job_id: str, error: str, backoff_ms: int) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT attempts, max_attempts FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                return {"status": "missing"}

            attempts = int(row["attempts"]) + 1
            max_attempts = int(row["max_attempts"])
            if attempts >= max_attempts:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'dead_letter',
                        attempts = ?,
                        last_error = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (attempts, error, _utc_now_iso(), job_id),
                )
                return {"status": "dead_letter", "attempts": attempts, "max_attempts": max_attempts}

            next_attempt = time.time() + (backoff_ms / 1000.0)
            conn.execute(
                """
                UPDATE jobs
                SET status = 'pending',
                    attempts = ?,
                    next_attempt_at = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (attempts, next_attempt, error, _utc_now_iso(), job_id),
            )
            return {"status": "retry", "attempts": attempts, "max_attempts": max_attempts}

    # ---------------------------------------------------------------------
    # Audit
    # ---------------------------------------------------------------------
    def append_audit(
        self,
        *,
        event_type: str,
        endpoint: str,
        scope: Optional[str],
        success: bool,
        converted: bool,
        cost_usd: float,
        correlation_id: Optional[str],
        payload: Optional[Dict[str, Any]],
        result: Optional[Dict[str, Any]],
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    event_type, endpoint, scope, success, converted, cost_usd,
                    correlation_id, payload, result, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    endpoint,
                    scope,
                    1 if success else 0,
                    1 if converted else 0,
                    float(cost_usd),
                    correlation_id,
                    _to_json(payload or {}),
                    _to_json(result or {}),
                    _utc_now_iso(),
                ),
            )

    def list_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "endpoint": row["endpoint"],
                "scope": row["scope"],
                "success": bool(row["success"]),
                "converted": bool(row["converted"]),
                "cost_usd": float(row["cost_usd"]),
                "correlation_id": row["correlation_id"],
                "payload": _from_json(row["payload"], {}),
                "result": _from_json(row["result"], {}),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_recent_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Backward-compatible alias used by API server endpoints."""
        return self.list_audit_events(limit=limit)

    def get_daily_spend(self, date_prefix: Optional[str] = None) -> float:
        date_prefix = date_prefix or datetime.now(timezone.utc).date().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(cost_usd), 0) AS spend
                FROM audit_events
                WHERE created_at LIKE ?
                """,
                (f"{date_prefix}%",),
            ).fetchone()
        return float(row["spend"] if row else 0.0)

    def get_route_stats_today(self, endpoint: str) -> Dict[str, float]:
        date_prefix = datetime.now(timezone.utc).date().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) AS errors,
                    COALESCE(SUM(converted), 0) AS conversions
                FROM audit_events
                WHERE endpoint = ?
                  AND created_at LIKE ?
                """,
                (endpoint, f"{date_prefix}%"),
            ).fetchone()
        total = int(row["total"] or 0)
        errors = int(row["errors"] or 0)
        conversions = int(row["conversions"] or 0)
        error_rate = (errors / total) if total else 0.0
        conversion_rate = (conversions / total) if total else 0.0
        return {
            "total": total,
            "errors": errors,
            "conversions": conversions,
            "error_rate": error_rate,
            "conversion_rate": conversion_rate,
        }

    # ---------------------------------------------------------------------
    # Guardrail key/value state
    # ---------------------------------------------------------------------
    def set_state(self, key: str, value: Any) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO guardrail_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, _to_json(value), _utc_now_iso()),
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM guardrail_state WHERE key = ?",
                (key,),
            ).fetchone()
        if not row:
            return default
        return _from_json(row["value"], default)

    def list_states(self, prefix: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if prefix:
                rows = conn.execute(
                    """
                    SELECT key, value, updated_at
                    FROM guardrail_state
                    WHERE key LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (f"{prefix}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT key, value, updated_at
                    FROM guardrail_state
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "key": row["key"],
                "value": _from_json(row["value"], None),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


class OperationsManager:
    """High-level orchestration around approvals, queueing, audits, and guardrails."""

    def __init__(self, store: OperationsStore, settings: Any, approval_policy: Any):
        self.store = store
        self.settings = settings
        self.approval_policy = approval_policy

    @staticmethod
    def compute_request_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return __import__("hashlib").sha256(canonical.encode("utf-8")).hexdigest()

    def register_idempotency(self, endpoint: str, key: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        if not key:
            return {"status": "missing"}
        request_hash = self.compute_request_hash(payload)
        return self.store.register_idempotency(
            idempotency_key=key,
            endpoint=endpoint,
            request_hash=request_hash,
            ttl_hours=self.settings.automation.idempotency_ttl_hours,
        )

    def complete_idempotency(self, key: Optional[str], status_code: int, body: Dict[str, Any]) -> None:
        if key:
            self.store.complete_idempotency(key, status_code, body)

    def fail_idempotency(self, key: Optional[str], status_code: int, body: Dict[str, Any]) -> None:
        if key:
            self.store.fail_idempotency(key, status_code, body)

    def requires_approval(self, scope: str) -> bool:
        return self.approval_policy.requires_manual_approval(scope)

    def create_approval(
        self,
        *,
        scope: str,
        endpoint: str,
        method: str,
        action_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.store.create_approval(
            scope=scope,
            endpoint=endpoint,
            method=method,
            action_type=action_type,
            request_hash=self.compute_request_hash(payload),
            payload=payload,
        )

    def consume_resume_token(self, token: str) -> Dict[str, Any]:
        return self.store.consume_approval_token(token)

    def enqueue_job(
        self,
        *,
        action_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str],
    ) -> Dict[str, Any]:
        return self.store.enqueue_job(
            action_type=action_type,
            payload=payload,
            idempotency_key=idempotency_key,
            max_attempts=self.settings.automation.auto_retry_max_attempts,
        )

    def evaluate_guardrails(self, endpoint: str, request_cost_usd: float) -> Dict[str, Any]:
        state = {
            "kill_switch": bool(self.store.get_state("kill_switch", False)),
            "paused": bool(self.store.get_state("auto_paused", False)),
            "reasons": [],
        }
        if state["kill_switch"]:
            state["reasons"].append("kill_switch_enabled")
            return state
        if state["paused"]:
            state["reasons"].append("auto_paused")
            return state

        if request_cost_usd > self.settings.automation.per_request_cost_cap_usd:
            state["reasons"].append("per_request_cost_cap_exceeded")
            if self.settings.automation.auto_pause_on_guardrail_breach:
                self.store.set_state("auto_paused", True)
                state["paused"] = True
            return state

        daily_spend = self.store.get_daily_spend()
        if daily_spend >= self.settings.automation.max_daily_spend_usd:
            state["reasons"].append("daily_spend_cap_exceeded")
            if self.settings.automation.auto_pause_on_guardrail_breach:
                self.store.set_state("auto_paused", True)
                state["paused"] = True
            return state

        route_stats = self.store.get_route_stats_today(endpoint)
        if route_stats["total"] >= self.settings.automation.min_requests_for_guardrail:
            if route_stats["error_rate"] > self.settings.automation.route_error_rate_threshold:
                state["reasons"].append("error_rate_threshold_exceeded")
            if route_stats["conversion_rate"] < self.settings.automation.conversion_rate_floor:
                state["reasons"].append("conversion_rate_floor_breached")
            if state["reasons"] and self.settings.automation.auto_pause_on_guardrail_breach:
                self.store.set_state("auto_paused", True)
                state["paused"] = True
        return state

