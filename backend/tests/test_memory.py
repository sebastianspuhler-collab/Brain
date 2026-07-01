from app.services.memory import _is_duplicate, is_important_email


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
