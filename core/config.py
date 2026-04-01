"""
Centralized Configuration Management for AIDAN-OS.

Uses pydantic BaseModel for schema definitions.
Env-var loading is handled via os.environ.get() directly since
pydantic-settings is not a dependency of AIDAN-OS.
"""

import os
from typing import Dict, Optional, List, Literal
from pydantic import Field, validator
from pydantic import BaseModel


class ModelConfig(BaseModel):
    """Configuration for a specific LLM model."""
    
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=8192)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


class OllamaSettings(BaseModel):
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


class APISettings(BaseModel):
    """API server configuration."""
    
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=8)
    cors_origins: List[str] = Field(default=["*"])
    enable_docs: bool = Field(default=True)
    
    # Authentication
    enable_auth: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    
    @validator('api_key')
    def validate_api_key(cls, v, values):
        if values.get('enable_auth') and not v:
            raise ValueError("API key is required when authentication is enabled")
        return v


class HTTPClientSettings(BaseModel):
    """HTTP client configuration."""
    
    timeout: int = Field(default=30, ge=1, le=300)
    connect_timeout: int = Field(default=5, ge=1, le=30)
    max_connections: int = Field(default=100, ge=10, le=500)
    max_keepalive_connections: int = Field(default=20, ge=5, le=100)
    keepalive_expiry: int = Field(default=30, ge=10, le=300)
    enable_http2: bool = Field(default=True)


class LoggingSettings(BaseModel):
    """Logging configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    format: Literal["json", "text"] = Field(default="json")
    log_file: Optional[str] = Field(default=None)
    enable_request_logging: bool = Field(default=True)
    enable_performance_logging: bool = Field(default=True)


class FeatureFlags(BaseModel):
    """Feature flags for enabling/disabling functionality."""
    
    use_mock_kb: bool = Field(default=False)
    debug_mode: bool = Field(default=False)
    enable_metrics: bool = Field(default=False)
    enable_tracing: bool = Field(default=False)
    enable_caching: bool = Field(default=True)


class ResourceLimits(BaseModel):
    """Resource usage limits."""
    
    max_queued_tasks_per_agent: int = Field(default=100, ge=10, le=1000)
    max_cached_models: int = Field(default=3, ge=1, le=10)
    max_concurrent_requests: int = Field(default=50, ge=5, le=200)
    request_rate_limit: int = Field(default=60, ge=1, le=1000)  # per minute


class Settings(BaseModel):
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
    
    if settings.api.api_key:
        os.environ['FRAMEWORK_API_KEY'] = settings.api.api_key
