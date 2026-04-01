# Quick Start Guide: Implementing Efficiency Improvements

This guide provides step-by-step instructions for implementing the efficiency improvements identified in the EFFICIENCY_REPORT.md.

## Prerequisites

- Python 3.11+
- Git
- Basic understanding of async/await patterns
- Familiarity with FastAPI

## Phase 1: Critical Fixes (Week 1)

### 1. Implement Connection Pooling (Day 1)

The `core/http_client.py` module has been created with connection pooling support. To use it:

**Before (inefficient)**:
```python
import requests

response = requests.get("https://api.example.com/data")
```

**After (efficient with connection pooling)**:
```python
from core.http_client import get_async_http_client, sync_get

# For async contexts
client = get_async_http_client()
response = await client.get("https://api.example.com/data")

# For sync contexts (convenience function)
response = sync_get("https://api.example.com/data")
```

**Action Items**:
- [ ] Update `api_server.py` to use connection pooling
- [ ] Update `core/live_tools.py` to use async HTTP client
- [ ] Update `core/privategpt_client.py` to use async HTTP client
- [ ] Update `core/llm_singleton.py` to use sync HTTP client for health checks
- [ ] Add lifespan context manager to FastAPI app

**Example Update for api_server.py**:
```python
from contextlib import asynccontextmanager
from core.http_client import http_client_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with http_client_lifespan():
        yield

app = FastAPI(
    title="JeweledTech Agentic Framework",
    description="...",
    version="1.0.0",
    lifespan=lifespan  # Add this
)
```

### 2. Implement Structured Error Handling (Day 1-2)

The `core/exceptions.py` module has been created with custom exception classes. To use it:

**Before (inefficient)**:
```python
try:
    result = risky_operation()
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**After (efficient with structured errors)**:
```python
from core.exceptions import (
    AgentTimeoutError, AgentResourceError, 
    AgentValidationError, AgentError
)

try:
    result = risky_operation()
except AgentTimeoutError as e:
    logger.warning(f"Operation timeout: {e}")
    raise HTTPException(status_code=504, detail="Operation timed out")
except AgentResourceError as e:
    logger.error(f"Resource unavailable: {e}")
    raise HTTPException(status_code=503, detail="Required resource unavailable")
except AgentValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except AgentError as e:
    logger.error(f"Agent error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal agent error")
```

**Action Items**:
- [ ] Update all endpoints in `api_server.py` to use structured exceptions
- [ ] Update `core/agent.py` to raise appropriate exceptions
- [ ] Update `core/llm_singleton.py` to use custom exceptions
- [ ] Update `core/tools.py` to use `AgentToolError`
- [ ] Add exception logging throughout

### 3. Implement Centralized Configuration (Day 2-3)

The `core/config.py` module has been created with Pydantic settings. To use it:

**Before (scattered configuration)**:
```python
import os

ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
use_mock = os.environ.get('USE_MOCK_KB', 'false').lower() == 'true'
```

**After (centralized configuration)**:
```python
from core.config import get_settings, is_mock_mode, get_ollama_host

settings = get_settings()
ollama_host = get_ollama_host()  # or settings.ollama.host
use_mock = is_mock_mode()  # or settings.features.use_mock_kb
```

**Action Items**:
- [ ] Update `api_server.py` to use centralized config
- [ ] Update `core/llm_singleton.py` to use centralized config
- [ ] Update `core/agent.py` to use centralized config
- [ ] Update `.env.example` to include all configuration options using nested `__` env var naming
- [ ] Document all configuration options in README
- [ ] Add configuration validation at startup

**Example .env file**:
```env
# Application
ENVIRONMENT=development
DEBUG_MODE=true

# Ollama Configuration
OLLAMA__HOST=http://localhost:11434
OLLAMA__DEFAULT_MODEL=llama3.2:3b
OLLAMA__HEALTH_CHECK_TIMEOUT=5
OLLAMA__HEALTH_CHECK_CACHE_TTL=60

# API Configuration
API__HOST=0.0.0.0
API__PORT=8000
API__ENABLE_AUTH=false
API__API_KEY=your_secret_key_here

# Feature Flags
FEATURES__USE_MOCK_KB=false
FEATURES__DEBUG_MODE=true
FEATURES__ENABLE_METRICS=false

# Resource Limits
LIMITS__MAX_QUEUED_TASKS_PER_AGENT=100
LIMITS__MAX_CACHED_MODELS=3
LIMITS__REQUEST_RATE_LIMIT=60
```

### 4. Cache Ollama Health Checks (Day 3)

Implement cached health checking in `core/llm_singleton.py`:

**Implementation**:
```python
import time
from functools import lru_cache
from core.http_client import sync_get

