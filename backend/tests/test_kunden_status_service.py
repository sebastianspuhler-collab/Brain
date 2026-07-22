import json

import pytest

from app.services import kunden_status_service as svc


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
    monkeypatch.setattr(svc, "complete_json", lambda *a, **kw: json.dumps(
        {"status": "neuer_kontakt", "sicherheit": "hoch",
         "begruendung": "x", "quellen": ["kickoff.md"], "warnsignal": None}
    ))

    ergebnis = svc.bewerte_kunde(kunde)
    assert ergebnis["status"] == "auftrag"  # Floor aus Vertraege/ gewinnt
    assert ergebnis["sicherheit"] == "niedrig"


def test_bewerte_kunde_downgrades_confidence_on_hallucinated_source(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    monkeypatch.setattr(svc, "complete_json", lambda *a, **kw: json.dumps(
        {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
         "quellen": ["kickoff.md", "erfundene-datei.md"], "warnsignal": None}
    ))

    ergebnis = svc.bewerte_kunde(kunde)
    assert ergebnis["sicherheit"] == "niedrig"
    assert ergebnis["quellen"] == ["kickoff.md"]


def test_floor_status_for_lead_file_uses_byte_size_heuristic(tmp_path):
    kurz = tmp_path / "kurz.md"
    kurz.write_text("x" * 100, encoding="utf-8")
    lang = tmp_path / "lang.md"
    lang.write_text("x" * 900, encoding="utf-8")
    assert svc._floor_status(kurz) == "neuer_kontakt"
    assert svc._floor_status(lang) == "erstgespraech"


def test_sammle_dokumente_reads_single_lead_file(tmp_path):
    lead = tmp_path / "lead.md"
    lead.write_text(
        "---\ndatum: 2026-07-02\nkategorie: Lead\n---\n\n## Zusammenfassung\nErstgespräch mit Interessent.\n",
        encoding="utf-8",
    )
    dokumente = svc._sammle_dokumente(lead)
    assert len(dokumente) == 1
    assert dokumente[0]["datei"] == "lead.md"
    assert dokumente[0]["ordner"] == "Leads"
    assert dokumente[0]["zusammenfassung"] == "Erstgespräch mit Interessent."


def test_sammle_dokumente_includes_lead_korrespondenz_ordner(tmp_path):
    lead = tmp_path / "2026-07-14-Zillmer-Elektrotechnik.md"
    lead.write_text(
        "---\ndatum: 2026-07-14\nkategorie: Lead\n---\n\n## Zusammenfassung\nErstgespräch geführt.\n",
        encoding="utf-8",
    )
    korr_dir = tmp_path / "Zillmer-Elektrotechnik-Korrespondenz"
    korr_dir.mkdir()
    (korr_dir / "2026-07-20-Email-abcd1234-Update.md").write_text(
        "---\ntype: email-korrespondenz\nlead: Zillmer-Elektrotechnik\ndatum: 2026-07-20\n---\n\n"
        "## Zusammenfassung\nNeuer Termin am 21.07. bestätigt.\n",
        encoding="utf-8",
    )
    dokumente = svc._sammle_dokumente(lead)
    assert len(dokumente) == 2
    # neuestes zuerst
    assert dokumente[0]["datei"] == "2026-07-20-Email-abcd1234-Update.md"
    assert dokumente[0]["zusammenfassung"] == "Neuer Termin am 21.07. bestätigt."
    assert dokumente[1]["datei"] == "2026-07-14-Zillmer-Elektrotechnik.md"


def test_sammle_dokumente_lead_without_korrespondenz_ordner_unaffected(tmp_path):
    lead = tmp_path / "lead.md"
    lead.write_text(
        "---\ndatum: 2026-07-02\nkategorie: Lead\n---\n\n## Zusammenfassung\nErstgespräch.\n",
        encoding="utf-8",
    )
    dokumente = svc._sammle_dokumente(lead)
    assert len(dokumente) == 1


def test_bewerte_kunde_propagates_ist_relevant_false(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    monkeypatch.setattr(svc, "complete_json", lambda *a, **kw: json.dumps(
        {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
         "quellen": ["kickoff.md"], "warnsignal": None,
         "ist_relevant": False, "relevanz_begruendung": "Externer Dienstleister, kein Kunde.",
         "anzeige_name": "TestKunde", "aktueller_stand": ""}
    ))

    ergebnis = svc.bewerte_kunde(kunde, kunde_name="TestKunde")
    assert ergebnis["ist_relevant"] is False
    assert ergebnis["relevanz_begruendung"] == "Externer Dienstleister, kein Kunde."


def test_bewerte_kunde_falls_back_to_kunde_name_when_llm_omits_anzeige_name(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    monkeypatch.setattr(svc, "complete_json", lambda *a, **kw: json.dumps(
        {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
         "quellen": ["kickoff.md"], "warnsignal": None}
    ))

    ergebnis = svc.bewerte_kunde(kunde, kunde_name="TestKunde")
    assert ergebnis["anzeige_name"] == "TestKunde"
    assert ergebnis["ist_relevant"] is True  # Default true, damit nichts faelschlich verschwindet


def test_bewerte_kunde_fallback_on_api_error_defaults_ist_relevant_true(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)

    def boom(*a, **kw):
        raise RuntimeError("API down")

    monkeypatch.setattr(svc, "complete_json", boom)

    ergebnis = svc.bewerte_kunde(kunde, kunde_name="TestKunde")
    assert ergebnis["ist_relevant"] is True
    assert ergebnis["anzeige_name"] == "TestKunde"


def test_get_status_uses_cache_when_input_unchanged(tmp_path, monkeypatch):
    kunde = _make_kunde(tmp_path, meetings=True)
    calls = []

    def fake_complete_json(*a, **kw):
        calls.append(1)
        return json.dumps(
            {"status": "erstgespraech", "sicherheit": "hoch", "begruendung": "x",
             "quellen": ["kickoff.md"], "warnsignal": None}
        )

    monkeypatch.setattr(svc, "complete_json", fake_complete_json)
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
