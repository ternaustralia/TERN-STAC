"""Small CLI helper for quick catalog introspection."""

import argparse
import json

from .client import TernStacClient


def main() -> None:
    parser = argparse.ArgumentParser(description="TERN STAC helper")
    parser.add_argument("--url", default=None, help="Optional STAC URL override")
    args = parser.parse_args()

    client = TernStacClient(api_url=args.url)
    root = client.client
    payload = {
        "type": getattr(root, "type", None),
        "id": getattr(root, "id", None),
        "title": getattr(root, "title", None),
        "description": getattr(root, "description", None),
    }
    print(json.dumps(payload, indent=2))
