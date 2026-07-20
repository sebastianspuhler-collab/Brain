import json
from types import SimpleNamespace

import pytest

from app.services import kunden_status_service as svc


def _fake_response(payload: dict):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])


def _make_kunde(tmp_path, vertraege=False, angebote=False, meetings=False, name="TestKunde"):
    kunde = tmp_path / name
    for sub in ("Vertraege", "Angebote", "Meetings", "Dokumente", "Praesentationen"):
        (kunde / sub).mkdir(parents=True)
    if vertraege:
        (kunde / "Vertraege" / "sla.md").write_text(
            "---\ndatum: 2026-07-01\nkategorie: Vertrag\n---\n\n## Zusammenfassung\nSLA unterschrieben.\n",
            encoding="utf-8",
        )
    if angebote:
        (kunde / "Angebote" / "angebot.md").write_text(
            "---\ndatum: 2026-07-05\nkategorie: Angebot\n---\n\n## Zusammenfassung\nAngebot verschickt.\n",
            encoding="utf-8",
        )
    if meetings:
        (kunde / "Meetings" / "kickoff.md").write_text(
            "---\ndatum: 2026-07-10\nkategorie: Meeting\n---\n\n"
            "## Zusammenfassung\nErstgespräch geführt.\n\n"
            "## Nächste Schritte\n- Angebot erstellen\n",
            encoding="utf-8",
        )
    return kunde


def test_floor_status_ranks_by_folder_contents(tmp_path):
    assert svc._floor_status(_make_kunde(tmp_path, name="K1")) == "neuer_kontakt"
    assert svc._floor_status(_make_kunde(tmp_path, name="K2", meetings=True)) == "erstgespraech"
    assert svc._floor_status(_make_kunde(tmp_path, name="K3", angebote=True)) == "angebotsphase"
    assert svc._floor_status(_make_kunde(tmp_path, name="K4", vertraege=True)) == "auftrag"


def test_sammle_dokumente_reads_frontmatter_and_sections(tmp_path):
    kunde = _make_kunde(tmp_path, meetings=True)
    dokumente = svc._sammle_dokumente(kunde)
    assert len(dokumente) == 1
    d = dokumente[0]
    assert d["datei"] == "kickoff.md"
    assert d["datum"] == "2026-07-10"
    assert d["zusammenfassung"] == "Erstgespräch geführt."
    assert d["naechste_schritte"] == "Angebot erstellen"


def test_bewerte_kunde_enforces_floor_when_llm_understates(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, vertraege=True, meetings=True)
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: _fake_response(
                {"status": "neuer_kontakt", "sicherheit": "hoch",
                 "begruendung": "x", "quellen": ["kickoff.md"], "warnsignal": None}
            )
        )
    )
    monkeypatch.setattr(svc, "get_client", lambda: fake_client)

    ergebnis = svc.bewerte_kunde(kunde)
    assert ergebnis["status"] == "auftrag"  # Floor aus Vertraege/ gewinnt
    assert ergebnis["sicherheit"] == "niedrig"


def test_bewerte_kunde_downgrades_confidence_on_hallucinated_source(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    fake_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: _fake_response(
                {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
                 "quellen": ["kickoff.md", "erfundene-datei.md"], "warnsignal": None}
            )
        )
    )
    monkeypatch.setattr(svc, "get_client", lambda: fake_client)

    ergebnis = svc.bewerte_kunde(kunde)
    assert ergebnis["sicherheit"] == "niedrig"
    assert ergebnis["quellen"] == ["kickoff.md"]


def test_get_status_uses_cache_when_input_unchanged(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    calls = []

    def fake_create(**kwargs):
        calls.append(1)
        return _fake_response(
            {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
             "quellen": ["kickoff.md"], "warnsignal": None}
        )

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(svc, "get_client", lambda: fake_client)
    monkeypatch.setattr(
        type(__import__("app.config", fromlist=["get_settings"]).get_settings()),
        "agent_dir", property(lambda self: tmp_path / "_agent"),
    )
    from app.config import get_settings
    get_settings.cache_clear()

    svc.get_status("TestKunde", kunde)
    svc.get_status("TestKunde", kunde)
    assert len(calls) == 1  # zweiter Aufruf kommt aus dem Cache, kein neuer LLM-Call

    get_settings.cache_clear()
