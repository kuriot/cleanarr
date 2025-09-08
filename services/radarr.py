"""
Radarr service for movie management
"""

from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

from utils import logger


class RadarrClient:
    """Client for interacting with Radarr API"""

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

    def get_movies(self) -> List[Dict[str, Any]]:
        """Get all movies from Radarr"""
        url = f"{self.server_url}/api/v3/movie"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_movie_by_title(
        self, title: str, year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find movie by title and optionally year"""
        movies = self.get_movies()

        for movie in movies:
            movie_title = movie.get("title", "").lower()
            movie_year = movie.get("year")

            if movie_title == title.lower():
                if year is None or movie_year == year:
                    return movie

        return None

    def get_movie_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """Find movie by TMDB ID"""
        movies = self.get_movies()

        for movie in movies:
            if movie.get("tmdbId") == tmdb_id:
                return movie

        return None

    def delete_movie(
        self, movie_id: int, delete_files: bool = True, add_exclusion: bool = False
    ) -> bool:
        """Delete a movie from Radarr"""
        url = f"{self.server_url}/api/v3/movie/{movie_id}"
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportExclusion": str(add_exclusion).lower(),
        }

        response = self.session.delete(url, params=params)
        response.raise_for_status()
        return response.status_code in [200, 204]

    def get_movie_files(self, movie_id: int) -> List[Dict[str, Any]]:
        """Get movie files for a specific movie"""
        url = f"{self.server_url}/api/v3/moviefile"
        params = {"movieId": movie_id}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_system_status(self) -> Dict[str, Any]:
        """Get Radarr system status"""
        url = f"{self.server_url}/api/v3/system/status"
        logger.api_debug("Radarr", f"Attempting to connect at: {url}")
        response = self.session.get(url)
        logger.api_debug("Radarr", f"Response status: {response.status_code}")
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> bool:
        """Test connection to Radarr"""
        try:
            logger.api_debug("Radarr", f"Testing connection to {self.server_url}")
            logger.api_debug(
                "Radarr",
                (
                    f"Using API key: {self.api_key[:8]}..."
                    if self.api_key
                    else "No API key"
                ),
            )
            logger.api_debug(
                "Radarr", f"Using basic auth: {'Yes' if self.session.auth else 'No'}"
            )

            status = self.get_system_status()
            logger.api_debug("Radarr", f"System status: {status}")

            if "version" in status:
                logger.api_debug(
                    "Radarr", f"Connection successful, version: {status.get('version')}"
                )
                return True
            else:
                logger.api_debug("Radarr", "Response missing version field")
                return False

        except Exception as e:
            logger.api_debug("Radarr", f"Connection failed: {type(e).__name__}: {e}")
            return False

    def get_movie_by_id(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific movie by ID"""
        try:
            url = f"{self.server_url}/api/v3/movie/{movie_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except:
            return None

    def search_movies(self, term: str) -> List[Dict[str, Any]]:
        """Search for movies by title"""
        url = f"{self.server_url}/api/v3/movie/lookup"
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
