"""
qBittorrent service for torrent management
"""

import re
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from utils import logger


class QbittorrentClient:
    """Client for interacting with qBittorrent Web API"""

    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        use_basic_auth: bool = False,
    ):
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.use_basic_auth = use_basic_auth
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"}
        )

        if use_basic_auth:
            logger.api_debug("qBittorrent", "Using HTTP Basic Auth")
            self.session.auth = HTTPBasicAuth(username, password)
        else:
            logger.api_debug("qBittorrent", "Using session-based auth")
            # Login to get session cookie
            self._login()

    def _login(self) -> bool:
        """Login to qBittorrent and establish session (for session-based auth)"""
        if self.use_basic_auth:
            return True  # Skip login for basic auth

        try:
            login_url = f"{self.server_url}/api/v2/auth/login"
            data = {"username": self.username, "password": self.password}

            logger.api_debug("qBittorrent", f"Logging in at {login_url}")
            response = self.session.post(login_url, data=data)

            if response.status_code == 200 and response.text == "Ok.":
                logger.api_debug("qBittorrent", "Session login successful")
                return True
            else:
                logger.api_debug(
                    "qBittorrent",
                    f"Session login failed: {response.status_code} - {response.text}",
                )
                return False

        except Exception as e:
            logger.api_debug("qBittorrent", f"Session login error: {e}")
            return False

    def get_torrents(self, filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of torrents"""
        url = f"{self.server_url}/api/v2/torrents/info"
        params = {}

        if filter_status:
            params["filter"] = filter_status

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_completed_torrents(self) -> List[Dict[str, Any]]:
        """Get only completed torrents"""
        return self.get_torrents(filter_status="completed")

    def get_torrent_files(self, torrent_hash: str) -> List[Dict[str, Any]]:
        """Get files for a specific torrent"""
        url = f"{self.server_url}/api/v2/torrents/files"
        params = {"hash": torrent_hash}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def normalize_title_for_matching(self, title: str) -> str:
        """Normalize torrent name for better matching with media titles"""
        # Convert dots to spaces first (common in torrent names)
        title = title.replace(".", " ")

        # Remove common torrent naming patterns
        title = re.sub(r"\b\d{4}\b", "", title)  # Remove years
        title = re.sub(
            r"\b(1080p|720p|2160p|4K|HDR|x264|x265|h264|h265|HEVC|BluRay|WEB-DL|WEBRip|BDRip|HDTC|AMZN|ZEE5|WEB|DL|DUAL|Hindi|English|AAC|CineVood|mkv|mp4|avi)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )
        title = re.sub(
            r"\b(PROPER|REPACK|INTERNAL|LIMITED|EXTENDED|UNRATED|DIRECTORS|CUT|For|Justice)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )
        title = re.sub(r"\[.*?\]", "", title)  # Remove brackets content
        title = re.sub(r"\(.*?\)", "", title)  # Remove parentheses content
        title = re.sub(r"[^\w\s]", " ", title)  # Replace special chars with spaces
        title = re.sub(r"\s+", " ", title).strip().lower()  # Normalize whitespace
        return title

    def find_matching_torrents(
        self, media_title: str, media_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find torrents that might match a media title"""
        completed_torrents = self.get_completed_torrents()
        normalized_media = self.normalize_title_for_matching(media_title)

        matches = []

        for torrent in completed_torrents:
            torrent_name = torrent.get("name", "")
            normalized_torrent = self.normalize_title_for_matching(torrent_name)

            # Calculate similarity
            similarity = self._calculate_similarity(
                normalized_media, normalized_torrent
            )

            # Boost score if years match
            year_bonus = 0.0
            if media_year:
                if str(media_year) in torrent_name:
                    year_bonus = 0.2

            total_score = similarity + year_bonus

            if total_score >= 0.6:  # Threshold for matching
                matches.append(
                    {
                        "torrent": torrent,
                        "similarity_score": total_score,
                        "normalized_name": normalized_torrent,
                    }
                )

        # Sort by similarity score descending
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple token matching"""
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        return len(intersection) / len(union) if union else 0.0

    def is_media_in_torrents(
        self,
        media_title: str,
        media_year: Optional[int] = None,
        min_similarity: float = 0.6,
    ) -> bool:
        """Check if media content exists in qBittorrent completed torrents"""
        matches = self.find_matching_torrents(media_title, media_year)

        if matches:
            best_match = matches[0]
            is_match = best_match["similarity_score"] >= min_similarity
            logger.api_debug(
                "qBittorrent",
                f"Match for '{media_title}': {best_match['torrent']['name']} (score: {best_match['similarity_score']:.2f}, threshold: {min_similarity})",
            )
            return is_match

        logger.api_debug("qBittorrent", f"No torrent match found for '{media_title}'")
        return False

    def get_torrent_properties(self, torrent_hash: str) -> Dict[str, Any]:
        """Get properties of a specific torrent"""
        url = f"{self.server_url}/api/v2/torrents/properties"
        params = {"hash": torrent_hash}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> bool:
        """Test connection to qBittorrent"""
        try:
            # Try to get torrent list as a connection test
            self.get_torrents()
            return True
        except Exception as e:
            logger.api_debug("qBittorrent", f"Connection test failed: {e}")
            return False

    def get_version(self) -> str:
        """Get qBittorrent version"""
        try:
            url = f"{self.server_url}/api/v2/app/version"
            response = self.session.get(url)
            response.raise_for_status()
            return response.text.strip()
        except:
            return "Unknown"
