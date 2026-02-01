"""FastAPI application entry point for Sentry OpenSearch Bridge."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .opensearch.client import OpenSearchClient
from .receiver.endpoints import router as receiver_router

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

    yield

    # Shutdown
    logger.info("shutting_down_sentrel")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include Sentry SDK receiver endpoints
app.include_router(receiver_router, tags=["Sentry SDK"])


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns basic health status.
    """
    return {"status": "healthy", "app": settings.app_name}


@app.get("/ready")
async def readiness_check(request: Request):
    """
    Readiness check endpoint.

    Verifies OpenSearch connection.
    """
    try:
        if hasattr(request.app.state, "opensearch"):
            health = request.app.state.opensearch.health_check()
            return {
                "status": "ready",
                "opensearch": {
                    "status": health.get("status"),
                    "cluster_name": health.get("cluster_name"),
                    "number_of_nodes": health.get("number_of_nodes"),
                },
            }
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "error": "OpenSearch not initialized"},
            )

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)},
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
