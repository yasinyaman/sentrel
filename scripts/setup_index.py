#!/usr/bin/env python3
"""
Setup OpenSearch index template and ISM policy.

Run this script before starting the application to ensure
proper index configuration.

Usage:
    python scripts/setup_index.py
    python scripts/setup_index.py --hosts http://localhost:9200
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.opensearch.client import OpenSearchClient


def main():
    parser = argparse.ArgumentParser(description="Setup OpenSearch indices")
    parser.add_argument(
        "--hosts",
        default="http://localhost:9200",
        help="OpenSearch hosts (comma-separated)",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="OpenSearch username",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="OpenSearch password",
    )
    parser.add_argument(
        "--prefix",
        default="sentry-events",
        help="Index prefix",
    )

    args = parser.parse_args()

    # Create settings
    settings = Settings(
        opensearch_hosts=args.hosts.split(","),
        opensearch_username=args.username,
        opensearch_password=args.password,
        opensearch_index_prefix=args.prefix,
    )

    print(f"Connecting to OpenSearch: {settings.opensearch_hosts}")

    # Initialize client
    client = OpenSearchClient(settings)

    # Check connection
    try:
        health = client.health_check()
        print(f"Cluster health: {health.get('status')}")
        print(f"Cluster name: {health.get('cluster_name')}")
        print(f"Number of nodes: {health.get('number_of_nodes')}")
    except Exception as e:
        print(f"ERROR: Failed to connect to OpenSearch: {e}")
        sys.exit(1)

    # Setup index template
    print("\nCreating index template...")
    if client.ensure_index_template():
        print("✓ Index template created/updated")
    else:
        print("✗ Failed to create index template")

    # Setup ISM policy
    print("\nCreating ISM policy...")
    if client.ensure_ism_policy():
        print("✓ ISM policy created/updated")
    else:
        print("⚠ ISM policy creation skipped (may not be supported)")

    # Create initial index
    from datetime import datetime

    initial_index = f"{settings.opensearch_index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
    print(f"\nCreating initial index: {initial_index}")

    if client.create_index_if_not_exists(initial_index):
        print(f"✓ Index '{initial_index}' ready")
    else:
        print(f"✗ Failed to create index '{initial_index}'")

    print("\nSetup complete!")
    client.close()


if __name__ == "__main__":
    main()
