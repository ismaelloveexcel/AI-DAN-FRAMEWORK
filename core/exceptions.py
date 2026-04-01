"""
Custom exceptions for the Agentic Framework.

This module provides structured exception handling for better error
classification, debugging, and appropriate HTTP responses.
"""

from typing import Optional, Dict, Any


class AgentError(Exception):
    """Base exception for all agent-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class AgentTimeoutError(AgentError):
    """Raised when an agent operation times out."""
    pass


class AgentConfigurationError(AgentError):
    """Raised when there's an error in agent configuration."""
    pass


class AgentResourceError(AgentError):
    """Raised when a required resource is unavailable."""
    pass


class AgentValidationError(AgentError):
    """Raised when input validation fails."""
    pass


class AgentModelError(AgentError):
    """Raised when there's an error with the LLM model."""
    pass


class AgentToolError(AgentError):
    """Raised when a tool execution fails."""
    pass


class AgentCommunicationError(AgentError):
    """Raised when inter-agent communication fails."""
    pass


class AgentKnowledgeBaseError(AgentError):
    """Raised when there's an error accessing the knowledge base."""
    pass


class HTTPClientError(AgentError):
    """Raised when an HTTP client operation fails."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# Convenience functions for common error scenarios

def raise_timeout_error(operation: str, timeout_seconds: int):
    """Raise a timeout error with consistent formatting."""
    raise AgentTimeoutError(
        f"Operation '{operation}' timed out after {timeout_seconds} seconds"
    )


def raise_configuration_error(config_key: str, reason: str):
    """Raise a configuration error with consistent formatting."""
    raise AgentConfigurationError(
        f"Invalid configuration for '{config_key}': {reason}"
    )


def raise_resource_error(resource_name: str, reason: str):
    """Raise a resource error with consistent formatting."""
    raise AgentResourceError(
        f"Resource '{resource_name}' unavailable: {reason}"
    )


def raise_validation_error(field_name: str, value: Any, reason: str):
    """Raise a validation error with consistent formatting."""
    raise AgentValidationError(
        f"Validation failed for field '{field_name}' with value '{value}': {reason}",
        details={"field": field_name, "value": str(value)}
    )
