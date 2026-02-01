#!/usr/bin/env python3
"""
OpenSearch Dashboards - Dashboard Import Script

This script imports pre-built dashboards into OpenSearch Dashboards.

Usage:
    python import_dashboards.py
    python import_dashboards.py --url http://localhost:5601
"""

import argparse
import glob
import os
import sys

try:
    import httpx
except ImportError:
    print("httpx not installed. Install with: pip install httpx")
    sys.exit(1)


def import_dashboard(url: str, filepath: str) -> bool:
    """
    Import a single dashboard file.

    Args:
        url: OpenSearch Dashboards URL
        filepath: Path to NDJSON file

    Returns:
        True if successful
    """
    filename = os.path.basename(filepath)
    print(f"\n[*] Importing: {filename}")

    # Read file
    with open(filepath, "rb") as f:
        content = f.read()

    # Import endpoint
    import_url = f"{url}/api/saved_objects/_import?overwrite=true"

    headers = {
        "osd-xsrf": "true",  # Required for CSRF protection
    }

    # Send as multipart form-data
    files = {
        "file": (filename, content, "application/ndjson")
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(import_url, headers=headers, files=files)

            if response.status_code == 200:
                data = response.json()
                success_count = data.get("successCount", 0)
                print(f"   [OK] Success: {success_count} objects imported")

                # Show errors if any
                errors = data.get("errors", [])
                if errors:
                    for err in errors:
                        print(f"   [!] Error: {err.get('error', {}).get('message', 'Unknown')}")

                return True
            else:
                print(f"   [ERROR] {response.status_code}")
                print(f"   {response.text[:200]}")
                return False

    except httpx.ConnectError:
        print(f"   [ERROR] Connection failed: Cannot reach {url}")
        return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False


def create_index_pattern(url: str, pattern: str = "sentry-events-*") -> bool:
    """
    Create index pattern.

    Args:
        url: OpenSearch Dashboards URL
        pattern: Index pattern

    Returns:
        True if successful
    """
    print(f"\n[*] Creating index pattern: {pattern}")

    create_url = f"{url}/api/saved_objects/index-pattern/{pattern}"

    headers = {
        "osd-xsrf": "true",
        "Content-Type": "application/json",
    }

    body = {
        "attributes": {
            "title": pattern,
            "timeFieldName": "@timestamp",
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(create_url, headers=headers, json=body)

            if response.status_code in [200, 201]:
                print(f"   [OK] Index pattern created: {pattern}")
                return True
            elif response.status_code == 409:
                print(f"   [OK] Index pattern already exists: {pattern}")
                return True
            else:
                print(f"   [ERROR] {response.status_code}")
                return False

    except Exception as e:
        print(f"   [ERROR] {e}")
        return False


def set_default_index_pattern(url: str, pattern: str = "sentry-events-*") -> bool:
    """
    Set default index pattern.
    """
    print(f"\n[*] Setting default index pattern: {pattern}")

    config_url = f"{url}/api/opensearch-dashboards/settings"

    headers = {
        "osd-xsrf": "true",
        "Content-Type": "application/json",
    }

    body = {
        "changes": {
            "defaultIndex": pattern
        }
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(config_url, headers=headers, json=body)

            if response.status_code == 200:
                print(f"   [OK] Default index pattern set")
                return True
            else:
                print(f"   [!] Could not set default: {response.status_code}")
                return False

    except Exception as e:
        print(f"   [!] Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="OpenSearch Dashboards - Dashboard Import Script"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5601",
        help="OpenSearch Dashboards URL (default: http://localhost:5601)"
    )
    parser.add_argument(
        "--dashboards-dir",
        default=None,
        help="Dashboard files directory"
    )
    parser.add_argument(
        "--skip-index-pattern",
        action="store_true",
        help="Skip index pattern creation"
    )

    args = parser.parse_args()

    # Find dashboards directory
    if args.dashboards_dir:
        dashboards_dir = args.dashboards_dir
    else:
        # Find dashboards folder relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dashboards_dir = os.path.join(os.path.dirname(script_dir), "dashboards")

    if not os.path.exists(dashboards_dir):
        print(f"[ERROR] Dashboard directory not found: {dashboards_dir}")
        sys.exit(1)

    print("=" * 60)
    print("  OpenSearch Dashboards - Dashboard Import")
    print("=" * 60)
    print(f"  URL: {args.url}")
    print(f"  Dashboard Directory: {dashboards_dir}")
    print("=" * 60)

    # Connection check
    print("\n[*] Checking connection...")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{args.url}/api/status")
            if response.status_code != 200:
                print(f"[ERROR] Cannot connect to OpenSearch Dashboards: {args.url}")
                print("   Please ensure OpenSearch Dashboards is running.")
                sys.exit(1)
            print(f"[OK] Connected to OpenSearch Dashboards")
    except httpx.ConnectError:
        print(f"[ERROR] Cannot connect to OpenSearch Dashboards: {args.url}")
        print("   Please ensure OpenSearch Dashboards is running.")
        print("\n   To start with Docker:")
        print("   cd docker && docker-compose up -d")
        sys.exit(1)

    # Create index pattern
    if not args.skip_index_pattern:
        create_index_pattern(args.url, "sentry-events-*")
        set_default_index_pattern(args.url, "sentry-events-*")

    # Find dashboard files
    ndjson_files = glob.glob(os.path.join(dashboards_dir, "*.ndjson"))

    if not ndjson_files:
        print(f"\n[!] No dashboard files found: {dashboards_dir}")
        sys.exit(1)

    print(f"\n[*] Found {len(ndjson_files)} dashboard files")

    # Import each file
    success = 0
    failed = 0

    for filepath in sorted(ndjson_files):
        if import_dashboard(args.url, filepath):
            success += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("  Import Summary")
    print("=" * 60)
    print(f"  [OK] Success: {success}")
    print(f"  [ERROR] Failed: {failed}")
    print("=" * 60)

    if success > 0:
        print(f"\n[*] View dashboards at:")
        print(f"   {args.url}/app/dashboards")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
