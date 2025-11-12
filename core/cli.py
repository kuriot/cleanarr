"""
Command-line interface for Cleanarr
"""

import argparse

from services.cleanup import CleanupService
from services.jellyfin import JellyfinClient
from services.qbittorrent import QbittorrentClient
from services.radarr import RadarrClient
from services.sonarr import SonarrClient
from utils import logger
from utils.config import config


def setup_cli() -> argparse.ArgumentParser:
    """Setup command-line interface"""
    parser = argparse.ArgumentParser(
        description="Cleanarr - Media Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Get defaults from config
    jellyfin_config = config.get_section("jellyfin")
    auth_config = config.get_section("auth")
    default_username = auth_config.get("username")
    default_password = auth_config.get("password")

    # Main cleanup arguments (no subcommands needed)
    parser.add_argument(
        "--jellyfin-server",
        default=jellyfin_config.get("server_url"),
        required=jellyfin_config.get("server_url") is None,
        help="Jellyfin server URL",
    )
    parser.add_argument(
        "--jellyfin-api-key",
        default=jellyfin_config.get("api_key"),
        required=jellyfin_config.get("api_key") is None,
        help="Jellyfin API key",
    )
    parser.add_argument(
        "--radarr-server",
        default=config.get("radarr", "server_url"),
        help="Radarr server URL",
    )
    parser.add_argument(
        "--radarr-api-key",
        default=config.get("radarr", "api_key"),
        help="Radarr API key",
    )
    parser.add_argument(
        "--auth-username",
        default=default_username,
        help="HTTP Basic auth username for Radarr/Sonarr",
    )
    parser.add_argument(
        "--auth-password",
        default=default_password,
        help="HTTP Basic auth password for Radarr/Sonarr",
    )
    parser.add_argument(
        "--sonarr-server",
        default=config.get("sonarr", "server_url"),
        help="Sonarr server URL",
    )
    parser.add_argument(
        "--sonarr-api-key",
        default=config.get("sonarr", "api_key"),
        help="Sonarr API key",
    )
    parser.add_argument(
        "--qbittorrent-server",
        default=config.get("qbittorrent", "server_url"),
        help="qBittorrent server URL",
    )
    parser.add_argument(
        "--qbittorrent-username",
        default=config.get("qbittorrent", "username") or config.get("auth", "username"),
        help="qBittorrent username",
    )
    parser.add_argument(
        "--qbittorrent-password",
        default=config.get("qbittorrent", "password") or config.get("auth", "password"),
        help="qBittorrent password",
    )
    parser.add_argument(
        "--qbittorrent-basic-auth",
        action="store_true",
        default=(config.get("qbittorrent", "use_basic_auth") or "false").lower()
        == "true",
        help="Use HTTP Basic Auth for qBittorrent instead of session login",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without actually deleting (default: true)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete the content (disables dry-run)",
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Delete from Radarr/Sonarr but keep the files",
    )
    parser.add_argument(
        "--add-exclusion",
        action="store_true",
        help="Add items to import exclusion list",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.8,
        help="Minimum similarity score for matching (0.0-1.0, default: 0.8)",
    )
    parser.add_argument(
        "--movies-only", action="store_true", help="Only process movies"
    )
    parser.add_argument(
        "--series-only", action="store_true", help="Only process TV series"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        help="Custom log file path (default: ~/.config/cleanarr/cleanarr.log)",
    )
    parser.add_argument(
        "--watched-before-days",
        type=int,
        help="Only consider content watched at least this many days ago",
    )
    return parser


def handle_cleanup(args) -> int:
    """Handle cleanup command"""
    try:
        # Setup logging
        from pathlib import Path

        log_file = Path(args.log_file) if args.log_file else None
        logger.setup_logging(args.log_level, log_file)

        # Log configuration details (debug level - goes to file only)
        logger.config_info(f"Jellyfin server: {args.jellyfin_server}")
        logger.config_info(
            f"Jellyfin API key: {args.jellyfin_api_key[:8]}..."
            if args.jellyfin_api_key
            else "Jellyfin API key: None"
        )
        logger.config_info(f"Radarr server: {args.radarr_server}")
        logger.config_info(
            f"Radarr API key: {args.radarr_api_key[:8]}..."
            if args.radarr_api_key
            else "Radarr API key: None"
        )
        logger.config_info(f"Sonarr server: {args.sonarr_server}")
        logger.config_info(
            f"Sonarr API key: {args.sonarr_api_key[:8]}..."
            if args.sonarr_api_key
            else "Sonarr API key: None"
        )
        logger.config_info(f"qBittorrent server: {args.qbittorrent_server}")
        logger.config_info(f"qBittorrent username: {args.qbittorrent_username}")
        logger.config_info(
            f"qBittorrent password: {'***' if args.qbittorrent_password else 'None'}"
        )
        logger.config_info(
            f"qBittorrent basic auth: {getattr(args, 'qbittorrent_basic_auth', False)}"
        )
        logger.config_info(f"Auth username: {args.auth_username}")
        logger.config_info(f"Auth password: {'***' if args.auth_password else 'None'}")

        logger.info("🚀 Starting Cleanarr cleanup process")

        # Initialize clients
        jellyfin = JellyfinClient(args.jellyfin_server, args.jellyfin_api_key)

        radarr = None
        if (
            args.radarr_server
            and args.radarr_api_key
            and not getattr(args, "series_only", False)
        ):
            logger.info("🎬 Initializing Radarr client...")
            radarr = RadarrClient(
                args.radarr_server,
                args.radarr_api_key,
                args.auth_username,
                args.auth_password,
            )
            if not radarr.test_connection():
                logger.connection_failure("Radarr", args.radarr_server)
                radarr = None
            else:
                logger.connection_success("Radarr")
        else:
            logger.skip(
                f"Radarr (server: {bool(args.radarr_server)}, api_key: {bool(args.radarr_api_key)}, series_only: {getattr(args, 'series_only', False)})"
            )

        sonarr = None
        if (
            args.sonarr_server
            and args.sonarr_api_key
            and not getattr(args, "movies_only", False)
        ):
            logger.info("📺 Initializing Sonarr client...")
            sonarr = SonarrClient(
                args.sonarr_server,
                args.sonarr_api_key,
                args.auth_username,
                args.auth_password,
            )
            if not sonarr.test_connection():
                logger.connection_failure("Sonarr", args.sonarr_server)
                sonarr = None
            else:
                logger.connection_success("Sonarr")
        else:
            logger.skip(
                f"Sonarr (server: {bool(args.sonarr_server)}, api_key: {bool(args.sonarr_api_key)}, movies_only: {getattr(args, 'movies_only', False)})"
            )

        # Initialize qBittorrent client
        qbittorrent = None
        if (
            args.qbittorrent_server
            and args.qbittorrent_username
            and args.qbittorrent_password
        ):
            logger.info("🌊 Initializing qBittorrent client...")
            qbittorrent = QbittorrentClient(
                args.qbittorrent_server,
                args.qbittorrent_username,
                args.qbittorrent_password,
                getattr(args, "qbittorrent_basic_auth", False),
            )
            if not qbittorrent.test_connection():
                logger.connection_failure("qBittorrent", args.qbittorrent_server)
                qbittorrent = None
            else:
                version = qbittorrent.get_version()
                logger.connection_success("qBittorrent", f"version: {version}")
        else:
            logger.skip(
                f"qBittorrent (server: {bool(args.qbittorrent_server)}, credentials: {bool(args.qbittorrent_username and args.qbittorrent_password)})"
            )

        if not radarr and not sonarr:
            logger.error("No valid Radarr or Sonarr connections available")
            return 1

        # Initialize cleanup service
        cleanup_service = CleanupService(jellyfin, radarr, sonarr, qbittorrent)

        logger.info("🔍 Finding cleanup candidates...")
        movies, series = cleanup_service.get_cleanup_candidates(
            min_watch_age_days=args.watched_before_days
        )

        # Filter by similarity threshold
        movies = [
            m for m in movies if m["similarity_score"] >= args.similarity_threshold
        ]
        series = [
            s for s in series if s["similarity_score"] >= args.similarity_threshold
        ]

        # Safety filter: Skip content that exists in qBittorrent
        skipped_movies = 0
        skipped_series = 0
        if qbittorrent:
            original_movie_count = len(movies)
            original_series_count = len(series)
            movies = [m for m in movies if not m.get("in_qbittorrent", False)]
            series = [s for s in series if not s.get("in_qbittorrent", False)]

            skipped_movies = original_movie_count - len(movies)
            skipped_series = original_series_count - len(series)
            if skipped_movies > 0 or skipped_series > 0:
                logger.info(
                    f"🛡️ Safety filter: Skipped {skipped_movies} movies and {skipped_series} series found in qBittorrent"
                )

        print(f"\n📊 Cleanup Summary:")
        print(f"   Movies to delete: {len(movies)}")
        print(f"   Series to delete: {len(series)}")
        if qbittorrent and (skipped_movies > 0 or skipped_series > 0):
            print(
                f"🛡️ Protected by qBittorrent: {skipped_movies} movies, {skipped_series} series"
            )

        if not movies and not series:
            if qbittorrent and (skipped_movies > 0 or skipped_series > 0):
                print(
                    "  All watched content is protected by qBittorrent - nothing to delete!"
                )
            else:
                print("  No content to clean up!")
            return 0

        # Show details
        if movies:
            print(f"\n📽️  Movies to delete:")
            print("-" * 80)
            for movie_data in movies:
                jellyfin_movie = movie_data["jellyfin_item"]
                radarr_movie = movie_data["radarr_item"]
                score = movie_data["similarity_score"]

                jellyfin_name = jellyfin_movie.get("Name", "Unknown")
                jellyfin_year = jellyfin_movie.get("ProductionYear", "Unknown")
                radarr_name = radarr_movie.get("title", "Unknown")
                radarr_year = radarr_movie.get("year", "Unknown")
                in_qbt = movie_data.get("in_qbittorrent", False)

                print(f"  • Jellyfin: {jellyfin_name} ({jellyfin_year})")
                print(f"    Radarr:   {radarr_name} ({radarr_year})")
                print(f"    Match score: {score:.2f}")
                if qbittorrent:
                    print(
                        f"    In qBittorrent: {'✅ Yes' if in_qbt else '❌ No (safe to delete)'}"
                    )
                else:
                    print(
                        f"    In qBittorrent: ❓ Not checked (no qBittorrent connection)"
                    )
                print()

        if series:
            print(f"\n📺 Series to delete:")
            print("-" * 80)
            for series_data in series:
                jellyfin_series = series_data["jellyfin_item"]
                sonarr_series = series_data["sonarr_item"]
                score = series_data["similarity_score"]
                fully_downloaded = series_data.get("fully_downloaded", False)

                jellyfin_name = jellyfin_series.get("Name", "Unknown")
                jellyfin_year = jellyfin_series.get("ProductionYear", "Unknown")
                sonarr_name = sonarr_series.get("title", "Unknown")
                sonarr_year = sonarr_series.get("year", "Unknown")
                in_qbt = series_data.get("in_qbittorrent", False)

                print(f"  • Jellyfin: {jellyfin_name} ({jellyfin_year})")
                print(f"    Sonarr:   {sonarr_name} ({sonarr_year})")
                print(f"    Match score: {score:.2f}")
                print(f"    Fully downloaded: {'Yes' if fully_downloaded else 'No'}")
                if qbittorrent:
                    print(
                        f"    In qBittorrent: {'✅ Yes' if in_qbt else '❌ No (safe to delete)'}"
                    )
                else:
                    print(
                        f"    In qBittorrent: ❓ Not checked (no qBittorrent connection)"
                    )
                print()

        # Determine if this is a dry run
        dry_run = not args.delete

        if dry_run:
            print("\n🔒 DRY RUN MODE - No files will be deleted")
            print("   Use --delete to actually delete content")
        else:
            print("\n⚠️  DELETE MODE - Content will be permanently deleted!")

        # Execute cleanup
        delete_files = not args.keep_files
        results = cleanup_service.execute_cleanup(
            movies,
            series,
            delete_files=delete_files,
            add_exclusion=args.add_exclusion,
            dry_run=dry_run,
        )

        # Show results
        print(f"\n✅ Cleanup Results:")
        print(f"  Movies deleted: {results['movies_deleted']}")
        print(f"  Movies failed: {results['movies_failed']}")
        print(f"  Series deleted: {results['series_deleted']}")
        print(f"  Series failed: {results['series_failed']}")

        if results["errors"]:
            print(f"\n❌ Errors:")
            for error in results["errors"]:
                print(f"  • {error}")

        return 0 if not results["errors"] else 1

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 1
