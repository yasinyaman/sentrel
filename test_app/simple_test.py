#!/usr/bin/env python3
"""
Sentrel Simple Test - Direct HTTP Requests

Tests Sentrel by sending direct HTTP requests without the Sentry SDK.
Useful for debugging SDK issues.

Usage:
    python simple_test.py --host localhost --port 8000 --project 1
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("httpx not installed. Install with: pip install httpx")
    sys.exit(1)


# =============================================================================
# Sample Event Data
# =============================================================================

SAMPLE_USERS = [
    {"id": "1001", "email": "john@example.com", "username": "john_doe", "ip_address": "192.168.1.100"},
    {"id": "1002", "email": "jane@example.com", "username": "jane_smith", "ip_address": "192.168.1.101"},
    {"id": "1003", "email": "bob@example.com", "username": "bob_wilson", "ip_address": "10.0.0.50"},
]

SAMPLE_ERRORS = [
    {
        "type": "DatabaseConnectionError",
        "value": "PostgreSQL connection failed: connection refused (localhost:5432)",
        "module": "app.database",
    },
    {
        "type": "APIRateLimitError",
        "value": "Rate limit exceeded: 429 Too Many Requests - Stripe API",
        "module": "app.integrations.stripe",
    },
    {
        "type": "PaymentProcessingError",
        "value": "Payment processing failed: Insufficient balance",
        "module": "app.payments",
    },
    {
        "type": "AuthenticationFailedError",
        "value": "JWT token invalid or expired",
        "module": "app.auth",
    },
    {
        "type": "ZeroDivisionError",
        "value": "division by zero",
        "module": "builtins",
    },
    {
        "type": "KeyError",
        "value": "'missing_key'",
        "module": "builtins",
    },
    {
        "type": "ValueError",
        "value": "invalid literal for int() with base 10: 'not_a_number'",
        "module": "builtins",
    },
    {
        "type": "TimeoutError",
        "value": "Connection timed out after 30 seconds",
        "module": "app.http",
    },
]


# =============================================================================
# Event Creation
# =============================================================================

def create_event(level: str = "error") -> dict:
    """Create a Sentry-compatible event."""
    error = random.choice(SAMPLE_ERRORS)
    user = random.choice(SAMPLE_USERS)
    event_id = uuid.uuid4().hex

    return {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": "python",
        "level": level,
        "logger": "test.error_generator",
        "server_name": "test-server",
        "release": "test-app@1.0.0",
        "environment": "test",
        "user": user,
        "tags": {
            "error_type": error["type"],
            "test_run": "true",
            "generated_at": datetime.now().isoformat(),
        },
        "extra": {
            "custom_field": "test_value",
            "random_number": random.randint(1, 100),
        },
        "contexts": {
            "os": {
                "name": "macOS",
                "version": "14.0",
            },
            "runtime": {
                "name": "CPython",
                "version": "3.11.0",
            },
        },
        "exception": {
            "values": [
                {
                    "type": error["type"],
                    "value": error["value"],
                    "module": error["module"],
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "test_app.py",
                                "function": "main",
                                "lineno": 42,
                                "context_line": "    result = process_data()",
                                "pre_context": ["def main():", "    data = load_data()"],
                                "post_context": ["    return result", ""],
                            },
                            {
                                "filename": "processor.py",
                                "function": "process_data",
                                "lineno": 128,
                                "context_line": f"    raise {error['type']}('{error['value']}')",
                                "pre_context": ["def process_data():", "    # Processing logic"],
                                "post_context": ["", ""],
                            },
                        ]
                    },
                }
            ]
        },
        "sdk": {
            "name": "sentrel-test",
            "version": "1.0.0",
        },
    }


def create_envelope(event: dict, dsn_public_key: str, project_id: int) -> bytes:
    """Create data in Sentry envelope format."""
    # Envelope header
    envelope_header = {
        "event_id": event["event_id"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "dsn": f"http://{dsn_public_key}@localhost/{project_id}",
    }

    # Item header
    item_header = {
        "type": "event",
        "content_type": "application/json",
    }

    # Event payload
    event_payload = json.dumps(event)

    # Envelope format: header\nitem_header\npayload\n
    envelope = f"{json.dumps(envelope_header)}\n{json.dumps(item_header)}\n{event_payload}\n"

    return envelope.encode("utf-8")


# =============================================================================
# HTTP Requests
# =============================================================================

def send_store_event(host: str, port: int, project_id: int, public_key: str, event: dict) -> bool:
    """Send event to legacy store endpoint."""
    url = f"http://{host}:{port}/api/{project_id}/store/"

    headers = {
        "Content-Type": "application/json",
        "X-Sentry-Auth": f"Sentry sentry_key={public_key}, sentry_version=7",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=event, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"  [OK] Event sent: {data.get('id', 'unknown')}")
                return True
            else:
                print(f"  [ERROR] {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return False


def send_envelope(host: str, port: int, project_id: int, public_key: str, event: dict) -> bool:
    """Send event to envelope endpoint."""
    url = f"http://{host}:{port}/api/{project_id}/envelope/"

    envelope = create_envelope(event, public_key, project_id)

    headers = {
        "Content-Type": "application/x-sentry-envelope",
        "X-Sentry-Auth": f"Sentry sentry_key={public_key}, sentry_version=7",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, content=envelope, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"  [OK] Envelope sent: {data.get('id', 'unknown')}")
                return True
            else:
                print(f"  [ERROR] {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return False


def test_health(host: str, port: int, project_id: int) -> bool:
    """Server health check."""
    url = f"http://{host}:{port}/api/{project_id}/"

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)

            if response.status_code == 200:
                print(f"[OK] Server healthy: {response.json()}")
                return True
            else:
                print(f"[ERROR] Server not responding: {response.status_code}")
                return False

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


# =============================================================================
# Main Functions
# =============================================================================

def run_test(host: str, port: int, project_id: int, public_key: str,
             count: int = 5, use_envelope: bool = True, delay: float = 0.5):
    """Run test."""
    print(f"\n=== Sentrel Test Starting ===")
    print(f"   Host: {host}:{port}")
    print(f"   Project ID: {project_id}")
    print(f"   Public Key: {public_key}")
    print(f"   Format: {'Envelope' if use_envelope else 'Store (Legacy)'}")
    print(f"   Count: {count}")
    print("-" * 50)

    # Health check
    print("\n[*] Health check...")
    if not test_health(host, port, project_id):
        print("[!] Server not reachable, continuing anyway...")

    # Send events
    print(f"\n[*] Sending {count} events...")
    success = 0

    for i in range(count):
        print(f"\n[{i+1}/{count}]", end="")
        event = create_event()

        if use_envelope:
            if send_envelope(host, port, project_id, public_key, event):
                success += 1
        else:
            if send_store_event(host, port, project_id, public_key, event):
                success += 1

        if i < count - 1:
            time.sleep(delay)

    # Result
    print(f"\n{'='*50}")
    print(f"[*] Result: {success}/{count} events sent successfully")

    return success


def main():
    parser = argparse.ArgumentParser(
        description="Sentrel Simple Test - Direct HTTP Requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple test (5 events)
  python simple_test.py --host localhost --port 8000 --project 1 --key test123

  # 20 events with envelope format
  python simple_test.py --host localhost --port 8000 --project 1 --key test123 -n 20

  # Legacy store format
  python simple_test.py --host localhost --port 8000 --project 1 --key test123 --legacy

  # Health check only
  python simple_test.py --host localhost --port 8000 --project 1 --health
        """
    )

    parser.add_argument("--host", default="localhost", help="Sentrel host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Sentrel port (default: 8000)")
    parser.add_argument("--project", "-p", type=int, default=1, help="Project ID (default: 1)")
    parser.add_argument("--key", "-k", default="test", help="DSN public key (default: test)")
    parser.add_argument("--count", "-n", type=int, default=5, help="Number of events to send (default: 5)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between events (default: 0.5s)")
    parser.add_argument("--legacy", action="store_true", help="Use legacy store format (instead of envelope)")
    parser.add_argument("--health", action="store_true", help="Health check only")

    args = parser.parse_args()

    if args.health:
        test_health(args.host, args.port, args.project)
        return

    run_test(
        host=args.host,
        port=args.port,
        project_id=args.project,
        public_key=args.key,
        count=args.count,
        use_envelope=not args.legacy,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
