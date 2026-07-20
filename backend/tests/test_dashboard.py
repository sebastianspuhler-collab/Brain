from app.routers.dashboard import _ist_einzel_lead


def _write(tmp_path, name, kategorie, quelle):
    p = tmp_path / name
    p.write_text(f"---\nkategorie: {kategorie}\nquelle: {quelle}\n---\n\nInhalt.\n", encoding="utf-8")
    return p


def test_ist_einzel_lead_excludes_non_lead_kategorie(tmp_path):
    # Belegter Fall (2026-07-20): "Report Immobilienmarkler" trägt selbst
    # kategorie: Marketing, tauchte aber trotzdem als Lead im Dashboard auf,
    # weil nur die Quelldatei-Endung geprüft wurde.
    p = _write(tmp_path, "report.md", "Marketing", "Report Immobilienmarkler.docx")
    assert _ist_einzel_lead(p) is False


def test_ist_einzel_lead_accepts_real_lead(tmp_path):
    p = _write(tmp_path, "lead.md", "Lead", "M.Reuss X Prozessia.pdf")
    assert _ist_einzel_lead(p) is True


def test_ist_einzel_lead_still_excludes_massenlisten(tmp_path):
    p = _write(tmp_path, "liste.md", "Lead", "Kaltakquise.xlsx")
    assert _ist_einzel_lead(p) is False


def test_ist_einzel_lead_handles_missing_kategorie_field(tmp_path):
    # Alte Kalender-Lead-Stubs haben kategorie: Lead, aber ein Dokument ganz
    # ohne kategorie-Feld darf nicht crashen - fällt auf die Quelle-Prüfung zurück.
    p = tmp_path / "ohne_kategorie.md"
    p.write_text("---\nquelle: irgendwas.pdf\n---\n\nInhalt.\n", encoding="utf-8")
    assert _ist_einzel_lead(p) is True
