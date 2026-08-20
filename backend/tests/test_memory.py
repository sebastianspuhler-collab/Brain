from app.services import memory as svc
from app.services.memory import _is_duplicate, is_important_email


# ── Kategorie-Normalisierung (2026-08-20) ───────────────────────────────────
# Hintergrund: append_to_memory() matchte Kategorien vorher rein exakt -
# "ANFORDERUNGEN" landete dadurch als eigene Parallel-Section neben einer
# schon bestehenden "ANFORDERUNG", ebenso "PREIS"/"PREISE" und
# "NÄCHSTE_SCHRITTE"/"NÄCHSTE SCHRITTE".

def test_find_existing_header_ignores_underscore_vs_space():
    content = "## NÄCHSTE_SCHRITTE\n- [x] alt\n"
    assert svc._find_existing_header("NÄCHSTE SCHRITTE", content) == "NÄCHSTE_SCHRITTE"


def test_find_existing_header_ignores_case():
    content = "## Kontext\n- [x] alt\n"
    assert svc._find_existing_header("KONTEXT", content) == "Kontext"


def test_find_existing_header_returns_none_for_new_category():
    content = "## KONTEXT\n- [x] alt\n"
    assert svc._find_existing_header("KUNDENWUNSCH", content) is None


def test_append_to_memory_reuses_existing_header_despite_spelling(tmp_path, monkeypatch):
    memory_path = tmp_path / "memory.md"
    memory_path.write_text("## NÄCHSTE_SCHRITTE\n- [2026-01-01 10:00] Altes Item\n", encoding="utf-8")

    class FakeSettings:
        pass

    fake = FakeSettings()
    fake.memory_path = memory_path
    monkeypatch.setattr(svc, "get_settings", lambda: fake)

    svc.append_to_memory("NÄCHSTE SCHRITTE", "Neues Item mit anderer Schreibweise")
    content = memory_path.read_text(encoding="utf-8")
    assert content.count("## NÄCHSTE") == 1
    assert "Neues Item mit anderer Schreibweise" in content


def test_duplicate_detected_by_shared_keywords():
    existing = "- [2026-01-01 10:00] Der Serverpreis liegt separat zur Verwaltungspauschale"
    new_fact = "Der Serverpreis liegt separat zur Pauschale, nicht enthalten"
    assert _is_duplicate(new_fact, existing)


def test_unrelated_fact_is_not_duplicate():
    existing = "- [2026-01-01 10:00] Der Serverpreis liegt separat zur Verwaltungspauschale"
    new_fact = "Kunde Mundinger wünscht Angebot bis Freitag"
    assert not _is_duplicate(new_fact, existing)


def test_newsletter_is_not_important():
    assert not is_important_email("newsletter@shop.de", "Dein Angebot", "unsubscribe hier")


def test_customer_email_is_important():
    assert is_important_email("kunde@schaufler.de", "Bestellung Nr. 42", "Bitte um Angebot")
