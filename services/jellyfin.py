"""
Jellyfin service for media management
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from utils import logger


class JellyfinClient:
    """Client for interacting with Jellyfin API"""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Emby-Token": api_key, "Content-Type": "application/json"}
        )

        # Detect API base path
        self.api_base = self._detect_api_base()

    def _detect_api_base(self) -> str:
        """Detect the correct API base path for Jellyfin"""
        # Try different common API base paths
        possible_bases = ["", "/jellyfin", "/emby"]

        for base in possible_bases:
            try:
                test_url = f"{self.server_url}{base}/Users/Me"
                logger.api_debug("Jellyfin", f"Testing API base at: {test_url}")
                response = self.session.get(test_url, timeout=10)
                logger.api_debug("Jellyfin", f"Response status: {response.status_code}")
                if response.status_code == 200:
                    logger.api_debug(
                        "Jellyfin", f"Found working API base: {base or 'root'}"
                    )
                    return base
            except Exception as e:
                logger.api_debug("Jellyfin", f"Failed to test {test_url}: {e}")
                continue

        # Default to empty (root path) if detection fails
        logger.api_debug("Jellyfin", "API detection failed, using root path")
        return ""

    def get_current_user(self) -> Dict[str, Any]:
        """Get current user from Jellyfin server"""
        url = f"{self.server_url}{self.api_base}/Users/Me"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users from Jellyfin server (requires admin privileges)"""
        url = f"{self.server_url}{self.api_base}/Users"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_watched_items(
        self, user_id: str, item_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get watched items for a specific user"""
        if item_types is None:
            item_types = ["Movie", "Series"]

        params = {
            "UserId": user_id,
            "IncludeItemTypes": ",".join(item_types),
            "Filters": "IsPlayed",
            "Recursive": "true",
            "Fields": "Name,OriginalTitle,ProductionYear,Overview,Genres,RunTimeTicks,DateCreated,UserData",
        }

        url = f"{self.server_url}{self.api_base}/Items"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("Items", [])

    def get_watched_episodes_for_series(
        self, user_id: str, series_id: str
    ) -> List[Dict[str, Any]]:
        """Get watched episodes for a specific series and user"""
        params = {
            "UserId": user_id,
            "ParentId": series_id,
            "IncludeItemTypes": "Episode",
            "Filters": "IsPlayed",
            "Recursive": "true",
            "Fields": "Name,ParentIndexNumber,IndexNumber,SeasonName,Overview,RunTimeTicks,DateCreated,UserData",
        }

        url = f"{self.server_url}{self.api_base}/Items"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("Items", [])

    def get_favorite_episodes_for_series(
        self, user_id: str, series_id: str
    ) -> List[Dict[str, Any]]:
        """Get favorite episodes for a specific series and user"""
        params = {
            "UserId": user_id,
            "ParentId": series_id,
            "IncludeItemTypes": "Episode",
            "Filters": "IsFavorite",
            "Recursive": "true",
            "Fields": "Name,ParentIndexNumber,IndexNumber,UserData",
        }

        url = f"{self.server_url}{self.api_base}/Items"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("Items", [])

    def get_favorite_seasons_for_series(
        self, user_id: str, series_id: str
    ) -> List[Dict[str, Any]]:
        """Get favorite seasons for a specific series and user"""
        params = {
            "UserId": user_id,
            "ParentId": series_id,
            "IncludeItemTypes": "Season",
            "Filters": "IsFavorite",
            "Recursive": "false",
            "Fields": "Name,IndexNumber,UserData",
        }

        url = f"{self.server_url}{self.api_base}/Items"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("Items", [])

    def format_runtime(self, runtime_ticks: int) -> str:
        """Convert runtime ticks to human readable format"""
        if not runtime_ticks:
            return "Unknown"

        total_seconds = runtime_ticks // 10000000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def mark_as_watched(
        self, item_id: str, user_id: str, date_played: Optional[datetime] = None
    ) -> bool:
        """Mark an item as watched for a specific user"""
        if date_played is None:
            date_played = datetime.now()

        # Format date in ISO format with timezone
        date_str = date_played.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        url = f"{self.server_url}{self.api_base}/UserPlayedItems/{item_id}"
        params = {"userId": user_id, "datePlayed": date_str}

        response = self.session.post(url, params=params)
        response.raise_for_status()
        return response.status_code == 200

    def mark_as_unwatched(self, item_id: str, user_id: str) -> bool:
        """Mark an item as unwatched for a specific user"""
        url = f"{self.server_url}{self.api_base}/UserPlayedItems/{item_id}"
        params = {"userId": user_id}

        response = self.session.delete(url, params=params)
        response.raise_for_status()
        return response.status_code == 200

    def get_unwatched_items(
        self, user_id: str, item_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get unwatched items for a specific user"""
        if item_types is None:
            item_types = ["Movie", "Series"]

        params = {
            "UserId": user_id,
            "IncludeItemTypes": ",".join(item_types),
            "Filters": "IsUnplayed",
            "Recursive": "true",
            "Fields": "Name,OriginalTitle,ProductionYear,Overview,Genres,RunTimeTicks,DateCreated,UserData",
        }

        url = f"{self.server_url}{self.api_base}/Items"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("Items", [])

    def delete_item(self, item_id: str) -> bool:
        """Delete a media item (and its files)"""
        url = f"{self.server_url}{self.api_base}/Items/{item_id}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.status_code in (200, 204)
