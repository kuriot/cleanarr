#!/usr/bin/env python3
"""Dump watched items grouped by type for quick debugging."""

import argparse
from collections import Counter

from services.jellyfin import JellyfinClient
from utils.config import config


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Jellyfin watched items")
    parser.add_argument("--jellyfin-server")
    parser.add_argument("--jellyfin-api-key")
    parser.add_argument(
        "--include-types",
        default="Movie,Series",
        help="Comma-separated IncludeItemTypes value (default: Movie,Series)",
    )

    args = parser.parse_args()

    jf_cfg = config.get_section("jellyfin")
    server = args.jellyfin_server or jf_cfg.get("server_url")
    api_key = args.jellyfin_api_key or jf_cfg.get("api_key")

    client = JellyfinClient(server, api_key)
    try:
        users = client.get_users()
    except Exception:
        users = [client.get_current_user()]

    include_types = [t.strip() for t in args.include_types.split(",") if t.strip()]

    for user in users:
        user_id = user["Id"]
        name = user.get("Name", user_id)
        print(f"\n=== User {name} ({user_id}) ===")
        items = client.get_watched_items(user_id, include_types)
        counts = Counter(item.get("Type") for item in items)
        print("Counts by Type:", counts)
        for item in items:
            print(
                f"- {item.get('Type')} | {item.get('Name')} ({item.get('ProductionYear')}) | Id={item.get('Id')}"
            )


if __name__ == "__main__":
    main()
