"""
Centralized Configuration Management for the Agentic Framework.

This module provides type-safe, validated configuration using Pydantic.
All environment variables and settings are defined here.
"""

import json
import os
from typing import Annotated, Dict, Optional, List, Literal
from pydantic import AliasChoices, Field, validator
from pydantic_settings import BaseSettings, NoDecode


class ModelConfig(BaseSettings):
    """Configuration for a specific LLM model."""
    
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=8192)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


class OllamaSettings(BaseSettings):
    """Ollama-specific configuration."""
    
    host: str = Field(default="http://localhost:11434")
    default_model: str = Field(default="llama3.2:3b")
    health_check_timeout: int = Field(default=5, ge=1, le=30)
    health_check_cache_ttl: int = Field(default=60, ge=10, le=300)
    
    @validator('host')
    def validate_host(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Ollama host must start with http:// or https://")
        return v.rstrip('/')


class APISettings(BaseSettings):
    """API server configuration."""
    
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=8)
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["*"],
        validation_alias=AliasChoices("API__CORS_ORIGINS", "CORS_ORIGINS")
    )
    enable_docs: bool = Field(default=True)
    
    # Authentication
    enable_auth: bool = Field(
        default=False,
        validation_alias=AliasChoices("API__ENABLE_AUTH", "ENABLE_AUTH")
    )
    api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("API__API_KEY", "FRAMEWORK_API_KEY", "API_KEY")
    )

    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Support JSON array or comma-delimited CORS origins."""
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return ["*"]
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v, values):
        if values.get('enable_auth') and not v:
            raise ValueError("API key is required when authentication is enabled")
        return v


class HTTPClientSettings(BaseSettings):
    """HTTP client configuration."""
    
    timeout: int = Field(default=30, ge=1, le=300)
    connect_timeout: int = Field(default=5, ge=1, le=30)
    max_connections: int = Field(default=100, ge=10, le=500)
    max_keepalive_connections: int = Field(default=20, ge=5, le=100)
    keepalive_expiry: int = Field(default=30, ge=10, le=300)
    enable_http2: bool = Field(default=True)


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    format: Literal["json", "text"] = Field(default="json")
    log_file: Optional[str] = Field(default=None)
    enable_request_logging: bool = Field(default=True)
    enable_performance_logging: bool = Field(default=True)


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling functionality."""
    
    use_mock_kb: bool = Field(default=False)
    debug_mode: bool = Field(default=False)
    enable_metrics: bool = Field(default=False)
    enable_tracing: bool = Field(default=False)
    enable_caching: bool = Field(default=True)


class ResourceLimits(BaseSettings):
    """Resource usage limits."""
    
    max_queued_tasks_per_agent: int = Field(default=100, ge=10, le=1000)
    max_cached_models: int = Field(default=3, ge=1, le=10)
    max_concurrent_requests: int = Field(default=50, ge=5, le=200)
    request_rate_limit: int = Field(default=60, ge=1, le=1000)  # per minute


class AutomationSettings(BaseSettings):
    """Autonomy and manual-approval controls."""

    approval_scope: str = Field(
        default="money,brand,legal",
        validation_alias=AliasChoices("AUTOMATION__APPROVAL_SCOPE", "APPROVAL_SCOPE")
    )
    auto_retry_max_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        validation_alias=AliasChoices("AUTOMATION__AUTO_RETRY_MAX_ATTEMPTS", "AUTO_RETRY_MAX_ATTEMPTS")
    )
    auto_retry_backoff_ms: int = Field(
        default=2000,
        ge=0,
        le=60000,
        validation_alias=AliasChoices("AUTOMATION__AUTO_RETRY_BACKOFF_MS", "AUTO_RETRY_BACKOFF_MS")
    )
    daily_digest_only: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTOMATION__DAILY_DIGEST_ONLY", "DAILY_DIGEST_ONLY")
    )
    auto_fallback_models: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTOMATION__AUTO_FALLBACK_MODELS", "AUTO_FALLBACK_MODELS")
    )
    max_daily_spend_usd: float = Field(
        default=100.0,
        ge=0.0,
        validation_alias=AliasChoices("AUTOMATION__MAX_DAILY_SPEND_USD", "MAX_DAILY_SPEND_USD")
    )
    per_request_cost_cap_usd: float = Field(
        default=25.0,
        ge=0.0,
        validation_alias=AliasChoices("AUTOMATION__PER_REQUEST_COST_CAP_USD", "PER_REQUEST_COST_CAP_USD")
    )
    route_error_rate_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("AUTOMATION__ROUTE_ERROR_RATE_THRESHOLD", "ROUTE_ERROR_RATE_THRESHOLD")
    )
    min_requests_for_guardrail: int = Field(
        default=20,
        ge=1,
        validation_alias=AliasChoices("AUTOMATION__MIN_REQUESTS_FOR_GUARDRAIL", "MIN_REQUESTS_FOR_GUARDRAIL")
    )
    conversion_rate_floor: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("AUTOMATION__CONVERSION_RATE_FLOOR", "CONVERSION_RATE_FLOOR")
    )
    auto_pause_on_guardrail_breach: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTOMATION__AUTO_PAUSE_ON_GUARDRAIL_BREACH", "AUTO_PAUSE_ON_GUARDRAIL_BREACH")
    )
    enable_background_worker: bool = Field(
        default=True,
        validation_alias=AliasChoices("AUTOMATION__ENABLE_BACKGROUND_WORKER", "ENABLE_BACKGROUND_WORKER")
    )
    queue_poll_interval_seconds: int = Field(
        default=2,
        ge=1,
        le=60,
        validation_alias=AliasChoices("AUTOMATION__QUEUE_POLL_INTERVAL_SECONDS", "QUEUE_POLL_INTERVAL_SECONDS")
    )
    idempotency_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        validation_alias=AliasChoices("AUTOMATION__IDEMPOTENCY_TTL_HOURS", "IDEMPOTENCY_TTL_HOURS")
    )
    operations_db_path: str = Field(
        default="data/ops_runtime.db",
        validation_alias=AliasChoices("AUTOMATION__OPERATIONS_DB_PATH", "OPERATIONS_DB_PATH")
    )


