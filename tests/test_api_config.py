"""
Tests for API config-driven auth and CORS behavior.
"""

import os
from unittest.mock import patch

from core.config import reload_settings


def _set_or_unset(var_name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(var_name, None)
    else:
        os.environ[var_name] = value


def test_api_settings_parse_cors_origins_csv_and_json():
    previous_cors = os.environ.get("CORS_ORIGINS")
    previous_nested = os.environ.get("API__CORS_ORIGINS")
    os.environ.pop("API__CORS_ORIGINS", None)

    os.environ["CORS_ORIGINS"] = "http://localhost:3000, https://app.example.com"
    settings = reload_settings()
    assert settings.api.cors_origins == ["http://localhost:3000", "https://app.example.com"]

    os.environ["CORS_ORIGINS"] = '["http://localhost:3000","https://app.example.com"]'
    settings = reload_settings()
    assert settings.api.cors_origins == ["http://localhost:3000", "https://app.example.com"]

    _set_or_unset("CORS_ORIGINS", previous_cors)
    _set_or_unset("API__CORS_ORIGINS", previous_nested)
    reload_settings()


def test_api_settings_reads_enable_auth_and_key_from_env():
    previous_auth = os.environ.get("ENABLE_AUTH")
    previous_key = os.environ.get("FRAMEWORK_API_KEY")
    previous_nested_auth = os.environ.get("API__ENABLE_AUTH")
    previous_nested_key = os.environ.get("API__API_KEY")
    os.environ.pop("API__ENABLE_AUTH", None)
    os.environ.pop("API__API_KEY", None)

    os.environ["ENABLE_AUTH"] = "true"
    os.environ["FRAMEWORK_API_KEY"] = "test-auth-key"
    settings = reload_settings()

    assert settings.api.enable_auth is True
    assert settings.api.api_key == "test-auth-key"

    _set_or_unset("ENABLE_AUTH", previous_auth)
    _set_or_unset("FRAMEWORK_API_KEY", previous_key)
    _set_or_unset("API__ENABLE_AUTH", previous_nested_auth)
    _set_or_unset("API__API_KEY", previous_nested_key)
    reload_settings()


def test_api_startup_fails_when_auth_enabled_without_key():
    previous_auth = os.environ.get("ENABLE_AUTH")
    previous_key = os.environ.get("FRAMEWORK_API_KEY")
    previous_nested_auth = os.environ.get("API__ENABLE_AUTH")
    previous_nested_key = os.environ.get("API__API_KEY")
    previous_cors = os.environ.get("CORS_ORIGINS")
    previous_nested_cors = os.environ.get("API__CORS_ORIGINS")

    os.environ["ENABLE_AUTH"] = "true"
    os.environ.pop("FRAMEWORK_API_KEY", None)
    os.environ.pop("API__ENABLE_AUTH", None)
    os.environ.pop("API__API_KEY", None)
    os.environ["CORS_ORIGINS"] = '["*"]'
    os.environ.pop("API__CORS_ORIGINS", None)

    import importlib
    import pytest

    import api_server
    with patch("core.config.get_settings", side_effect=RuntimeError("Authentication is enabled but no API key is configured")):
        with pytest.raises(RuntimeError, match="Authentication is enabled"):
            importlib.reload(api_server)

    _set_or_unset("ENABLE_AUTH", previous_auth)
    _set_or_unset("FRAMEWORK_API_KEY", previous_key)
    _set_or_unset("API__ENABLE_AUTH", previous_nested_auth)
    _set_or_unset("API__API_KEY", previous_nested_key)
    _set_or_unset("CORS_ORIGINS", previous_cors)
    _set_or_unset("API__CORS_ORIGINS", previous_nested_cors)
    reload_settings()
