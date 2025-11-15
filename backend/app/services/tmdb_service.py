"""TMDb (The Movie Database) API service for metadata enrichment."""
import time
from typing import Optional, Dict, Any
import requests
from loguru import logger

from app.config import get_settings

settings = get_settings()


class TMDbService:
    """Service for interacting with The Movie Database API."""

    def __init__(self):
        self.api_key = settings.tmdb_api_key
        self.read_token = settings.tmdb_read_access_token
        self.base_url = settings.tmdb_base_url
        self.rate_limit = settings.tmdb_rate_limit

        # Rate limiting
        self.request_times = []

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.read_token}',
            'Content-Type': 'application/json;charset=utf-8'
        })

    def _rate_limit(self):
        """Implement rate limiting (40 requests per 10 seconds)."""
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 10]

        if len(self.request_times) >= self.rate_limit:
            sleep_time = 10 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_times = []

        self.request_times.append(now)

    def search_tv(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a TV show."""
        self._rate_limit()

        params = {'query': title, 'include_adult': False}
        if year:
            params['first_air_date_year'] = year

        try:
            response = self.session.get(f"{self.base_url}search/tv", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get('results', [])

            if results:
                show = results[0]
                return {
                    'tmdb_id': show.get('id'),
                    'tmdb_type': 'tv',
                    'tmdb_title': show.get('name'),
                    'tmdb_year': int(show.get('first_air_date', '').split('-')[0]) if show.get('first_air_date') else None,
                    'tmdb_overview': show.get('overview'),
                    'tmdb_poster_path': show.get('poster_path'),
                }
            return None
        except Exception as e:
            logger.error(f"TMDb search error: {e}")
            return None

    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Search for a movie."""
        self._rate_limit()

        params = {'query': title, 'include_adult': False}
        if year:
            params['year'] = year

        try:
            response = self.session.get(f"{self.base_url}search/movie", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get('results', [])

            if results:
                movie = results[0]
                return {
                    'tmdb_id': movie.get('id'),
                    'tmdb_type': 'movie',
                    'tmdb_title': movie.get('title'),
                    'tmdb_year': int(movie.get('release_date', '').split('-')[0]) if movie.get('release_date') else None,
                    'tmdb_overview': movie.get('overview'),
                    'tmdb_poster_path': movie.get('poster_path'),
                }
            return None
        except Exception as e:
            logger.error(f"TMDb search error: {e}")
            return None

    def get_external_ids(self, tmdb_id: int, media_type: str) -> Optional[str]:
        """Get IMDB ID for a TMDb entry."""
        self._rate_limit()

        try:
            endpoint = f"{media_type}/{tmdb_id}/external_ids"
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            response.raise_for_status()
            return response.json().get('imdb_id')
        except Exception as e:
            logger.error(f"TMDb external IDs error: {e}")
            return None

    def enrich_media_metadata(self, title: str, year: Optional[int], media_type: str) -> Optional[Dict[str, Any]]:
        """Enrich media file with TMDb and IMDB metadata."""
        if not title:
            return None

        result = self.search_tv(title, year) if media_type == "tv" else self.search_movie(title, year)

        if result and result.get('tmdb_id'):
            imdb_id = self.get_external_ids(result['tmdb_id'], result['tmdb_type'])
            if imdb_id:
                result['imdb_id'] = imdb_id

        return result
