#!/usr/bin/env python3
"""
Test scan for Red Dwarf S12 to verify metadata extraction.

This script scans just the Red Dwarf S12 folder to verify that:
- Resolution is detected correctly
- Codec information is extracted
- File size is calculated
- MD5 hash is generated
- All metadata fields are populated
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load .env file from backend directory
from dotenv import load_dotenv
backend_dir = Path(__file__).parent / "backend"
env_file = backend_dir / ".env"
load_dotenv(env_file)

from app.database import SessionLocal
from app.services.scanner_service import ScannerService
from app.config import get_settings


def test_scan_red_dwarf():
    """Scan Red Dwarf S12 folder and verify metadata."""

    settings = get_settings()

    # Red Dwarf S12 path
    test_path = "/mnt/nas-media/volume1/docker/transmission/downloads/complete/tv/Red.Dwarf.S12.1080p.BluRay.x264-SHORTBREHD [NO RAR]"

    print("=" * 70)
    print("MediaVault Test Scan - Red Dwarf S12")
    print("=" * 70)
    print()
    print(f"Target: {test_path}")
    print()

    # Check path exists
    if not Path(test_path).exists():
        print(f"ERROR: Path does not exist: {test_path}")
        return 1

    # Count video files
    video_files = list(Path(test_path).glob("*.mkv"))
    print(f"Found {len(video_files)} MKV files:")
    for vf in video_files:
        size_mb = vf.stat().st_size / (1024 * 1024)
        print(f"  - {vf.name} ({size_mb:.1f} MB)")
    print()

    # Create scanner service
    db = SessionLocal()
    try:
        scanner = ScannerService(db)

        print("Starting scan...")
        print("This will:")
        print("  1. Extract metadata (resolution, codecs, duration, etc.)")
        print("  2. Calculate MD5 hashes (may take a few minutes)")
        print("  3. Parse filename for show/season/episode info")
        print("  4. Store in database")
        print()

        # Run scan on this specific directory
        # Pass the absolute path directly since mounts are at subdirectories
        scan_history = scanner.scan_nas(
            paths=[test_path],
            scan_type="full"
        )

        results = {
            'files_scanned': scan_history.files_found,
            'files_added': scan_history.files_new,
            'files_updated': scan_history.files_updated,
            'errors': scan_history.errors_count
        }

        print()
        print("=" * 70)
        print("Scan Results:")
        print("=" * 70)
        print(f"Files scanned: {results.get('files_scanned', 0)}")
        print(f"Files added: {results.get('files_added', 0)}")
        print(f"Files updated: {results.get('files_updated', 0)}")
        print(f"Errors: {results.get('errors', 0)}")
        print()

        # Query database to verify data
        from app.models.media import MediaFile

        red_dwarf_files = db.query(MediaFile).filter(
            MediaFile.parsed_title.ilike("%red%dwarf%")
        ).all()

        print("=" * 70)
        print(f"Verification: {len(red_dwarf_files)} Red Dwarf episodes in database")
        print("=" * 70)
        print()

        if red_dwarf_files:
            # Show detailed info for first file
            file = red_dwarf_files[0]
            print(f"Sample Entry (Episode {file.parsed_episode}):")
            print(f"  Filename: {file.filename}")
            print(f"  Resolution: {file.resolution}")
            print(f"  Video Codec: {file.video_codec}")
            print(f"  Audio Codec: {file.audio_codec}")
            print(f"  File Size: {file.file_size / (1024*1024*1024):.2f} GB")
            print(f"  Duration: {file.duration} seconds")
            print(f"  Bitrate: {file.bitrate} kbps" if file.bitrate else "  Bitrate: N/A")
            print(f"  MD5 Hash: {file.md5_hash[:16]}..." if file.md5_hash else "  MD5 Hash: NOT CALCULATED")
            print(f"  Audio Channels: {file.audio_channels}")
            print(f"  Audio Languages: {file.audio_languages}")
            print(f"  Show: {file.parsed_title} S{file.parsed_season:02d}E{file.parsed_episode:02d}")
            print(f"  Year: {file.parsed_year}")
            print(f"  Release Group: {file.parsed_release_group}")
            print()

            # Summary for all files
            print("All Episodes:")
            for f in sorted(red_dwarf_files, key=lambda x: x.parsed_episode or 0):
                has_md5 = "✓" if f.md5_hash else "✗"
                has_resolution = "✓" if f.resolution else "✗"
                has_codec = "✓" if f.video_codec else "✗"
                print(f"  E{f.parsed_episode:02d}: {f.filename[:50]:<50} | MD5:{has_md5} | Res:{has_resolution} | Codec:{has_codec}")
            print()

            # Check completeness
            missing_md5 = sum(1 for f in red_dwarf_files if not f.md5_hash)
            missing_resolution = sum(1 for f in red_dwarf_files if not f.resolution)
            missing_codec = sum(1 for f in red_dwarf_files if not f.video_codec)

            print("Completeness Check:")
            print(f"  MD5 Hashes: {len(red_dwarf_files) - missing_md5}/{len(red_dwarf_files)}")
            print(f"  Resolution: {len(red_dwarf_files) - missing_resolution}/{len(red_dwarf_files)}")
            print(f"  Video Codec: {len(red_dwarf_files) - missing_codec}/{len(red_dwarf_files)}")
            print()

            if missing_md5 == 0 and missing_resolution == 0 and missing_codec == 0:
                print("✓ ALL METADATA CAPTURED SUCCESSFULLY!")
                return 0
            else:
                print("⚠ Some metadata is missing")
                return 1
        else:
            print("ERROR: No Red Dwarf files found in database after scan")
            return 1

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = test_scan_red_dwarf()
    sys.exit(exit_code)