class EnhancedLLMSingleton:
    _health_check_cache = {'timestamp': 0, 'result': False}
    _health_check_ttl = 60  # seconds
    
    def _is_ollama_available(self) -> bool:
        """Check if Ollama service is available (with caching)."""
        current_time = time.time()
        
        # Check cache
        if current_time - self._health_check_cache['timestamp'] < self._health_check_ttl:
            return self._health_check_cache['result']
        
        # Perform actual health check
        try:
            response = sync_get(
                f"{settings.ollama.host}/api/tags",
                timeout=settings.ollama.health_check_timeout
            )
            result = response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            result = False
        
        # Update cache
        self._health_check_cache = {
            'timestamp': current_time,
            'result': result
        }
        
        return result
```

**Action Items**:
- [ ] Update `_is_ollama_available()` method with caching
- [ ] Use `sync_get()` from `core.http_client` instead of `requests.get()`
- [ ] Add cache TTL configuration
- [ ] Add background health check task (optional)

## Phase 2: High-Impact Optimizations (Week 2)

### 5. Implement Lazy Agent Initialization (Day 1-2)

**Current Problem**: Agents are instantiated at module load time, blocking API startup.

**Solution**: Lazy initialization pattern

**Implementation**:
```python
# api_server.py

from typing import Dict, Optional
from core.agent import BaseAgent
from agents.examples import ResearchAgent, WriterAgent
from agents.executive_chat import ExecutiveChatAgent

# Global agent cache
_agents: Dict[str, BaseAgent] = {}

def get_agent(agent_type: str) -> BaseAgent:
    """Get or create an agent instance (lazy initialization)."""
    if agent_type not in _agents:
        if agent_type == "research":
            _agents[agent_type] = ResearchAgent()
        elif agent_type == "writer":
            _agents[agent_type] = WriterAgent()
        elif agent_type == "executive_chat":
            _agents[agent_type] = ExecutiveChatAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    return _agents[agent_type]

@app.post("/research")
async def research_topic(request: ResearchRequest):
    try:
        agent = get_agent("research")  # Lazy load on first use
        result = await asyncio.to_thread(
            agent.research_topic,
            topic=request.topic,
            depth=request.depth
        )
        return AgentResponse(...)
    except Exception as e:
        # ... structured error handling
```

**Optional: Pre-warm Critical Agents**:
```python
@app.on_event("startup")
async def startup_event():
    """Pre-warm critical agents in background."""
    logger.info("Pre-warming critical agents...")
    
    async def prewarm():
        await asyncio.gather(
            asyncio.to_thread(lambda: get_agent("research")),
            asyncio.to_thread(lambda: get_agent("writer")),
            return_exceptions=True
        )
    
    # Don't block startup, run in background
    asyncio.create_task(prewarm())
    logger.info("API server ready")
```

**Action Items**:
- [ ] Remove module-level agent instantiation
- [ ] Implement `get_agent()` lazy loader
- [ ] Update all endpoints to use `get_agent()`
- [ ] Add optional pre-warming in startup event
- [ ] Add proper shutdown cleanup for agents

### 6. Make Endpoints Truly Async (Day 2-3)

**Problem**: Async endpoints call blocking functions, defeating the purpose of async.

**Solution**: Use `asyncio.to_thread()` or proper async implementations.

**Implementation**:
```python
import asyncio

@app.post("/research")
async def research_topic(request: ResearchRequest):
    try:
        agent = get_agent("research")
        
        # Run blocking operation in thread pool
        result = await asyncio.to_thread(
            agent.research_topic,
            topic=request.topic,
            depth=request.depth
        )
        
        return AgentResponse(
            agent="research_agent",
            task=f"Research '{request.topic}'",
            result=result,
            timestamp=datetime.now().isoformat(),
            status="completed"
        )
    except AgentTimeoutError as e:
        raise HTTPException(status_code=504, detail="Research timed out")
    except Exception as e:
        logger.error(f"Research error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")

