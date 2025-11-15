#!/usr/bin/env python3
"""Test TMDb integration."""
import sys
import os
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv('/home/mercury/projects/mediavault/backend/.env')

sys.path.insert(0, '/home/mercury/projects/mediavault/backend')

from app.services.tmdb_service import TMDbService

# Test search
tmdb = TMDbService()

print("Testing TMDb TV search...")
result = tmdb.enrich_media_metadata("Red Dwarf", None, "tv")
if result:
    print(f"✓ Found: {result.get('tmdb_title')} (ID: {result.get('tmdb_id')})")
    print(f"  TMDb Type: {result.get('tmdb_type')}")
    print(f"  Year: {result.get('tmdb_year')}")
    print(f"  IMDB ID: {result.get('imdb_id')}")
else:
    print("✗ No results found")

print("\nTesting TMDb movie search...")
result = tmdb.enrich_media_metadata("The Matrix", 1999, "movie")
if result:
    print(f"✓ Found: {result.get('tmdb_title')} (ID: {result.get('tmdb_id')})")
    print(f"  TMDb Type: {result.get('tmdb_type')}")
    print(f"  Year: {result.get('tmdb_year')}")
    print(f"  IMDB ID: {result.get('imdb_id')}")
else:
    print("✗ No results found")
