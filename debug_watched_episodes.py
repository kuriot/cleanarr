#!/usr/bin/env python3
"""
Helper script for inspecting watched Jellyfin episodes per series.

Uses the existing Cleanarr config to authenticate with Jellyfin and dumps
episode metadata so you can verify which items the API returns.
"""

import argparse
from typing import Dict, List

from services.jellyfin import JellyfinClient
from utils.config import config


def iter_users(client: JellyfinClient) -> List[Dict]:
    """Return all users if possible, otherwise fall back to the current user."""
    try:
        return client.get_users()
    except Exception:
        return [client.get_current_user()]


def series_matches(series: Dict, args: argparse.Namespace) -> bool:
    """Apply optional filters from CLI args to a Jellyfin series entry."""
    if args.series_id and series.get("Id") != args.series_id:
        return False

    if args.series_name:
        name = series.get("Name", "")
        if args.series_name.lower() not in name.lower():
            return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Debug helper: list watched Jellyfin episodes per series"
    )
    parser.add_argument(
        "--series-id",
        help="Restrict output to a specific Jellyfin series ID",
    )
    parser.add_argument(
        "--series-name",
        help="Restrict output to series whose name contains this text (case insensitive)",
    )
    parser.add_argument(
        "--jellyfin-server",
        help="Override Jellyfin server URL (defaults to config value)",
    )
    parser.add_argument(
        "--jellyfin-api-key",
        help="Override Jellyfin API key (defaults to config value)",
    )

    args = parser.parse_args()

    jellyfin_cfg = config.get_section("jellyfin")
    server = args.jellyfin_server or jellyfin_cfg.get("server_url")
    api_key = args.jellyfin_api_key or jellyfin_cfg.get("api_key")

    if not server or not api_key:
        raise SystemExit(
            "Missing Jellyfin server_url or api_key in your Cleanarr config."
        )

    client = JellyfinClient(server, api_key)
    users = iter_users(client)

    for user in users:
        user_id = user.get("Id")
        username = user.get("Name", user_id)
        print(f"\n=== User: {username} ({user_id}) ===")

        watched_series = client.get_watched_items(user_id, ["Series"])
        if args.series_id or args.series_name:
            watched_series = [s for s in watched_series if series_matches(s, args)]

        if not watched_series:
            print("No watched series matched the provided filters.")
            continue

        for series in watched_series:
            series_id = series.get("Id")
            series_name = series.get("Name", "Unknown")
            print(f"\nSeries: {series_name} (ID: {series_id})")

            episodes = client.get_watched_episodes_for_series(user_id, series_id)
            if not episodes:
                print("  No watched episodes returned for this series.")
                continue

            for episode in episodes:
                ep_id = episode.get("Id")
                season = episode.get("ParentIndexNumber")
                number = episode.get("IndexNumber")
                title = episode.get("Name", "Untitled episode")
                last_played = (
                    (episode.get("UserData") or {}).get("LastPlayedDate") or "unknown"
                )
                is_favorite = (episode.get("UserData") or {}).get("IsFavorite", False)

                print(
                    f"  - {title} (ID: {ep_id}) "
                    f"S{season or '?':>02}E{number or '?':>02} "
                    f"| LastPlayed: {last_played} "
                    f"| Favorite: {'yes' if is_favorite else 'no'}"
                )


if __name__ == "__main__":
    main()