@app.post("/collaborate")
async def collaborate_agents(request: CollaborativeRequest):
    try:
        research_agent = get_agent("research")
        writer_agent = get_agent("writer")
        
        # Run research in background
        research_task = asyncio.create_task(
            asyncio.to_thread(
                research_agent.research_topic,
                topic=request.topic,
                depth="comprehensive"
            )
        )
        
        # Wait for research
        research_result = await research_task
        
        # Then run writing
        writing_result = await asyncio.to_thread(
            writer_agent.write_blog_post,
            topic=request.topic,
            research_data=research_result["findings"],
            tone="professional",
            word_count=1000
        )
        
        return {
            "collaboration": "research_and_write",
            "research_phase": research_result,
            "writing_phase": writing_result,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Collaboration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Collaboration failed")
```

**Action Items**:
- [ ] Wrap all blocking agent calls with `asyncio.to_thread()`
- [ ] Update `/research` endpoint
- [ ] Update `/write` endpoint
- [ ] Update `/collaborate` endpoint
- [ ] Update `/chat` endpoint
- [ ] Add timeout handling for long-running operations

### 7. Add Structured Logging (Day 3)

**Implementation**:
```python
# core/logging_config.py
import logging
import json
import sys
from datetime import datetime
from core.config import get_settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields from non-standard LogRecord attributes (e.g., extra=...)
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
            'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
            'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
            'thread', 'threadName', 'processName', 'process', 'taskName'
        }
        extra_attrs = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_attrs and not key.startswith('_')
        }
        log_data.update(extra_attrs)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging():
    """Configure structured logging for the application."""
    settings = get_settings()
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.logging.level))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.logging.format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if settings.logging.log_file:
        file_handler = logging.FileHandler(settings.logging.log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    return logger


# Usage in api_server.py
from core.logging_config import setup_logging

logger = setup_logging()

@app.post("/research")
async def research_topic(request: ResearchRequest):
    logger.info(
        "Research request received",
        extra={
            'topic': request.topic,
            'depth': request.depth,
            'client_ip': request.client.host
        }
    )
    # ... endpoint logic
```

**Action Items**:
- [ ] Create `core/logging_config.py`
- [ ] Replace all `print()` statements with proper logging
- [ ] Add request/response logging middleware
- [ ] Add performance metrics logging
- [ ] Configure log rotation for production

## Phase 3: Testing & Documentation (Week 3)

### 8. Add Comprehensive Tests

**Test Structure**:
```
tests/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_api_endpoints.py          # API integration tests
├── test_agents.py                 # Agent unit tests
├── test_http_client.py            # HTTP client tests
├── test_config.py                 # Configuration tests
├── test_exceptions.py             # Exception handling tests
└── test_performance.py            # Performance benchmarks
```

**Example Test Implementation**:
```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from api_server import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# tests/test_api_endpoints.py
import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "agents_loaded" in data

@pytest.mark.asyncio
async def test_research_endpoint(client):
    response = await client.post(
        "/research",
        json={"topic": "AI agents", "depth": "medium"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "result" in data

@pytest.mark.asyncio
async def test_research_endpoint_validation_error(client):
    response = await client.post(
        "/research",
        json={"topic": "", "depth": "invalid"}
    )
    assert response.status_code == 422  # Validation error
```

**Action Items**:
- [ ] Create comprehensive test suite
- [ ] Add endpoint integration tests
- [ ] Add agent unit tests
- [ ] Add performance benchmarks
- [ ] Set up CI/CD pipeline for tests
- [ ] Target 60%+ code coverage

### 9. Document Changes

**Action Items**:
- [ ] Update README.md with new features
- [ ] Document configuration options
- [ ] Add migration guide from old code
- [ ] Create API documentation examples
- [ ] Add performance benchmarks
- [ ] Create troubleshooting guide

## Validation Checklist

After implementing all improvements, validate:

### Performance Metrics
- [ ] API startup time < 5 seconds
- [ ] Research endpoint latency < 30 seconds
- [ ] Write endpoint latency < 25 seconds
- [ ] Collaborate endpoint latency < 40 seconds
- [ ] Health check latency < 20ms
- [ ] Can handle 50+ concurrent requests

### Code Quality
- [ ] No bare `except Exception` blocks
- [ ] All HTTP calls use connection pooling
- [ ] All configuration centralized
- [ ] Structured logging throughout
- [ ] Test coverage > 60%
- [ ] No code duplication in critical paths

### Resource Management
- [ ] Memory usage stable under load
- [ ] No connection leaks
- [ ] Proper cleanup on shutdown
- [ ] Model instances properly cached
- [ ] Task queues have limits

## Getting Help

If you encounter issues during implementation:

1. Check the EFFICIENCY_REPORT.md for detailed explanations
2. Review the example code in this guide
3. Check logs for error messages
4. Open an issue on GitHub with:
   - Description of the problem
   - Steps to reproduce
   - Relevant log output
   - Your environment details

## Next Steps

After completing these improvements:

1. Deploy to staging environment
2. Run load tests
3. Monitor performance metrics
4. Gather user feedback
5. Plan for next iteration

---

**Last Updated**: February 5, 2026  
**Version**: 1.0.0
