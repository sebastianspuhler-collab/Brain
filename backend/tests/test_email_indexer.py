from app.services import email_indexer as svc


def test_match_customer_ignores_names_shorter_than_six_chars(monkeypatch):
    # Belegter Fall (2026-07-20): eine Spam-Mail mit "tpg" im Fließtext landete
    # im echten Kundenordner "TPG", weil die alte Mindestlänge 3 war.
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: ["TPG"])
    treffer = svc._match_customer(
        "Nick Todd <n.todd@mintonsentinel.info>",
        "Carlos | saidspentplanextra ZRSMQTG",
        "irgendein Text mit tpg zufaellig drin",
    )
    assert treffer is None


def test_match_customer_still_matches_names_six_chars_or_longer(monkeypatch):
    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: ["Schaufler"])
    treffer = svc._match_customer("jonas.roesch@schaufler.de", "AW: Bestellung", "Text")
    assert treffer == "Schaufler"
