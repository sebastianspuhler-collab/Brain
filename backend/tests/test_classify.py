import json
from pathlib import Path

from app.services import classify as svc
from app.services.classify import SKIP_EXTENSIONS, extract_text, is_meeting_transcript


def test_skip_extensions_cover_code_files():
    assert ".js" in SKIP_EXTENSIONS
    assert ".lock" in SKIP_EXTENSIONS


def test_extract_text_reads_plain_markdown(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Titel\n\nInhalt der Notiz", encoding="utf-8")
    assert extract_text(f) == "# Titel\n\nInhalt der Notiz"


def test_extract_text_unknown_format_is_labeled(tmp_path):
    f = tmp_path / "archive.xyz"
    f.write_bytes(b"binary-ish")
    assert extract_text(f) == "[Unbekanntes Format: .xyz]"


def test_extract_text_image_has_no_text(tmp_path):
    f = tmp_path / "photo.png"
    f.write_bytes(b"\x89PNG")
    assert extract_text(f) == "[Bilddatei, kein Text extrahierbar]"


# ── Transkript-Erkennung (2026-07-27) ────────────────────────────────────────
# Hintergrund: Lead-Gespräche landeten in Leads/[Lead]-Korrespondenz/ statt in
# einem Meetings-Ordner und fehlten dadurch in der Transkripte-Übersicht
# (files.py:list_meetings filtert auf "Meetings" im Pfad).

def test_teams_transkript_wird_erkannt():
    inhalt = (
        "Update Zillmer X Prozessia-20260721_105953-Besprechungstranskript\n"
        "21. Juli 2026, 08:59AM\nSebastian Spuhler Transkription gestartet"
    )
    assert is_meeting_transcript(Path("Update Zillmer X Prozessia.docx"), inhalt, {})


def test_google_meet_transkript_wird_erkannt():
    assert is_meeting_transcript(
        Path("New Record from Google Meet (1).pdf"), "Teilnehmer sprechen ...", {}
    )


def test_transkript_tag_reicht_als_hinweis():
    assert is_meeting_transcript(
        Path("gespraech.docx"), "irgendein Text", {"tags": ["Lead", "Besprechungstranskript"]}
    )


def test_angebot_ist_kein_transkript():
    assert not is_meeting_transcript(
        Path("Angebot_AG0027.pdf"),
        "Angebot über die Einrichtung eines Beschaffungsagenten",
        {"tags": ["Angebot", "Kunde"]},
    )


# ── Zielordner-Sanitizing (Klassifizierungs-Robustheit, 2026-08-20) ────────

def test_sanitize_zielordner_passes_normal_path_through():
    assert svc._sanitize_zielordner("Kunden/Schaufler/Dokumente") == "Kunden/Schaufler/Dokumente"


def test_sanitize_zielordner_rejects_path_traversal():
    assert svc._sanitize_zielordner("../../etc/passwd") == "Memos"


def test_sanitize_zielordner_rejects_empty_or_absolute():
    assert svc._sanitize_zielordner("") == "Memos"
    assert svc._sanitize_zielordner("/etc/passwd") == "Memos"


# ── Trivial-Bild-Filter (Klassifizierungs-Robustheit, 2026-08-20) ──────────

def test_trivial_image_detected_by_size(tmp_path):
    f = tmp_path / "signature.png"
    f.write_bytes(b"x" * 500)
    assert svc._is_trivial_image(f)


def test_trivial_image_detected_by_outlook_inline_name(tmp_path):
    f = tmp_path / "image001.png"
    f.write_bytes(b"x" * 50_000)
    assert svc._is_trivial_image(f)


def test_large_image_is_not_trivial(tmp_path):
    f = tmp_path / "scan.jpg"
    f.write_bytes(b"x" * 500_000)
    assert not svc._is_trivial_image(f)


def test_non_image_is_never_trivial(tmp_path):
    f = tmp_path / "vertrag.pdf"
    f.write_bytes(b"x" * 100)
    assert not svc._is_trivial_image(f)


# ── Dedup-Check (Klassifizierungs-Robustheit, 2026-08-20) ──────────────────

class _FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path
        self.inbox_dir = tmp_path / "_inbox"
        self.agent_dir = tmp_path / "_agent"
        self.memory_path = tmp_path / "_agent" / "memory.md"
        self.mistral_api_key = ""


def _fake_classify_json(**overrides):
    base = {
        "kategorie": "Kunde", "zusammenfassung": "Testdokument", "tags": ["Test"],
        "zielordner": "Kunden/TestKunde/Dokumente", "neuer_kunde": False,
        "unsicher": False, "unsicherheitsgrund": "",
    }
    base.update(overrides)
    return json.dumps(base)


def test_process_file_flags_duplicate_by_content_hash(tmp_path, monkeypatch):
    settings = _FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc, "complete_json", lambda *a, **kw: _fake_classify_json())
    settings.inbox_dir.mkdir(parents=True)

    f1 = settings.inbox_dir / "vertrag.txt"
    f1.write_text("Identischer Inhalt fuer Dedup-Test", encoding="utf-8")
    ok1, info1 = svc.process_file(f1)
    assert ok1 and not info1.startswith("Duplikat")

    f2 = settings.inbox_dir / "vertrag_kopie.txt"
    f2.write_text("Identischer Inhalt fuer Dedup-Test", encoding="utf-8")
    ok2, info2 = svc.process_file(f2)
    assert not ok2
    assert info2.startswith("Duplikat von ")
    # Datei wurde verschoben, nicht kopiert liegen gelassen oder gelöscht.
    assert not f2.exists()
    assert (settings.inbox_dir / "_duplikate" / "vertrag_kopie.txt").exists()


def test_process_file_marks_uncertain_classification(tmp_path, monkeypatch):
    settings = _FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(
        svc, "complete_json",
        lambda *a, **kw: _fake_classify_json(unsicher=True, unsicherheitsgrund="Mehrdeutiger Kunde"),
    )
    settings.inbox_dir.mkdir(parents=True)

    f = settings.inbox_dir / "unklar.txt"
    f.write_text("Ein Dokument mit unklarer Zuordnung", encoding="utf-8")
    ok, info = svc.process_file(f)
    assert ok
    assert info.startswith("⚠️ UNSICHER: ")


def test_pitch_deck_ueber_transkriptions_produkt_ist_kein_transkript():
    # Bug 2026-07-28: ein Pitch-Deck über ein Voice-/Transkriptions-Produkt
    # landete fälschlich in Meetings/, weil "transkript" ein Präfix von
    # "Transkription" ist und der alte Substring-Check das als Treffer wertete.
    assert not is_meeting_transcript(
        Path("Seifert_GmbH_pitch_deck.pptx"),
        "Vorstellung unserer KI-Lösung mit Live-Transkription für Meetings",
        {"tags": ["Pitch-Deck", "Transkription", "Lead"]},
    )
