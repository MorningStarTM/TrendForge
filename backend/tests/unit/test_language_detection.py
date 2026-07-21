from __future__ import annotations

from app.services.ingestion.normalizer.language_detection import detect_language


def test_empty_text_is_other_without_loading_the_model() -> None:
    assert detect_language("") == "other"
    assert detect_language("   \n  ") == "other"


def test_detects_english() -> None:
    assert detect_language("Best pizza in town, come try it now!") == "en"


def test_detects_arabic() -> None:
    assert detect_language("أفضل بيتزا في المدينة، تعالوا جربوها الآن") == "ar"


def test_other_languages_are_tagged_other() -> None:
    assert detect_language("Le meilleur pizza en ville, venez l'essayer") == "other"
