from app.services.quality_service import QualityService


def test_rank_files_orders_by_quality_score():
    service = QualityService()
    ranked = service.rank_files([
        {"id": 1, "quality_score": 50},
        {"id": 2, "quality_score": 120},
        {"id": 3, "quality_score": 95},
    ])

    assert [item["id"] for item in ranked] == [2, 3, 1]
    assert [item["rank"] for item in ranked] == [1, 2, 3]


def test_check_language_concern_identifies_english_tracks():
    service = QualityService()

    concern, reason = service.check_language_concern({
        "audio_languages": ["eng", "spa"],
        "subtitle_languages": ["eng"],
        "dominant_audio_language": "eng",
    })
    assert concern is True
    assert "English audio" in reason


def test_check_language_concern_flags_foreign_film_with_english_subs():
    service = QualityService()

    concern, reason = service.check_language_concern({
        "audio_languages": ["kor"],
        "subtitle_languages": ["eng"],
        "dominant_audio_language": "kor",
    })
    assert concern is True
    assert "Foreign-film" in reason or "Foreign film" in reason
