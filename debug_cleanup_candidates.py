#!/usr/bin/env python3
"""
Debug helper to inspect raw cleanup candidates before CLI filtering.

Shows which movies/series Cleanarr considers, their similarity scores, and whether
they are flagged as in qBittorrent. This helps explain why nothing reaches the summary.
"""

import argparse

from services.cleanup import CleanupService
from services.jellyfin import JellyfinClient
from services.qbittorrent import QbittorrentClient
from services.radarr import RadarrClient
from services.sonarr import SonarrClient
from utils.config import config


def build_clients(args):
    jellyfin_cfg = config.get_section("jellyfin")
    jellyfin = JellyfinClient(
        args.jellyfin_server or jellyfin_cfg.get("server_url"),
        args.jellyfin_api_key or jellyfin_cfg.get("api_key"),
    )

    sonarr = None
    sonarr_cfg = config.get_section("sonarr")
    if args.include_series:
        sonarr = SonarrClient(
            args.sonarr_server or sonarr_cfg.get("server_url"),
            args.sonarr_api_key or sonarr_cfg.get("api_key"),
            config.get("auth", "username"),
            config.get("auth", "password"),
        )

    radarr = None
    radarr_cfg = config.get_section("radarr")
    if args.include_movies:
        radarr = RadarrClient(
            args.radarr_server or radarr_cfg.get("server_url"),
            args.radarr_api_key or radarr_cfg.get("api_key"),
            config.get("auth", "username"),
            config.get("auth", "password"),
        )

    qb = None
    qb_cfg = config.get_section("qbittorrent")
    if args.include_qb:
        qb = QbittorrentClient(
            args.qbittorrent_server or qb_cfg.get("server_url"),
            args.qbittorrent_username or qb_cfg.get("username") or config.get("auth", "username"),
            args.qbittorrent_password or qb_cfg.get("password") or config.get("auth", "password"),
            (qb_cfg.get("use_basic_auth") or "false").lower() == "true",
        )

    return jellyfin, radarr, sonarr, qb


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect raw cleanup candidates")
    parser.add_argument("--movies", dest="include_movies", action="store_true")
    parser.add_argument("--series", dest="include_series", action="store_true")
    parser.add_argument("--no-qb", dest="include_qb", action="store_false")
    parser.add_argument("--watched-before-days", type=int)
    parser.add_argument("--collect-episodes", action="store_true")
    parser.add_argument("--jellyfin-server")
    parser.add_argument("--jellyfin-api-key")
    parser.add_argument("--sonarr-server")
    parser.add_argument("--sonarr-api-key")
    parser.add_argument("--radarr-server")
    parser.add_argument("--radarr-api-key")
    parser.add_argument("--qbittorrent-server")
    parser.add_argument("--qbittorrent-username")
    parser.add_argument("--qbittorrent-password")
    parser.set_defaults(include_movies=False, include_series=True, include_qb=True)

    args = parser.parse_args()

    jellyfin, radarr, sonarr, qb = build_clients(args)
    cleanup = CleanupService(jellyfin, radarr=radarr, sonarr=sonarr, qbittorrent=qb)

    movies, series, episodes = cleanup.get_cleanup_candidates(
        min_watch_age_days=args.watched_before_days,
        collect_episode_data=args.collect_episodes,
    )

    print("Sonarr series fetched:", len(sonarr.get_series()) if sonarr else 0)
    print(
        f"Raw counts -> movies: {len(movies)}, series: {len(series)}, episode-series: {len(episodes)}"
    )
    print(f"Movies candidates: {len(movies)}")
    for movie in movies:
        jf = movie["jellyfin_item"]
        rd = movie["radarr_item"]
        print(
            f"  - {jf.get('Name')} ({jf.get('ProductionYear')}) -> Radarr {rd.get('title')} | score={movie['similarity_score']:.3f} | in_qb={movie.get('in_qbittorrent')}"
        )

    print(f"\nSeries candidates: {len(series)}")
    for show in series:
        jf = show["jellyfin_item"]
        sn = show["sonarr_item"]
        print(
            f"  - {jf.get('Name')} ({jf.get('ProductionYear')}) -> Sonarr {sn.get('title')} | score={show['similarity_score']:.3f} | in_qb={show.get('in_qbittorrent')}"
        )

    if args.collect_episodes:
        print(f"\nEpisode-cleanup series: {len(episodes)}")
        for entry in episodes:
            jf = entry["jellyfin_series"]
            print(
                f"  - {jf.get('Name')} ({len(entry.get('episodes', []))} episodes) | in_qb={entry.get('in_qbittorrent')}"
            )


if __name__ == "__main__":
    main()
