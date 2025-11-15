"""
Cleanup service for matching Jellyfin watched content with Radarr/Sonarr
"""

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from services.jellyfin import JellyfinClient
from services.qbittorrent import QbittorrentClient
from services.radarr import RadarrClient
from services.sonarr import SonarrClient
from utils import logger


class CleanupService:
    """Service to match and clean up watched content across services"""

    def __init__(
        self,
        jellyfin: JellyfinClient,
        radarr: Optional[RadarrClient] = None,
        sonarr: Optional[SonarrClient] = None,
        qbittorrent: Optional[QbittorrentClient] = None,
    ):
        self.jellyfin = jellyfin
        self.radarr = radarr
        self.sonarr = sonarr
        self.qbittorrent = qbittorrent

    def normalize_title(self, title: str) -> str:
        """Normalize title for better matching"""
        # Remove common prefixes/suffixes and special characters
        title = re.sub(r"^(The|A|An)\s+", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s*\([^)]*\)$", "", title)  # Remove year in parentheses
        title = re.sub(r"[^\w\s]", " ", title)  # Replace special chars with spaces
        title = re.sub(r"\s+", " ", title).strip().lower()  # Normalize whitespace
        return title

    def calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_matching_movie(
        self,
        jellyfin_movie: Dict[str, Any],
        radarr_movies: List[Dict[str, Any]],
        threshold: float = 0.8,
    ) -> Optional[Dict[str, Any]]:
        """Find matching movie in Radarr based on Jellyfin movie"""
        jellyfin_title = jellyfin_movie.get("Name", "")
        jellyfin_year = jellyfin_movie.get("ProductionYear")

        best_match = None
        best_score = 0.0

        for radarr_movie in radarr_movies:
            radarr_title = radarr_movie.get("title", "")
            radarr_year = radarr_movie.get("year")

            # Calculate title similarity
            title_score = self.calculate_similarity(jellyfin_title, radarr_title)

            # Boost score if years match
            year_bonus = (
                0.1
                if jellyfin_year and radarr_year and jellyfin_year == radarr_year
                else 0
            )

            total_score = title_score + year_bonus

            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = radarr_movie

        return best_match

    def find_matching_series(
        self,
        jellyfin_series: Dict[str, Any],
        sonarr_series: List[Dict[str, Any]],
        threshold: float = 0.8,
    ) -> Optional[Dict[str, Any]]:
        """Find matching series in Sonarr based on Jellyfin series"""
        jellyfin_title = jellyfin_series.get("Name", "")
        jellyfin_year = jellyfin_series.get("ProductionYear")

        best_match = None
        best_score = 0.0

        for sonarr_show in sonarr_series:
            sonarr_title = sonarr_show.get("title", "")
            sonarr_year = sonarr_show.get("year")

            # Calculate title similarity
            title_score = self.calculate_similarity(jellyfin_title, sonarr_title)

            # Boost score if years match
            year_bonus = (
                0.1
                if jellyfin_year and sonarr_year and jellyfin_year == sonarr_year
                else 0
            )

            total_score = title_score + year_bonus

            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = sonarr_show

        return best_match

    def _is_favorite(self, item: Dict[str, Any]) -> bool:
        """Check if an item is marked as favorite in Jellyfin"""
        user_data = item.get("UserData", {})
        return user_data.get("IsFavorite", False)

    def _parse_last_played(self, item: Dict[str, Any]) -> Optional[datetime]:
        """Parse Jellyfin LastPlayedDate into a timezone-aware datetime"""
        user_data = item.get("UserData") or {}
        date_str = user_data.get("LastPlayedDate")
        if not date_str:
            return None

        try:
            trimmed = date_str.rstrip("Z")
            if "." in trimmed:
                main, fraction = trimmed.split(".", 1)
            else:
                main, fraction = trimmed, "0"

            fraction = (fraction + "000000")[:6]
            normalized = f"{main}.{fraction}"
            parsed = datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S.%f")
            return parsed.replace(tzinfo=timezone.utc)
        except Exception:
            logger.debug(f"Unable to parse LastPlayedDate: {date_str}")
            return None

    def _filter_by_watch_age(
        self, items: List[Dict[str, Any]], min_age_days: int, label: str
    ) -> List[Dict[str, Any]]:
        """Keep only items watched at least min_age_days ago"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=min_age_days)
        filtered: List[Dict[str, Any]] = []
        skipped = 0

        for item in items:
            last_played = self._parse_last_played(item)
            if last_played and last_played <= cutoff:
                filtered.append(item)
            else:
                skipped += 1

        if skipped:
            logger.info(
                f"⏳ Skipped {skipped} {label} newer than {min_age_days} days (or missing watch date)"
            )

        return filtered

    def _collect_watched_episodes_for_series(
        self,
        users: List[Dict[str, Any]],
        jellyfin_series: Dict[str, Any],
        min_watch_age_days: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Collect watched Jellyfin episodes for the provided series from all users"""
        series_id = jellyfin_series.get("Id")
        if not series_id:
            return []

        episodes_by_id: Dict[str, Dict[str, Any]] = {}
        favorite_episodes = 0
        favorite_season_numbers = set()

        for user in users:
            user_id = user["Id"]
            try:
                watched_episodes = self.jellyfin.get_watched_episodes_for_series(
                    user_id, series_id
                )
                favorite_seasons = self.jellyfin.get_favorite_seasons_for_series(
                    user_id, series_id
                )
            except Exception as exc:
                logger.error(
                    f"Error fetching watched episodes for {jellyfin_series.get('Name', 'Unknown')} (user {user_id}): {exc}"
                )
                continue

            for season in favorite_seasons:
                number = season.get("IndexNumber")
                if number is not None:
                    favorite_season_numbers.add(number)

            for episode in watched_episodes:
                season_number = episode.get("ParentIndexNumber")
                if self._is_favorite(episode) or (
                    season_number in favorite_season_numbers
                ):
                    favorite_episodes += 1
                    continue
                episodes_by_id[episode.get("Id")] = episode

        if favorite_episodes:
            logger.info(
                f"🌟 Protected favorite episodes: {favorite_episodes} for {jellyfin_series.get('Name', 'Unknown')}"
            )

        episodes = list(episodes_by_id.values())
        if (
            min_watch_age_days is not None
            and min_watch_age_days >= 0
            and episodes
        ):
            episodes = self._filter_by_watch_age(
                episodes,
                min_watch_age_days,
                f"episodes for {jellyfin_series.get('Name', 'Unknown')}",
            )

        return episodes

    def _series_has_favorite_content(
        self, users: List[Dict[str, Any]], jellyfin_series: Dict[str, Any]
    ) -> bool:
        """Determine if any user has favorited episodes or seasons in this series"""
        series_id = jellyfin_series.get("Id")
        if not series_id:
            return False

        for user in users:
            user_id = user["Id"]
            try:
                favorites = self.jellyfin.get_favorite_episodes_for_series(
                    user_id, series_id
                )
                seasons = self.jellyfin.get_favorite_seasons_for_series(
                    user_id, series_id
                )
            except Exception as exc:
                logger.error(
                    f"Error fetching favorite sub-items for {jellyfin_series.get('Name', 'Unknown')} (user {user_id}): {exc}"
                )
                continue

            if favorites or seasons:
                return True

        return False

    def _build_episode_cleanup_entry(
        self,
        users: List[Dict[str, Any]],
        jellyfin_series: Dict[str, Any],
        sonarr_series: Dict[str, Any],
        similarity_score: float,
        min_watch_age_days: Optional[int],
        in_qbittorrent: bool,
    ) -> Optional[Dict[str, Any]]:
        """Build cleanup data for watched episodes in a series"""
        if not self.sonarr:
            return None

        jellyfin_episodes = self._collect_watched_episodes_for_series(
            users, jellyfin_series, min_watch_age_days
        )
        if not jellyfin_episodes:
            return None

        try:
            sonarr_episodes = self.sonarr.get_episodes(sonarr_series.get("id"))
        except Exception as exc:
            logger.error(
                f"Error fetching Sonarr episodes for {sonarr_series.get('title', 'Unknown')}: {exc}"
            )
            return None

        sonarr_episode_map = {}
        for episode in sonarr_episodes:
            key = (episode.get("seasonNumber"), episode.get("episodeNumber"))
            sonarr_episode_map[key] = episode

        matched_episodes = []
        for episode in jellyfin_episodes:
            season = episode.get("ParentIndexNumber")
            number = episode.get("IndexNumber")
            if season is None or number is None:
                logger.debug(
                    f"Skipping episode without season/episode numbers: {episode.get('Name', 'Unknown')}"
                )
                continue

            sonarr_episode = sonarr_episode_map.get((season, number))
            if not sonarr_episode:
                logger.debug(
                    f"No Sonarr episode match for {jellyfin_series.get('Name', 'Unknown')} S{season:02}E{number:02}"
                )
                continue

            matched_episodes.append(
                {
                    "jellyfin_episode": episode,
                    "sonarr_episode": sonarr_episode,
                    "season_number": season,
                    "episode_number": number,
                }
            )

        if not matched_episodes:
            return None

        return {
            "jellyfin_series": jellyfin_series,
            "sonarr_series": sonarr_series,
            "similarity_score": similarity_score,
            "episodes": matched_episodes,
            "in_qbittorrent": in_qbittorrent,
        }

    def get_cleanup_candidates(
        self,
        min_watch_percentage: float = 0.8,
        min_watch_age_days: Optional[int] = None,
        collect_episode_data: bool = False,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get movies and series that are candidates for cleanup"""
        cleanup_movies = []
        cleanup_series = []
        episode_cleanup = []

        try:
            # Get all users
            try:
                users = self.jellyfin.get_users()
            except:
                # Fall back to current user if no admin access
                users = [self.jellyfin.get_current_user()]

            # Get watched content for all users
            all_watched_movies = []
            all_watched_series = []

            for user in users:
                user_id = user["Id"]
                watched_movies = self.jellyfin.get_watched_items(user_id, ["Movie"])
                watched_series = self.jellyfin.get_watched_items(user_id, ["Series"])

                all_watched_movies.extend(watched_movies)
                all_watched_series.extend(watched_series)

            # Remove duplicates (same item watched by multiple users)
            unique_movies = {
                item.get("Id"): item for item in all_watched_movies
            }.values()
            unique_series = {
                item.get("Id"): item for item in all_watched_series
            }.values()

            # Filter out favorites
            non_favorite_movies = []
            favorite_movies = 0
            for movie in unique_movies:
                if self._is_favorite(movie):
                    favorite_movies += 1
                    logger.debug(
                        f"Skipping favorite movie: {movie.get('Name', 'Unknown')}"
                    )
                else:
                    non_favorite_movies.append(movie)

            non_favorite_series = []
            favorite_series = 0
            for series in unique_series:
                if self._is_favorite(series):
                    favorite_series += 1
                    logger.debug(
                        f"Skipping favorite series: {series.get('Name', 'Unknown')}"
                    )
                else:
                    non_favorite_series.append(series)

            if favorite_movies > 0 or favorite_series > 0:
                logger.info(
                    f"🌟 Protected favorites: {favorite_movies} movies, {favorite_series} series"
                )

            unique_movies = non_favorite_movies
            unique_series = non_favorite_series

            if min_watch_age_days is not None and min_watch_age_days >= 0:
                unique_movies = list(unique_movies)
                unique_series = list(unique_series)
                unique_movies = self._filter_by_watch_age(
                    unique_movies, min_watch_age_days, "movies"
                )
                unique_series = self._filter_by_watch_age(
                    unique_series, min_watch_age_days, "series"
                )

            # Match with Radarr movies
            if self.radarr:
                radarr_movies = self.radarr.get_movies()

                for jellyfin_movie in unique_movies:
                    radarr_match = self.find_matching_movie(
                        jellyfin_movie, radarr_movies
                    )

                    if radarr_match:
                        movie_title = jellyfin_movie.get("Name", "")
                        movie_year = jellyfin_movie.get("ProductionYear")

                        # Check if movie exists in qBittorrent (if qBittorrent client available)
                        in_qbittorrent = False
                        if self.qbittorrent:
                            in_qbittorrent = self.qbittorrent.is_media_in_torrents(
                                movie_title, movie_year
                            )

                        cleanup_movies.append(
                            {
                                "jellyfin_item": jellyfin_movie,
                                "radarr_item": radarr_match,
                                "similarity_score": self.calculate_similarity(
                                    movie_title, radarr_match.get("title", "")
                                ),
                                "in_qbittorrent": in_qbittorrent,
                            }
                        )

            # Match with Sonarr series
            protected_by_favorite_episodes = 0
            if self.sonarr:
                sonarr_series = self.sonarr.get_series()
                for jellyfin_show in unique_series:
                    sonarr_match = self.find_matching_series(
                        jellyfin_show, sonarr_series
                    )

                    if sonarr_match:
                        series_title = jellyfin_show.get("Name", "")
                        series_year = jellyfin_show.get("ProductionYear")
                        series_id = sonarr_match.get("id")

                        # Check if series exists in qBittorrent (if qBittorrent client available)
                        in_qbittorrent = False
                        if self.qbittorrent:
                            in_qbittorrent = self.qbittorrent.is_media_in_torrents(
                                series_title, series_year
                            )

                        similarity = self.calculate_similarity(
                            series_title, sonarr_match.get("title", "")
                        )
                        has_favorite_episodes = self._series_has_favorite_content(
                            users, jellyfin_show
                        )
                        series_entry = {
                            "jellyfin_item": jellyfin_show,
                            "sonarr_item": sonarr_match,
                            "similarity_score": similarity,
                            "fully_downloaded": (
                                self.sonarr.is_series_fully_watched(series_id)
                                if series_id
                                else False
                            ),
                            "in_qbittorrent": in_qbittorrent,
                            "favorite_episodes": has_favorite_episodes,
                        }

                        if has_favorite_episodes:
                            protected_by_favorite_episodes += 1
                            logger.debug(
                                f"Skipping full series deletion for {series_title} due to favorite episodes"
                            )
                        else:
                            cleanup_series.append(series_entry)

                        if collect_episode_data and not in_qbittorrent:
                            episode_entry = self._build_episode_cleanup_entry(
                                users,
                                jellyfin_show,
                                sonarr_match,
                                similarity,
                                min_watch_age_days,
                                in_qbittorrent,
                            )
                            if episode_entry:
                                episode_cleanup.append(episode_entry)

            if protected_by_favorite_episodes > 0:
                logger.info(
                    f"🌟 Favorite episodes protected: {protected_by_favorite_episodes} series"
                )

        except Exception as e:
            logger.error(f"Error getting cleanup candidates: {e}")

        return cleanup_movies, cleanup_series, episode_cleanup

    def execute_cleanup(
        self,
        movies: List[Dict[str, Any]],
        series: List[Dict[str, Any]],
        episode_series: Optional[List[Dict[str, Any]]] = None,
        delete_files: bool = True,
        add_exclusion: bool = False,
        dry_run: bool = True,
        delete_episodes: bool = False,
    ) -> Dict[str, Any]:
        """Execute the cleanup operation"""
        results = {
            "movies_deleted": 0,
            "movies_failed": 0,
            "series_deleted": 0,
            "series_failed": 0,
            "episodes_deleted": 0,
            "episodes_failed": 0,
            "errors": [],
        }

        # Delete individual episodes if requested
        if delete_episodes and episode_series:
            if not self.sonarr:
                logger.warning(
                    "Episode deletion requested but Sonarr client is unavailable"
                )
            elif not self.jellyfin:
                logger.warning(
                    "Episode deletion requested but Jellyfin client is unavailable"
                )
            else:
                for series_entry in episode_series:
                    jellyfin_series = series_entry.get("jellyfin_series", {})
                    sonarr_series = series_entry.get("sonarr_series", {})
                    series_title = jellyfin_series.get("Name", sonarr_series.get("title", "Unknown"))
                    episodes = series_entry.get("episodes", [])

                    for episode in episodes:
                        jellyfin_episode = episode.get("jellyfin_episode", {})
                        sonarr_episode = episode.get("sonarr_episode", {})
                        season_number = episode.get("season_number")
                        episode_number = episode.get("episode_number")

                        season_str = (
                            f"S{int(season_number):02d}"
                            if isinstance(season_number, int)
                            else "S??"
                        )
                        episode_str = (
                            f"E{int(episode_number):02d}"
                            if isinstance(episode_number, int)
                            else "E??"
                        )
                        episode_label = f"{series_title} {season_str}{episode_str}"

                        try:
                            if dry_run:
                                logger.info(
                                    f"[DRY RUN] Would delete episode: {episode_label}"
                                )
                                results["episodes_deleted"] += 1
                                continue

                            self.jellyfin.delete_item(jellyfin_episode.get("Id"))
                            unmonitored = self.sonarr.set_single_episode_monitored(
                                sonarr_episode.get("id"), False
                            )
                            if not unmonitored:
                                logger.warning(
                                    f"Episode deleted but failed to update Sonarr monitoring: {episode_label}"
                                )

                            logger.success(f"Episode deleted: {episode_label}")
                            results["episodes_deleted"] += 1

                        except Exception as e:
                            error_msg = f"Error deleting episode {episode_label}: {e}"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            results["episodes_failed"] += 1

        # Delete movies
        if self.radarr:
            for movie_data in movies:
                radarr_movie = movie_data["radarr_item"]
                movie_id = radarr_movie.get("id")
                movie_title = radarr_movie.get("title", "Unknown")

                try:
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would delete movie: {movie_title} (ID: {movie_id})"
                        )
                        results["movies_deleted"] += 1
                    else:
                        success = self.radarr.delete_movie(
                            movie_id, delete_files, add_exclusion
                        )
                        if success:
                            logger.success(f"Movie deleted: {movie_title}")
                            results["movies_deleted"] += 1
                        else:
                            logger.failure(f"Movie deletion failed: {movie_title}")
                            results["movies_failed"] += 1

                except Exception as e:
                    error_msg = f"Error deleting movie {movie_title}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["movies_failed"] += 1

        # Delete series
        if self.sonarr:
            for series_data in series:
                sonarr_series = series_data["sonarr_item"]
                series_id = sonarr_series.get("id")
                series_title = sonarr_series.get("title", "Unknown")

                try:
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would delete series: {series_title} (ID: {series_id})"
                        )
                        results["series_deleted"] += 1
                    else:
                        success = self.sonarr.delete_series(
                            series_id, delete_files, add_exclusion
                        )
                        if success:
                            logger.success(f"Series deleted: {series_title}")
                            results["series_deleted"] += 1
                        else:
                            logger.failure(f"Series deletion failed: {series_title}")
                            results["series_failed"] += 1

                except Exception as e:
                    error_msg = f"Error deleting series {series_title}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["series_failed"] += 1

        return results
