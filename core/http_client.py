"""
HTTP Client Manager with Connection Pooling.

This module provides a singleton HTTP client with connection pooling
to improve performance and reduce connection overhead.
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """Singleton HTTP client manager with connection pooling."""
    
    _instance: Optional['HTTPClientManager'] = None
    _lock = asyncio.Lock()
    _async_client: Optional[httpx.AsyncClient] = None
    _sync_client: Optional[httpx.Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HTTPClientManager, cls).__new__(cls)
        return cls._instance
    
    def get_async_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client with connection pooling."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=30.0
                ),
                http2=True,  # Enable HTTP/2 for better performance
                follow_redirects=True
            )
            logger.info("Async HTTP client initialized with connection pooling")
        return self._async_client
    
    def get_sync_client(self) -> httpx.Client:
        """Get or create the sync HTTP client with connection pooling."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=httpx.Timeout(30.0, connect=5.0),
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=30.0
                ),
                http2=True,
                follow_redirects=True
            )
            logger.info("Sync HTTP client initialized with connection pooling")
        return self._sync_client
    
    async def close_async_client(self):
        """Close the async HTTP client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None
            logger.info("Async HTTP client closed")
    
    def close_sync_client(self):
        """Close the sync HTTP client."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None
            logger.info("Sync HTTP client closed")
    
    async def close_all(self):
        """Close all HTTP clients."""
        await self.close_async_client()
        self.close_sync_client()


# Global singleton instance
_http_client_manager = HTTPClientManager()


def get_async_http_client() -> httpx.AsyncClient:
    """
    Get the shared async HTTP client with connection pooling.
    
    This client should be used for all async HTTP operations to benefit
    from connection pooling and improved performance.
    
    Example:
        client = get_async_http_client()
        response = await client.get("https://api.example.com/data")
    """
    return _http_client_manager.get_async_client()


def get_sync_http_client() -> httpx.Client:
    """
    Get the shared sync HTTP client with connection pooling.
    
    This client should be used for all sync HTTP operations to benefit
    from connection pooling and improved performance.
    
    Example:
        client = get_sync_http_client()
        response = client.get("https://api.example.com/data")
    """
    return _http_client_manager.get_sync_client()


async def close_http_clients():
    """
    Close all HTTP clients.
    
    This should be called during application shutdown to properly
    cleanup resources.
    """
    await _http_client_manager.close_all()


@asynccontextmanager
async def http_client_lifespan():
    """
    Context manager for HTTP client lifecycle.
    
    Example usage with FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with http_client_lifespan():
                yield
        
        app = FastAPI(lifespan=lifespan)
    """
    try:
        yield
    finally:
        await close_http_clients()


# Convenience functions for common HTTP operations

async def async_get(url: str, **kwargs) -> httpx.Response:
    """Perform an async GET request using the pooled client."""
    client = get_async_http_client()
    return await client.get(url, **kwargs)


async def async_post(url: str, **kwargs) -> httpx.Response:
    """Perform an async POST request using the pooled client."""
    client = get_async_http_client()
    return await client.post(url, **kwargs)


async def async_put(url: str, **kwargs) -> httpx.Response:
    """Perform an async PUT request using the pooled client."""
    client = get_async_http_client()
    return await client.put(url, **kwargs)


async def async_delete(url: str, **kwargs) -> httpx.Response:
    """Perform an async DELETE request using the pooled client."""
    client = get_async_http_client()
    return await client.delete(url, **kwargs)


def sync_get(url: str, **kwargs) -> httpx.Response:
    """Perform a sync GET request using the pooled client."""
    client = get_sync_http_client()
    return client.get(url, **kwargs)


def sync_post(url: str, **kwargs) -> httpx.Response:
    """Perform a sync POST request using the pooled client."""
    client = get_sync_http_client()
    return client.post(url, **kwargs)


def sync_put(url: str, **kwargs) -> httpx.Response:
    """Perform a sync PUT request using the pooled client."""
    client = get_sync_http_client()
    return client.put(url, **kwargs)


def sync_delete(url: str, **kwargs) -> httpx.Response:
    """Perform a sync DELETE request using the pooled client."""
    client = get_sync_http_client()
    return client.delete(url, **kwargs)
