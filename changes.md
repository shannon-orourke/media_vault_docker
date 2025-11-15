# Changes — 2025-11-10

## Frontend Scanner Defaults (Codex)
- Updated backend default NAS scan paths in `backend/app/config.py` to `/volume1/docker/transmission/downloads/complete/tv`, `/volume1/docker/transmission/downloads/complete/movies`, `/volume1/videos`, and `/volume1/docker/data/torrents/torrents`.
- Synced frontend scanner defaults (`frontend/src/pages/Scanner.tsx`) with the new NAS paths so the textarea initial value and placeholder match.
- Rebuilt the frontend production bundle (`frontend/dist`) so the deployment can pick up the updated scanner defaults.

## TMDb/IMDB Integration (Claude)
- Created `backend/app/services/tmdb_service.py` with full TMDb API integration including TV/movie search, external ID fetching (IMDB), and rate limiting (40 req/10sec).
- Integrated TMDb enrichment into `backend/app/services/scanner_service.py` to automatically fetch metadata during scans.
- Added database migration `002_add_tmdb_imdb_fields.sql` to add `tmdb_type`, `tmdb_year`, and `imdb_id` columns to `media_files` table.
- Updated `backend/app/models/media.py` to include new TMDb/IMDB fields.
- Updated `backend/app/routes/media.py` to return TMDb/IMDB fields in API responses.
- Updated `frontend/src/pages/Library.tsx` to show "View on TMDb" and "View on IMDB" buttons with direct links when metadata is available, fallback to "Search TMDb" otherwise.
- Updated `frontend/src/services/api.ts` TypeScript interfaces to include TMDb/IMDB fields.
- Fixed import errors in `backend/app/routes/rename.py` (corrected `TMDBService` to `TMDbService`).
- Cleared Python bytecode cache to force reload of updated models.
- Backend restarted successfully on port 8007 with TMDb integration active.
