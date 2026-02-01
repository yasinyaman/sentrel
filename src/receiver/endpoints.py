"""FastAPI endpoints for receiving Sentry SDK events."""

import uuid
from typing import Dict, Optional

import structlog
from fastapi import APIRouter, Header, HTTPException, Request, Response

from ..config import settings
from .auth import DSNAuth
from .envelope_parser import EnvelopeParser
from .event_parser import EventParser

logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize components
dsn_auth = DSNAuth(
    allowed_keys=settings.allowed_public_keys,
    auth_required=settings.auth_required,
)
envelope_parser = EnvelopeParser()
event_parser = EventParser()


def get_query_params(request: Request) -> Dict[str, str]:
    """Extract query parameters from request."""
    return dict(request.query_params)


def validate_project(project_id: int) -> bool:
    """Validate project ID against allowed list."""
    if not settings.project_ids:
        return True
    return project_id in settings.project_ids


async def validate_request_size(request: Request) -> bytes:
    """
    Validate and read request body with size limit.

    Args:
        request: FastAPI request object

    Returns:
        Request body bytes

    Raises:
        HTTPException: If body exceeds max_request_size
    """
    content_length = request.headers.get("content-length")
    
    if content_length:
        try:
            if int(content_length) > settings.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body too large. Maximum size: {settings.max_request_size} bytes"
                )
        except ValueError:
            pass
    
    body = await request.body()
    
    if len(body) > settings.max_request_size:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large. Maximum size: {settings.max_request_size} bytes"
        )
    
    return body


async def authenticate_request(
    request: Request,
    x_sentry_auth: Optional[str] = None,
) -> str:
    """
    Authenticate a request and return the public key.

    Args:
        request: FastAPI request object
        x_sentry_auth: X-Sentry-Auth header value

    Returns:
        The validated public key

    Raises:
        HTTPException: If authentication fails
    """
    query_params = get_query_params(request)
    public_key = dsn_auth.extract_public_key(x_sentry_auth, query_params)

    if not dsn_auth.validate_key(public_key):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    return public_key or ""


@router.post("/api/{project_id}/envelope/")
async def receive_envelope(
    project_id: int,
    request: Request,
    x_sentry_auth: Optional[str] = Header(None, alias="X-Sentry-Auth"),
    content_type: str = Header(default="application/x-sentry-envelope"),
) -> Response:
    """
    Receive Sentry SDK envelopes.

    Envelope format:
    - First line: JSON header (event_id, dsn, sent_at)
    - Following lines: item header + item payload pairs

    Content-Type: application/x-sentry-envelope
    """
    # Validate project
    if not validate_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # Authenticate request
    await authenticate_request(request, x_sentry_auth)

    # Read and validate body size
    body = await validate_request_size(request)

    if not body:
        return Response(
            content='{"id": null}',
            media_type="application/json",
        )

    # Parse envelope
    try:
        envelope = envelope_parser.parse(body)
    except Exception as e:
        logger.error(f"Failed to parse envelope: {e}")
        raise HTTPException(status_code=400, detail="Invalid envelope format")

    # Extract and process events
    event_payloads = envelope_parser.extract_events(envelope)
    event_ids = []

    for payload in event_payloads:
        try:
            event = event_parser.parse(payload)
            event_id = event.event_id or envelope.header.event_id or str(uuid.uuid4())
            event_ids.append(event_id)

            # Queue for processing
            await _process_event(event, project_id, event_id)

        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            continue

    # Return success response
    # Sentry SDK expects event_id in response
    response_id = event_ids[0] if event_ids else envelope.header.event_id

    return Response(
        content=f'{{"id": "{response_id}"}}',
        media_type="application/json",
    )


