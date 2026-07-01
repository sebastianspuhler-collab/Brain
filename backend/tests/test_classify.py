from pathlib import Path

from app.services.classify import SKIP_EXTENSIONS, extract_text


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
