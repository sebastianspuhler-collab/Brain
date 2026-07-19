"""Zentrale Modell-Konstanten (Sebastian, 2026-07-18: Modellauswahl war über
viele Dateien verstreut hartkodiert, keine zentrale Quelle). Ersetzt die
bisherigen String-Literale in chat.py, inbox.py, classify.py und den übrigen
Services - keine Verhaltensänderung, nur eine gemeinsame Quelle."""


class Models:
    SONNET = "claude-sonnet-5"
    OPUS = "claude-opus-4-8"
    HAIKU = "claude-haiku-4-5-20251001"


ALL_MODELS = {Models.SONNET, Models.OPUS, Models.HAIKU}
