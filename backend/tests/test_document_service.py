import pytest

from app.services import document_service as svc


class _FakeSettings:
    def __init__(self, tmp_path):
        self.vault_path = tmp_path


@pytest.fixture
def vault(tmp_path, monkeypatch):
    settings = _FakeSettings(tmp_path)
    monkeypatch.setattr(svc, "get_settings", lambda: settings)
    monkeypatch.setattr(svc.rag, "reindex_new_files", lambda: [])
    ordner = tmp_path / "Kunden" / "Schaufler"
    ordner.mkdir(parents=True)
    (ordner / "Bestellung.md").write_text(
        "Bestellung BEST-PROZESSIA-124952 vom 25.02.2026.\n"
        "Implementierung: 10.000,00 € netto. Laufender Betrieb 220 € pro Monat (AG0024, 27.05.2026).\n"
        "Laufzeit 12 Monate, Kündigungsfrist 3 Monate. Schaeufler Bergwerk GmbH & Co. KG, HRB 1034.\n"
        "Geschäftsführer: Herr Siegfried Heinrich. Kontakt: einkauf@schaufler.example, PLZ 66123.\n",
        encoding="utf-8",
    )
    return tmp_path


PFAD = "Kunden/Schaufler/Vertraege/Abnahme.pdf"
QUELLE = ["Kunden/Schaufler/Bestellung.md"]


def _doc(extra=""):
    return (
        "# Abnahmeprotokoll\n\n"
        "Bestellung BEST-PROZESSIA-124952 vom 25.02.2026, Angebot AG0024 vom 27.05.2026.\n\n"
        "| Position | Betrag |\n|---|---|\n| Implementierung | 10.000 € |\n| Betrieb | 220 € |\n\n"
        "Laufzeit 12 Monate, Kündigung mit 3 Monaten Frist. HRB 1034.\n" + extra
    )


def test_verified_document_is_created_with_pdf_and_source(vault):
    r = svc.create_pdf(PFAD, "Abnahmeprotokoll", _doc(), QUELLE)
    assert r["ok"], r
    pdf = vault / PFAD
    assert pdf.read_bytes().startswith(b"%PDF")
    assert (vault / "_agent" / "documents_src" / "Kunden/Schaufler/Vertraege/Abnahme.md").exists()
    assert r["download_url"] == "/api/files/download/" + PFAD
    assert r["verifiziert"]["anzahl"] >= 8


def test_wrong_amount_blocks_pdf(vault):
    r = svc.create_pdf(PFAD, "X", _doc("Monatlich 250 € Betrieb.\n"), QUELLE)
    assert not r["ok"]
    assert any(f["text"].startswith("250") for f in r["nicht_verifiziert"])
    assert not (vault / PFAD).exists()


def test_wrong_date_and_id_and_percent_block(vault):
    r = svc.create_pdf(PFAD, "X", _doc("Vom 26.02.2026, BEST-PROZESSIA-124953, 19 % USt.\n"), QUELLE)
    texts = {f["text"] for f in r["nicht_verifiziert"]}
    assert "26.02.2026" in texts
    assert "BEST-PROZESSIA-124953" in texts
    assert "19 %" in texts


def test_wrong_person_and_company_block(vault):
    r = svc.create_pdf(PFAD, "X", _doc("Vertreten durch Herr Peter Müller, Muster Werkzeugbau GmbH.\n"), QUELLE)
    texts = {f["text"] for f in r["nicht_verifiziert"]}
    assert "Herr Peter Müller" in texts
    assert "Muster Werkzeugbau GmbH" in texts


def test_wrong_duration_blocks(vault):
    r = svc.create_pdf(PFAD, "X", _doc("Kündigungsfrist 6 Monate.\n"), QUELLE)
    assert any(f["text"] == "6 Monate" for f in r["nicht_verifiziert"])


def test_umlaut_spelling_and_iso_date_match(vault):
    r = svc.create_pdf(PFAD, "X", "# T\n\nBestellt am 2026-02-25 bei Schäufler Bergwerk GmbH & Co. KG.\n", QUELLE)
    assert r["ok"], r


def test_freigegeben_allows_new_value_and_reports_it(vault):
    r = svc.create_pdf(
        PFAD, "X", _doc("Summe brutto 11.900 €.\n"), QUELLE,
        freigegeben=["11.900 € (berechnet: 10.000 + 19 % USt, Angabe Sebastian)"],
    )
    assert r["ok"], r
    assert r["freigegeben_nicht_in_quellen"]


def test_todays_date_is_allowed(vault):
    from datetime import date

    heute = date.today().strftime("%d.%m.%Y")
    r = svc.create_pdf(PFAD, "X", f"# T\n\nSaarbrücken, {heute}\n", QUELLE)
    assert r["ok"], r


def test_weitere_fakten_must_be_in_sources(vault):
    r = svc.create_pdf(PFAD, "X", "# T\n\nAnsprechpartner Erika Beispiel.\n", QUELLE, weitere_fakten=["Erika Beispiel"])
    assert not r["ok"]
    r = svc.create_pdf(PFAD, "X", "# T\n\nGeschäftsführer Siegfried Heinrich.\n", QUELLE, weitere_fakten=["Siegfried Heinrich"])
    assert r["ok"], r


def test_missing_sources_and_missing_source_file(vault):
    assert not svc.create_pdf(PFAD, "X", _doc(), [])["ok"]
    r = svc.create_pdf(PFAD, "X", _doc(), ["Kunden/Nope/gibt-es-nicht.md"])
    assert not r["ok"] and "nicht gefunden" in r["error"]


def test_target_rules(vault):
    assert not svc.create_pdf("Kunden/x.docx", "X", _doc(), QUELLE)["ok"]
    assert not svc.create_pdf("../out.pdf", "X", _doc(), QUELLE)["ok"]
    assert not svc.create_pdf("_agent/x.pdf", "X", _doc(), QUELLE)["ok"]
    assert not svc.create_pdf("nur-root.pdf", "X", _doc(), QUELLE)["ok"]


def test_existing_file_not_overwritten_without_flag(vault):
    assert svc.create_pdf(PFAD, "X", _doc(), QUELLE)["ok"]
    r = svc.create_pdf(PFAD, "X", _doc(), QUELLE)
    assert not r["ok"] and "existiert bereits" in r["error"]
    assert svc.create_pdf(PFAD, "X", _doc(), QUELLE, ueberschreiben=True)["ok"]


def test_german_and_english_number_formats():
    assert svc.Decimal("10000") in svc._to_decimal("10.000,00")
    assert svc.Decimal("10000") in svc._to_decimal("10,000.00")
    assert svc.Decimal("19.5") in svc._to_decimal("19,5")
    assert svc.Decimal("4500") in svc._to_decimal("4.500")


def test_signature_line_becomes_lines_not_hr():
    html_pdf = svc.markdown_to_pdf("# T\n\nText\n\n______________  ______________\n", "T")
    assert html_pdf.startswith(b"%PDF")
    assert 'class="sigline"' in svc._signature_blocks("______  ______")
    assert svc._signature_blocks("______  ______").count("sigline") == 2