@router.post("/api/{project_id}/store/")
async def receive_store(
    project_id: int,
    request: Request,
    x_sentry_auth: Optional[str] = Header(None, alias="X-Sentry-Auth"),
) -> Response:
    """
    Legacy Sentry event format (JSON).

    For older SDK versions that don't use envelope format.
    """
    # Validate project
    if not validate_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # Authenticate request
    await authenticate_request(request, x_sentry_auth)

    # Read and validate body size
    body = await validate_request_size(request)

    if not body:
        return Response(
            content='{"id": null}',
            media_type="application/json",
        )

    # Parse event directly
    try:
        event = event_parser.parse(body)
        event_id = event.event_id or str(uuid.uuid4())

        # Queue for processing
        await _process_event(event, project_id, event_id)

        return Response(
            content=f'{{"id": "{event_id}"}}',
            media_type="application/json",
        )

    except Exception as e:
        logger.error(f"Failed to process store event: {e}")
        raise HTTPException(status_code=400, detail="Invalid event format")


@router.post("/api/{project_id}/minidump/")
async def receive_minidump(
    project_id: int,
    request: Request,
    x_sentry_auth: Optional[str] = Header(None, alias="X-Sentry-Auth"),
) -> Response:
    """
    Native crash dump endpoint.

    Currently just acknowledges receipt.
    Full minidump processing is optional.
    """
    # Validate project
    if not validate_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # Authenticate request
    await authenticate_request(request, x_sentry_auth)

    # Validate request size (minidumps can be large, use 50MB limit)
    content_length = request.headers.get("content-length")
    max_minidump_size = 50 * 1024 * 1024  # 50MB
    
    if content_length:
        try:
            if int(content_length) > max_minidump_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Minidump too large. Maximum size: {max_minidump_size} bytes"
                )
        except ValueError:
            pass

    logger.info(f"Received minidump for project {project_id}")

    # Just acknowledge for now
    return Response(
        content='{"id": null, "status": "acknowledged"}',
        media_type="application/json",
    )


@router.post("/api/{project_id}/security/")
async def receive_security(
    project_id: int,
    request: Request,
    x_sentry_auth: Optional[str] = Header(None, alias="X-Sentry-Auth"),
) -> Response:
    """
    CSP violation and security report endpoint.
    """
    # Validate project
    if not validate_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    # Authenticate request
    await authenticate_request(request, x_sentry_auth)

    # Read and validate body size
    body = await validate_request_size(request)

    if body:
        logger.info(f"Received security report for project {project_id}")
        # TODO: Process security reports

    return Response(
        content='{"id": null}',
        media_type="application/json",
    )


@router.get("/api/{project_id}/")
async def project_health(project_id: int) -> dict:
    """
    SDK connection check endpoint.

    SDKs may call this to verify connectivity.
    """
    if not validate_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    return {"project_id": project_id, "status": "ok"}


async def _process_event(event, project_id: int, event_id: str) -> None:
    """
    Process event - via Celery, batcher, or immediately.

    Args:
        event: SentryEvent object
        project_id: Project identifier
        event_id: Event identifier for logging
    """
    from ..config import settings

    logger.info(f"Processing event {event_id} for project {project_id}")

    # Convert event to dict for serialization
    event_dict = event.model_dump() if hasattr(event, "model_dump") else event.dict()

    if settings.use_celery:
        # Use Celery for distributed processing
        try:
            from ..tasks.celery_tasks import process_event_task
            process_event_task.delay(event_dict, project_id)
            return
        except ImportError:
            logger.warning("Celery not configured, using batcher")
    
    # Use batcher for efficient bulk processing
    try:
        from .batcher import get_batcher
        batcher = await get_batcher(
            batch_size=settings.batch_size,
            batch_timeout_seconds=settings.batch_timeout_seconds,
        )
        await batcher.add(event_dict, project_id, event_id)
    except Exception as e:
        # Fallback to immediate processing
        logger.warning(f"Batcher error, processing immediately: {e}")
        await _process_event_sync(event, project_id)


async def _process_event_sync(event, project_id: int) -> None:
    """
    Process event using async pipeline.
    
    Uses async OpenSearch operations to avoid blocking the event loop.
    """
    try:
        from ..etl.pipeline import get_pipeline

        pipeline = get_pipeline()
        # Use async method to avoid blocking
        await pipeline.process_event_async(event, project_id)
    except ImportError:
        logger.warning("Pipeline not configured yet")
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
