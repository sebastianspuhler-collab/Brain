from app.services.rag import _extract_entities


def test_extracts_capitalized_entities():
    entities = _extract_entities("Was weißt du über Schaufler und die Rechnung von Mundinger?")
    assert "Schaufler" in entities
    assert "Mundinger" in entities


def test_filters_common_german_stopwords():
    entities = _extract_entities("Was Kann Sie mir sagen")
    assert "Was" not in entities
    assert "Kann" not in entities
    assert "Sie" not in entities


def test_caps_at_four_entities():
    entities = _extract_entities("Alpha Beta Gamma Delta Epsilon Zeta")
    assert len(entities) <= 4
