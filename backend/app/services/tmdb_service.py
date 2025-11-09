"""TMDB API service for metadata and auto-rename."""
import time
from typing import Dict, Any, List, Optional
import requests
from loguru import logger

from app.config import get_settings
from app.models import MediaFile

settings = get_settings()


class TMDBService:
    """Service for interacting with The Movie Database API."""

    def __init__(self):
        self.api_key = settings.tmdb_api_key
        self.read_token = settings.tmdb_read_access_token
        self.base_url = settings.tmdb_base_url
        self.rate_limit = settings.tmdb_rate_limit  # 40 requests per 10 seconds
        self.last_request_times: List[float] = []

    def _rate_limit_check(self):
        """Enforce rate limiting."""
        now = time.time()

        # Remove requests older than 10 seconds
        self.last_request_times = [t for t in self.last_request_times if now - t < 10]

        # If we've hit the limit, wait
        if len(self.last_request_times) >= self.rate_limit:
            sleep_time = 10 - (now - self.last_request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.last_request_times.clear()

        self.last_request_times.append(now)

    def search_title(
        self,
        query: str,
        media_type: str = "multi",
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search TMDB for a title.

        Args:
            query: Search query
            media_type: "movie", "tv", or "multi"
            year: Optional year to filter

        Returns:
            List of search results
        """
        self._rate_limit_check()

        endpoint = f"{self.base_url}search/{media_type}"

        params = {
            "api_key": self.api_key,
            "query": query,
            "include_adult": "false"
        }

        if year:
            if media_type == "movie":
                params["year"] = year
            elif media_type == "tv":
                params["first_air_date_year"] = year

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get("results", [])

        except Exception as e:
            logger.error(f"TMDB search error: {e}")
            return []

    def get_details(
        self,
        tmdb_id: int,
        media_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a movie or TV show.

        Args:
            tmdb_id: TMDB ID
            media_type: "movie" or "tv"

        Returns:
            Full details or None
        """
        self._rate_limit_check()

        endpoint = f"{self.base_url}{media_type}/{tmdb_id}"

        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,videos"
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"TMDB details error: {e}")
            return None

    def get_tv_episode_details(
        self,
        tmdb_id: int,
        season: int,
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """Get TV episode details."""
        self._rate_limit_check()

        endpoint = f"{self.base_url}tv/{tmdb_id}/season/{season}/episode/{episode}"

        params = {"api_key": self.api_key}

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"TMDB episode details error: {e}")
            return None

    def suggest_filename(
        self,
        media_file: MediaFile,
        tmdb_data: Dict[str, Any],
        media_type: str,
        episode_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate suggested filename from TMDB data.

        Args:
            media_file: MediaFile object
            tmdb_data: TMDB show/movie data
            media_type: "movie" or "tv"
            episode_data: Optional episode data for TV shows

        Returns:
            Suggested filename
        """
        extension = media_file.filepath.split(".")[-1]

        if media_type == "movie":
            title = tmdb_data.get("title", "Unknown")
            year = tmdb_data.get("release_date", "")[:4]

            # Format: "Movie Title (Year).mkv"
            filename = f"{title} ({year}).{extension}"

        else:  # TV show
            show_name = tmdb_data.get("name", "Unknown")
            season = media_file.parsed_season or 1
            episode = media_file.parsed_episode or 1

            if episode_data:
                episode_title = episode_data.get("name", "")
                # Format: "Show Name - S01E01 - Episode Title.mkv"
                filename = f"{show_name} - S{season:02d}E{episode:02d} - {episode_title}.{extension}"
            else:
                # Format: "Show Name - S01E01.mkv"
                filename = f"{show_name} - S{season:02d}E{episode:02d}.{extension}"

        # Sanitize filename (remove invalid characters)
        filename = filename.replace("/", "-").replace("\\", "-").replace(":", " -")

        return filename

    def enrich_metadata(
        self,
        media_file: MediaFile,
        tmdb_id: int,
        media_type: str
    ) -> bool:
        """
        Enrich media file with TMDB metadata.

        Args:
            media_file: MediaFile to enrich
            tmdb_id: TMDB ID
            media_type: "movie" or "tv"

        Returns:
            True if successful, False otherwise
        """
        details = self.get_details(tmdb_id, media_type)

        if not details:
            return False

        try:
            # Update TMDB fields
            media_file.tmdb_id = tmdb_id
            media_file.tmdb_title = details.get("title") or details.get("name")
            media_file.tmdb_overview = details.get("overview")
            media_file.tmdb_poster_path = details.get("poster_path")
            media_file.tmdb_rating = details.get("vote_average")

            # Extract genres
            genres = details.get("genres", [])
            media_file.tmdb_genres = [g["name"] for g in genres]

            media_file.tmdb_last_updated = time.time()

            logger.success(f"Enriched metadata for: {media_file.filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to enrich metadata: {e}")
            return False
