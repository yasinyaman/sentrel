"""FastAPI application entry point for Sentry OpenSearch Bridge."""

import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Lock
from typing import Dict, Tuple

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .opensearch.client import OpenSearchClient
from .receiver.endpoints import router as receiver_router


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    
    For production with multiple instances, use Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_window: int = 1000, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self.lock = Lock()
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Use X-Forwarded-For if behind a proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_rate_limited(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if client is rate limited.
        
        Returns:
            Tuple of (is_limited, remaining_requests)
        """
        current_time = time.time()
        
        with self.lock:
            count, window_start = self.requests[client_id]
            
            # Check if we're in a new window
            if current_time - window_start >= self.window_seconds:
                # Reset for new window
                self.requests[client_id] = (1, current_time)
                return False, self.requests_per_window - 1
            
            # Check if limit exceeded
            if count >= self.requests_per_window:
                return True, 0
            
            # Increment counter
            self.requests[client_id] = (count + 1, window_start)
            return False, self.requests_per_window - count - 1
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        is_limited, remaining = self._is_rate_limited(client_id)
        
        if is_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": self.window_seconds,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                },
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Set log level
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(message)s",
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "starting_sentrel",
        app_name=settings.app_name,
        host=settings.host,
        port=settings.port,
    )

    # Initialize OpenSearch client
    os_client = OpenSearchClient(settings)

    try:
        # Ensure index template exists
        os_client.ensure_index_template()

        # Try to create ISM policy (optional)
        os_client.ensure_ism_policy()

        # Store client in app state
        app.state.opensearch = os_client

        logger.info("opensearch_connected", hosts=settings.opensearch_hosts)

    except Exception as e:
        logger.error("opensearch_connection_failed", error=str(e))
        # Continue anyway - will retry on first request

    # Initialize event batcher (if not using Celery)
    if not settings.use_celery:
        from .receiver.batcher import get_batcher
        
        batcher = await get_batcher(
            batch_size=settings.batch_size,
            batch_timeout_seconds=settings.batch_timeout_seconds,
        )
        app.state.batcher = batcher
        logger.info(
            "event_batcher_started",
            batch_size=settings.batch_size,
            timeout=settings.batch_timeout_seconds,
        )

    yield

    # Shutdown
    logger.info("shutting_down_sentrel")

    # Stop event batcher
    if hasattr(app.state, "batcher"):
        from .receiver.batcher import shutdown_batcher
        await shutdown_batcher()

    if hasattr(app.state, "opensearch"):
        app.state.opensearch.close()


# Create FastAPI application
app = FastAPI(
    title="Sentrel",
    description="Self-hosted Sentry alternative - Receive SDK events and store in OpenSearch",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
# In production, configure ALLOWED_CORS_ORIGINS environment variable
# Empty list = deny all cross-origin requests (recommended for production)
cors_origins = settings.allowed_cors_origins if settings.allowed_cors_origins else []

# Allow all origins only in debug mode with no configured origins
if settings.debug and not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-Sentry-Auth", "Content-Type", "Authorization"],
)

# Rate limiting middleware (only if enabled)
if settings.rate_limit_enabled:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window,
    )

# Include Sentry SDK receiver endpoints
app.include_router(receiver_router, tags=["Sentry SDK"])


@app.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns basic health status and application info.
    """
    health_status = {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
    }
    
    # Check if batcher is running (if enabled)
    if hasattr(request.app.state, "batcher"):
        health_status["batcher"] = {
            "running": request.app.state.batcher.is_running,
            "pending_events": request.app.state.batcher.pending_count,
        }
    
    return health_status


@app.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check endpoint.

    Verifies all dependencies are connected and ready.
    """
    checks = {}
    is_ready = True
    
    # Check OpenSearch
    try:
        if hasattr(request.app.state, "opensearch"):
            health = request.app.state.opensearch.health_check()
            os_status = health.get("status", "unknown")
            checks["opensearch"] = {
                "status": "ok" if os_status in ["green", "yellow"] else "degraded",
                "cluster_status": os_status,
                "cluster_name": health.get("cluster_name"),
                "number_of_nodes": health.get("number_of_nodes"),
            }
            if os_status == "red":
                is_ready = False
        else:
            checks["opensearch"] = {"status": "not_initialized"}
            is_ready = False
    except Exception as e:
        checks["opensearch"] = {"status": "error", "error": str(e)}
        is_ready = False
    
    # Check Redis (if Celery is enabled)
    if settings.use_celery:
        try:
            import redis as redis_lib
            r = redis_lib.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                socket_timeout=2,
            )
            r.ping()
            checks["redis"] = {"status": "ok"}
            r.close()
        except Exception as e:
            checks["redis"] = {"status": "error", "error": str(e)}
            is_ready = False
    
    # Check batcher health (if enabled)
    if hasattr(request.app.state, "batcher"):
        batcher = request.app.state.batcher
        checks["batcher"] = {
            "status": "ok" if batcher.is_running else "stopped",
            "pending_events": batcher.pending_count,
        }
    
    if is_ready:
        return {"status": "ready", "checks": checks}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": checks},
        )


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format.
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    except ImportError:
        return JSONResponse(
            status_code=501,
            content={"error": "prometheus_client not installed"},
        )


@app.get("/stats")
async def stats(request: Request):
    """
    Application statistics endpoint.

    Returns index statistics.
    """
    try:
        if hasattr(request.app.state, "opensearch"):
            client = request.app.state.opensearch
            index_stats = client.get_index_stats()

            return {
                "indices": len(index_stats.get("indices", {})),
                "total_docs": index_stats.get("_all", {})
                .get("primaries", {})
                .get("docs", {})
                .get("count", 0),
                "total_size_bytes": index_stats.get("_all", {})
                .get("primaries", {})
                .get("store", {})
                .get("size_in_bytes", 0),
            }
        else:
            return {"error": "OpenSearch not initialized"}

    except Exception as e:
        return {"error": str(e)}


def main():
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
