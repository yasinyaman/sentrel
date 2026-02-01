#!/usr/bin/env python3
"""
Generate DSN for Sentry SDK configuration.

This script generates a DSN string that can be used to configure
Sentry SDKs to send events to the bridge.

Usage:
    python scripts/generate_dsn.py
    python scripts/generate_dsn.py --host sentry-bridge.example.com --project 1
    python scripts/generate_dsn.py --key my-custom-key --project 42
"""

import argparse
import secrets
import string


def generate_public_key(length: int = 32) -> str:
    """Generate a random public key."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_dsn(host: str, project_id: int, public_key: str, use_https: bool = True) -> str:
    """
    Generate a Sentry DSN string.

    Args:
        host: Bridge host (e.g., sentry-bridge.example.com)
        project_id: Project identifier
        public_key: Public key for authentication
        use_https: Use HTTPS protocol

    Returns:
        DSN string
    """
    protocol = "https" if use_https else "http"
    return f"{protocol}://{public_key}@{host}/{project_id}"


def main():
    parser = argparse.ArgumentParser(description="Generate Sentry DSN")
    parser.add_argument(
        "--host",
        default="localhost:8000",
        help="Bridge host (default: localhost:8000)",
    )
    parser.add_argument(
        "--project",
        type=int,
        default=1,
        help="Project ID (default: 1)",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="Public key (default: auto-generated)",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP instead of HTTPS",
    )
    parser.add_argument(
        "--key-length",
        type=int,
        default=32,
        help="Length of auto-generated key (default: 32)",
    )

    args = parser.parse_args()

    # Generate or use provided key
    public_key = args.key or generate_public_key(args.key_length)

    # Generate DSN
    dsn = generate_dsn(
        host=args.host,
        project_id=args.project,
        public_key=public_key,
        use_https=not args.http,
    )

    print("=" * 60)
    print("Generated DSN for Sentry SDK")
    print("=" * 60)
    print()
    print(f"DSN: {dsn}")
    print()
    print(f"Public Key: {public_key}")
    print(f"Project ID: {args.project}")
    print(f"Host: {args.host}")
    print()
    print("=" * 60)
    print("SDK Configuration Examples")
    print("=" * 60)
    print()
    print("Python:")
    print("-" * 40)
    print(f'''import sentry_sdk

sentry_sdk.init(
    dsn="{dsn}",
    environment="production",
    release="myapp@1.0.0",
)
''')

    print("JavaScript (Browser):")
    print("-" * 40)
    print(f'''import * as Sentry from "@sentry/browser";

Sentry.init({{
    dsn: "{dsn}",
    environment: "production",
    release: "myapp@1.0.0",
}});
''')

    print("Node.js:")
    print("-" * 40)
    print(f'''const Sentry = require("@sentry/node");

Sentry.init({{
    dsn: "{dsn}",
    environment: "production",
    release: "myapp@1.0.0",
}});
''')

    print("=" * 60)
    print()
    print("NOTE: Save the public key if you want to restrict access.")
    print("Add it to ALLOWED_PUBLIC_KEYS environment variable.")


if __name__ == "__main__":
    main()