class Settings(BaseSettings):
    """Main settings class combining all configuration sections."""
    
    # Application info
    app_name: str = Field(default="JeweledTech Agentic Framework")
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    
    # Sub-configurations
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    api: APISettings = Field(default_factory=APISettings)
    http_client: HTTPClientSettings = Field(default_factory=HTTPClientSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    limits: ResourceLimits = Field(default_factory=ResourceLimits)
    automation: AutomationSettings = Field(default_factory=AutomationSettings)
    
    # Model configurations
    models: Dict[str, ModelConfig] = Field(default_factory=lambda: {
        "general": ModelConfig(
            model="ollama/llama3:8b",
            temperature=0.7,
            max_tokens=2048
        ),
        "coding": ModelConfig(
            model="ollama/llama3:8b",
            temperature=0.3,
            max_tokens=4096
        ),
        "analysis": ModelConfig(
            model="ollama/llama3:8b",
            temperature=0.5,
            max_tokens=2048
        ),
        "creative": ModelConfig(
            model="ollama/llama3:8b",
            temperature=0.9,
            max_tokens=2048
        ),
    })
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_nested_delimiter = "__"  # Use __ for nested config (e.g., OLLAMA__HOST)
        
        # Allow extra fields for backward compatibility
        extra = "allow"
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    This function initializes settings on first call and returns
    the cached instance on subsequent calls.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings():
    """
    Reload settings from environment variables.
    
    This can be useful for testing or dynamic configuration updates.
    """
    global _settings
    _settings = Settings()
    return _settings


# Convenience accessors for commonly used settings
def get_ollama_host() -> str:
    """Get the Ollama host URL."""
    return get_settings().ollama.host


def get_api_host() -> str:
    """Get the API server host."""
    return get_settings().api.host


def get_api_port() -> int:
    """Get the API server port."""
    return get_settings().api.port


def is_mock_mode() -> bool:
    """Check if running in mock mode."""
    return get_settings().features.use_mock_kb


def is_debug_mode() -> bool:
    """Check if running in debug mode."""
    return get_settings().features.debug_mode


def get_model_config(task_type: str = "general") -> ModelConfig:
    """Get model configuration for a specific task type."""
    settings = get_settings()
    return settings.models.get(task_type, settings.models["general"])


# Environment variable mapping for backward compatibility
def setup_legacy_env_vars():
    """
    Set up environment variables for backward compatibility.
    
    This ensures that existing code using os.environ.get() still works.
    """
    settings = get_settings()
    
    # Set legacy environment variables
    os.environ['OLLAMA_HOST'] = settings.ollama.host
    os.environ['OLLAMA_MODEL'] = settings.ollama.default_model
    os.environ['API_HOST'] = settings.api.host
    os.environ['API_PORT'] = str(settings.api.port)
    os.environ['USE_MOCK_KB'] = str(settings.features.use_mock_kb).lower()
    os.environ['DEBUG_MODE'] = str(settings.features.debug_mode).lower()
    os.environ['ENABLE_AUTH'] = str(settings.api.enable_auth).lower()
    os.environ['APPROVAL_SCOPE'] = settings.automation.approval_scope
    os.environ['AUTO_RETRY_MAX_ATTEMPTS'] = str(settings.automation.auto_retry_max_attempts)
    os.environ['AUTO_RETRY_BACKOFF_MS'] = str(settings.automation.auto_retry_backoff_ms)
    os.environ['DAILY_DIGEST_ONLY'] = str(settings.automation.daily_digest_only).lower()
    os.environ['AUTO_FALLBACK_MODELS'] = str(settings.automation.auto_fallback_models).lower()
    os.environ['MAX_DAILY_SPEND_USD'] = str(settings.automation.max_daily_spend_usd)
    os.environ['PER_REQUEST_COST_CAP_USD'] = str(settings.automation.per_request_cost_cap_usd)
    os.environ['ROUTE_ERROR_RATE_THRESHOLD'] = str(settings.automation.route_error_rate_threshold)
    os.environ['MIN_REQUESTS_FOR_GUARDRAIL'] = str(settings.automation.min_requests_for_guardrail)
    os.environ['CONVERSION_RATE_FLOOR'] = str(settings.automation.conversion_rate_floor)
    os.environ['AUTO_PAUSE_ON_GUARDRAIL_BREACH'] = str(settings.automation.auto_pause_on_guardrail_breach).lower()
    os.environ['ENABLE_BACKGROUND_WORKER'] = str(settings.automation.enable_background_worker).lower()
    os.environ['QUEUE_POLL_INTERVAL_SECONDS'] = str(settings.automation.queue_poll_interval_seconds)
    os.environ['IDEMPOTENCY_TTL_HOURS'] = str(settings.automation.idempotency_ttl_hours)
    os.environ['OPERATIONS_DB_PATH'] = settings.automation.operations_db_path
    
    if settings.api.api_key:
        os.environ['FRAMEWORK_API_KEY'] = settings.api.api_key
