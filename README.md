# Sentrel

Self-hosted Sentry alternative - Receive error data from Sentry SDKs and store/visualize in OpenSearch.

## Features

- Fully compatible with Sentry SDKs (Python, JavaScript, Node.js, etc.)
- Supports Sentry Envelope and legacy JSON formats
- Real-time event indexing to OpenSearch
- Async processing with Celery
- GeoIP and User-Agent enrichment
- Visualization with OpenSearch Dashboards
- Easy deployment with Docker

## Quick Start

### Docker Compose (Recommended)

```bash
# Start all services
cd docker
docker-compose up -d

# View logs
docker-compose logs -f app
```

Services:
- **Sentrel App**: http://localhost:8000
- **OpenSearch**: http://localhost:9200
- **OpenSearch Dashboards**: http://localhost:5601

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env file

# Set up OpenSearch indices
python scripts/setup_index.py

# Start the application
python -m src.main
```

## Creating a DSN

Generate a DSN to configure Sentry SDKs:

```bash
python scripts/generate_dsn.py --host localhost:8000 --project 1

# Example output:
# DSN: http://abc123def456@localhost:8000/1
```

## SDK Configuration

### Python

```python
import sentry_sdk

sentry_sdk.init(
    dsn="http://YOUR_KEY@localhost:8000/1",
    environment="production",
    release="myapp@1.0.0",
)

# Test
try:
    raise ValueError("Test error")
except Exception:
    sentry_sdk.capture_exception()
```

### JavaScript

```javascript
import * as Sentry from "@sentry/browser";

Sentry.init({
    dsn: "http://YOUR_KEY@localhost:8000/1",
    environment: "production",
});
```

### Node.js

```javascript
const Sentry = require("@sentry/node");

Sentry.init({
    dsn: "http://YOUR_KEY@localhost:8000/1",
    environment: "production",
});
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/{project_id}/envelope/` | POST | Main event endpoint (Envelope format) |
| `/api/{project_id}/store/` | POST | Legacy event endpoint (JSON) |
| `/api/{project_id}/minidump/` | POST | Native crash dumps |
| `/api/{project_id}/security/` | POST | CSP/Security reports |
| `/api/{project_id}/` | GET | SDK connection check |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/metrics` | GET | Prometheus metrics |
| `/stats` | GET | Index statistics |

## Configuration

All configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `sentrel` | Application name |
| `AUTH_REQUIRED` | `true` | Require authentication |
| `ALLOWED_PUBLIC_KEYS` | - | Allowed DSN public keys |
| `ALLOWED_CORS_ORIGINS` | - | Allowed CORS origins |
| `MAX_REQUEST_SIZE` | `5242880` | Maximum request body size (bytes) |
| `OPENSEARCH_HOSTS` | `http://localhost:9200` | OpenSearch host list |
| `OPENSEARCH_USERNAME` | - | OpenSearch username |
| `OPENSEARCH_PASSWORD` | - | OpenSearch password |
| `OPENSEARCH_INDEX_PREFIX` | `sentry-events` | Index prefix |
| `OPENSEARCH_USE_SSL` | `false` | Enable SSL |
| `OPENSEARCH_VERIFY_CERTS` | `true` | Verify SSL certificates |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `USE_CELERY` | `true` | Enable async processing |
| `BATCH_SIZE` | `100` | Event batch size |
| `BATCH_TIMEOUT_SECONDS` | `5` | Batch timeout |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `1000` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |
| `PROJECT_IDS` | - | Allowed project IDs |
| `ENABLE_GEOIP` | `false` | Enable GeoIP enrichment |
| `GEOIP_DATABASE_PATH` | - | MaxMind GeoIP2 DB path |

## OpenSearch Index Structure

Events are indexed in the following format:

```json
{
  "@timestamp": "2024-01-15T10:00:00Z",
  "event_id": "abc123",
  "project_id": 1,
  "level": "error",
  "platform": "python",
  "environment": "production",
  "message": "ValueError: invalid value",
  "exception_type": "ValueError",
  "exception_value": "invalid value",
  "stacktrace": "...",
  "user": {
    "id": "user123",
    "email_hash": "abc123...",
    "ip": "192.168.1.1"
  },
  "browser": {"name": "Chrome", "version": "120"},
  "os": {"name": "Windows", "version": "10"},
  "geo": {
    "country_code": "US",
    "city": "New York",
    "location": {"lat": 40.7, "lon": -74.0}
  },
  "tags": {"server": "web-1"},
  "sdk": {"name": "sentry.python", "version": "1.0.0"}
}
```

## Dashboards

Pre-built dashboards are available in the `dashboards/` folder:

- **Error Overview** - General error overview
- **Project Metrics** - Project and release metrics
- **User Impact** - User impact and geographic analysis
- **Developer Debug** - Detailed error tracking for developers

Import dashboards:
```bash
python scripts/import_dashboards.py
```

Or manually: OpenSearch Dashboards > Stack Management > Saved Objects > Import

## Celery Workers

Start Celery workers for async processing:

```bash
# Event processing worker
celery -A src.tasks.celery_tasks worker -l info -Q events,batch -c 4

# Periodic task scheduler
celery -A src.tasks.celery_tasks beat -l info
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_envelope_parser.py -v
```

## Test Application

A test application is included to generate sample errors:

```bash
# CLI mode - send random errors
python test_app/simple_test.py --host localhost --port 8000 --project 1 --key test --count 10

# Web UI mode
python test_app/web_error_generator.py --dsn "http://test@localhost:8000/1" --port 8080
```

## Project Structure

```
sentrel/
├── src/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── receiver/            # Sentry SDK endpoints
│   ├── opensearch/          # OpenSearch client & indexer
│   ├── etl/                 # Transform & enrich pipeline
│   └── tasks/               # Celery async tasks
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── dashboards/              # OpenSearch Dashboard JSONs
├── test_app/                # Error generation test app
├── tests/                   # Unit tests
├── scripts/                 # Utility scripts
├── requirements.txt
└── pyproject.toml
```

## Security

For production deployments:

1. Set `AUTH_REQUIRED=true` and configure `ALLOWED_PUBLIC_KEYS`
2. Configure `ALLOWED_CORS_ORIGINS` (don't use `*`)
3. Enable SSL for OpenSearch (`OPENSEARCH_USE_SSL=true`, `OPENSEARCH_VERIFY_CERTS=true`)
4. Use strong passwords for Redis and OpenSearch
5. Run behind a reverse proxy (nginx, traefik) with HTTPS

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request
