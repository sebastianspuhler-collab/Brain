from pathlib import Path

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


def test_pitch_deck_ueber_transkriptions_produkt_ist_kein_transkript():
    # Bug 2026-07-28: ein Pitch-Deck über ein Voice-/Transkriptions-Produkt
    # landete fälschlich in Meetings/, weil "transkript" ein Präfix von
    # "Transkription" ist und der alte Substring-Check das als Treffer wertete.
    assert not is_meeting_transcript(
        Path("Seifert_GmbH_pitch_deck.pptx"),
        "Vorstellung unserer KI-Lösung mit Live-Transkription für Meetings",
        {"tags": ["Pitch-Deck", "Transkription", "Lead"]},
    )
