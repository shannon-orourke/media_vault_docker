"""Deduplication service for exact and fuzzy duplicate detection."""
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
import guessit
from rapidfuzz import fuzz

from sqlalchemy.orm import Session
from app.models import MediaFile, DuplicateGroup, DuplicateMember
from app.services.quality_service import QualityService
from app.config import get_settings

settings = get_settings()


class DeduplicationService:
    """Service for detecting exact and fuzzy duplicates."""

    def __init__(self, db: Session):
        self.db = db
        self.quality_service = QualityService()
        self.fuzzy_threshold = settings.fuzzy_match_threshold
        self.auto_approve_threshold = settings.quality_auto_approve_threshold
        self.manual_review_threshold = settings.quality_manual_review_threshold

    def find_exact_duplicates(self) -> List[DuplicateGroup]:
        """
        Find exact duplicates based on MD5 hash.

        Returns:
            List of duplicate groups created
        """
        logger.info("Finding exact duplicates by MD5 hash...")

        # Query files grouped by MD5 hash
        from sqlalchemy import func
        hash_groups = (
            self.db.query(MediaFile.md5_hash, func.count(MediaFile.id))
            .filter(MediaFile.md5_hash.isnot(None))
            .filter(MediaFile.is_deleted == False)
            .group_by(MediaFile.md5_hash)
            .having(func.count(MediaFile.id) > 1)
            .all()
        )

        duplicate_groups = []

        for md5_hash, count in hash_groups:
            # Get all files with this hash
            files = (
                self.db.query(MediaFile)
                .filter(MediaFile.md5_hash == md5_hash)
                .filter(MediaFile.is_deleted == False)
                .all()
            )

            if len(files) < 2:
                continue

            # Create duplicate group
            group = self._create_duplicate_group(
                files=files,
                duplicate_type="exact",
                confidence=100.0,
            )

            if group:
                duplicate_groups.append(group)
                logger.info(f"Found exact duplicate group: {group.title} ({len(files)} files)")

        logger.success(f"✓ Found {len(duplicate_groups)} exact duplicate groups")
        return duplicate_groups

    def find_fuzzy_duplicates(self) -> List[DuplicateGroup]:
        """
        Find fuzzy duplicates using guessit + rapidfuzz.

        Returns:
            List of duplicate groups created
        """
        logger.info("Finding fuzzy duplicates using guessit + rapidfuzz...")

        # Get all files that haven't been processed
        files = (
            self.db.query(MediaFile)
            .filter(MediaFile.is_deleted == False)
            .filter(MediaFile.parsed_title.isnot(None))
            .all()
        )

        # Group by parsed metadata
        grouped_files: Dict[str, List[MediaFile]] = {}

        for file in files:
            # Create grouping key based on media type
            if file.media_type == "tv":
                # TV shows: group by title + season + episode
                key = f"{file.parsed_title}|{file.parsed_year or ''}|S{file.parsed_season:02d}E{file.parsed_episode:02d}".lower()
            else:
                # Movies: group by title + year
                key = f"{file.parsed_title}|{file.parsed_year or ''}".lower()

            if key not in grouped_files:
                grouped_files[key] = []
            grouped_files[key].append(file)

        # Find groups with multiple files
        duplicate_groups = []

        for key, file_list in grouped_files.items():
            if len(file_list) < 2:
                continue

            # Verify fuzzy match with rapidfuzz
            verified_groups = self._verify_fuzzy_matches(file_list)

            for verified_files in verified_groups:
                if len(verified_files) < 2:
                    continue

                # Calculate confidence score
                confidence = self._calculate_fuzzy_confidence(verified_files)

                # Create duplicate group
                group = self._create_duplicate_group(
                    files=verified_files,
                    duplicate_type="fuzzy",
                    confidence=confidence,
                )

                if group:
                    duplicate_groups.append(group)
                    logger.info(f"Found fuzzy duplicate group: {group.title} ({len(verified_files)} files, {confidence:.1f}% confidence)")

        logger.success(f"✓ Found {len(duplicate_groups)} fuzzy duplicate groups")
        return duplicate_groups

    def _verify_fuzzy_matches(self, files: List[MediaFile]) -> List[List[MediaFile]]:
        """
        Verify fuzzy matches using filename similarity.

        Returns:
            List of verified duplicate groups
        """
        if len(files) < 2:
            return []

        # Compare all pairs
        groups = []
        used_files = set()

        for i, file1 in enumerate(files):
            if file1.id in used_files:
                continue

            group = [file1]
            used_files.add(file1.id)

            for file2 in files[i + 1:]:
                if file2.id in used_files:
                    continue

                # Calculate similarity
                similarity = fuzz.ratio(file1.filename.lower(), file2.filename.lower())

                if similarity >= self.fuzzy_threshold:
                    group.append(file2)
                    used_files.add(file2.id)

            if len(group) >= 2:
                groups.append(group)

        return groups

    def _calculate_fuzzy_confidence(self, files: List[MediaFile]) -> float:
        """Calculate confidence score for fuzzy match group."""
        if len(files) < 2:
            return 0.0

        # Calculate average pairwise similarity
        similarities = []
        for i, file1 in enumerate(files):
            for file2 in files[i + 1:]:
                similarity = fuzz.ratio(file1.filename.lower(), file2.filename.lower())
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _create_duplicate_group(
        self,
        files: List[MediaFile],
        duplicate_type: str,
        confidence: float
    ) -> Optional[DuplicateGroup]:
        """
        Create a duplicate group and analyze quality differences.

        Returns:
            Created DuplicateGroup or None
        """
        if len(files) < 2:
            return None

        # Rank files by quality
        files_metadata = []
        for file in files:
            files_metadata.append({
                "id": file.id,
                "quality_score": file.quality_score if file.quality_score is not None else 0,
                "quality_tier": file.quality_tier,
                "video_codec": file.video_codec,
                "bitrate": file.bitrate,
                "audio_channels": file.audio_channels,
                "audio_track_count": file.audio_track_count,
                "subtitle_track_count": file.subtitle_track_count,
                "hdr_type": file.hdr_type,
                "audio_languages": file.audio_languages,
                "subtitle_languages": file.subtitle_languages,
                "dominant_audio_language": file.dominant_audio_language,
            })

        ranked_files = self.quality_service.rank_files(files_metadata)

        # Determine recommended action
        best_file = ranked_files[0]
        worst_file = ranked_files[-1]
        quality_diff = best_file["quality_score"] - worst_file["quality_score"]

        if quality_diff < self.manual_review_threshold:
            recommended_action = "manual_review"
            action_reason = f"Quality difference too small ({quality_diff} points) - requires manual review"
        elif quality_diff >= self.auto_approve_threshold:
            # Check language concerns
            has_language_concern = False
            for file_meta in ranked_files[1:]:  # Check files to be deleted
                concern, reason = self.quality_service.check_language_concern(file_meta)
                if concern:
                    has_language_concern = True
                    action_reason = reason
                    break

            if has_language_concern:
                recommended_action = "manual_review"
            else:
                recommended_action = "auto_delete"
                action_reason = f"Clear quality winner (Δ{quality_diff} points)"
        else:
            recommended_action = "manual_review"
            action_reason = f"Moderate quality difference ({quality_diff} points)"

        # Create group hash
        file_ids_sorted = sorted([f.id for f in files])
        group_hash = hashlib.sha256(
            "|".join(map(str, file_ids_sorted)).encode()
        ).hexdigest()

        # Check if group already exists
        existing_group = (
            self.db.query(DuplicateGroup)
            .filter(DuplicateGroup.group_hash == group_hash)
            .first()
        )

        if existing_group:
            logger.debug(f"Duplicate group already exists: {group_hash}")
            return existing_group

        # Create new group
        first_file = files[0]
        group = DuplicateGroup(
            group_hash=group_hash,
            duplicate_type=duplicate_type,
            confidence=confidence,
            title=first_file.parsed_title or first_file.filename,
            year=first_file.parsed_year,
            season=first_file.parsed_season,
            episode=first_file.parsed_episode,
            media_type=first_file.media_type,
            member_count=len(files),
            recommended_action=recommended_action,
            action_reason=action_reason,
            detected_at=datetime.now(),
        )

        self.db.add(group)
        self.db.flush()  # Get group.id

        # Create members with ranks
        for ranked_meta in ranked_files:
            file = next(f for f in files if f.id == ranked_meta["id"])

            # Determine member action
            if ranked_meta["rank"] == 1:
                member_action = "keep"
                member_reason = f"Best quality (score: {ranked_meta['quality_score']})"
            else:
                if recommended_action == "auto_delete":
                    member_action = "delete"
                    member_reason = f"Lower quality (score: {ranked_meta['quality_score']}, rank: {ranked_meta['rank']})"
                else:
                    member_action = "review"
                    member_reason = f"Quality score: {ranked_meta['quality_score']}, rank: {ranked_meta['rank']}"

            member = DuplicateMember(
                duplicate_group_id=group.id,
                media_file_id=file.id,
                rank=ranked_meta["rank"],
                recommended_action=member_action,
                action_reason=member_reason,
            )

            self.db.add(member)

            # Update media file
            file.is_duplicate = True
            file.quality_score = ranked_meta["quality_score"]

        self.db.commit()
        return group
