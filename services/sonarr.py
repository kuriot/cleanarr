"""
Sonarr service for TV series management
"""

from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from utils import logger


class SonarrClient:
    """Client for interacting with Sonarr API"""

    def __init__(
        self,
        server_url: str,
        api_key: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {"X-Api-Key": api_key, "Content-Type": "application/json"}
        )

        # Add basic auth if credentials provided
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)

    def get_series(self) -> List[Dict[str, Any]]:
        """Get all series from Sonarr"""
        url = f"{self.server_url}/api/v3/series"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_series_by_title(
        self, title: str, year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find series by title and optionally year"""
        series_list = self.get_series()

        for series in series_list:
            series_title = series.get("title", "").lower()
            series_year = series.get("year")

            if series_title == title.lower():
                if year is None or series_year == year:
                    return series

        return None

    def get_series_by_tvdb_id(self, tvdb_id: int) -> Optional[Dict[str, Any]]:
        """Find series by TVDB ID"""
        series_list = self.get_series()

        for series in series_list:
            if series.get("tvdbId") == tvdb_id:
                return series

        return None

    def delete_series(
        self, series_id: int, delete_files: bool = True, add_exclusion: bool = False
    ) -> bool:
        """Delete a series from Sonarr"""
        url = f"{self.server_url}/api/v3/series/{series_id}"
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportExclusion": str(add_exclusion).lower(),
        }

        response = self.session.delete(url, params=params)
        response.raise_for_status()
        return response.status_code in [200, 204]

    def get_episodes(self, series_id: int) -> List[Dict[str, Any]]:
        """Get all episodes for a specific series"""
        url = f"{self.server_url}/api/v3/episode"
        params = {"seriesId": series_id}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_episode_files(self, series_id: int) -> List[Dict[str, Any]]:
        """Get episode files for a specific series"""
        url = f"{self.server_url}/api/v3/episodefile"
        params = {"seriesId": series_id}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def is_series_fully_watched(self, series_id: int) -> bool:
        """Check if all episodes in a series are monitored and downloaded"""
        episodes = self.get_episodes(series_id)

        # Get only monitored episodes that should be downloaded
        monitored_episodes = [ep for ep in episodes if ep.get("monitored", False)]

        if not monitored_episodes:
            return False

        # Check if all monitored episodes have files
        for episode in monitored_episodes:
            if not episode.get("hasFile", False):
                return False

        return True

    def get_system_status(self) -> Dict[str, Any]:
        """Get Sonarr system status"""
        url = f"{self.server_url}/api/v3/system/status"
        logger.api_debug("Sonarr", f"Attempting to connect at: {url}")
        response = self.session.get(url)
        logger.api_debug("Sonarr", f"Response status: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> bool:
        """Test connection to Sonarr"""
        try:
            logger.api_debug("Sonarr", f"Testing connection to {self.server_url}")
            logger.api_debug(
                "Sonarr",
                (
                    f"Using API key: {self.api_key[:8]}..."
                    if self.api_key
                    else "No API key"
                ),
            )
            logger.api_debug(
                "Sonarr", f"Using basic auth: {'Yes' if self.session.auth else 'No'}"
            )

            status = self.get_system_status()
            logger.api_debug("Sonarr", f"System status: {status}")

            if "version" in status:
                logger.api_debug(
                    "Sonarr", f"Connection successful, version: {status.get('version')}"
                )
                return True
            else:
                logger.api_debug("Sonarr", "Response missing version field")
                return False

        except Exception as e:
            logger.api_debug("Sonarr", f"Connection failed: {type(e).__name__}: {e}")
            return False

    def get_series_by_id(self, series_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific series by ID"""
        try:
            url = f"{self.server_url}/api/v3/series/{series_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except:
            return None

    def search_series(self, term: str) -> List[Dict[str, Any]]:
        """Search for series by title"""
        url = f"{self.server_url}/api/v3/series/lookup"
        params = {"term": term}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_queue(self) -> List[Dict[str, Any]]:
        """Get current download queue"""
        url = f"{self.server_url}/api/v3/queue"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get("records", [])
