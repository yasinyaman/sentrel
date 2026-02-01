# Sentrel Test Application - Error Generator

This application generates various errors for testing Sentrel and sends them via the Sentry SDK.

## Installation

```bash
cd test_app
pip install -r requirements.txt
```

## Getting a DSN

Sentrel DSN format:
```
http://PUBLIC_KEY@localhost:8000/PROJECT_ID
```

Generate a DSN using the `generate_dsn.py` script:
```bash
python scripts/generate_dsn.py
```

## 1. CLI Error Generator

Generate errors from the command line:

### Send Single Error

```bash
# Database error
python error_generator.py --dsn "http://KEY@localhost:8000/1" --type database

# Payment error
python error_generator.py --dsn "http://KEY@localhost:8000/1" --type payment

# Authentication error
python error_generator.py --dsn "http://KEY@localhost:8000/1" --type auth
```

### Send Random Errors

```bash
# 10 random errors
python error_generator.py --dsn "http://KEY@localhost:8000/1" --random 10

# 50 errors with 1 second delay
python error_generator.py --dsn "http://KEY@localhost:8000/1" --random 50 --delay 1.0
```

### Burst Mode

```bash
python error_generator.py --dsn "http://KEY@localhost:8000/1" --burst
```

### Interactive Mode

```bash
python error_generator.py --dsn "http://KEY@localhost:8000/1" --interactive
```

Available commands in interactive mode:
- `list` - List error types
- `send <type>` - Send specific error type
- `random <count>` - Send random errors
- `burst` - Quick error burst
- `message` - Send test message
- `quit` - Exit

### List Error Types

```bash
python error_generator.py --list
```

## 2. Web-Based Error Generator

Generate errors with a visual interface:

```bash
python web_error_generator.py --dsn "http://KEY@localhost:8000/1" --port 8080
```

Then open `http://localhost:8080` in your browser.

### Web UI Features

- One-click quick error sending
- Custom error messages and user info
- Burst mode (multiple error burst)
- Real-time statistics
- Operation history

## 3. Simple HTTP Test

Direct HTTP requests without Sentry SDK:

```bash
python simple_test.py --host localhost --port 8000 --project 1 --key test --count 5
```

## Supported Error Types

| Type | Description | Level |
|------|-------------|-------|
| `database` | Database connection error | error |
| `rate_limit` | API rate limit error | warning |
| `payment` | Payment processing error | error |
| `auth` | Authentication error | warning |
| `validation` | Data validation error | warning |
| `file_upload` | File upload error | error |
| `cache` | Cache error | warning |
| `external` | External service error | error |
| `division` | Division by zero error | error |
| `key` | KeyError - missing key | error |
| `index` | IndexError - invalid index | error |
| `type` | TypeError - type mismatch | error |
| `attribute` | AttributeError - None object | error |
| `value` | ValueError - invalid value | error |
| `timeout` | Timeout error | error |
| `memory` | Memory error | fatal |
| `recursion` | Infinite loop error | fatal |

## Docker Usage

```bash
# Run test app from Docker container
docker run --rm -it --network sentrel_default \
  -v $(pwd)/test_app:/app \
  python:3.11-slim \
  bash -c "pip install sentry-sdk && python /app/error_generator.py --dsn 'http://KEY@sentrel:8000/1' --random 5"
```

## Example Test Scenario

1. Start Sentrel:
   ```bash
   cd docker && docker-compose up -d
   ```

2. Generate a DSN:
   ```bash
   python scripts/generate_dsn.py
   ```

3. Run the test application:
   ```bash
   python test_app/error_generator.py --dsn "http://GENERATED_KEY@localhost:8000/1" --random 20
   ```

4. View errors in OpenSearch Dashboards:
   ```
   http://localhost:5601
   ```

## Notes

- Errors are sent using the real Sentry SDK
- Each error is assigned a random user
- Timestamps and tags are added automatically
- Debug mode is active for detailed console output
