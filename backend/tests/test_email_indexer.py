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


def test_match_lead_matches_hyphenated_lead_names(monkeypatch):
    monkeypatch.setattr(svc.classify, "list_lead_names", lambda: ["Zillmer-Elektrotechnik"])
    treffer = svc._match_lead(
        "Dierk Biendarra <dierk@zillmer-elektrotechnik.de>", "Update Zillmer X Prozessia", "Text"
    )
    assert treffer == "Zillmer-Elektrotechnik"


def test_match_lead_ignores_names_shorter_than_six_chars(monkeypatch):
    monkeypatch.setattr(svc.classify, "list_lead_names", lambda: ["ABC"])
    treffer = svc._match_lead("spam@example.com", "irrelevant", "abc irgendwo im Text")
    assert treffer is None


def test_korrespondenz_markdown_has_iso_date_and_zusammenfassung():
    md = svc._korrespondenz_markdown(
        "kunde", "TestKunde", "a@b.de", "Betreff", "Mon, 13 Jul 2026 14:59:32 +0000", "Kurzer Text."
    )
    assert "datum: 2026-07-13\n" in md
    assert "## Zusammenfassung\nKurzer Text." in md
    assert "## Volltext\nKurzer Text." in md


def test_korrespondenz_markdown_truncates_long_body_in_zusammenfassung():
    langer_text = "x" * 1000
    md = svc._korrespondenz_markdown("lead", "TestLead", "a@b.de", "Betreff", "Mon, 13 Jul 2026 14:59:32 +0000", langer_text)
    zusammenfassung_block = md.split("## Zusammenfassung\n")[1].split("\n\n## Volltext")[0]
    assert len(zusammenfassung_block) < 650
    assert zusammenfassung_block.endswith("…")
    assert langer_text in md  # voller Text bleibt im "## Volltext"-Abschnitt erhalten


def test_index_new_emails_falls_back_to_lead_when_no_customer_matches(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(svc.classify, "list_customer_names", lambda: [])
    monkeypatch.setattr(svc.classify, "list_lead_names", lambda: ["Zillmer-Elektrotechnik"])
    monkeypatch.setattr(svc.gmail_client, "is_authenticated", lambda: True)
    monkeypatch.setattr(svc.rag, "is_loaded", lambda: True)
    monkeypatch.setattr(svc.rag, "add_documents_batch", lambda docs: None)
    monkeypatch.setattr(svc.memory, "is_important_email", lambda *a: False)
    monkeypatch.setattr(
        svc.gmail_client,
        "get_emails",
        lambda top: [
            {
                "id": "abc123",
                "from": "Dierk Biendarra <dierk@zillmer-elektrotechnik.de>",
                "subject": "Update Zillmer X Prozessia",
                "date": "Mon, 13 Jul 2026 14:59:32 +0000",
                "body": "Neuer Termin passt.",
            }
        ],
    )

    class FakeSettings:
        vault_path = tmp_path
        email_cache_dir = tmp_path / "_agent" / "email_cache"

    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())

    n = svc.index_new_emails()
    assert n == 1
    korr_dir = tmp_path / "Leads" / "Zillmer-Elektrotechnik-Korrespondenz"
    dateien = list(korr_dir.glob("*.md"))
    assert len(dateien) == 1
    assert "lead: Zillmer-Elektrotechnik" in dateien[0].read_text(encoding="utf-8")
