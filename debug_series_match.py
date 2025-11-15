#!/usr/bin/env python3
"""
Helper script to inspect Jellyfin->Sonarr matching for watched series.

Prints the best Sonarr match and similarity score for each watched Jellyfin series,
so you can confirm whether Cleanarr should consider the series for deletion.
"""

import argparse
from typing import Dict, List, Optional, Tuple

from services.cleanup import CleanupService
from services.jellyfin import JellyfinClient
from services.sonarr import SonarrClient
from utils.config import config


def get_jellyfin_series(client: JellyfinClient, series_id: Optional[str]) -> List[Dict]:
    try:
        users = client.get_users()
    except Exception:
        users = [client.get_current_user()]

    series_items: Dict[str, Dict] = {}
    for user in users:
        watched = client.get_watched_items(user["Id"], ["Series"])
        for item in watched:
            if series_id and item.get("Id") != series_id:
                continue
            series_items[item["Id"]] = item

    return list(series_items.values())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show Jellyfin series matches against Sonarr data"
    )
    parser.add_argument("--series-id", help="Limit to a single Jellyfin series ID")
    parser.add_argument("--series-name", help="Case-insensitive substring filter")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.0,
        help="Minimum score required to report a match (default: 0.0)",
    )
    parser.add_argument(
        "--jellyfin-server",
        help="Override Jellyfin server URL (defaults to config value)",
    )
    parser.add_argument(
        "--jellyfin-api-key",
        help="Override Jellyfin API key (defaults to config value)",
    )
    parser.add_argument(
        "--sonarr-server",
        help="Override Sonarr server URL (defaults to config value)",
    )
    parser.add_argument(
        "--sonarr-api-key",
        help="Override Sonarr API key (defaults to config value)",
    )

    args = parser.parse_args()

    jellyfin_cfg = config.get_section("jellyfin")
    sonarr_cfg = config.get_section("sonarr")

    jellyfin = JellyfinClient(
        args.jellyfin_server or jellyfin_cfg.get("server_url"),
        args.jellyfin_api_key or jellyfin_cfg.get("api_key"),
    )
    sonarr = SonarrClient(
        args.sonarr_server or sonarr_cfg.get("server_url"),
        args.sonarr_api_key or sonarr_cfg.get("api_key"),
        config.get("auth", "username"),
        config.get("auth", "password"),
    )

    cleanup = CleanupService(jellyfin, sonarr=sonarr)
    sonarr_series = sonarr.get_series()

    series_items = get_jellyfin_series(jellyfin, args.series_id)
    if args.series_name:
        series_items = [
            item
            for item in series_items
            if args.series_name.lower() in item.get("Name", "").lower()
        ]

    if not series_items:
        print("No watched Jellyfin series matched the provided filters.")
        return

    for item in series_items:
        name = item.get("Name", "Unknown")
        year = item.get("ProductionYear")

        match = cleanup.find_matching_series(item, sonarr_series, threshold=0.0)
        if not match:
            print(f"{name} ({year}) -> no Sonarr match")
            continue

        score = cleanup.calculate_similarity(name, match.get("title", ""))
        if score < args.similarity_threshold:
            continue

        print(
            f"{name} ({year}) -> Sonarr: {match.get('title')} ({match.get('year')}) | score={score:.3f}"
        )


if __name__ == "__main__":
    main()
